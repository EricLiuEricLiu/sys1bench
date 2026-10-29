"""Compact public records derived only from revalidated native Gateway runs."""

import tempfile
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path

from .adapters import GATEWAY_DECISION_ENDPOINT, GATEWAY_RESPONSES_ENDPOINT
from .campaign import preflight_campaign
from .core import canonical, digest, file_digest, load_json, parse_choice, require, write_json
from .gateway import GatewayDecisionAdapter, GatewayResponsesAdapter, allowed_model_ids
from .runner import now, harness_digest
from .scoring import read_run, score

SCHEMA = "system1-model-leaderboard-v1"
CONDITION = "independent-no-thinking"
ADAPTERS = {
    "vercel-responses": (GatewayResponsesAdapter, GATEWAY_RESPONSES_ENDPOINT),
    "vercel-decision": (GatewayDecisionAdapter, GATEWAY_DECISION_ENDPOINT),
}


def validate_live_provenance(config, meta):
    require(config["provider"] in ADAPTERS and meta.get("participant_kind") == "model" and meta.get("is_mock") is False,
            "Public leaderboard requires real Gateway model runs; mocks are never publishable")
    cls, endpoint = ADAPTERS[config["provider"]]
    require(meta.get("execution_mode") == "native_https" and meta.get("adapter_injected") is False,
            "Public leaderboard requires native HTTPS provenance, not an injected adapter")
    require(meta.get("adapter_class") == cls.__module__ + "." + cls.__qualname__ and meta.get("endpoint") == endpoint,
            "Native adapter/endpoint provenance mismatch")
    require(meta.get("status") == "complete" and meta.get("completed_items") == 17 and meta.get("planned_items") == 17,
            "Only complete 17-item native runs may be published")
    require(meta.get("started_at") and meta.get("finished_at"), "Missing real execution timestamps")
    started, finished = (datetime.fromisoformat(meta[k].replace("Z", "+00:00")) for k in ["started_at", "finished_at"])
    require(started.tzinfo is not None and finished.tzinfo is not None and started <= finished, "Invalid execution timestamps")


def replay_provenance(config, attempts):
    """Re-run production decoding offline; no constructor, credential or HTTP call."""
    cls, _ = ADAPTERS[config["provider"]]
    decoder = object.__new__(cls)
    decoder.config = config
    returned, providers = Counter(), Counter()
    verified_scored, response_count, unknown_provider = 0, 0, 0
    for rows in attempts.values():
        require(len(rows) == 1 and rows[0]["attempt"] == 1, "Published campaign cannot contain retries")
        row = rows[0]
        from .image_submission import submitted_images
        _, expected_images = submitted_images(row["request"], config)
        if config.get("image_preprocessing") or row.get("submitted_images") is not None:
            require(row.get("submitted_images") == expected_images, "Submitted image evidence differs from the registered input policy")
        if row["status"] in {"error", "timeout"}:
            continue
        raw = row["raw_response"]
        require(isinstance(raw, dict) and not raw.get("fixture"), "Synthetic provider fixtures are never publishable")
        reply = decoder.decode(raw, row["request_id"])
        expected = reply.status if reply.status != "ok" else ("valid" if parse_choice(reply.text) else "invalid")
        require(expected != "unexpected_output", "Reasoning, routing or output-protocol violation blocks publication")
        require(expected == row["status"] and reply.text == row["response_text"] and reply.returned_model == row["model_returned"],
                "Journal differs from replayed provider response")
        require(reply.usage == row["usage"] and reply.gateway_metadata == row["gateway_metadata"], "Provider provenance differs from raw response")
        routing = (reply.gateway_metadata or {}).get("routing", {})
        require(isinstance(routing, dict), "Invalid provider routing metadata")
        expected_models = allowed_model_ids(config["model"]) | {config["model"].split("/", 1)[1]}
        require(reply.returned_model in expected_models or routing.get("canonicalSlug") in allowed_model_ids(config["model"]),
                "No verified identity for the model that answered")
        if reply.returned_model:
            returned[reply.returned_model] += 1
        for key in ["finalProvider", "resolvedProvider"]:
            require(not routing.get(key) or routing[key] in config["gateway_only"], "Reported provider differs from the pinned provider")
        provider = routing.get("finalProvider") or routing.get("resolvedProvider")
        if provider:
            providers[provider] += 1
        else:
            unknown_provider += 1
        response_count += 1
        verified_scored += row["kind"] == "scored"
    require(verified_scored > 0, "No validated scored model responses; do not publish an API failure as a model score")
    return {"modelReturned": dict(returned), "providerReported": dict(providers),
            "providerUnreportedResponses": unknown_provider, "modelResponses": response_count,
            "validatedScoredResponses": verified_scored}


def model_record(plan, config, meta, summary, provenance):
    counts = summary["counts"]
    require(summary["complete"] and not summary["is_mock"] and counts["planned_scored"] == 15 and counts["practice"] == 2,
            "Publication requires 15 scored items plus two excluded practices")
    catalog = load_json(Path(__file__).parent / "fixtures/gateway/models.catalog.json")
    name = next(m["name"] for m in catalog["data"] if m["id"] == config["model"])
    return {
        "datasetVersion": plan["dataset_version"], "humanProtocol": plan["protocol"]["human_protocol_version"],
        "cohort": plan["dataset_version"] + ":" + plan["protocol"]["human_protocol_version"],
        "modelId": config["model"], "name": name, "protocol": plan["protocol_version"],
        "correct": counts["correct"], "total": counts["planned_scored"], "accuracy": summary["primary_accuracy"],
        "valid": counts["valid"], "unanswered": counts["planned_scored"] - counts["valid"],
        "failures": {k: v for k, v in counts["by_status"].items() if k != "valid"},
        "startedAt": meta["started_at"], "evaluatedAt": meta["finished_at"], "runId": meta["run_id"],
        "bankSha256": summary["answer_bank_sha256"], "real": True, "condition": CONDITION,
        "reasoningRequested": config["reasoning_effort"], "responseFormat": "native-choice" if config["provider"] == "vercel-decision" else "direct-ab",
        "adapter": config["provider"], "adapterClass": meta["adapter_class"], "endpoint": meta["endpoint"],
        "providerPinned": config["gateway_only"], **provenance,
        "imagePreprocessing": config.get("image_preprocessing", "original-captured-bytes"),
        "inputNotes": "Avatars were pixel-repeated to meet the provider image minimum; no new detail was added." if config.get("image_preprocessing") else None,
        "imagePreprocessingDisclosure": "Jev avatars repeat each decoded source pixel into a 6x6 block to meet its 280px minimum; no new detail. Other models receive original bytes." if config.get("image_preprocessing") else None,
        "revalidation": {k: v for k, v in meta.get("revalidation", {}).items() if k != "original_run_directory"} or None,
        "protocolSha256": plan["protocol_sha256"], "planSha256": plan["plan_sha256"],
        "configSha256": meta["config_sha256"], "journalSha256": meta["attempts_file_sha256"],
        "harnessSha256": meta["harness_source_sha256"], "sourceRevision": meta.get("source_revision"),
    }


def revalidate_native_run(original_run, out):
    """Derive decoder corrections without another request or altering source journals."""
    original_run, out = Path(original_run).resolve(), Path(out)
    plan, config, meta, attempts = read_run(original_run)
    validate_live_provenance(config, meta)
    require(not out.exists(), "Derived run already exists")
    cls, _ = ADAPTERS[config["provider"]]
    decoder = object.__new__(cls)
    decoder.config = config
    corrected, changes = [], 0
    for rows in attempts.values():
        for row in rows:
            derived = dict(row)
            if row["status"] not in {"error", "timeout"}:
                reply = decoder.decode(row["raw_response"], row["request_id"])
                status = reply.status if reply.status != "ok" else ("valid" if parse_choice(reply.text) else "invalid")
                choice = parse_choice(reply.text) if status == "valid" else None
                require(row["status"] != "valid" or (status == "valid" and choice == row["parsed_choice"]), "A valid original model answer cannot be replaced")
                if status != row["status"] or choice != row["parsed_choice"]:
                    require(row["status"] == "unexpected_output" and (row.get("gateway_metadata") or {}).get("routing", {}).get("canonicalSlug") in allowed_model_ids(config["model"]),
                            "Only verified canonical-alias decoder corrections are allowed")
                    derived.update(status=status, parsed_choice=choice)
                    changes += 1
            corrected.append(derived)
    out.mkdir(parents=True, exist_ok=False)
    for name in ["plan.json", "config.json"]:
        shutil.copyfile(original_run / name, out / name)
    if (original_run / "harness-source").is_dir():
        shutil.copytree(original_run / "harness-source", out / "harness-source")
    (out / "attempts.jsonl").write_text("".join(canonical(row) + "\n" for row in corrected))
    meta = {**meta, "attempts_file_sha256": file_digest(out / "attempts.jsonl"),
            "revalidation": {"original_run_directory": str(original_run), "original_run_sha256": file_digest(original_run / "run.json"),
                             "original_journal_sha256": file_digest(original_run / "attempts.jsonl"), "revalidated_at": now(),
                             "decoder_harness_sha256": harness_digest(), "changed_validation_records": changes,
                             "reason": "Verified Gateway creator-prefix alias normalization only; requests, raw replies, timestamps and all valid answers are preserved", "additional_model_calls": 0}}
    write_json(out / "run.json", meta)
    return meta


def validate_revalidation(run_dir, meta, attempts):
    if not meta.get("revalidation"):
        return
    lineage = meta["revalidation"]
    parent = Path(lineage["original_run_directory"])
    require(file_digest(parent / "run.json") == lineage["original_run_sha256"] and file_digest(parent / "attempts.jsonl") == lineage["original_journal_sha256"], "Original journal lineage changed")
    plan, config, prior_meta, prior = read_run(parent)
    validate_live_provenance(config, prior_meta)
    require(meta["run_id"] == prior_meta["run_id"] and meta["harness_source_sha256"] == prior_meta["harness_source_sha256"], "Revalidation changed execution identity")
    require(load_json(Path(run_dir) / "plan.json") == plan and load_json(Path(run_dir) / "config.json") == config, "Revalidation changed original inputs")
    for item_id, rows in attempts.items():
        require(len(rows) == len(prior[item_id]), "Revalidation changed attempt count")
        for row, original in zip(rows, prior[item_id]):
            require({k: v for k, v in row.items() if k not in {"status", "parsed_choice"}} == {k: v for k, v in original.items() if k not in {"status", "parsed_choice"}}, "Revalidation changed recorded request/response data")
            require(original["status"] != "valid" or (row["status"], row["parsed_choice"]) == (original["status"], original["parsed_choice"]), "Revalidation replaced a valid answer")


def export_leaderboard(manifest_path, runs, out):
    manifest, jobs = preflight_campaign(manifest_path)
    require(len(jobs) == 4 and manifest["maximum_requests"] == 68, "Public primary comparison requires the four-model 68-request campaign")
    runs, out = Path(runs), Path(out)
    require(not out.exists(), "Public export exists; preserve it and choose a new directory")
    require(load_json(runs / "campaign.json") == manifest, "Executed campaign differs from approved manifest")
    completed = load_json(runs / "campaign-results.private.json")
    require(isinstance(completed, list) and len(completed) == 4, "Campaign must contain all four completed model runs")
    records, sources = [], []
    with tempfile.TemporaryDirectory(prefix="system1-public-recheck-") as temporary:
        for number, (entry, paths, frozen_plan, frozen_config) in enumerate(jobs, 1):
            run_dir = runs / f"{number:02d}" / "run"
            plan, config, meta, attempts = read_run(run_dir)
            require(plan == frozen_plan and config == frozen_config and plan["variant"] == "primary", "Run differs from frozen primary plan/config")
            validate_live_provenance(config, meta)
            archive = run_dir / "harness-source"
            require(archive.is_dir() and digest({p.name: p.read_text(encoding="utf-8") for p in sorted(archive.glob("*.py"))}) == meta["harness_source_sha256"],
                    "Executed harness source archive/hash mismatch")
            validate_revalidation(run_dir, meta, attempts)
            require(completed[number - 1]["run_id"] == meta["run_id"] and completed[number - 1]["model"] == config["model"], "Completed-run identity mismatch")
            provenance = replay_provenance(config, attempts)
            summary, _ = score(run_dir, paths["bank"], Path(temporary) / str(number))
            record = model_record(plan, config, meta, summary, provenance)
            records.append(record)
            sources.append({"runId": meta["run_id"], "runDirectory": str(run_dir.resolve()),
                            "filesSha256": {name: file_digest(run_dir / name) for name in ["run.json", "config.json", "plan.json", "attempts.jsonl"]},
                            "bankSha256": summary["answer_bank_sha256"]})
    require(len({r["modelId"] for r in records}) == 4 and len({r["bankSha256"] for r in records}) == 1,
            "Public records must contain four distinct models on one exact bank")
    first = jobs[0][2]
    public = {"schemaVersion": SCHEMA, "publishedAt": now(), "datasetVersion": first["dataset_version"],
              "humanProtocol": first["protocol"]["human_protocol_version"], "cohort": records[0]["cohort"],
              "benchmarkId": first["benchmark_id"], "benchmarkVersion": first["benchmark_version"],
              "bankSha256": records[0]["bankSha256"], "stimuliSha256": first["stimuli_sha256"],
              "outcome": "impressions", "condition": CONDITION, "pilot": True, "rankingValidated": False,
              "feedbackDifference": first["protocol"]["comparability"],
              "denominatorPolicy": "First attempt on all 15 scored pairs; invalid/error/timeout/refusal/unrun count as incorrect. Two practices excluded.",
              "models": records}
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "leaderboard.public.json", public)
    write_json(out / "publication-manifest.private.json", {"schemaVersion": SCHEMA, "campaignSha256": digest(manifest),
        "publicSha256": file_digest(out / "leaderboard.public.json"), "sources": sources,
        "note": "Only leaderboard.public.json is intended for API/static integration. No labels, raw responses, request IDs, image bytes or keys are public."})
    return {"models": len(records), "real": True, "datasetVersion": first["dataset_version"],
            "publicFile": str(out / "leaderboard.public.json"), "publicSha256": file_digest(out / "leaderboard.public.json")}

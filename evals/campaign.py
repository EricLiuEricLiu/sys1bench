"""One sequential primary run per approved entry; no automatic repeats or tuning."""

import os
from pathlib import Path

from .core import CURRENT_DATASET_VERSION, DECISION_PROTOCOL_VERSION, PROTOCOL_VERSION, digest, file_digest, load_json, prepare, require, write_json
from .runner import run, validate_execution
from .scoring import labels_for, score


def prepare_campaign(out, seed="pilot-cohort-001"):
    """Freeze the user-approved four-model disabled-thinking comparison offline."""
    package = Path(__file__).parent.resolve()
    data = package / ("fixtures/cross-author-v" + CURRENT_DATASET_VERSION)
    require((data / "stimuli.client.json").is_file(), "Current 0.5.0 bank is not frozen yet; no historical paid campaign may be prepared")
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    plan_paths = {}
    for kind, protocol in [("direct", PROTOCOL_VERSION), ("decision", DECISION_PROTOCOL_VERSION)]:
        plan = prepare(data / "stimuli.client.json", seed, avatar_manifest=data / "avatars/avatar-manifest.private.json", protocol_version=protocol)
        plan_paths[kind] = out / (kind + "-primary-plan.json")
        write_json(plan_paths[kind], plan)
    entries = []
    for config_path in sorted((package / "configs/gateway").glob("*.json")):
        config = load_json(config_path)
        plan_path = plan_paths["decision" if config["provider"] == "vercel-decision" else "direct"]
        plan = load_json(plan_path)
        validate_execution(plan, config)
        paths = {"plan": plan_path, "config": config_path, "bank": data / "question-bank.server.json"}
        entry = {"model": config["model"], "planned_items": len(plan["items"]), "protocol_version": plan["protocol_version"]}
        for name, path in paths.items():
            entry[name] = os.path.relpath(path, out)
            entry[name + "_file_sha256"] = file_digest(path)
        entries.append(entry)
    manifest = {"schema_version": "gateway-campaign-v1", "lineup_approved": True, "primary_runs_per_model": 1,
                "automatic_mirrors": 0, "maximum_requests": sum(e["planned_items"] for e in entries), "entries": entries,
                "reasoning_policy": "disabled only; no minimal or low reasoning; no fallback models",
                "spending_scope": "Eric authorized intended comparison with no spending cap. This manifest bounds request count; local Gateway key is still required."}
    write_json(out / "campaign.json", manifest)
    preflight_campaign(out / "campaign.json")
    return manifest


def preflight_campaign(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    manifest = load_json(manifest_path)
    require(manifest.get("schema_version") == "gateway-campaign-v1", "Unknown campaign schema")
    require(manifest.get("lineup_approved") is True, "Campaign lineup is pending user selection; no calls allowed")
    require(manifest.get("primary_runs_per_model") == 1 and manifest.get("automatic_mirrors") == 0, "Campaign must contain exactly one primary run per model")
    require(isinstance(manifest.get("entries"), list) and 1 <= len(manifest["entries"]) <= 4, "Campaign must contain 1 to 4 explicit model entries")
    require(manifest["maximum_requests"] == sum(e["planned_items"] for e in manifest["entries"]), "Campaign request bound mismatch")
    seen, jobs = set(), []
    cohort = None
    for entry in manifest["entries"]:
        paths = {k: (manifest_path.parent / entry[k]).resolve() for k in ["plan", "config", "bank"]}
        for k, path in paths.items():
            require(file_digest(path) == entry[k + "_file_sha256"], "Campaign source file changed; freeze a new manifest")
        plan, config = validate_execution(load_json(paths["plan"]), load_json(paths["config"]))
        labels_for(plan, paths["bank"])
        require(config["provider"].startswith("vercel-") and config["diagnostic_retries"] == 0, "Campaign requires Gateway and zero retries")
        require(config["model"] == entry["model"] and config["model"] not in seen, "Duplicate/different campaign model")
        require(plan["variant"] == "primary" and len(plan["items"]) == entry["planned_items"], "Invalid campaign plan/size")
        require(cohort is None or plan["stimuli_sha256"] == cohort, "Campaign stimuli must match across models")
        cohort = plan["stimuli_sha256"]
        seen.add(config["model"])
        jobs.append((entry, paths, plan, config))
    return manifest, jobs


def run_campaign(manifest_path, out, *, allow_paid=False):
    manifest, jobs = preflight_campaign(manifest_path)
    require(allow_paid, "Campaign execution requires --allow-paid; preflight makes zero model calls")
    require(bool(os.environ.get("AI_GATEWAY_API_KEY")), "AI_GATEWAY_API_KEY is missing; no requests sent")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "campaign.json", manifest)
    results = []
    for index, (entry, paths, plan, config) in enumerate(jobs, 1):
        root = out / f"{index:02d}"
        meta = run(plan, config, root / "run", allow_paid=True)
        summary, _ = score(root / "run", paths["bank"], root / "score.private")
        results.append({"model": config["model"], "run_id": meta["run_id"], "protocol_version": plan["protocol_version"],
                        "complete": summary["complete"], "primary_accuracy": summary["primary_accuracy"]})
        write_json(out / "campaign-results.private.json", results)
    return {"campaign_sha256": digest(manifest), "completed_runs": len(results), "maximum_model_requests": manifest["maximum_requests"], "is_mock": False}

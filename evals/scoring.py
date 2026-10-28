"""Trusted local scoring: outcome labels enter here, after inference is over."""

import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

from .adapters import validate_config
from .core import digest, file_digest, load_json, parse_choice, request_for, require, validate_plan, write_json
from .runner import now


def wilson(successes, total):
    if not total:
        return None
    z = 1.959963984540054
    p = successes / total
    denom = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denom
    radius = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return [max(0.0, center - radius), min(1.0, center + radius)]


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    i = (len(values) - 1) * p
    lo, hi = math.floor(i), math.ceil(i)
    return values[lo] + (values[hi] - values[lo]) * (i - lo)


def cluster_interval(answers, seed="cluster-bootstrap-v1", draws=5000):
    if any(len(a.get("author_cluster_ids", [])) > 1 for a in answers):
        return {"method": "not estimated for crossed-author pairs", "interval_95": None,
                "interpretation": "Each item involves two authors and authors may recur across pairs. The historical one-author bootstrap is invalid for this dependency structure; collect more data and preregister a crossed-author analysis."}
    groups = defaultdict(list)
    for a in answers:
        groups[a["author_cluster_id"]].append(int(a["correct"]))
    if len(groups) < 2:
        return None
    clusters = sorted(groups)
    rng = random.Random(int(digest(seed), 16))
    samples = []
    for _ in range(draws):
        selected = rng.choices(clusters, k=len(clusters))
        numerator = sum(sum(groups[g]) for g in selected)
        denominator = sum(len(groups[g]) for g in selected)
        samples.append(numerator / denominator)
    return {"method": "author-cluster percentile bootstrap", "draws": draws, "seed": seed,
            "clusters": len(clusters), "interval_95": [percentile(samples, .025), percentile(samples, .975)],
            "interpretation": "Exploratory sensitivity only: few editorially selected authors do not establish population coverage; intervals can degenerate."}


def labels_for(plan, bank_path):
    bank = load_json(bank_path)
    require(bank["version"] == plan["dataset_version"], "Answer bank version differs from stimuli")
    require(bank.get("outcome") == "cumulative_snapshot_views", "Unexpected outcome definition")
    if plan["dataset_version"] == "0.4.0":
        require(bank.get("timing") == {"exposureMs": 6000, "decisionMs": 4000}, "Current bank timing differs from the frozen human protocol")
    practice = bank["practice"] if isinstance(bank["practice"], list) else [bank["practice"]]
    pairs = [("practice", p) for p in practice] + [("scored", p) for p in bank["pairs"]]
    require(len(pairs) == len(plan["items"]), "Answer bank item count mismatch")
    index = {p["id"]: (kind, p) for kind, p in pairs}
    require(len(index) == len(pairs) and set(index) == {i["item_id"] for i in plan["items"]}, "Answer bank item IDs mismatch")
    labels = {}
    for item in plan["items"]:
        kind, pair = index[item["item_id"]]
        require(kind == item["kind"], "Practice/scored mismatch")
        by_id = {pair[s]["id"]: pair[s] for s in ["left", "right"]}
        require(set(by_id) == {item[s]["id"] for s in ["A", "B"]}, "Post IDs differ from frozen stimuli")
        authors = []
        for s in ["A", "B"]:
            post = by_id[item[s]["id"]]
            visible = post.get("displayText") if "author" in item[s] else post["text"]
            require(visible == item[s]["text"], "Post text differs from frozen stimuli")
            if "author" in item[s]:
                require({k: post["author"][k] for k in ["name", "handle"]} == {k: item[s]["author"][k] for k in ["name", "handle"]}, "Visible author differs from frozen stimuli")
                require([m["sha256"] for m in post["media"]] == [m["sha256"] for m in item[s]["images"]], "Captured images differ from frozen stimuli")
            require(type(post.get("views")) is int and post["views"] > 0, "Missing/invalid view outcome")
            url = urlparse(post["url"])
            path = url.path.strip("/").split("/")
            named_url = len(path) == 3 and path[0] != "i" and path[1:] == ["status", post["id"]]
            canonical_url = path in [["i", "web", "status", post["id"]], ["i", "status", post["id"]]]
            require(url.hostname in {"x.com", "www.x.com", "twitter.com"} and (named_url or canonical_url), "Invalid source URL in answer bank")
            if "author" in item[s]:
                source_handle = post["author"]["handle"].casefold()
                require(not named_url or path[0].casefold() == source_handle, "Source URL author differs from visible author")
                authors.append(source_handle)
            else:
                require(named_url, "Historical hidden-author bank requires an author-bearing source URL")
                authors.append(path[0].casefold())
        cross_author = plan["dataset_version"] == "0.4.0"
        if cross_author:
            require(authors[0] != authors[1], "Current protocol requires different-author pairs")
            ids = [by_id[item[s]["id"]]["author"]["id"] for s in ["A", "B"]]
            require(all(isinstance(a, str) and a for a in ids) and ids[0] != ids[1], "Current protocol requires distinct source author IDs")
            require(all(by_id[item[s]["id"]]["views"] >= 100_000 for s in ["A", "B"]), "Current bank requires at least 100000 captured views per post")
        else:
            require(authors[0] == authors[1], "Historical protocol requires same-author pairs")
        av, bv = by_id[item["A"]["id"]]["views"], by_id[item["B"]["id"]]["views"]
        require(av != bv, "Tied outcomes require a new protocol/dataset")
        cluster_ids = sorted({digest(a)[:16] for a in authors})
        labels[item["item_id"]] = {"correct_choice": "A" if av > bv else "B", "author_cluster_id": None if cross_author else digest(authors[0])[:16], "author_cluster_ids": cluster_ids}
    return labels, bank


def read_run(run_dir):
    root = Path(run_dir)
    plan = validate_plan(load_json(root / "plan.json"))
    config, meta = validate_config(load_json(root / "config.json")), load_json(root / "run.json")
    require(meta["plan_sha256"] == plan["plan_sha256"] and meta["config_sha256"] == digest(config), "Run/plan/config hash mismatch")
    require(meta["participant_kind"] == ("mock" if config["provider"] == "mock" else "model"), "Participant kind mismatch")
    require(meta["is_mock"] == (config["provider"] == "mock") and meta["provider"] == config["provider"] and meta["model_requested"] == config["model"], "Provider metadata mismatch")
    journal = root / "attempts.jsonl"
    if meta.get("attempts_file_sha256"):
        require(meta["attempts_file_sha256"] == file_digest(journal), "Attempt journal hash mismatch")
    else:
        require(meta["status"] != "complete", "Complete run lacks journal hash")
    planned = {i["item_id"]: i for i in plan["items"]}
    attempts = defaultdict(list)
    lines = journal.read_text(encoding="utf-8").splitlines()
    for pos, line in enumerate(lines):
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A partial last write after SIGKILL is not silently discarded.
            raise ValueError(f"Corrupt attempt journal line {pos + 1}; preserve and repair before scoring") from None
        require(row["run_id"] == meta["run_id"] and row["item_id"] in planned, "Unexpected journal run/item")
        item = planned[row["item_id"]]
        require(row["kind"] == item["kind"] and row["request"] == request_for(item) and row["request_sha256"] == item["request_sha256"], "Attempt request differs from frozen plan")
        previous = attempts[row["item_id"]]
        require(row["attempt"] == len(previous) + 1 and row["is_primary_attempt"] == (row["attempt"] == 1), "Duplicate/missing/out-of-order attempt")
        require(row["attempt"] <= config["diagnostic_retries"] + 1, "Unregistered retry")
        require(not previous or previous[-1]["retryable"], "Retry after nonretryable response")
        expected = parse_choice(row["response_text"]) if row["status"] == "valid" else None
        require(row["parsed_choice"] == expected and (row["status"] != "valid" or expected is not None), "Parsed answer/status mismatch")
        require(row["status"] in {"valid", "invalid", "timeout", "error", "refused", "provider_incomplete", "unexpected_output"}, "Unknown attempt status")
        require(type(row["latency_ms"]) in {float, int} and row["latency_ms"] >= 0, "Invalid latency")
        previous.append(row)
    return plan, config, meta, attempts


def score(run_dir, bank_path, out):
    plan, config, meta, attempts = read_run(run_dir)
    labels, bank = labels_for(plan, bank_path)
    answers = []
    for ordinal, item in enumerate(plan["items"]):
        rows = attempts[item["item_id"]]
        primary = rows[0] if rows else None
        choice = primary["parsed_choice"] if primary else None
        answer = {
            "schema_version": plan["schema_version"], "run_id": meta["run_id"],
            "item_id": item["item_id"], "ordinal": ordinal, "kind": item["kind"],
            "A_post_id": item["A"]["id"], "B_post_id": item["B"]["id"], "flipped": item["flipped"],
            "status": primary["status"] if primary else "not_run", "choice": choice,
            "selected_post_id": item[choice]["id"] if choice else None,
            "correct_choice": labels[item["item_id"]]["correct_choice"],
            "correct": choice == labels[item["item_id"]]["correct_choice"],
            "author_cluster_id": labels[item["item_id"]]["author_cluster_id"],
            "author_cluster_ids": labels[item["item_id"]]["author_cluster_ids"],
            "primary_latency_ms": primary["latency_ms"] if primary else None,
            "attempt_count": len(rows), "request_sha256": item["request_sha256"],
        }
        answers.append(answer)
    scored = [a for a in answers if a["kind"] == "scored"]
    correct, total = sum(a["correct"] for a in scored), len(scored)
    latencies = [a["primary_latency_ms"] for a in scored if a["primary_latency_ms"] is not None]
    flat = [row for rows in attempts.values() for row in rows]
    costs = [r["estimated_cost_usd"] for r in flat]
    reported_costs = [r.get("gateway_reported_cost_usd") for r in flat]
    usage = [r["usage"] for r in flat]
    usage_totals = None
    if usage and all(isinstance(u, dict) and all(type(u.get(k)) is int for k in ["input_tokens", "output_tokens", "total_tokens"]) for u in usage):
        usage_totals = {k: sum(u[k] for u in usage) for k in ["input_tokens", "output_tokens", "total_tokens"]}
    complete = meta["status"] == "complete" and all(attempts[i["item_id"]] for i in plan["items"])
    summary = {
        "schema_version": plan["schema_version"], "run": meta,
        "benchmark_id": plan["benchmark_id"], "benchmark_version": plan["benchmark_version"],
        "dataset_version": plan["dataset_version"], "stimuli_sha256": plan["stimuli_sha256"],
        "source_file_sha256": plan["source_file_sha256"], "answer_bank_sha256": file_digest(bank_path),
        "protocol_version": plan["protocol_version"], "protocol_sha256": plan["protocol_sha256"],
        "config_sha256": meta["config_sha256"], "plan_sha256": plan["plan_sha256"],
        "assignment_seed": plan["assignment_seed"], "variant": plan["variant"],
        "split_status": plan["split_status"], "scored_at": now(),
        "complete": complete, "is_mock": meta["is_mock"], "ranking_validated": False,
        "counts": {"planned_scored": total, "correct": correct, "valid": sum(a["status"] == "valid" for a in scored),
                   "by_status": dict(Counter(a["status"] for a in scored)), "practice": len(answers) - total,
                   "all_attempts_including_practice_and_retries": len(flat)},
        "primary_accuracy": correct / total,
        "denominator_policy": "All planned scored pairs; invalid/error/timeout/refusal/not_run count as incorrect; first attempt only.",
        "wilson_95_iid_reference": wilson(correct, total),
        "wilson_caveat": "Conditional IID reference only; item independence fails with repeated authors, so this is not a population confidence interval.",
        "cluster_bootstrap_sensitivity": cluster_interval(scored),
        "latency_ms": {"n": len(latencies), "median": statistics.median(latencies) if latencies else None,
                       "p95": percentile(latencies, .95), "scope": "all observed first attempts of scored pairs, including failures; socket timeout is not a human glimpse"},
        "usage_totals_all_attempts": usage_totals,
        "known_estimated_cost_usd": sum(c for c in costs if c is not None) if any(c is not None for c in costs) else None,
        "estimated_cost_complete": bool(costs) and all(c is not None for c in costs),
        "known_gateway_reported_cost_usd": sum(c for c in reported_costs if c is not None) if any(c is not None for c in reported_costs) else None,
        "gateway_reported_cost_complete": bool(reported_costs) and all(c is not None for c in reported_costs),
        "billed_cost_usd": None, "pricing": config.get("pricing"),
        "limitations": bank["limitations"] + [
            "No registered held-out split exists for this pilot; it must not be described as a held-out generalization test.",
            "Model requests are independent choices with unscored practice calls and no feedback; humans have timed visual presentation and educational feedback.",
            "Captured image bytes are identical at submission; provider-specific image preprocessing can differ. No internal visual representation equivalence is claimed.",
            "Exact post text may be recognized from pretraining; hiding metadata does not establish absence of memorization.",
            "Mirrored-side and repeat-seed runs reuse the same posts; they are diagnostics, not additional independent observations.",
        ],
    }
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "answers.jsonl").write_text("".join(json.dumps(a, ensure_ascii=False, sort_keys=True) + "\n" for a in answers), encoding="utf-8")
    summary["answers_file_sha256"] = file_digest(out / "answers.jsonl")
    write_json(out / "summary.json", summary)
    return summary, answers


def compare_mirror(primary_dir, mirrored_dir):
    p, m = load_json(Path(primary_dir) / "summary.json"), load_json(Path(mirrored_dir) / "summary.json")
    for field in ["benchmark_id", "benchmark_version", "stimuli_sha256", "dataset_version", "protocol_sha256", "assignment_seed", "config_sha256"]:
        require(p[field] == m[field], f"Mirror comparison differs on {field}")
    require(p["variant"] == "primary" and m["variant"] == "mirrored", "Expected primary and mirrored variants")
    require(p["run"]["participant_kind"] == m["run"]["participant_kind"], "Participant kinds differ")
    def read_answers(folder):
        return {a["item_id"]: a for a in [json.loads(line) for line in (Path(folder) / "answers.jsonl").read_text().splitlines()] if a["kind"] == "scored"}
    pa, ma = read_answers(primary_dir), read_answers(mirrored_dir)
    require(set(pa) == set(ma), "Mirror item sets differ")
    comparable, consistent = 0, 0
    for item_id in pa:
        a, b = pa[item_id], ma[item_id]
        require(a["A_post_id"] == b["B_post_id"] and a["B_post_id"] == b["A_post_id"], "Sides not mirrored")
        if a["status"] == b["status"] == "valid":
            comparable += 1
            consistent += a["selected_post_id"] == b["selected_post_id"]
    return {"diagnostic": "mirrored-side-v1", "primary_run_id": p["run"]["run_id"], "mirrored_run_id": m["run"]["run_id"],
            "is_mock": p["is_mock"], "planned_pairs": len(pa), "both_valid_pairs": comparable,
            "same_post_choices": consistent, "same_post_fraction_when_both_valid": consistent / comparable if comparable else None,
            "primary_A_choices": sum(a["choice"] == "A" for a in pa.values()),
            "mirror_A_choices": sum(a["choice"] == "A" for a in ma.values()),
            "primary_accuracy": p["primary_accuracy"], "mirrored_accuracy": m["primary_accuracy"],
            "note": "Separate diagnostics, never pool these into a 30-item benchmark. Invalid pairs remain in each run's accuracy denominator."}

import argparse
import json
import os
from pathlib import Path

from .adapters import validate_config
from .core import PROTOCOL_VERSION, DECISION_PROTOCOL_VERSION, load_json, prepare, read_stimuli, require, validate_plan, write_json
from .assets import capture_avatars
from .export import export_records
from .runner import run, validate_execution
from .scoring import compare_mirror, score


def main():
    parser = argparse.ArgumentParser(description="System 1 Bench: offline-first, label-isolated model evaluations")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("inspect", help="Validate client stimuli and show environment availability without values")
    p.add_argument("--stimuli", required=True)
    p.add_argument("--avatar-manifest")
    p = sub.add_parser("capture-avatars", help="Explicit free source-image downloads; never invokes a model")
    p.add_argument("--stimuli", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("prepare", help="Freeze every practice/scored item without reading outcomes")
    p.add_argument("--stimuli", required=True)
    p.add_argument("--seed", required=True)
    p.add_argument("--mirror", action="store_true")
    p.add_argument("--out", required=True)
    p.add_argument("--avatar-manifest")
    p.add_argument("--protocol", choices=[PROTOCOL_VERSION, DECISION_PROTOCOL_VERSION], default=PROTOCOL_VERSION)
    p = sub.add_parser("preflight", help="Validate plan/config locally; never contacts a provider")
    p.add_argument("--plan", required=True)
    p.add_argument("--config", required=True)
    p = sub.add_parser("run", help="Execute all frozen items; mock by default config, paid runs opt in")
    p.add_argument("--plan", required=True)
    p.add_argument("--config", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--allow-paid", action="store_true")
    p = sub.add_parser("score", help="Join labels locally; all planned scored items remain in denominator")
    p.add_argument("--run", required=True)
    p.add_argument("--bank", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("export", help="Create private JSONL/SQL for future trusted ingestion; no network")
    p.add_argument("--run", required=True)
    p.add_argument("--score", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("mirror-report", help="Compare primary/mirror runs without pooling scores")
    p.add_argument("--primary-score", required=True)
    p.add_argument("--mirrored-score", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("prepare-campaign", help="Freeze approved four-model, 68-request primary plan offline")
    p.add_argument("--out", required=True)
    p.add_argument("--seed", default="pilot-cohort-001")
    p = sub.add_parser("campaign-preflight", help="Validate bounded Gateway campaign; never contacts models")
    p.add_argument("--manifest", required=True)
    p = sub.add_parser("campaign", help="One primary run per approved model; requires a new output directory")
    p.add_argument("--manifest", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--allow-paid", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "inspect":
            ds = read_stimuli(args.stimuli, args.avatar_manifest)
            result = {k: v for k, v in ds.items() if k != "items"}
            result.update(scored=sum(i["kind"] == "scored" for i in ds["items"]), practice=sum(i["kind"] == "practice" for i in ds["items"]),
                          provider_environment_present={k: bool(os.environ.get(k)) for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "AI_GATEWAY_API_KEY"]})
        elif args.command == "capture-avatars":
            manifest = capture_avatars(args.stimuli, args.out)
            result = {"captured_avatars": len(manifest["entries"]), "model_calls": 0, "manifest": str(Path(args.out) / "avatar-manifest.private.json")}
        elif args.command == "prepare":
            require(not Path(args.out).exists(), "Output already exists; refuse to overwrite frozen plan")
            plan = prepare(args.stimuli, args.seed, args.mirror, args.avatar_manifest, args.protocol)
            write_json(args.out, plan)
            result = {k: plan[k] for k in ["plan_sha256", "stimuli_sha256", "variant", "dataset_version"]}
            result["planned_items"] = len(plan["items"])
        elif args.command == "preflight":
            plan, config = validate_execution(load_json(args.plan), load_json(args.config))
            require(not config["model"].startswith("REPLACE_"), "Replace the example model identifier after model selection")
            if config["provider"].startswith("vercel-"):
                from .gateway import validate_gateway_config
                validate_gateway_config(config)
            result = {"network_requests": 0, "provider": config["provider"], "model": config["model"],
                      "reasoning_effort_requested": config["reasoning_effort"], "max_output_tokens": config["max_output_tokens"],
                      "planned_items": len(plan["items"]), "maximum_requests_including_diagnostic_retries": len(plan["items"]) * (1 + config["diagnostic_retries"]),
                      "api_key_available": bool(os.environ.get("AI_GATEWAY_API_KEY" if config["provider"].startswith("vercel-") else "OPENAI_API_KEY")) if config["provider"] != "mock" else None,
                      "note": "Local validation only. Model access and reasoning support have not been tested. No billed-cost cap is enforced."}
        elif args.command == "run":
            plan, config = load_json(args.plan), load_json(args.config)
            require(not config["model"].startswith("REPLACE_"), "Replace the example model identifier after model selection")
            result = run(plan, config, args.out, allow_paid=args.allow_paid)
        elif args.command == "score":
            summary, _ = score(args.run, args.bank, args.out)
            result = {"run_id": summary["run"]["run_id"], "is_mock": summary["is_mock"], "counts": summary["counts"],
                      "note": "Mock outputs are software fixtures, never model results." if summary["is_mock"] else "Pilot only; inspect summary limitations and uncertainty."}
        elif args.command == "export":
            result = export_records(args.run, args.score, args.out)
        elif args.command in {"prepare-campaign", "campaign", "campaign-preflight"}:
            from .campaign import prepare_campaign, preflight_campaign, run_campaign
            if args.command == "prepare-campaign":
                manifest = prepare_campaign(args.out, args.seed)
                result = {"model_calls": 0, "models": len(manifest["entries"]), "maximum_requests": manifest["maximum_requests"], "manifest": str(Path(args.out) / "campaign.json")}
            elif args.command == "campaign":
                result = run_campaign(args.manifest, args.out, allow_paid=args.allow_paid)
            else:
                manifest, jobs = preflight_campaign(args.manifest)
                result = {"network_requests": 0, "models": [job[3]["model"] for job in jobs], "maximum_requests": manifest["maximum_requests"],
                          "api_key_available": bool(os.environ.get("AI_GATEWAY_API_KEY"))}
        else:
            require(not Path(args.out).exists(), "Output already exists")
            result = compare_mirror(args.primary_score, args.mirrored_score)
            write_json(args.out, result)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except (ValueError, KeyError, OSError) as exc:
        # Config may contain secrets accidentally: never echo invalid field values.
        parser.exit(2, f"Evaluation stopped: {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()

"""Append-only attempt journal; this module never opens an answer bank."""

import os
import platform
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .adapters import AdapterError, OPENAI_ENDPOINT, estimated_cost, make_adapter, validate_config
from .core import canonical, digest, parse_choice, request_for, require, validate_plan, write_json


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def harness_digest():
    root = Path(__file__).parent
    return digest({p.name: p.read_text(encoding="utf-8") for p in sorted(root.glob("*.py"))})


def append_record(path, row):
    with Path(path).open("a", encoding="utf-8") as f:
        f.write(canonical(row) + "\n")
        f.flush()
        os.fsync(f.fileno())


def validate_execution(plan, config):
    validate_plan(plan)
    validate_config(config)
    if config["provider"] != "mock":
        from .core import ACTIVE_PROTOCOL_VERSIONS, CURRENT_DATASET_VERSION
        require(plan["dataset_version"] == CURRENT_DATASET_VERSION and plan["protocol_version"] in ACTIVE_PROTOCOL_VERSIONS,
                "Historical datasets are frozen; paid execution requires current 0.5.0 impressions protocol")
        expected = "omit-nonreasoning" if config["provider"] == "vercel-decision" else "none"
        require(config["reasoning_effort"] == expected, "Thinking must be disabled for real runs; low/minimal reasoning is not allowed")
        from .core import DECISION_PROTOCOL_VERSION
        require((config["provider"] == "vercel-decision") == (plan["protocol_version"] == DECISION_PROTOCOL_VERSION), "Model API and protocol do not match")
        if config["provider"].startswith("vercel-"):
            from .gateway import validate_gateway_config
            validate_gateway_config(config)
    return plan, config


def run(plan, config, out, *, allow_paid=False, adapter=None):
    validate_execution(plan, config)
    if config["provider"] != "mock" and not allow_paid:
        raise ValueError("Real provider runs require explicit --allow-paid; no request sent")
    adapter = adapter or make_adapter(config)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / "plan.json", plan)
    write_json(out / "config.json", config)
    meta = {
        "schema_version": plan["schema_version"], "run_id": str(uuid.uuid4()),
        "participant_kind": "mock" if config["provider"] == "mock" else "model",
        "is_mock": config["provider"] == "mock", "provider": config["provider"],
        "model_requested": config["model"], "plan_sha256": plan["plan_sha256"],
        "config_sha256": digest(config), "harness_version": __version__, "harness_source_sha256": harness_digest(),
        "python_version": platform.python_version(),
        "endpoint": getattr(adapter, "endpoint", None if config["provider"] == "mock" else OPENAI_ENDPOINT),
        "timeout_semantics": "per socket I/O; not a total generation deadline",
        "started_at": now(), "finished_at": None, "status": "running",
        "planned_items": len(plan["items"]), "completed_items": 0,
    }
    write_json(out / "run.json", meta)
    attempts_path = out / "attempts.jsonl"
    attempts_path.touch()
    try:
        for item in plan["items"]:
            request = request_for(item)
            for number in range(1, config["diagnostic_retries"] + 2):
                started_at, started = now(), time.perf_counter()
                row = {
                    "schema_version": plan["schema_version"], "run_id": meta["run_id"],
                    "item_id": item["item_id"], "kind": item["kind"], "attempt": number,
                    "is_primary_attempt": number == 1, "request": request,
                    "request_sha256": item["request_sha256"], "started_at": started_at,
                    "raw_response": None, "response_text": None, "parsed_choice": None,
                    "request_id": None, "model_returned": None, "usage": None,
                    "estimated_cost_usd": None, "billed_cost_usd": None,
                    "gateway_reported_cost_usd": None, "gateway_metadata": None,
                    "error_code": None, "retryable": False,
                }
                try:
                    reply = adapter.generate(request)
                    choice = parse_choice(reply.text)
                    row.update(raw_response=reply.raw, response_text=reply.text, parsed_choice=choice,
                               request_id=reply.request_id, model_returned=reply.returned_model,
                               usage=reply.usage, estimated_cost_usd=estimated_cost(reply.usage, config.get("pricing")),
                               gateway_reported_cost_usd=reply.reported_cost_usd, gateway_metadata=reply.gateway_metadata,
                               status=reply.status if reply.status != "ok" else ("valid" if choice else "invalid"))
                    if row["status"] != "valid":
                        row["parsed_choice"] = None
                except AdapterError as exc:
                    row.update(status="timeout" if exc.code == "timeout" else "error", error_code=exc.code,
                               retryable=exc.retryable, raw_response=exc.raw, request_id=exc.request_id)
                except Exception as exc:
                    # Preserve item denominator even for adapter bugs. Never log exception text,
                    # which can include credentials, headers or raw request objects.
                    row.update(status="error", error_code="adapter_exception:" + type(exc).__name__)
                row["finished_at"] = now()
                row["latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
                append_record(attempts_path, row)
                if not row["retryable"]:
                    break
                if number <= config["diagnostic_retries"]:
                    time.sleep(min(2 ** (number - 1), 4))
            meta["completed_items"] += 1
            write_json(out / "run.json", meta)
        meta["status"] = "complete"
    except BaseException:
        meta["status"] = "interrupted"
        raise
    finally:
        meta["finished_at"] = now()
        meta["attempts_file_sha256"] = __import__("hashlib").sha256(attempts_path.read_bytes()).hexdigest()
        write_json(out / "run.json", meta)
    return meta

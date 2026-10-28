"""Private, offline JSONL and SQL exports for later trusted D1 ingestion."""

import json
from pathlib import Path

from .core import canonical, file_digest, load_json, require, write_json
from .scoring import read_run


def sql_value(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if type(v) in {float, int}:
        return str(v)
    require(isinstance(v, str) and "\0" not in v, "Unsupported SQL value")
    return "'" + v.replace("'", "''") + "'"


def insert(table, row):
    return f"INSERT INTO {table} ({', '.join(row)}) VALUES ({', '.join(sql_value(v) for v in row.values())});"


def export_records(run_dir, score_dir, out):
    plan, config, meta, attempts = read_run(run_dir)
    score_dir = Path(score_dir)
    summary = load_json(score_dir / "summary.json")
    require(summary["run"]["run_id"] == meta["run_id"] and summary["plan_sha256"] == plan["plan_sha256"] and summary["config_sha256"] == meta["config_sha256"], "Score belongs to a different run")
    require(summary["answers_file_sha256"] == file_digest(score_dir / "answers.jsonl"), "Scored answer file hash mismatch")
    answers = [json.loads(line) for line in (score_dir / "answers.jsonl").read_text().splitlines()]
    require(len(answers) == len(plan["items"]), "Scored answer count mismatch")
    envelope = {"summary": summary, "config": config, "protocol": plan["protocol"]}
    run_row = {k: summary[k] for k in ["schema_version", "benchmark_id", "benchmark_version", "dataset_version", "stimuli_sha256", "protocol_version", "protocol_sha256", "config_sha256", "plan_sha256", "assignment_seed", "variant", "split_status", "complete"]}
    run_row.update({k: meta[k] for k in ["run_id", "participant_kind", "is_mock", "provider", "model_requested", "started_at", "finished_at"]})
    run_row.update(planned_scored=summary["counts"]["planned_scored"], record_json=canonical(envelope))
    answer_rows = [{**{k: a[k] for k in ["run_id", "item_id", "ordinal", "kind", "A_post_id", "B_post_id", "status", "choice", "correct_choice", "correct", "primary_latency_ms", "attempt_count"]}, "record_json": canonical(a)} for a in answers]
    attempt_rows = []
    for rows in attempts.values():
        for a in rows:
            # Store hashes/metadata in D1, while exact bytes remain in the raw run
            # bundle and frozen fixture. Repeating base64 would inflate SQL rows.
            record = {**a, "request": {**a["request"]}}
            if "images" in record["request"]:
                record["request"]["images"] = [{k: v for k, v in image.items() if k != "data_base64"} for image in a["request"]["images"]]
                record["request"]["image_bytes_storage"] = "See original attempts.jsonl and matching frozen image sha256 assets; not stored in D1"
            attempt_rows.append({**{k: a[k] for k in ["run_id", "item_id", "attempt", "status", "request_sha256", "request_id", "model_returned", "latency_ms"]}, "record_json": canonical(record)})
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    statements = ["-- PRIVATE: contains labels and raw responses. Mock exports are fixtures only.", "PRAGMA foreign_keys = ON;", "BEGIN TRANSACTION;", insert("eval_runs", run_row)]
    statements += [insert("eval_answers", row) for row in answer_rows]
    statements += [insert("eval_attempts", row) for row in attempt_rows]
    statements.append("COMMIT;")
    (out / "import.private.sql").write_text("\n".join(statements) + "\n", encoding="utf-8")
    for name, records in [("runs", [run_row]), ("answers", answer_rows), ("attempts", attempt_rows)]:
        (out / f"{name}.private.jsonl").write_text("".join(canonical(r) + "\n" for r in records), encoding="utf-8")
    write_json(out / "export-manifest.json", {"schema_version": summary["schema_version"], "run_id": meta["run_id"],
        "participant_kind": meta["participant_kind"], "is_mock": meta["is_mock"],
        "counts": {"runs": 1, "answers": len(answer_rows), "attempts": len(attempt_rows)},
        "files_sha256": {p.name: file_digest(p) for p in sorted(out.iterdir()) if p.is_file()},
        "ingestion": "Apply evals/schema.sql first, then import.private.sql to a trusted SQLite/D1 store. Duplicate run IDs fail rather than overwrite."})
    return {"run_id": meta["run_id"], "is_mock": meta["is_mock"], "answers": len(answer_rows), "attempts": len(attempt_rows)}

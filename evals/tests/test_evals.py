"""Synthetic fixtures test mechanics only. No network calls or model results."""

import copy
import io
import json
import os
import sqlite3
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from evals.adapters import AdapterError, OpenAIResponsesAdapter, Reply, decode_openai, estimated_cost, openai_payload
from evals.core import digest, load_json, parse_choice, prepare, read_stimuli, request_for, validate_plan, write_json
from evals.export import export_records
from evals.runner import run
from evals.scoring import compare_mirror, score, wilson

ROOT = Path(__file__).resolve().parents[2]
MOCK = {"provider": "mock", "model": "mock-fixture-v1", "scenario": "choices", "reasoning_effort": "none", "max_output_tokens": 32, "timeout_seconds": 5, "diagnostic_retries": 0, "pricing": None}


class Scripted:
    def __init__(self, events):
        self.events = iter(events)
        self.requests = []

    def generate(self, request):
        self.requests.append(copy.deepcopy(request))
        event = next(self.events)
        if isinstance(event, BaseException):
            raise event
        return event


def reply(choice):
    return Reply(choice, {"fixture": True, "text": choice}, returned_model="synthetic-test-only")


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        client = {"version": "test-fixture-v1", "language": "en", "practice": self.pair("practice", "1", "2", "Practice red", "Practice blue"),
                  "pairs": [self.pair("q1", "3", "4", "Scored orange", "Scored green"), self.pair("q2", "5", "6", "Scored yellow", "Scored violet")]}
        self.client = self.root / "stimuli.json"
        write_json(self.client, client)
        bank = copy.deepcopy(client)
        bank.update(outcome="cumulative_snapshot_views", limitations=["Synthetic test fixture; never real data."])
        for index, pair in enumerate([bank["practice"]] + bank["pairs"]):
            for side in ["left", "right"]:
                pair[side].update(views=90001 if side == "left" else 50001, url=f"https://x.com/synthetic{index}/status/{pair[side]['id']}")
        self.bank = self.root / "bank.json"
        write_json(self.bank, bank)
        self.plan = prepare(self.client, "test-seed")

    @staticmethod
    def pair(item, left, right, lt, rt):
        return {"id": item, "left": {"id": left, "text": lt}, "right": {"id": right, "text": rt}}

    def winner(self, item):
        return "B" if item["flipped"] else "A"

    def execute(self, events, config=None, name="run"):
        adapter = Scripted(events)
        folder = self.root / name
        run(self.plan, config or MOCK, folder, adapter=adapter)
        return folder, adapter

    def test_real_bank_matches_stimuli_and_all_items_are_frozen(self):
        from evals.scoring import labels_for
        path = ROOT / "evals/fixtures/text-v0.1.1/stimuli.client.json"
        plan = prepare(path, "cohort-001")
        validate_plan(plan)
        labels, _ = labels_for(plan, path.with_name("question-bank.server.json"))
        self.assertEqual(len(labels), 16)
        self.assertEqual(sum(i["kind"] == "scored" for i in plan["items"]), 15)
        for item in plan["items"]:
            payload = request_for(item)
            self.assertEqual(set(json.loads(payload["user"])), {"A", "B"})
            for side in ["A", "B"]:
                self.assertNotIn(item[side]["id"], json.dumps(payload))
                self.assertEqual(json.loads(payload["user"])[side], item[side]["text"])

    def test_server_bank_and_extra_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            read_stimuli(self.bank)
        for field in ["views", "url", "author", "followers", "correct_choice"]:
            data = load_json(self.client)
            data["pairs"][0]["left"][field] = "SECRET_OUTCOME"
            write_json(self.client, data)
            with self.assertRaises(ValueError):
                read_stimuli(self.client)
            del data["pairs"][0]["left"][field]
            write_json(self.client, data)

    def test_author_visible_or_multimodal_dataset_requires_another_protocol(self):
        data = load_json(self.client)
        data["display"] = {"authors": True, "avatars": True}
        write_json(self.client, data)
        with self.assertRaisesRegex(ValueError, "client stimuli schema"):
            read_stimuli(self.client)
        del data["display"]
        data["pairs"][0]["left"]["media"] = [{"type": "image", "url": "https://example.com/image.jpg"}]
        write_json(self.client, data)
        with self.assertRaisesRegex(ValueError, "post fields"):
            read_stimuli(self.client)

    def test_handle_and_url_are_rejected_without_rewriting_text(self):
        for text in ["See https://x.com/name/status/3", "Hello @author"]:
            data = load_json(self.client)
            data["pairs"][0]["left"]["text"] = text
            write_json(self.client, data)
            with self.assertRaises(ValueError):
                prepare(self.client, "seed")

    def test_adapter_boundary_and_scoring_orientation(self):
        events = [reply(self.winner(i)) for i in self.plan["items"]]
        folder, adapter = self.execute(events)
        summary, answers = score(folder, self.bank, self.root / "score")
        self.assertEqual(summary["counts"]["correct"], 2)
        self.assertEqual(summary["counts"]["planned_scored"], 2)
        self.assertTrue(all(a["correct"] for a in answers))
        for request in adapter.requests:
            self.assertEqual(set(request), {"system", "user"})
            self.assertNotIn("90001", json.dumps(request))
            self.assertNotIn("50001", json.dumps(request))
            self.assertNotIn("synthetic0", json.dumps(request))
        self.assertEqual(summary["run"]["participant_kind"], "mock")

    def test_strict_parser(self):
        for text, expected in [("A", "A"), (" B\n", "B"), ("a", None), ("A.", None), ("A because", None), ('{"choice":"A"}', None), ("", None), (None, None), ("AB", None)]:
            self.assertEqual(parse_choice(text), expected)

    def test_invalid_and_incomplete_never_earn_credit(self):
        events = [reply("A"), reply("A because"), Reply(self.winner(self.plan["items"][2]), {"fixture": True}, status="provider_incomplete")]
        folder, _ = self.execute(events)
        summary, answers = score(folder, self.bank, self.root / "score")
        self.assertEqual(summary["primary_accuracy"], 0)
        self.assertEqual(summary["counts"]["by_status"], {"invalid": 1, "provider_incomplete": 1})
        self.assertTrue(all(a["choice"] is None for a in answers[1:]))

    def test_diagnostic_retry_does_not_rescue_first_attempt(self):
        config = {**MOCK, "diagnostic_retries": 1}
        events = [reply("A"), AdapterError("timeout", retryable=True), reply(self.winner(self.plan["items"][1])), reply(self.winner(self.plan["items"][2]))]
        with patch("evals.runner.time.sleep"):
            folder, _ = self.execute(events, config)
        summary, answers = score(folder, self.bank, self.root / "score")
        self.assertEqual(summary["primary_accuracy"], .5)
        self.assertEqual(answers[1]["status"], "timeout")
        self.assertEqual(answers[1]["attempt_count"], 2)
        self.assertFalse(answers[1]["correct"])
        self.assertEqual(summary["counts"]["all_attempts_including_practice_and_retries"], 4)

    def test_interruption_counts_every_unrun_item(self):
        folder = self.root / "interrupted"
        with self.assertRaises(KeyboardInterrupt):
            run(self.plan, MOCK, folder, adapter=Scripted([reply("A"), KeyboardInterrupt()]))
        summary, _ = score(folder, self.bank, self.root / "score")
        self.assertFalse(summary["complete"])
        self.assertEqual(summary["counts"]["by_status"], {"not_run": 2})
        self.assertEqual(summary["primary_accuracy"], 0)

    def test_errors_and_adapter_bugs_keep_denominator_and_hide_messages(self):
        folder, _ = self.execute([reply("A"), AdapterError("http_429", retryable=True), RuntimeError("DO_NOT_LOG_SECRET")])
        summary, _ = score(folder, self.bank, self.root / "score")
        self.assertEqual(summary["counts"]["by_status"], {"error": 2})
        self.assertNotIn("DO_NOT_LOG_SECRET", (folder / "attempts.jsonl").read_text())

    def test_mirror_is_deterministic_and_never_pools(self):
        self.assertEqual(self.plan, prepare(self.client, "test-seed"))
        mirrored = prepare(self.client, "test-seed", mirror=True)
        for a, b in zip(self.plan["items"], mirrored["items"]):
            self.assertEqual(a["A"], b["B"])
            self.assertEqual(a["B"], b["A"])
        pdir, _ = self.execute([reply(self.winner(i)) for i in self.plan["items"]])
        mdir = self.root / "mirror"
        run(mirrored, MOCK, mdir, adapter=Scripted([reply(self.winner(i)) for i in mirrored["items"]]))
        score(pdir, self.bank, self.root / "pscore")
        score(mdir, self.bank, self.root / "mscore")
        comparison = compare_mirror(self.root / "pscore", self.root / "mscore")
        self.assertEqual(comparison["planned_pairs"], 2)
        self.assertEqual(comparison["same_post_choices"], 2)

    def test_mutated_plan_or_journal_or_bank_is_rejected(self):
        bad = copy.deepcopy(self.plan)
        bad["items"][0]["A"]["text"] = "Changed"
        with self.assertRaises(ValueError):
            validate_plan(bad)
        folder, _ = self.execute([reply("A")] * 3)
        bank = load_json(self.bank)
        bank["pairs"][0]["left"]["text"] = "Different source text"
        write_json(self.bank, bank)
        with self.assertRaisesRegex(ValueError, "text differs"):
            score(folder, self.bank, self.root / "score")
        with (folder / "attempts.jsonl").open("a") as f:
            f.write('{}\n')
        with self.assertRaisesRegex(ValueError, "journal hash"):
            score(folder, self.bank, self.root / "score2")

    def test_paid_gate_and_missing_key_make_no_requests(self):
        config = {**MOCK, "provider": "openai-responses", "model": "approved-test-id"}
        del config["scenario"]
        adapter = Scripted([])
        with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
            run(self.plan, config, self.root / "paid", adapter=adapter)
        self.assertEqual(adapter.requests, [])
        self.assertFalse((self.root / "paid").exists())
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
                run(self.plan, config, self.root / "paid", allow_paid=True)

    def test_openai_payload_has_no_metadata_tools_or_history(self):
        payload = openai_payload(request_for(self.plan["items"][1]), MOCK)
        self.assertEqual(payload["tools"], [])
        self.assertEqual(payload["tool_choice"], "none")
        self.assertFalse(payload["store"])
        self.assertEqual(len(payload["input"]), 1)
        self.assertNotIn("previous_response_id", payload)
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertNotIn("reasoning", openai_payload(request_for(self.plan["items"][1]), {**MOCK, "reasoning_effort": "omit-nonreasoning"}))

    def test_openai_response_states_and_usage(self):
        raw = {"status": "completed", "model": "snapshot-test", "output": [{"type": "message", "content": [{"type": "output_text", "text": "A"}]}],
               "usage": {"input_tokens": 100, "output_tokens": 22, "total_tokens": 122, "input_tokens_details": {"cached_tokens": 20}, "output_tokens_details": {"reasoning_tokens": 21}}}
        reply_ = decode_openai(raw, "req-test")
        self.assertEqual((reply_.text, reply_.returned_model, reply_.request_id), ("A", "snapshot-test", "req-test"))
        self.assertEqual(decode_openai({**raw, "status": "incomplete"}).status, "provider_incomplete")
        self.assertEqual(decode_openai({**raw, "output": [{"type": "message", "content": [{"type": "refusal"}]}]}).status, "refused")
        self.assertEqual(decode_openai({**raw, "output": [{"type": "web_search_call"}]}).status, "unexpected_output")
        prices = {"input_usd_per_million": 1, "cached_input_usd_per_million": .5, "output_usd_per_million": 2}
        self.assertAlmostEqual(estimated_cost(raw["usage"], prices), .000134)
        self.assertIsNone(estimated_cost(None, prices))

    def test_http_error_is_recorded_and_credentials_redacted(self):
        config = {**MOCK, "provider": "openai-responses", "model": "snapshot-test"}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "secret-test-key"}):
            adapter = OpenAIResponsesAdapter(config)
        error = urllib.error.HTTPError("https://api.openai.com/v1/responses", 429, "rate limit", {"x-request-id": "req-test"}, io.BytesIO(b'{"error":"secret-test-key"}'))
        with patch.object(adapter.opener, "open", side_effect=error):
            with self.assertRaises(AdapterError) as captured:
                adapter.generate(request_for(self.plan["items"][0]))
        self.assertEqual(captured.exception.code, "http_429")
        self.assertTrue(captured.exception.retryable)
        self.assertNotIn("secret-test-key", json.dumps(captured.exception.raw))

    def test_private_sql_roundtrip_keeps_mock_out_of_public_view(self):
        folder, _ = self.execute([reply("A"), reply(self.winner(self.plan["items"][1])), reply("invalid")])
        summary, _ = score(folder, self.bank, self.root / "score")
        export_records(folder, self.root / "score", self.root / "export")
        connection = sqlite3.connect(":memory:")
        self.addCleanup(connection.close)
        connection.executescript((ROOT / "evals/schema.sql").read_text())
        sql = (self.root / "export/import.private.sql").read_text()
        connection.executescript(sql)
        self.assertEqual(connection.execute("SELECT count(*) FROM eval_answers").fetchone()[0], 3)
        self.assertEqual(connection.execute("SELECT count(*) FROM eval_attempts").fetchone()[0], 3)
        self.assertEqual(connection.execute("SELECT count(*) FROM eval_public_run_aggregates").fetchone()[0], 0)
        # A synthetic DB-only participant exercises aggregate math, never exported.
        connection.execute("UPDATE eval_runs SET participant_kind='model',is_mock=0")
        row = connection.execute("SELECT denominator,correct,failed_or_invalid FROM eval_public_run_aggregates").fetchone()
        self.assertEqual(row, (2, 1, 1))
        self.assertEqual(summary["primary_accuracy"], .5)
        with self.assertRaises(sqlite3.IntegrityError):
            connection.executescript(sql)

    def test_known_wilson_reference_and_limits(self):
        lo, hi = wilson(0, 15)
        self.assertAlmostEqual(lo, 0)
        self.assertAlmostEqual(hi, .203883301, places=7)
        lo, hi = wilson(15, 15)
        self.assertAlmostEqual(lo, .796116699, places=7)
        self.assertAlmostEqual(hi, 1)


if __name__ == "__main__":
    unittest.main()

"""Synthetic publication-guard tests; temporary fixtures are never real results."""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.adapters import AdapterError, Reply
from evals.core import file_digest, load_json, prepare, request_for
from evals.credentials import load_gateway_env
from evals.gateway import GatewayResponsesAdapter, add_gateway_metadata
from evals.image_submission import submitted_images
from evals.leaderboard import (model_record, replay_provenance, revalidate_native_run,
                              validate_live_provenance, validate_revalidation)
from evals.runner import run
from evals.scoring import read_run, score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evals/fixtures/cross-author-v0.6.0"


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=DATA / "avatars/avatar-manifest.private.json")
        cls.grok = load_json(ROOT / "evals/configs/gateway/grok-4.20-no-thinking.json")
        cls.jev = load_json(ROOT / "evals/configs/gateway/jev-1.14.json")
        cls.mock = load_json(ROOT / "evals/configs/mock.json")

    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix="synthetic-publication-unit-")
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def alias_raw(self):
        return {"fixture": True, "model": "xai/grok-4.20-non-reasoning", "status": "completed",
                "output": [{"type": "message", "content": [{"type": "output_text", "text": "A"}]}],
                "usage": {"input_tokens": 100, "output_tokens": 1, "total_tokens": 101, "output_tokens_details": {"reasoning_tokens": 0}},
                "provider_metadata": {"gateway": {"routing": {"originalModelId": self.grok["model"],
                    "canonicalSlug": "xai/grok-4.20-non-reasoning", "finalProvider": "xai", "resolvedProvider": "xai"}}}}

    def test_only_verified_creator_prefix_alias_is_accepted(self):
        raw = self.alias_raw()
        self.assertEqual(add_gateway_metadata(Reply("A", raw), raw, self.grok).status, "ok")
        for field, value in [("canonicalSlug", "xai/grok-4.20-reasoning"), ("originalModelId", "spacexai/grok-4.7"), ("finalProvider", "vertex")]:
            bad = copy.deepcopy(raw)
            bad["provider_metadata"]["gateway"]["routing"][field] = value
            self.assertEqual(add_gateway_metadata(Reply("A", bad), bad, self.grok).status, "unexpected_output")

    def test_mock_and_injected_adapters_cannot_be_published(self):
        meta = run(self.plan, self.mock, self.root / "mock")
        self.assertEqual(meta["execution_mode"], "mock")
        with self.assertRaisesRegex(ValueError, "real Gateway"):
            validate_live_provenance(self.mock, meta)
        fake = {**meta, "participant_kind": "model", "is_mock": False,
                "execution_mode": "injected_adapter", "adapter_injected": True}
        with self.assertRaisesRegex(ValueError, "native HTTPS"):
            validate_live_provenance(self.grok, fake)

    def test_jev_avatar_policy_records_exact_original_and_submitted_hashes(self):
        request = request_for(self.plan["items"][0])
        images, evidence = submitted_images(request, self.jev)
        direct, original = submitted_images(request, self.grok)
        self.assertEqual(direct, request["images"])
        for before, after, record, unchanged in zip(request["images"], images, evidence, original):
            self.assertEqual((before["width"], before["height"]), (48, 48))
            self.assertEqual((after["width"], after["height"]), (288, 288))
            self.assertEqual(record["source_sha256"], before["sha256"])
            self.assertEqual(record["submitted_sha256"], after["sha256"])
            self.assertNotEqual(before["sha256"], after["sha256"])
            self.assertEqual(unchanged["source_sha256"], unchanged["submitted_sha256"])

    def test_key_file_loads_only_named_key_without_interpolation(self):
        path = self.root / ".env.local"
        path.write_text("UNRELATED=do-not-load\nAI_GATEWAY_API_KEY='synthetic-unit-key'\n")
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(load_gateway_env(path))
            self.assertEqual(os.environ["AI_GATEWAY_API_KEY"], "synthetic-unit-key")
            self.assertNotIn("UNRELATED", os.environ)
        for content in ["AI_GATEWAY_API_KEY=\n", "AI_GATEWAY_API_KEY=a\nAI_GATEWAY_API_KEY=b\n"]:
            path.write_text(content)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaises(ValueError):
                    load_gateway_env(path)

    def test_fatal_http_stops_after_one_request_and_keeps_unrun_denominator(self):
        class Fatal:
            calls = 0
            def generate(self, request):
                self.calls += 1
                raise AdapterError("http_401", raw={"fixture": True, "http_status": 401})
        adapter = Fatal()
        with self.assertRaisesRegex(ValueError, "Fatal provider HTTP"):
            run(self.plan, self.mock, self.root / "fatal", adapter=adapter, stop_on_fatal_http=True)
        self.assertEqual(adapter.calls, 1)
        self.assertEqual(load_json(self.root / "fatal/run.json")["status"], "interrupted")
        summary, _ = score(self.root / "fatal", DATA / "question-bank.server.json", self.root / "score")
        self.assertEqual(summary["counts"]["planned_scored"], 15)
        self.assertEqual(summary["counts"]["by_status"], {"not_run": 15})
        self.assertFalse(summary["complete"])

    def test_offline_alias_revalidation_preserves_source_and_never_publishes_fixture(self):
        def synthetic_post(instance, payload):
            raw = self.alias_raw()
            return Reply("A", raw, status="unexpected_output", request_id="synthetic-only",
                         returned_model=raw["model"], usage=raw["usage"], gateway_metadata=raw["provider_metadata"]["gateway"])
        with patch.dict(os.environ, {"AI_GATEWAY_API_KEY": "synthetic-unit-key"}), patch.object(GatewayResponsesAdapter, "post", synthetic_post):
            run(self.plan, self.grok, self.root / "original", allow_paid=True)
        prior_hash = file_digest(self.root / "original/attempts.jsonl")
        meta = revalidate_native_run(self.root / "original", self.root / "derived")
        self.assertEqual(meta["revalidation"]["additional_model_calls"], 0)
        self.assertEqual(meta["revalidation"]["changed_validation_records"], 17)
        self.assertEqual(file_digest(self.root / "original/attempts.jsonl"), prior_hash)
        _, config, meta, attempts = read_run(self.root / "derived")
        validate_revalidation(self.root / "derived", meta, attempts)
        self.assertTrue(all(rows[0]["status"] == "valid" for rows in attempts.values()))
        with self.assertRaisesRegex(ValueError, "Synthetic provider fixtures"):
            replay_provenance(config, attempts)

    def test_public_record_contract_contains_aggregate_fields_and_preprocessing_note(self):
        summary = {"complete": True, "is_mock": False, "counts": {"planned_scored": 15, "practice": 2, "correct": 9,
                   "valid": 14, "by_status": {"valid": 14, "invalid": 1}}, "primary_accuracy": .6, "answer_bank_sha256": "synthetic-bank-hash"}
        meta = {"started_at": "2026-10-28T00:00:00Z", "finished_at": "2026-10-28T00:01:00Z", "run_id": "synthetic-unit-only",
                "adapter_class": "synthetic-unit", "endpoint": "synthetic-unit", "config_sha256": "synthetic", "attempts_file_sha256": "synthetic", "harness_source_sha256": "synthetic"}
        record = model_record(self.plan, self.jev, meta, summary, {})
        self.assertEqual((record["correct"], record["total"], record["unanswered"]), (9, 15, 1))
        self.assertEqual(record["condition"], "independent-no-thinking")
        self.assertIn("no new detail", record["inputNotes"])
        self.assertTrue({"datasetVersion", "humanProtocol", "modelId", "name", "protocol", "correct", "total", "unanswered", "evaluatedAt", "runId", "bankSha256", "real", "condition"} <= set(record))
        self.assertFalse({"answers", "raw_response", "request", "data_base64", "correct_choice"} & set(record))

    def test_actual_06_bank_is_frozen_and_contains_two_ai_pairs(self):
        audit = load_json(DATA / "audit.json")
        self.assertEqual(file_digest(DATA / "question-bank.server.json"), "1cb873b4d6da67cb22e0e65582d70c2418a13050cd691b9c05a8df17fe6a744b")
        self.assertEqual(audit["summary"]["aiRelatedScoredPairs"], 2)
        self.assertEqual(audit["summary"]["selectedUniquePosts"], 34)
        self.assertEqual(audit["releaseChangeVerification"]["retainedPostRecords"], 30)
        self.assertEqual(audit["releaseChangeVerification"]["newPostRecords"], 4)


if __name__ == "__main__":
    unittest.main()

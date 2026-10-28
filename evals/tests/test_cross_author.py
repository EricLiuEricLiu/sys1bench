"""Synthetic mechanics checks; actual frozen 0.4 data is tested separately."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from evals.core import (DECISION_PROTOCOL_VERSION, PROTOCOL_VERSION, V03_PROTOCOL_VERSION,
                        load_json, prepare, request_for, write_json)
from evals.runner import run, validate_execution
from evals.scoring import labels_for, score
from evals.tests.fixture_helpers import cross_author_fixture

ROOT = Path(__file__).resolve().parents[2]
MOCK = load_json(ROOT / "evals/configs/mock.json")


class CrossAuthorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stimuli, self.bank = cross_author_fixture(self.root / "synthetic-only")
        self.plan = prepare(self.stimuli, "cross-author-synthetic")

    def test_prompt_timing_versions_and_author_context_match_new_task(self):
        p = self.plan
        self.assertEqual(p["schema_version"], "2.1.0")
        self.assertEqual(p["benchmark_version"], "0.3.1-pilot")
        self.assertEqual(p["protocol_version"], PROTOCOL_VERSION)
        self.assertEqual(p["protocol"]["human_timing"], {"exposure_ms": 15000, "decision_ms": 5000})
        self.assertIn("different authors", p["protocol"]["system"])
        self.assertNotIn("same author", p["protocol"]["system"])
        for item in p["items"]:
            request = request_for(item)
            visible = json.loads(request["user"])
            self.assertNotEqual(visible["A"]["author"]["handle"], visible["B"]["author"]["handle"])
            self.assertNotIn("150000", request["user"])
            self.assertNotIn("300000", request["user"])
            self.assertNotIn("100000", request["system"])

    def test_same_handles_or_same_source_author_ids_are_rejected(self):
        original = load_json(self.stimuli)
        for field in ["handle", "id"]:
            bad = copy.deepcopy(original)
            pair = bad["pairs"][0]
            pair["right"]["author"][field] = pair["left"]["author"][field]
            write_json(self.stimuli, bad)
            with self.assertRaises(ValueError):
                prepare(self.stimuli, "synthetic")

    def test_incorrect_human_timing_or_historical_protocol_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Protocol does not match"):
            prepare(self.stimuli, "synthetic", protocol_version=V03_PROTOCOL_VERSION)
        data = load_json(self.stimuli)
        data["timing"] = {"exposureMs": 3000, "decisionMs": 2000}
        write_json(self.stimuli, data)
        with self.assertRaisesRegex(ValueError, "Human timing differs"):
            prepare(self.stimuli, "synthetic")

    def test_server_join_enforces_100k_floor_for_every_post(self):
        labels_for(self.plan, self.bank)
        bank = load_json(self.bank)
        bank["practice"][0]["left"]["views"] = 99999
        write_json(self.bank, bank)
        with self.assertRaisesRegex(ValueError, "100000 captured views"):
            labels_for(self.plan, self.bank)

    def test_both_author_clusters_are_orientation_invariant_and_iid_caveat_is_retained(self):
        mirror = prepare(self.stimuli, "cross-author-synthetic", mirror=True)
        primary_labels, _ = labels_for(self.plan, self.bank)
        mirror_labels, _ = labels_for(mirror, self.bank)
        for item_id, label in primary_labels.items():
            self.assertIsNone(label["author_cluster_id"])
            self.assertEqual(len(label["author_cluster_ids"]), 2)
            self.assertEqual(label["author_cluster_ids"], mirror_labels[item_id]["author_cluster_ids"])
        run(self.plan, MOCK, self.root / "mock-run")
        summary, _ = score(self.root / "mock-run", self.bank, self.root / "mock-score")
        self.assertIsNone(summary["cluster_bootstrap_sensitivity"]["interval_95"])
        self.assertIn("crossed-author", summary["cluster_bootstrap_sensitivity"]["method"])
        self.assertIn("not a population", summary["wilson_caveat"])

    def test_all_four_models_validate_on_current_protocol_without_any_calls(self):
        for path in (ROOT / "evals/configs/gateway").glob("*.json"):
            config = load_json(path)
            plan = self.plan
            if config["provider"] == "vercel-decision":
                plan = prepare(self.stimuli, "cross-author-synthetic", protocol_version=DECISION_PROTOCOL_VERSION)
            validate_execution(plan, config)
            self.assertEqual(plan["stimuli_sha256"], self.plan["stimuli_sha256"])

    def test_current_protocol_still_rejects_low_and_minimal_thinking_before_requests(self):
        config = load_json(ROOT / "evals/configs/gateway/opus-5-no-thinking.json")
        for effort in ["low", "minimal"]:
            with self.assertRaisesRegex(ValueError, "Thinking must be disabled"):
                run(self.plan, {**config, "reasoning_effort": effort}, self.root / effort, allow_paid=True)
            self.assertFalse((self.root / effort).exists())

    def test_historical_plan_and_prompt_remain_exactly_reproducible_but_cannot_run_paid(self):
        old = ROOT / "evals/fixtures/author-image-v0.3.0"
        historical = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json")
        self.assertEqual(historical["protocol_version"], V03_PROTOCOL_VERSION)
        self.assertEqual(historical["stimuli_sha256"], "bcd87621491f530c7861d067dd3302269ab3a7e276268183c7eaa979795830b3")
        self.assertEqual(historical["protocol"]["human_timing"], {"exposure_ms": 3000, "decision_ms": 2000})
        self.assertIn("same author", historical["protocol"]["system"])
        config = load_json(ROOT / "evals/configs/gateway/opus-5-no-thinking.json")
        with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
            run(historical, config, self.root / "paid-must-not-exist", allow_paid=True)
        self.assertFalse((self.root / "paid-must-not-exist").exists())


if __name__ == "__main__":
    unittest.main()

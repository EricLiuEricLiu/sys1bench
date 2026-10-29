"""Synthetic checks for the visible-choice, post-answer feedback protocol."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from evals.core import (DECISION_PROTOCOL_VERSION, HUMAN_PROTOCOL_VERSION, PROTOCOL_VERSION,
                        V041_DECISION_PROTOCOL_VERSION, V041_PROTOCOL_VERSION,
                        file_digest, load_json, prepare, request_for, write_json)
from evals.gateway import decision_payload
from evals.runner import run, validate_execution
from evals.scoring import labels_for, score
from evals.tests.fixture_helpers import cross_author_fixture

ROOT = Path(__file__).resolve().parents[2]


class ImpressionsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.stimuli, self.bank = cross_author_fixture(self.root / "synthetic-only")
        self.plan = prepare(self.stimuli, "impressions-synthetic")

    def test_one_visible_window_and_feedback_every_round_are_explicit(self):
        p = self.plan["protocol"]
        self.assertEqual(p["human_protocol_version"], HUMAN_PROTOCOL_VERSION)
        self.assertEqual(p["human_timing"], {"round_ms": 15000, "reveal_ms": 2500})
        self.assertNotIn("exposure_ms", p["human_timing"])
        self.assertNotIn("decision_ms", p["human_timing"])
        self.assertIn("remain visible", p["human_presentation"])
        self.assertEqual(p["human_feedback"]["rounds"], "practice_and_scored")
        self.assertEqual(p["human_feedback"]["metrics"], ["replies", "reposts", "likes", "impressions"])
        self.assertEqual(p["human_feedback"]["advance_after_ms"], 2500)
        self.assertIn("different feedback conditions", p["comparability"])
        self.assertIn("no feedback", p["practice"])

    def test_both_api_surfaces_target_impressions_and_receive_no_engagement(self):
        config = load_json(ROOT / "evals/configs/gateway/jev-1.14.json")
        for protocol in [PROTOCOL_VERSION, DECISION_PROTOCOL_VERSION]:
            plan = prepare(self.stimuli, "impressions-synthetic", protocol_version=protocol)
            for item in plan["items"]:
                request = request_for(item)
                self.assertIn("cumulative impressions", request["system"])
                self.assertNotIn("cumulative views", request["system"])
                visible = json.loads(request["user"])
                for side in ["A", "B"]:
                    self.assertEqual(set(visible[side]), {"text", "author", "avatar_ref", "image_refs"})
                for key in ["engagement", "replies", "reposts", "likes", "impressions", "views", "150000", "300000"]:
                    self.assertNotIn(key, request["user"])
                if protocol == DECISION_PROTOCOL_VERSION:
                    payload = decision_payload(request, config)
                    for choice in payload["questions"][0]["choices"]:
                        self.assertIn("cumulative impressions", choice["description"])
                        self.assertNotIn("views", choice["description"])

    def test_scoring_uses_impressions_when_likes_and_other_metrics_disagree(self):
        bank = load_json(self.bank)
        for pair in bank["practice"] + bank["pairs"]:
            pair["left"]["engagement"].update(replies=1000, reposts=1000, likes=1000)
            pair["right"]["engagement"].update(replies=0, reposts=0, likes=0)
        write_json(self.bank, bank)
        labels, _ = labels_for(self.plan, self.bank)
        for item in self.plan["items"]:
            choice = labels[item["item_id"]]["correct_choice"]
            self.assertTrue(item[choice]["id"].endswith("-b"))

    def test_missing_or_invalid_metrics_and_inconsistent_alias_are_rejected(self):
        original = load_json(self.bank)
        for metric in ["replies", "reposts", "likes", "impressions"]:
            for bad_value in [None, -1, True, 1.5]:
                bad = copy.deepcopy(original)
                bad["pairs"][0]["left"]["engagement"][metric] = bad_value
                write_json(self.bank, bad)
                with self.assertRaises(ValueError):
                    labels_for(self.plan, self.bank)
            bad = copy.deepcopy(original)
            del bad["pairs"][0]["left"]["engagement"][metric]
            write_json(self.bank, bad)
            with self.assertRaisesRegex(ValueError, "Four captured engagement"):
                labels_for(self.plan, self.bank)
        bad = copy.deepcopy(original)
        bad["pairs"][0]["left"]["views"] += 1
        write_json(self.bank, bad)
        with self.assertRaisesRegex(ValueError, "alias differs"):
            labels_for(self.plan, self.bank)

    def test_engagement_injected_into_client_cannot_reach_prepare(self):
        original = load_json(self.stimuli)
        for field in ["engagement", "views", "impressions", "replies", "reposts", "likes"]:
            bad = copy.deepcopy(original)
            bad["pairs"][0]["left"][field] = 123456
            write_json(self.stimuli, bad)
            with self.assertRaisesRegex(ValueError, "Unexpected post fields"):
                prepare(self.stimuli, "injected-synthetic")

    def test_wrong_human_protocol_or_feedback_cannot_be_labeled_as_current(self):
        for path, validate in [(self.stimuli, lambda: prepare(self.stimuli, "wrong-condition")),
                               (self.bank, lambda: labels_for(self.plan, self.bank))]:
            original = load_json(path)
            bad = copy.deepcopy(original)
            bad["humanProtocolId"] = "human-15s5s-cross-author-highreach-education2-v3"
            write_json(path, bad)
            with self.assertRaisesRegex(ValueError, "Human protocol ID differs"):
                validate()
            for value in [False, 1]:
                bad = copy.deepcopy(original)
                bad["feedback"]["afterEveryRound"] = value
                write_json(path, bad)
                with self.assertRaisesRegex(ValueError, "Human feedback differs"):
                    validate()
            write_json(path, original)

    def test_feedback_condition_is_recorded_without_giving_models_feedback(self):
        run(self.plan, load_json(ROOT / "evals/configs/mock.json"), self.root / "run")
        summary, _ = score(self.root / "run", self.bank, self.root / "score")
        self.assertEqual(summary["outcome_metric"], "cumulative impressions")
        self.assertEqual(summary["human_protocol_version"], HUMAN_PROTOCOL_VERSION)
        self.assertEqual(summary["human_feedback"]["rounds"], "practice_and_scored")
        self.assertIn("independent label-free", summary["model_feedback"])
        attempts = [json.loads(line) for line in (self.root / "run/attempts.jsonl").read_text().splitlines()]
        self.assertEqual(len(attempts), 3)
        for attempt in attempts:
            self.assertEqual(attempt["request"], request_for(next(i for i in self.plan["items"] if i["item_id"] == attempt["item_id"])))
            self.assertNotIn("engagement", attempt["request"]["user"])

    def test_campaign_preflight_rejects_missing_reveal_metric_before_any_requests(self):
        from evals.campaign import preflight_campaign
        plan_path, config_path = self.root / "plan.json", self.root / "config.json"
        write_json(plan_path, self.plan)
        config = load_json(ROOT / "evals/configs/gateway/opus-5-no-thinking.json")
        write_json(config_path, config)
        bank = load_json(self.bank)
        del bank["pairs"][0]["left"]["engagement"]["reposts"]
        write_json(self.bank, bank)
        entry = {"model": config["model"], "planned_items": 3}
        for name, path in [("plan", plan_path), ("config", config_path), ("bank", self.bank)]:
            entry[name] = str(path)
            entry[name + "_file_sha256"] = file_digest(path)
        write_json(self.root / "campaign.json", {"schema_version": "gateway-campaign-v1", "lineup_approved": True,
            "primary_runs_per_model": 1, "automatic_mirrors": 0, "maximum_requests": 3, "entries": [entry]})
        with self.assertRaisesRegex(ValueError, "Four captured engagement"):
            preflight_campaign(self.root / "campaign.json")

    def test_041_hashes_and_payloads_replay_but_cannot_launch_paid(self):
        old = ROOT / "evals/fixtures/cross-author-v0.4.1"
        expected = {
            V041_PROTOCOL_VERSION: "ce275012c9350506e6a64662bac50990521069f34671cf95854fea629ac4db1a",
            V041_DECISION_PROTOCOL_VERSION: "fcdaf5a478fad8615b452abd088411ddd295c4cd6ef72f951556ca64f5c21401",
        }
        for protocol, protocol_hash in expected.items():
            plan = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json", protocol_version=protocol)
            self.assertEqual(plan["protocol_sha256"], protocol_hash)
            self.assertEqual(plan["protocol"]["human_timing"], {"exposure_ms": 15000, "decision_ms": 5000})
            self.assertIn("cumulative views", request_for(plan["items"][0])["system"])
            config = load_json(ROOT / "evals/configs/gateway" / ("jev-1.14.json" if protocol == V041_DECISION_PROTOCOL_VERSION else "opus-5-no-thinking.json"))
            with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
                validate_execution(plan, config)
            if protocol == V041_DECISION_PROTOCOL_VERSION:
                payload = decision_payload(request_for(plan["items"][0]), config)
                self.assertTrue(all("cumulative views" in c["description"] for c in payload["questions"][0]["choices"]))


if __name__ == "__main__":
    unittest.main()

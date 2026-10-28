"""Timing-patch checks on the frozen source; synthetic responses remain mocks."""

import base64
import json
import tempfile
import unittest
from pathlib import Path

from evals.core import (DECISION_PROTOCOL_VERSION, HUMAN_PROTOCOL_VERSION, PROTOCOL_VERSION,
                        V04_DECISION_PROTOCOL_VERSION, V04_PROTOCOL_VERSION,
                        file_digest, load_json, prepare, request_for, write_json)
from evals.export import export_records
from evals.runner import run
from evals.scoring import labels_for, score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evals/fixtures/cross-author-v0.4.1"


class CurrentBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=DATA / "avatars/avatar-manifest.private.json")

    def test_actual_audit_hashes_reach_and_all_authors_are_distinct(self):
        client, bank, audit = (load_json(DATA / n) for n in ["stimuli.client.json", "question-bank.server.json", "audit.json"])
        self.assertEqual(audit["questionBankSha256"], file_digest(DATA / "question-bank.server.json"))
        self.assertEqual(audit["stimuliSha256"], file_digest(DATA / "stimuli.client.json"))
        self.assertEqual(audit["status"], "passed_timing_patch_source_equivalence_checks")
        self.assertEqual(client["timing"], {"exposureMs": 15000, "decisionMs": 5000})
        pairs = bank["practice"] + bank["pairs"]
        posts = [pair[s] for pair in pairs for s in ["left", "right"]]
        self.assertEqual((len(bank["practice"]), len(bank["pairs"]), len(posts)), (2, 15, 34))
        self.assertEqual(len({p["id"] for p in posts}), 34)
        self.assertEqual(len({p["author"]["id"] for p in posts}), 34)
        self.assertTrue(all(p["views"] >= 100000 for p in posts))
        self.assertEqual(sum(p["views"] >= 1000000 for p in posts), audit["summary"]["millionPlusPosts"])
        for pair in pairs:
            self.assertNotEqual(pair["left"]["author"]["id"], pair["right"]["author"]["id"])
        self.assertEqual(len(labels_for(self.plan, DATA / "question-bank.server.json")[0]), 17)

    def test_actual_captured_content_bytes_and_visible_authors_match_source(self):
        client = load_json(DATA / "stimuli.client.json")
        source = {post["id"]: post for pair in client["practice"] + client["pairs"] for post in [pair["left"], pair["right"]]}
        avatars = {e["url"]: e for e in load_json(DATA / "avatars/avatar-manifest.private.json")["entries"]}
        self.assertEqual(len(avatars), 34)
        for item in self.plan["items"]:
            request = request_for(item)
            visible = json.loads(request["user"])
            self.assertNotIn("same author", request["system"])
            for side in ["A", "B"]:
                original = source[item[side]["id"]]
                self.assertEqual(visible[side]["text"], original["displayText"])
                self.assertEqual(visible[side]["author"], {k: original["author"][k] for k in ["name", "handle"]})
                captured = avatars[original["author"]["avatarUrl"]]
                self.assertEqual(base64.b64decode(item[side]["author"]["avatar"]["data_base64"]), (DATA / "avatars" / captured["assetFile"]).read_bytes())
                self.assertNotIn(original["id"], request["user"])
                self.assertNotIn(original["author"]["avatarUrl"], request["user"])
                for image, media in zip(item[side]["images"], original["media"]):
                    self.assertEqual(base64.b64decode(image["data_base64"]), (DATA / media["assetFile"]).read_bytes())
                    self.assertNotIn(media["url"], request["user"])

    def test_both_protocols_and_mirrored_side_sets_have_same_stimulus_hash(self):
        common = {"avatar_manifest": DATA / "avatars/avatar-manifest.private.json"}
        typed = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", protocol_version=DECISION_PROTOCOL_VERSION, **common)
        mirrored = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", mirror=True, **common)
        self.assertEqual(typed["stimuli_sha256"], self.plan["stimuli_sha256"])
        self.assertEqual(mirrored["stimuli_sha256"], self.plan["stimuli_sha256"])
        self.assertNotEqual(typed["protocol_sha256"], self.plan["protocol_sha256"])
        for a, b in zip(self.plan["items"], mirrored["items"]):
            self.assertEqual(a["A"], b["B"])
            self.assertEqual(a["B"], b["A"])

    def test_current_mock_scoring_and_export_keep_15_item_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(self.plan, load_json(ROOT / "evals/configs/mock.json"), root / "run")
            summary, answers = score(root / "run", DATA / "question-bank.server.json", root / "score")
            self.assertTrue(summary["is_mock"])
            self.assertEqual(summary["counts"]["planned_scored"], 15)
            self.assertEqual(summary["counts"]["practice"], 2)
            self.assertEqual(len(answers), 17)
            self.assertTrue(all(len(a["author_cluster_ids"]) == 2 and a["author_cluster_id"] is None for a in answers))
            self.assertIsNone(summary["cluster_bootstrap_sensitivity"]["interval_95"])
            export_records(root / "run", root / "score", root / "export")
            self.assertNotIn("data_base64", (root / "export/import.private.sql").read_text())

    def test_timing_patch_preserves_posts_outcomes_and_every_model_request(self):
        old = ROOT / "evals/fixtures/cross-author-v0.4.0"
        previous = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json")
        for name in ["stimuli.client.json", "question-bank.server.json"]:
            before, after = load_json(old / name), load_json(DATA / name)
            self.assertEqual(before["practice"], after["practice"])
            self.assertEqual(before["pairs"], after["pairs"])
        self.assertEqual(self.plan["protocol"]["human_protocol_version"], HUMAN_PROTOCOL_VERSION)
        self.assertEqual(self.plan["protocol"]["human_timing"], {"exposure_ms": 15000, "decision_ms": 5000})
        self.assertEqual(self.plan["protocol_version"], PROTOCOL_VERSION)
        self.assertNotEqual(self.plan["plan_sha256"], previous["plan_sha256"])
        self.assertNotEqual(self.plan["protocol_sha256"], previous["protocol_sha256"])
        for prior_protocol, protocol in [(V04_PROTOCOL_VERSION, PROTOCOL_VERSION), (V04_DECISION_PROTOCOL_VERSION, DECISION_PROTOCOL_VERSION)]:
            prior_plan = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json", protocol_version=prior_protocol)
            current_plan = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=DATA / "avatars/avatar-manifest.private.json", protocol_version=protocol)
            for before, after in zip(prior_plan["items"], current_plan["items"]):
                self.assertEqual(request_for(before), request_for(after))
                self.assertEqual(before["request_sha256"], after["request_sha256"])

    def test_frozen_040_protocols_replay_with_original_hashes_but_paid_calls_are_blocked(self):
        from evals.runner import validate_execution
        old = ROOT / "evals/fixtures/cross-author-v0.4.0"
        historical = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json")
        self.assertEqual(historical["protocol_version"], V04_PROTOCOL_VERSION)
        self.assertEqual(historical["benchmark_version"], "0.3.0-pilot")
        self.assertEqual(historical["stimuli_sha256"], "0652f1c243fd5f1c8d63cdc84ccb577a9cb5867758d1167e506a6ed1786acdb7")
        # Literal protocol hashes come from the previously published a5f7c56 checkpoint.
        expected = {
            V04_PROTOCOL_VERSION: "0b685fc2fc6e3018f079e9f123017c100e958d19bdcd5d28b3092c9ee5536867",
            V04_DECISION_PROTOCOL_VERSION: "d4344ae38b436806b979e66ff3f2b8442a25dabbe9998cd4f9582d01f820e53e",
        }
        for protocol, protocol_hash in expected.items():
            plan = prepare(old / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=old / "avatars/avatar-manifest.private.json", protocol_version=protocol)
            self.assertEqual(plan["protocol_sha256"], protocol_hash)
            self.assertEqual(plan["protocol"]["human_timing"], {"exposure_ms": 6000, "decision_ms": 4000})
            self.assertNotIn("human_protocol_version", plan["protocol"])
            labels_for(plan, old / "question-bank.server.json")
            config = "jev-1.14.json" if protocol == V04_DECISION_PROTOCOL_VERSION else "opus-5-no-thinking.json"
            with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
                validate_execution(plan, load_json(ROOT / "evals/configs/gateway" / config))

    def test_old_timer_or_wrong_version_bank_cannot_score_current_plan(self):
        import copy
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bank.json"
            bank = load_json(DATA / "question-bank.server.json")
            wrong_timer = copy.deepcopy(bank)
            wrong_timer["timing"] = {"exposureMs": 6000, "decisionMs": 4000}
            write_json(path, wrong_timer)
            with self.assertRaisesRegex(ValueError, "timing differs"):
                labels_for(self.plan, path)
            bank["version"] = "0.4.0"
            write_json(path, bank)
            with self.assertRaisesRegex(ValueError, "version differs"):
                labels_for(self.plan, path)


if __name__ == "__main__":
    unittest.main()

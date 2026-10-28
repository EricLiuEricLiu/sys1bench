"""Checks on actual audited 0.4.0 source; synthetic responses remain mocks."""

import base64
import json
import tempfile
import unittest
from pathlib import Path

from evals.core import DECISION_PROTOCOL_VERSION, file_digest, load_json, prepare, request_for
from evals.export import export_records
from evals.runner import run
from evals.scoring import labels_for, score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evals/fixtures/cross-author-v0.4.0"


class CurrentBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = prepare(DATA / "stimuli.client.json", "pilot-cohort-001", avatar_manifest=DATA / "avatars/avatar-manifest.private.json")

    def test_actual_audit_hashes_reach_and_all_authors_are_distinct(self):
        client, bank, audit = (load_json(DATA / n) for n in ["stimuli.client.json", "question-bank.server.json", "audit.json"])
        self.assertEqual(audit["questionBankSha256"], file_digest(DATA / "question-bank.server.json"))
        self.assertEqual(audit["stimuliSha256"], file_digest(DATA / "stimuli.client.json"))
        self.assertEqual(audit["status"], "passed_saved_source_and_media_checks")
        self.assertEqual(client["timing"], {"exposureMs": 6000, "decisionMs": 4000})
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


if __name__ == "__main__":
    unittest.main()

"""Checks on the real frozen 0.5.0 source; responses remain synthetic mocks."""

import base64
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from evals.core import (DECISION_PROTOCOL_VERSION, HUMAN_PROTOCOL_VERSION, PROTOCOL_VERSION,
                        file_digest, load_json, prepare, request_for)
from evals.export import export_records
from evals.gateway import decision_payload
from evals.runner import run, validate_execution
from evals.scoring import labels_for, score

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evals/fixtures/cross-author-v0.5.0"
SEED = "pilot-cohort-001"


class FeedbackBankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.common = {"avatar_manifest": DATA / "avatars/avatar-manifest.private.json"}
        cls.plan = prepare(DATA / "stimuli.client.json", SEED, **cls.common)

    def test_real_freeze_hashes_metrics_and_viral_counts_match_audit(self):
        receipt = load_json(DATA / "dataset-manifest.json")
        for entry in receipt["files"]:
            self.assertEqual(file_digest(DATA / entry["path"]), entry["sha256"])
            self.assertEqual((DATA / entry["path"]).stat().st_size, entry["bytes"])
        bank, audit = (load_json(DATA / name) for name in ["question-bank.server.json", "audit.json"])
        self.assertEqual(file_digest(DATA / "question-bank.server.json"), "621b9d6dcb0589ff87e8e197fd40c4e9cbdcde03999317d4f44465c0d9a6890b")
        self.assertEqual(audit["questionBankSha256"], file_digest(DATA / "question-bank.server.json"))
        self.assertEqual(audit["stimuliSha256"], file_digest(DATA / "stimuli.client.json"))
        self.assertEqual(audit["status"], "passed_saved_source_and_media_checks")
        pairs = bank["practice"] + bank["pairs"]
        posts = [q[s] for q in pairs for s in ["left", "right"]]
        self.assertEqual((len(bank["practice"]), len(bank["pairs"]), len(posts)), (2, 15, 34))
        self.assertEqual(len({p["id"] for p in posts}), 34)
        self.assertEqual(len({p["author"]["id"] for p in posts}), 34)
        self.assertEqual(sum(len(p["media"]) for p in posts), 8)
        for p in posts:
            self.assertEqual(set(p["engagement"]), {"replies", "reposts", "likes", "impressions"})
            self.assertTrue(all(type(v) is int and v >= 0 for v in p["engagement"].values()))
            self.assertEqual(p["engagement"]["impressions"], p["views"])
            self.assertGreaterEqual(p["engagement"]["impressions"], 100000)
        viral = sorted(p["engagement"]["impressions"] for q in bank["pairs"] for p in [q["left"], q["right"]] if p["engagement"]["impressions"] >= 10000000)
        self.assertEqual(viral, [10230865, 14821801, 18951622])
        self.assertEqual(audit["summary"]["tenMillionPlusScoredPosts"], len(viral))
        self.assertEqual(len(labels_for(self.plan, DATA / "question-bank.server.json")[0]), 17)

    def test_visible_inputs_match_source_and_exact_captured_image_bytes(self):
        client = load_json(DATA / "stimuli.client.json")
        self.assertEqual(client["timing"], {"roundMs": 15000, "revealMs": 2500})
        self.assertEqual(client["humanProtocolId"], HUMAN_PROTOCOL_VERSION)
        source = {p["id"]: p for q in client["practice"] + client["pairs"] for p in [q["left"], q["right"]]}
        avatars = {e["url"]: e for e in load_json(self.common["avatar_manifest"])["entries"]}
        self.assertEqual(len(avatars), 34)
        for item in self.plan["items"]:
            request = request_for(item)
            self.assertIn("cumulative impressions", request["system"])
            visible = json.loads(request["user"])
            for side in ["A", "B"]:
                original = source[item[side]["id"]]
                self.assertEqual(visible[side]["text"], original["displayText"])
                self.assertEqual(visible[side]["author"], {k: original["author"][k] for k in ["name", "handle"]})
                self.assertEqual(set(visible[side]), {"text", "author", "avatar_ref", "image_refs"})
                self.assertNotIn(original["id"], request["user"])
                self.assertNotIn(original["author"]["avatarUrl"], request["user"])
                avatar = avatars[original["author"]["avatarUrl"]]
                self.assertEqual(base64.b64decode(item[side]["author"]["avatar"]["data_base64"]), (DATA / "avatars" / avatar["assetFile"]).read_bytes())
                for image, media in zip(item[side]["images"], original["media"]):
                    self.assertEqual(base64.b64decode(image["data_base64"]), (DATA / media["assetFile"]).read_bytes())
            for name in ["engagement", "replies", "reposts", "likes", "impressions", "views"]:
                self.assertNotIn('"' + name + '":', request["user"])

    def test_four_plain_models_and_both_protocols_use_same_real_stimuli(self):
        typed = prepare(DATA / "stimuli.client.json", SEED, protocol_version=DECISION_PROTOCOL_VERSION, **self.common)
        mirror = prepare(DATA / "stimuli.client.json", SEED, mirror=True, **self.common)
        self.assertEqual(typed["stimuli_sha256"], self.plan["stimuli_sha256"])
        self.assertEqual(mirror["stimuli_sha256"], self.plan["stimuli_sha256"])
        self.assertEqual(self.plan["protocol_version"], PROTOCOL_VERSION)
        self.assertNotEqual(typed["protocol_sha256"], self.plan["protocol_sha256"])
        paths = list((ROOT / "evals/configs/gateway").glob("*.json"))
        self.assertEqual(len(paths), 4)
        for path in paths:
            config = load_json(path)
            plan = typed if config["provider"] == "vercel-decision" else self.plan
            validate_execution(plan, config)
            if config["provider"] == "vercel-decision":
                payload = decision_payload(request_for(plan["items"][0]), config)
                self.assertTrue(all("impressions" in c["description"] for c in payload["questions"][0]["choices"]))
        for primary, reverse in zip(self.plan["items"], mirror["items"]):
            self.assertEqual(primary["A"], reverse["B"])
            self.assertEqual(primary["B"], reverse["A"])

    def test_real_bank_mock_score_export_keeps_feedback_conditions_and_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(self.plan, load_json(ROOT / "evals/configs/mock.json"), root / "run")
            summary, answers = score(root / "run", DATA / "question-bank.server.json", root / "score")
            self.assertTrue(summary["is_mock"])
            self.assertEqual(summary["counts"]["planned_scored"], 15)
            self.assertEqual(summary["counts"]["practice"], 2)
            self.assertEqual(len(answers), 17)
            self.assertEqual(summary["outcome_metric"], "cumulative impressions")
            self.assertEqual(summary["human_timing"], {"round_ms": 15000, "reveal_ms": 2500})
            self.assertEqual(summary["human_feedback"]["rounds"], "practice_and_scored")
            self.assertIn("no reveal/history", summary["human_model_comparability"])
            self.assertIsNone(summary["cluster_bootstrap_sensitivity"]["interval_95"])
            export_records(root / "run", root / "score", root / "export")
            sql = (root / "export/import.private.sql").read_text()
            self.assertNotIn("data_base64", sql)
            self.assertLess(max(len(line.encode()) for line in sql.splitlines()), 100000)
            with closing(sqlite3.connect(":memory:")) as db:
                db.executescript((ROOT / "evals/schema.sql").read_text())
                db.executescript(sql)
                self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
                self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
                self.assertEqual(db.execute("SELECT count(*) FROM eval_public_run_aggregates").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()

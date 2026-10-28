"""Offline checks against actual frozen 0.3.0 stimuli; no provider calls."""

import base64
import copy
import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evals.adapters import Reply, openai_payload
from evals.assets import image_info, validate_blob
from evals.core import (V03_DECISION_PROTOCOL_VERSION as DECISION_PROTOCOL_VERSION, PROTOCOL_VERSION, digest, file_digest,
                        load_json, prepare, read_stimuli, request_for, validate_request, write_json)
from evals.export import export_records
from evals.gateway import (GatewayDecisionAdapter, GatewayResponsesAdapter, add_gateway_metadata,
                           decision_payload, validate_gateway_config)
from evals.runner import run, validate_execution
from evals.scoring import labels_for, score
from evals.tests.fixture_helpers import cross_author_fixture

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "evals/fixtures/author-image-v0.3.0"
STIMULI = DATA / "stimuli.client.json"
AVATARS = DATA / "avatars/avatar-manifest.private.json"
CATALOG = ROOT / "evals/fixtures/gateway/models.catalog.json"
MOCK = {"provider": "mock", "model": "mock-fixture-v1", "scenario": "choices", "reasoning_effort": "none", "max_output_tokens": 32, "timeout_seconds": 5, "diagnostic_retries": 0, "pricing": None}


def gateway_config(model="anthropic/claude-opus-5", provider="vercel-responses"):
    return {"provider": provider, "model": model, "reasoning_effort": "omit-nonreasoning" if provider == "vercel-decision" else "none",
            "max_output_tokens": 0 if provider == "vercel-decision" else 128, "timeout_seconds": 30, "diagnostic_retries": 0,
            "pricing": None, "image_detail": "high", "gateway_catalog_sha256": file_digest(CATALOG),
            "gateway_only": [model.split("/")[0] if not model.startswith("spacexai/") else "xai"],
            "no_thinking_policy_sha256": file_digest(CATALOG.parent / "no-thinking-policy.json")}


class CaptureAdapter:
    def __init__(self):
        self.requests = []

    def generate(self, request):
        self.requests.append(copy.deepcopy(request))
        return Reply("A", {"fixture": True, "text": "A"}, returned_model="synthetic-only")


class MultimodalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = prepare(STIMULI, "pilot-cohort-001", avatar_manifest=AVATARS)

    def test_actual_two_practices_15_scored_no_repeat_and_matching_bank(self):
        items = self.plan["items"]
        self.assertEqual([i["kind"] for i in items], ["practice"] * 2 + ["scored"] * 15)
        self.assertFalse(items[0]["A"]["images"])
        self.assertTrue(items[1]["A"]["images"])
        self.assertEqual(len({i[s]["id"] for i in items for s in ["A", "B"]}), 34)
        self.assertEqual(sum(len(i[s]["images"]) for i in items for s in ["A", "B"]), 8)
        labels, bank = labels_for(self.plan, DATA / "question-bank.server.json")
        self.assertEqual(len(labels), 17)
        self.assertEqual(bank["version"], "0.3.0")

    def test_visible_text_author_and_image_bytes_match_human_export(self):
        client = load_json(STIMULI)
        source = {p["id"]: p for pair in client["practice"] + client["pairs"] for p in [pair["left"], pair["right"]]}
        captures = {e["url"]: e for e in load_json(AVATARS)["entries"]}
        for item in self.plan["items"]:
            request = validate_request(request_for(item))
            visible = json.loads(request["user"])
            for side in ["A", "B"]:
                post = item[side]
                original = source[post["id"]]
                self.assertEqual(visible[side]["text"], original["displayText"])
                self.assertEqual(visible[side]["author"], {k: original["author"][k] for k in ["name", "handle"]})
                avatar = captures[original["author"]["avatarUrl"]]
                self.assertEqual(base64.b64decode(post["author"]["avatar"]["data_base64"]), (AVATARS.parent / avatar["assetFile"]).read_bytes())
                for blob, original_image in zip(post["images"], original["media"]):
                    self.assertEqual(base64.b64decode(blob["data_base64"]), (DATA / original_image["assetFile"]).read_bytes())
                    self.assertEqual(blob["sha256"], original_image["sha256"])

    def test_adapter_gets_no_outcomes_urls_ids_or_hidden_metadata(self):
        bank = load_json(DATA / "question-bank.server.json")
        originals = [p for pair in bank["practice"] + bank["pairs"] for p in [pair["left"], pair["right"]]]
        with tempfile.TemporaryDirectory() as directory:
            adapter = CaptureAdapter()
            run(self.plan, MOCK, Path(directory) / "run", adapter=adapter)
        self.assertEqual(len(adapter.requests), 17)
        for request in adapter.requests:
            self.assertEqual(set(request), {"system", "user", "images"})
            body = json.loads(request["user"])
            self.assertEqual(set(body), {"A", "B"})
            for p in originals:
                self.assertNotIn(p["id"], request["user"])
                self.assertNotIn(p["url"], request["user"])
                self.assertNotIn(p["author"]["avatarUrl"], request["user"])
            for side in ["A", "B"]:
                self.assertEqual(set(body[side]), {"text", "author", "avatar_ref", "image_refs"})
            for image in request["images"]:
                self.assertNotIn("url", image)
                self.assertNotIn("alt", image)
                self.assertNotIn("assetFile", image)

    def test_injected_response_metadata_at_each_boundary_is_rejected(self):
        request = request_for(self.plan["items"][1])
        for location in ["post", "author", "image"]:
            bad = copy.deepcopy(request)
            if location == "image":
                bad["images"][0]["views"] = 123456
            else:
                posts = json.loads(bad["user"])
                target = posts["A"] if location == "post" else posts["A"]["author"]
                target["followers"] = 123456
                bad["user"] = json.dumps(posts)
            with self.assertRaises(ValueError):
                validate_request(bad)

    def test_missing_or_tampered_assets_fail_before_provider(self):
        with self.assertRaisesRegex(ValueError, "Avatar bytes missing"):
            prepare(STIMULI, "seed")
        blob = copy.deepcopy(self.plan["items"][1]["A"]["images"][0])
        blob["data_base64"] = blob["data_base64"][:-8] + "AAAAAAAA"
        with self.assertRaises(ValueError):
            validate_blob(blob)

    def test_mirror_moves_whole_author_and_image_stimuli(self):
        mirror = prepare(STIMULI, "pilot-cohort-001", mirror=True, avatar_manifest=AVATARS)
        self.assertEqual(mirror["stimuli_sha256"], self.plan["stimuli_sha256"])
        for a, b in zip(self.plan["items"], mirror["items"]):
            self.assertEqual(a["A"], b["B"])
            self.assertEqual(a["B"], b["A"])

    def test_openresponses_uses_inline_original_bytes_and_disables_reasoning(self):
        request = request_for(self.plan["items"][1])
        payload = openai_payload(request, gateway_config())
        self.assertEqual(payload["reasoning"], {"effort": "none"})
        self.assertEqual(payload["tools"], [])
        self.assertEqual(payload["tool_choice"], "none")
        parts = payload["input"][0]["content"]
        images = [p for p in parts if p["type"] == "input_image"]
        self.assertEqual(len(images), 4)
        for wire, source in zip(images, request["images"]):
            self.assertTrue(wire["image_url"].startswith("data:"))
            self.assertEqual(wire["image_url"].split(",", 1)[1], source["data_base64"])
        self.assertNotIn("models", json.dumps(payload))

    def test_always_thinking_requested_models_are_ineligible(self):
        for model in ["anthropic/claude-opus-5.5", "anthropic/claude-fable-5.1", "openai/gpt-6-astra", "openai/gpt-6.1-sol", "spacexai/grok-4.7"]:
            with self.assertRaisesRegex(ValueError, "thinking disabled"):
                validate_gateway_config(gateway_config(model))
        for model in ["anthropic/claude-opus-5", "openai/gpt-6-sol", "spacexai/grok-4.20-non-reasoning"]:
            validate_gateway_config(gateway_config(model))

    def test_all_four_selected_configs_have_reviewed_disabled_thinking(self):
        paths = sorted((ROOT / "evals/configs/gateway").glob("*.json"))
        self.assertEqual(len(paths), 4)
        self.assertEqual({load_json(p)["model"] for p in paths}, {
            "anthropic/claude-opus-5", "openai/gpt-6-sol",
            "spacexai/grok-4.20-non-reasoning", "typesafe-ai/jev-1.14.0",
        })
        for path in paths:
            config = load_json(path)
            validate_gateway_config(config)
            if config["provider"] == "vercel-responses":
                self.assertEqual(config["reasoning_effort"], "none")
                with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
                    validate_execution(self.plan, config)
        with self.assertRaisesRegex(ValueError, "reviewed strict no-thinking"):
            validate_gateway_config(gateway_config("mistral/mistral-large-4"))
        policy = load_json(CATALOG.parent / "no-thinking-policy.json")
        for model in ["google/gemini-2.5-flash", "meta/llama-4-maverick"]:
            self.assertFalse(policy["models"][model]["eligible"])

    def test_low_minimal_cannot_launch_even_if_adapter_injected(self):
        for effort in ["low", "minimal"]:
            config = {**gateway_config(), "reasoning_effort": effort}
            adapter = CaptureAdapter()
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
                    run(self.plan, config, Path(directory) / "run", allow_paid=True, adapter=adapter)
            self.assertEqual(adapter.requests, [])

    def test_jev_has_its_own_protocol_and_typed_choice_not_probability_argmax(self):
        plan = prepare(STIMULI, "pilot-cohort-001", avatar_manifest=AVATARS, protocol_version=DECISION_PROTOCOL_VERSION)
        self.assertEqual(plan["stimuli_sha256"], self.plan["stimuli_sha256"])
        self.assertNotEqual(plan["protocol_sha256"], self.plan["protocol_sha256"])
        config = gateway_config("typesafe-ai/jev-1.14.0", "vercel-decision")
        with self.assertRaisesRegex(ValueError, "Historical datasets are frozen"):
            validate_execution(plan, config)
        payload = decision_payload(request_for(plan["items"][1]), config)
        self.assertNotIn("reasoning", payload)
        self.assertNotIn("max_output_tokens", payload)
        self.assertEqual([c["value"] for c in payload["questions"][0]["choices"]], ["A", "B"])
        self.assertEqual(payload["providerOptions"], {"gateway": {"only": ["typesafe-ai"]}})
        with patch.dict(os.environ, {"AI_GATEWAY_API_KEY": "synthetic-secret"}):
            adapter = GatewayDecisionAdapter(config)
        raw = {"model": config["model"], "answers": [{"name": "winner", "type": "choice", "choice": "A", "probabilities": [{"value": "B", "probability": .99}]}], "usage": {"input_tokens": 100, "output_tokens": 0, "total_tokens": 100}}
        self.assertEqual(adapter.decode(raw, "fixture-request").text, "A")
        raw["answers"][0]["choice"] = "invalid"
        self.assertEqual(adapter.decode(raw, "fixture-request").text, "invalid")
        with self.assertRaises(ValueError):
            validate_execution(self.plan, config)

    def test_gateway_cost_routing_and_reasoning_violations_are_recorded(self):
        config = gateway_config()
        raw = {"provider_metadata": {"gateway": {"cost": "0.0012", "generationId": "synthetic-gen", "routing": {"originalModelId": config["model"], "canonicalSlug": config["model"], "finalProvider": "anthropic"}}}}
        reply = add_gateway_metadata(Reply("A", raw), raw, config)
        self.assertEqual(reply.reported_cost_usd, .0012)
        self.assertEqual(reply.gateway_metadata["generationId"], "synthetic-gen")
        reply = add_gateway_metadata(Reply("A", raw, usage={"output_tokens_details": {"reasoning_tokens": 1}}), raw, config)
        self.assertEqual(reply.status, "unexpected_output")
        raw["provider_metadata"]["gateway"]["routing"]["canonicalSlug"] = "unexpected/fallback-model"
        self.assertEqual(add_gateway_metadata(Reply("A", raw), raw, config).status, "unexpected_output")

    def test_two_practices_are_excluded_from_sql_and_scoring_denominator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            run(self.plan, MOCK, root / "run")
            summary, answers = score(root / "run", DATA / "question-bank.server.json", root / "score")
            self.assertEqual(summary["counts"]["planned_scored"], 15)
            self.assertEqual(summary["counts"]["practice"], 2)
            self.assertEqual(len(answers), 17)
            export_records(root / "run", root / "score", root / "export")
            db = sqlite3.connect(":memory:")
            self.addCleanup(db.close)
            db.executescript((ROOT / "evals/schema.sql").read_text())
            sql = (root / "export/import.private.sql").read_text()
            self.assertNotIn("data_base64", sql)
            self.assertLess(max(len(line.encode()) for line in sql.splitlines()), 100_000)
            db.executescript(sql)
            self.assertEqual(db.execute("SELECT count(*) FROM eval_answers WHERE kind='practice'").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT count(*) FROM eval_public_run_aggregates").fetchone()[0], 0)
            db.execute("UPDATE eval_runs SET participant_kind='model',is_mock=0")
            self.assertEqual(db.execute("SELECT denominator FROM eval_public_run_aggregates").fetchone()[0], 15)

    def test_bounded_campaign_cannot_repeat_models_or_run_without_key(self):
        from evals.campaign import preflight_campaign, run_campaign
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stimuli, bank = cross_author_fixture(root / "synthetic-inputs")
            current_plan = prepare(stimuli, "synthetic-seed")
            write_json(root / "plan.json", current_plan)
            config = load_json(ROOT / "evals/configs/gateway/opus-5-no-thinking.json")
            write_json(root / "config.json", config)
            write_json(root / "bank.json", load_json(bank))
            entry = {"model": config["model"], "planned_items": 3, "plan": "plan.json", "config": "config.json", "bank": "bank.json",
                     **{k + "_file_sha256": file_digest(root / (k + ".json")) for k in ["plan", "config", "bank"]}}
            manifest = {"schema_version": "gateway-campaign-v1", "lineup_approved": True, "primary_runs_per_model": 1, "automatic_mirrors": 0, "maximum_requests": 3, "entries": [entry]}
            write_json(root / "campaign.json", manifest)
            _, jobs = preflight_campaign(root / "campaign.json")
            self.assertEqual(len(jobs), 1)
            with patch.dict(os.environ, {}, clear=True):
                with self.assertRaisesRegex(ValueError, "AI_GATEWAY_API_KEY is missing"):
                    run_campaign(root / "campaign.json", root / "out", allow_paid=True)
            self.assertFalse((root / "out").exists())
            manifest["entries"].append(entry)
            manifest["maximum_requests"] = 6
            write_json(root / "campaign.json", manifest)
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                preflight_campaign(root / "campaign.json")

    def test_prepared_campaign_is_four_distinct_models_68_requests(self):
        from evals.campaign import prepare_campaign
        with tempfile.TemporaryDirectory() as directory:
            manifest = prepare_campaign(Path(directory) / "campaign")
        self.assertEqual(len({e["model"] for e in manifest["entries"]}), 4)
        self.assertEqual(manifest["maximum_requests"], 68)
        self.assertEqual(manifest["automatic_mirrors"], 0)

    def test_frozen_text_baseline_still_has_identical_plan_hash(self):
        original = ROOT / "evals/fixtures/text-v0.1.1/stimuli.client.json"
        plan = prepare(original, "pilot-cohort-001")
        self.assertEqual(plan["protocol_version"], "direct-ab-v1")
        self.assertEqual(plan["stimuli_sha256"], "a714efd07d6cf5ad9383d6a386c8e5040c98fc78f3293564c6ef949a97b2fb5b")


if __name__ == "__main__":
    unittest.main()

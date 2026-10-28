"""Bounded Gateway calls; exact catalog IDs, no fallback models, no tools."""

import math
from pathlib import Path

from .adapters import (AdapterError, GATEWAY_DECISION_ENDPOINT, GATEWAY_RESPONSES_ENDPOINT,
                       OpenAIResponsesAdapter, Reply, decode_openai, image_content, openai_payload)
from .core import DECISION_SYSTEM_PROMPT, file_digest, load_json, require, validate_request

CATALOG = Path(__file__).parent / "fixtures/gateway/models.catalog.json"


def validate_gateway_config(config):
    require(config["gateway_catalog_sha256"] == file_digest(CATALOG), "Gateway catalog snapshot/hash mismatch")
    models = load_json(CATALOG)["data"]
    model = next((m for m in models if m["id"] == config["model"]), None)
    require(model is not None, "Exact model absent from saved Gateway catalog; refresh/review catalog explicitly")
    require("image" in model.get("modalities", {}).get("input", []), "Model does not accept matched visual stimuli")
    decision = config["provider"] == "vercel-decision"
    require(model["type"] == ("evaluation" if decision else "language"), "Wrong API surface for model type")
    efforts = [v for option in model.get("reasoning_options", []) if option.get("type") == "effort" for v in option["values"]]
    if not decision:
        require(config["reasoning_effort"] == "none" and "none" in efforts, "This benchmark requires thinking disabled; always-thinking models are ineligible")
    policy_path = CATALOG.parent / "no-thinking-policy.json"
    policy = load_json(policy_path)
    require(config.get("no_thinking_policy_sha256") == file_digest(policy_path), "No-thinking policy review/hash mismatch")
    require(policy["models"].get(config["model"], {}).get("eligible") is True, "Model lacks a reviewed strict no-thinking configuration")
    endpoint_path = CATALOG.parent / (config["model"].replace("/", "--") + ".endpoints.json")
    endpoints = load_json(endpoint_path)["data"]["endpoints"]
    allowed = config.get("gateway_only")
    require(isinstance(allowed, list) and len(allowed) == 1 and allowed[0] in {e["provider_name"] for e in endpoints}, "Pin one verified provider endpoint; no automatic provider failover")
    return model


def routing_options(config):
    return {"gateway": {"only": config["gateway_only"]}}


def decision_payload(request, config):
    validate_request(request)
    require(request["system"] == DECISION_SYSTEM_PROMPT, "Native decision adapter requires its own versioned choice protocol")
    return {"model": config["model"], "input": [{"role": "user", "content": image_content(request, config)}],
            "questions": [{"type": "choice", "name": "winner", "instructions": request["system"],
                           "choices": [{"value": "A", "description": "The left post received more cumulative views at capture."},
                                       {"value": "B", "description": "The right post received more cumulative views at capture."}]}],
            "providerOptions": routing_options(config)}


def add_gateway_metadata(reply, raw, config):
    envelope = raw.get("provider_metadata", raw.get("providerMetadata", {}))
    metadata = envelope.get("gateway", {}) if isinstance(envelope, dict) else {}
    reply.gateway_metadata = metadata
    reasoning_tokens = ((reply.usage or {}).get("output_tokens_details") or {}).get("reasoning_tokens") if isinstance(reply.usage, dict) else None
    if reasoning_tokens is not None and reasoning_tokens > 0:
        reply.status = "unexpected_output"
    routing = metadata.get("routing", {})
    if isinstance(routing, dict):
        # Reject routing/model substitution if the gateway reports it.
        for key in ["originalModelId", "canonicalSlug"]:
            if routing.get(key) and routing[key] != config["model"]:
                reply.status = "unexpected_output"
        final = routing.get("finalProvider")
        if final and final not in config["gateway_only"]:
            reply.status = "unexpected_output"
    try:
        cost = float(metadata["cost"])
        if math.isfinite(cost) and cost >= 0:
            reply.reported_cost_usd = cost
    except (ValueError, TypeError, KeyError):
        pass
    return reply


class GatewayResponsesAdapter(OpenAIResponsesAdapter):
    endpoint = GATEWAY_RESPONSES_ENDPOINT
    key_env = "AI_GATEWAY_API_KEY"

    def __init__(self, config):
        validate_gateway_config(config)
        super().__init__(config)

    def generate(self, request):
        payload = openai_payload(request, self.config)
        payload["providerOptions"] = routing_options(self.config)
        return self.post(payload)

    def decode(self, raw, request_id):
        return add_gateway_metadata(decode_openai(raw, request_id), raw, self.config)


class GatewayDecisionAdapter(GatewayResponsesAdapter):
    endpoint = GATEWAY_DECISION_ENDPOINT

    def generate(self, request):
        return self.post(decision_payload(request, self.config))

    def decode(self, raw, request_id):
        if not isinstance(raw, dict):
            raise AdapterError("malformed_provider_response", raw={"body": raw}, request_id=request_id)
        answers = raw.get("answers")
        if not isinstance(answers, list) or len(answers) != 1 or not isinstance(answers[0], dict):
            raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
        answer = answers[0]
        if answer.get("type") != "choice" or answer.get("name") != "winner":
            raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
        # The model's declared choice is authoritative. Never select argmax as a repair.
        choice = answer.get("choice")
        reply = Reply(choice if isinstance(choice, str) else None, raw, request_id=request_id,
                      returned_model=raw.get("model"), usage=raw.get("usage"))
        return add_gateway_metadata(reply, raw, self.config)

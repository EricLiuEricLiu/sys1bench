"""Adapters receive visible stimuli only, including captured image bytes."""

import json
import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

from .core import canonical, digest, require, validate_request, DECISION_SYSTEM_PROMPTS

OPENAI_ENDPOINT = "https://api.openai.com/v1/responses"
GATEWAY_RESPONSES_ENDPOINT = "https://ai-gateway.vercel.sh/v1/responses"
GATEWAY_DECISION_ENDPOINT = "https://ai-gateway.vercel.sh/v1/decisions"


@dataclass
class Reply:
    text: str | None
    raw: dict
    status: str = "ok"
    request_id: str | None = None
    returned_model: str | None = None
    usage: dict | None = None
    reported_cost_usd: float | None = None
    gateway_metadata: dict | None = None


class AdapterError(Exception):
    def __init__(self, code, *, retryable=False, raw=None, request_id=None):
        super().__init__(code)
        self.code = code
        self.retryable = retryable
        self.raw = raw
        self.request_id = request_id


class Adapter(Protocol):
    def generate(self, request: dict) -> Reply: ...


def validate_config(config):
    common = {"provider", "model", "reasoning_effort", "max_output_tokens", "timeout_seconds", "diagnostic_retries", "pricing", "image_detail", "gateway_catalog_sha256", "gateway_only", "requested_name", "no_thinking_policy_sha256"}
    require(isinstance(config, dict), "Config must be an object")
    provider = config.get("provider")
    require(provider in {"mock", "openai-responses", "vercel-responses", "vercel-decision"}, "Unsupported provider adapter")
    allowed = common | ({"scenario"} if provider == "mock" else set())
    require(not set(config) - allowed, "Unexpected config fields; credentials and arbitrary request overrides are prohibited")
    require(isinstance(config.get("model"), str) and config["model"].strip(), "Explicit model identifier required")
    require(config.get("reasoning_effort") in {"none", "minimal", "low", "omit-nonreasoning"}, "Choose none, minimal, low, or omit-nonreasoning after checking model support")
    require(config.get("image_detail", "high") in {"low", "high", "original", "auto"}, "Invalid image detail setting")
    if provider.startswith("vercel-"):
        require("/" in config["model"] and not config["model"].startswith("vmc/"), "Exact catalog provider/model required; virtual routing is not allowed")
    if provider == "vercel-decision":
        require(config["reasoning_effort"] == "omit-nonreasoning", "Native decision API has no reasoning effort parameter")
    for field, lower, upper in [("max_output_tokens", 0 if provider == "vercel-decision" else 1, 4096), ("timeout_seconds", 1, 60), ("diagnostic_retries", 0, 2)]:
        require(type(config.get(field)) is int and lower <= config[field] <= upper, f"Invalid {field}")
    if provider == "mock":
        require(config["model"] == "mock-fixture-v1", "Mock model must be mock-fixture-v1")
        require(config.get("scenario", "choices") in {"choices", "mixed-failures"}, "Unknown mock scenario")
        require(config.get("pricing") is None, "Mock fixtures have no token pricing")
    if provider == "vercel-decision":
        require(config["max_output_tokens"] == 0, "Decision output is a typed choice; use 0 to denote no output-token parameter")
    pricing = config.get("pricing")
    if pricing is not None:
        fields = {"input_usd_per_million", "cached_input_usd_per_million", "output_usd_per_million", "source", "as_of"}
        require(isinstance(pricing, dict) and set(pricing) == fields, "Pricing requires all rates, source and as_of")
        for k in fields - {"source", "as_of"}:
            require(type(pricing[k]) in {int, float} and 0 <= pricing[k] < 1000000, "Invalid token price")
        require(all(isinstance(pricing[k], str) and pricing[k] for k in ["source", "as_of"]), "Pricing provenance required")
    return config


class MockAdapter:
    def __init__(self, config):
        self.config = config
        self.calls = 0

    def generate(self, request):
        validate_request(request)
        self.calls += 1
        event = (self.calls - 1) % 6 if self.config.get("scenario") == "mixed-failures" else 0
        raw = {"fixture": True, "scenario": self.config.get("scenario", "choices"), "call": self.calls}
        if event == 2:
            raise AdapterError("timeout", retryable=True, raw=raw)
        if event == 3:
            raise AdapterError("http_429", retryable=True, raw=raw)
        text = "A" if int(digest(request)[-1], 16) % 2 == 0 else "B"
        if event == 1:
            text = "A because this is a synthetic invalid response."
        if event == 4:
            return Reply(None, {**raw, "refusal": "synthetic refusal"}, status="refused", returned_model="mock-fixture-v1")
        return Reply(text, {**raw, "text": text}, returned_model="mock-fixture-v1")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not forward Authorization to a redirected endpoint.
        return None


def image_content(request, config):
    content = [{"type": "input_text", "text": request["user"]}]
    for image in request.get("images", []):
        content.append({"type": "input_text", "text": "Image reference: " + image["ref"]})
        content.append({"type": "input_image", "image_url": f"data:{image['mime_type']};base64,{image['data_base64']}", "detail": config.get("image_detail", "high")})
    return content


def openai_payload(request, config):
    validate_request(request)
    require(request["system"] not in DECISION_SYSTEM_PROMPTS, "Typed decision protocol requires the decision adapter")
    payload = {
        "model": config["model"],
        "instructions": request["system"],
        "input": [{"role": "user", "content": image_content(request, config) if "images" in request else request["user"]}],
        "max_output_tokens": config["max_output_tokens"],
        "tools": [],
        "tool_choice": "none",
        "store": False,
        "stream": False,
    }
    if config["reasoning_effort"] != "omit-nonreasoning":
        payload["reasoning"] = {"effort": config["reasoning_effort"]}
    return payload


def decode_openai(raw, request_id=None):
    if not isinstance(raw, dict):
        raise AdapterError("malformed_provider_response", raw={"body": raw}, request_id=request_id)
    text, refusal, unexpected = [], False, False
    output = raw.get("output", [])
    if not isinstance(output, list):
        raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
    for part in output:
        if not isinstance(part, dict):
            raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
        if part.get("type") not in {"message", "reasoning"}:
            unexpected = True
        if part.get("type") == "message":
            contents = part.get("content", [])
            if not isinstance(contents, list) or any(not isinstance(c, dict) for c in contents):
                raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
            for content in contents:
                if content.get("type") == "output_text":
                    if not isinstance(content.get("text"), str):
                        raise AdapterError("malformed_provider_response", raw=raw, request_id=request_id)
                    text.append(content["text"])
                elif content.get("type") == "refusal":
                    refusal = True
                else:
                    unexpected = True
    status = "ok" if raw.get("status") == "completed" else "provider_incomplete"
    if unexpected:
        status = "unexpected_output"
    if refusal:
        status = "refused"
    usage = raw.get("usage")
    reasoning_tokens = ((usage.get("output_tokens_details") or {}).get("reasoning_tokens")) if isinstance(usage, dict) else None
    if status == "ok" and isinstance(reasoning_tokens, (int, float)) and reasoning_tokens > 0:
        status = "unexpected_output"
    if status == "ok" and any(p.get("type") == "reasoning" and any(p.get(k) for k in ["summary", "content", "text"]) for p in output):
        status = "unexpected_output"
    return Reply("".join(text), raw, status, request_id, raw.get("model"), raw.get("usage"))


class OpenAIResponsesAdapter:
    endpoint = OPENAI_ENDPOINT
    key_env = "OPENAI_API_KEY"

    def __init__(self, config):
        self.config = config
        expected = "omit-nonreasoning" if self.endpoint == GATEWAY_DECISION_ENDPOINT else "none"
        require(config["reasoning_effort"] == expected, "Thinking must be disabled before constructing a real adapter")
        self.key = os.environ.get(self.key_env)
        require(bool(self.key), self.key_env + " must be set in the environment; do not put it in config")
        self.opener = urllib.request.build_opener(NoRedirect())

    def generate(self, request):
        return self.post(openai_payload(request, self.config))

    def post(self, payload):
        req = urllib.request.Request(self.endpoint, data=canonical(payload).encode(), headers={
            "Authorization": "Bearer " + self.key,
            "Content-Type": "application/json",
            "User-Agent": "system-1-bench-evals/2.0.0",
        }, method="POST")
        try:
            with self.opener.open(req, timeout=self.config["timeout_seconds"]) as response:
                body = response.read().decode("utf-8")
                request_id = response.headers.get("x-request-id")
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace").replace(self.key, "[REDACTED]")
            finally:
                exc.close()
            raise AdapterError(f"http_{exc.code}", retryable=exc.code == 429 or exc.code >= 500,
                               raw={"http_status": exc.code, "body": body}, request_id=exc.headers.get("x-request-id")) from None
        except (TimeoutError, socket.timeout):
            raise AdapterError("timeout", retryable=True) from None
        except urllib.error.URLError as exc:
            code = "timeout" if isinstance(exc.reason, (TimeoutError, socket.timeout)) else "network_error"
            raise AdapterError(code, retryable=True) from None
        except UnicodeError:
            raise AdapterError("malformed_provider_response") from None
        body = body.replace(self.key, "[REDACTED]")
        try:
            raw = json.loads(body)
        except ValueError:
            raise AdapterError("malformed_provider_response", raw={"body": body}, request_id=request_id) from None
        # Scrub a key if an upstream response ever echoes it; never persist auth headers.
        raw = json.loads(canonical(raw).replace(self.key, "[REDACTED]"))
        return self.decode(raw, request_id)

    def decode(self, raw, request_id):
        return decode_openai(raw, request_id)


def make_adapter(config):
    validate_config(config)
    if config["provider"] == "mock":
        return MockAdapter(config)
    if config["provider"].startswith("vercel-"):
        from .gateway import GatewayResponsesAdapter, GatewayDecisionAdapter
        return (GatewayDecisionAdapter if config["provider"] == "vercel-decision" else GatewayResponsesAdapter)(config)
    return OpenAIResponsesAdapter(config)


def estimated_cost(usage, pricing):
    if not isinstance(usage, dict) or not pricing:
        return None
    input_tokens, output_tokens = usage.get("input_tokens"), usage.get("output_tokens")
    cached = (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)
    if any(type(x) is not int or x < 0 for x in [input_tokens, output_tokens, cached]) or cached > input_tokens:
        return None
    return ((input_tokens - cached) * pricing["input_usd_per_million"] + cached * pricing["cached_input_usd_per_million"] + output_tokens * pricing["output_usd_per_million"]) / 1_000_000

# Why this no-thinking lineup

Eric originally requested `opus5.5 fable5.1 astra sol6.1 grok and jev`, confirmed Grok 4.7/Jev 1.14 pins, then made **disabled thinking** a strict condition. After seeing the incompatibilities, he approved the four plain alternatives. He later asked to remove the older Gemini 2.5 and Llama 4 additions. The active four are:

| Gateway model | Why it is included | Deliberation control |
| --- | --- | --- |
| `anthropic/claude-opus-5` | Opus-family representative with a real off switch; approved replacement for Opus 5.5 | Gateway `none` → thinking disabled |
| `openai/gpt-6-sol` | Recognizable OpenAI general-purpose Sol representative; approved replacement for Sol 6.1 | Responses `reasoning.effort: none` |
| `spacexai/grok-4.20-non-reasoning` | Dedicated plain Grok variant; approved replacement for Grok 4.7 | Non-reasoning model ID plus `none` |
| `typesafe-ai/jev-1.14.0` | Requested System One decision baseline with image support | Native typed-decision API; separate protocol |

These are useful family representatives under the strict constraint, not a claim that every entry is its vendor's newest flagship or that any performs well on this benchmark. Each active model is pinned to its cataloged native provider endpoint. All four routes were exercised in the real 0.6.0 comparison. They receive the same captured visible content; Jev requires registered avatar pixel repetition to meet its documented image minimum, with that difference disclosed in its own protocol and public inputNotes. See [REAL_RUNS.md](REAL_RUNS.md) for actual scores, routing and preserved recovery provenance.

The original versions are preserved in the resolution report as ineligible: Opus 5.5/Fable 5.1 always think; Astra, Sol 6.1 and Grok 4.7 lack an off setting. Anthropic explicitly rejects disabled thinking for the first two, and the other exact versions' supported efforts start at `low`. See [Anthropic's API errors](https://platform.claude.com/docs/en/api/errors), [OpenAI's reasoning guide](https://developers.openai.com/api/docs/guides/reasoning) and the [Gateway catalog](https://ai-gateway.vercel.sh/v1/models).

Primary checks matter: Google documents that [2.5 Flash can disable thinking, while 2.5 Pro cannot](https://ai.google.dev/gemini-api/docs/generate-content/thinking). Mistral Large 4 was considered and excluded because its [primary docs describe `none` as minimal hidden thinking](https://docs.mistral.ai/studio/conversations/reasoning). A generic catalog `none` flag alone therefore does not satisfy this task. Jev's [versioned image support](https://vercel.com/changelog/typesafe-ais-jev-1-14-is-now-available-on-ai-gateway) uses typed decisions, not free-text generation.

The bounded primary plan is **four models × (two unscored practices + 15 scored items) = 68 requests**. No automated repeats, parameter search, fallback models or mirror runs. Generated-token cap is 128 per language-model request; native Jev decisions have no output-token parameter. Unknown usage/cost stays null. The test measures direct choices with deliberation features disabled; it cannot establish absence of latent computation or reasoning ability inside a model.

Gemini 2.5 Flash and Llama 4 Maverick are removed from active configs and eligibility. Newer Gemini 3/4 models do not support full thinking-off according to [Google's current guide](https://ai.google.dev/gemini-api/docs/generate-content/thinking). Current Meta Muse models do not provide a verified replacement under this policy: [Wonder starts at minimal](https://dev.meta.ai/docs/models), and [Glimmer's primary prompting guide documents a private reasoning turn with low-through-xhigh strength](https://dev.meta.ai/docs/muse-glimmer/prompting), despite generic catalog none metadata. No newer model is substituted automatically. Historical catalog entries remain only for the selection audit.

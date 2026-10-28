# System 1 Bench evaluations

Python 3.11+, standard library only. Run from `/Users/ericliu/Documents/ChatGPT/sys1bench`. The current task shows author name/handle/avatar and attached images, hides followers/engagement, and uses two educational practices followed by 15 scored pairs. Human timing is now 6 seconds to look + 4 seconds to choose. Every practice/scored pair compares different authors.

Eric requires **thinking/reasoning disabled**, including no `low` or `minimal`. The approved substitutions are documented in [MODEL_SELECTION.md](MODEL_SELECTION.md). The original exact always-thinking versions remain recorded as ineligible; none is silently substituted during execution.

**Current release:** the actual audited 0.4.0 bank is frozen under tracked fixtures. Historical 0.3.0 campaigns remain replayable but cannot launch paid calls. The current primary plan uses only the new cross-author bank.

## Verify and prepare offline

```sh
python3 -m unittest discover -s evals/tests -v
python3 -m evals prepare-campaign --out evals/runs/no-thinking-campaign
python3 -m evals campaign-preflight --manifest evals/runs/no-thinking-campaign/campaign.json
```

Preparation uses tracked `evals/fixtures/cross-author-v0.4.0/` and four exact Gateway configs. It makes **zero network/model calls**. CI needs no `outputs/`, API keys, paid requests, package installation, or avatar downloads. The frozen bank has two practice pairs (text then image), 15 scored pairs, 34 distinct posts and 34 distinct authors. All posts exceed 100,000 captured views; 22 exceed one million. It contains three scored image pairs plus one image practice pair. It remains an interaction pilot, not a registered held-out test.

The campaign freezes **one primary run per model: 68 requests total**, including 8 unscored practice calls and 60 scored calls. It has no automatic retries, repeats, setting tuning, fallback models, or mirror runs. All models receive identical visible stimuli and captured image bytes. Jev uses a separately versioned typed-choice protocol.

The model/provider configs are under `evals/configs/gateway/`. Every language model explicitly requests `reasoning.effort: none`; Jev uses its native decision API without a thinking parameter. An exact catalog snapshot, per-model provider endpoints, and primary-document policy review are under `evals/fixtures/gateway/`. Preflight checks their hashes, image support, declared off setting, and reviewed eligibility. Each config pins one provider endpoint to prevent automatic provider failover. No model fallbacks or virtual models are configured.

## Run mock software verification

```sh
python3 -m evals run --plan evals/runs/no-thinking-campaign/direct-primary-plan.json --config evals/configs/mock.json --out evals/runs/mock-direct
python3 -m evals score --run evals/runs/mock-direct --bank evals/fixtures/cross-author-v0.4.0/question-bank.server.json --out evals/runs/mock-direct-score.private
python3 -m evals export --run evals/runs/mock-direct --score evals/runs/mock-direct-score.private --out evals/runs/mock-direct-export.private
```

The mixed-failure mock deliberately returns synthetic choices, explanations, refusals, timeouts and HTTP errors. Its scores are software fixtures, never model ability. `participant_kind=mock`/`is_mock=true` persist throughout, and `eval_public_run_aggregates` excludes them. Existing output paths are never overwritten.

## Real Gateway execution

Eric authorized the intended comparison without a spending cap. No Gateway key is currently configured in this chat's process environment, and no paid model requests have run. Set `AI_GATEWAY_API_KEY` locally through the environment or a secret manager; never paste it into chat, commit it, or place it in a config. The scripts do not automatically load `.env` files or use Codex sign-in credentials.

Once the key is available, this explicit command executes the bounded comparison:

```sh
python3 -m evals campaign --manifest evals/runs/no-thinking-campaign/campaign.json --out evals/runs/CHOOSE_NEW_RUN_DIRECTORY --allow-paid
```

That command can incur charges. Preflight validates local contracts; live provider access/compatibility is not yet tested. A 128-token output limit bounds each language model's generated output; Jev's typed decision endpoint has no output-token parameter, recorded as `max_output_tokens: 0` in its config. Socket I/O timeout is 30 seconds. It is not a total generation deadline or an equivalent of the human's six-second look. Failed requests may still incur costs. A rerun needs a new output directory and must be disclosed.

The adapters use documented Gateway [OpenResponses](https://vercel.com/docs/ai-gateway/sdks-and-apis/openresponses) and [OpenAI-compatible Decisions](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-decisions) HTTP APIs with `AI_GATEWAY_API_KEY`; no provider SDK dependency is needed. Direct OpenAI and mock adapters remain available. HTTP redirects are disabled and authentication headers are never persisted. Provider-returned model IDs, Gateway routing, generation IDs, usage and reported cost are stored when available. Reported cost is distinct from an independently reconciled bill; unknown values remain null.

## Visible inputs and captured bytes

`prepare` only reads client stimuli and frozen assets. `run` has no bank argument and never opens an answer key. Inference receives the versioned prompt, A/B visible text and author name/handle, side-specific image reference labels, and original PNG/JPEG bytes as inline base64. **No post/item IDs, source/media/avatar URLs, local filenames, view counts, follower counts, engagement, matching ratios, editorial alt captions, seeds or answer labels cross the adapter boundary.** Exact `displayText` is used because original source `text` may contain an image's t.co link that the human UI omits.

Attached image hashes must reconcile to the frozen data-owned client/server exports. Avatars are captured once from that dataset's public avatar URLs without model calls. Their private manifest binds capture to the source stimuli byte hash. The frozen fixture stores those bytes, SHA-256, MIME type and dimensions; the self-contained plan embeds them unchanged. A missing, changed or mismatched asset fails preparation instead of reducing the item to text.

For a new data export, capture avatars explicitly before offline preparation:

```sh
python3 -m evals capture-avatars --stimuli outputs/system-1-bench-data/stimuli.client.json --out evals/runs/avatar-capture
python3 -m evals prepare --stimuli outputs/system-1-bench-data/stimuli.client.json --avatar-manifest evals/runs/avatar-capture/avatar-manifest.private.json --seed pilot-cohort-001 --out evals/runs/new-primary-plan.json
```

`capture-avatars` performs free image downloads only; it never invokes a model. `prepare` and `run` never fetch remote image URLs. Main-chat integration must serve these **same frozen avatar and attached image bytes** to a matched human cohort. Original human avatar URLs alone cannot establish byte identity. The data-owned fixture and avatar manifest provide the source mapping; do not publish server labels.

## Protocol, scoring and storage

Current record schema: `2.1.0`; benchmark version: `0.3.0-pilot`; dataset: `0.4.0`. Language protocol: `direct-ab-cross-author-image-v3`; Jev typed-choice protocol: `choice-cross-author-image-v2`. See [PROTOCOL.md](PROTOCOL.md).

Model calls are independent and label-free, including two unscored practice calls. Humans receive educational feedback; models receive none. This difference is explicit. Strict direct parsing accepts only uppercase A or B after surrounding whitespace. Jev's declared `winner.choice` is parsed directly, never repaired by probability argmax. All planned scored items stay in the denominator, including invalid/refused/incomplete/error/timeout/unrun items. The first attempt is primary; optional manually configured transport retries remain diagnostics and cannot rescue it. Real executions reject `low`/`minimal` settings before constructing an adapter. Unexpected positive reported reasoning tokens are protocol violations and earn no credit.

Outcome keys enter only in `score`, which verifies versions, post IDs, visible text, different source authors, at least 100,000 captured views per post, and attached-image hashes before joining labels. The selection floor is never included in adapter inputs. Raw attempt journals, timestamps, side assignments, code/protocol/config/dataset/content/journal hashes, responses, errors, usage and latency remain private. Wilson intervals are conditional IID references; the old one-author bootstrap is disabled for cross-author pairs, which have two overlapping author memberships. Both author hashes are retained for future dependency-aware analysis. No human percentile or validated ranking is inferred.

`schema.sql` remains SQLite/D1 compatible with private `eval_runs`, `eval_answers`, `eval_attempts` and a derived per-run public aggregate view. Exported D1 records contain image hashes/metadata; exact image bytes stay in the raw run bundle and frozen fixture rather than being repeated as large SQL strings. Mock and incomplete runs are excluded from the view. Keep participant kind, dataset, benchmark, protocol, config and variant explicit, and never combine Jev/direct or mirror/primary cohorts implicitly. Server-side correctness must not be accepted from a browser.

## Baseline and review artifacts

The historical same-author `0.3.0` protocol remains reproducible with 3s+2s timing and unchanged hashes, while paid execution is blocked. The original author-hidden `0.1.1` baseline remains reproducible through `legacy_core.py` and tracked `evals/fixtures/text-v0.1.1/`; its prompt, side rule and content hash are unchanged. Original local outputs and a full original harness snapshot were preserved under `outputs/system-1-bench-evals/`.

Current review outputs are under `outputs/system-1-bench-evals/cross-author-v0.4.0/`; these are ignored by Git. Private scored/exported examples contain labels/raw responses and must never be served as static assets. The tracked fixtures contain necessary source data, not API secrets or run journals. No new human cohort, paid model results, leaderboard deployment, D1 provisioning, or DNS change has been made here.

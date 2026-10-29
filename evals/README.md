# System 1 Bench evaluations

Python 3.11+, standard library only. Run from `/Users/ericliu/Documents/ChatGPT/sys1bench`. The `0.5.0` task asks which English X post received more captured cumulative **impressions**. Authors, handles, avatars and attached images are visible; all engagement counts are hidden before the answer. Humans have **one 15-second window to view and choose while both posts remain visible**, then see replies, reposts, likes and impressions inside both cards for 2.5 seconds. Feedback follows every answered or timed-out round, including scored questions. Two unscored educational practices precede 15 scored pairs; each pair uses different authors.

Eric requires **thinking/reasoning disabled**, including no `low` or `minimal`. The four approved models and their selection rationale remain in [MODEL_SELECTION.md](MODEL_SELECTION.md). Gemini 2.5 and Llama 4 remain removed. Mandatory-thinking versions are ineligible; execution never substitutes another model automatically.

**Current release:** the real audited `0.5.0` bank is frozen under `evals/fixtures/cross-author-v0.5.0/`, copied byte-for-byte from the data release. Its bank hash matches main's integrated bank. Historical `0.4.1`, `0.4.0`, `0.3.0` and `0.1.1` fixtures/protocols remain reproducible and cannot launch paid calls.

## Verify and prepare offline

```sh
python3 -m unittest discover -s evals/tests -v
python3 -m evals prepare-campaign --out evals/runs/no-thinking-campaign-v05
python3 -m evals campaign-preflight --manifest evals/runs/no-thinking-campaign-v05/campaign.json
```

Preparation uses tracked `evals/fixtures/cross-author-v0.5.0/` and four exact Gateway configs. It makes zero network/model calls. CI uses tracked fixtures and needs no `outputs/`, API keys, packages or avatar downloads. The bank has 34 distinct posts/authors, eight attached images, 26 posts at or above one million impressions, and three scored posts at or above ten million. Captured impressions range from 113,216 to 18,951,622, with median 1,611,190. These outcome-selection statistics never enter inference. The campaign is **one primary run per model: 68 requests total**, including 8 unscored practice calls and 60 scored calls. There are no automatic retries, repeats, parameter searches, fallback models or mirror runs. All four receive the same visible content and captured image bytes. Jev uses a separately versioned typed-choice protocol.

Every language request explicitly sends `reasoning.effort: none`. Native Jev decisions have no thinking parameter. Saved catalog/endpoints and primary-document eligibility checks remain under `evals/fixtures/gateway/`. Each config pins one provider endpoint with no provider failover. A generic catalog off flag alone is insufficient; primary-document policy review must also approve that exact model.

## Mock verification and real execution

```sh
python3 -m evals run --plan evals/runs/no-thinking-campaign-v05/direct-primary-plan.json --config evals/configs/mock.json --out evals/runs/mock-v05
python3 -m evals score --run evals/runs/mock-v05 --bank evals/fixtures/cross-author-v0.5.0/question-bank.server.json --out evals/runs/mock-v05-score.private
python3 -m evals export --run evals/runs/mock-v05 --score evals/runs/mock-v05-score.private --out evals/runs/mock-v05-export.private
```

Mock choices, failures and scores are synthetic software fixtures, never model ability. `participant_kind=mock` and `is_mock=true` persist throughout; public aggregate rows exclude mocks and incomplete runs. Existing output paths are never overwritten.

Eric authorized the intended real comparison without a spending cap. No paid requests have run, and the local process lacks `AI_GATEWAY_API_KEY`. Keep the key in a local environment or secret manager; never paste it into chat or commit it. The harness does not load `.env` files or use Codex sign-in credentials.

With the frozen bank and a local key available, real execution requires:

```sh
python3 -m evals campaign --manifest evals/runs/no-thinking-campaign-v05/campaign.json --out evals/runs/CHOOSE_NEW_RUN_DIRECTORY --allow-paid
```

Preflight is local only; live provider access/compatibility is untested. Campaign preflight validates the private bank's version, timing, metric completeness and trusted label join before any requests. The model adapter never receives that bank or the computed labels. Output-token cap remains 128 for language models; Jev has no output-token parameter, recorded as zero. The 30-second socket I/O timeout is a transport control, independent of the human's 15-second visible-choice window. Failed calls can incur charges. Reruns need new IDs/directories and a disclosed reason.

Adapters use Gateway [OpenResponses](https://vercel.com/docs/ai-gateway/sdks-and-apis/openresponses) and [Decisions](https://vercel.com/docs/ai-gateway/sdks-and-apis/openai-decisions). HTTP redirects are disabled. Authentication headers are not saved. Requested/returned model IDs, routing, generation IDs, token usage and reported costs are recorded when returned; unknown cost remains null, distinct from a reconciled bill.

## Outcome-free inference and human feedback

`prepare` reads only initial client stimuli and frozen assets; `run` has no bank argument. Adapters receive the exact versioned prompt, A/B `displayText`, author name/handle, image reference labels and original captured PNG/JPEG bytes. No item/post IDs, source/media/avatar URLs, paths, follower counts, replies, reposts, likes, impression counts, ratios, editorial alt captions, seeds or labels cross the adapter boundary. Server data with engagement fields is rejected as client input. Images must be checked upstream for visible engagement leaks too.

Humans receive engagement feedback after every round. Model calls remain independent and label-free, including two unscored practices; they receive no reveal and no previous-question history. The protocol and scored summary explicitly record these **different feedback conditions**. Do not describe this as a fully matched human/model learning or exposure experiment. Introducing model feedback/history requires a separate protocol.

Freeze avatars explicitly before preparing new data, or use data-owned captured assets:

```sh
python3 -m evals capture-avatars --stimuli outputs/system-1-bench-data/stimuli.client.json --out evals/runs/avatar-capture-v05
python3 -m evals prepare --stimuli outputs/system-1-bench-data/stimuli.client.json --avatar-manifest evals/runs/avatar-capture-v05/avatar-manifest.private.json --seed pilot-cohort-001 --out evals/runs/primary-v05.json
```

Capture downloads free public images only, never model calls. Preparation and inference never download assets. A missing/tampered asset fails closed. Serve these same frozen avatar and attachment bytes to humans; remote URLs alone cannot establish byte identity. Provider-specific image preprocessing and human perception still differ.

## Protocol, scoring and storage

Record schema `2.2.0`; harness `2.2.0`; benchmark `0.4.0-pilot`; dataset `0.5.0`; human protocol `human-15s-visible-feedback-cross-author-education2-v4`. Model protocols: `direct-ab-cross-author-impressions-v5` / `choice-cross-author-impressions-v4`. See [PROTOCOL.md](PROTOCOL.md).

Trusted scoring uses `engagement.impressions`, not likes, reposts, replies or a generic count fallback. Four engagement metrics must be real nonnegative integers; impressions must be positive, and the provider `views` alias must agree if present. Missing values never become zero. Reposts mean source `retweetCount`, without adding quote counts. Versioned bank timing, distinct authors, captured-image hashes and the 100,000-impression selection floor are verified before labels join. The data contract retains the historical `cumulative_snapshot_views` source enum, recorded separately from the evaluation target; this does not enable a fallback to `views`. Source field `viewCount` is reported as impressions per the data contract; these are cumulative snapshots, not unique people or fixed-age outcomes.

First-attempt accuracy divides by all 15 planned scored pairs. Practice is excluded. Invalid/refused/incomplete/error/timeout/unrun and protocol violations count as incorrect. Direct output accepts only uppercase A/B after surrounding whitespace; native Jev parses its declared choice field, never a probability argmax. Positive reported reasoning tokens invalidate a response. Diagnostic retries cannot rescue the first attempt.

Private journals and summaries record timestamps, side assignment, code/config/protocol/dataset/plan/content/bank hashes, raw replies, errors, usage, cost and latency. Current summaries also name the impression target, human timing, feedback conditions and comparison limits. Wilson intervals are conditional IID references. The historical one-author bootstrap remains disabled for cross-author pairs; both author memberships are retained. A curated pilot with previous exposure and no registered holdout does not establish population rankings or human percentiles.

`schema.sql` and private JSONL/SQL exports remain SQLite/D1 compatible. D1 stores image metadata/hashes; exact bytes stay in the private journal and frozen fixture. Keep participant kind, dataset, benchmark, protocol, config and side variant explicit. Server-side correctness cannot come from browser claims. Human engagement reveals must occur only after an answer/timeout; keep unrevealed labels and raw journals private.

## Historical preservation

`0.4.1` remains 15s look / 5s hidden choice; `0.4.0` remains 6s/4s; `0.3.0` remains same-author 3s/2s; `0.1.1` remains anonymous text. Their original fixtures, prompts and hashes are unchanged. They replay/score offline but cannot launch paid calls. Do not combine these cohorts with the visible-choice, feedback-after-every-round `0.5.0` protocol.

Review outputs belong under `outputs/system-1-bench-evals/` and stay ignored by Git. Never publish private banks, scored SQL or raw attempt journals as static assets. Main chat owns app integration, deployment and production result ingestion.

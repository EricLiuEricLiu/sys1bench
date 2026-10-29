# Real no-thinking evaluation records

The four approved models completed the frozen 0.6.0 impression-prediction pilot. These are actual native HTTPS calls through Vercel AI Gateway, with original request/reply journals, source snapshots and trusted offline scoring. Model requests contained no engagement counts, labels or earlier-round feedback.

| Exact requested Gateway model | Correct | Accuracy | Invalid/unanswered | Run ID | Completed (Los Angeles) |
| --- | --- | --- | --- | --- | --- |
| anthropic/claude-opus-5 | 11/15 | 73.3% | 0 | 1e03f7ea-8e10-4a69-81a6-b160d50825cb | 2026-10-28 18:48 PDT |
| openai/gpt-6-sol | 9/15 | 60.0% | 0 | 7b4282f6-d685-436d-a75f-9157fa6c8719 | 2026-10-28 18:48 PDT |
| spacexai/grok-4.20-non-reasoning | 7/15 | 46.7% | 1 | 82dcd201-8b22-4ac3-97fe-e75151427060 | 2026-10-28 18:28 PDT |
| typesafe-ai/jev-1.14.0 | 4/15 | 26.7% | 0 | f58dc61f-74f6-4cde-b09e-574c04c84f14 | 2026-10-28 18:47 PDT |

Every row uses all 15 planned scored pairs. Two practices are excluded. Grok's one invalid output remains incorrect. No mirror, repeated-seed selection or valid-answer retry was performed. This tiny curated pilot does not validate population ranks, human percentiles or superiority over humans.

## Exact cohort and protocols

- Dataset: `0.6.0`; bank SHA-256 `1cb873b4d6da67cb22e0e65582d70c2418a13050cd691b9c05a8df17fe6a744b`.
- Human protocol: `human-15s-visible-feedback-cross-author-education2-v4`, one 15s visible-choice window and 2.5s feedback after every answer/timeout.
- Benchmark: `0.4.0-pilot`; record schema `2.2.0`; harness `2.3.0` with each executed source tree archived and hashed.
- Direct models: `direct-ab-cross-author-impressions-v5`.
- Jev: `choice-cross-author-impressions-v5`, native typed choice with registered avatar preprocessing.
- Model condition: `independent-no-thinking`. Humans receive feedback between rounds; models receive independent label-free calls. This is not a matched learning/exposure condition.

The source bank retains its legacy cumulative_snapshot_views enum and viewCount/ views alias. Trusted labels require engagement.impressions; all four metrics reconcile to the source audit. Thirty post records are retained from 0.5.0, and four new records form two AI-related pairs. All older fixtures/protocols remain untouched.

## Disabled-thinking and actual routing

Language requests explicitly used reasoning.effort none; every language-model response reported zero reasoning tokens. Opus routed to anthropic, Sol to openai and Grok to xai. Jev used the native decision API routed to typesafe-ai, without a reasoning parameter; its API does not report reasoning-token counts, which remain unknown rather than inferred zero. No reported model/provider substitution or positive reasoning-token response was accepted.

The authenticated Gateway response identifies the exact requested model, selected provider and routing. Raw provider metadata/costs remain private. Gateway-reported cost is not a reconciled invoice; Grok's existing BYOK routing can charge the provider directly even where Gateway cost is zero.

## Preserved recovery

The initial campaign sent Grok's 17 requests and one failed Jev practice request, then stopped on HTTP400. Grok's exact requested ID was spacexai/grok-4.20-non-reasoning; Gateway reported the canonical creator prefix xai/grok-4.20-non-reasoning, unchanged originalModelId and native xai provider, with one routing attempt and zero reasoning tokens. The original strict decoder falsely flagged that known alias. The corrected, explicitly allowlisted identity rule replayed those same raw responses offline. No Grok request was repeated and its invalid answer was not repaired.

Jev's first request failed because captured 48px avatars were below its documented 280px image minimum. Its documented recovery repeated each decoded source pixel into a 6x6 block and submitted a 288px PNG. This adds no detail, crop, sharpening or interpolation; original source files, human cards, other-model bytes and attachment bytes stay unchanged. The native-choice protocol, public inputNotes, registered transform manifest and each request's submitted-image hashes disclose this difference. Pixel round-trip equality was verified with bundled Pillow when the frozen assets were authored; runtime and CI need only the standard library.

Original journals and exact execution source snapshots remain in real-campaign-001. The recovery directory real-campaign-002-recovered preserves Grok's parent hashes/revalidation lineage, the fresh valid Jev run, and the first Opus/Sol runs. Totals: 68 primary requests plus one failed Jev compatibility request = **69 actual HTTP requests**. No valid answer was repeated, selected or tuned.

## Public versus private artifacts

The public export is `outputs/system-1-bench-evals/cross-author-v0.6.0/publication-001/leaderboard.public.json`. SHA-256: `18560ac2a6712cd7692baaac5cdbb930ce0c6b8255df34d984df7232a373d765`.

Its wrapper contains models, datasetVersion, humanProtocol, cohort, bankSha256, condition and comparison disclosures. Each row includes main's requested IDs, correct/total, unanswered, timestamp, run ID and real flag, plus failures, adapter/provider evidence, source hashes and inputNotes. It contains no answer labels, individual choices, request IDs, raw replies, image bytes, local credential paths or credentials. Main owns API/UI integration and deployment; no production DB was modified by this evaluation chat.

The sibling publication manifest, attempts, score files, SQL/JSONL and original/recovery execution bundles are private. Re-exporting runs validates original source archives, raw decoder replay, exact frozen plans/configs, metric labels, complete denominators, routing/model identity, image submission evidence and derived-journal lineage. Mocks, injected adapters, incomplete runs, missing model identity and protocol violations are rejected before any public file is written.

Offline CI command: `python3 -m unittest discover -s evals/tests -v`. Python3.11+ standard library only; no network or real credentials are required. Do not run the paid campaign again just to reproduce a public export.

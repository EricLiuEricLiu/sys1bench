# Real leaderboard handoff complete

All four real strict no-thinking evaluations are complete on frozen dataset 0.6.0: Opus 11/15, Sol 9/15, Grok 7/15, Jev 4/15. Grok's one invalid answer stays incorrect. The validated public export is outputs/system-1-bench-evals/cross-author-v0.6.0/publication-001/leaderboard.public.json. Main owns API/UI/database publication. See REAL_RUNS.md and outputs/system-1-bench-evals/HANDOFF.md for the exact cohort, hashes, run IDs and source provenance.

Bank SHA-256: 1cb873b4d6da67cb22e0e65582d70c2418a13050cd691b9c05a8df17fe6a744b. Human protocol remains human-15s-visible-feedback-cross-author-education2-v4: one 15s visible-choice window plus 2.5s feedback after every round. Model calls are independent and label-free, so the feedback difference is disclosed. Thirty posts are retained from 0.5.0; four new posts form two AI-related pairs. All source receipt files and earlier frozen datasets remain byte-identical.

Current model protocols: direct-ab-cross-author-impressions-v5 and choice-cross-author-impressions-v5. Record schema 2.2.0; harness 2.3.0; benchmark 0.4.0-pilot. Jev's protocol records API-compatible 6x nearest-neighbor avatar pixel repetition. Original human/direct-model avatars and attached image bytes are unchanged. Its public inputNotes disclose this preprocessing; the exact transform and submitted hashes are private provenance.

The initial Grok creator-prefix decoder false positive was corrected by offline replay of the same authenticated responses, preserving original journals. No successful request was repeated. Jev's failed practice request remains preserved; its documented recovery is separate. There were 68 primary requests plus 1 failed compatibility request, 69 HTTP requests overall. No valid answer retry, selection or tuning occurred.

All 70 offline tests pass. Command: python3 -m unittest discover -s evals/tests -v. Tests/runtime/export are standard-library-only and need no keys, network or outputs directory. Optional regeneration of the already frozen Jev preprocessing PNGs uses Pillow. The actual source files for each real run are archived and hashed. Public export rejects mock/injected/incomplete runs, validates raw reply decoding, model/provider identities, image submission evidence and source/derivation lineage, then recomputes private scores.

AI_GATEWAY_API_KEY was loaded only from ignored .env.local (mode 0600); its value was never printed or committed. Raw replies, error journals, labels and scored SQL remain private. No server/web or production DB edits were made here.

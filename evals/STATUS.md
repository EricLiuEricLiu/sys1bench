# Frozen impressions evaluation checkpoint

Dataset `0.5.0` matches main's integrated bank SHA-256 `621b9d6dcb0589ff87e8e197fd40c4e9cbdcde03999317d4f44465c0d9a6890b`. The audited source bank, initial client, audit, receipt and eight images were copied without modification into `evals/fixtures/cross-author-v0.5.0/`. All 34 avatars are captured and bound to the exact client byte hash. **62 offline tests pass**; no paid model calls occurred.

Human protocol `human-15s-visible-feedback-cross-author-education2-v4`: one 15,000ms window for viewing and choosing while both posts remain visible, then 2,500ms of feedback inside both cards after every answer/timeout, practice and scored. This is a different feedback condition from stateless model calls. Protocol objects and score summaries record the difference explicitly.

Model protocols are `direct-ab-cross-author-impressions-v5` / `choice-cross-author-impressions-v4`. Record schema/harness `2.2.0`; benchmark `0.4.0-pilot`. Both API surfaces target cumulative impressions. Trusted scoring requires all four real integer engagement metrics and labels on `engagement.impressions`; there is no fallback to a generic views count. The source retains its legacy `cumulative_snapshot_views` enum and `viewCount`/views alias, recorded separately from the evaluation target.

The bank has two practice + 15 scored pairs, 34 distinct posts/authors, eight attached images, 26 million-plus posts, and three scored posts above ten million impressions. Minimum 113,216; median 1,611,190; maximum 18,951,622. Twenty-eight posts are retained from 0.4.1 and six are new. Mixed capture ages now extend to 174.92 days. All outcome-selection and prior-exposure limits remain disclosed.

The approved four no-thinking models are unchanged. Gemini 2.5 and Llama 4 remain removed. The current prepared campaign is under `outputs/system-1-bench-evals/cross-author-v0.5.0/ready-campaign/`: one primary run per model, 68 requests, zero automatic retries/mirrors/tuning/fallbacks. No real model result, human percentile or validated ranking has been fabricated. Model socket timeout remains 30 seconds per I/O, independent of human timing.

All 0.4.1 / 0.4.0 / 0.3.0 / 0.1.1 fixture bytes and protocol hashes remain unchanged and replayable/scorable offline. Paid execution rejects them before adapter construction. Public comparisons must preserve dataset/protocol/config/participant/side boundaries and the feedback-condition distinction. Main owns app integration, deployment and production result ingestion; this chat edits only evals and evaluation outputs.

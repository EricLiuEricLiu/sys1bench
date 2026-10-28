# Stable timing-patch evaluation checkpoint

Current dataset `0.4.1` uses 15,000ms viewing plus 5,000ms choice and human protocol `human-15s5s-cross-author-highreach-education2-v3`. The original `0.4.0` source and protocol hashes remain frozen. All posts, pairs, outcomes, captured avatars/images and per-item model requests are identical across the timing patch. **49 offline checks pass**; no paid calls occurred.

Current evaluation protocols are `direct-ab-cross-author-image-v4` and `choice-cross-author-image-v3`; record schema `2.1.0`, benchmark `0.3.1-pilot`, harness `2.1.1`. The four approved model IDs and strict disabled-thinking controls are unchanged. Gemini 2.5 and Llama 4 remain removed. Current paid execution requires dataset 0.4.1 and the new protocol; earlier datasets can only be replayed/scored offline.

The frozen timing patch is under `evals/fixtures/cross-author-v0.4.1/`. It retains 2 practice + 15 scored pairs, 34 distinct posts/authors, 8 attached images and 34 captured avatars. The new audit records timing-patch equivalence and inherits the original saved-source/media review; it does not imply a fresh source query or visual review. Its avatar manifest rebinds the exact original capture bytes to the new client metadata hash.

Current offline campaign: `outputs/system-1-bench-evals/cross-author-v0.4.1/ready-campaign/campaign.json`. Four exact model IDs, 68 primary requests, zero automatic retries/mirrors/tuning/fallbacks. Models receive independent unscored label-free practice calls; humans receive educational feedback. Model transport timeout remains 30 seconds per socket I/O and is independent of human timing. No model result or human percentile has been fabricated.

Main-chat timing coupling: the integrated 0.4.1 bank at app commit 1661887 still has a limitation saying scored rounds use 6,000ms/4,000ms. This eval fixture corrects that one stale sentence to 15,000ms/5,000ms; posts/outcomes are unchanged. Consequently its bank SHA differs until main applies the same copy correction. See the new snapshot provenance and `outputs/system-1-bench-evals/HANDOFF.md` for exact hashes. Do not modify the frozen 0.4.0 bank to fix current copy.

Keep 0.4.0 human cohorts separate from 0.4.1. Serve the same captured avatar/image bytes for human/model stimulus alignment. Selection, mixed-age outcome, author-context, overlapping development posts and no-holdout limitations still apply. This chat edits only evals and evaluation outputs; app deployment and production result ingestion remain with main.

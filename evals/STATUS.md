# Stable cross-author evaluation checkpoint

Current 0.4.0 source and frozen fixtures are ready for review. **46 passing offline checks** cover the new protocol plus historical replay. No model calls. The root app release lock has been released; this evals-only update is ready to commit/push. The previous pushed eval checkpoint is 9078a03.

Current protocols: direct-ab-cross-author-image-v3 and choice-cross-author-image-v2; record schema 2.1.0; benchmark version 0.3.0-pilot. Human exposure/decision timing is 6000ms + 4000ms. Every pair has different source author IDs and handles. Author-visible image inputs and the strict disabled-thinking policy remain unchanged. Trusted scoring enforces at least 100,000 captured views per post without exposing the threshold or labels to inference.

Actual audited data is frozen under evals/fixtures/cross-author-v0.4.0/: 2 practice + 15 scored pairs, 34 unique posts and 34 authors, 8 attached images, 34 captured avatars. Minimum captured views 113,216, median 1,176,533.5, maximum 8,211,513; 22 million-plus posts. The server-bank byte hash is dae4ad6a6f1becfc5489c4c52aa3476004746f44629c3433e854b2d224a65b29.

Old 0.3.0 same-author/3s+2s and 0.1.1 anonymous-text protocols remain replayable with unchanged prompt/content hashes. Paid execution rejects every historical dataset before adapter construction. No model results exist for those banks.

Current offline campaign: outputs/system-1-bench-evals/cross-author-v0.4.0/ready-campaign/campaign.json — 4 unchanged model IDs, exactly 68 primary requests, zero automatic retries/mirrors/tuning/fallbacks. Four mock pipelines verify direct/typed and primary/mirrored paths, never model performance. Local Gateway key remains absent.

The one-author bootstrap is disabled for cross-author pairs. Both author memberships are stored orientation-invariantly; the actual release has no reused authors. Wilson is only a conditional IID reference, not a population claim. Outcome-based selection, visible-author reach/reputation confounds, 3 posts overlapping 0.3.0, and no registered holdout are disclosed.

Main integration action: outputs/system-1-bench-evals/cross-author-v0.4.0/human-avatar-alignment.json maps 34 public avatar URLs to captured files/hashes and suggested local asset paths. Serve those bytes to establish exact avatar identity across human/model cohorts; attached image hashes already match data-owned assets. This chat did not edit web/, server/, data-chat files, deployment or production DB.

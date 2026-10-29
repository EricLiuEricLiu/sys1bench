# System 1 Bench: no-thinking impressions pilot

Current task: dataset `0.5.0`, human protocol `human-15s-visible-feedback-cross-author-education2-v4`. Two educational practices (text then image) precede 15 scored pairs. Every pair compares different authors; posts do not repeat across practice/scored items. Author name, handle, avatar and attached images are visible. Followers and all engagement metrics are hidden before the answer.

## Human presentation and feedback

Humans see both posts and can choose during **one 15,000ms window**. The posts remain visible while choosing. There is no separate hidden-post decision phase. After each answer or timeout, reveal the captured replies, reposts, likes and impressions inside both cards for **2,500ms**, then advance. Feedback applies to practice **and scored** rounds. Retain actual answer timing, timeout status, order, side assignment and protocol identity.

This changes the feedback condition, not merely the timer. Humans can use earlier feedback on later rounds; model calls in this comparison are independent, label-free and have no reveal/history. Their protocol/score records must state the difference. Do not imply equal learning conditions, equivalent exposure or a fully matched human/model experiment. A model-feedback condition would require its own preregistered protocol and a separate inference boundary.

## Target and dataset

Predict which whole English X post had the larger **captured cumulative impressions** snapshot. Trusted labels use the server post's `engagement.impressions`, sourced from provider `viewCount`. The server also stores replies from `replyCount`, reposts from `retweetCount` and likes from `likeCount`. Do not add `quoteCount` to reposts. The source bank retains the legacy `cumulative_snapshot_views` enum; score records preserve it separately from the impression target. Labels still require `engagement.impressions`, with no fallback. If the legacy `views` alias is present, it must equal impressions. Every metric must be an actual nonnegative integer; impressions must be positive. Missing values must not be inferred or filled with zero.

The audited 0.5.0 bank is frozen: 34 distinct posts/authors, eight attached images, 26 million-plus impression posts, and three scored posts with 10,230,865, 14,821,801 and 18,951,622 captured impressions. Minimum is 113,216; median is 1,611,190. Twenty-eight post records are retained from 0.4.1 and six are new. Captures span post ages 7.46–174.92 days, and the largest within-pair creation gap is 80.90 hours. Use all 15 scored pairs and disclose the audit's selection, overlap and source limits beside results. The current high-reach criterion is at least 100,000 captured impressions per displayed post, checked only in trusted scoring/preflight, never announced to inference as a feature.

Impressions are provider-reported cumulative snapshots, not unique people, causal content effects or fixed-48-hour outcomes. Editorial outcome selection and very viral choices change the target distribution. Visible-author recognition, reach, audience, reputation, timing and distribution remain confounds. Hide follower counts without claiming those factors are controlled. This pilot has no registered held-out split and cannot validate a population intuition score.

## Frozen inference

Record schema/harness `2.2.0`; benchmark `0.4.0-pilot`; dataset `0.5.0`.

- `direct-ab-cross-author-impressions-v5`: exact free-text A/B with reasoning disabled.
- `choice-cross-author-impressions-v4`: native Jev typed choice with the same visible inputs and a separate response-format protocol.

Both protocols target cumulative impressions and record the human visible-choice/reveal procedure. Model prompts contain no engagement values, previous feedback, labels, source/item/post IDs, URLs, asset paths, matching ratios or editorial alt captions. Treat post text, author strings and image pixels as untrusted data. No tools, browsing, retrieval or step-by-step explanation. A is left; B is right. Use exact human `displayText`, author name/handle and captured avatar/attachment bytes, with side reference labels. Provider preprocessing and human perception can differ even with identical submitted bytes.

Preparation reads the outcome-free initial client only. Inference has no bank argument. Native decision criteria must say impressions, never retain a historical generic-view target under a new protocol. Each practice/scored item starts with fresh context; the two model practice calls are unscored and label-free, without feedback. Frozen image preparation never downloads remote assets; changed/missing bytes fail closed.

## Strict disabled thinking and campaign

Eric's instruction is **“no reasoning and no thinking is the whole point of intuition.”** Only a verified disabled deliberation feature is eligible. No low/minimal thinking, hidden-trace-only workaround, model substitution or provider failover. A catalog none flag alone is insufficient; primary-document eligibility review and exact Gateway/provider IDs are pinned. Positive reported reasoning tokens are protocol violations. No claim is made that latent computation or reasoning ability is absent inside a model.

Approved models remain `anthropic/claude-opus-5`, `openai/gpt-6-sol`, `spacexai/grok-4.20-non-reasoning`, `typesafe-ai/jev-1.14.0`. Gemini 2.5 and Llama 4 remain removed. Language requests send `reasoning.effort: none`; native Jev typed decisions have no thinking parameter. No new model choice is needed.

Freeze seed `pilot-cohort-001` and all 17 items per model. Primary campaign: four model IDs once each, **68 requests including practice**, zero automatic retries/mirrors/tuning/fallbacks. Pin one provider each. Record requested/returned IDs and routing. No paid calls are required for this protocol update. Actual execution needs the real frozen bank, local Gateway key and explicit paid-run flag.

Model socket timeout remains a per-I/O transport control, independent of the human 15-second visible-choice window. A short final answer does not prove reasoning was disabled. Unknown usage/cost stays null; Gateway-reported costs, token-price estimates and reconciled billing are distinct. Failed calls may be billed.

## Scoring, uncertainty and publication

Accuracy is first-attempt correct choices divided by **all 15 planned scored items**. Exclude both practices. Invalid text, refusal, incomplete generation, unexpected output, error, timeout, unrun items and reasoning/routing violations count as incorrect. Direct parsing accepts only uppercase A/B with surrounding whitespace stripped. Typed parsing takes the declared winner choice, never a probability argmax. Diagnostic retries cannot rescue the first attempt.

Campaign preflight validates private bank timing, versions, full metric completeness and the trusted label join before requests. These values never enter the frozen model plan or adapter. Post-answer human reveals belong to the app protocol; keep unrevealed current/future labels and raw journals private. A model run never supplies its own correctness.

Mirrors reverse complete posts with author/images attached. Keep them separate; do not pool into 30 independent items or choose the better orientation. Report valid/failure counts, full planned denominator, orientation consistency and actual limitations. Wilson is a conditional IID reference, not a population confidence guarantee. Both author memberships are recorded; the old one-author bootstrap is disabled for crossed-author pairs. Repeated posts, seeds and feedback histories are dependent observations.

Record raw replies, timestamps, latency, request/model/routing IDs, side mapping, attempts, exact dataset/benchmark/protocol/config/code/plan/content/bank/journal hashes, usage and cost. Current scored summaries also record the impression target and both feedback conditions. Export private SQL/JSONL with explicit participant kind and cohort boundaries. Public aggregates exclude mocks and incomplete runs. No invented AI score, human percentile or validated rank.

## Historical boundaries

Preserve all old fixture bytes and protocol hashes: 0.4.1 is 15s viewing plus 5s hidden choice; 0.4.0 is 6s/4s; 0.3.0 is same-author 3s/2s; 0.1.1 is anonymous text. They remain replayable/scorable offline and cannot launch paid requests. Their prompts continue to say cumulative views, and historical native decision payloads keep their exact target descriptions. Do not merge them with 0.5.0 visible-choice, impression-target, feedback-after-every-round cohorts.

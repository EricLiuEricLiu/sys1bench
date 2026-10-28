# System 1 Bench: strict no-thinking author/image pilot

This protocol implements Eric's latest direction: visible author name/handle/avatar and attached images; hidden followers and engagement; two total educational practices with feedback for humans, then 15 scored rounds; no repeated posts; English UI; 6-second exposure and 4-second choice; every question compares different authors. His direct instruction here is: **“no reasoning and no thinking is the whole point of intuition.”**

## Dataset and estimand

Predict which whole English X post had the larger saved provider-reported cumulative view snapshot. Different-author pairing is disclosed. The new version is `0.4.0`: two practice pairs and 15 scored pairs with 34 distinct posts and 34 distinct authors. It has one image practice pair, three scored image pairs, and 12 text-only scored pairs. The captured view minimum is 113,216, median 1,176,533.5, maximum 8,211,513; 22 posts exceed one million. Every post must have at least 100,000 provider-reported captured views; disclose this outcome-based selection in reporting, never in model inputs. Captured cumulative outcomes at mixed post ages are not fixed-48-hour outcomes. The bank is keyword-sampled, editorially outcome-selected and not representative; quote status is imperfectly verified and no registered held-out split exists. Keep these limits next to any result.

Freeze every available scored pair; never select a better-performing subset or extrapolate population rankings from this pilot. The historical `0.3.0` same-author/3s+2s protocol and original `0.1.1` text-only baseline remain separate and reproducible. Paid execution rejects them.

## Inference and disabled thinking

Record schema `2.1.0`; benchmark `0.3.0-pilot`; dataset `0.4.0`.

- `direct-ab-cross-author-image-v3`: one exact free-text A/B response from a language model with reasoning explicitly disabled.
- `choice-cross-author-image-v2`: native Jev typed-choice request, with the same visible stimuli and a distinct response-format protocol.

Use the exact embedded prompt/protocol and hashes. Treat post strings, author context and image pixels as untrusted task data, not instructions. No tools, browsing, retrieval, explanations, labels, post/source IDs or hidden engagement are supplied. A means visual left, B means right. Send author name/handle, exact human `displayText`, and original captured avatar/attachment bytes with side reference labels. Alt captions are excluded because they would add model-only context. Provider-specific preprocessing may differ even when submitted bytes are identical; do not claim identical internal representations or equivalent human/model exposure.

**Only disabled reasoning is eligible.** Never coerce unsupported `none` to `minimal`/`low`, hide a thinking trace and call it disabled, or substitute another model automatically. Eligibility uses the current Gateway catalog plus primary-document review; a generic catalog flag alone is insufficient. Always-thinking requested versions are listed in the selection audit. Reject model/provider substitution and reported positive reasoning tokens as protocol violations. Lack of reported reasoning tokens is not proof that a model lacks latent reasoning ability; the operational requirement is no enabled deliberation feature.

Model practice calls are two independent, unscored, label-free calls in text-then-image order. Each subsequent item starts with fresh context and receives no educational feedback. Human onboarding gives feedback, so a matched-stimulus comparison still has that documented procedural difference. A separate training/feedback condition would need a new protocol; it is not injected into this one.

Freeze primary seed `pilot-cohort-001` across models; record actual orientation/order for humans. The SHA-256 seed rule is unchanged from the baseline. The primary campaign runs four distinct model IDs once each: 68 requests including practice, zero retries, zero automatic mirrors or tuning runs. Pin one provider per model and no fallback models. Record requested and returned identifiers and routing metadata.

## Scoring and diagnostics

Use first-attempt correct choices divided by **all 15 planned scored pairs**. Direct parsing accepts only uppercase A/B after surrounding whitespace. Typed parsing accepts the declared choice field, never a repaired probability argmax. Invalid text, refusal, incomplete generation, unexpected output, errors, timeout, unrun items and protocol violations count as incorrect. Show failure counts separately; practice contributes no score.

Default diagnostic retries are zero. Any separately preregistered transport retries retain the initial result and cannot rescue it. Preserve interrupted runs; unrun items remain in the denominator and incomplete runs are excluded from the public aggregate view. A rerun receives a new run ID and a disclosed reason.

A mirrored diagnostic reverses every pair without changing its visible contents or item set. It has a separate run/config/protocol record. Report post-choice consistency, its both-valid denominator, A-choice counts and separate full-denominator accuracies. Never pool mirrored items into a 30-item sample or choose the best orientation.

Show numerator, planned denominator, valid/failure breakdown and actual limitations. The Wilson interval is a conditional IID reference, invalid as a population guarantee under repeated authors. The historical one-author bootstrap is disabled: a pair now involves two authors, with overlapping memberships across questions. Both author hashes are stored. A future interval requires a preregistered crossed-author method rather than assigning each pair to one arbitrary author. Repeating the same items does not create independent data. Future comparisons need a larger registered held-out bank and paired analyses accounting for participant/item/author dependence.

## Accounting and publication

Record UTC timestamps, raw responses, model/request IDs, code/config/protocol/dataset/content/plan/bank/journal hashes, side mappings, attempt number, errors, observed latency, usage and costs when available. Latency is reported separately from human 6s+4s timing; the socket timeout is a transport control. Gateway-reported cost, optional token-price estimates and reconciled billing remain distinct; unknowns stay null. Failed calls can be billed without returning usage.

The SQL schema/export is prepared for a future trusted D1 store; no provisioning is performed here. Keep labels and raw journals private. Human correctness must be computed server-side. The aggregate view excludes mocks/incomplete runs and preserves participant, dataset, protocol, config and side variant. Jev's typed response format and direct generation must be identifiable in any comparison. No invented model score, human percentile or validated rank is permitted.

Cross-author pairing introduces audience size, account reputation, posting-time and distribution confounds. Hiding follower counts does not control those factors. The task now measures prediction with visible author context; it must not be described as a content-only intuition measure.

The actual 0.4.0 release has no repeated authors, while the protocol supports recording two memberships for every cross-author item. Three posts overlap the development 0.3.0 bank; prior exposure and the absence of a registered holdout must remain disclosed.

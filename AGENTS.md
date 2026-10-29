# System 1 Bench

The product name is **System 1 Bench**. The canonical domain is **sys1bench.com**, purchased by Eric and managed in his Cloudflare account.

Use this shared project directory: `/Users/ericliu/Documents/ChatGPT/sys1bench`. Continue all specialist chats here. Do not create separate projects or worktrees for these tasks.

## Product direction

- Benchmark quick intuition across categories, starting with internet instinct (网感).
- Start with English X posts. Eric subsequently requested showing authors and including some image posts in the X data chat; this supersedes the earlier author-hidden direction. Show names, handles, avatars, and attached images; hide follower counts and engagement during questions.
- Initial interaction: two unscored educational practice rounds with feedback, then 15 scored pairs; one 15-second window to view and choose with both posts always visible. Reveal real replies, reposts, likes, and impressions inside both cards for 2.5 seconds after every answer, then advance automatically. Practice posts must be distinct from the scored set.
- Eric's latest experiment compares different authors within every question, using substantially higher-reach posts. The current pilot targets at least 100,000 captured views per displayed post and includes a few much more viral posts. Preserve previous question sets/protocols and keep their results separate.
- Keep visible product copy in English. The landing page should introduce the benchmark generally, with Internet instinct as the first test, a short snippet, and a Start button.
- Keep the UI extremely simple and styles modular, with shared design tokens. The practice cover contains only the title “Practice rounds”, subtitle “Select the post with more impressions.”, a static X-post skeleton, and Start practice with an Enter hint. Omit footers throughout. Center question blocks vertically in the space above the timer.
- During rounds, make the post cards selectable. Keep the question visible; omit Look/Choose status, visible Left/Right labels, and the two engagement/intuition footer hints. Center the prominent timer immediately above the thick countdown bar spanning the viewport bottom.
- Preserve completed result snapshots in D1 and serve a dedicated /results?run=… page, including refresh/back navigation and retry (R shortcut). Hide keyboard shortcut hints on mobile. Review labels the selected post; source links live on the X logos. Preload and decode the next pair during the reveal, then swap on its first visible frame without a loading screen. Retain published media and avatars used by saved results.
- Show the leaderboard directly on results: pin the current result first with its true rank, combine individually numbered anonymous human entries and AI entries, and add an AI tag to each model. Equal scores share competition ranks. Keep all entries for small lists; for long lists retain leaders, viewer neighbors, the tail, and every AI, with explicit omitted-entry counts. Shared rankings retain first completed attempts; repeat results replace only the viewer’s personal comparison row. Describe the model lineup as selected leading models with reasoning disabled, without an unsupported universal “best available” claim.
- The current dataset includes two AI/LLM pairs about coding capability and Silicon Valley AI culture. Do not publicly label individual authors as LARPers.
- Use real collected data and disclose pilot limitations. Do not fabricate view counts, human percentiles, or AI scores.
- LLM comparisons must use a strict no-thinking mode, following Eric's later direction in the evaluations chat. Models with mandatory reasoning are ineligible for that comparison; a short final answer alone does not establish that thinking was disabled. Verify exact Gateway IDs and provider capabilities. `AI_GATEWAY_API_KEY` stays local or in a server secret store.

## Shared work

- UI components chat owns `work/ui-components/`.
- X data chat owns `work/data-search/` and uses the Monid skill.
- Landing page chat owns `work/landing-page/` and uses the requested `elayadesign/ai-design-skills` landing-page skill.
- LLM evaluations chat owns `evals/` and prepares model evaluation protocols, adapters, and reproducible run records. Keep outcome labels out of inference inputs; distinguish mock verification from real model runs.
- The main chat owns integration in `web/` and deployment coordination.
- `work/` contains intermediate material; user-facing deliverables belong in `outputs/`.
- Reuse existing drafts from the original chat folder when migrating. Preserve original files until the migration has been verified.
- Deployment is intended for `https://sys1bench.com`. Coordinate hosting and DNS in the main chat; specialist chats should not create or deploy separate hosted sites.

## Merge preference

When Eric asks to merge a PR, wait for CI to pass, address valid review findings, then use `gh pr merge --admin` if needed. Eric has authorized this workflow; do not ask again solely because GitHub requires an approving review. This does not authorize skipping failing CI.

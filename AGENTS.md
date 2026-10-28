# System 1 Bench

The product name is **System 1 Bench**. The canonical domain is **sys1bench.com**, purchased by Eric and managed in his Cloudflare account.

Use this shared project directory: `/Users/ericliu/Documents/ChatGPT/sys1bench`. Continue all specialist chats here. Do not create separate projects or worktrees for these tasks.

## Product direction

- Benchmark quick intuition across categories, starting with internet instinct (网感).
- Start with English X posts. Eric subsequently requested showing authors and including some image posts in the X data chat; this supersedes the earlier author-hidden direction. Show names, handles, avatars, and attached images; hide follower counts and engagement during questions.
- Initial interaction: two unscored educational practice rounds with feedback, then 15 scored pairs; 3 seconds to view both posts, followed by 2 seconds to choose left or right after the posts disappear. Practice posts must be distinct from the scored set.
- Keep visible product copy in English. The landing page should introduce the benchmark generally, with Internet instinct as the first test, a short snippet, and a Start button.
- Keep the UI extremely simple and styles modular, with shared design tokens.
- Use real collected data and disclose pilot limitations. Do not fabricate view counts, human percentiles, or AI scores.

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

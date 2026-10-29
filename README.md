# System 1 Bench

A minimal website for benchmarking intuition, beginning with internet instinct: predict which of two English X posts received more impressions within 15 seconds.

**Production domain:** [sys1bench.com](https://sys1bench.com), managed in Eric's Cloudflare account.

The pilot is live on Cloudflare Workers, with anonymous first-attempt comparisons at [/leaderboard](https://sys1bench.com/leaderboard) backed by D1.

The format has two unscored educational practice pairs with feedback, followed by 15 scored pairs. Users have one 15-second window to view both posts and select the one with more impressions. Both posts stay visible. After each answer, replies, reposts, likes, and impressions appear inside each card for 2.5 seconds, then the next pair starts. Each pair compares different authors, with at least 100,000 captured views per post in the current pilot. Author context and attached images are shown; engagement is hidden until answering, and follower counts remain hidden. Human and AI comparisons use versioned question sets and protocols. The next pair preloads during feedback, and completed scores have persistent result URLs. Two scored pairs cover AI/LLM ideas and Silicon Valley AI culture.

## Project layout

- `web/` — integrated website source.
- `server/` — Cloudflare Worker API and trusted scoring.
- `data/` — private Worker answer bank, validated model rollups, and captured-avatar mapping.
- `migrations/` — Cloudflare D1 database schema.
- `evals/` — model evaluation harness, protocols, and run-record formats.
- `work/ui-components/` — shared tokens, reusable components, and component gallery drafts.
- `work/landing-page/` — landing-page mockup and design assets.
- `work/data-search/` — Monid collection scripts, question bank, and private provenance.
- `outputs/` — reviewable deliverables.

The initial data is a small pilot using keyword searches and captured cumulative views. It does not yet represent a random sample of X or measure views at a fixed post age. Pilot results should not be presented as a validated ranking of intuition.

## Develop and deploy

Run `npm ci`, `npm run check`, then follow [DEPLOYMENT.md](DEPLOYMENT.md). The site uses Cloudflare Workers with static assets and D1. GitHub Actions verifies source on pushes and pull requests.

# System 1 Bench

A minimal website for benchmarking intuition, beginning with internet instinct: predict which of two English X posts received more views after a brief glimpse.

**Production domain:** [sys1bench.com](https://sys1bench.com), managed in Eric's Cloudflare account.

The pilot is live on Cloudflare Workers, with anonymous first-attempt comparisons at [/leaderboard](https://sys1bench.com/leaderboard) backed by D1.

The format has two unscored educational practice pairs with feedback, followed by 15 scored pairs. Posts appear for 15 seconds, disappear, and users have 5 seconds to choose left or right. Each pair compares different authors, with at least 100,000 captured views per post in the current pilot. Author context and attached images are shown; engagement and follower counts are hidden. Human and AI comparisons use versioned question sets and protocols.

## Project layout

- `web/` — integrated website source.
- `server/` — Cloudflare Worker API and trusted scoring.
- `data/` — private Worker answer bank.
- `migrations/` — Cloudflare D1 database schema.
- `evals/` — model evaluation harness, protocols, and run-record formats.
- `work/ui-components/` — shared tokens, reusable components, and component gallery drafts.
- `work/landing-page/` — landing-page mockup and design assets.
- `work/data-search/` — Monid collection scripts, question bank, and private provenance.
- `outputs/` — reviewable deliverables.

The initial data is a small pilot using keyword searches and captured cumulative views. It does not yet represent a random sample of X or measure views at a fixed post age. Pilot results should not be presented as a validated ranking of intuition.

## Develop and deploy

Run `npm ci`, `npm run check`, then follow [DEPLOYMENT.md](DEPLOYMENT.md). The site uses Cloudflare Workers with static assets and D1. GitHub Actions verifies source on pushes and pull requests.

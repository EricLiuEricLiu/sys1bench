# Cloudflare deployment

Live pilot: **https://sys1bench.com**, in Eric's Personal Cloudflare account. Repository: **https://github.com/EricLiuEricLiu/sys1bench** (private).

The `sys1bench` Worker and D1 database are provisioned. Their account/database IDs and custom domain are already configured in `wrangler.jsonc`.

The `cf` helper isolates this project's Cloudflare login in gitignored `work/cloudflare-config/`, preserving the existing Ditto login.

```sh
npm ci
npm run check
npm run cf -- login --scopes account:read user:read workers:write workers_scripts:write workers_routes:write d1:write zone:read ssl_certs:write
npm run cf -- whoami
```

Sign in to the account that owns `sys1bench.com`, then apply pending migrations and publish:

```sh
npm run cf -- d1 migrations apply sys1bench --remote
npm run deploy
```

Only when bootstrapping a different account or environment, create a separate D1 database with `npm run cf -- d1 create <name>` and update the binding with its returned ID. Do not recreate the existing production database during a routine deployment.

Wrangler deploys the Worker, static assets, and configured custom domain together. Verify `/api/health`, the two practice rounds, a completed test, and `/leaderboard.html` afterward. Migrate the production database before deploying code that requires a new schema.

## Local development

```sh
npm run cf -- d1 migrations apply sys1bench --local
npm run dev
```

The local database is separate from production. Browser QA records must remain local. The current human protocol has one 15-second window with posts visible and selectable, followed by a 2.5-second in-card reveal before automatic advancement.

## Data boundaries

- Only `web/` is packaged as public assets in `dist/`.
- `data/question-bank.server.json` is bundled privately in Worker code. Scores are computed on the server; all four captured engagement counts for the current pair are returned only after that answer or timeout is saved. Future pairs never include engagement values.
- Anonymous answers, timings, and completed result snapshots are stored in D1. Result URLs remain participant-authenticated and readable across later question-set versions. Retain previously published media/avatar files referenced by snapshots. An HttpOnly browser cookie deduplicates first completions for each dataset/protocol. This is a browser-based pilot comparison, not verified unique-human identity.
- Raw collection, provider credentials, evaluation journals, and review artifacts stay out of Git and public assets.
- Validated real model summaries live in data/model-results.server.json and are returned only for the matching dataset/human protocol. The build verifies bank hashes and real-run metadata. Mock verification scores must never be published as model results.

## CI and model credentials

GitHub Actions runs the build, API tests, and a Worker deployment dry run on pushes and PRs. Production deployment currently uses the authenticated local `cf` helper. A future automated deployment should use a dedicated Cloudflare API token scoped to the intended account; do not copy personal OAuth refresh credentials into CI.

LLM evaluations run separately under `evals/` with `AI_GATEWAY_API_KEY` configured locally in the ignored .env.local file. The Worker has an empty .dev.vars to keep evaluation credentials out of its development bindings. Never put that key in browser code, the question bank, or committed configuration.

The results page fetches its participant-authenticated `/api/runs/:id/leaderboard`, scoped to the saved result’s dataset and protocol. Public rankings expose anonymous labels and scores, never human run/participant IDs or answer reviews. Ranking and truncation happen in SQL before returning a bounded list; ties share a rank, and AI rows are always retained. Repeated results are a personal comparison only and do not alter shared first-attempt records.

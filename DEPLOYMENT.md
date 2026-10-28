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

The local database is separate from production. Browser QA records must remain local.

## Data boundaries

- Only `web/` is packaged as public assets in `dist/`.
- `data/question-bank.server.json` is bundled privately in Worker code. Scores are computed on the server; outcomes are returned after a practice answer or a finished test.
- Anonymous answers and timings are stored in D1. An HttpOnly browser cookie deduplicates first completions for each dataset/protocol. This is a browser-based pilot comparison, not verified unique-human identity.
- Raw collection, provider credentials, evaluation journals, and review artifacts stay out of Git and public assets.
- The initial model section stays empty until real matching-protocol runs are imported. Mock verification scores must never be published as model results.

## CI and model credentials

GitHub Actions runs the build, API tests, and a Worker deployment dry run on pushes and PRs. Production deployment currently uses the authenticated local `cf` helper. A future automated deployment should use a dedicated Cloudflare API token scoped to the intended account; do not copy personal OAuth refresh credentials into CI.

LLM evaluations run separately under `evals/` with `AI_GATEWAY_API_KEY` configured locally. Never put that key in browser code, the question bank, or committed configuration.

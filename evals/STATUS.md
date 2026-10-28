# Stable evaluation checkpoint

Source is ready for main-chat commit/push and CI. Current command: `python3 -m unittest discover -s evals/tests -v` — **34 passing checks**, standard library only, no network/API keys required. All test fixtures are under tracked `evals/fixtures/`; tests do not depend on gitignored `outputs/`.

Latest user direction is implemented: actual author/image dataset 0.3.0, two practice pairs (text then image), 15 scored pairs, no repeated posts, exact captured image bytes, visible author context, hidden outcomes/followers/engagement. Record schema 2.0.0; direct protocol direct-ab-author-image-v2; native Jev protocol choice-author-image-v1. Original 0.1.1 text baseline and prompt remain reproducible.

Eric directly approved the strict no-thinking substitutes and requested additional iconic families. Four active configs: Opus 5, GPT-6 Sol, Grok 4.20 Non-Reasoning, Jev 1.14. Eric subsequently removed the older Gemini 2.5 and Llama 4 additions; no newer replacement with verified thinking-off was selected. Five originally requested always-thinking versions are ineligible; none is run at low/minimal. See MODEL_SELECTION.md for exact IDs, rationale and sources. Mistral Large 4 and Gemini 2.5 Pro were excluded after primary-document checks.

`python3 -m evals prepare-campaign --out evals/runs/no-thinking-campaign` prepares a bounded 68-request plan offline. No paid calls have been made; AI_GATEWAY_API_KEY was absent at setup. Eric authorized the intended comparison without a spending cap. No further old-model-choice confirmation is needed.

Human alignment action for main: use the attached image bytes from evals/fixtures/author-image-v0.3.0/media/ and captured avatars from evals/fixtures/author-image-v0.3.0/avatars/. The avatar manifest maps original public URLs to content hashes; human remote-avatar URLs alone do not establish identical bytes. Keep server banks private. This chat has not edited web/, data-chat files, DNS or deployment configuration.

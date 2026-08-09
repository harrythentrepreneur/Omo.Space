# UGC HeyGen Day-1 canary

This directory freezes the first executable contract for the Cognition
marketplace's HeyGen UGC workflow. The authoritative script shape is exactly
`{hook, lines[], cta}`. The canary runs only the OpenAI-compatible script and
captions steps; `render_video=false`, `video` is `null`, and no HeyGen request
can be made by this code.

The account-free test suite uses a stubbed LLM client, so it makes no network
calls and incurs no provider spend. The Modal runner reads `LLM_API_KEY`,
`LLM_BASE_URL`, and `LLM_MODEL` only when a real canary run is invoked. The
model defaults to `deepseek-v4-flash`; secrets are bound only through the named
Modal Secret `cognition-ugc-heygen`.

## Run locally

Python 3.12 dependencies are pinned in `container.yaml` and `modal_app.py`:
`modal==1.5.0`, `fastapi==0.109.0`, `pydantic==2.13.3`, `openai==2.36.0`,
`jsonschema==4.26.0`, and test-only `pytest==8.4.0`.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install \
  'modal==1.5.0' 'fastapi==0.109.0' 'pydantic==2.13.3' \
  'openai==2.36.0' 'jsonschema==4.26.0' 'pytest==8.4.0'
python -m pytest containers/ugc-heygen/tests/
```

No account or environment variable is needed for the tests. After Modal and
the named Secret are configured, serve the protected API surface with:

```bash
modal serve containers/ugc-heygen/modal_app.py
```

`POST /v1/runs` returns `202` with `run_id`, Modal `call_id`, and `result_url`.
`GET /v1/runs/{call_id}` returns `202` while running and the schema-validated
result with HTTP `200` when complete. Modal Proxy Token authentication remains
enabled. Do not publish this LLM-only canary as the finished workflow.

## Day 2 checklist

- Modal account/workspace, staging environment, and `modal setup` authorization
  (or CI service-user tokens).
- Modal Proxy Token ID and secret for the HTTP endpoint.
- OpenAI-compatible LLM key, confirmed base URL, and valid model alias.
- HeyGen account with v3 access and `HEYGEN_API_KEY` for later Day-3 work.
- One commercially approved HeyGen `avatar_id` and `voice_id`, plus proof of
  rights for the avatar, voice, and product material.

The Day-3 provider TODO is deliberately only a documented stub for one
idempotent `POST /v3/videos` followed by `GET /v3/videos/{video_id}` polling.

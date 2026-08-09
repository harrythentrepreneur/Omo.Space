# Claude SEO Skill — pure-LLM canary

This is the cheaper first Modal container for the marketplace listing
`claude-seo-skill-replaces-2k-mo-agency`. It performs one synchronous,
OpenAI-compatible LLM call and returns a schema-validated SEO audit. There is
no background job, polling, media provider, or HeyGen dependency.

`POST /v1/run` validates the request before spending anything and returns HTTP
`200` with:

```json
{
  "status": "completed",
  "result": {
    "findings": [{"issue": "...", "fix": "...", "priority": "high"}],
    "quick_wins": ["..."],
    "summary": "..."
  },
  "usage": {
    "estimated_cost_usd": 0.0002,
    "buyer_run_price_usd": 0.10
  }
}
```

The listing is free to test. Estimated provider cost is about `$0.0002` per
run, while paid buyer runs use the marketplace's `$0.10` minimum price.

## Test locally

The suite is fully offline: it uses an injected LLM stub, makes no network
requests, and needs no account, key, or environment variable.

```bash
python3 -m pytest containers/claude-seo-skill/tests/
```

Runtime and test dependency pins are recorded in `container.yaml`. To serve the
protected endpoint after setup:

```bash
modal serve containers/claude-seo-skill/modal_app.py
```

The Modal endpoint requires Proxy Token authentication. The default provider
base is `https://opencode.ai/zen/go/v1` and the default model is
`deepseek-v4-flash`; `LLM_BASE_URL` and `LLM_MODEL` can override them.

## Day 2 needs

- A Modal account/workspace, `modal setup`, and a Proxy Token for calling the
  protected endpoint.
- One OpenAI-compatible `LLM_API_KEY` stored in the Modal Secret
  `cognition-claude-seo-skill`. Add `LLM_BASE_URL` or `LLM_MODEL` to that Secret
  only when overriding the defaults.

No HeyGen account, key, avatar, voice, external media API, or job-state store is
needed.

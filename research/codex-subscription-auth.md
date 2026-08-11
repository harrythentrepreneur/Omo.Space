# Codex / ChatGPT subscription authentication probe

Date tested: 2026-08-11  
Client inspected: `codex-cli 0.145.0`  
Credential sources: `~/.codex/auth.json` and
`~/.hermes/auth.json` (`providers.openai-codex.tokens`)

No token, account identifier, email, response image, or secret fingerprint is
recorded here. The `OPENAI_API_KEY` in `~/.hermes/.env` was explicitly excluded
because the founder identified it as invalid.

## Result

ChatGPT subscription OAuth works for models, text inference, and image
generation through the Codex backend. It does **not** grant corresponding
public API scopes at `api.openai.com`.

| Probe | Result |
|---|---|
| `GET https://chatgpt.com/backend-api/codex/models?client_version=0.145.0` | HTTP 200; 9 Codex models |
| streamed `POST https://chatgpt.com/backend-api/codex/responses`, tiny text | HTTP 200; terminal `response.completed`; exact output `OK` |
| same Responses route with forced `image_generation` tool | HTTP 200; image-generation lifecycle events and terminal `response.completed` |
| implemented adapter, one low-quality image | decoded 939,667-byte PNG, 1024×1536, passed the pipeline's black-on-white visual gate |
| `GET https://api.openai.com/v1/models` | HTTP 403 |
| `POST https://api.openai.com/v1/responses` | HTTP 401; missing `api.responses.write` |
| `POST https://api.openai.com/v1/images/generations` | HTTP 401; missing `api.model.images.request` |

The direct guessed route
`https://chatgpt.com/backend-api/codex/images/generations` did not produce a
usable response in the bounded probe. The proven image route is the Codex
Responses image tool, not the public Images API and not that guessed route.

## Working request recipe

Load these values at runtime; do not paste them into a command, source file,
fixture, log, or deployment manifest:

- access token: `tokens.access_token`;
- account ID: `tokens.account_id` (the same value is present as the
  `chatgpt_account_id` JWT claim);
- refresh token, if a controlled rotation owner exists:
  `tokens.refresh_token`.

The working headers were:

```http
Authorization: Bearer $OPENAI_CODEX_ACCESS_TOKEN
ChatGPT-Account-Id: $OPENAI_CODEX_ACCOUNT_ID
Content-Type: application/json
Accept: text/event-stream
OpenAI-Beta: responses=experimental
originator: codex_cli_rs
session_id: <new UUID per request>
```

Models are listed at:

```text
GET https://chatgpt.com/backend-api/codex/models?client_version=0.145.0
```

Tiny text inference uses `POST /backend-api/codex/responses` with `stream:true`
and a Codex model returned by that models endpoint. Image generation uses the
same endpoint and authentication with:

```json
{
  "model": "gpt-5.6-terra",
  "input": [{
    "role": "user",
    "content": [{"type": "input_text", "text": "<bounded image prompt>"}]
  }],
  "tools": [{
    "type": "image_generation",
    "quality": "low",
    "size": "1024x1536"
  }],
  "tool_choice": {"type": "image_generation"},
  "parallel_tool_calls": false,
  "store": false,
  "stream": true
}
```

The final base64 image is in the `image_generation_call` item carried by the
`response.output_item.done` SSE event. The adapter also accepts the equivalent
`response.image_generation_call.completed` event shape. For a chained edit,
the last accepted parent is sent as an `input_image` data URL alongside the new
bounded text prompt; a rejected frame never becomes a parent.

## Refresh recipe and deployment limit

The open-source Codex CLI refreshes at
`POST https://auth.openai.com/oauth/token` with JSON:

```json
{
  "client_id": "app_EMoamEEZ73f0CkXaXp7hrann",
  "grant_type": "refresh_token",
  "refresh_token": "$OPENAI_CODEX_REFRESH_TOKEN"
}
```

The client ID is public; the refresh token is a credential. A successful
refresh can rotate the refresh token. The container keeps a returned token only
in memory and cannot persist it back into a Modal Secret after scale-to-zero.
Running the same refresh-token chain concurrently in a developer Codex login
and Modal can also invalidate one side. Therefore subscription OAuth is valid
private staging evidence, but it is not a durable unattended server credential
until one owner serializes refresh and updates the secret atomically.

## OpenCode Go

`OPENCODE_GO_API_KEY` was present as a 67-character `sk-`-prefixed value; its
value was never printed. A tiny
`POST https://opencode.ai/zen/go/v1/chat/completions` using
`deepseek-v4-flash` returned HTTP 200, model `deepseek-v4-flash`, visible output
exactly `OK`, `finish_reason:stop`, and a usage object. The director adapter
remains bounded and falls back to the disclosed deterministic director if
OpenCode Go is absent or fails.

## Honest capability boundary

- Subscription image generation is real and decoded by the checked-in adapter.
- Subscription image Responses currently return no billable USD meter usable
  by Omo settlement. The pipeline preserves the provider identity as
  `openai-codex-subscription`, marks provider costs incomplete, and guarded
  settlement fails closed instead of recording a zero-cost paid success.
- Arbitrary customer audio still needs a valid scoped transcription credential;
  the subscription token lacks the public API scopes used by the current audio
  adapter.
- The bundled `sample-demello-10s` lane remains deterministic and uses its
  checked-in transcript plus the explicitly disclosed procedural renderer.
- The exposed milestone sets `DEMELLO_PROVIDER_LANE_ENABLED=0`; non-bundled
  input fails admission before download or provider spend.
- `paid_traffic_ready` remains `false`.

## Source evidence

The refresh request shape, endpoint, public client identifier, and managed-token
behavior were cross-checked against the open-source Codex CLI implementation:

- <https://github.com/openai/codex/blob/main/codex-rs/login/src/auth/manager.rs>
- <https://github.com/openai/codex/blob/main/codex-rs/app-server/README.md>

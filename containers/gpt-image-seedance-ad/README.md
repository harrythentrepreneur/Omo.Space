# GPT Image + Seedance cinematic product ad

This is Cognition's **in-between Modal workflow** for the catalog concept
`gpt-image-seedance-product-ad`: turn a product description and style hint into
a strict ad concept, then create three product-image variants for a future
15-second cinematic ad.

It sits between the pure-LLM SEO canary and the asynchronous HeyGen workflow.
`POST /v1/run` is synchronous and needs no HeyGen account, avatar, voice,
polling, or job store. Unlike a proxy-only LLM workflow, its `image-gen` step is
a distinct Modal Function configured with `gpu="A10G"`; the API calls that
Function and the image-generation path executes inside its container.

The Day-1 GPU body is deliberately a **MOCK**: it creates deterministic
placeholder URLs instead of pixels, so the full contract can be tested with
zero accounts and zero spend. The code's `TODO(Day 3)` marks where a reviewed
small image model will be loaded and run locally on the GPU. It must not be
replaced by a remote-image-API-only passthrough.

## Contract and cost

Valid calls return HTTP `200`:

```json
{
  "status": "completed",
  "result": {
    "concept": {
      "scene": "...",
      "visual_style": "...",
      "camera": "...",
      "lighting": "...",
      "prompt_text": "..."
    },
    "images": [
      {"url": "https://.../MOCK-....png", "width": 576, "height": 1024, "aspect": "9:16"}
    ]
  },
  "usage": {"estimated_cost_usd": 0.22, "buyer_run_price_usd": 1.10}
}
```

The catalog estimate is `$0.2202`, represented by three `openai_image` and two
`modal_gpu_30s` cost buckets. The public usage contract rounds that to
`$0.22/run`; the buyer price is `$1.10` at 5× markup. Offline tests incur no
provider or Modal cost.

## Test and run

The suite mocks the LLM client and GPU runner and never accesses the network:

```bash
python3 -m pytest containers/gpt-image-seedance-ad/tests/
modal serve containers/gpt-image-seedance-ad/modal_app.py
```

`modal_app.py` includes a small Modal import fallback so schema/parser tests can
import cleanly even when the Modal SDK is absent. A deployed endpoint requires
Modal Proxy Token authentication (`requires_proxy_auth=True`).

## Day 2 needs

- A Modal account/workspace, `modal setup`, a staging environment, and a Proxy
  Token for calling the protected endpoint.
- An OpenAI-compatible `LLM_API_KEY` in the Modal Secret
  `cognition-gpt-image-seedance-ad`; optionally override `LLM_BASE_URL` or
  `LLM_MODEL` (default `deepseek-v4-flash`).
- `OPENAI_API_KEY` is optional for later image-path comparisons and is not used
  by the canary's Modal-GPU path.

No HeyGen account, video polling, avatar, or voice is needed. Day 3 still needs
model selection, weight licensing/review, artifact storage, and actual GPU
latency/cost measurement before this canary is marked live.

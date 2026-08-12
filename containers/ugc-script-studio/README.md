# UGC Script Studio Modal runtime

Generated from `packages/ugc-script-studio/SKILL.md` by `tools/skill-to-modal/compiler.py`.

- Modal is the private execution plane.
- Vercel `POST /api/v1/runs` is the public boundary.
- The Modal endpoint requires Proxy Token authentication.
- Secret values are never generated or committed.

## Verify

```bash
python3 tools/skill-to-modal/compiler.py packages/ugc-script-studio/SKILL.md --output containers/ugc-script-studio/generated
python3 -m pytest containers/ugc-script-studio/tests -q
node --test api/tests/run-handler.test.mjs
modal deploy containers/ugc-script-studio/generated/modal_app.py
```

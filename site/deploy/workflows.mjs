// Cognition — HeyGen UGC workflow (the user's example, made concrete)
//
// What the marketplace runs automatically for a buyer:
//   1. LLM step — write the UGC script from the product + brand voice
//   2. HeyGen step — render the avatar video from the script + avatar choice
//   3. LLM step — generate captions/hook lines for the video
//
// The API price is computed from step costs (cost-model.mjs) and becomes the
// listing's "Run" price. This is the moat: the buyer clicks "Run", we execute
// the whole chain, they get the video.

export const HEYGEN_UGC_WORKFLOW = {
  id: 'ugc-heygen-editor',
  steps: [
    {
      type: 'llm',
      role: 'script',
      model: 'deepseek-v4-flash',
      max_output: 700,
      system: `You are a UGC ad script writer for ecommerce brands.
Return EXACTLY this JSON shape:
{
  "hook": "first 2 seconds, stops the scroll",
  "lines": ["3-5 spoken lines, natural, first-person"],
  "cta": "one call to action"
}
HARD RULES:
- lines must be a flat array of STRINGS.
- hook and cta are plain strings.
- Never nest objects.
- Write in the requested voice: raw, honest, hype, luxury, or funny.
- Never invent claims; only use what the product description supports.
- Output ONLY the JSON object, no markdown fences, no commentary.`,
    },
    {
      type: 'api',
      api: 'heygen_avatar_render',
      qty: 1,
    },
    {
      type: 'api',
      api: 'heygen_voiceover',
      qty: 1,
    },
    {
      type: 'llm',
      role: 'captions',
      model: 'deepseek-v4-flash',
      max_output: 300,
      system: `You write short on-screen captions for short-form UGC videos.
Return EXACTLY this JSON shape:
{
  "captions": ["one short lowercase caption per line of the script"]
}
- captions must be a flat array of STRINGS, same length as the script lines.
- Output ONLY the JSON object, no markdown fences, no commentary.`,
    },
  ],
};

// A simpler one-step workflow (e.g., Listing Copy Engine, Email Flow Copilot):
export const LLM_ONLY_TEMPLATE = {
  steps: [
    {
      type: 'llm',
      role: 'main',
      model: 'deepseek-v4-flash',
      max_output: 600,
      system: '', // filled per skill
    },
  ],
};

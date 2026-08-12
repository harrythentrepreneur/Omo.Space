// LEGACY DATA — 100 workflow definitions retained as SOURCE DATA for future
// marketplace import. NOT a live catalogue; no page renders this file. Do not delete.
// Omo — 100-skill catalog (2026-08-08)
// Each entry is a WORKFLOW we run automatically. runPrice is precomputed from
// cost-model.mjs (LLM_RATES + API_STEP_COSTS, ×1.25 markup, $0.10 floor).
// Shape mirrors the storefront PRODUCTS entries; icon stays null (emoji fallback).
window.COGNITION_CATALOG = [
  {
    slug: 'avatar-ugc-video-studio',
    name: 'Avatar UGC Video Studio',
    emoji: '🎬',
    category: 'content',
    promise: 'Turn a product pitch into a talking-head UGC video with a HeyGen avatar — script, render, and voiceover in one run.',
    maker: '@avatarmaster',
    makerName: 'Río Alvarado',
    email: 'rio@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Paste a product pitch and pick an avatar style. We write the script, render the avatar video, and add a voiceover — you get a finished UGC-style ad without hiring talent or touching an editor.',
    inputs: ['pitch: your product pitch or bullet points', 'avatar_style: friendly · professional · energetic', 'length: 30 or 60 seconds'],
    outputs: ['video — rendered avatar video with voiceover', 'script — the exact lines spoken on camera', 'captions — on-screen text per line'],
    exampleIn: 'ergonomic desk chair, lumbar support, $249 · avatar: friendly · 30s',
    exampleOut: [
      'video: 30s avatar video, friendly presenter, studio background',
      'script: hook "Your back will thank you by Friday." + 4 lines + CTA',
      'captions: ["your back will thank you", "lumbar support is real", "code CHAIR10"]'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'script', model: 'deepseek-v4-flash', max_output: 600, system: `You write UGC ad scripts for avatar videos. Return EXACTLY this JSON shape: {"hook":"first 2 seconds","lines":["3-5 spoken lines, first-person, natural"],"cta":"one call to action"} HARD RULES: - lines is a flat array of STRINGS - never nest objects - never invent claims, only use the pitch - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'heygen_avatar_render', qty: 1 },
        { type: 'api', api: 'heygen_voiceover', qty: 1 },
        { type: 'llm', role: 'captions', model: 'deepseek-v4-flash', max_output: 300, system: `You write on-screen captions for avatar videos. Return EXACTLY this JSON shape: {"captions":["one short lowercase caption per script line"]} HARD RULES: - captions is a flat array of STRINGS, same length as the script - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.15,
    icon: null,
  },
  {
    slug: 'ugc-script-batch',
    name: 'UGC Script Batch',
    emoji: '📦',
    category: 'content',
    promise: 'Five ready-to-film UGC scripts from one product, in five different angles.',
    maker: '@scriptstack',
    makerName: 'Zara Odum',
    email: 'zara@cognition.cv',
    priceOwn: 39,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Get five distinct UGC scripts for the same product — problem/solution, demo, testimonial-style, comparison, and raw honest — so you can A/B test angles without a brainstorm.',
    inputs: ['product: what you sell and its key features', 'audience: who buys it'],
    outputs: ['scripts — 5 angle scripts with hooks and CTAs', 'angle_notes — why each angle works'],
    exampleIn: 'collagen powder, $39/mo, women 35+ wanting skin/join support',
    exampleOut: [
      'angle 1 problem/solution: "I stopped apologizing for my knees…"',
      'angle 2 demo: morning routine, 30s, direct-to-camera',
      'angle 5 raw: "My sister asked what changed. It\\u2019s this."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 800, system: `You are a UGC script factory. Return EXACTLY this JSON shape: {"scripts":[{"angle":"problem_solution|demo|testimonial|comparison|raw","hook":"first 2 seconds","lines":["4-6 spoken lines"],"cta":"one call to action"}]} HARD RULES: - scripts is a flat array, exactly 5 entries - lines must be flat arrays of STRINGS - never invent claims - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'hook-generator',
    name: 'Hook Generator',
    emoji: '🪝',
    category: 'content',
    promise: 'Ten scroll-stopping first-2-seconds hooks for your product ad.',
    maker: '@hookline',
    makerName: 'Miles Tanaka',
    email: 'miles@cognition.cv',
    priceOwn: 19,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'The first two seconds decide whether your ad plays. Feed in your product and get ten hooks across pattern-interrupt, curiosity-gap, pain-agitation, and social-proof styles.',
    inputs: ['product: what you sell', 'pain_point: the problem it solves'],
    outputs: ['hooks — 10 hook lines, labeled by style', 'best_bet — the one most likely to stop the scroll'],
    exampleIn: 'air fryer · pain: cooking takes too long after work',
    exampleOut: [
      'pattern-interrupt: "Dinner in 9 minutes. Yes, really."',
      'pain-agitation: "You spent 40 minutes on this last night. Again."',
      'best_bet: "9-minute dinner" — lead with the number'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write ad hooks. Return EXACTLY this JSON shape: {"hooks":["10 hook lines, one per style: pattern-interrupt, curiosity-gap, pain-agitation, social-proof, bold-claim, question, stat, story-open, direct, command"],"best_bet":"the strongest single hook"} HARD RULES: - hooks is a flat array of STRINGS, exactly 10 - best_bet is a plain string - never invent claims - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'ad-voice-switcher',
    name: 'Ad Voice Switcher',
    emoji: '🎙️',
    category: 'content',
    promise: 'Rewrite one ad script into four brand voices — raw, hype, luxury, funny.',
    maker: '@voicelab',
    makerName: 'Ivy Chen',
    email: 'ivy@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Keep the facts, change the feel. Paste an existing script and get four rewritten versions tuned to different brand voices so you can test which resonates with your audience.',
    inputs: ['script: your existing ad script', 'facts_only: what claims are true'],
    outputs: ['versions — raw · hype · luxury · funny rewrites', 'tone_map — what changed and why'],
    exampleIn: 'script: "This matte lipstick lasts 12 hours" · voice: all 4',
    exampleOut: [
      'raw: "12 hours. I tested it. It\\u2019s real."',
      'luxury: "Twelve hours, uninterrupted. Color that respects your day."',
      'funny: "12 hours. Longer than most of my relationships."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You rewrite ad scripts in different voices. Return EXACTLY this JSON shape: {"versions":{"raw":"rewrite, honest first-person","hype":"rewrite, energetic big","luxury":"rewrite, quiet premium","funny":"rewrite, makes you smile"},"tone_map":["what changed per version"]} HARD RULES: - versions contains exactly 4 plain STRING values - tone_map is a flat array of STRINGS - never change facts, only tone - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'shorts-script-writer',
    name: 'Shorts Script Writer',
    emoji: '📱',
    category: 'content',
    promise: 'A complete YouTube Shorts script with hook, beat points, and caption blocks.',
    maker: '@shortstack',
    makerName: 'Kai Bergström',
    email: 'kai@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Shorts have a different rhythm than long-form. Get a tight under-60-second script with a visual beat per line and the caption text viewers read along with.',
    inputs: ['topic: what the short is about', 'goal: views · followers · sales', 'style: talking-head · b-roll · screen-record'],
    outputs: ['script — beat-by-beat lines with timings', 'captions — caption text per beat', 'cta — end-screen call to action'],
    exampleIn: 'wireless earbuds under $50 · goal: sales · style: talking-head',
    exampleOut: [
      '0-2s hook: "$50 earbuds that beat my $200 pair."',
      'captions: ["$50 earbuds?", "vs my $200 pair", "bass test next"]',
      'cta: "Link in bio — I returned the $200 ones."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write YouTube Shorts scripts. Return EXACTLY this JSON shape: {"script":["beat line with timestamp like 0-2s: line"],"captions":["caption text, one per beat"],"cta":"end-screen call to action"} HARD RULES: - script and captions are flat arrays of STRINGS, same length - cta is a plain string - never invent claims - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'transcript-captioner',
    name: 'Transcript Captioner',
    emoji: '💬',
    category: 'content',
    promise: 'Turn a raw video transcript into punchy on-screen captions that boost watch time.',
    maker: '@captionco',
    makerName: 'Nora Haddad',
    email: 'nora@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste any transcript and get short, keyword-highlighted caption lines — the kind that keep viewers watching with sound off.',
    inputs: ['transcript: the raw spoken text', 'tone: casual · hype · informative'],
    outputs: ['captions — short caption lines, one per beat', 'highlights — the words to bold/emphasize'],
    exampleIn: 'transcript: "so we tried the spray for two weeks and honestly the frizz is gone"',
    exampleOut: [
      'captions: ["we tried it for 2 weeks", "honestly?", "frizz = gone"]',
      'highlights: ["2 weeks", "frizz", "gone"]'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write on-screen captions from transcripts. Return EXACTLY this JSON shape: {"captions":["short caption per beat, lowercase"],"highlights":["words to emphasize"]} HARD RULES: - captions and highlights are flat arrays of STRINGS - keep each caption under 40 characters - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'broll-shot-planner',
    name: 'B-Roll Shot Planner',
    emoji: '🎥',
    category: 'content',
    promise: 'A full b-roll shot list for your script — angles, props, and camera notes per line.',
    maker: '@shotlistpro',
    makerName: 'Owen Fitzpatrick',
    email: 'owen@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your script and get a matching shot list: which lines need close-ups, lifestyle footage, product demos, or text overlays — so any creator can film it in one take.',
    inputs: ['script: your script lines', 'product: what\\u2019s on camera', 'style: studio · lifestyle · outdoor'],
    outputs: ['shots — one shot per script line with camera notes', 'props_list — what to have on set'],
    exampleIn: 'script: "3 lines about the lamp" · product: minimalist desk lamp',
    exampleOut: [
      'shot 1 CU: lamp switch click, soft light flare',
      'shot 2 wide: lamp on walnut desk, laptop glow',
      'props: lamp, notebook, coffee mug, warm bulbs'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You are a director of photography. Return EXACTLY this JSON shape: {"shots":["shot i: angle, action, camera note — one per script line"],"props_list":["props needed"]} HARD RULES: - shots and props_list are flat arrays of STRINGS - never invent props the script contradicts - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'explainer-script-writer',
    name: 'Explainer Script Writer',
    emoji: '📹',
    category: 'content',
    promise: 'A 60-second explainer video script that gets the problem, the fix, and the CTA into one tight arc.',
    maker: '@explainpro',
    makerName: 'Sage Whitfield',
    email: 'sage@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Explainer videos die in the middle. This script forces the classic arc — open the wound, introduce the fix, prove it, close — in under 150 words of voiceover.',
    inputs: ['product: what it does', 'problem: what it fixes', 'audience: who it\\u2019s for'],
    outputs: ['script — voiceover lines with visual notes', 'arc_check — where each beat lands'],
    exampleIn: 'project-management app for freelancers · problem: scattered client work',
    exampleOut: [
      'VO: "Three clients, four tools, zero calm."',
      'visual: split-screen chaos → single dashboard',
      'cta: "Free for solo freelancers. Start today."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write 60-second explainer scripts. Return EXACTLY this JSON shape: {"script":["VO line with visual note, ~10 lines"],"arc_check":["problem|fix|proof|cta — where each lands"]} HARD RULES: - script and arc_check are flat arrays of STRINGS - keep total voiceover under 150 words - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'product-demo-voiceover',
    name: 'Product Demo Voiceover',
    emoji: '🗣️',
    category: 'content',
    promise: 'A narrated product demo — script written, then voiced with ElevenLabs so you can drop it straight into a screen recording.',
    maker: '@voiceninja',
    makerName: 'Luna Park',
    email: 'luna@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Paste your product\\u2019s features and the on-screen steps. We write a tight demo narration and generate a natural voiceover track — no microphone needed.',
    inputs: ['features: what the product does', 'steps: the on-screen flow to narrate', 'voice: warm · upbeat · professional'],
    outputs: ['narration — timed script lines', 'audio — ElevenLabs voiceover track', 'sync_notes — which line goes with which step'],
    exampleIn: 'calendar app · steps: create event → invite → auto-remind',
    exampleOut: [
      'narration: "Create an event in two taps. Invite anyone. Reminders handle the rest."',
      'audio: 28s voiceover, upbeat female voice',
      'sync: line 1 → step 1, line 2 → step 2, line 3 → step 3'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'narration', model: 'deepseek-v4-flash', max_output: 400, system: `You write product demo narrations. Return EXACTLY this JSON shape: {"narration":["one line per on-screen step"],"sync_notes":["which step each line narrates"]} HARD RULES: - narration and sync_notes are flat arrays of STRINGS - plain words, no jargon - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'elevenlabs_tts', qty: 1 }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'ugc-cast-studio',
    name: 'UGC Cast Studio',
    emoji: '🎭',
    category: 'content',
    promise: 'One portrait, four consistent ad-ready variations — outfits, backgrounds, and expressions that keep the same face.',
    maker: '@castlab',
    makerName: 'Finn Gallagher',
    email: 'finn@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Upload one clear portrait and get four generated variations of the same person in different settings — the recurring face that makes UGC ads feel like a real customer.',
    inputs: ['portrait_url: one clear face-forward photo', 'scenes: e.g. kitchen, office, gym, unboxing', 'expression: smiling · neutral · surprised'],
    outputs: ['variations — 4 generated images, same face', 'usage_notes — which scene fits which ad'],
    exampleIn: 'portrait of a woman · scenes: kitchen, office, park, unboxing',
    exampleOut: [
      'variation 1: same face, kitchen counter, morning light, holding a mug',
      'variation 4: same face, unboxing a package, excited expression',
      'note: kitchen + unboxing are the two to test first'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 400, system: `You write image generation briefs. Return EXACTLY this JSON shape: {"briefs":[{"scene":"setting","action":"what the person does","expression":"face expression","lighting":"lighting style"}]} HARD RULES: - briefs is a flat array of exactly 4 entries - keep the SAME person in every brief, only change scene/action - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'openai_image', qty: 4 }
      ]
    },
    runPrice: 0.2,
    icon: null,
  },
  {
    slug: 'product-hero-studio',
    name: 'Product Hero Studio',
    emoji: '🖼️',
    category: 'content',
    promise: 'Four hero product shots — clean background, lifestyle, scale, and detail — generated from your product description.',
    maker: '@heroshots',
    makerName: 'Avery Collins',
    email: 'avery@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Sellers without a studio get four professional product images: a white-background hero, a lifestyle scene, a scale shot with context, and a macro detail — ready for listings and ads.',
    inputs: ['product: description, color, materials', 'style: minimal · warm · bold'],
    outputs: ['images — 4 generated hero shots', 'shot_notes — which image goes where'],
    exampleIn: 'matte black water bottle, 32oz, stainless steel · style: minimal',
    exampleOut: [
      'image 1: white background, centered, soft shadow',
      'image 2: lifestyle — bottle on hiking trail at sunrise',
      'image 4: macro — matte texture close-up'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 400, system: `You write product photography briefs. Return EXACTLY this JSON shape: {"briefs":[{"shot":"hero|lifestyle|scale|detail","background":"description","props":"props if any","angle":"camera angle"}]} HARD RULES: - briefs is a flat array of exactly 4 entries - the product must stay visually identical across shots - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'openai_image', qty: 4 }
      ]
    },
    runPrice: 0.2,
    icon: null,
  },
  {
    slug: 'ad-thumbnail-lab',
    name: 'Ad Thumbnail Lab',
    emoji: '🖌️',
    category: 'content',
    promise: 'Two generated thumbnail concepts plus the copy overlay that makes people click.',
    maker: '@thumblab',
    makerName: 'Rowan Blythe',
    email: 'rowan@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Feed in your video topic and get two AI-generated thumbnail images with a short overlay text recommendation — click-worthy without a designer.',
    inputs: ['topic: what the video is about', 'style: bold · clean · funny'],
    outputs: ['thumbnails — 2 generated images', 'overlay_text — the words to put on top'],
    exampleIn: 'video: "I tested 5 phone stands" · style: bold',
    exampleOut: [
      'thumbnail 1: face reacting + product explosion graphic',
      'thumbnail 2: 5 stands fanned out with number badges',
      'overlay: "5 tested · 1 winner"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 300, system: `You write thumbnail briefs. Return EXACTLY this JSON shape: {"briefs":[{"subject":"main visual","composition":"layout description","text_space":"where the overlay goes"}],"overlay_text":"short punchy words for the thumbnail"} HARD RULES: - briefs is a flat array of exactly 2 entries - overlay_text is a plain string under 20 characters - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'openai_image', qty: 2 }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'video-ad-auditor',
    name: 'Video Ad Auditor',
    emoji: '🔍',
    category: 'content',
    promise: 'A scored audit of your ad script against the patterns that actually convert.',
    maker: '@adjudge',
    makerName: 'Bella Fontaine',
    email: 'bella@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your ad script and get a hook/offer/proof/CTA score, plus the specific rewrites that fix the weakest line. Built on the structure of winning short-form ads.',
    inputs: ['script: your full ad script', 'offer: what you\\u2019re selling and for how much'],
    outputs: ['score — out of 100 with per-section breakdown', 'fixes — line-by-line suggested rewrites'],
    exampleIn: 'script: "Great product. Buy now." · offer: $49 skincare set',
    exampleOut: [
      'score: 34/100 — hook 4, offer 6, proof 8, cta 16',
      'fix: hook has no pattern-interrupt — try "My dermatologist asked what I changed."',
      'fix: add one proof line before the CTA'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You audit ad scripts. Return EXACTLY this JSON shape: {"score":45,"sections":{"hook":10,"offer":10,"proof":10,"cta":15},"fixes":["specific rewrites, one per weakness"]} HARD RULES: - fixes is a flat array of STRINGS - score and sections are plain numbers - never suggest fake claims - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'tiktok-hashtag-finder',
    name: 'TikTok Hashtag Finder',
    emoji: '#️⃣',
    category: 'content',
    promise: 'A curated hashtag stack for your niche — with the mix of sizes that actually gets reach.',
    maker: '@tagstack',
    makerName: 'Enzo Ricci',
    email: 'enzo@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your niche and video topic. Get 20 hashtags in three size tiers — small, mid, big — so your video isn\\u2019t buried or flagged as spam.',
    inputs: ['niche: your content category', 'topic: this specific video\\u2019s topic'],
    outputs: ['hashtags — 20 tags in size tiers', 'strategy — which tier does what'],
    exampleIn: 'niche: skincare · topic: morning routine with serum',
    exampleOut: [
      'small: #skincareroutine, #glassskin',
      'mid: #skincaretips, #morningritual',
      'big: #skincare, #beauty',
      'strategy: 3 small + 2 mid + 1 big, in the caption not comments'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You pick TikTok hashtags. Return EXACTLY this JSON shape: {"hashtags":{"small":["5 low-competition tags"],"mid":["5 medium tags"],"big":["5 high-volume tags"]},"strategy":"how to combine them"} HARD RULES: - each tier is a flat array of STRINGS, exactly 5 - tags must be real, relevant, no spaces - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'pinterest-pin-designer',
    name: 'Pinterest Pin Designer',
    emoji: '📌',
    category: 'content',
    promise: 'Pin titles, descriptions, and image briefs that pull long-tail search traffic to your product.',
    maker: '@pinpro',
    makerName: 'Isla Moreno',
    email: 'isla@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Pinterest is a search engine. Get keyword-led pin copy in the right format (up to 500 chars, front-loaded) plus an image brief for a vertical 2:3 pin.',
    inputs: ['product: what you sell', 'keyword: your main search term'],
    outputs: ['pin_copy — title + 500-char description', 'image_brief — vertical pin visual', 'keywords — 5 supporting terms'],
    exampleIn: 'product: linen curtains · keyword: linen curtains living room',
    exampleOut: [
      'title: "Light-Filtering Linen Curtains for a Cozy Living Room"',
      'image brief: bright window, sheer linen, plant, 2:3 vertical',
      'keywords: blackout linen, natural fiber curtains, farmhouse window'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write Pinterest pin copy. Return EXACTLY this JSON shape: {"title":"keyword-first, under 100 chars","description":"up to 500 chars, front-loaded with keywords","image_brief":"2:3 vertical visual description","keywords":["5 supporting terms"]} HARD RULES: - keywords is a flat array of STRINGS - no emoji spam, no hashtag spam - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'reels-script-writer',
    name: 'Reels Script Writer',
    emoji: '📸',
    category: 'content',
    promise: 'Instagram Reels scripts tuned to save, share, and comment triggers.',
    maker: '@reelsmith',
    makerName: 'Theo Laurent',
    email: 'theo@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Reels convert on engagement. Get a script with an explicit engagement hook (save/share/comment) built into the lines, plus the caption that asks for it.',
    inputs: ['topic: reel subject', 'goal: save · share · comments · sales'],
    outputs: ['script — lines with visual beats', 'caption — post caption with hook question'],
    exampleIn: 'topic: 3 ways to style one scarf · goal: save',
    exampleOut: [
      'line: "Save this for your next outfit crisis."',
      'caption: "Which styling trick are you trying first? 👇"',
      'visual: number badges 1-2-3, quick cuts'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write Instagram Reels scripts. Return EXACTLY this JSON shape: {"script":["line with visual note"],"caption":"post caption that drives the goal","engagement_line":"the line that asks for save/share/comment"} HARD RULES: - script is a flat array of STRINGS - one engagement ask, built in naturally - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'carousel-post-builder',
    name: 'Carousel Post Builder',
    emoji: '🎠',
    category: 'content',
    promise: 'A 6-slide Instagram carousel — headline per slide, body copy, and design direction.',
    maker: '@carouselforge',
    makerName: 'Mae Calloway',
    email: 'mae@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Carousels get 3x the saves of single images. Get a complete 6-slide structure: hook slide, three value slides, proof, and CTA — with copy and visual direction per slide.',
    inputs: ['topic: the idea to teach or sell', 'audience: who it\\u2019s for'],
    outputs: ['slides — headline + body per slide (6)', 'design_direction — visual style per slide'],
    exampleIn: 'topic: how to photograph products with phone · audience: small sellers',
    exampleOut: [
      'slide 1: "Your phone is a studio. Here\\u2019s proof."',
      'slide 3: "Lighting: window light, 3pm, no filter"',
      'slide 6: "Save this — your next listing will thank you."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You build Instagram carousels. Return EXACTLY this JSON shape: {"slides":[{"headline":"short, bold","body":"2-3 sentences","visual":"design direction"}]} HARD RULES: - slides is a flat array of exactly 6 entries - slide 1 is the hook, slide 6 is the CTA/save ask - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'trend-adaptor',
    name: 'Trend Adaptor',
    emoji: '🔥',
    category: 'content',
    promise: 'Adapt your product pitch to the latest trending audio or format without sounding forced.',
    maker: '@trendfitter',
    makerName: 'Jude Mbeki',
    email: 'jude@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste a trending format (POV, green screen, stitch, text-on-screen) and your pitch. Get a natural adaptation that rides the trend instead of cringing into it.',
    inputs: ['trend: the format or audio vibe', 'pitch: your product pitch', 'guardrails: what to never do'],
    outputs: ['adapted_script — trend-native script', 'why_it_works — the hook reasoning'],
    exampleIn: 'trend: POV green screen · pitch: $29 meal kit',
    exampleOut: [
      'script: "POV: you open the box and dinner makes itself."',
      'beat 2: green screen of 6pm decision paralysis',
      'why: the POV frame sells the fantasy, not the features'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You adapt ads to trending formats. Return EXACTLY this JSON shape: {"adapted_script":["lines in the trend format"],"why_it_works":"one sentence","guardrail_check":"one line on what we avoided"} HARD RULES: - adapted_script is a flat array of STRINGS - stay true to the product facts - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'ad-variant-multiplier',
    name: 'Ad Variant Multiplier',
    emoji: '✖️',
    category: 'content',
    promise: 'One ad concept, ten copy variants — different hooks, offers, and CTAs for clean A/B testing.',
    maker: '@variantlab',
    makerName: 'Wren Okafor',
    email: 'wren@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Creative testing needs volume. Paste one concept and get ten variants that change the hook, the offer angle, and the CTA — identical facts, different persuasion.',
    inputs: ['concept: your ad idea', 'facts: what\\u2019s true about the product', 'price: the offer price'],
    outputs: ['variants — 10 full ad copies', 'testing_note — how to split them'],
    exampleIn: 'concept: pet camera · facts: treats dispenser, app, $99',
    exampleOut: [
      'v1: "You\\u2019re at work. The dog is fine. The camera proves it."',
      'v5: "Treats on demand. Guilt off. $99."',
      'testing_note: test v1 vs v5 first — worry vs relief angle'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 800, system: `You write ad variants. Return EXACTLY this JSON shape: {"variants":["10 distinct full ad copies"],"testing_note":"how to split-test them"} HARD RULES: - variants is a flat array of STRINGS, exactly 10 - each variant changes hook OR offer angle OR cta - never invent facts - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'uvp-miner',
    name: 'UVP Miner',
    emoji: '💎',
    category: 'content',
    promise: 'Mine your reviews to find the unique value proposition customers actually repeat.',
    maker: '@uvphunter',
    makerName: 'Otto Lindqvist',
    email: 'otto@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Your customers already told you why they buy. Paste reviews and get the recurring themes, the exact phrases they use, and a one-line UVP you can put on the homepage.',
    inputs: ['reviews: pasted customer reviews', 'product: what you sell'],
    outputs: ['themes — recurring reasons people buy', 'customer_phrases — verbatim-style lines', 'uvp — a one-line unique value proposition'],
    exampleIn: 'reviews of a weighted blanket, ~10 pasted reviews',
    exampleOut: [
      'themes: sleep quality, anxiety relief, weight feel',
      'phrases: "like being hugged", "fall asleep in 10 min"',
      'uvp: "The weighted blanket people describe as a hug — 15 lbs of calm."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You mine reviews for UVPs. Return EXACTLY this JSON shape: {"themes":["recurring buying reasons"],"customer_phrases":["phrases customers repeat"],"uvp":"one line usable on a homepage"} HARD RULES: - themes and customer_phrases are flat arrays of STRINGS - only use what the reviews support - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'creative-brief-writer',
    name: 'Creative Brief Writer',
    emoji: '📋',
    category: 'content',
    promise: 'A one-page creative brief for your designer or agency — insight, angle, and deliverables.',
    maker: '@briefsmith',
    makerName: 'Elia Marchetti',
    email: 'elia@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Vague briefs produce vague work. Feed in the product, audience, and goal — get a structured brief with the core insight, the creative angle, tone, and the exact deliverables.',
    inputs: ['product: what you sell', 'audience: who it\\u2019s for', 'goal: awareness · clicks · sales'],
    outputs: ['brief — full one-page creative brief', 'deliverables — list of assets to produce'],
    exampleIn: 'product: refillable deodorant · audience: eco-conscious 20s · goal: clicks',
    exampleOut: [
      'insight: guilt-free routines beat eco-lectures',
      'angle: "The last plastic deodorant you\\u2019ll buy"',
      'deliverables: 3x 9:16 ads, 1x 30s cutdown, 3 static banners'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write creative briefs. Return EXACTLY this JSON shape: {"insight":"core consumer insight","angle":"the creative direction in one line","tone":"brand tone words","deliverables":["assets with formats and durations"]} HARD RULES: - deliverables is a flat array of STRINGS - insight must trace back to the inputs - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'podcast-shorts-clipper',
    name: 'Podcast Shorts Clipper',
    emoji: '✂️',
    category: 'content',
    promise: 'Find the 5 most clip-worthy moments in your podcast transcript — with titles and hooks.',
    maker: '@clipfinder',
    makerName: 'Rex Armstrong',
    email: 'rex@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste a podcast transcript and get the five moments with standalone value — a hot take, a story, a concrete tip — each with a suggested title and hook line for Shorts/Reels.',
    inputs: ['transcript: the episode text', 'show_topic: what the episode covers'],
    outputs: ['clips — 5 moments with timestamps + titles', 'hook_lines — opener for each clip'],
    exampleIn: 'transcript: 30-min episode on solo founder burnout',
    exampleOut: [
      'clip 1 (12:30): "The day I almost shut the company down"',
      'hook: "I had $400 left and payroll on Friday."',
      'clip 3 (21:05): concrete 3-step boundary system'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You find clip-worthy podcast moments. Return EXACTLY this JSON shape: {"clips":[{"time":"mm:ss","title":"short title","reason":"why it stands alone"}],"hook_lines":["opener for each clip"]} HARD RULES: - clips is a flat array, exactly 5 entries - hook_lines is a flat array of STRINGS - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'live-shopping-script',
    name: 'Live Shopping Script',
    emoji: '🛍️',
    category: 'content',
    promise: 'A timed livestream shopping script with demos, engagement prompts, and offer cadence.',
    maker: '@livestudio',
    makerName: 'Juno Reyes',
    email: 'juno@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Livestreams die without a structure. Get a minute-by-minute script: warm-up, three demo blocks, engagement prompts every 5 minutes, and the offer cadence that drives purchases.',
    inputs: ['products: what you\\u2019re selling', 'length: 30 or 60 minutes', 'offer: the live-only deal'],
    outputs: ['script — timed blocks with talking points', 'engagement_prompts — one per 5-min block'],
    exampleIn: 'skincare set · 30 min · live-only: 20% off + free mask',
    exampleOut: [
      '0-5min warm-up: unbox the set, greet by name',
      '10min first demo: serum on hand, close-up',
      'prompt: "Type MASK if you want the free mask with your order"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 800, system: `You write live shopping scripts. Return EXACTLY this JSON shape: {"script":["minute-range block: what to do and say"],"engagement_prompts":["one interactive ask per 5-minute block"]} HARD RULES: - script and engagement_prompts are flat arrays of STRINGS - each block must have one clear job - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'audio-ad-script',
    name: 'Audio Ad Script',
    emoji: '📻',
    category: 'content',
    promise: 'A podcast/radio ad script — plus a voiced audio track ready to drop into your buy.',
    maker: '@audiocopy',
    makerName: 'Cole Bennett',
    email: 'cole@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Audio ads need spoken rhythm, not written grammar. Get a 30-60s host-read script and a generated voiceover track you can send straight to your podcast buy.',
    inputs: ['offer: what you\\u2019re promoting', 'audience: the show\\u2019s listeners', 'tone: host-style · brand · direct'],
    outputs: ['script — timed host-read lines', 'audio — ElevenLabs voiceover track'],
    exampleIn: 'offer: meal kit $30 off · audience: busy parents · tone: host-style',
    exampleOut: [
      'script: "If dinner is your 6pm villain — this one\\u2019s for you."',
      'script: "30 bucks off, code PANTRY, first box only."',
      'audio: 35s warm host-read track'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'script', model: 'deepseek-v4-flash', max_output: 400, system: `You write audio ad scripts. Return EXACTLY this JSON shape: {"script":["spoken lines, written for the ear"],"code_and_offer":"the offer line with code"} HARD RULES: - script is a flat array of STRINGS - short sentences, natural pauses - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'elevenlabs_tts', qty: 1 }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'youtube-seo-pack',
    name: 'YouTube SEO Pack',
    emoji: '▶️',
    category: 'content',
    promise: 'Title, description, tags, and chapters for your video — built around what people actually search.',
    maker: '@seoforvideo',
    makerName: 'Vera Kimura',
    email: 'vera@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your video topic or transcript. Get a click-tuned title, a keyword-first description with timestamps, and a tag stack — everything you paste into the upload form.',
    inputs: ['topic: video subject', 'keywords: your target search terms'],
    outputs: ['title — click-optimized, under 70 chars', 'description — keyword-first with chapters', 'tags — 10-tag stack'],
    exampleIn: 'topic: how to clean suede sneakers · keywords: clean suede, suede care',
    exampleOut: [
      'title: "How to Clean Suede Sneakers (Without Ruining Them)"',
      'description: "Clean suede the right way\\u2026 0:00 what you need, 1:20 dry brush, 3:00 stains"',
      'tags: suede cleaner, clean suede shoes, sneaker care'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write YouTube SEO metadata. Return EXACTLY this JSON shape: {"title":"under 70 chars, keyword-led","description":"first 2 lines keyword-rich, then chapters with timestamps","tags":["10 tags"]} HARD RULES: - tags is a flat array of STRINGS - never keyword-stuff - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'repurpose-planner',
    name: 'Repurpose Planner',
    emoji: '♻️',
    category: 'content',
    promise: 'One long video becomes a month of shorts, posts, and threads — mapped out.',
    maker: '@repurposer',
    makerName: 'Hugo Van Der Berg',
    email: 'hugo@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Stop filming more, start re-cutting. Paste your long-form transcript and get a repurposing plan: which moments become Shorts, which become a carousel, which become a thread.',
    inputs: ['transcript: your long video text', 'platforms: where you want to publish'],
    outputs: ['plan — moment → platform → format map', 'priority_order — what to cut first'],
    exampleIn: 'transcript: 40-min tutorial · platforms: TikTok, IG, X, LinkedIn',
    exampleOut: [
      'Short #1: the 2-min "aha" at 23:00 → TikTok + Reels',
      'carousel: 5-step recap → IG + LinkedIn',
      'thread: the 3 mistakes section → X',
      'priority: Short #1 first — it stands alone best'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You plan content repurposing. Return EXACTLY this JSON shape: {"plan":[{"moment":"what happens and where","format":"short|carousel|thread|post","platform":"where it goes"}],"priority_order":["what to cut first"]} HARD RULES: - plan is a flat array of entries - priority_order is a flat array of STRINGS - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'ad-fatigue-refresher',
    name: 'Ad Fatigue Refresher',
    emoji: '⚡',
    category: 'content',
    promise: 'New angles for creatives that stopped performing — same product, fresh persuasion.',
    maker: '@freshangle',
    makerName: 'Mica Santos',
    email: 'mica@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'When frequency kills your ads, the fix is a new angle, not a new budget. Paste your current ad and product facts, get five fresh creative angles that reframe the same offer.',
    inputs: ['current_ad: what you\\u2019re running', 'product_facts: what\\u2019s true', 'past_angles: what you already tried'],
    outputs: ['angles — 5 new creative directions', 'hook_each — opening line per angle'],
    exampleIn: 'current: benefit-led demo · facts: dishwasher-safe lunchbox · tried: mom, office',
    exampleOut: [
      'angle: the "meal prep as therapy" reframe',
      'hook: "The 10 minutes a day that keep you sane."',
      'angle: kid-perspective — film from the lunchbox\\u2019s POV'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You find fresh ad angles. Return EXACTLY this JSON shape: {"angles":["5 creative directions that reframe the offer"],"hook_each":["one hook line per angle"]} HARD RULES: - angles and hook_each are flat arrays of STRINGS, same length - avoid the angles already tried - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'video-hook-surgery',
    name: 'Video Hook Surgery',
    emoji: '🩹',
    category: 'content',
    promise: 'Diagnose why your video\\u2019s first 3 seconds fail — and get 3 replacement hooks.',
    maker: '@hooksurgeon',
    makerName: 'Arlo Nguyen',
    email: 'arlo@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Low retention usually means the first seconds are weak. Paste your hook and its context; get a diagnosis plus three rewritten hooks that fix the specific failure mode.',
    inputs: ['current_hook: your first 3 seconds', 'video_topic: what the video is about', 'audience: who it\\u2019s for'],
    outputs: ['diagnosis — why it fails', 'rewrites — 3 replacement hooks'],
    exampleIn: 'hook: "Welcome to my channel\\u2026" · topic: budget meal prep · audience: students',
    exampleOut: [
      'diagnosis: greeting wastes the first beat — no tension',
      'rewrite: "$3 dinners. All week. Here\\u2019s the trick."',
      'rewrite: "Your food budget is lying to you."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You fix video hooks. Return EXACTLY this JSON shape: {"diagnosis":"why the hook fails in one line","rewrites":["3 replacement hooks"]} HARD RULES: - rewrites is a flat array of STRINGS, exactly 3 - each rewrite must stay true to the topic - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'testimonial-script-maker',
    name: 'Testimonial Script Maker',
    emoji: '💌',
    category: 'content',
    promise: 'Turn a written review into a spoken testimonial script your customer can film in one take.',
    maker: '@testimaker',
    makerName: 'Sienna Cole',
    email: 'sienna@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Written reviews sound stiff read aloud. Convert one into a natural first-person script — short sentences, one core claim, a specific detail that makes it believable.',
    inputs: ['review: the customer\\u2019s written words', 'name: first name to use', 'length: 15 or 30 seconds'],
    outputs: ['script — natural spoken lines', 'delivery_tips — how to film it'],
    exampleIn: 'review: "This bag fits my 16-inch laptop and looks expensive" · Maya',
    exampleOut: [
      'script: "I was a tote person. Then this bag…"',
      'script: "16-inch laptop, water bottle, gym stuff — it all fits."',
      'tip: film in daylight, hold the bag up at 0:05'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You turn reviews into testimonial scripts. Return EXACTLY this JSON shape: {"script":["natural first-person spoken lines"],"delivery_tips":["how to film it, one tip per line"]} HARD RULES: - script and delivery_tips are flat arrays of STRINGS - only use what the review actually says - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'before-after-pairer',
    name: 'Before/After Pairer',
    emoji: '🪄',
    category: 'content',
    promise: 'Before/after image briefs that dramatize your product\\u2019s transformation — honestly.',
    maker: '@transformco',
    makerName: 'Dario Petrov',
    email: 'dario@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Before/after content is the highest-converting format in ecom. Get paired image briefs (same framing, same light) plus the honest caption language that avoids ad-review flags.',
    inputs: ['product: what transforms what', 'before_state: the starting condition', 'after_state: the claimed result'],
    outputs: ['briefs — before & after shot descriptions', 'caption — compliant side-by-side caption'],
    exampleIn: 'product: teeth whitening strips · before: stained · after: visibly whiter',
    exampleOut: [
      'before: same angle, same light, neutral face, no retouching claim',
      'after: identical framing, whiter teeth, natural smile',
      'caption: "Results in 14 days. Individual results vary."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write before/after image briefs. Return EXACTLY this JSON shape: {"briefs":[{"shot":"before|after","framing":"identical framing notes","lighting":"same lighting","state":"what the product state is"}],"caption":"compliant side-by-side caption"} HARD RULES: - briefs is a flat array of exactly 2 entries - framing and lighting must match across both - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'ugc-script-localizer',
    name: 'UGC Script Localizer',
    emoji: '🌍',
    category: 'content',
    promise: 'Localize your UGC script for a new market — language, references, and price framing included.',
    maker: '@localvoice',
    makerName: 'Amara Diallo',
    email: 'amara@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Translation is not localization. Get your script rewritten for a target market: natural phrasing, local references, correct pricing framing, and no lost wordplay.',
    inputs: ['script: your original UGC script', 'target_market: country/region', 'language: output language'],
    outputs: ['localized_script — market-native lines', 'localization_notes — what changed and why'],
    exampleIn: 'script: US slang-heavy gym ad · target: Germany · language: German',
    exampleOut: [
      'localized: "Dein Rücken wird es dir danken." (your back will thank you)',
      'note: removed US-specific "swole" slang, kept short-form directness',
      'note: price shown as EUR with local payment framing'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You localize ad scripts. Return EXACTLY this JSON shape: {"localized_script":["lines in the target language, natural and market-native"],"localization_notes":["what changed and why"]} HARD RULES: - both fields are flat arrays of STRINGS - keep the same facts and CTA intent - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'avatar-tutorial-video',
    name: 'Avatar Tutorial Video',
    emoji: '🎓',
    category: 'content',
    promise: 'A HeyGen avatar explains your product — scripted, rendered, and voiced for onboarding or ads.',
    maker: '@tutormatic',
    makerName: 'Kenji Watanabe',
    email: 'kenji@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Tutorial videos at scale, no studio. Give us the steps and audience; we write a teaching script, render a friendly avatar, and voice it — a 60-second explainer, done.',
    inputs: ['steps: what the viewer learns', 'audience: who\\u2019s watching', 'avatar: friendly · expert · casual'],
    outputs: ['video — rendered avatar tutorial', 'script — the teaching lines', 'chapter_marks — where each step starts'],
    exampleIn: 'steps: install, connect, first sync · audience: new users',
    exampleOut: [
      'video: 60s expert avatar tutorial with clear visuals',
      'chapter 1 (0:00): install — "Three clicks, no admin drama."',
      'chapter 3 (0:38): first sync — "Now it\\u2019s automatic."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'script', model: 'deepseek-v4-flash', max_output: 500, system: `You write tutorial video scripts. Return EXACTLY this JSON shape: {"script":["one teaching line per step, friendly and concrete"],"chapter_marks":["step label per line"]} HARD RULES: - script and chapter_marks are flat arrays of STRINGS, same length - no jargon without a plain explanation - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'heygen_avatar_render', qty: 1 },
        { type: 'api', api: 'heygen_voiceover', qty: 1 }
      ]
    },
    runPrice: 0.15,
    icon: null,
  },
  {
    slug: 'bg-swap-studio',
    name: 'Background Swap Studio',
    emoji: '🌅',
    category: 'content',
    promise: 'Three background variations of your product shot — studio, lifestyle, and seasonal.',
    maker: '@bgmagic',
    makerName: 'Lila Novak',
    email: 'lila@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'One good product photo, three ad-ready backgrounds. Describe the product shot and get generated variations that keep the product identical while changing the scene.',
    inputs: ['product_photo: describe the current shot', 'scenes: e.g. studio, kitchen, holiday'],
    outputs: ['variations — 3 generated background swaps', 'fit_notes — which scene for which channel'],
    exampleIn: 'ceramic mug on white desk · scenes: cozy kitchen, autumn leaves, neon studio',
    exampleOut: [
      'variation 1: same mug, warm kitchen counter, steam',
      'variation 3: same mug, neon studio for TikTok ads',
      'fit: kitchen → Instagram, neon → TikTok, autumn → seasonal'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 300, system: `You write background-swap briefs. Return EXACTLY this JSON shape: {"briefs":[{"scene":"new background","mood":"lighting and vibe","channel":"where it fits best"}]} HARD RULES: - briefs is a flat array of exactly 3 entries - the product must stay identical in every brief - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'openai_image', qty: 3 }
      ]
    },
    runPrice: 0.15,
    icon: null,
  },
  {
    slug: 'ad-preview-browser',
    name: 'Ad Preview Browser',
    emoji: '🖥️',
    category: 'content',
    promise: 'See how your landing page or ad actually renders across devices — with a written verdict.',
    maker: '@previewbot',
    makerName: 'Gus Thornton',
    email: 'gus@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'We open your page in a real browser session and describe what a visitor sees — layout, load issues, broken elements — then flag the top three things killing conversion.',
    inputs: ['url: the page to check', 'goal: what the page should make visitors do'],
    outputs: ['page_report — what renders and what breaks', 'top_fixes — 3 conversion-blocking issues'],
    exampleIn: 'url: your product landing page · goal: add to cart',
    exampleOut: [
      'report: hero loads, CTA above the fold, carousel images missing on mobile',
      'fix 1: carousel fallback needed — blank on mobile Safari',
      'fix 3: CTA color matches background on the sale banner'
    ],
    workflow: {
      steps: [
        { type: 'api', api: 'browserbase_session', qty: 1 },
        { type: 'llm', role: 'verdict', model: 'deepseek-v4-flash', max_output: 500, system: `You write page-review verdicts. Return EXACTLY this JSON shape: {"page_report":["what renders, what breaks, what visitors see"],"top_fixes":["3 conversion-blocking issues in priority order"]} HARD RULES: - page_report and top_fixes are flat arrays of STRINGS - only report what the page observation supports - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.13,
    icon: null,
  },
  {
    slug: 'video-style-transfer',
    name: 'Video Style Transfer',
    emoji: '🎨',
    category: 'content',
    promise: 'Re-style your product video — film look, animation, or bold graphic — with two generated style passes.',
    maker: '@styleforge',
    makerName: 'Nadia Haddad',
    email: 'nadia@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Paste a video description and pick a style — cinematic, stop-motion vibe, bold graphic. We generate styled passes via Replicate so you can compare looks before committing.',
    inputs: ['video: describe the footage', 'style: cinematic · graphic · film-grain'],
    outputs: ['styled_passes — 2 generated style versions', 'style_notes — which fits your brand'],
    exampleIn: 'footage: product unboxing on desk · style: cinematic',
    exampleOut: [
      'pass 1: teal-orange grade, shallow depth, slow push-in',
      'pass 2: film grain, 24fps feel, warm skin tones',
      'note: pass 1 matches your premium line; pass 2 for storytelling ads'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 300, system: `You write video style briefs. Return EXACTLY this JSON shape: {"briefs":[{"style":"the chosen look","grade":"color direction","motion":"camera and pacing feel"}],"style_notes":"which style fits which brand context"} HARD RULES: - briefs is a flat array of exactly 2 entries - keep the footage content unchanged - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'replicate_run', qty: 2 }
      ]
    },
    runPrice: 0.15,
    icon: null,
  },
  {
    slug: 'product-3d-studio',
    name: 'Product 3D Studio',
    emoji: '🧊',
    category: 'content',
    promise: 'Four 3D-style product views — orbit, exploded, cutaway, and scene — from a single description.',
    maker: '@threedee',
    makerName: 'Ravi Mehta',
    email: 'ravi@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: '3D-looking product renders lift perceived value on listings. Get four generated views (orbit, exploded parts, cutaway, in-scene) from your product description — no CAD skills.',
    inputs: ['product: description and materials', 'scene: floating · desk · outdoor'],
    outputs: ['views — 4 generated 3D-style images', 'usage_map — which view for which page'],
    exampleIn: 'product: mechanical keyboard, aluminum, RGB · scene: desk',
    exampleOut: [
      'view 1: orbit angle, keycaps visible, RGB glow',
      'view 2: exploded — keys, switches, plate, PCB separated',
      'usage: exploded view on the features section'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 400, system: `You write 3D render briefs. Return EXACTLY this JSON shape: {"briefs":[{"view":"orbit|exploded|cutaway|scene","composition":"what is visible","lighting":"render lighting"}]} HARD RULES: - briefs is a flat array of exactly 4 entries - materials and colors must stay consistent - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'replicate_run', qty: 4 }
      ]
    },
    runPrice: 0.3,
    icon: null,
  },
  {
    slug: 'social-image-pack',
    name: 'Social Image Pack',
    emoji: '🗂️',
    category: 'content',
    promise: 'Six on-brand images for a week of social posts — generated from one product brief.',
    maker: '@packager',
    makerName: 'Tessa Lindgren',
    email: 'tessa@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'A week of posts without a designer: six generated images in a consistent visual language — quote card, product shot, lifestyle, detail, comparison, CTA — plus the caption for each.',
    inputs: ['product: what you sell', 'brand_colors: palette words', 'week_theme: the message of the week'],
    outputs: ['images — 6 generated posts', 'captions — one per image'],
    exampleIn: 'product: matcha powder · colors: green, cream, gold · theme: slow mornings',
    exampleOut: [
      'post 1: quote card "slow mornings" on cream background',
      'post 4: lifestyle — matcha bowl, morning light, book',
      'caption 4: "Your 7am reset, in green. Link in bio."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 500, system: `You write social image briefs. Return EXACTLY this JSON shape: {"briefs":[{"post":"quote|product|lifestyle|detail|comparison|cta","visual":"composition and text space","caption":"matching caption"}]} HARD RULES: - briefs is a flat array of exactly 6 entries - brand colors must repeat across all six - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'openai_image', qty: 6 }
      ]
    },
    runPrice: 0.3,
    icon: null,
  },
  {
    slug: 'multilingual-voiceover',
    name: 'Multilingual Voiceover',
    emoji: '🈯',
    category: 'content',
    promise: 'Your ad script voiced in three languages — ready to localize your video buys.',
    maker: '@polyvoice',
    makerName: 'Yuki Sato',
    email: 'yuki@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Paste your English script and pick three markets. We localize the lines and generate a natural voiceover track for each — no translators or voice actors in the loop.',
    inputs: ['script: your ad lines', 'languages: 3 target languages'],
    outputs: ['localized_lines — script per language', 'audio — 3 voiceover tracks'],
    exampleIn: 'script: "Your back will thank you." · languages: Spanish, German, Japanese',
    exampleOut: [
      'ES: "Tu espalda te lo agradecerá."',
      'DE: "Dein Rücken wird es dir danken."',
      'JP: "背中が喜びます。" — 3 audio tracks ready'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'localize', model: 'deepseek-v4-flash', max_output: 500, system: `You localize ad scripts for voiceover. Return EXACTLY this JSON shape: {"localized_lines":["line per language, natural and spoken-style"]} HARD RULES: - localized_lines is a flat array of STRINGS, one per requested language - keep meaning and CTA intact - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'elevenlabs_tts', qty: 3 }
      ]
    },
    runPrice: 0.11,
    icon: null,
  },
  {
    slug: 'youtube-comment-replier',
    name: 'YouTube Comment Replier',
    emoji: '💬',
    category: 'content',
    promise: 'Friendly, on-voice replies to your YouTube comments — in bulk, without sounding like a bot.',
    maker: '@replysmith',
    makerName: 'Caleb Osei',
    email: 'caleb@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste up to 10 comments and get replies in your channel\\u2019s voice — short, specific, and varied enough that no two replies look templated.',
    inputs: ['comments: paste the comments', 'voice: how you talk to viewers'],
    outputs: ['replies — one per comment, in order'],
    exampleIn: 'comments: "does this work on glass?" "great video" · voice: casual, helpful',
    exampleOut: [
      'reply 1: "Yes — glass is exactly where it shines, I\\u2019ll link the test clip!"',
      'reply 2: "Thanks! The cleaning part at 4:10 is the one people screenshot."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You reply to YouTube comments. Return EXACTLY this JSON shape: {"replies":["one reply per comment, same order as input"]} HARD RULES: - replies is a flat array of STRINGS - vary sentence structure, no two replies alike - match the channel voice, stay specific - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'video-title-ab-tester',
    name: 'Video Title A/B Tester',
    emoji: '🆎',
    category: 'content',
    promise: 'Six A/B title pairs for your video, each with a predicted winner and why.',
    maker: '@titletest',
    makerName: 'Opal Reed',
    email: 'opal@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Titles are the cheapest CTR lever you have. Give us the video topic and audience; get six tested-style title pairs — curiosity vs clarity, question vs statement — with a predicted winner.',
    inputs: ['topic: video subject', 'audience: who searches for it'],
    outputs: ['pairs — 6 A/B title pairs', 'predictions — winner and reasoning per pair'],
    exampleIn: 'topic: protein pancakes · audience: gym beginners',
    exampleOut: [
      'A: "Protein Pancakes in 10 Minutes" vs B: "The Pancake That Made Me Quit Protein Powder"',
      'prediction: B wins — curiosity gap + identity hook',
      'pair 4: question vs number-led — number likely wins'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You design title A/B tests. Return EXACTLY this JSON shape: {"pairs":[{"a":"title A","b":"title B"}],"predictions":["winner and why, one per pair"]} HARD RULES: - pairs is a flat array of exactly 6 entries - predictions is a flat array of STRINGS - titles must stay honest to the content - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'cold-email-sequencer',
    name: 'Cold Email Sequencer',
    emoji: '📧',
    category: 'leads',
    promise: 'A 4-email cold outreach sequence for one prospect type — built to get replies, not deleted.',
    maker: '@sequencelab',
    makerName: 'Nico Ferraro',
    email: 'nico@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste who you\\u2019re selling to and what you sell. Get four emails: a pattern-interrupt opener, a value follow-up, a social-proof nudge, and a clean break-up — each under 120 words.',
    inputs: ['offer: what you sell', 'prospect: who you\\u2019re emailing', 'pain: their likely problem'],
    outputs: ['emails — 4-sequence, ready to send', 'subject_lines — one per email', 'send_notes — timing guidance'],
    exampleIn: 'offer: ecom bookkeeping · prospect: Shopify owners doing their own books',
    exampleOut: [
      'email 1: "Your books are 6 months behind and it\\u2019s costing you sleep."',
      'email 3: "We just saved a candle brand $3k in late fees."',
      'send notes: 48-72h apart, Tuesday-Thursday'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write cold email sequences. Return EXACTLY this JSON shape: {"emails":["4 emails, each under 120 words, with a subject line on the first line prefixed SUBJECT:"],"send_notes":["timing and cadence guidance"]} HARD RULES: - emails and send_notes are flat arrays of STRINGS - no invented testimonials - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'reply-drafter',
    name: 'Reply Drafter',
    emoji: '📨',
    category: 'leads',
    promise: 'Quick, human-sounding drafts for tricky inbox replies — objections, pricing, and scheduling.',
    maker: '@inboxpro',
    makerName: 'Freya Lindholm',
    email: 'freya@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the email you received and your goal — close, reschedule, decline. Get two draft replies with different tones so the message lands the way you intend.',
    inputs: ['incoming: the email to answer', 'goal: close · schedule · push back', 'tone: warm · direct · formal'],
    outputs: ['drafts — 2 reply options', 'note — which tone fits when'],
    exampleIn: 'incoming: "your price is too high" · goal: close · tone: warm',
    exampleOut: [
      'draft A: "Totally fair — most of our clients said that before the first month. Want to see the math?"',
      'draft B: "What would it need to cost for it to be a no-brainer?"',
      'note: A keeps the conversation, B surfaces the real objection'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You draft email replies. Return EXACTLY this JSON shape: {"drafts":["2 reply drafts"],"note":"when to use which"} HARD RULES: - drafts is a flat array of STRINGS, exactly 2 - match the requested tone - never fabricate facts about your business - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'cart-saver-email',
    name: 'Cart Saver Email',
    emoji: '🛒',
    category: 'leads',
    promise: 'An abandoned-cart email that brings buyers back without a desperate discount.',
    maker: '@cartfix',
    makerName: 'Max Ellison',
    email: 'max@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Abandoned carts are the cheapest revenue on the table. Give us the product and cart value; get a three-email recovery flow — nudge, proof, and last chance — with optional discount logic.',
    inputs: ['product: what was left in the cart', 'cart_value: the dollar amount', 'discount: optional offer'],
    outputs: ['emails — 3 recovery emails', 'subject_lines — per email'],
    exampleIn: 'product: leather tote, $180 · discount: none yet',
    exampleOut: [
      'email 1: "Your tote is still holding your spot."',
      'email 3: "Last call — the tan one sells out first."',
      'note: hold the discount for email 3 only'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write abandoned-cart emails. Return EXACTLY this JSON shape: {"emails":["3 emails: nudge, proof, last-chance"],"subject_lines":["one per email"]} HARD RULES: - emails and subject_lines are flat arrays of STRINGS, same length - only use the discount if provided - no guilt-tripping - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'welcome-flow-writer',
    name: 'Welcome Flow Writer',
    emoji: '👋',
    category: 'leads',
    promise: 'A 4-email welcome sequence that turns a new subscriber into a first-time buyer.',
    maker: '@welcomewave',
    makerName: 'Rosie Feldman',
    email: 'rosie@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'The first emails decide your list\\u2019s lifetime value. Get a four-email welcome arc: the story, the promise, the proof, the offer — written for your brand voice.',
    inputs: ['brand: what you sell and your story', 'offer: the welcome incentive'],
    outputs: ['emails — 4-part welcome sequence', 'flow_map — why each email exists'],
    exampleIn: 'brand: artisan coffee roaster · offer: 15% first order',
    exampleOut: [
      'email 1: story — "We roast on Tuesdays. Here\\u2019s why that matters."',
      'email 4: offer — 15% code, 72h window',
      'flow_map: story → trust → proof → offer'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write welcome email sequences. Return EXACTLY this JSON shape: {"emails":["4 emails in arc order: story, promise, proof, offer"],"flow_map":["why each email exists"]} HARD RULES: - emails and flow_map are flat arrays of STRINGS, same length - no fake reviews - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'winback-campaign',
    name: 'Winback Campaign',
    emoji: '🔁',
    category: 'leads',
    promise: 'A 3-email winback flow for customers who stopped buying — friendly, not needy.',
    maker: '@winbackco',
    makerName: 'Elliot Grant',
    email: 'elliot@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Lapsed customers already know you — that\\u2019s the easiest sale you\\u2019ll ever make again. Get three emails: a what\\u2019s-new note, a we-miss-you nudge, and a come-back offer.',
    inputs: ['product: what they bought before', 'days_since: how long they\\u2019ve been gone', 'whats_new: what changed since'],
    outputs: ['emails — 3 winback emails', 'offer_suggestion — what to incentivize with'],
    exampleIn: 'product: subscription skincare · 90 days gone · whats_new: new SPF line',
    exampleOut: [
      'email 1: "Your skin routine\\u2019s been on pause. We added SPF."',
      'email 3: "Come back — 30% on your first refill."',
      'offer: 30% refill beats a flat discount here'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write winback emails. Return EXACTLY this JSON shape: {"emails":["3 emails: whats-new, we-miss-you, offer"],"offer_suggestion":"the incentive that fits"} HARD RULES: - emails is a flat array of STRINGS - warm, not guilt-tripping - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'newsletter-drafter',
    name: 'Newsletter Drafter',
    emoji: '📰',
    category: 'leads',
    promise: 'A full newsletter issue — subject, hook, story, and links — from your raw notes.',
    maker: '@dispatchwriter',
    makerName: 'Hana Kobayashi',
    email: 'hana@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your scattered ideas and links. Get a complete issue: a subject line that gets opens, a personal hook, the body in your voice, and a single clear call to action.',
    inputs: ['notes: your raw ideas and links', 'audience: who reads it', 'voice: how you write'],
    outputs: ['newsletter — full issue draft', 'subject_options — 3 open-worthy subjects'],
    exampleIn: 'notes: 3 tools I liked, one mistake story · audience: indie founders',
    exampleOut: [
      'subject: "I almost paid for the wrong tool (again)"',
      'body: mistake story → the 3 tools, one line each → takeaway',
      'cta: reply with your own tool stack — replies feed next issue'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 800, system: `You draft newsletters. Return EXACTLY this JSON shape: {"newsletter":"full issue: hook, body, one CTA","subject_options":["3 subject lines"]} HARD RULES: - subject_options is a flat array of STRINGS - write in the requested voice - keep links mentioned but don\\u2019t invent URLs - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'press-pitch-writer',
    name: 'Press Pitch Writer',
    emoji: '🗞️',
    category: 'leads',
    promise: 'A journalist-ready pitch with a news hook, not a product announcement.',
    maker: '@presspilot',
    makerName: 'Griffin Walsh',
    email: 'griffin@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Journalists skip product spam. Give us your news and the outlet; get a short pitch built around a real news angle, plus subject line and follow-up lines.',
    inputs: ['news: what\\u2019s actually new', 'outlet: the publication or beat', 'founder: who\\u2019s available to talk'],
    outputs: ['pitch — under 150 words, news-first', 'subject_line — one that gets opened', 'follow_ups — 2 polite nudges'],
    exampleIn: 'news: ecom brand hits carbon-neutral shipping · outlet: retail trade press',
    exampleOut: [
      'pitch: "Retailers are quietly rewiring last-mile logistics. Here\\u2019s the playbook one brand just shipped."',
      'subject: "Carbon-neutral shipping, minus the greenwashing"',
      'follow-up 2: "Happy to share the cost breakdown — it\\u2019s the surprising part."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write press pitches. Return EXACTLY this JSON shape: {"pitch":"under 150 words, news angle first","subject_line":"one line","follow_ups":["2 polite follow-ups"]} HARD RULES: - follow_ups is a flat array of STRINGS - no invented stats - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'influencer-dm-outreach',
    name: 'Influencer DM Outreach',
    emoji: '🤝',
    category: 'leads',
    promise: 'Personal-feeling DM pitches for creator partnerships — short enough to actually get read.',
    maker: '@dmcraft',
    makerName: 'Mia Kowalski',
    email: 'mia@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Creators ignore copy-paste DMs. Give us their niche and your offer; get a short, specific pitch that references why they specifically fit — plus the rate ask.',
    inputs: ['creator: their niche and vibe', 'offer: what you\\u2019re proposing', 'budget: what you can pay'],
    outputs: ['dm — under 80 words, specific', 'rate_ask — how to bring up money'],
    exampleIn: 'creator: 50k skincare TikToker · offer: free product + $300 · budget: $300',
    exampleOut: [
      'dm: "Your vitamin-C video made me re-check my whole routine. Would you try ours and say what you actually think?"',
      'rate: "We budgeted $300 + product. If that\\u2019s far off, tell me your number — no hard feelings."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write influencer outreach DMs. Return EXACTLY this JSON shape: {"dm":"under 80 words, references their specific content","rate_ask":"how to raise budget naturally"} HARD RULES: - dm and rate_ask are plain STRINGS - no generic flattery - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'partnership-proposal',
    name: 'Partnership Proposal',
    emoji: '🤲',
    category: 'leads',
    promise: 'A short partnership email that proposes a concrete win-win, not vague synergies.',
    maker: '@partnernote',
    makerName: 'Leo Marchetti',
    email: 'leo@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Partnership emails fail when they ask for "a chat." Get one that names the exact audience overlap, the concrete offer, and the first step — under 150 words.',
    inputs: ['your_brand: what you offer', 'their_brand: who you\\u2019re pitching', 'idea: the collaboration concept'],
    outputs: ['proposal — one concrete partnership email', 'first_step — the smallest yes to ask for'],
    exampleIn: 'your: subscription coffee · their: ceramic mug brand · idea: bundle + co-branded box',
    exampleOut: [
      'proposal: "Your mugs, our beans, one box — split margin 50/50, tested on 200 customers."',
      'first_step: "Open to a 15-min call Thursday to look at numbers?"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write partnership proposals. Return EXACTLY this JSON shape: {"proposal":"under 150 words, concrete win-win","first_step":"the smallest specific yes"} HARD RULES: - proposal and first_step are plain STRINGS - no vague synergy language - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'referral-program-copy',
    name: 'Referral Program Copy',
    emoji: '🎁',
    category: 'leads',
    promise: 'The full referral loop — invite email, landing page copy, and reward framing.',
    maker: '@referallab',
    makerName: 'Ruby Chen',
    email: 'ruby@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Referrals convert at 10x cold traffic. Get the complete loop written: the invite email, the referral landing copy, and reward framing that makes both sides say yes.',
    inputs: ['product: what you sell', 'reward: what each side gets'],
    outputs: ['invite_email — the ask', 'landing_copy — the referral page', 'reward_lines — framing for both sides'],
    exampleIn: 'product: $60/mo analytics tool · reward: $20 each side',
    exampleOut: [
      'invite: "You use it daily — your friends should too. $20 says so."',
      'landing: "Give $20, get $20. The tool that made your dashboards bearable."',
      'reward framing: "$20 credit, no caps, lands instantly"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write referral program copy. Return EXACTLY this JSON shape: {"invite_email":"the referral ask","landing_copy":"referral page copy","reward_lines":["reward framing for referrer and friend"]} HARD RULES: - reward_lines is a flat array of STRINGS - keep rewards exactly as provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'launch-email-arc',
    name: 'Launch Email Arc',
    emoji: '🚀',
    category: 'leads',
    promise: 'A 5-email product launch arc — tease, reveal, proof, urgency, and close.',
    maker: '@launchwriter',
    makerName: 'Sam Okafor',
    email: 'sam@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'A launch is a story told over days. Get five emails with the right escalation — from teaser to final hours — written for your product and launch offer.',
    inputs: ['product: what you\\u2019re launching', 'launch_offer: the deal', 'launch_date: when it goes live'],
    outputs: ['emails — 5-email arc in order', 'send_schedule — day-by-day plan'],
    exampleIn: 'product: AI meeting notes tool · offer: 50% first 3 months · launch: Friday',
    exampleOut: [
      'email 1 (Mon): tease — "Meetings just got a witness."',
      'email 3 (Wed): proof — beta users saved 6h/week',
      'email 5 (Fri): close — 50% off, ends Sunday'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 800, system: `You write launch email arcs. Return EXACTLY this JSON shape: {"emails":["5 emails: tease, reveal, proof, urgency, close"],"send_schedule":["day and job of each email"]} HARD RULES: - emails and send_schedule are flat arrays of STRINGS, same length - no fake beta stats - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'feedback-request-email',
    name: 'Feedback Request Email',
    emoji: '⭐',
    category: 'leads',
    promise: 'A review-request email that gets 3x more responses than "please leave a review".',
    maker: '@askfirst',
    makerName: 'Clara Voss',
    email: 'clara@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Timing and framing decide review rates. Get an email that asks one specific question first (easy to answer), then routes happy buyers to reviews and unhappy ones to you.',
    inputs: ['product: what they bought', 'review_site: where reviews live'],
    outputs: ['email — the full request', 'split_logic — happy vs unhappy routing'],
    exampleIn: 'product: standing desk · review_site: Trustpilot',
    exampleOut: [
      'email: "One question: does the desk wobble at full height? Reply and win nothing — I just want the truth."',
      'happy path: "If it\\u2019s solid, a 30-second Trustpilot note would help other buyers."',
      'unhappy path: "If not, reply \\u2018wobble\\u2019 and my team fixes it today."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write feedback-request emails. Return EXACTLY this JSON shape: {"email":"the full email","split_logic":["how happy vs unhappy customers are routed"]} HARD RULES: - split_logic is a flat array of STRINGS - one easy question first, review ask second - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'support-reply-copilot',
    name: 'Support Reply Copilot',
    emoji: '🛟',
    category: 'leads',
    promise: 'Draft replies to support tickets that solve the problem and keep the customer warm.',
    maker: '@ticketfix',
    makerName: 'Dave Lindqvist',
    email: 'dave@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the customer\\u2019s ticket and your answer to the problem. Get a reply that explains the fix clearly, sets expectations, and sounds like a human — not a policy bot.',
    inputs: ['ticket: what the customer wrote', 'fix: what solves it', 'policy: any rules to include'],
    outputs: ['reply — ready-to-send draft', 'tone_check — how it reads'],
    exampleIn: 'ticket: "order never arrived" · fix: reship + tracking · policy: refunds after 30 days',
    exampleOut: [
      'reply: "Ugh, that\\u2019s the last thing you needed. I\\u2019ve reshipped it — tracking below, arrives Friday."',
      'policy line: "If it\\u2019s not there by Tuesday, reply here and we\\u2019ll refund you directly."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You draft support replies. Return EXACTLY this JSON shape: {"reply":"ready-to-send draft","tone_check":"one line on how it reads"} HARD RULES: - reply and tone_check are plain STRINGS - acknowledge the frustration first - include only the policy provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'lead-qualifier',
    name: 'Lead Qualifier',
    emoji: '🎯',
    category: 'leads',
    promise: 'Score and qualify inbound leads from their notes — hot, warm, or nurture.',
    maker: '@leadscore',
    makerName: 'Esther Blum',
    email: 'esther@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste a batch of lead notes (form answers, call notes, emails) and your ideal-customer criteria. Get each lead scored, bucketed, and given the exact next action.',
    inputs: ['leads: pasted notes per lead', 'criteria: your ideal customer profile', 'next_steps: what actions exist'],
    outputs: ['verdicts — score + bucket per lead', 'next_action — one per lead'],
    exampleIn: 'leads: 5 notes · criteria: budget > $500/mo, 10+ employees',
    exampleOut: [
      'lead 1: HOT (92) — has budget, 25 staff, asked about onboarding',
      'lead 3: NURTURE (40) — right size, no budget signal, needs case study',
      'action lead 1: book demo within 24h, mention onboarding question'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You qualify leads. Return EXACTLY this JSON shape: {"verdicts":["score 0-100, bucket HOT|WARM|NURTURE, and why — one per lead"],"next_action":["one action per lead"]} HARD RULES: - verdicts and next_action are flat arrays of STRINGS, same length - judge only against the criteria given - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'sales-followup-cadence',
    name: 'Sales Follow-up Cadence',
    emoji: '📅',
    category: 'leads',
    promise: 'A 5-touch follow-up plan for a stalled deal — right message, right day, right channel.',
    maker: '@cadencepro',
    makerName: 'Felix Andersen',
    email: 'felix@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Most deals die in the follow-up. Give us where the deal stalled; get a five-touch plan mixing email and social touches that add value instead of nagging.',
    inputs: ['deal: where the conversation stalled', 'offer: what they were interested in'],
    outputs: ['touches — 5 follow-ups with channel + day', 'value_angle — what each touch adds'],
    exampleIn: 'deal: sent proposal, no reply in 4 days · offer: $3k onboarding package',
    exampleOut: [
      'touch 1 (day 5, email): "One clarifying question, 30 seconds"',
      'touch 3 (day 9, LinkedIn): share a client result in their industry',
      'touch 5 (day 14, email): "Closing the loop — happy to leave it here"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You plan sales follow-ups. Return EXACTLY this JSON shape: {"touches":["day, channel, and message per touch"],"value_angle":["what each touch adds"]} HARD RULES: - touches and value_angle are flat arrays of STRINGS, same length - no invented client results - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'prospect-brief',
    name: 'Prospect Brief',
    emoji: '🧭',
    category: 'leads',
    promise: 'A one-page research brief on any prospect — what they do, what they\\u2019re struggling with, how to pitch.',
    maker: '@researchbot',
    makerName: 'Gemma Walsh',
    email: 'gemma@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste everything you know about a prospect (website text, LinkedIn snippet, notes) and get a structured brief: business model, likely pains, and the angle most likely to earn a reply.',
    inputs: ['prospect_info: paste what you know', 'your_offer: what you\\u2019d pitch'],
    outputs: ['brief — structured prospect summary', 'angle — the best opening hook'],
    exampleIn: 'prospect: DTC candle brand, 20 staff, founder-led marketing · offer: email automation',
    exampleOut: [
      'brief: founder-led brand, manual flows, growing SKU count',
      'pains: personalization at scale, launch emails done by hand',
      'angle: "Your launch emails read great — we can make them send themselves."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write prospect research briefs. Return EXACTLY this JSON shape: {"brief":["what they do, how they operate, what they likely struggle with"],"angle":"the opening hook for outreach"} HARD RULES: - brief is a flat array of STRINGS - only infer from what the info supports - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'case-study-writer',
    name: 'Case Study Writer',
    emoji: '📚',
    category: 'leads',
    promise: 'Turn interview notes into a 3-part case study — situation, change, result.',
    maker: '@casestack',
    makerName: 'Harry Osei',
    email: 'harry@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your customer interview notes (messy is fine). Get a structured case study with a headline, the before-state, the change, and the results — using only what the notes support.',
    inputs: ['notes: your raw interview notes', 'metrics: any numbers mentioned'],
    outputs: ['case_study — full draft with headline', 'quotes — pull-quote candidates'],
    exampleIn: 'notes: warehouse manager, cut picking errors, switched to our scanner app',
    exampleOut: [
      'headline: "How a 40-person warehouse cut picking errors by 60%"',
      'body: before (paper lists) → change (app rollout) → result (60% fewer errors)',
      'quote: "I stopped getting calls at 7am about wrong boxes."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write case studies from notes. Return EXACTLY this JSON shape: {"case_study":"full draft: headline, before, change, result","quotes":["2-3 pull-quote candidates"]} HARD RULES: - quotes is a flat array of STRINGS - only use metrics the notes mention - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'linkedin-post-engine',
    name: 'LinkedIn Post Engine',
    emoji: '💼',
    category: 'leads',
    promise: 'A scroll-stopping LinkedIn post from your raw idea — plus a comment that keeps the thread alive.',
    maker: '@linkedlab',
    makerName: 'Ines Duarte',
    email: 'ines@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste a rough idea or story. Get a hook-first LinkedIn post with short lines (the format that reads well in feed) and a first comment that invites replies.',
    inputs: ['idea: your raw thought or story', 'audience: your network\\u2019s profile'],
    outputs: ['post — hook-first, line-broken', 'first_comment — the conversation starter'],
    exampleIn: 'idea: hired our first VA, felt like cheating · audience: solo founders',
    exampleOut: [
      'post: "I hired a VA last month. It felt like cheating.\nThen I got 9 hours back."',
      'first comment: "What would YOU do with 9 extra hours? Genuinely asking."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write LinkedIn posts. Return EXACTLY this JSON shape: {"post":"hook-first, short lines, one story arc","first_comment":"a question that invites replies"} HARD RULES: - post and first_comment are plain STRINGS - no hashtag spam, no engagement-bait clichés - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'x-thread-writer',
    name: 'X Thread Writer',
    emoji: '🧵',
    category: 'leads',
    promise: 'A 8-tweet thread from your idea — hook tweet, value tweets, and a soft CTA.',
    maker: '@threadsmith',
    makerName: 'Jack Morrison',
    email: 'jack@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Threads grow accounts when each tweet earns the next. Get eight tweets: a curiosity hook, six value tweets with one idea each, and a closing CTA.',
    inputs: ['idea: the core insight', 'audience: who you\\u2019re writing for'],
    outputs: ['tweets — 8-tweet thread', 'hook_variants — 2 alternates for tweet 1'],
    exampleIn: 'idea: founders should email customers before building · audience: indie hackers',
    exampleOut: [
      't1: "Before you build anything: email 20 customers. Here\\u2019s what happens."',
      't4: "Reply #7 changed our roadmap. One email. Free."',
      't8: "Try it this week. Tell me what customers say — quote-tweet me."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write X threads. Return EXACTLY this JSON shape: {"tweets":["8 tweets, one idea each, numbered by position"],"hook_variants":["2 alternate hooks"]} HARD RULES: - tweets and hook_variants are flat arrays of STRINGS - each tweet under 240 characters - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'seo-linkbuilding-email',
    name: 'SEO Linkbuilding Email',
    emoji: '🔗',
    category: 'leads',
    promise: 'A link-building outreach email that offers something worth linking to.',
    maker: '@linkcraft',
    makerName: 'Kira Volkov',
    email: 'kira@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Link outreach fails when it asks for a link and gives nothing. Get an email built around an asset you actually have — data, tool, or expert quote — pitched to one type of site.',
    inputs: ['asset: what you can offer (data, tool, quote)', 'target_site: who you\\u2019re pitching', 'page: their page it fits'],
    outputs: ['email — asset-first outreach', 'subject_line — one that gets opened'],
    exampleIn: 'asset: survey of 500 shoppers · target: ecom blog · page: their shipping-costs article',
    exampleOut: [
      'email: "Your shipping-costs piece cites 2023 numbers. Our 500-shopper survey has fresh ones — want the data?"',
      'subject: "Fresh shipping-cost data for your 2026 update"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write link-building emails. Return EXACTLY this JSON shape: {"email":"asset-first, under 120 words","subject_line":"one line"} HARD RULES: - email and subject_line are plain STRINGS - only offer the asset provided, no invented data - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'webinar-promo-copy',
    name: 'Webinar Promo Copy',
    emoji: '🎪',
    category: 'leads',
    promise: 'Invite email, landing copy, and reminder sequence for your next webinar.',
    maker: '@eventcopy',
    makerName: 'Lucas Meyer',
    email: 'lucas@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Webinar attendance dies at the invite. Get the full promo package: a benefit-first invite email, landing page copy, and the 24h/1h reminder sequence that fills seats.',
    inputs: ['topic: what you\\u2019ll teach', 'audience: who should attend', 'date: when it runs'],
    outputs: ['invite — the registration email', 'landing_copy — page headline + body', 'reminders — 2 reminder emails'],
    exampleIn: 'topic: 3 pricing experiments · audience: SaaS founders · date: Thursday',
    exampleOut: [
      'invite: "Three pricing experiments that survive contact with customers."',
      'landing: headline "Steal these 3 pricing tests" + bullet agenda',
      'reminder 24h: "Thursday — bring your pricing page"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write webinar promo copy. Return EXACTLY this JSON shape: {"invite":"registration email","landing_copy":"headline plus body","reminders":["2 reminder emails"]} HARD RULES: - reminders is a flat array of STRINGS - benefits before logistics - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'demo-call-script',
    name: 'Demo Call Script',
    emoji: '📞',
    category: 'leads',
    promise: 'A 30-minute demo call script — discovery questions, demo flow, and the close.',
    maker: '@callscript',
    makerName: 'Marta Silva',
    email: 'marta@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Demos flop without structure. Get a timed call script: 10 minutes of discovery questions, a demo flow mapped to their answers, and three ways to close for next steps.',
    inputs: ['product: what you demo', 'prospect_type: who\\u2019s on the call'],
    outputs: ['script — timed call structure', 'questions — discovery questions', 'closes — 3 next-step options'],
    exampleIn: 'product: inventory software · prospect: ecom ops manager',
    exampleOut: [
      '0-10min: "What happened the last time stock ran out?" (find the pain, not the feature)',
      'demo flow: show dashboard only after they name the metric',
      'close: "Want me to set up a trial with your actual SKUs?"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write demo call scripts. Return EXACTLY this JSON shape: {"script":["timed blocks: minutes, what to do, what to say"],"questions":["discovery questions"],"closes":["3 next-step closes"]} HARD RULES: - script, questions, closes are flat arrays of STRINGS - questions before features - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'pricing-page-copywriter',
    name: 'Pricing Page Copywriter',
    emoji: '💲',
    category: 'leads',
    promise: 'Pricing page copy that frames each tier around value — not features.',
    maker: '@pricecopy',
    makerName: 'Noah Eriksen',
    email: 'noah@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your tiers and features. Get per-tier headlines, value-first descriptions, and the FAQ lines that kill the top objections — copy that makes the middle tier the obvious choice.',
    inputs: ['tiers: name, price, features per tier', 'audience: who buys', 'anchor: which tier should win'],
    outputs: ['tier_copy — headline + description per tier', 'faq_lines — objection-handling FAQs'],
    exampleIn: 'tiers: Starter $29, Pro $79, Scale $199 · audience: agencies · anchor: Pro',
    exampleOut: [
      'Pro: "For agencies juggling 10+ clients — automate the busywork, keep the margins."',
      'faq: "Can I start on Starter and move up? Yes — upgrades prorate same-day."',
      'anchor logic: Pro features make Scale feel like overkill, Starter feel like a tease'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write pricing page copy. Return EXACTLY this JSON shape: {"tier_copy":[{"tier":"name","headline":"value-first line","description":"2 sentences"}],"faq_lines":["objection-handling FAQ answers"]} HARD RULES: - tier_copy is a flat array, one entry per tier - faq_lines is a flat array of STRINGS - never invent features - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'carrier-comparer',
    name: 'Carrier Comparer',
    emoji: '🚚',
    category: 'save',
    promise: 'Compare shipping options for one order — cost, speed, and the smart pick.',
    maker: '@shipwise',
    makerName: 'Olive Harper',
    email: 'olive@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your shipment details and the carrier quotes you have. Get a clean comparison with cost-per-day math and a recommendation that balances price and delivery promise.',
    inputs: ['shipment: weight, size, destination', 'quotes: carrier rates you have'],
    outputs: ['comparison — cost vs speed table text', 'recommendation — the smart pick and why'],
    exampleIn: 'shipment: 2kg to Chicago · quotes: FedEx $18 (3d), UPS $22 (2d), USPS $11 (5d)',
    exampleOut: [
      'comparison: USPS saves $7-11, adds 2-3 days',
      'recommendation: USPS unless the order is >$80 — then UPS, delivery speed protects the review score'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You compare shipping options. Return EXACTLY this JSON shape: {"comparison":["cost vs speed per option"],"recommendation":"the smart pick and why"} HARD RULES: - comparison is a flat array of STRINGS - only use the quotes provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'refund-policy-drafter',
    name: 'Refund Policy Drafter',
    emoji: '↩️',
    category: 'save',
    promise: 'A refund policy that protects you and reads fair to customers.',
    maker: '@policypro',
    makerName: 'Pablo Iglesias',
    email: 'pablo@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your product type and the refund terms you want. Get a plain-language policy with clear windows, conditions, and return steps — plus the two edge cases sellers always forget.',
    inputs: ['product_type: physical · digital · subscription', 'terms: your intended window and conditions'],
    outputs: ['policy — plain-language refund policy', 'edge_cases — the clauses you\\u2019re missing'],
    exampleIn: 'product: physical goods · terms: 30 days, buyer pays return shipping',
    exampleOut: [
      'policy: "30 days from delivery. Return shipping on you; we refund within 5 business days of receipt."',
      'edge case 1: damaged in transit — we cover return, always',
      'edge case 2: missing the window — store credit instead of refusal'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You draft refund policies. Return EXACTLY this JSON shape: {"policy":"plain-language policy using the given terms","edge_cases":["clauses sellers often miss"]} HARD RULES: - edge_cases is a flat array of STRINGS - keep the terms exactly as provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'supplier-negotiation-email',
    name: 'Supplier Negotiation Email',
    emoji: '🤝',
    category: 'save',
    promise: 'A supplier email that asks for better terms without burning the relationship.',
    maker: '@negotiateai',
    makerName: 'Quinn Farrell',
    email: 'quinn@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Price increases are negotiable if asked right. Give us your volume and the ask; get a respectful email that leads with the relationship, then makes a specific, reasonable ask.',
    inputs: ['supplier: your history with them', 'ask: lower price · better terms · MOQ', 'volume: what you order'],
    outputs: ['email — relationship-first ask', 'fallback — the second ask if the first fails'],
    exampleIn: 'supplier: 2-year partner · ask: 8% price cut · volume: 2x growth',
    exampleOut: [
      'email: "Our orders doubled this year. Can we revisit pricing at 8%? Locking it in a 12-month PO helps you plan too."',
      'fallback: "If 8% is hard, how about free freight over $5k orders instead?"'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write supplier negotiation emails. Return EXACTLY this JSON shape: {"email":"relationship-first, specific ask","fallback":"a second reasonable ask"} HARD RULES: - email and fallback are plain STRINGS - make the ask concrete and fair - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'reorder-planner',
    name: 'Reorder Planner',
    emoji: '📦',
    category: 'save',
    promise: 'Reorder quantities for your SKUs — no stockouts, no overstock — from your sales numbers.',
    maker: '@stockbot',
    makerName: 'Rena Weiss',
    email: 'rena@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your SKU-level sales history, lead times, and current stock. Get reorder quantities with safety-stock logic and a note on which SKUs are trending up or down.',
    inputs: ['sales: units sold per SKU per month', 'lead_time: days to restock', 'stock: current units on hand'],
    outputs: ['reorder — qty per SKU', 'flags — SKUs to watch'],
    exampleIn: 'SKU A: 120/mo, lead 20d, stock 40 · SKU B: 30/mo, lead 45d, stock 60',
    exampleOut: [
      'SKU A: reorder 120 (cover 2 months + 2 weeks safety) — stock runs out in ~10 days',
      'SKU B: no reorder — 2 months cover, demand flat',
      'flag: SKU B lead time is long; if it trends up, order early'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You plan reorders. Return EXACTLY this JSON shape: {"reorder":["SKU: quantity and reasoning"],"flags":["SKUs to watch"]} HARD RULES: - reorder and flags are flat arrays of STRINGS - show the math per SKU - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'kpi-sql-writer',
    name: 'KPI SQL Writer',
    emoji: '🗄️',
    category: 'save',
    promise: 'Plain English to SQL — get the query for the KPI you actually want.',
    maker: '@sqlgenie',
    makerName: 'Seth Kamara',
    email: 'seth@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Describe the metric and your tables; get a correct, commented SQL query with the joins, filters, and time bucketing spelled out — plus what the result will and won\\u2019t tell you.',
    inputs: ['question: the KPI you want', 'schema: your tables and columns'],
    outputs: ['sql — the query with comments', 'caveats — what the number misses'],
    exampleIn: 'question: revenue per returning customer this quarter · schema: orders(id, customer_id, total, created_at), customers(id, first_order_at)',
    exampleOut: [
      'sql: SELECT ... WHERE created_at >= 2026-04-01 AND customer has first_order_at < quarter start',
      'caveat: returning depends on when you started tracking — new customers look returning if first_order_at is NULL'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write SQL. Return EXACTLY this JSON shape: {"sql":"the query, commented, one code block","caveats":["what the result misses"]} HARD RULES: - caveats is a flat array of STRINGS - use only the schema provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'expense-categorizer',
    name: 'Expense Categorizer',
    emoji: '🧾',
    category: 'save',
    promise: 'A messy expense list becomes clean categories — with the tax-relevant ones flagged.',
    maker: '@cashflowai',
    makerName: 'Tara Ngo',
    email: 'tara@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste raw expense lines ("uber to airport", "adobe cc") and get each one categorized, with likely-deductible items flagged and the ones needing a receipt called out.',
    inputs: ['expenses: your raw lines', 'business_type: what you do'],
    outputs: ['categorized — every line with a category', 'flags — deductible or needs-receipt items'],
    exampleIn: 'expenses: "uber 24.50", "notion 10", "coffee with client 8.75"',
    exampleOut: [
      'uber 24.50 → travel (deductible if business trip — flag)',
      'notion 10 → software (deductible)',
      'coffee 8.75 → meals & entertainment (50% rule — keep receipt)'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You categorize expenses. Return EXACTLY this JSON shape: {"categorized":["original line: category and reason"],"flags":["deductible or needs-receipt items"]} HARD RULES: - categorized and flags are flat arrays of STRINGS - one line per expense, no omissions - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'invoice-chaser',
    name: 'Invoice Chaser',
    emoji: '💸',
    category: 'save',
    promise: 'Polite payment-reminder emails that get invoices paid without souring clients.',
    maker: '@cashchaser',
    makerName: 'Uri Feldman',
    email: 'uri@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the invoice details and days overdue. Get a tiered reminder — gentle nudge, friendly follow-up, firm-but-warm final — that escalates without accusing.',
    inputs: ['invoice: amount, client, due date', 'days_overdue: how late it is'],
    outputs: ['reminders — 3 escalating emails', 'escalation_plan — when to send each'],
    exampleIn: 'invoice: $2,400, client "Northwind", due 3 weeks ago',
    exampleOut: [
      'reminder 1: "Quick check — did the invoice land OK?" (assume good faith)',
      'reminder 3: "I\\u2019m pausing work on the next phase until this clears — happy to set up a plan."',
      'plan: send 1 now, 2 in 5 days, 3 in 12 days'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write invoice reminders. Return EXACTLY this JSON shape: {"reminders":["3 escalating emails: nudge, follow-up, final"],"escalation_plan":["when to send each"]} HARD RULES: - reminders and escalation_plan are flat arrays of STRINGS, same length - firm but professional, never hostile - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'contract-summarizer',
    name: 'Contract Summarizer',
    emoji: '📑',
    category: 'save',
    promise: 'Any contract in plain English — obligations, dates, and the clauses to negotiate.',
    maker: '@plainterms',
    makerName: 'Veda Raman',
    email: 'veda@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste a contract (or its key sections) and get a plain-English summary: what you\\u2019re agreeing to, the dates that matter, and the clauses a lawyer would flag.',
    inputs: ['contract: paste the text', 'your_role: which side you are'],
    outputs: ['summary — plain-English obligations', 'flags — clauses to negotiate or watch'],
    exampleIn: 'contract: 6-page vendor agreement, you are the buyer',
    exampleOut: [
      'summary: auto-renewing annual deal, $12k/yr, 90-day termination window',
      'flag: auto-renewal without notice — add 30-day email alert',
      'flag: liability cap favors them 10:1 — ask to raise it'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You summarize contracts. Return EXACTLY this JSON shape: {"summary":["plain-English obligations and dates"],"flags":["clauses to negotiate or watch"]} HARD RULES: - summary and flags are flat arrays of STRINGS - never invent clauses, only report what is there - not legal advice, say so in one line - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'saas-spend-auditor',
    name: 'SaaS Spend Auditor',
    emoji: '🪓',
    category: 'save',
    promise: 'Find the subscriptions bleeding your budget — with a cut-or-keep verdict per tool.',
    maker: '@spendwatch',
    makerName: 'Wade Ellis',
    email: 'wade@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your subscriptions (tool, price, last-used notes) and get each one judged: keep, downgrade, or cut — with the annual savings and a 30-day plan to action it.',
    inputs: ['subscriptions: tool, price, usage notes', 'team_size: how many seats you pay for'],
    outputs: ['verdicts — keep/downgrade/cut per tool', 'savings — total annual number'],
    exampleIn: 'subs: analytics $99/mo (used weekly), backup $45/mo (untouched 4mo), CRM $200/mo (10 seats, 4 users)',
    exampleOut: [
      'cut: backup — $540/yr back, no usage in 4 months',
      'downgrade: CRM to 4 seats — save $1,440/yr',
      'total: ~$2,000/yr recoverable this quarter'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You audit SaaS spending. Return EXACTLY this JSON shape: {"verdicts":["tool: keep|downgrade|cut with math"],"savings":"total annual recoverable"} HARD RULES: - verdicts is a flat array of STRINGS - judge only on the usage given - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'tax-deduction-finder',
    name: 'Tax Deduction Finder',
    emoji: '🧮',
    category: 'save',
    promise: 'Deductions you\\u2019re likely missing — mapped to your actual expenses.',
    maker: '@deductionpro',
    makerName: 'Xena Patel',
    email: 'xena@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your business expenses and setup. Get the deductions that plausibly apply, what evidence to keep, and the ones that need a professional\\u2019s sign-off before claiming.',
    inputs: ['expenses: your business spend', 'setup: solo · LLC · employees · home office'],
    outputs: ['deductions — applicable ones with evidence notes', 'cautions — items to run by an accountant'],
    exampleIn: 'expenses: laptop, home internet, client lunches · setup: solo, home office',
    exampleOut: [
      'deductions: home office % of rent, internet %, laptop amortized, 50% client meals',
      'caution: home-office % must be exclusive use — keep the floor plan photo',
      'caution: vehicle miles need a contemporaneous log, not a guess'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You find tax deductions. Return EXACTLY this JSON shape: {"deductions":["applicable deduction: evidence to keep"],"cautions":["items to confirm with an accountant"]} HARD RULES: - deductions and cautions are flat arrays of STRINGS - generic guidance only, never a guarantee - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'aov-booster',
    name: 'AOV Booster',
    emoji: '🆙',
    category: 'save',
    promise: 'Upsell, cross-sell, and bundle ideas that raise average order value.',
    maker: '@aovlab',
    makerName: 'Yara Haddad',
    email: 'yara@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Give us your catalog and current AOV. Get ten concrete bundle, upsell, and threshold ideas (free shipping at X, pair with Y) — with the logic that makes them work.',
    inputs: ['catalog: your products and prices', 'aov: current average order value'],
    outputs: ['ideas — 10 AOV plays', 'thresholds — the numbers to set'],
    exampleIn: 'catalog: candles $24, diffuser $45, gift set $60 · aov: $32',
    exampleOut: [
      'bundle: "Evening Ritual" candle + diffuser at $59 vs $69 separately',
      'threshold: free shipping at $40 (10% above AOV) — lifts it ~15%',
      'upsell: at checkout, $9 add-on refill keeps cart momentum'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You design AOV plays. Return EXACTLY this JSON shape: {"ideas":["10 concrete bundle/upsell/threshold plays"],"thresholds":["the numbers to set, with reasoning"]} HARD RULES: - ideas and thresholds are flat arrays of STRINGS - only use catalog prices provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'promo-calendar-planner',
    name: 'Promo Calendar Planner',
    emoji: '🗓️',
    category: 'save',
    promise: 'A 90-day promotion calendar — discounts, bundles, and events, sequenced to protect margins.',
    maker: '@promoplan',
    makerName: 'Zeke Navarro',
    email: 'zeke@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Constant discounting kills margins. Get a 90-day calendar that spaces promos, pairs them with events, and alternates offer types so nothing becomes expected.',
    inputs: ['products: what you sell', 'events: known dates (holidays, launches)', 'margin: your typical margin %'],
    outputs: ['calendar — week-by-week promos', 'margin_notes — discount ceilings'],
    exampleIn: 'products: apparel · events: back-to-school, Black Friday · margin: 55%',
    exampleOut: [
      'wk 1: no promo — full-price drop to reset expectations',
      'wk 6: bundle deal (20% off pair) — protects margin vs sitewide',
      'wk 9: BTS flash 15% 48h — discount ceiling for apparel is ~25%'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You plan promo calendars. Return EXACTLY this JSON shape: {"calendar":["week: promo or hold, with offer details"],"margin_notes":["discount ceilings and reasoning"]} HARD RULES: - calendar and margin_notes are flat arrays of STRINGS - alternate offer types, never stack sitewide - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'margin-checker',
    name: 'Margin Checker',
    emoji: '⚖️',
    category: 'save',
    promise: 'Price vs cost math per product — margins, break-even, and what to raise.',
    maker: '@marginlab',
    makerName: 'Abe Rosen',
    email: 'abe@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste per-product cost and price data. Get gross margin per SKU, the ones below your target, and the price or cost change that fixes each.',
    inputs: ['products: price and cost per unit', 'target_margin: your goal %'],
    outputs: ['margins — per-SKU math', 'fixes — what to change and by how much'],
    exampleIn: 'SKU A: $40 price, $18 cost · SKU B: $25 price, $19 cost · target: 50%',
    exampleOut: [
      'SKU A: 55% margin — healthy',
      'SKU B: 24% margin — below target; +$10 price or -$5 cost to hit 50%',
      'note: SKU B price bump is safer than renegotiating cost this quarter'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You check margins. Return EXACTLY this JSON shape: {"margins":["SKU: margin % and status"],"fixes":["what to change per SKU"]} HARD RULES: - margins and fixes are flat arrays of STRINGS - show the arithmetic - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'wholesale-quote-builder',
    name: 'Wholesale Quote Builder',
    emoji: '🏭',
    category: 'save',
    promise: 'A wholesale quote for bulk buyers — tiers, terms, and the margin floor.',
    maker: '@bulkquote',
    makerName: 'Bianca Rossi',
    email: 'bianca@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your retail prices and cost, plus the buyer\\u2019s request. Get a tiered wholesale quote (3 tiers), payment terms, and the minimum order that keeps you profitable.',
    inputs: ['retail: your prices', 'cost: your unit cost', 'request: what the buyer wants'],
    outputs: ['quote — tiered wholesale pricing', 'terms — payment and MOQ recommendations'],
    exampleIn: 'retail $30, cost $9 · request: 200 units',
    exampleOut: [
      'tier 1 (100+): $18/unit (40% margin)',
      'tier 3 (500+): $15/unit (33%) — floor',
      'terms: 50% deposit, net-30 on balance, MOQ 100'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You build wholesale quotes. Return EXACTLY this JSON shape: {"quote":["tier: qty range, price, margin %"],"terms":["payment and MOQ recommendations"]} HARD RULES: - quote and terms are flat arrays of STRINGS - show margin math per tier - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'roi-formula-builder',
    name: 'ROI Formula Builder',
    emoji: '📐',
    category: 'save',
    promise: 'Spreadsheet formulas for your business math — ROI, LTV, CAC, break-even — explained.',
    maker: '@sheetformula',
    makerName: 'Carter Blake',
    email: 'carter@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Describe the number you want to calculate and your column layout; get the exact spreadsheet formula with cell references, plus a plain-English explanation of what it computes.',
    inputs: ['goal: the metric to compute', 'columns: your sheet\\u2019s layout'],
    outputs: ['formula — ready to paste', 'explanation — what it computes and assumes'],
    exampleIn: 'goal: ROAS per campaign · columns: A=campaign, B=spend, C=revenue',
    exampleOut: [
      'formula: =IFERROR(C2/B2,"") — ROAS per row, blank if no spend',
      'explanation: ROAS = revenue ÷ spend; IFERROR hides div-by-zero rows'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write spreadsheet formulas. Return EXACTLY this JSON shape: {"formula":"the exact formula to paste","explanation":"what it computes and assumes"} HARD RULES: - formula and explanation are plain STRINGS - reference the columns provided exactly - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'cashflow-forecaster',
    name: 'Cashflow Forecaster',
    emoji: '🔮',
    category: 'save',
    promise: 'A 90-day cash forecast from your numbers — with the month that will hurt.',
    maker: '@cashlab',
    makerName: 'Dina Kovac',
    email: 'dina@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your monthly revenue, fixed costs, and known upcoming payments. Get a 90-day cash projection, the lowest-cash month, and the one move that softens it.',
    inputs: ['revenue: monthly averages and trends', 'costs: fixed and variable', 'payments: known upcoming big bills'],
    outputs: ['forecast — month-by-month cash position', 'risk_month — when cash dips and why', 'move — the single fix'],
    exampleIn: 'rev $40k flat · costs $35k · big bills: $15k inventory in month 2',
    exampleOut: [
      'month 2: cash dips to $12k — lowest point',
      'cause: inventory bill lands before holiday sales',
      'move: split the PO into two deliveries, 30 days apart'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You forecast cash flow. Return EXACTLY this JSON shape: {"forecast":["month: projected cash position"],"risk_month":"when it dips and why","move":"the single best fix"} HARD RULES: - forecast is a flat array of STRINGS - only use the numbers provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'job-description-writer',
    name: 'Job Description Writer',
    emoji: '🧑‍💼',
    category: 'save',
    promise: 'A role description that attracts the right person — responsibilities, requirements, and the honest part.',
    maker: '@hirecopy',
    makerName: 'Erik Johansson',
    email: 'erik@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the role, level, and what success looks like. Get a complete JD: compelling summary, real responsibilities, must-have vs nice-to-have, and the honest "what it\\u2019s really like" section.',
    inputs: ['role: title and level', 'responsibilities: what they\\u2019ll do', 'success: what good looks like'],
    outputs: ['jd — full description', 'requirements — must-have vs nice-to-have'],
    exampleIn: 'role: marketing manager at DTC brand · success: own campaigns end-to-end',
    exampleOut: [
      'summary: "You\\u2019ll own campaigns from concept to ROAS — with budget authority, not committee sign-off."',
      'must-have: ran paid social with real numbers',
      'nice-to-have: UGC creative experience'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write job descriptions. Return EXACTLY this JSON shape: {"jd":"summary, responsibilities, honest section","requirements":["must-have then nice-to-have, labeled"]} HARD RULES: - requirements is a flat array of STRINGS - no inflated perks lists - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'proposal-writer',
    name: 'Proposal Writer',
    emoji: '📝',
    category: 'save',
    promise: 'A freelance or agency proposal that scopes the work, the price, and the process.',
    maker: '@proposalforge',
    makerName: 'Faye O\\u2019Connor',
    email: 'faye@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste the client\\u2019s request and your rate. Get a structured proposal: their problem in their words, your approach, deliverables, timeline, and pricing framed around outcomes.',
    inputs: ['request: what the client asked for', 'your_rate: how you price', 'timeline: how long it takes'],
    outputs: ['proposal — full structured draft', 'pricing_block — outcome-framed pricing'],
    exampleIn: 'request: redo their Shopify store · rate: $150/hr, ~40h · timeline: 3 weeks',
    exampleOut: [
      'proposal: "Your store converts at 0.8% — the redesign targets 2% by fixing the product page flow."',
      'deliverables: 12 pages, mobile-first, CRO pass',
      'pricing: "Fixed $6,000 (vs hourly) — you get certainty, I get focus."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write proposals. Return EXACTLY this JSON shape: {"proposal":"problem, approach, deliverables, timeline","pricing_block":"outcome-framed pricing"} HARD RULES: - proposal and pricing_block are plain STRINGS - only use scope and rates provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'negotiation-email-writer',
    name: 'Negotiation Email Writer',
    emoji: '🥂',
    category: 'save',
    promise: 'Negotiation emails that hold your number and keep the door open.',
    maker: '@negotiatepro',
    makerName: 'Gino Barbieri',
    email: 'gino@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the offer you received and your target. Get an email that anchors, justifies, and leaves room — plus the counter-move if they push back again.',
    inputs: ['offer: what they proposed', 'your_target: what you need', 'leverage: what you bring'],
    outputs: ['email — the anchored counter', 'fallback_move — if they push back'],
    exampleIn: 'offer: $8k for a 3-week build · target: $10k · leverage: niche Shopify experience',
    exampleOut: [
      'email: "I\\u2019d love to make this work. At $10k I can guarantee the migration week — at $8k it\\u2019s best-effort. Your call on priority."',
      'fallback: if they hold at $8k, trade scope — cut the analytics page, keep the number'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write negotiation emails. Return EXACTLY this JSON shape: {"email":"anchored counter that justifies the number","fallback_move":"the scope-or-terms trade if they push back"} HARD RULES: - email and fallback_move are plain STRINGS - professional, never adversarial - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'returns-reason-analyser',
    name: 'Returns Reason Analyser',
    emoji: '📉',
    category: 'save',
    promise: 'Find the real reason behind your returns — and the fix that stops the bleeding.',
    maker: '@returnfix',
    makerName: 'Hilda Berg',
    email: 'hilda@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your return reasons and product details. Get the dominant return driver, whether it\\u2019s a listing, sizing, or quality problem, and the concrete fix for each cluster.',
    inputs: ['returns: return reasons per order', 'product: what\\u2019s being returned'],
    outputs: ['clusters — grouped return drivers', 'fixes — one fix per cluster'],
    exampleIn: 'returns: "too big", "color differs", "too big", "looks cheap" for a t-shirt',
    exampleOut: [
      'clusters: sizing (40%), color expectation (30%), quality perception (30%)',
      'fix: add measurement chart + model height; it\\u2019s a listing fix, not a product fix',
      'fix: photos on neutral background only — color filters cause the returns'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You analyse return reasons. Return EXACTLY this JSON shape: {"clusters":["return driver: share and evidence"],"fixes":["one fix per cluster"]} HARD RULES: - clusters and fixes are flat arrays of STRINGS - only use the reasons provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'review-reply-bot',
    name: 'Review Reply Bot',
    emoji: '💬',
    category: 'save',
    promise: 'On-brand replies to customer reviews — good ones get thanks, bad ones get a fix path.',
    maker: '@reviewreply',
    makerName: 'Ian Fletcher',
    email: 'ian@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste up to 8 reviews. Get a reply per review in your brand voice: positive reviews get warmth and a detail from their review; negative ones get ownership and a concrete fix.',
    inputs: ['reviews: paste the reviews', 'brand_voice: how you talk'],
    outputs: ['replies — one per review, same order'],
    exampleIn: 'reviews: "love it!" and "broke in a week" · voice: friendly, accountable',
    exampleOut: [
      'reply 1: "So glad it\\u2019s holding up — which color did you get?"',
      'reply 2: "That\\u2019s on us. Replacement\\u2019s on the way — DM\\u2019d you the tracking."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You reply to customer reviews. Return EXACTLY this JSON shape: {"replies":["one reply per review, same order as input"]} HARD RULES: - replies is a flat array of STRINGS - reference something specific from each review - negative reviews: own it, then a fix - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'review-theme-miner',
    name: 'Review Theme Miner',
    emoji: '⛏️',
    category: 'save',
    promise: 'The themes hiding in your reviews — praises to amplify and complaints to fix, with quotes.',
    maker: '@thememiner',
    makerName: 'Jessa Malone',
    email: 'jessa@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste a batch of reviews and get grouped themes: what customers love (put it in your ads), what they complain about (fix it), each with the real quotes as evidence.',
    inputs: ['reviews: paste the batch', 'product: what it is'],
    outputs: ['themes — praised and complained themes with quotes', 'actions — what to amplify and fix'],
    exampleIn: 'reviews: 12 reviews of a travel backpack',
    exampleOut: [
      'praised: "fits under the seat" (8 mentions) — use in ads',
      'complained: strap padding (4 mentions) — fix or reframe sizing',
      'action: lead ad #2 with the under-seat line'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You mine review themes. Return EXACTLY this JSON shape: {"themes":[{"sentiment":"praised|complained","theme":"the recurring topic","mentions":"count","quotes":["real short quotes"]}],"actions":["what to amplify and fix"]} HARD RULES: - themes is a flat array of entries - quotes must be from the reviews provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'competitor-price-analyser',
    name: 'Competitor Price Analyser',
    emoji: '🕵️',
    category: 'save',
    promise: 'Your prices vs the market — where you\\u2019re leaving money or losing the click.',
    maker: '@pricespy',
    makerName: 'Kyle Nguyen',
    email: 'kyle@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your SKU prices and the competitor prices you\\u2019ve collected. Get a positioning read: where you\\u2019re premium, where you\\u2019re undercutting yourself, and what to adjust.',
    inputs: ['your_prices: SKU: price', 'competitor_prices: SKU: their price', 'position: intended brand tier'],
    outputs: ['analysis — per-SKU positioning', 'moves — price changes to consider'],
    exampleIn: 'yours: serum $38 · competitor A $42, B $30 · position: mid-premium',
    exampleOut: [
      'serum: mid-market — within $4 of both, fine for the tier',
      'move: hold price; add a bundle vs matching B\\u2019s $30',
      'flag: if A runs a 30% sale you\\u2019re suddenly the expensive one'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You analyse competitive pricing. Return EXACTLY this JSON shape: {"analysis":["SKU: where you sit vs competitors"],"moves":["price changes to consider"]} HARD RULES: - analysis and moves are flat arrays of STRINGS - only use the prices provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'pnl-cost-cutter',
    name: 'P&L Cost Cutter',
    emoji: '✂️',
    category: 'save',
    promise: 'A P&L read that finds the costs to cut without touching what grows revenue.',
    maker: '@costcutter',
    makerName: 'Leila Farouk',
    email: 'leila@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your P&L lines. Get cost lines ranked by cut-ability (impact vs pain), the fixed vs variable split, and a 30-day action list with the savings per line.',
    inputs: ['pnl: your cost lines and amounts', 'revenue: total and trends'],
    outputs: ['rankings — costs by cut-ability with savings', 'action_list — the 30-day plan'],
    exampleIn: 'pnl: ads $8k, software $1.2k, freight $2.5k, office $900 · revenue $40k',
    exampleOut: [
      'ads: highest leverage — cut worst 20% of campaigns, save ~$1.6k not $X',
      'software: 3 overlapping tools — consolidate, save ~$400/mo',
      'office: fixed but renegotiable — ask for 10% off at renewal'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You find cost cuts in a P&L. Return EXACTLY this JSON shape: {"rankings":["cost line: cut-ability and savings"],"action_list":["30-day actions with expected savings"]} HARD RULES: - rankings and action_list are flat arrays of STRINGS - only use the lines provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'e2b-data-cruncher',
    name: 'E2B Data Cruncher',
    emoji: '📊',
    category: 'save',
    promise: 'Paste a messy dataset, get real computed analysis — run in a sandbox, not a guess.',
    maker: '@datacrunch',
    makerName: 'Marco Bellini',
    email: 'marco@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Paste CSV data and the question you want answered. We write the analysis code and run it in a sandbox — you get actual computed numbers, not an LLM\\u2019s estimate.',
    inputs: ['data: paste your CSV', 'question: what to compute', 'columns: what each column means'],
    outputs: ['results — computed numbers with method', 'code — the analysis script you keep'],
    exampleIn: 'data: sales.csv with date, sku, qty, revenue · question: top SKU by revenue per quarter',
    exampleOut: [
      'results: Q2 top SKU = "mug-sage" at $12,400 (34% of Q2 revenue)',
      'method: grouped by quarter, summed revenue, ranked',
      'code: pandas script you can rerun on fresh data'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'planner', model: 'deepseek-v4-flash', max_output: 500, system: `You plan data analyses. Return EXACTLY this JSON shape: {"method":"the exact computation steps","expected_columns":"columns the data must have","edge_cases":["missing data, dupes, types to handle"]} HARD RULES: - expected_columns and edge_cases are flat arrays of STRINGS - the method must be runnable, step by step - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'e2b_sandbox', qty: 2 },
        { type: 'llm', role: 'summary', model: 'deepseek-v4-flash', max_output: 400, system: `You summarize computed data results. Return EXACTLY this JSON shape: {"results":["computed finding: number and meaning"],"caveats":["what the data can\\u2019t tell you"]} HARD RULES: - results and caveats are flat arrays of STRINGS - only report numbers the computation produced - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.15,
    icon: null,
  },
  {
    slug: 'browser-price-check',
    name: 'Browser Price Check',
    emoji: '🌐',
    category: 'save',
    promise: 'Live competitor price check — we browse the actual pages and bring back the numbers.',
    maker: '@liveprice',
    makerName: 'Nina Petrova',
    email: 'nina@cognition.cv',
    priceOwn: 49,
    priceMaintain: 12,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Give us the competitor URLs and your SKUs. We open each page in a real browser session, extract the live prices, and return a clean comparison table with a positioning read.',
    inputs: ['urls: competitor product pages', 'your_skus: what to compare against'],
    outputs: ['prices — live prices per URL', 'comparison — your price vs market'],
    exampleIn: 'urls: 3 competitor pages for "ceramic pour-over" · your price: $42',
    exampleOut: [
      'live: Brand A $45, Brand B $38, Brand C $49 (with $6 shipping)',
      'comparison: you\\u2019re mid-market, but B is $4 under with free ship',
      'note: B\\u2019s price looks like a launch discount — verify again in 2 weeks'
    ],
    workflow: {
      steps: [
        { type: 'api', api: 'browserbase_session', qty: 1 },
        { type: 'llm', role: 'read', model: 'deepseek-v4-flash', max_output: 500, system: `You turn browsed page observations into price comparisons. Return EXACTLY this JSON shape: {"prices":["URL: price found and any shipping notes"],"comparison":["your price vs each competitor"],"note":"anything suspicious about the prices"} HARD RULES: - prices, comparison are flat arrays of STRINGS - only report prices actually observed - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.13,
    icon: null,
  },
  {
    slug: 'modal-batch-upscaler',
    name: 'Modal Batch Upscaler',
    emoji: '🔬',
    category: 'save',
    promise: 'Upscale and enhance your product images in batch — GPU-powered, detail-preserving.',
    maker: '@upscalelab',
    makerName: 'Oscar Lindt',
    email: 'oscar@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 2 a day',
    desc: 'Give us your image descriptions and target resolution. We run enhancement passes on a GPU sandbox and return the upscaled versions with a quality note per image.',
    inputs: ['images: describe each image and its issue', 'target: resolution to reach'],
    outputs: ['enhanced — upscaled image descriptions + notes', 'quality_notes — what improved per image'],
    exampleIn: 'images: 3 product shots, soft at 2000px · target: 4000px for print',
    exampleOut: [
      'image 1: upscaled to 4000px, edge detail recovered',
      'image 2: texture sharpened without plastic look',
      'quality: all 3 printable; image 3 needs a source re-shoot for true sharpness'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'brief', model: 'deepseek-v4-flash', max_output: 300, system: `You write upscale briefs. Return EXACTLY this JSON shape: {"briefs":["per image: source issue, target resolution, what to preserve"]} HARD RULES: - briefs is a flat array of STRINGS - keep expectations honest about source quality - Output ONLY the JSON object, no markdown fences, no commentary.` },
        { type: 'api', api: 'modal_gpu_30s', qty: 2 }
      ]
    },
    runPrice: 0.13,
    icon: null,
  },
  {
    slug: 'sop-builder',
    name: 'SOP Builder',
    emoji: '🧱',
    category: 'ops',
    promise: 'Messy notes become a step-by-step SOP anyone on the team can follow.',
    maker: '@sopforge',
    makerName: 'Petra Novak',
    email: 'petra@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste your rough process notes. Get a clean SOP: numbered steps with owners, the tools used per step, decision points, and the "when it goes wrong" section.',
    inputs: ['notes: your process notes, messy is fine', 'owner: who runs it'],
    outputs: ['sop — numbered steps with tools and owners', 'failure_modes — what breaks and the fix'],
    exampleIn: 'notes: "fulfill orders — print label, pack, drop at UPS, email tracking"',
    exampleOut: [
      'steps: 1) print label (ShipStation) 2) pack with insert 3) drop at UPS by 4pm 4) email tracking',
      'decision: if out of stock → email customer with ETA, don\\u2019t ship partial',
      'failure: printer down → backup is the UPS store\\u2019s label service'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write SOPs from notes. Return EXACTLY this JSON shape: {"sop":["numbered steps with tools and owners"],"failure_modes":["what breaks and the fix"]} HARD RULES: - sop and failure_modes are flat arrays of STRINGS - keep every step from the notes, fill gaps with obvious defaults - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'meeting-notes-to-actions',
    name: 'Meeting Notes to Actions',
    emoji: '🗒️',
    category: 'ops',
    promise: 'Any meeting transcript becomes owners, deadlines, and next steps.',
    maker: '@actionminer',
    makerName: 'Ralph Delgado',
    email: 'ralph@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your transcript or notes. Get the decisions, the action items with owners and deadlines, and the open questions — a summary you can paste straight into your task tracker.',
    inputs: ['notes: the transcript or notes', 'team: who was there'],
    outputs: ['actions — owner + deadline per item', 'decisions — what was settled'],
    exampleIn: 'notes: rambling 30-min call about the Q3 launch',
    exampleOut: [
      'action: Sam owns pricing page copy, due Friday',
      'decision: launch date locked — Sept 1, no more moves',
      'open: who owns the email list cleanup? unanswered'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You turn meeting notes into actions. Return EXACTLY this JSON shape: {"actions":["owner: task, deadline"],"decisions":["what was settled"],"open":["unresolved questions"]} HARD RULES: - actions, decisions, open are flat arrays of STRINGS - only assign owners named in the notes, else mark UNASSIGNED - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'decision-memo-writer',
    name: 'Decision Memo Writer',
    emoji: '📄',
    category: 'ops',
    promise: 'A one-page decision memo — options, trade-offs, and a clear recommendation.',
    maker: '@memolab',
    makerName: 'Stella Grant',
    email: 'stella@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the decision, the options, and what you know. Get a structured memo: the question, 2-3 options with trade-offs, what you\\u2019d need to know to be sure, and a recommendation.',
    inputs: ['decision: what\\u2019s being decided', 'options: the choices on the table', 'context: what you know so far'],
    outputs: ['memo — one-page structured decision memo', 'recommendation — with confidence and conditions'],
    exampleIn: 'decision: build vs buy email platform · options: build, buy, hybrid',
    exampleOut: [
      'memo: question, options, trade-offs in 3 columns',
      'recommendation: buy now, build later — time-to-value beats customization this quarter',
      'condition: revisit if email becomes the core product'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write decision memos. Return EXACTLY this JSON shape: {"memo":"question, options with trade-offs, what\\u2019s unknown","recommendation":"clear pick with conditions"} HARD RULES: - memo and recommendation are plain STRINGS - mark assumptions as assumptions - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'weekly-report-builder',
    name: 'Weekly Report Builder',
    emoji: '📊',
    category: 'ops',
    promise: 'Your raw weekly numbers become a report your team actually reads.',
    maker: '@reportgen',
    makerName: 'Tyler Brooks',
    email: 'tyler@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste this week\\u2019s numbers and last week\\u2019s. Get a tight report: what moved, what\\u2019s on track, what needs a decision — written so a busy founder gets it in 60 seconds.',
    inputs: ['numbers: this week vs last week', 'goals: what you\\u2019re tracking toward'],
    outputs: ['report — the weekly write-up', 'decision_needed — what\\u2019s blocked'],
    exampleIn: 'numbers: revenue $38k vs $35k, ads spend $4k vs $4.5k · goal: $40k run-rate',
    exampleOut: [
      'report: "Revenue up 8.6% on 11% less ad spend — efficiency improving."',
      'flag: conversion dipped 0.2% — likely the new landing variant, decide by Friday',
      'on track: annual run-rate now $1.9M vs $2M goal'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 500, system: `You write weekly reports. Return EXACTLY this JSON shape: {"report":"60-second read: what moved, what\\u2019s on track","decision_needed":"what needs a decision"} HARD RULES: - report and decision_needed are plain STRINGS - show the actual math from the numbers - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'test-case-generator',
    name: 'Test Case Generator',
    emoji: '🧪',
    category: 'ops',
    promise: 'QA test cases from a feature description — happy path, edge cases, and the nasty ones.',
    maker: '@qagenie',
    makerName: 'Uma Krishnan',
    email: 'uma@cognition.cv',
    priceOwn: 29,
    priceMaintain: 9,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 3 a day',
    desc: 'Paste the feature you\\u2019re shipping. Get a test case suite: happy path, boundary values, empty states, permission cases, and the failure paths developers forget.',
    inputs: ['feature: what you built', 'inputs: what users can enter', 'roles: who can use it'],
    outputs: ['cases — grouped test cases with steps', 'edge_cases — the ones QA usually misses'],
    exampleIn: 'feature: coupon code field at checkout · roles: guest, logged-in',
    exampleOut: [
      'happy: valid code → discount applies, shown in summary',
      'edge: expired code → clear error, cart untouched',
      'nasty: 10,000-char code → no crash, input capped; guest + code + login switch → code survives'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write QA test cases. Return EXACTLY this JSON shape: {"cases":["grouped cases: steps and expected result"],"edge_cases":["cases QA usually misses"]} HARD RULES: - cases and edge_cases are flat arrays of STRINGS - each case must have steps and expected result - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'release-notes-writer',
    name: 'Release Notes Writer',
    emoji: '📣',
    category: 'ops',
    promise: 'Changelog entries from your commit or feature list — clear, honest, skimmable.',
    maker: '@changelog',
    makerName: 'Vince Lorenzo',
    email: 'vince@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your feature list or commit titles. Get grouped release notes (new, improved, fixed) with user-facing language — no internal jargon, no hype.',
    inputs: ['changes: your features/fixes list', 'audience: users or developers'],
    outputs: ['notes — grouped release notes', 'headline — the top line for the email'],
    exampleIn: 'changes: "dark mode", "fix: crash on empty cart", "faster sync"',
    exampleOut: [
      'new: Dark mode — easy on the eyes, everywhere.',
      'fixed: No more crash when your cart is empty.',
      'improved: Sync is noticeably faster.',
      'headline: "Dark mode, faster sync, and a crash gone."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write release notes. Return EXACTLY this JSON shape: {"notes":["grouped as new|improved|fixed, user-facing language"],"headline":"one top line"} HARD RULES: - notes is a flat array of STRINGS - no internal jargon, no hype - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'help-center-article',
    name: 'Help Center Article',
    emoji: '📖',
    category: 'ops',
    promise: 'A help article that answers the question once, so support stops answering it daily.',
    maker: '@helpdesk',
    makerName: 'Winnie Zhou',
    email: 'winnie@cognition.cv',
    priceOwn: 29,
    priceMaintain: 8,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste the question customers keep asking and the answer you give. Get a scannable help article: short intro, numbered steps, a screenshot placeholder, and the "still stuck" path.',
    inputs: ['question: the recurring support question', 'answer: how you currently solve it'],
    outputs: ['article — full help doc', 'tldr — the 1-line version for ticket replies'],
    exampleIn: 'question: "how do I change my billing email?" · answer: settings → account → email',
    exampleOut: [
      'article: "Change your billing email in 3 steps" with numbered steps',
      'tip: payments stay on the old email for 48h after the change',
      'tldr: "Settings → Account → Email. Done."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 600, system: `You write help center articles. Return EXACTLY this JSON shape: {"article":"title, short intro, numbered steps, stuck-path","tldr":"one line for ticket replies"} HARD RULES: - article and tldr are plain STRINGS - use the steps provided, add nothing that contradicts them - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'faq-generator',
    name: 'FAQ Generator',
    emoji: '❓',
    category: 'ops',
    promise: 'The FAQ your customers actually have — from your product, support chats, and reviews.',
    maker: '@faqbot',
    makerName: 'Xander Reed',
    email: 'xander@cognition.cv',
    priceOwn: 19,
    priceMaintain: 6,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste your product details, common questions, and review snippets. Get 10-12 real FAQs with short, confident answers — plus which ones to put on the product page vs the help center.',
    inputs: ['product: what you sell', 'questions: ones you\\u2019ve seen', 'facts: policies and specs'],
    outputs: ['faqs — 10-12 Q&As', 'placement — product page vs help center'],
    exampleIn: 'product: bamboo desk organizer · questions: "fits a laptop?" · facts: 30-day returns',
    exampleOut: [
      'Q: "Will it fit my 15-inch laptop?" A: "Yes — the main slot fits up to 16 inches."',
      'placement: laptop-fit → product page; returns → help center',
      'Q: "Is the bamboo real?" A: "Solid Moso bamboo, FSC-certified."'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write FAQs. Return EXACTLY this JSON shape: {"faqs":["Q: question A: short answer"],"placement":["which FAQs go on product page vs help center"]} HARD RULES: - faqs and placement are flat arrays of STRINGS - answers only from facts provided - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'schema-markup-generator',
    name: 'Schema Markup Generator',
    emoji: '🏷️',
    category: 'ops',
    promise: 'JSON-LD schema for your pages — products, reviews, FAQs — with the tags to test them.',
    maker: '@schemalab',
    makerName: 'Yvonne Ashford',
    email: 'yvonne@cognition.cv',
    priceOwn: 39,
    priceMaintain: 10,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Describe your page (product, review, FAQ, article) and paste the details. Get valid JSON-LD structured data you can paste into your page head, plus a validation checklist.',
    inputs: ['page_type: product · review · faq · article', 'details: name, price, rating, questions'],
    outputs: ['jsonld — valid schema markup', 'checklist — how to test it in Search Console'],
    exampleIn: 'page_type: product · details: "Bamboo Desk Organizer", $49, 4.6 stars',
    exampleOut: [
      'jsonld: Product schema with name, offers.price=49, aggregateRating 4.6',
      'checklist: paste into Rich Results Test → fix warnings → resubmit sitemap',
      'note: rating must come from real reviews — don\\u2019t mark up fake ones'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 700, system: `You write JSON-LD schema. Return EXACTLY this JSON shape: {"jsonld":"the complete valid JSON-LD markup as a string","checklist":["how to validate and ship it"]} HARD RULES: - checklist is a flat array of STRINGS - use only the details provided, no invented ratings - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
  {
    slug: 'alt-text-writer',
    name: 'Alt Text Writer',
    emoji: '♿',
    category: 'ops',
    promise: 'Descriptive alt text for your images — accessible, SEO-friendly, and human.',
    maker: '@alttxt',
    makerName: 'Zion Brooks',
    email: 'zion@cognition.cv',
    priceOwn: 15,
    priceMaintain: 5,
    version: 'v1.0.0 · 2026-08-08',
    demoCap: 'Free demo: 5 a day',
    desc: 'Paste image descriptions (or what the image shows) and get alt text that describes what\\u2019s actually there — with the key product words in, and keyword-stuffing out.',
    inputs: ['images: describe each image', 'context: page or purpose'],
    outputs: ['alt_text — one line per image', 'notes — what you deliberately included/excluded'],
    exampleIn: 'image: "white sneakers on marble with a plant" · context: product listing',
    exampleOut: [
      'alt: "White leather low-top sneakers on a marble surface with a potted plant"',
      'note: led with the product name and material — useful for both screen readers and image search',
      'note: skipped "stylish" — subjective words add no information'
    ],
    workflow: {
      steps: [
        { type: 'llm', role: 'main', model: 'deepseek-v4-flash', max_output: 400, system: `You write image alt text. Return EXACTLY this JSON shape: {"alt_text":["one line per image"],"notes":["what you included and why"]} HARD RULES: - alt_text and notes are flat arrays of STRINGS - describe facts, no subjective hype - Output ONLY the JSON object, no markdown fences, no commentary.` }
      ]
    },
    runPrice: 0.1,
    icon: null,
  },
];

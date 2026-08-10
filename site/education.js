// OMO — Education category workflows (PhonicsMaker)
// runPrice values are precomputed from deploy/cost-model.mjs (5x markup, $0.10 floor).
window.COGNITION_EDUCATION = [
  {
    slug: 'phonics-book-maker',
    name: 'Phonics Book Maker',
    emoji: '📚',
    maker: '@omo',
    makerHandle: '@omo',
    makerName: 'OMO · PhonicsMaker',
    category: 'Education',
    niche: 'Phonics',
    tags: ['education', 'phonics', 'teachers', 'reading'],
    promise: 'Turn a reading level and topic into a complete illustrated phonics book and printable PDF.',
    desc: 'Choose a reading level, target phonics skill, and topic. OMO writes the decodable story, creates eight page illustrations, and compiles the finished classroom-ready book as a PDF.',
    priceOwn: 19,
    priceMaintain: 5,
    free: false,
    freeReason: null,
    version: 'v1.0.0 · 2026-08-10',
    demoCap: 'Free demo: 1 preview a day',
    upvotes: 0,
    inputs: [
      'reading_level: learner age or reading stage',
      'phonics_skill: target sound, blend, or spelling pattern',
      'topic: story theme or classroom topic'
    ],
    outputs: [
      'story_pages — decodable story with page-by-page copy',
      'illustrations — 8 matching page images',
      'book_pdf — print-ready phonics book'
    ],
    exampleIn: 'early reader · short a / CVC words · a cat camping',
    exampleOut: [
      'story_pages: 8-page decodable story with teacher notes',
      'illustrations: 8 consistent camping scenes',
      'book_pdf: print-ready classroom booklet'
    ],
    workflow: {
      steps: [
        {
          type: 'llm',
          role: 'story',
          model: 'deepseek-v4-flash',
          max_output: 1200,
          system: 'You are an expert phonics teacher and decodable-book writer. Given a reading level, target phonics skill, and topic, return EXACTLY this JSON shape: {"title":"book title","teacher_note":"one short note","pages":[{"page":1,"text":"decodable page text","image_prompt":"child-safe illustration prompt"}]} HARD RULES: make exactly 8 pages, keep vocabulary decodable for the stated level, repeat the target skill naturally, use flat STRING fields, and output ONLY the JSON object.'
        },
        { type: 'api', api: 'openai_image', qty: 8, note: 'Generate one illustration for each story page.' },
        { type: 'api', api: 'pdf-compile', qty: 1, note: 'Compile the story pages and illustrations into a printable PDF.' }
      ]
    },
    runPrice: 1.85,
    cover: null,
    icon: 'covers/omo-phonics-book.svg',
    embedHtml: null,
    reelUrl: null
  },
  {
    slug: 'phonics-song-maker',
    name: 'AI Song + Animation Maker',
    emoji: '🎵',
    maker: '@omo',
    makerHandle: '@omo',
    makerName: 'OMO · PhonicsMaker',
    category: 'Education',
    niche: 'Phonics',
    tags: ['education', 'phonics', 'teachers', 'music'],
    promise: 'Turn a phonics rule and topic into an original learning song with an animated video.',
    desc: 'Give OMO a phonics rule, classroom topic, and learner age. It writes singable lyrics, creates the audio, and renders six animated scenes as one ready-to-play lesson video.',
    priceOwn: 49,
    priceMaintain: 12,
    free: false,
    freeReason: null,
    version: 'v1.0.0 · 2026-08-10',
    demoCap: 'Free demo: 1 lyric preview a day',
    upvotes: 0,
    inputs: [
      'phonics_rule: target sound, blend, or spelling pattern',
      'topic: song theme or classroom topic',
      'learner_age: target age range'
    ],
    outputs: [
      'lyrics — original verse, chorus, and repetition cues',
      'song_audio — classroom-ready original song',
      'animated_video — 6-scene learning video'
    ],
    exampleIn: 'silent e · space adventure · ages 6–7',
    exampleOut: [
      'lyrics: verse + repeating silent-e chorus',
      'song_audio: original 60-second learning song',
      'animated_video: 6 connected space scenes with lyric timing'
    ],
    workflow: {
      steps: [
        {
          type: 'llm',
          role: 'lyrics',
          model: 'deepseek-v4-flash',
          max_output: 500,
          system: 'You write original, age-appropriate phonics songs for classroom use. Given a phonics rule, topic, and learner age, return EXACTLY this JSON shape: {"title":"song title","verse":"short verse","chorus":"repeating chorus","scene_prompts":["scene 1","scene 2","scene 3","scene 4","scene 5","scene 6"]} HARD RULES: reinforce the target sound accurately, make every lyric original, keep scene_prompts a flat array of exactly 6 STRINGS, and output ONLY the JSON object.'
        },
        { type: 'api', api: 'elevenlabs_tts', qty: 1, note: 'Create the original learning-song audio.' },
        { type: 'api', api: 'replicate_run', qty: 6, note: 'Render six animated scenes for the finished video.' }
      ]
    },
    runPrice: 1.95,
    cover: null,
    icon: 'covers/omo-phonics-song.svg',
    embedHtml: null,
    reelUrl: null
  },
  {
    slug: 'phonics-worksheet-maker',
    name: 'Phonics Worksheet Maker',
    emoji: '✏️',
    maker: '@omo',
    makerHandle: '@omo',
    makerName: 'OMO · PhonicsMaker',
    category: 'Education',
    niche: 'Phonics',
    tags: ['education', 'phonics', 'teachers', 'printable'],
    promise: 'Turn a reading level and phonics skill into a printable worksheet PDF with an answer key.',
    desc: 'Choose the reading level, target skill, and exercise style. OMO writes level-appropriate practice questions and compiles a clean classroom worksheet plus answer key as a printable PDF.',
    priceOwn: 9,
    priceMaintain: 3,
    free: false,
    freeReason: null,
    version: 'v1.0.0 · 2026-08-10',
    demoCap: 'Free demo: 1 preview a day',
    upvotes: 0,
    inputs: [
      'reading_level: learner age or reading stage',
      'phonics_skill: target sound, blend, or spelling pattern',
      'exercise_style: matching, fill-in, sorting, or mixed'
    ],
    outputs: [
      'worksheet — level-appropriate printable exercises',
      'answer_key — teacher answer sheet',
      'worksheet_pdf — print-ready PDF'
    ],
    exampleIn: 'grade 1 · sh and ch digraphs · mixed practice',
    exampleOut: [
      'worksheet: 12 matching, sorting, and fill-in questions',
      'answer_key: complete teacher key',
      'worksheet_pdf: two-page print-ready file'
    ],
    workflow: {
      steps: [
        {
          type: 'llm',
          role: 'worksheet',
          model: 'deepseek-v4-flash',
          max_output: 900,
          system: 'You are an expert phonics teacher and worksheet designer. Given a reading level, phonics skill, and exercise style, return EXACTLY this JSON shape: {"title":"worksheet title","instructions":"one clear sentence","questions":["question 1"],"answer_key":["answer 1"]} HARD RULES: make exactly 12 age-appropriate questions, align every question to the target skill, keep questions and answer_key as flat arrays of STRINGS, and output ONLY the JSON object.'
        },
        { type: 'api', api: 'pdf-compile', qty: 1, note: 'Compile the worksheet and answer key into a printable PDF.' }
      ]
    },
    runPrice: 0.25,
    cover: null,
    icon: 'covers/omo-phonics-worksheet.svg',
    embedHtml: null,
    reelUrl: null
  }
];

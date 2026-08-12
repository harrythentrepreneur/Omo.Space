# TPT phonics structure research and Omo catalog plan

Research date: 2026-08-13

Scope: public, logged-out pages only; research and planning only

Build status: no worksheets, images, product files, listings, or site changes were created

## Executive decision

Omo should copy the marketplace logic, not any TPT seller's expression. The reusable model is: a deep subject taxonomy, small buy-once resources, related singles rolled into discounted bundles, free samples, visual previews, precise grade/skill metadata, verified-use social proof, and later a custom generator. Every Omo page, word list, answer key, illustration, title, thumbnail, description, and layout must be independently created.

The best first catalog is five original, evergreen PreK-2 products: CVC practice, digraphs and blends, controlled decodable readers, high-frequency/heart-word practice, and a diagnostic/progress-monitoring kit. Ship the five as useful standalone downloads, then offer an honest $35 collection after all five pass educator QA.

**Execution default if the founder delegates before answering the open questions:** classroom teachers first, en-US, static downloads inside Omo Education, one free CVC sample, individual-educator license draft, no third-party program-name alignment claims, and mandatory review by a qualified K-2 literacy educator. Luna may prepare internal artifacts under that default but may not publish them.

## Method and access note

- TPT's current public search route is [`/browse?search=phonics`](https://www.teacherspayteachers.com/browse?search=phonics). Both `https://www.teacherspayteachers.com/search?query=phonics` and `/search?search=phonics` returned TPT's “Page not found” page during this audit.
- The site was inspected in a real Chromium session with no signup or login. Public homepage, browse, category, product, store, Terms, and Help pages were used. No product download or preview file was saved.
- The phonics result count (660,000+) and all prices, ratings, follower counts, and sale prices below are dated observations, not durable guarantees. TPT can reorder results and sellers can change listings at any time.
- A second, read-only sol-agent audit independently checked the marketplace and phonics taxonomy. Its findings were then verified against the live pages and official Help pages.
- Product-page screenshots timed out, so visual-layout conclusions are limited to the rendered page structure, thumbnail slots, page text, metadata, and descriptions. Recommendations about US Letter page geometry are Omo specifications, not claims that every TPT product uses the same geometry.

## The TPT model in five bullets

1. TPT is a two-sided educator marketplace: its homepage describes it as the largest marketplace for PreK-12 resources and currently shows 7M+ teachers, 7M+ teacher-created lessons, and 1B+ resources downloaded ([homepage](https://www.teacherspayteachers.com/)).
2. The catalog is a faceted browse system. Phonics search exposes grade, subject, supports, price, format, and all-filter controls; the expanded filters add resource type, standards, theme, audience, language, and programs/methods ([phonics browse](https://www.teacherspayteachers.com/browse?search=phonics)).
3. The core unit is a buy-once licensed resource—commonly a PDF, presentation, Google file, image, audio/video, or ZIP—not a subscription. TPT supports numerous upload types ([supported file types](https://help.teacherspayteachers.com/hc/en-us/articles/360042429292-What-file-types-are-supported-on-TPT)); individual users need individual licenses ([multiple licenses](https://help.teacherspayteachers.com/hc/en-us/articles/360042448512-What-are-multiple-licenses)).
4. Merchandising compounds: related singles appear in bundles, bundles show component count plus list-price comparison, listings cross-link “also included in,” and free samples lead to paid units. Official TPT bundles contain 2-500 listed resources and automatically reflect component updates ([bundle rules](https://help.teacherspayteachers.com/hc/en-us/articles/360042429532-What-are-bundles)).
5. Trust is visible at the buying decision: thumbnails, preview, detailed contents, file/grade/subject/standards tags, ratings and review count, verified-purchase feedback, seller rating/followers, wish list, Q&A, and related products all sit on the resource page ([representative phonics listing](https://www.teacherspayteachers.com/Product/MEGA-Phonics-Worksheet-Bundle-Pre-K-Kindergarten--2793672)).

## 1. Platform structure

### 1.1 Discovery and category tree

The default phonics browse sort is Relevance. The live sort menu also offers Rating, Price (Ascending), and Most Recent ([phonics browse](https://www.teacherspayteachers.com/browse?search=phonics); [rating-sorted phonics](https://www.teacherspayteachers.com/browse?order=Rating&search=phonics)).

| Dimension | Public structure observed | Omo implication |
| --- | --- | --- |
| Grade | Elementary expands to Preschool, Kindergarten, and grades 1-5; middle and high school expand through grade 12; higher education, adult education, and not-grade-specific also exist. | Start with a visible PreK, K, 1, 2 facet. Do not bury grade only in copy. |
| Subject | English Language Arts contains Alphabet, Phonics & Phonological Awareness, Reading, Science of Reading, Sight Words, Spelling, Vocabulary, Writing, and adjacent categories. | Primary path: Education → ELA → Phonics; allow secondary tags rather than duplicate listings. |
| Price | Free, under $5, $5-10, $10+, and on sale. | Support Free, $2-8 singles, and $15-40 bundles; show normal and bundle price without fake scarcity. |
| Format | Audio, Digital, Easel, eBook, Fonts, Google Apps, Image, Interactive Whiteboards, Microsoft, PDF, and Video. Digital expands to Boom Cards, Canva, Prezi, Seesaw, and other digital resources. | Launch PDF first; reserve Slides and hosted-interactive formats for later variants. |
| Resource type | Classroom decor (including posters and word walls), forms, teacher tools (lessons, manuals, planners, curricula), printables, clip art, hands-on activities, centers, games, and student-practice tags such as worksheets. | Make resource type a first-class filter and product-schema field. |
| Instructional metadata | Standard, seasonal/holiday/theme, audience, language, programs/methods, supports. Audiences include homeschool, parents, staff/administrators, and TPT sellers. | Omo should support audience, accessibility/support, language, standard, and season independently. |

Relevant public category route: [Phonics & Phonological Awareness](https://www.teacherspayteachers.com/browse/english-language-arts/phonics-and-phonological-awareness).

### 1.2 Seller economics and transaction model

TPT currently offers two teacher-author seller plans ([official seller account rates](https://help.teacherspayteachers.com/hc/en-us/articles/360044408171-What-types-of-Seller-accounts-are-offered-on-TPT)):

| Plan | Membership | Seller payout | Transaction fee |
| --- | ---: | ---: | ---: |
| Basic | $29 one time | 55% | $0.30 per resource |
| Premium | $59.95/year | 80% | $0.15 per resource, only on orders totaling under $3 |

TPT pays seller earnings monthly through Hyperwallet ([payment FAQ](https://help.teacherspayteachers.com/hc/en-us/articles/360042580932-How-do-I-get-paid-as-a-Seller)). Digital purchases are generally final, with limited exceptions such as damaged/missing files, misrepresentation, technical limitations, duplicate purchases, or files never accessed ([refund policy](https://help.teacherspayteachers.com/hc/en-us/articles/360042884331-What-is-your-refund-policy)).

The implication is not that Omo should reproduce TPT's fees. It is that low-ticket downloads work when the product is reusable, discovery is strong, and sellers can ladder a buyer from free sample → focused single → bundle. Omo's 85/15 marketplace-discovered and 95/5 creator-referred license economics are materially more creator-friendly than TPT's public payout rates; the details are in [Omo's business-model design](./06-business-model.md).

### 1.3 Listing page and social proof

The representative 50-page phonics pack exposes the following page model ([live listing](https://www.teacherspayteachers.com/Product/MEGA-Phonics-Worksheet-Bundle-Pre-K-Kindergarten--2793672)):

- Above the fold: title, price, aggregate rating/review count, Add to cart, and Wish List.
- Media: four product-preview image positions plus a larger “View Preview” control. TPT officially allows up to four thumbnails; its downloadable previews are commonly 1-3 pages, and TPT says products with previews are better positioned to sell ([thumbnail/preview FAQ](https://help.teacherspayteachers.com/hc/en-us/articles/360042865851-What-s-the-difference-between-a-thumbnail-and-a-preview)).
- Information architecture: Description, Reviews, Q&A, and More from seller; descriptions can enumerate page/activity contents and link a free sample.
- Highlights: Digital download/file type, grade band, “mostly used with” grade, subjects, standards when present, tags, and page count.
- Social proof: rating distribution, verified-purchase reviews, grade-use distribution, value/expectation signals, seller store rating, seller review total, Follow CTA, and follower count.
- Cross-selling: “also included in” bundle links, related products, more from the teacher-author, and the seller's custom categories.
- License: TPT resources are licensed, not resold outright. Its Terms describe a limited individual-use license and prohibit transferring/sharing without more licenses ([Terms of Service](https://www.teacherspayteachers.com/Terms-of-Service/); [multiple licenses](https://help.teacherspayteachers.com/hc/en-us/articles/360042448512-What-are-multiple-licenses)).

Omo should implement the same decision-support jobs—clear content, preview, license, evidence, and related products—using its own UI and copy.

## 2. Phonics deep dive

### 2.1 Catalog types found

Prices below are ranges observed in relevance-ranked samples on 2026-08-13, not a statistical census.

| Type | Typical instructional structure and format | Grade band | Observed price convention | Evidence |
| --- | --- | --- | --- | --- |
| Alphabet/letter-sound sheets | One target letter/sound; identify, trace/write, match or color pictures; printable PDF, often blackline/no-prep. | PreK-1 | $1-3 focused; $5-8 broader set | [phonics worksheets](https://www.teacherspayteachers.com/browse?search=phonics%20worksheets) |
| CVC and word-family worksheets | Blend/read/write, match word to picture, segment phonemes, sort, word-building, short sentence; packs of roughly 25-70 pages are common in the sampled leaders. | PreK-1 | $3.97-5 sampled; larger mixed packs can be $8-12 | [CVC browse](https://www.teacherspayteachers.com/browse?search=CVC) |
| Blends, digraphs, trigraphs | Initial/final sound sets; word/picture sort, cloze, spell, I Spy, read-and-find, cut/paste; printable PDF. | K-2 | $1 entry pack; $4-5 larger pack | [digraphs](https://www.teacherspayteachers.com/browse?search=digraphs) |
| Long vowels/CVCe, vowel teams, diphthongs | Pattern-specific word work, picture sorts, cloze, passages, brochures, centers, and fluency practice. | K-2, sometimes 3 | $1 center; $4.25-7.50 pack | [vowel teams](https://www.teacherspayteachers.com/browse?search=vowel%20teams) |
| R-controlled vowels | Pattern sort/list, sentence or passage hunt, mini-book, game/cards, spelling practice. | 1-3 | $2.50-5 focused pack | [r-controlled vowels](https://www.teacherspayteachers.com/browse?search=r%20controlled%20vowels) |
| Decodable readers and passages | Skill-controlled mini-books or passages, often with word warm-up, heart words, comprehension/sequencing, differentiated levels, color and blackline versions. | K-2, some K-3 | $3-5 focused set; $12-30 bundle | [decodable readers](https://www.teacherspayteachers.com/browse?search=decodable%20readers) |
| Sight/high-frequency/heart words | One word per predictable page: read, recognize, trace, write, build, find, and use in context; flash cards and decodable sentences also appear. | PreK-2 | $1.75-5 focused; $7-10 large/bundle | [sight words](https://www.teacherspayteachers.com/browse?search=sight%20words) |
| Phonemic/phonological awareness | Oral word lists and routines for rhyme, syllables, isolation, blending, segmenting, substitution and manipulation; ring cards, intervention binders, assessment and slides. | PreK-1 primarily | $4 routine cards; $8-12 packs; about $19 larger bundle | [phonemic awareness](https://www.teacherspayteachers.com/browse?search=phonemic%20awareness) |
| Flashcards/task cards | Small printable cards, picture/word reveal, segment/blend cues, self-checking back or answer strip; often 4-up or 6-up for cut/laminate. | PreK-2 | $3-6 focused set | [CVC browse](https://www.teacherspayteachers.com/browse?search=CVC) |
| Games, puzzles and BINGO-style practice | Board/guessing games, word building, roll-and-read, I Spy, mystery pictures, puzzles and partner games; printable or interactive. | K-3 | $1.10-6.50 single; around $20 bundle | [phonics games](https://www.teacherspayteachers.com/browse?search=phonics%20games) |
| Centers/stations | Sort cards, mats, folders, pocket-chart pieces, cut/paste, recording sheets, reusable boards, directions and keys. | PreK-2 | $1-8 focused; $20-35 year/bundle | [phonics centers](https://www.teacherspayteachers.com/browse?search=phonics%20centers) |
| Posters, anchor charts, word/sound walls | Large reference visual per rule/pattern plus examples; color and printer-friendly variants; sometimes card-size versions. | K-3 | about $5 focused; $12-18 extensive library | [phonics posters](https://www.teacherspayteachers.com/browse?search=phonics%20posters) |
| Assessments and progress monitoring | Student stimulus pages, teacher record form, decoding/encoding, real and pseudo-word checks, phonemic section, pre/post or repeated probes, scoring guide. | K-3 | $3-7.50 single; about $10-16 bundle | [phonics assessment](https://www.teacherspayteachers.com/browse?search=phonics%20assessment) |
| Scope/sequence and teacher guides | Ordered skill map, lesson or intervention planning, assessment links, word/sentence practice, tracking sheets. | K-4 or not grade specific | $5.50 planner; $12.50-37.50 assessment/content bundle | [scope and sequence](https://www.teacherspayteachers.com/browse?search=phonics%20scope%20and%20sequence) |
| Interactive Slides/PowerPoint | Predictable explicit-instruction routine, blending drill, guided practice, decoding/encoding, sentence practice, animation or drag/drop; often hundreds of slides. | K-3 | $12-15 substantial set; $18-68 bundle | [Google Slides](https://www.teacherspayteachers.com/browse?search=phonics%20Google%20Slides) |
| Boom Cards/other digital decks | Self-checking drag/drop or choice tasks, audio support, immediate feedback, assignable skill decks. | K-3 | $3.50-8.50 deck; $15-79 bundle | [Boom Cards](https://www.teacherspayteachers.com/browse?search=phonics%20Boom%20Cards) |
| Seasonal variants | Evergreen skill sequence with holiday/season art, vocabulary and search intent; print packs or digital slides. | PreK-2 | $2.25-4.50 single; around $9 bundle | [Halloween phonics](https://www.teacherspayteachers.com/browse?search=Halloween%20phonics) |
| Free lead magnets | A short, complete sample from a larger unit, usually linked prominently to the paid sequence. | PreK-2 | Free | [free phonics browse](https://www.teacherspayteachers.com/browse/free?search=phonics); [8-page free example](https://www.teacherspayteachers.com/Product/Free-Phonics-Worksheets-Letter-Sounds-CVC-Words-Beginning-Initial-Sounds-3875284) |

### 2.2 Relevance-ranked and rating-ranked patterns

Representative public observations:

| Listing archetype | Observed merchandising | Evidence |
| --- | --- | --- |
| 50-page early-phonics PDF | $5; PreK-1; 4.86/5 from 1,922 ratings; free sample link; itemized activity count. | [product](https://www.teacherspayteachers.com/Product/MEGA-Phonics-Worksheet-Bundle-Pre-K-Kindergarten--2793672) |
| Broad worksheet bundle | 24 products; displayed component total $277 and $29 sale price; K-2; 4.97/5 from 887 ratings. | [product](https://www.teacherspayteachers.com/Product/MEGA-Phonics-Worksheet-Bundle-SCIENCE-OF-READING-HUGE-BUNDLE-12983920) |
| Centers bundle | 32 products; displayed component total $195.50 and $35 price; K-2; 4.96/5 from 1,292 ratings. | [product](https://www.teacherspayteachers.com/Product/THE-ULTIMATE-PHONICS-BUNDLE-Phonics-Centers-Science-of-Reading-10848460) |
| CVC fluency/comprehension pack | $6.50; K-1; printable and digital claim; 4.86/5 from 10,807 ratings. | [product](https://www.teacherspayteachers.com/Product/CVC-Reading-Fluency-Comprehension-Passages-Digital-Resources-Sequencing-Phonics-1668935) |
| Decodable-reader collection | Six-product bundle; displayed $40 total and $30 price; K-1; 4.90/5 from 1,513 ratings. | [product](https://www.teacherspayteachers.com/Product/Decodable-Readers-Phonics-Books-HUGE-BUNDLE-Science-of-Reading-7129591) |
| Yearlong curriculum | Displayed $135 original and $59.99 price; PreK-2; 4.93/5 from 6,495 ratings. | [product](https://www.teacherspayteachers.com/Product/Science-of-Reading-Guided-Phonics-Beyond-Yearlong-Curriculum-Decodable-Books-6967851) |
| Rating-sorted focused pack | A vowel-team activity set appeared first at 5.0/5 from 1,158 ratings and a displayed $5.99 sale price. | [rating-sorted browse](https://www.teacherspayteachers.com/browse?order=Rating&search=phonics) |

### 2.3 Top-seller formula

The following is an inference from the live relevance/rating result sets, not a claim about TPT's ranking algorithm:

1. **Title = skill + format + grade/use case.** Titles front-load phrases such as phonics, CVC, worksheets, decodable, kindergarten, fluency, center, intervention, or bundle. Omo should be descriptive without copying a seller's exact title.
2. **Immediate specificity.** Winning cards say how many pages/products/readers/slides are included and which skill families are covered.
3. **Low-prep and predictable routine.** “No prep,” “print and go,” independent center use, repeated page structure, answer keys, and differentiated variants reduce teacher risk.
4. **Proof close to price.** High rating volume, verified reviews, grade-use data, seller followers, standards tags, page count, and a detailed preview answer “will this work tomorrow?”
5. **Bundle ladder.** A focused single links upward to a bundle; the bundle shows component count and savings; an honest free sample sends buyers into the sequence. TPT officially recommends clear bundle contents and careful, non-excessive discounting ([bundle listing guidance](https://help.teacherspayteachers.com/hc/en-us/articles/360042865171-What-s-the-best-way-to-post-a-bundle-on-TPT)).
6. **Evergreen core, seasonal acquisition.** The pedagogy stays stable while Halloween, winter, back-to-school, and other themes create additional discovery routes.
7. **Method and standards language.** “Science of Reading,” structured literacy, and CCSS tags recur. Omo must substantiate any such claim; it must not use third-party program names as a shortcut to credibility without a trademark/compatibility review.
8. **Promotional urgency is common but not mandatory.** Flash-sale language and very large comparison-price anchors appear often. Omo should adapt the value communication but use real, durable prices and verifiable savings—no fake countdowns or inflated anchors.

## 3. Copy-adapt boundary and IP rules

### 3.1 What Omo can adapt

- Marketplace ideas: faceted browse, product cards, wish list, reviews, previews, related products, creator profiles, license choices, and free/paid/bundle ladder.
- Non-proprietary instructional categories: alphabet sounds, CVC, blends, digraphs, CVCe, vowel teams, r-controlled vowels, phonemic awareness, high-frequency words, decodable text, assessment, games, centers, posters, and teacher guides.
- Generic resource formats: printable worksheet, mini-book, task card, board game, poster, recording sheet, answer key, teacher note, scope/sequence, and downloadable bundle.
- Market conventions: skill-first names, transparent page count, grade/subject/standard metadata, four thumbnails, short downloadable preview, $2-8 focused downloads, and $15-40 bundles.

These are patterns and functional ideas. Omo should still use its own information architecture and visual system rather than cloning TPT's trade dress.

### 3.2 What must be original

- Every activity prompt, instruction, sentence, passage, question, answer key, word-selection rationale, and sequence/arrangement.
- Every page composition, grid, icon placement, cover, thumbnail, table of contents, and teacher note.
- Every illustration and mascot. Generate from Omo prompts; do not upload a TPT thumbnail or worksheet as an image reference.
- Every product title and description. Keyword research may inform them; seller wording must not be paraphrased line by line.
- Every underlying asset license/provenance record.

TPT's own IP guidance says a seller should include material only when they created it, have permission, are within fair use, or the material is public domain ([copyright FAQ](https://help.teacherspayteachers.com/hc/en-us/articles/360042548092-How-can-I-know-if-something-I-want-to-include-as-part-of-my-resource-is-copyrighted); [IP policy](https://help.teacherspayteachers.com/hc/en-us/articles/360042197012-What-is-TPT-s-intellectual-property-policy)). Its product workflow also requires the seller to affirm that bundle materials do not infringe third-party rights ([bundle posting guidance](https://help.teacherspayteachers.com/hc/en-us/articles/360042865171-What-s-the-best-way-to-post-a-bundle-on-TPT)).

### 3.3 Working rule

**Copy the model, never the product.** Do not inspect or ingest paid files; do not trace screenshots; do not ask an image model to imitate a named TPT seller, existing illustrator, franchise, or character. Maintain a provenance manifest for Omo-authored text, standards sources, generated image prompts, model/date, human edits, and final asset hashes. This document is product planning, not legal advice; counsel should review the license and AI-asset policy before sale at scale.

## 4. Omo phonics catalog plan

### 4.1 Shared page and visual system

This is an Omo specification, not an observed TPT template.

| Element | Omo v1 specification |
| --- | --- |
| Page | US Letter 8.5 × 11 in, portrait by default; 0.4 in safe margin; 0.5 in hole-punch-safe left option; cards/boards may use landscape. |
| Print | Full-color PDF plus printer-friendly blackline PDF in the same download. Avoid full-page ink coverage. |
| Header | Product/skill label, short student-facing instruction (one sentence), name/date line, optional small original mascot. |
| Body | One dominant task; 6-10 items for K-1; consistent grid and response area; at least 14 pt student text, larger for target graphemes. |
| Footer | Page ID/version, tiny Omo mark, license reminder; no distracting upsell on student pages. |
| Pack order | Cover → contents → teacher setup/skill scope → student pages in instructional order → quick checks → answer keys → accessibility/printing note → license. |
| Answer keys | Render from the same structured content manifest as the student page. Never recreate answers manually after layout. |
| Accessibility | High contrast, color never carries the only meaning, dyslexia-friendly spacing, no decorative script, alt descriptions in source manifest. |

**Image style lock `OMO_PHONICS_FRIENDS_V1`:** “Original friendly early-learning classroom illustration, simple rounded shapes, consistent dark-navy 5 px outline, flat coral, mint, sunflower and sky-blue palette, generous white space, one clearly recognizable subject, age-neutral and inclusive, calm cheerful expression, no text, no letters, no numbers, no logo, no watermark, no branded or existing character, no artist imitation, transparent or pure-white background, raster PNG.”

The image model must never draw instructional words. Luna places all letters and text with deterministic fonts after image generation. Generate and approve reusable noun/mascot assets once, then reuse them across pages; do not pay to regenerate the same object per sheet.

### 4.2 Phase 1 — five flagship products

Build-time estimates are Luna agent-hours for content, assets, layout, and self-QA. They exclude founder/educator review and marketplace implementation.

#### P1. Omo CVC Word Families: Read, Map, Write & Check

| Field | Plan |
| --- | --- |
| Audience | Kindergarten-1st; intervention and homeschool secondary audience |
| Download | 64-page PDF: cover/contents (2), teacher guide and skill map (3), 40 student sheets, 5 quick checks, 12 answer-key pages, license/print note (2); color + blackline variants |
| Student-page sequence | Picture/sound warm-up → phoneme boxes → blend/read → match → write/encode → one controlled sentence → mixed review; short-vowel bands followed by cumulative practice |
| Original content gate | Build an Omo-owned controlled lexicon; flag dialect-sensitive or ambiguous picture words; every answer must be derivable from the manifest |
| Image manifest | 50-70 approved noun icons plus Omo mascot poses; reuse icons rather than one-off decoration |
| Per-sheet prompt templates | `ICON`: append “single [target_noun], canonical front/three-quarter view, isolated, no props except those essential to disambiguate the noun” to the style lock. `SEGMENT`: “Omo owl gently tapping three blank sound counters on a desk; no letters or words.” `COVER`: “Omo owl arranging three blank rounded tiles beside three small original object icons; open white center for title added later.” |
| Luna time | 10-14 hours |
| Suggested price | $6 single; $5.10 creator payout on marketplace discovery or $5.70 on creator link under Omo's 85/95 license split; first-party Omo retains its own contribution after fees/refunds |
| Listing title | **CVC Word Families Worksheets for Kindergarten \| Read, Map, Write & Assess** |
| Description | “A 64-page, print-ready progression from short-vowel picture mapping to cumulative CVC decoding and encoding, with quick checks and answer keys.” |
| Tags/standards | `CVC`, `short vowels`, `word families`, `phonics`, `decoding`, `encoding`, `orthographic mapping`, `worksheets`, `kindergarten`, `first grade`; candidate CCSS RF.K.2d/RF.K.3a/RF.1.3b only after educator verification |
| Preview | Four thumbnails: cover, progression map, three reduced sample sheets, what-is-included panel. Three-page preview: contents, one sample sheet, matching key with “sample” footer. |

#### P2. Omo Digraphs & Blends: Sort, Build, Read & Play

| Field | Plan |
| --- | --- |
| Audience | K-2; whole class, literacy centers, intervention |
| Download | 72-page PDF: teacher notes/scope (4), 36 worksheets, 12 center/task-card pages, 4 reusable game boards, 14 keys/recording sheets, cover/license (2); color + blackline |
| Student-page sequence | Hear/identify → sort initial/final pattern → build/spell → read phrases/sentences → mixed discrimination → partner game |
| Original content gate | Independently sequence common consonant digraphs and initial/final blends; do not mirror a seller's group/order or branded curriculum lesson numbering |
| Image manifest | 60-80 original noun icons chosen for unambiguous target position; 4 mascot/game poses; blank tiles and counters drawn in layout code |
| Per-sheet prompt templates | `SORT`: style lock + “single [target_noun], target sound occurs at [initial/final] position, isolated, visually unmistakable.” `GAME`: “Omo owl and fox cub playing a simple blank path board with counters, friendly cooperative mood, no text or numbers.” `COVER`: “Omo owl joining two blank puzzle pieces that form one glowing sound symbol area; leave the symbol area empty.” |
| Luna time | 12-16 hours |
| Suggested price | $8; creator keeps $6.80 marketplace / $7.60 creator-referred |
| Listing title | **Digraphs and Consonant Blends Worksheets & Centers \| Kindergarten-2nd** |
| Description | “Original print-and-go practice that moves from sound identification and sorting to spelling, sentence reading, task cards, and four reusable games.” |
| Tags/standards | `digraphs`, `consonant blends`, `phonics centers`, `word work`, `task cards`, `games`, `decoding`, `spelling`, `K-2`; candidate RF.K.3/RF.1.3/RF.2.3 after review |
| Preview | Four thumbnails: scope strip, worksheet collage, cards/game close-up, answer-key/print-options panel. Three pages: scope, one sheet, one game board. |

#### P3. Omo Step-by-Step Decodable Readers — Set 1

| Field | Plan |
| --- | --- |
| Audience | K-1 core; 2nd-grade intervention |
| Download | 88-page PDF: 12 original 6-page foldable readers (72), teacher scope/heart-word ledger (4), word warm-ups (4), comprehension/retell pages (4), keys/printing/license (4); full-page and booklet print modes |
| Reader structure | Skill banner → preteach 3-5 spellings/declared irregular words → original 6-page controlled story → one literal and one sequencing/retell check → optional fluency reread |
| Original content gate | Automated decodability report per story: every token is previously taught, in the target set, or explicitly declared as an irregular/heart word. Human educator checks naturalness, representation, and comprehension. No adaptation of any seller story. |
| Image manifest | 3 recurring original characters, 2-3 reusable settings, 4-6 illustrations per story; visual consistency references only Omo-owned prior assets |
| Per-sheet prompt templates | `CHARACTER`: style lock + “[Omo character ID and locked appearance] performing [simple action] in [setting], exactly [named props], one clear focal action, leave lower quarter uncluttered for text added later.” `SEQUENCE`: same prompt plus “match prior accepted character sheet; do not add characters or written signs.” `COVER`: three original Omo characters reading small blank booklets in a sunny classroom nook, title-safe upper third. |
| Luna time | 18-24 hours |
| Suggested price | $15; creator keeps $12.75 marketplace / $14.25 creator-referred |
| Listing title | **Decodable Readers Set 1 \| CVC, Digraphs & Early Blends \| K-1** |
| Description | “Twelve original, skill-controlled foldable readers with word warm-ups, declared heart words, comprehension checks, and a machine-readable decodability report.” |
| Tags/standards | `decodable readers`, `controlled text`, `CVC`, `digraphs`, `blends`, `fluency`, `comprehension`, `guided reading`, `K-1`; candidate RF.K.3/RF.K.4/RF.1.3/RF.1.4 after review |
| Preview | Four thumbnails: 12-reader scope, one spread close-up, print/fold diagram, decodability/teacher-support panel. Three pages: scope, one complete sample reader spread sequence, teacher ledger excerpt. |

#### P4. Omo Heart Words & High-Frequency Words Practice Pack

| Field | Plan |
| --- | --- |
| Audience | PreK-1 core; 2nd-grade intervention |
| Download | 120-page PDF: 96 predictable word-practice pages, 8 cumulative read/find sheets, 6 sentence/card pages, 8 keys/teacher pages, cover/license (2); editable source manifest, not buyer-editable v1 |
| Student-page sequence | Say/read → mark regular sound-spelling parts → identify the unexpected part → trace once → write from memory → read in an original decodable sentence → cumulative retrieval |
| Original content gate | Founder chooses the target list/source; Omo independently authors every sentence and mapping explanation. Do not claim a proprietary list or program alignment without permission. |
| Image manifest | Small scene/icon only where it clarifies the original sentence; mascot gesture poses; most pages remain low-ink and text-led |
| Per-sheet prompt templates | `WORD_PAGE`: style lock + “Omo owl pointing to a large completely blank teaching card, encouraging pose, no symbols.” `SENTENCE`: style lock + “single scene depicting [original_sentence_semantics], only the named characters/objects, no signs or printed material.” `COVER`: “Omo owl collecting blank star-shaped cards in a calm classroom, title-safe center.” |
| Luna time | 12-16 hours |
| Suggested price | $8; creator keeps $6.80 marketplace / $7.60 creator-referred |
| Listing title | **Heart Words & High-Frequency Word Worksheets \| Read, Map, Write, Use** |
| Description | “A predictable, low-ink routine for mapping, recalling, and reading high-frequency words in original controlled sentences, plus cumulative retrieval.” |
| Tags/standards | `heart words`, `high-frequency words`, `sight words`, `word mapping`, `fluency`, `sentence reading`, `kindergarten`, `first grade`; standards only after list and sequence review |
| Preview | Four thumbnails: routine anatomy, sheet collage, cumulative review, ink/answer-key options. Three pages: guide, sample practice page, cumulative check. |

#### P5. Omo Phonics Diagnostic & Progress Monitoring Kit

| Field | Plan |
| --- | --- |
| Audience | K-2 classroom/intervention; 3rd-grade diagnostic use only after validation |
| Download | 48-page PDF: administration guide (4), student forms (10), teacher record/scoring forms (12), skill probes (12), group summary and planning forms (6), reproducibility/license/keys (4) |
| Assessment structure | Letter-sound optional baseline → phoneme awareness → pattern-based real/pseudo-word decoding → encoding/dictation → controlled sentence reading → score by skill band → repeatable short probes |
| Original content gate | Independent item bank with parallel difficulty; pseudo-words checked for accidental real/offensive words; no diagnostic/clinical claims; educator validates directions, ceiling/floor rules, scoring, and standards mapping |
| Image manifest | Minimal. Neutral mascot on section dividers only; assessment stimuli use layout shapes or independently generated noun icons where truly required |
| Per-sheet prompt templates | `DIVIDER`: style lock + “Omo owl holding a blank clipboard and pencil, neutral encouraging expression, no text.” `STIMULUS`: `ICON` template from P1 with strict one-object output. `COVER`: “Omo owl reviewing a blank progress chart with simple unlabeled bars, calm professional classroom tone.” |
| Luna time | 8-12 hours |
| Suggested price | $7; creator keeps $5.95 marketplace / $6.65 creator-referred |
| Listing title | **Phonics Assessment & Progress Monitoring Kit \| K-2 Decoding and Encoding** |
| Description | “A printable, skill-banded classroom screener with student pages, teacher records, scoring guidance, and repeatable progress probes; not a clinical diagnostic.” |
| Tags/standards | `phonics assessment`, `screener`, `progress monitoring`, `decoding`, `encoding`, `intervention`, `small group`, `K-2`; verified standards added only after review |
| Preview | Four thumbnails: assessment map, student/teacher pairing, score-to-plan flow, included forms. Three pages: administration summary, sample student form, matching record form with dummy data. |

#### Phase 1 commercial ladder

| Offer | Price | Marketplace-discovered creator keeps 85% | Creator-referred keeps 95% |
| --- | ---: | ---: | ---: |
| CVC pack | $6 | $5.10 | $5.70 |
| Digraphs & blends | $8 | $6.80 | $7.60 |
| Decodable readers | $15 | $12.75 | $14.25 |
| Heart words | $8 | $6.80 | $7.60 |
| Assessment | $7 | $5.95 | $6.65 |
| Five-product launch collection | $35 vs. $44 singles (20.5% real savings) | $29.75 | $33.25 |

Omo's 85/95 split applies to third-party creator-owned license revenue under the current internal model; taxes, refunds, chargebacks, and the final treatment of processing must follow the marketplace terms. These five founder-directed products would be first-party Omo resources, so the split is a benchmark and future teacher-author template rather than an internal payout. See [business model](./06-business-model.md) and [positioning](./positioning.md).

### 4.3 Phase 2 — 25 focused singles

Default contract for every row: original US Letter PDF; cover + teacher note + student pages + answer key + license; color and blackline; `OMO_PHONICS_FRIENDS_V1`; four listing thumbnails; a two-page preview containing contents/sample; description formula “No-prep [skill] practice through [activities], with [count] pages and keys”; tags always include the listed skill, `phonics`, grade, format, and use case. `ICON(x)`, `MASCOT(action)`, and `SCENE(meaning)` refer to the safe prompt templates in Phase 1. Titles below are the proposed listing titles.

| # | Product / grade | PDF and activity structure | Images and prompt key | Luna time | Price | Unique listing tags/hook |
| ---: | --- | --- | --- | ---: | ---: | --- |
| 1 | Short A Word Families / K-1 | 24 pp; map, build, read, write, mixed check | 20-25 `ICON(noun)` | 4-6h | $3 | `short a`, `word families`, `morning work`; one-sound focus |
| 2 | Short E Word Families / K-1 | Same reliable routine, independently authored items | 20-25 `ICON(noun)` | 4-6h | $3 | `short e`, `encoding`, `literacy center` |
| 3 | Short I Word Families / K-1 | 24 pp; include dialect/visual ambiguity audit | 20-25 `ICON(noun)` | 4-6h | $3 | `short i`, `decoding`, `word work` |
| 4 | Short O Word Families / K-1 | 24 pp; map/build/read/write/check | 20-25 `ICON(noun)` | 4-6h | $3 | `short o`, `CVC`, `independent practice` |
| 5 | Short U Word Families / K-1 | 24 pp; map/build/read/write/check | 20-25 `ICON(noun)` | 4-6h | $3 | `short u`, `CVC`, `home practice` |
| 6 | Mixed CVC Fluency & Sentences / K-1 | 30 pp; phrase ladder, controlled sentence, reread tally, literal check | 12 `SCENE(sentence)` | 6-8h | $5 | `CVC fluency`, `controlled sentences`, `intervention` |
| 7 | L-Blends Word Work / K-2 | 28 pp; initial sort, build, cloze, sentence hunt | 28 `ICON(noun)` | 5-7h | $4 | `l blends`, `CCVC`, `centers` |
| 8 | R-Blends Word Work / K-2 | 28 pp; same page grammar, original item set | 28 `ICON(noun)` | 5-7h | $4 | `r blends`, `CCVC`, `spelling` |
| 9 | S-Blends Word Work / K-2 | 32 pp; include three-consonant extension separately marked | 32 `ICON(noun)` | 6-8h | $4 | `s blends`, `CCVC`, `differentiation` |
| 10 | Ending Blends / 1-2 | 28 pp; hear, sort, spell, read, sentence search | 28 `ICON(noun)` | 5-7h | $4 | `final blends`, `CVCC`, `decoding` |
| 11 | CH & SH Digraphs / K-2 | 26 pp; initial/final contrast, build, read, game | 24 `ICON(noun)` + `MASCOT(game)` | 5-7h | $4 | `ch`, `sh`, `digraphs`, `print and go` |
| 12 | TH, WH & PH Digraphs / K-2 | 30 pp; explicitly teach voiced/unvoiced distinction only after review | 28 `ICON(noun)` | 6-8h | $4 | `th`, `wh`, `ph`, `digraph practice` |
| 13 | Final Digraphs & Early Trigraphs / 1-2 | 30 pp; pattern sort, map, spell, passage hunt | 24 `ICON(noun)` + 4 `SCENE` | 6-8h | $5 | `final digraphs`, `trigraphs`, `advanced phonics` |
| 14 | CVCe / Silent-E Long Vowels / K-2 | 36 pp; compare CVC/CVCe, build, transform, read | 30 `ICON(noun)` + `MASCOT(transform)` | 7-9h | $5 | `CVCe`, `silent e`, `long vowels` |
| 15 | AI & AY Vowel Teams / 1-2 | 24 pp; position sort, spell, sentence, passage hunt | 20 `ICON(noun)` + 3 `SCENE` | 5-7h | $4 | `ai`, `ay`, `vowel teams` |
| 16 | EE & EA Vowel Teams / 1-2 | 24 pp; discriminate spellings without overstating a rule | 20 `ICON(noun)` + 3 `SCENE` | 5-7h | $4 | `ee`, `ea`, `long e` |
| 17 | OA, OW & OE Vowel Teams / 1-2 | 28 pp; position sort, mapping, fluency | 24 `ICON(noun)` + 3 `SCENE` | 6-8h | $4 | `oa`, `ow`, `oe`, `long o` |
| 18 | OI/OY and OU/OW Diphthongs / 1-2 | 32 pp; two clearly separated modules plus cumulative sort | 28 `ICON(noun)` + 4 `SCENE` | 7-9h | $5 | `diphthongs`, `oi oy`, `ou ow` |
| 19 | AR & OR R-Controlled Vowels / 1-2 | 26 pp; sound map, position sort, word hunt, mini-book | 22 `ICON(noun)` + 4 `SCENE` | 6-8h | $4 | `bossy r`, `ar`, `or`, `mini book` |
| 20 | ER, IR & UR R-Controlled Vowels / 1-3 | 30 pp; same-sound spelling sort, mapping, sentence work | 24 `ICON(noun)` + 4 `SCENE` | 6-8h | $5 | `er ir ur`, `r controlled`, `spelling patterns` |
| 21 | Phonics Pattern Posters & Mini Cards / K-2 | 36 pp; full-page reference plus 4-up student cards, color/B&W | `MASCOT(example)` and 20 icons | 6-8h | $5 | `posters`, `anchor charts`, `reference cards` |
| 22 | Phonics Flashcards & Word-Mapping Cards / K-2 | 40 pp; 4-up cards, fronts/backs, teacher index | 60 approved icons, no scenes | 7-10h | $6 | `flashcards`, `task cards`, `word mapping` |
| 23 | Phonics BINGO & Board Games / K-2 | 32 pp; 12 boards, calling cards, 4 path games, keys | 36 icons + 3 `MASCOT(game)` | 7-10h | $6 | `phonics games`, `BINGO`, `partner practice` |
| 24 | Phonemic Awareness Oral Routine Cards / PreK-1 | 42 pp; rhyme, syllable, isolate, blend, segment, manipulate; no print decoding demand | Minimal `MASCOT(gesture)` | 8-10h | $6 | `phonemic awareness`, `oral routines`, `on a ring` |
| 25 | Phonics Scope, Sequence & Small-Group Planner / K-2 | 30 pp; editable-source tables, grouping map, weekly plan, data tracker | Dividers only | 7-10h | $6 | `scope and sequence`, `teacher planner`, `small group` |

Bundle Phase 2 singles only after each is separately useful and reviewed:

- Short Vowel Five-Pack: $12 vs. $15 singles.
- Blends & Digraphs Collection: $19 vs. $25 singles.
- Advanced Vowel Patterns Collection: $22 vs. $31 singles.
- Games, Cards & Posters Collection: $14 vs. $17 singles.
- Phase 1 + Phase 2 Complete Phonics Library: price only after actual page count, duplicate-content audit, and support burden are known; target $39-59 rather than a fabricated comparison value.

Every Omo bundle should ship as a versioned ZIP with a new original bundle cover, `start-here.pdf`, hyperlinked table of contents, scope/sequence map, the unchanged component PDFs, an optional merged print file, a consolidated answer-key index, license, and provenance manifest. Its listing must name and link every included single, state any overlapping pages, show exact à-la-carte total and real savings, and provide a 1-3 page sampler drawn from approved component previews. Do not make a “bundle” by duplicating or lightly recoloring the same pack.

### 4.4 Phase 3 — seasonal discovery and free lead magnets

Seasonal products reuse the instructional engine and Omo-owned asset library but must contain meaningful new activity selection or theme integration, not merely a recolored duplicate listing.

| Product | Grade / format | Structure, imagery and prompt | Luna time | Price / funnel metadata |
| --- | --- | --- | ---: | --- |
| Free CVC Starter Sample | K; 8 pp PDF | One complete mini-progression + key; `ICON` assets from P1 | 2-3h | Free; description links to P1 CVC pack and $35 collection |
| Free One-Minute Phonics Check | K-2; 4 pp PDF | Directions, student card, teacher record, interpretation limits | 2-3h + educator review | Free; links to P5 assessment |
| Free Decodable Mini-Reader | K-1; 8 pp PDF | One complete original controlled story; P3 `CHARACTER` prompts | 4-5h | Free; links to P3 readers |
| Back-to-School Sound Sorts | PreK-1; 24 pp | School-neutral scenes; “original classroom supplies, no logos or written labels” | 5-7h | $4; `back to school`, `beginning sounds`, `centers` |
| Autumn CVC Read & Find | K-1; 24 pp | Nature scenes; no holiday branding; P1 icons plus seasonal props | 5-7h | $4; `fall`, `CVC`, `I Spy` |
| Halloween Digraph Games | K-2; 26 pp | Friendly non-scary original costumes/objects, no franchises | 6-8h | $4; `Halloween`, `digraphs`, `games` |
| Winter Vowel Teams | 1-2; 28 pp | Inclusive winter-weather scenes, no required holiday | 6-8h | $5; `winter`, `vowel teams`, `word work` |
| Friendship Heart-Word Practice | K-1; 24 pp | Diverse original characters helping one another; no Valentine's dependency | 6-8h | $4; `friendship`, `heart words`, `February` |
| Spring R-Controlled Review | 1-2; 28 pp | Garden/nature icons, uncluttered white background | 6-8h | $5; `spring`, `r controlled vowels`, `review` |
| Summer Phonics Review Games | K-2; 34 pp | Outdoor, travel-free inclusive activities; board/card mix | 7-10h | $6; `summer review`, `phonics games`, `end of year` |

## 5. Luna build pipeline

### 5.1 Repository/tooling finding

There is no checked-in, worksheet-specific PDF generator in `tools/` or `containers/`. The repository does contain two useful precedents:

- `containers/woven-storybook-pipeline/source/SKILL.md` specifies HTML rendering followed by headless Chrome `--print-to-pdf` and Ghostscript compression. This is the best starting rendering pattern for fixed printable pages, but that full PDF workflow is not a production-ready Omo artifact service.
- `containers/demello-awake/image_gen.py` has an injectable ChatGPT/GPT Image generation-and-validation adapter with prompt hashing, usage accounting, retries, and image QA. Its sumi-e visual gates are specific to that workflow; reuse the provider/ledger architecture, not its style rules.
- `tools/host-skill/` and the skill-to-Modal compiler provide reviewed schema/profile/test/price scaffolding. The current compiler safely auto-runs only reviewed `single_llm` profiles; artifact/media workflows remain fail-closed until their capabilities and artifact delivery are materialized ([hosting pipeline](./skill-to-modal-pipeline.md)).

Recommendation: Luna builds worksheets as structured JSON/YAML manifests rendered through original HTML/CSS templates, then Chromium PDF, then Ghostscript optimization. Prefer HTML/CSS over hand-positioned ReportLab for v1 because CSS grids, reusable components, preview HTML, and print variants are easier to inspect. ReportLab remains a fallback for deterministic form fields. Do not depend on an online document editor.

### 5.2 One-pack repeatable process

1. **Lock the brief.** Select product ID, grade, skill scope/prerequisites, dialect, page types, page count, answer-key policy, color/blackline variants, price, and listing promise. Freeze a manifest schema before writing content.
2. **Author the instructional manifest.** Each item stores `skill`, `prompt`, `response_type`, `answer`, `accepted_answers`, `asset_id`, `difficulty`, `decodable_graphemes`, `irregular_words`, and `source/provenance`. Luna creates original content from the approved scope, not from a seller listing.
3. **Run content checks before art.** Deduplicate items, check spelling, answer uniqueness, target-position accuracy, cumulative skill order, dialect/ambiguity flags, sentence decodability, and standards candidates. Block the pack on unresolved items.
4. **Create an asset manifest.** Assign reusable `asset_id`s; generate only missing assets with `OMO_PHONICS_FRIENDS_V1` plus the per-sheet template. Save prompt, model, date, seed/reference IDs if available, hash, review status, color/blackline derivation, and where-used list. Never ask image generation to render words.
5. **Image QA.** Human/vision review: correct object/action, no extra limbs/objects, no accidental text/logo, no resemblance to a protected character, background clean, consistent outline/palette, readable at final 1-1.5 inch size. Reject rather than silently repair a semantically wrong icon.
6. **Render from one source of truth.** HTML/CSS page components consume the same manifest for worksheet and key. Use `@page { size: Letter; margin: 0; }`, pixel-independent inch dimensions, embedded/licensed fonts, SVG layout primitives, and PNG art. Render color, blackline, answer-key, and preview editions.
7. **Technical QA.** Validate page count/order, no clipped content, embedded fonts, PDF opens, print permission, compressed size, selectable text, 300-dpi-equivalent art, and checksums. Render every page to PNG for contact-sheet review; print at least representative low-ink and dense pages at 100% scale.
8. **Instructional QA.** A qualified educator checks every answer, phoneme/grapheme claim, decodability ledger, directions, difficulty progression, representation, accessibility, and standards mapping. For assessment, also review score interpretation and non-clinical disclaimer.
9. **Package.** Deliver `product-color.pdf`, `product-blackline.pdf`, optional cards/reader print mode, `preview.pdf`, `license.txt`, `read-me.pdf`, `manifest.json`, and `provenance.json` in a versioned ZIP. Buyer files must not expose provider credentials or internal paths.
10. **Prepare—not publish—the listing.** Title, one-sentence outcome, “what is included,” use cases, exact pages/formats, grade/subject/standards, license, technical requirements, four original thumbnails, and 1-3 page preview. Publishing or external promotion requires founder approval under the repo safety rules.

### 5.3 QA release checklist

- [ ] Every visible word is spelled correctly and uses the chosen English dialect.
- [ ] Every image unambiguously denotes the intended word; alternative names do not invalidate the answer.
- [ ] Target sound/grapheme occurs in the declared position and follows the taught scope.
- [ ] Decodable text has a machine report; exceptions are explicitly declared and instructionally justified.
- [ ] Answer keys are generated from the item manifest and independently spot-checked.
- [ ] No copied seller text, page, thumbnail, character, or composition; provenance is complete.
- [ ] No protected brand/program name in title/tags without review; no “aligned” or efficacy claim without evidence.
- [ ] Color and blackline versions work; color is not the only information carrier.
- [ ] PDF renders, prints at 100%, has safe margins, embedded fonts, correct page count, and acceptable file size.
- [ ] Four thumbnails and preview accurately represent the download; comparison price and savings are mathematically real.
- [ ] Educator review is signed and versioned; defects route back to the manifest, not patched only in the PDF.

## 6. Marketplace fit

### 6.1 Download-first fit

Static phonics PDFs fit Omo's portable “download” door: pay once, receive a versioned artifact, and use it under a clear educator license. Content is expensive once—authoring, image generation, educator QA—but cheap to serve repeatedly, so $2-8 focused resources and $15-40 bundles can carry high contribution margin after payment, storage, support, refunds, and taxes. This matches Omo's outcome positioning: a teacher buys the worksheet/book needed now, not another subscription ([Omo positioning](./positioning.md)).

Omo advantages versus TPT:

- 85% of qualifying license revenue to a marketplace-discovered creator and 95% when the creator supplies the buyer, rather than TPT's public 55%/80% plans.
- A future second door: generate a level- and skill-specific version on demand instead of buying only a static pack.
- Versioned provenance, deterministic QA evidence, and a portable workflow package can become trust features, not backend details.

Do not promise “high margin” as “zero cost.” Track payment processing, chargebacks/refunds, storage/egress, support, content review, image-generation amortization, and free-sample acquisition.

### 6.2 Hosted-skill fit

`phonics-worksheet-generator` is a natural later Omo workflow:

```yaml
input:
  grade: PreK | K | 1 | 2
  skill: CVC | blends | digraphs | CVCe | vowel-teams | r-controlled
  activity: map-write | sort | passage | game | assessment
  page_count: 1..12
  dialect: en-US | en-GB | en-AU
  print_mode: color | blackline
  theme: neutral | approved-seasonal
output:
  worksheet_pdf: private versioned artifact
  answer_key_pdf: private versioned artifact
  content_report: decodability, answers, provenance, standards-candidates
```

The hosted skill should compile from a reviewed `SKILL.md` profile into the existing skill→Modal flow, but only after deterministic PDF rendering, private artifact storage/delivery, image policy, cost metering, fixture tests, and educator acceptance gates exist. Invalid inputs must fail before spend; provider or QA failure must not return a placeholder as a paid worksheet. The first hosted version should reuse the approved Omo asset library and charge roughly Omo's existing worksheet anchor (about $0.20) only after delivered cost and accepted-output yield are measured, not assumed.

## 7. Roadmap

### Phase 0 — decisions and template proof (no catalog build)

1. Founder answers the open questions below.
2. Recruit one K-2 literacy/phonics reviewer and define paid review/signoff.
3. Approve the original Omo phonics scope, dialect policy, mascot/style lock, font licenses, and resource license.
4. Have Luna build one internal, non-sale 3-page template proof only when the founder starts the build phase: worksheet, answer key, and listing thumbnail. Validate print and content before multiplying it.

### Phase 1 — flagship shelf

- Build in risk order: CVC → digraphs/blends → assessment → heart words → readers.
- Estimated production: 60-82 Luna agent-hours plus educator review. With four independent Luna workstreams after the template and lexicon are stable, expect roughly 4-7 working days of agent production and 2-4 days of review/revision; this is a planning estimate, not a delivery promise.
- Release each standalone only after its own QA; assemble the $35 collection last.
- Create the free CVC sample only from final approved original pages.

### Phase 2 — search coverage

- Produce 25 focused singles from the shared template and asset library.
- Batch by shared asset/skill family, but review each listing independently.
- Use sales, wish-list, preview, refund, and support evidence to choose which bundles to create. Do not generate all possible combinations.

### Phase 3 — acquisition and generator

- Add three complete freebies and 7 seasonal resources; measure free → single → bundle conversion.
- Specify and test `phonics-worksheet-generator` offline against fixed fixtures.
- Promote the hosted skill only after PDF artifact delivery, metered cost, successful print/render QA, and a 95%+ accepted-output benchmark on an educator-reviewed test set.

## 8. Open questions for the founder

1. **Primary buyer:** classroom teachers, parents/homeschool, specialists/interventionists, or a ranked combination? This changes directions, license, standards, and listing language.
2. **Brand surface:** are these first-party products inside the Omo marketplace, an “Omo Education” category, or a separate PhonicsMaker-adjacent storefront? The repository's current positioning favors Omo Education, but this needs confirmation.
3. **Dialect and market:** en-US first, or simultaneous US/UK/Australian variants? A single illustration/word can map differently across dialects.
4. **Pedagogy claim:** should v1 claim general systematic phonics/structured literacy, or pursue a reviewed “Science of Reading aligned” claim? Avoid UFLI/Orton-Gillingham/program-name compatibility until permission and evidence are clear.
5. **Freebie funnel:** does the founder want free account-gated samples, ungated previews, or both? What conversion and support metrics justify continuing them?
6. **Luna budget and schedule:** how many concurrent Luna agents, what image-generation budget, and who owns educator QA? The current Phase 1 estimate is 60-82 agent-hours plus review.
7. **License:** individual educator only, household/homeschool, classroom, school, and/or additional-seat pricing? What printing and secure digital-sharing rights should Omo grant?
8. **Static vs. generated priority:** should Omo validate buy-once demand with the five static resources before funding the hosted generator? Recommendation: yes.
9. **Assessment risk:** is the founder comfortable shipping a classroom screener with a non-clinical disclaimer, or should Phase 1 replace it with a lower-risk teacher planner until a qualified reviewer is retained?
10. **Launch evidence:** what is the go/no-go threshold—educator QA count, buyer tests, print tests, conversion, refund rate, or repeat purchase—before scaling to Phase 2?

## Source index

Official platform/policy sources:

- [TPT homepage](https://www.teacherspayteachers.com/)
- [Phonics browse](https://www.teacherspayteachers.com/browse?search=phonics)
- [Phonics category](https://www.teacherspayteachers.com/browse/english-language-arts/phonics-and-phonological-awareness)
- [Seller account rates](https://help.teacherspayteachers.com/hc/en-us/articles/360044408171-What-types-of-Seller-accounts-are-offered-on-TPT)
- [Supported product file types](https://help.teacherspayteachers.com/hc/en-us/articles/360042429292-What-file-types-are-supported-on-TPT)
- [Thumbnail vs. preview](https://help.teacherspayteachers.com/hc/en-us/articles/360042865851-What-s-the-difference-between-a-thumbnail-and-a-preview)
- [Bundle rules](https://help.teacherspayteachers.com/hc/en-us/articles/360042429532-What-are-bundles)
- [Bundle listing guidance](https://help.teacherspayteachers.com/hc/en-us/articles/360042865171-What-s-the-best-way-to-post-a-bundle-on-TPT)
- [Multiple licenses](https://help.teacherspayteachers.com/hc/en-us/articles/360042448512-What-are-multiple-licenses)
- [Refund policy](https://help.teacherspayteachers.com/hc/en-us/articles/360042884331-What-is-your-refund-policy)
- [TPT Terms of Service](https://www.teacherspayteachers.com/Terms-of-Service/)
- [TPT intellectual-property policy](https://help.teacherspayteachers.com/hc/en-us/articles/360042197012-What-is-TPT-s-intellectual-property-policy)

Live search samples:

- [Phonics worksheets](https://www.teacherspayteachers.com/browse?search=phonics%20worksheets)
- [Phonics bundles](https://www.teacherspayteachers.com/browse?search=phonics%20bundle)
- [CVC](https://www.teacherspayteachers.com/browse?search=CVC)
- [Digraphs](https://www.teacherspayteachers.com/browse?search=digraphs)
- [Sight words](https://www.teacherspayteachers.com/browse?search=sight%20words)
- [Phonemic awareness](https://www.teacherspayteachers.com/browse?search=phonemic%20awareness)
- [Decodable readers](https://www.teacherspayteachers.com/browse?search=decodable%20readers)
- [Games](https://www.teacherspayteachers.com/browse?search=phonics%20games)
- [Posters](https://www.teacherspayteachers.com/browse?search=phonics%20posters)
- [Assessments](https://www.teacherspayteachers.com/browse?search=phonics%20assessment)
- [Vowel teams](https://www.teacherspayteachers.com/browse?search=vowel%20teams)
- [R-controlled vowels](https://www.teacherspayteachers.com/browse?search=r%20controlled%20vowels)
- [Scope and sequence](https://www.teacherspayteachers.com/browse?search=phonics%20scope%20and%20sequence)
- [Google Slides](https://www.teacherspayteachers.com/browse?search=phonics%20Google%20Slides)
- [Boom Cards](https://www.teacherspayteachers.com/browse?search=phonics%20Boom%20Cards)
- [Free phonics](https://www.teacherspayteachers.com/browse/free?search=phonics)
- [Halloween phonics](https://www.teacherspayteachers.com/browse?search=Halloween%20phonics)

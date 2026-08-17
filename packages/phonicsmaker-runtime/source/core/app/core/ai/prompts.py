# app/core/ai/prompts.py

import re
from typing import Optional

######################################################################
# CHARACTER REFERENCE PROMPT - Used for ACE++ Character Consistency
######################################################################

CHARACTER_REFERENCE_PROMPT = """
You are an expert at extracting and describing characters for storybook illustrations.

Based on the following story information, create a detailed CHARACTER REFERENCE IMAGE PROMPT that will be used to generate a reference image for maintaining character consistency across all illustrations.

STORY INFORMATION:
- Story Idea: {story_idea}
- Cover Image Description: {cover_image_prompt}

YOUR TASK:
Create a prompt for generating a CHARACTER REFERENCE SHEET image. This image will be used as a reference for the ACE++ AI framework to maintain character identity across all scenes.

REQUIREMENTS FOR THE CHARACTER REFERENCE PROMPT:
1. **Full body shot**: The character must be shown full body, from head to toe
2. **Neutral pose**: Standing straight, facing forward, arms relaxed at sides
3. **Simple background**: Pure white or very light gray background
4. **Detailed appearance**: Include EVERY visual detail about the character:
   - Build and stature ({build_descriptors}) — NEVER state a numeric age
   - Hair color, style, and length
   - Eye color and shape
   - Skin tone
   - Facial features (glasses, freckles, etc.)
   - Exact clothing with colors and patterns — {image_clothing}
   - Shoes or footwear
   - Any accessories (hat, backpack, etc.)
5. **Art style**: {illustration_style_instruction}
   **INTENDED AUDIENCE**: This reference sheet is for {image_audience}.
6. **No text**: The image MUST be completely text-free. Do NOT include any text, letters, words, numbers, titles, labels, captions, signs, writing, or typography of any kind anywhere in the image. No text on clothing, accessories, or background elements.
7. **Clear and clean**: High detail, no complex backgrounds or action

When describing characters, avoid stating a numeric age (e.g. "6-year-old"). Instead convey their build through physical descriptors ({build_descriptors}).

OUTPUT FORMAT:
Provide ONLY the image generation prompt (100-150 words). Start with the art style keyword, then "Character reference sheet."

Example output (default Cartoonish style, for a young child — copy the STRUCTURE only, and match the
character's age, build, clothing and bearing to {image_audience} instead):
Cartoonish. Character reference sheet. Full body, front view, standing neutral pose, white background. Emma, a cheerful, short, small-statured girl with long curly brown hair in pigtails tied with pink ribbons. Big bright green eyes with long lashes, small button nose, rosy cheeks with light freckles. Warm tan skin. Wearing a bright yellow sundress with white daisy pattern, white lace collar. White ankle socks with pink trim. Red Mary Jane shoes with small buckles. Small red heart-shaped backpack on her back. Friendly smile showing small teeth. Cartoonish children's book illustration style. Clean, detailed. No text, no letters, no words, no numbers, no writing, completely text-free.
"""

CHARACTER_DESCRIPTION_EXTRACTION_PROMPT = """
Based on the following cover image prompt and story scenes for a storybook aimed at {image_audience}, extract CONCISE character descriptions that capture the visual identity of the main character AND any other named character who recurs across more than one scene (e.g. a coach, teacher, parent, sibling).

COVER IMAGE PROMPT:
{cover_image_prompt}

STORY SCENES:
{story_scenes}

For the main character, and for each recurring named secondary character (up to 2), extract a description that includes:
- Character type/species FIRST (e.g. human child, fairy with wings, talking rabbit, dragon) — this must be explicit
- Distinctive features that MUST appear in EVERY image (e.g. wings — yes/no and colour, tail, fur colour/pattern, ears)
- Primary body colour or skin tone
- Build and stature (e.g. {build_descriptors}) — do NOT state a numeric age
- Hair style/colour and eye details
- Clothing with specific colours
- Any distinctive accessories

When describing characters, avoid stating a numeric age (e.g. "6-year-old"). Instead convey their build through physical descriptors ({build_descriptors}).

Output ONLY the descriptions in this exact format, no other text:
MAIN CHARACTER: <50-70 word description>
SECONDARY CHARACTER (<name>): <40-60 word description>

Omit SECONDARY CHARACTER lines entirely if no other named character recurs across scenes.
"""

# Individual language instruction templates
US_ENGLISH_INSTRUCTIONS = """
*   **Spelling:** Use US English spelling conventions (e.g., "color", "flavor", "center", "gray", "pediatric", "program").
*   **Vocabulary:** Use vocabulary common in US English (e.g., "truck", "elevator", "apartment", "soccer", "candy", "sidewalk", "vacation").
*   **Expressions:** Use expressions typical of US English.
*   **Phoneme Pronunciation:** Ensure pronunciation patterns for phoneme teaching match US English. This includes aspects like:
    *   Rhoticity (pronounces 'r' after vowels, e.g. in "car", "bird").
    *   Specific word pronunciations (e.g., "schedule" with /sk/).

Your writing must consistently adhere to the rules for **US English**.
"""

UK_ENGLISH_INSTRUCTIONS = """
*   **Spelling:** Use UK English spelling conventions (e.g., "colour", "flavour", "centre", "grey", "paediatric", "programme").
*   **Vocabulary:** Use vocabulary common in UK English (e.g., "lorry", "lift", "flat", "football", "sweets", "pavement", "holiday").
*   **Expressions:** Use expressions typical of UK English.
*   **Phoneme Pronunciation:** Ensure pronunciation patterns for phoneme teaching match UK English. This includes aspects like:
    *   Non-rhoticity (does not pronounce 'r' after vowels unless followed by another vowel, e.g. in "car", "bird").
    *   Specific word pronunciations (e.g., "schedule" with /ʃ/).

Your writing must consistently adhere to the rules for **UK English**.
"""

AU_ENGLISH_INSTRUCTIONS = """
*   **Spelling:** Use Australian English spelling conventions (generally follows British conventions with some exceptions like "program" for software/events, but "colour" is used).
*   **Vocabulary:** Use vocabulary common in Australian English (e.g., "truck" or "ute" for pickup, "lift", "flat", "soccer" or "football" context-dependent, "lollies", "footpath", "holiday"). Many unique slang terms, but use sparingly for clarity in children's books unless specifically requested.
*   **Expressions:** Use expressions typical of Australian English.
*   **Phoneme Pronunciation:** Ensure pronunciation patterns for phoneme teaching match Australian English. This includes aspects like:
    *   Non-rhoticity, similar to UK English.
    *   Specific word pronunciations (e.g., "schedule" with /ʃ/).

Your writing must consistently adhere to the rules for **Australian English**.
"""

FRENCH_INSTRUCTIONS = """
*   **Spelling and Grammar:** Use standard French spelling (e.g., accents like é, è, â, ç). Apply correct French grammar, including:
    *   Noun-adjective agreement (gender and number).
    *   Accurate verb conjugations (tense, mood, person).
    *   Correct use of articles (le, la, les, un, une, des) and prepositions.
*   **Vocabulary:** Use common French words and expressions suitable for the target age group and the specified {user_level}. Avoid anglicisms unless very common and appropriate in French children's literature.
*   **Expressions:** Use natural French phrasing and idiomatic expressions for children.
*   **Phoneme Pronunciation:** When targeting specific {phonemes} (which will be provided as letter sequences), interpret their pronunciation according to standard French. For example:
    *   "ou" as in "chou" (not as in English "out").
    *   "ch" as in "chat" (not as in English "chair").
    *   "an/am/en/em" as nasal vowels (e.g., "temps", "enfant").
    *   "é", "è", "ê" represent distinct sounds.
    *   Silent letters (e.g., final 's', 't', 'x' in many words) must be respected.
    *   Liaisons: Apply liaisons where appropriate for natural spoken French flow, but keep it simple for young readers (e.g., "un petit enfant").
*   **Formality:** Use "tu" for addressing characters unless a formal context ("vous") is explicitly required (which is rare in children's stories).
*   **Sentence Structure:** While adhering to the level-specific sentence complexity guidelines (e.g., "single-clause sentences only" implies simple sentence structures in French), ensure the sentences are grammatically correct and sound natural in French.
*   **Numbers and Punctuation:** Use French conventions for numbers and punctuation (e.g., a non-breaking space before a colon, semicolon, question mark, and exclamation mark: ` :`, ` ;`, ` ?`, ` !`). For dialogue, use French quotation marks (« guillemets ») with non-breaking spaces, or em dashes (—) for each speaker if simpler for the target age.

Your writing must be entirely in **French** and suitable for young French-speaking children, reflecting the style and complexity appropriate for the specified {user_level}.
"""

SPANISH_INSTRUCTIONS = """
*   **Spelling and Grammar:** Use standard Latin American/Castilian Spanish spelling (e.g., accents like á, é, í, ó, ú, ñ, ü). Apply correct Spanish grammar, including:
    *   Noun-adjective agreement (gender and number: el gato negro, la gata negra).
    *   Accurate verb conjugations (tense, mood, person). Prefer present tense for early levels.
    *   Correct use of articles (el, la, los, las, un, una, unos, unas) and prepositions.
    *   Correct use of ser vs. estar.
*   **Vocabulary:** Use common Spanish words and expressions suitable for the target age group and the specified {user_level}. Use vocabulary that is widely understood across Spanish-speaking countries. Avoid highly regional slang.
*   **Expressions:** Use natural, child-friendly Spanish phrasing and idiomatic expressions.
*   **Phoneme Pronunciation:** When targeting specific {phonemes} (which will be provided as letter sequences), interpret their pronunciation according to standard Spanish. For example:
    *   "ll" as in "lluvia" (the /ʎ/ or /ʝ/ sound, not English "ll").
    *   "ñ" as in "niño" (the /ɲ/ sound).
    *   "rr" as in "perro" (the rolled /r/ sound).
    *   "ch" as in "chico" (the /tʃ/ sound).
    *   "h" is always silent in Spanish (e.g., "hola").
    *   "j" and "ge/gi" produce the /x/ sound (e.g., "jugar", "gente").
    *   "b" and "v" are pronounced similarly in most dialects.
    *   "z" and "ce/ci" produce /s/ in Latin American Spanish or /θ/ in Castilian.
    *   "qu" as in "queso" (the /k/ sound before e/i).
    *   "güe/güi" with diaeresis to indicate the /w/ sound (e.g., "pingüino").
*   **Formality:** Use "tú" for addressing characters (informal, standard in children's stories). Avoid "usted" unless a formal context requires it.
*   **Sentence Structure:** While adhering to the level-specific sentence complexity guidelines, ensure the sentences are grammatically correct and sound natural in Spanish. Spanish allows more flexible word order than English.
*   **Numbers and Punctuation:** Use Spanish conventions for punctuation: inverted question marks (¿) and exclamation marks (¡) at the beginning of questions and exclamations. Use Spanish quotation marks (« » or "") for dialogue.

Your writing must be entirely in **Spanish** and suitable for young Spanish-speaking children, reflecting the style and complexity appropriate for the specified {user_level}.
"""

# NEW: Dictionary mapping language variant name to its specific instructions
LANGUAGE_SPECIFIC_INSTRUCTIONS = {
    "US": US_ENGLISH_INSTRUCTIONS,
    "UK": UK_ENGLISH_INSTRUCTIONS,
    "AU": AU_ENGLISH_INSTRUCTIONS,
    "FR": FRENCH_INSTRUCTIONS,
    "ES": SPANISH_INSTRUCTIONS,
    # Add more languages here as keys with their corresponding instruction strings as values
}

######################################################################
# INTEREST AGE CONFIGS — decoupled from reading level
#
# Reading level (level_configs, 1-5) controls DECODING difficulty: which
# graphemes, word lengths and sentence structures appear.
#
# Interest age controls WHAT THE STORY IS ABOUT: themes, character ages,
# tone, titles, and how the illustrations look.
#
# The two are deliberately independent. An 11-13 year old with dyslexia
# reading at Level 1 needs Level 1 decoding with tween content — the
# "hi-lo" (high interest / low readability) case. Before this existed the
# reading level implied the interest age, so older struggling readers were
# served nursery content and disengaged.
#
# "early_years" reproduces the pre-existing prompt wording verbatim so it
# remains the default and nothing changes for existing users.
######################################################################

DEFAULT_INTEREST_AGE_BAND = "early_years"

# Shared instruction for every band above early_years. Older struggling
# readers abandon books that look or sound like they were made for little
# kids, however well the decoding is pitched.
_DIGNITY_RULE = (
    "**DIGNITY RULE (NON-NEGOTIABLE):** This reader may be decoding several years below their "
    "age. Simple words are required; babyish content is not. Nothing in the story may signal "
    "\"this book is for little kids\" — no baby talk, no nursery imagery, no sing-song narration, "
    "no praise-the-reader asides. The VOCABULARY is simple. The STORY is not.\n"
)

INTEREST_AGE_CONFIGS = {
    "early_years": {
        "label": "4-7 years",
        "author_persona": "children's author and literacy specialist",
        "reviewer_persona": "children's book editor and quality reviewer",
        "book_framing": "lively picture-book story",
        "reader_descriptor": "young child",
        "article": "a",
        # Both templates take {user_level}. early_years reproduces the original
        # prompt wording verbatim; other bands separate decoding from content.
        "reader_target_template": "{user_level} readers",
        "vocab_target_template": "a typical {user_level} child",
        "author_test": "Would a real children's book author write this sentence?",
        "action_vocabulary": "run, sit, hug, eat, play, nap, look, jump, wave, clap",
        "themes": (
            "pets and baby animals, playgrounds, family routines, birthdays, weather, "
            "sharing and kindness, bedtime, first-time experiences"
        ),
        "avoid_themes": "",
        "character_framing": (
            "The main character is a young child, around the reader's own age."
        ),
        "title_examples": "'The Lost Kitten', 'Finn Goes to the Beach', 'A Rainy Day Surprise'",
        "tone": "Warm, fun, playful; no moralising or filler.",
        "quality_bad_examples": (
            "❌ BAD: \"Kip is a top tot.\" → Forced, meaningless word salad. No child talks like this.\n"
            "❌ BAD: \"He can nap in a cot.\" → Disconnected, random action stuffed with decodable words.\n"
            "❌ BAD: \"The cop got a mop.\" → Why? No story reason. Just cramming words.\n"
            "❌ BAD: \"Pam had a pot of cod on top.\" → Unnatural compound phrase.\n"
        ),
        "quality_good_examples": (
            "✅ GOOD: \"Kit the cat sat on a mat.\" → Simple, natural, a child can picture it.\n"
            "✅ GOOD: \"He had a big nap in the sun.\" → Relatable action, cosy feeling.\n"
            "✅ GOOD: \"Kit ran to the pond to find a frog.\" → Story movement, a purpose.\n"
            "✅ GOOD: \"The dog dug a pit and hid his bone.\" → Cause and effect, character motivation.\n"
        ),
        "natural_word_test": "Keep only words a 5-year-old would naturally say.",
        "smile_line": "The story should make a child SMILE or feel something — not just decode words.",
        "understands_line": "Characters should DO things children understand: nap, sit, pat a pet, spot something fun, run, play.",
        "conversation_line": "Use natural, everyday language a child would use in conversation.",
        # ── Illustration side ──
        "image_audience": "a young audience",
        "image_clothing": "colourful, cartoonish, and child-friendly",
        "build_descriptors": "short, small-statured, petite",
        "recommended_styles": ["vivid_cartoon", "soft_watercolor", "bright_inclusive"],
    },
    "middle_primary": {
        "label": "8-10 years",
        "author_persona": "children's author and literacy specialist writing for middle-primary readers",
        "reviewer_persona": "children's book editor working on middle-primary fiction",
        "book_framing": "illustrated story",
        "reader_descriptor": "8-10 year old reader",
        "article": "an",
        "reader_target_template": "an 8-10 year old who decodes at {user_level} level",
        "vocab_target_template": "an 8-10 year old decoding at {user_level} level",
        "author_test": "Would a real author of 8-10 fiction write this sentence?",
        "action_vocabulary": "run, ride, build, hide, search, race, sneak, fix, plan, win, lose",
        "themes": (
            "friendship and falling out, mysteries and clues, sport and competition, animals and "
            "rescues, building and inventing things, school life, camping and the outdoors, humour "
            "and pranks, small acts of bravery"
        ),
        "avoid_themes": (
            "toddler routines (naptime, snacktime, potty, learning to share toys), nursery settings, "
            "talking teddies, baby animals as the emotional core"
        ),
        "character_framing": (
            "The main character is 8-10 years old. They solve their own problem — an adult may help "
            "but must not rescue them."
        ),
        "title_examples": "'The Clue in the Old Shed', 'Race to the Finish', 'Nobody Believed Max'",
        "tone": "Energetic and playful, with real stakes. No moralising, no babying the reader.",
        "quality_bad_examples": (
            "❌ BAD: \"Kip is a top tot.\" → Forced word salad. Nobody talks like this.\n"
            "❌ BAD: \"Kit the cat sat on a mat.\" → Nursery-level content. This reader is 8-10 and will find it dull.\n"
            "❌ BAD: \"He can nap in a cot.\" → Disconnected, random action stuffed with decodable words.\n"
            "❌ BAD: \"Pam had a pot of cod on top.\" → Unnatural compound phrase.\n"
        ),
        "quality_good_examples": (
            "✅ GOOD: \"Sam had one shot left to win.\" → Simple words, real stakes.\n"
            "✅ GOOD: \"The shed door was open, and the bike was gone.\" → Sets up a mystery.\n"
            "✅ GOOD: \"He ran until his legs hurt.\" → Physical, vivid, easy to decode.\n"
            "✅ GOOD: \"Nobody had seen who did it.\" → Question the reader wants answered.\n"
        ),
        "natural_word_test": "Keep only words an 8-10 year old would naturally use.",
        "smile_line": "The story should grip the reader — give them something to find out.",
        "understands_line": "Characters should DO things 8-10 year olds care about: compete, investigate, build, sneak, fix, win, lose.",
        "conversation_line": "Use natural, everyday language an 8-10 year old would actually use.",
        "image_audience": "readers aged 8-10 (not a picture book for toddlers)",
        "image_clothing": "everyday contemporary kids' clothing (t-shirts, jeans, trainers, sports kit) and age-appropriate",
        "build_descriptors": "average height for their age, wiry, sturdy",
        "recommended_styles": ["vivid_cartoon", "comic_book", "retro_cartoon", "bright_inclusive"],
    },
    "tween": {
        "label": "11-13 years",
        "author_persona": (
            "author of high-interest / low-readability (hi-lo) readers for older struggling readers, "
            "and a literacy specialist"
        ),
        "reviewer_persona": "editor of hi-lo readers for older struggling readers",
        "book_framing": "illustrated hi-lo reader (simple to decode, written for an older reader)",
        "reader_descriptor": "11-13 year old reader",
        "article": "an",
        "reader_target_template": "an 11-13 year old who decodes at {user_level} level",
        "vocab_target_template": "an 11-13 year old decoding at {user_level} level",
        "author_test": "Would a 12-year-old read this sentence without feeling patronised?",
        "action_vocabulary": "skate, ride, film, post, sneak, escape, search, train, quit, risk, defend, hide",
        "themes": (
            "loyalty and friendship being tested, skating / BMX / football / basketball, gaming and "
            "streaming, survival and getting out of trouble, mysteries and detective work, the "
            "unexplained, music and bands, animal rescue, standing up to something unfair, moving "
            "house or family change, secrets, wanting to be trusted with something"
        ),
        "avoid_themes": (
            "nursery or toddler settings, cutesy talking toys or teddies, naptime / snacktime / "
            "bedtime routines, baby animals as the emotional core, learning to share, sing-song or "
            "rhyming nursery cadence, exclamation-heavy narration, adults solving the problem"
        ),
        "character_framing": (
            "The main character is 11-13 — a tween, NOT a little kid. Give them real agency: they "
            "make the decisions and resolve their own problem. No adult swoops in to fix it."
        ),
        "title_examples": (
            "'The Night the Lights Went Out', 'Nobody Saw Her Leave', 'Twelve Seconds', "
            "'The Last Ride', 'What Jay Did Next'"
        ),
        "tone": (
            "Direct and respectful, with a little edge. Dry humour is welcome. Never cutesy, never "
            "talk down to the reader."
        ),
        "quality_bad_examples": (
            "❌ BAD: \"Kit the cat sat on a mat.\" → Nursery content. A 12-year-old will shut the book.\n"
            "❌ BAD: \"He can nap in a cot.\" → Babyish and pointless.\n"
            "❌ BAD: \"Kip is a top tot.\" → Forced word salad, and \"tot\" frames the reader as an infant.\n"
            "❌ BAD: \"Good job, Sam! What a big helper!\" → Praise-the-reader narration. Patronising.\n"
        ),
        "quality_good_examples": (
            "✅ GOOD: \"Sam did not want to go back in.\" → Simple words, real tension.\n"
            "✅ GOOD: \"The bike was gone, and no one had seen it go.\" → A hook, easy to decode.\n"
            "✅ GOOD: \"He had one job to do and he did not want to mess it up.\" → Stakes and self-doubt.\n"
            "✅ GOOD: \"She did not tell them what she saw.\" → A secret, told in one-syllable words.\n"
        ),
        "natural_word_test": (
            "Discard any word that would sound babyish to a 12-year-old (e.g. 'tot', 'cot', 'wee', "
            "'nap', 'tum'), even if it is decodable."
        ),
        "smile_line": "The story should make the reader want the next page — tension, a secret, or a problem worth solving.",
        "understands_line": (
            "Characters should DO things a 11-13 year old cares about: skate, ride, film something, "
            "sneak out, cover for a friend, train for something, investigate, take a risk."
        ),
        "conversation_line": "Use natural language a 11-13 year old would actually use — plain, not childish.",
        "image_audience": (
            "readers aged 11-13 — the illustrations must NOT look like a picture book for little "
            "children"
        ),
        "image_clothing": (
            "contemporary tween clothing (hoodies, jeans, trainers, sports kit, caps) and "
            "age-appropriate — never toddler clothing, no nursery patterns or pastel baby colours"
        ),
        "build_descriptors": "tall for their age, lanky, long-limbed, wiry",
        "recommended_styles": ["comic_book", "modern_line_art", "watercolour_realism", "retro_pixel"],
    },
    "teen": {
        "label": "14-17 years",
        "author_persona": (
            "author of high-interest / low-readability (hi-lo) readers for teenagers, and a "
            "literacy specialist"
        ),
        "reviewer_persona": "editor of hi-lo readers for teenagers",
        "book_framing": "illustrated hi-lo reader for teenagers (simple to decode, written for a teen)",
        "reader_descriptor": "14-17 year old reader",
        "article": "a",
        "reader_target_template": "a 14-17 year old who decodes at {user_level} level",
        "vocab_target_template": "a 14-17 year old decoding at {user_level} level",
        "author_test": "Would a 16-year-old read this sentence without feeling patronised?",
        "action_vocabulary": "drive, work, quit, train, film, argue, leave, save, fix, risk, defend, choose",
        "themes": (
            "independence and identity, first jobs and money, learning to drive, friendship and "
            "betrayal, family pressure, injustice and standing up, sport and training, music, "
            "gaming, survival and thrillers, plans that go wrong, second chances"
        ),
        "avoid_themes": (
            "childhood or nursery settings, talking toys, primary-school framing, cutesy animals, "
            "praise-the-reader narration, adults solving the problem"
        ),
        "character_framing": (
            "The main character is 14-17. They carry adult-adjacent responsibility and make their "
            "own choices, including bad ones. No adult rescues them."
        ),
        "title_examples": (
            "'One More Shift', 'The Long Way Home', 'He Knew What She Did', 'Last Train Out'"
        ),
        "tone": (
            "Spare, cinematic and honest. Treat the reader as an equal. Keep content "
            "school-appropriate — tension and consequence, never graphic."
        ),
        "quality_bad_examples": (
            "❌ BAD: \"Kit the cat sat on a mat.\" → Nursery content. A teenager will refuse to read it.\n"
            "❌ BAD: \"He can nap in a cot.\" → Babyish and pointless.\n"
            "❌ BAD: \"Good job! What a big helper!\" → Praise-the-reader narration. Insulting at this age.\n"
            "❌ BAD: \"Mum said it was time for bed.\" → Frames a teenager as a small child.\n"
        ),
        "quality_good_examples": (
            "✅ GOOD: \"He had to be at work by six.\" → Adult stakes, one-syllable words.\n"
            "✅ GOOD: \"She did not tell them the truth.\" → Moral weight, easy to decode.\n"
            "✅ GOOD: \"The van did not start.\" → Concrete problem, immediate tension.\n"
            "✅ GOOD: \"He knew he had to quit or lose them both.\" → A real choice.\n"
        ),
        "natural_word_test": (
            "Discard any word that would sound childish to a teenager (e.g. 'tot', 'cot', 'nap', "
            "'mummy'), even if it is decodable."
        ),
        "smile_line": "The story should land like a short film — tension, a choice, a consequence.",
        "understands_line": (
            "Characters should DO things teenagers care about: work a shift, drive, train, argue, "
            "leave, cover for someone, take a risk, make a hard call."
        ),
        "conversation_line": "Use natural language a teenager would actually use — plain and direct, never childish.",
        "image_audience": (
            "readers aged 14-17 — the illustrations must read as a teen graphic novel, never as a "
            "children's picture book"
        ),
        "image_clothing": (
            "contemporary teenage clothing (hoodies, jackets, jeans, trainers, work uniform, sports "
            "kit) and age-appropriate — never childlike clothing or nursery colours"
        ),
        "build_descriptors": "tall, lanky, broad-shouldered, teenage build",
        "recommended_styles": ["comic_book", "modern_line_art", "watercolour_realism", "cyberpunk"],
    },
    "adult": {
        "label": "adult learners",
        "author_persona": "author of adult literacy readers and a literacy specialist",
        "reviewer_persona": "editor of adult literacy readers",
        "book_framing": "illustrated adult literacy reader (simple to decode, written for an adult)",
        "reader_descriptor": "adult learner",
        "article": "an",
        "reader_target_template": "an adult learner who decodes at {user_level} level",
        "vocab_target_template": "an adult learner decoding at {user_level} level",
        "author_test": "Would an adult read this sentence without feeling patronised?",
        "action_vocabulary": "work, drive, pay, move, apply, fix, call, plan, wait, decide, help, start",
        "themes": (
            "work and shifts, housing and moving, health appointments, family responsibility, money "
            "and bills, learning to drive, travel, community and neighbours, starting over, study "
            "and retraining"
        ),
        "avoid_themes": (
            "school settings framed from a pupil's point of view, childhood themes, talking animals, "
            "toys, praise-the-reader narration, anything that frames the reader as a child"
        ),
        "character_framing": (
            "The main character is an adult with adult responsibilities — a job, a home, a family, "
            "bills. They make their own decisions."
        ),
        "title_examples": (
            "'The New Job', 'A Long Way to Work', 'The Letter That Came Late', 'Second Chance'"
        ),
        "tone": (
            "Respectful and matter-of-fact. Never patronising, never cute. Adult situations handled "
            "plainly."
        ),
        "quality_bad_examples": (
            "❌ BAD: \"Kit the cat sat on a mat.\" → Nursery content. Insulting to an adult learner.\n"
            "❌ BAD: \"He can nap in a cot.\" → Frames an adult as an infant.\n"
            "❌ BAD: \"Good job! What a big helper!\" → Praise-the-reader narration. Patronising.\n"
            "❌ BAD: \"Mum said it was time for bed.\" → Childhood framing.\n"
        ),
        "quality_good_examples": (
            "✅ GOOD: \"He had to be at work by six.\" → Adult stakes, simple words.\n"
            "✅ GOOD: \"The rent was due and the cash was short.\" → Real adult problem, easy to decode.\n"
            "✅ GOOD: \"She had to call them back.\" → A task with weight.\n"
            "✅ GOOD: \"The bus did not come.\" → Concrete, relatable, one syllable per word.\n"
        ),
        "natural_word_test": (
            "Discard any word that would sound childish to an adult (e.g. 'tot', 'cot', 'nap', "
            "'mummy'), even if it is decodable."
        ),
        "smile_line": "The story should feel true to adult life — a real situation with a real outcome.",
        "understands_line": (
            "Characters should DO things adults do: work a shift, pay a bill, catch a bus, fix "
            "something, make a call, deal with a setback."
        ),
        "conversation_line": "Use natural language an adult would actually use — plain and clear, never childish.",
        "image_audience": (
            "adult learners — the illustrations must depict adults in adult settings, never a "
            "children's picture book"
        ),
        "image_clothing": (
            "everyday adult clothing (work uniform, coat, jeans, shirt, hi-vis, scrubs) and "
            "appropriate — never childlike clothing or nursery colours"
        ),
        "build_descriptors": "adult build, average height, tall, sturdy",
        "recommended_styles": ["watercolour_realism", "modern_line_art", "comic_book", "heritage_ink"],
    },
}

# Free-text values the frontend, tests, or older clients may send.
INTEREST_AGE_ALIASES = {
    "adult_learner": "adult",
    "adults": "adult",
    "child": "early_years",
    "children": "early_years",
    "kids": "early_years",
    "early": "early_years",
    "early_childhood": "early_years",
    "prep": "early_years",
    "infant": "early_years",
    "primary": "middle_primary",
    "middle": "middle_primary",
    "upper_primary": "middle_primary",
    "preteen": "tween",
    "pre_teen": "tween",
    "tweens": "tween",
    "middle_school": "tween",
    "teens": "teen",
    "teenager": "teen",
    "teenagers": "teen",
    "young_adult": "teen",
    "ya": "teen",
    "high_school": "teen",
    "secondary": "teen",
}

# Upper age bound → band, for numeric values like "12", "6-7", "age 15".
INTEREST_AGE_THRESHOLDS = (
    (7, "early_years"),
    (10, "middle_primary"),
    (13, "tween"),
    (17, "teen"),
)


def resolve_interest_age_band(student_age: Optional[str]) -> str:
    """
    Resolve any incoming interest-age value to an INTEREST_AGE_CONFIGS key.

    Accepts band keys ("tween"), aliases ("adult_learner", "middle_school"),
    and free-text ages ("12", "6-7", "age 15"). Numeric values resolve on the
    OLDEST age mentioned, so "11-13" lands in tween rather than middle_primary.

    Unrecognised or empty values fall back to the default band, which
    reproduces the historical prompt wording exactly.
    """
    if not student_age:
        return DEFAULT_INTEREST_AGE_BAND

    raw = str(student_age).strip().lower().replace(" ", "_").replace("-", "_")
    if raw in INTEREST_AGE_CONFIGS:
        return raw
    if raw in INTEREST_AGE_ALIASES:
        return INTEREST_AGE_ALIASES[raw]

    # Alias may be embedded in a longer label, e.g. "tween_11_13".
    for alias, band in INTEREST_AGE_ALIASES.items():
        if alias in raw:
            return band
    for band in INTEREST_AGE_CONFIGS:
        if band in raw:
            return band

    ages = [int(n) for n in re.findall(r"\d+", raw)]
    if ages:
        oldest = max(ages)
        for ceiling, band in INTEREST_AGE_THRESHOLDS:
            if oldest <= ceiling:
                return band
        return "adult"

    return DEFAULT_INTEREST_AGE_BAND


def get_interest_age_config(student_age: Optional[str]) -> dict:
    """Return the INTEREST_AGE_CONFIGS entry for any incoming interest-age value."""
    return INTEREST_AGE_CONFIGS[resolve_interest_age_band(student_age)]


def build_interest_age_block(student_age: Optional[str], scope_note: str = "") -> str:
    """
    Build the interest-age override block appended to story prompts.

    Returns "" for the default band so early-years generations keep their
    historical prompt byte-for-byte.
    """
    band = resolve_interest_age_band(student_age)
    if band == DEFAULT_INTEREST_AGE_BAND:
        return ""

    cfg = INTEREST_AGE_CONFIGS[band]
    parts = [
        f"### INTEREST AGE — {cfg['label'].upper()} (OVERRIDES THE STYLE GUIDE ABOVE)",
        (
            "The reading level above controls DECODING ONLY — which sounds, word lengths and "
            "sentence structures are allowed. It does NOT set the content. This section sets the "
            "content, and it wins on every conflict about theme, character age, title or tone.\n"
        ),
        _DIGNITY_RULE,
        f"**WRITE AS:** {cfg['author_persona']}.",
        f"**THIS IS:** {cfg['book_framing']}. The reader is {cfg['article']} {cfg['reader_descriptor']}.",
        f"**MAIN CHARACTER:** {cfg['character_framing']}",
        f"**THEMES TO DRAW ON:** {cfg['themes']}.",
        f"**NEVER USE:** {cfg['avoid_themes']}.",
        f"**TONE:** {cfg['tone']}",
        (
            f"**TITLE OVERRIDE:** Ignore the title examples in the style guide above — they are "
            f"pitched too young. Use titles like these instead: {cfg['title_examples']}."
        ),
        f"**ACTIONS:** {cfg['understands_line']}",
        f"**WORD CHOICE:** {cfg['natural_word_test']}",
        "",
        "EXAMPLES AT THIS INTEREST AGE:",
        cfg["quality_bad_examples"],
        cfg["quality_good_examples"],
    ]
    if scope_note:
        parts.append(scope_note)
    return "\n".join(parts)


# ── Difficulty configs keyed by 1–5 (decoupled from curriculum stage) ──
# 1 = Beginner, 2 = Easy, 3 = Medium, 4 = Challenging, 5 = Advanced
level_configs = {
    "1": {
        "user_level": "Prep",
        "word_count_range": "3-8 words",
        "title_spec": "2-5 playful words that sound like a real children's book title. The title must make sense as a phrase or sentence — avoid random word combos like 'Harry's Park Play'. Good examples: 'The Lost Kitten', 'Finn Goes to the Beach', 'A Rainy Day Surprise'. Plain text, then `|||`",
        "vocab_guardrail": "• Use high-frequency CVC/CVCC words and simple digraphs.\n   • Avoid tricky multi-syllable or irregular words.",
        "phonics_use": "• Across the book, weave **3-6 different words** containing each {phonemes}.\n   • Treat every item in {phonemes} as a letter sequences (e.g., *sh* in *ship*), defaulting to their most common sound when ambiguous, **consistent with {language_variant_name} pronunciation conventions**.\n   • Avoid obvious stuffing—phoneme words must serve the plot or imagery.",
        "language_mechanics": """• Adhere strictly to {language_variant_name}. Ensure correct {language_variant_name} spelling and grammar.
• Sentence structure: single-clause sentences only.

**{language_variant_name} GUIDELINES:**
{language_variant_instructions}""",
        "tone_description": "• Warm, fun, age-appropriate; no moralising or filler.",
    },
    "2": {
        "user_level": "Year 1",
        "word_count_range": "4-12 words",
        "title_spec": "3-6 catchy words that sound like a real children's book title. The title must make sense as a phrase or sentence — avoid random word combos or '[Name]'s [Noun] [Noun]' patterns. Good examples: 'The Magic Shell', 'Sam and the Big Storm', 'Where Did the Duck Go?'. Plain text, then `|||`",
        "vocab_guardrail": "• Use high-frequency and decodable words; introduce simple blends and digraphs.\n   • Limit multi-syllable or uncommon words.",
        "phonics_use": "• Across the book, weave **4-8 different words** containing each {phonemes}.\n   • Treat every item in {phonemes} as a letter sequences (e.g., *sh* in *ship*), defaulting to their most common sound when ambiguous, **consistent with {language_variant_name} pronunciation conventions**.\n   • Avoid obvious stuffing—phoneme words must serve the plot or imagery.",
        "language_mechanics": """• Adhere strictly to {language_variant_name}. Ensure correct {language_variant_name} spelling and grammar.
• Sentence structure: mostly single-clause sentences.

**{language_variant_name} GUIDELINES:**
{language_variant_instructions}""",
        "tone_description": "• Imaginative, fun, age-appropriate; avoid heavy moralising or filler.",
    },
    "3": {
        "user_level": "Year 2",
        "word_count_range": "5-14 words",
        "title_spec": "3-6 catchy words that sound like a real children's book title. The title must make sense as a phrase or sentence — avoid random word combos or '[Name]'s [Noun] [Noun]' patterns. Good examples: 'The Secret Garden Gate', 'Lily's Amazing Adventure', 'A Trip to the Moon'. Plain text, then `|||`",
        "vocab_guardrail": "• Use common Year 2 words and high-frequency sight words.\n   • Sprinkle in interesting but decodable words; avoid advanced multi-syllable terms.",
        "phonics_use": '• Across the whole book, weave **4-9 different words** containing each {phonemes}.\n   • Treat every item in {phonemes} as a **letter sequence** (e.g., "ign" in *sign*, *design*, *align*), defaulting to their most common sound when ambiguous, **consistent with {language_variant_name} pronunciation conventions**.\n   • Avoid obvious stuffing—let phoneme words serve the plot or imagery.',
        "language_mechanics": """• Adhere strictly to {language_variant_name}. Ensure correct {language_variant_name} spelling and grammar.
• Sentence structure: simple, single-clause sentences preferred.

**{language_variant_name} GUIDELINES:**
{language_variant_instructions}""",
        "tone_description": "• Imaginative, fun, age-appropriate; avoid heavy moralising or filler.",
    },
    "4": {
        "user_level": "Year 3",
        "word_count_range": "7-17 words",
        "title_spec": "3-6 engaging words that sound like a real children's book title. The title must make sense as a phrase or sentence — avoid random word combos. Good examples: 'The Inventor's Secret', 'Race to Thunder Mountain', 'When the Lights Went Out'. Plain text, then `|||`",
        "vocab_guardrail": "• Everyday language plus vivid adjectives and verbs children meet in Year 3-4 texts.\n   • Some compound and three-syllable words are fine if commonly known; avoid obscure terms.",
        "phonics_use": "• Across the book, weave **5-9 different words** containing each {phonemes}.\n   • Treat every item in {phonemes} as a letter sequence (e.g., *ign* in *design*), defaulting to their most common sound when ambiguous, **consistent with {language_variant_name} pronunciation conventions**.\n   • Avoid obvious stuffing—phoneme words must serve the plot or imagery.",
        "language_mechanics": """• Adhere strictly to {language_variant_name}. Ensure correct {language_variant_name} spelling and grammar.
• Sentence structure: simple or compound sentences acceptable, but keep clauses clear.

**{language_variant_name} GUIDELINES:**
{language_variant_instructions}""",
        "tone_description": "• Imaginative, fun, and age-appropriate; avoid heavy moralising or filler.",
    },
    "5": {
        "user_level": "Year 5",
        "word_count_range": "8-18 words",
        "title_spec": "3-6 engaging words that sound like a real children's book title. The title must make sense as a phrase or sentence — avoid random word combos. Good examples: 'The Midnight Map', 'Beyond the Frozen River', 'How Leo Saved the Day'. Plain text, then `|||`",
        "vocab_guardrail": "• Rich but accessible language; vivid three-syllable words often met in Year 5 texts.\n   • Keep technical terms or figurative language clear from context; avoid obscure jargon.",
        "phonics_use": "• Across the book, weave **5-9 different words** containing each {phonemes}.\n   • Treat every item in {phonemes} as a letter sequence (e.g., *ough* in *through*, *thought*), defaulting to their most common sound when ambiguous, **consistent with {language_variant_name} pronunciation conventions**.\n   • Avoid obvious stuffing—phoneme words must serve the plot or imagery.",
        "language_mechanics": """• Adhere strictly to {language_variant_name}. Ensure correct {language_variant_name} spelling and grammar.
• Sentence structure: compound or complex sentences acceptable, but keep them clear.

**{language_variant_name} GUIDELINES:**
{language_variant_instructions}""",
        "tone_description": "• Imaginative, engaging, and age-appropriate; avoid heavy moralising or filler.",
    },
}

# Legacy mapping: old DifficultyLevel enum values → new "1"-"5" keys
LEGACY_DIFFICULTY_MAP = {
    "FOUNDATION": "1",
    "Level 1": "2",
    "Level 2": "3",
    "Level 3": "4",
    "Level 4": "4",  # Merged with Level 3 → "4" (Challenging)
    "Level 5": "5",
}

BASE_STORY_GENERATION_PROMPT = """
### SYSTEM
You are a {author_persona}. You will be writing for a {language_variant_name} audience.
Write a {book_framing} for {reader_target} using the inputs below.
The story must be grammatically correct for {language_variant_name}, flow naturally, and use vocabulary {vocab_target} can understand, appropriate for {language_variant_name}.

### USER VARIABLES
{story_idea}                 - one-line concept
{phonemes}                   - comma-separated list (may be empty)
{scene_count}                - total number of scenes
{language_variant_name}      - e.g., "US English", "UK English", "Australian English", "French"

### STYLE GUIDE - {user_level}
1. **Word count per scene:** exactly {word_count_range}. (Interpret for natural sentence length in {language_variant_name})
2. **One scene = one sentence.** (Ensure this is a complete, natural sentence in {language_variant_name})
3. **Total scenes = {scene_count}.** No more, no less.
4. **Title:** {title_spec}. (Ensure title is in {language_variant_name})
   • The title should hint at the story's plot, character, or setting — it must feel like a real book you'd find in a library.
   • AVOID generic or nonsensical titles like "[Name]'s [Place] [Activity]" (e.g., "Harry's Park Play"). Instead, create a title that sparks curiosity or tells the reader what the story is about.

5. **Vocabulary Guardrail**
   {vocab_guardrail} (Interpret guidelines for {language_variant_name}, e.g., "CVC words" means simple syllable structures in French)

6. **Narrative Flow (Flow-First Rule)**
   • Clear beginning → middle → end; each scene follows logically (cause → effect).
   • If a phoneme hurts flow, replace or skip it—story quality outranks phoneme count.

7. **Story Quality (NON-NEGOTIABLE)**
   • The story must make sense and be enjoyable to read EVEN WITHOUT considering the phonics goals.
   • Every story needs a SIMPLE PLOT: a character wants something, tries something, or something happens to them.
   • Include EMOTIONAL BEATS — characters should feel things (happy, surprised, tired, excited, proud, silly).
   • Each sentence must connect logically to the next — no random, disconnected observations.
   • Ask yourself: "{author_test}" If not, rewrite it.
   • Fewer phoneme words in a GOOD story is always better than more phoneme words in a BAD story.

8. **Vocabulary Simplicity**
   • Use the SIMPLEST, most natural phrasing possible — write how {article} {reader_descriptor} speaks and thinks.
   • Avoid forced or awkward constructions that only exist to shoehorn in a decodable word.
   • Avoid unusual compound phrases (e.g., "tip top", "spin top", "top pic") — prefer simple, everyday words.
   • Prefer common actions the reader does and understands: {action_vocabulary}.
   • Every word should feel natural — if it sounds odd when read aloud, replace it.

9. **Characters**
   • Introduce naturally; keep names and details consistent. (Use culturally appropriate names for {language_variant_name} if not specified)

10. **Phonics Use**
   {phonics_use}

11. **Language Mechanics & Variant ({language_variant_name})**
   {language_mechanics}

12. **Tone**
    {tone_description} (Ensure tone is culturally appropriate for {language_variant_name})

### OUTPUT FORMAT
You MUST output EXACTLY this format — title first, then three pipe characters `|||`, then each scene separated by three hyphens `---`.
There must be EXACTLY {scene_count} scenes. Each scene is ONE sentence.
Do NOT include scene numbers, bullet points, labels, or any other formatting.
Output ONLY the raw text in this structure:

Title|||First scene sentence.---Second scene sentence.---Third scene sentence.---...and so on for all {scene_count} scenes.

Example (for a 4-scene story):
The Big Red Balloon|||Sam found a big red balloon.---The balloon flew up into the sky.---Sam chased it over the hill.---He caught it just in time!

"""

######################################################################
# STORY QUALITY REVIEW PROMPT - Two-pass self-critique & rewrite
######################################################################

STORY_QUALITY_REVIEW_PROMPT = """
### SYSTEM
You are a {reviewer_persona}. Your job is to review a generated phonics story
and rewrite any sentences that sound unnatural, forced, or like random word salad.

### THE STORY TO REVIEW
{story_text}

### YOUR TASK
Read the story above aloud in your head. For EACH sentence (scene), decide:
1. ✅ **KEEP** — the sentence sounds natural, tells part of the story, and {article} {reader_descriptor} would enjoy it.
2. ✂️ **REWRITE** — the sentence sounds forced, awkward, or like random words jammed together.

REWRITE RULES:
• Only rewrite sentences that NEED it — if a sentence is already good, leave it EXACTLY as-is.
• Rewritten sentences must still fit the overall story arc and connect logically to neighbouring scenes.
• Keep the same character names and general plot direction.
• Keep the same title. If the title is good, don't change it.
• The total number of scenes must stay EXACTLY {scene_count}.
• Each scene must still be ONE sentence.
• **NEVER MAKE THE STORY YOUNGER.** Simplifying means shorter words and shorter sentences — it does
  NOT mean changing the story into something for younger readers. Do not swap the setting, the
  characters' ages, or the themes for babyish ones. Do not add sing-song rhythm, cutesy asides, or
  praise-the-reader narration. If a sentence is already pitched correctly for the interest age
  below, leave it alone.

{decodability_constraints}

{interest_age_constraints}

### QUALITY CHECKS
Before finalising, verify each sentence passes ALL of these:
• "{author_test}" — If no, rewrite it.
• "Does this sentence connect to the one before and after it?" — If not, fix the connection.
• "Would {article} {reader_descriptor} understand and enjoy this?" — If not, simplify the WORDS, never the content.
• "Does this sound like natural speech?" — If it sounds robotic or forced, rewrite it.

### COMMON PROBLEMS TO FIX
• Sentences that are just random decodable words: "Kip is a top tot" → Rewrite with purpose
• Disconnected actions with no story reason: "The cop got a mop" → Give a reason or replace
• Unnatural compound phrases: "tip top", "pot of cod on top" → Use simpler, common words
• Repetitive sentence structures: if 5+ sentences start the same way, vary them
• Missing emotional beats: add character feelings (happy, surprised, tired, proud)

### OUTPUT FORMAT
Output EXACTLY the same format as the input — title first, then `|||`, then scenes separated by `---`.
Do NOT add scene numbers, bullet points, labels, markdown, or any other formatting.

{title_and_scenes_example}
"""

######################################################################
# DIFFERENTIATION PROMPT - Rewrite story to a different difficultly level
######################################################################
DIFFERENTIATE_STORY_PROMPT = """
### SYSTEM
You are an expert reading-level adapter and literacy specialist. 
Your objective is to adapt an existing phonics story to a new difficulty level ({target_level_name}) while keeping the core narrative and exact number of scenes identical.

### ORIGINAL STORY
{original_story}

### TARGET AUDIENCE DETAILS
{language_variant_name} audience decoding at the {target_level_name} level.

{interest_age_block}

### STYLE GUIDE FOR {target_level_name}
1. **Word count per scene:** exactly {word_count_range}.
2. **One scene = one sentence.**
3. **Total scenes = EXACTLY {scene_count}.** You must map your new scenes 1-to-1 with the original scenes so the pre-generated illustrations still match perfectly.
   • Re-levelling changes the DECODING difficulty only. Never shift the themes, character ages, or tone toward a younger audience.
4. **Vocabulary Guardrail:**
   {vocab_guardrail}
5. **Language Mechanics & Variant ({language_variant_name}):**
   {language_mechanics}

### YOUR TASK
Rewrite the story to match the targeted reading level constraints ABOVE. 

CRITICAL RULES:
1. The title can remain the same or be adapted, but it must be followed by `|||`.
2. You MUST have EXACTLY {scene_count} scenes separated by `---`. If the original had 20 scenes, your output MUST have exactly 20 scenes.
3. Scene 1 of your rewrite must describe the same event as Scene 1 of the original, so the image remains relevant.
4. Your output MUST ONLY be plain text in the exact format:
   Title|||Scene 1.---Scene 2.---Scene 3...
5. DO NOT add any markdown, numbers, or bullet points.
"""

# First Image Prompt Generation Prompt
COVER_IMAGE_PROMPT_GENERATION_PROMPT = """
You are a children's story book cover page prompt generator expert. Your task is to make a cover page prompt for given story idea and short story scenes:

Story Idea: {story_idea}
Short Scenes: {short_scenes}

The cover page prompt should:
- Be 100-150 words. Use English language.
- Keep the tone engaging and suitable for {image_audience}.
- {illustration_style_instruction}
- ABSOLUTELY CRITICAL — NO CHARACTER NAMES:
  Do NOT include the character's name (e.g. "Santiago", "Layla", "Barnaby", etc.) anywhere in the prompt. Instead, use generic descriptions (e.g. "the boy", "the girl", "the pup", "the dog"). Image generation models do not understand names and using proper nouns/names frequently triggers content moderation filters (resulting in blocked/failed generation).
- ABSOLUTELY CRITICAL — TEXT-FREE IMAGE: The generated image MUST contain ZERO text of any kind. This means:
  * NO book title, NO author name, NO character names written anywhere
  * NO letters, NO words, NO numbers, NO signs, NO labels, NO captions
  * NO text on objects (books, signs, shirts, banners, screens, etc.)
  * NO letter-like shapes, NO writing, NO typography, NO watermarks
  * NO speech bubbles, NO dialogue bubbles, NO thought bubbles, NO word balloons, NO comic-style text containers of any kind
  * The image is PURELY visual — only illustration, no text overlay
  * Do NOT describe any text appearing in the scene (e.g., do NOT say "a sign that reads..." or "a book titled...")
  * Do NOT describe speech bubbles or dialogue containers in the scene
  * Always end the prompt with: "Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."
- Include details about every characters' clothing and appearance that are appropriate for the specified art style. Clothing must be {image_clothing}. Never depict revealing or sexualised clothing.
- Important: Add a detailed explanation about the characters and other entities at the beginning of the prompt to maintain consistency of entities across scenes. Mention about clothing, wearings, and etc.
- Important: Prefer framing the main character in a medium shot (full body or waist-up) as the default. This helps maintain a consistent character scale across scene images.
- Specifically mention the art style in the prompt. Be specific about the art style.
- Specifically mention the actions/tasks the entities are doing/behaving in the prompt.
- Specifically mention the emotions the characters are feeling in the prompt.
- Specifically mention the background of the scene in the prompt.

Examples (for default Cartoonish style):

Example 1:
Story Idea: A snowboarder making lots of money but running into trouble because of an ad ban
Short Scenes: 01. His snowboarding skills shone brightly. 02. He thought of sharing his journey. 03. An ad might highlight his talent. 04. But, a ban shattered his plan.
Output: Cartoonish. Medium shot, full body view. A vibrant boy with curly black hair, sparkling brown eyes, and olive-toned skin stands atop a snowy peak in his red shirt and blue trousers, gripping his snowboard with pride. Behind him, the sky fades from golden sunset to starry night, with faint swirling shapes above, reflecting his dreams and the world he's about to challenge. His eyes shine with bold determination—a hero on the edge of his story. Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only.

Example 2:
Story Idea: A genius coder builds an app that helps students manage homework, and she quickly gains a following. But when her school finds out she's using the school's internal database, they suspend her access.
Short Scenes: 01. Her app skyrocketed in popularity. 02. She grinned as positive reviews poured in. 03. She connected it to the school's system for better performance. 04. But then, the school cracked down hard.
Output: Cartoonish. Medium shot, full body view. A sharp-eyed girl with wild curly hair tied in a yellow bandana and slipping oversized glasses crouches over her glowing laptop in a swirl of digital sparks. Her oversized hoodie beams with cartoon icons as colour streams rise like magic. Behind her, shadows of school hallways and whispering students loom faintly, while her cat watches quietly—her genius, courage, and the storm ahead all captured in one frozen moment. Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only.
"""

# Detailed Scene Generation Prompt
DETAILED_SCENE_GENERATION_PROMPT = """
You are a children's story book story pages prompts generator expert.

Here are the inputs provided:
1. Story idea: {story_idea}
2. All Short Scenes: {all_short_scenes}
3. Cover page prompt: {cover_page_prompt}
4. Story page prompt needed scene: {scene_number}.{scene}

Your task is to make the story page prompt exactly for that provided scene considering the story idea, all scenes and Cover page prompt.

ABSOLUTELY CRITICAL — NO CHARACTER NAMES:
Do NOT include the character's name (e.g. "Santiago", "Layla", "Barnaby", etc.) anywhere in the prompt. Instead, refer to them using generic descriptions (e.g. "the boy", "the girl", "the pup", "the dog"). Image generation models do not understand names and using proper nouns/names frequently triggers content moderation filters (resulting in blocked/failed generation).

ABSOLUTELY CRITICAL — TEXT-FREE IMAGE: The generated image MUST contain ZERO text of any kind. This means:
- NO book title, NO author name, NO character names written anywhere
- NO letters, NO words, NO numbers, NO signs, NO labels, NO captions
- NO text on objects (books, signs, shirts, banners, screens, etc.)
- NO letter-like shapes, NO writing, NO typography, NO watermarks
- NO speech bubbles, NO dialogue bubbles, NO thought bubbles, NO word balloons, NO comic-style text containers of any kind
- Do NOT describe any text appearing in the scene
- Do NOT describe speech bubbles or dialogue containers in the scene
- Always end the prompt with: "Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."

For the consistency of entities like characters, objects, etc, across scenes, give as much details about those entities when mention them in the story.
For eg. the cat (yellow fur, big eyes, small ears, etc) went to the park.

CHARACTER AGE DESCRIPTION STYLE:
When describing characters, do NOT state a numeric age (e.g. "6-year-old", "fourteen-year-old"). Instead convey their size and build through physical descriptors like {build_descriptors}.
The characters must look right for {image_audience} — match their build, clothing and bearing to that audience, not to a younger one.

CHARACTER SIZE CONSISTENCY (important):
- Try to keep the main character(s) at a similar scale across scenes - avoid dramatic jumps between close-ups and wide shots.
- Prefer medium shots (waist-up or full body) as the default framing, but vary naturally when the scene calls for it.
- The character(s) should generally occupy a similar proportion of the image across scenes.
- Keep character proportions (head size, body shape) consistent throughout.

ART STYLE INSTRUCTION:
{illustration_style_instruction}

In your output for each scene,
- Specifically mention the art style in the prompt. Be specific about the art style.
- Specifically mention the actions/tasks the entities are doing/behaving in the prompt.
- Specifically mention the emotions the characters are feeling in the prompt.
- Specifically mention the background of the scene in the prompt.


The story page prompt should be,
- About 100-150 words (max 2800 characters as otherwise the API breaks.) Output only the most important parts of the prompt.
- Use English language.
- Keeps the tone engaging and suitable for {image_audience}
- Include details about every characters' clothing and appearance that are appropriate for the specified art style. Clothing must be {image_clothing}. Never depict revealing or sexualised clothing.
- Maintains consistency of characters and background with the story's overall theme considering Cover page prompt.
- {illustration_style_instruction}
- Important: Exactly make the story page prompt for the specified scene.
- Important: Add a detailed explanation about the characters and other entities at the beginning of the prompt to maintain consistency of entities across scenes. Mention about clothing, wearings, and etc.
- Specifically mention the art style in the prompt. Be specific about the art style.
- Make the story very interesting and engaging. Make sure the story is not boring at all.
- ABSOLUTELY CRITICAL — NO CHARACTER NAMES: Do NOT include character names in the prompt. Use descriptions like "the boy" or "the girl" instead.
- ABSOLUTELY CRITICAL — TEXT-FREE IMAGE: The image MUST contain ZERO text of any kind. NO letters, NO words, NO numbers, NO signs, NO labels, NO text on objects, NO speech bubbles, NO dialogue bubbles. Always end the prompt with: "Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."


Examples:

Example 1:
Story Idea: A snowboarder making lots of money but running into trouble because of an ad ban
All Short Scenes: 01.His snowboarding skills shone brightly.---02.He thought of sharing his journey.---03.An ad might highlight his talent.---04.But, a ban shattered his plan.
Cover Page Prompt: Cartoonish. A vibrant, energetic boy with curly black hair, sparkling brown eyes, and olive-toned skin stands atop a snowy peak in his red shirt and blue trousers, gripping his snowboard with pride. Behind him, the sky fades from golden sunset to starry night, with faint swirling shapes above, reflecting his dreams and the world he's about to challenge. His eyes shine with bold determination—a hero on the edge of his story.
Story page prompt needed scene: 01.His snowboarding skills shone brightly.
Output: Cartoonish. Medium shot, full body view. A vibrant and ambitious boy with curly black hair, sparkling brown eyes, and warm olive-toned skin, wearing his signature red shirt and blue trousers, with an expressive face that reflects his passion, drive, and youthful energy, glides smoothly down a sunlit snow-covered hill, his movements graceful and precise, his face beaming with triumph as the setting sun casts a golden glow across the landscape. Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only.

Example 2:
Story Idea: A genius coder builds an app that helps students manage homework, and she quickly gains a following. But when her school finds out she's using the school's internal database, they suspend her access.
All Short Scenes: 01.Her app skyrocketed in popularity.---02.She grinned as positive reviews poured in.---03.She connected it to the school's system for better performance.---04.But then, the school cracked down hard.
Cover Page Prompt: Cartoonish. A sharp-eyed, small-statured girl with wild curly hair tied in a yellow bandana and slipping oversized glasses crouches over her glowing laptop in a swirl of digital sparks. Her oversized hoodie beams with cartoon icons as code streams rise like magic. Behind her, shadows of school hallways and whispering students loom faintly, while her cat watches quietly—her genius, courage, and the storm ahead all captured in one frozen moment.
Story page prompt needed scene: 04.But then, the school cracked down hard.
Output: Cartoonish. Medium shot, full body view. A sharp-eyed, small-statured girl with a wild puff of curly hair tied back in a bright yellow bandana, oversized glasses that constantly slip down her nose, and an oversized hoodie with cartoon icons on it, stands frozen in the school hallway, phone in hand, mouth slightly open. A gray storm cloud forms above her head while other students whisper and glance at her with wide eyes. Her backpack looks heavier than ever. Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only.
"""


# ── Minimal scene prompt (used when the full prompt triggers content filters) ──
# Omits the bulk "all_short_scenes" text which is the most common trigger for
# Gemini PROHIBITED_CONTENT blocks (the concatenated story text can trip safety
# filters even though each individual scene is innocuous).
DETAILED_SCENE_GENERATION_PROMPT_MINIMAL = """
You are a children's story book illustration prompt generator.

Inputs:
1. Story idea: {story_idea}
2. Cover page prompt: {cover_page_prompt}
3. Scene to illustrate: {scene_number}. {scene}

Generate a detailed image generation prompt for this scene.

ABSOLUTELY CRITICAL — NO CHARACTER NAMES:
Do NOT include the character's name (e.g. "Santiago", "Layla", "Barnaby", etc.) anywhere in the prompt. Instead, use generic descriptions (e.g. "the boy", "the girl", "the pup", "the dog"). Proper nouns/names frequently trigger content moderation filters.

CRITICAL — TEXT-FREE IMAGE: The image MUST contain ZERO text. NO letters, words, numbers, signs, labels, speech bubbles, dialogue bubbles, or writing of any kind.

CHARACTER AGE DESCRIPTION STYLE:
Do NOT state numeric ages. Use physical descriptors like {build_descriptors}.
The characters must look right for {image_audience}, not for a younger audience.

ART STYLE INSTRUCTION:
{illustration_style_instruction}

Requirements:
- 100-150 words (max 2800 characters)
- Start with character descriptions (clothing, appearance) for consistency with the cover prompt
- Include the art style, actions, emotions, and background
- Suitable for {image_audience}
- End with: "Absolutely no text, no speech bubbles, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."
"""

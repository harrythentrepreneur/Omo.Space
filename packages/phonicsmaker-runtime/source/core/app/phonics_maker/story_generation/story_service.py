# core/story_generation/story_service.py

from typing import List, Optional
from app.core.config.config import settings
from app.core.config.logger import logger
from app.core.utils.retry import retry
from app.core.ai.ai_config import ai_config
from app.core.ai.prompts import (
    BASE_STORY_GENERATION_PROMPT,
    DETAILED_SCENE_GENERATION_PROMPT,
    DETAILED_SCENE_GENERATION_PROMPT_MINIMAL,
    STORY_QUALITY_REVIEW_PROMPT,
    DIFFERENTIATE_STORY_PROMPT,
    LANGUAGE_SPECIFIC_INSTRUCTIONS,
    level_configs,
    LEGACY_DIFFICULTY_MAP,
    DEFAULT_INTEREST_AGE_BAND,
    build_interest_age_block,
    get_interest_age_config,
    resolve_interest_age_band,
)
from app.core.ai.ai_config import GeminiContentRejectedError
from app.db.models.story import DifficultyLevel, LanguageVariant
import re
import asyncio
import time


class StoryService:
    def __init__(self):
        pass

    @staticmethod
    def _resolve_difficulty_key(difficulty_level) -> str:
        """Resolve any difficulty value to a '1'-'5' key for level_configs."""
        raw = str(difficulty_level.value if hasattr(difficulty_level, 'value') else difficulty_level)
        # Already a new-style key?
        if raw in level_configs:
            return raw
        # Try legacy mapping
        if raw in LEGACY_DIFFICULTY_MAP:
            return LEGACY_DIFFICULTY_MAP[raw]
        # Default to "1" (Beginner) if unrecognised
        return "1"

    @retry(
        exceptions=(Exception),
        max_retries=settings.GENERATE_SCENES_MAX_RETRIES,
        initial_delay=settings.GENERATE_SCENES_DELAY,
        max_delay=settings.GENERATE_SCENES_MAX_RETRIES,
        backoff_factor=2,
    )
    async def generate_short_scenes(
        self,
        story_idea: str,
        phonemes: List[str],
        difficulty_level: DifficultyLevel,
        is_free: bool,
        language_variant: Optional[LanguageVariant] = None,
        story_type: Optional[str] = None,
        # ── V2 fields ──
        known_phonemes: Optional[List[str]] = None,
        focus_phonemes: Optional[List[str]] = None,
        sight_words: Optional[List[str]] = None,
        strict_decodable: Optional[bool] = None,
        vocabulary_mode: Optional[str] = None,
        focus_mode: Optional[str] = None,
        morphology_focus: Optional[List[str]] = None,
        story_format: Optional[str] = None,
        student_age: Optional[str] = None,
        year_level: Optional[str] = None,
        curriculum: Optional[str] = None,
        # ── Series context (book sets) ──
        book_title: Optional[str] = None,
        series_characters: Optional[list] = None,
        series_theme: Optional[str] = None,
        series_info: Optional[dict] = None,
        character_pronouns: Optional[str] = None,
        page_count: Optional[int] = None,
    ) -> List[str]:
        """
        Generate short story scenes based on phonemes, story idea, and difficulty level.
        Each scene is a single sentence of 5-7 words.
        
        V2 mode: When known_phonemes/focus_phonemes are provided, appends strict
        decodability constraints to the prompt so every word is decodable using
        only the known + focus GPCs (plus any permitted sight words).
        """
        try:
            # Detect V2 mode
            is_v2 = bool(known_phonemes or focus_phonemes)
            
            logger.info(
                f"Generating short scenes for phonemes: {phonemes}, idea: {story_idea}, "
                f"level: {difficulty_level}, is_free: {is_free}, v2={is_v2}"
            )
            if is_v2:
                logger.info(
                    f"V2 params: known={len(known_phonemes or [])}, focus={len(focus_phonemes or [])}, "
                    f"sight_words={len(sight_words or [])}, strict={strict_decodable}, "
                    f"focus_mode={focus_mode}, morphology={morphology_focus}, "
                    f"format={story_format}, age={student_age}"
                )

            if is_free:
                num_scenes = 6
            elif page_count:
                num_scenes = max(6, min(page_count, 20))
            else:
                num_scenes = 20

            # 1. Determine language_variant_name
            VARIANT_MAP = {
                # Frontend codes
                "en_au": ("AU", "Australian English"),
                "en_gb": ("UK", "UK English"),
                "en_uk": ("UK", "UK English"),
                "en_us": ("US", "US English"),
                "en_ca": ("US", "US English"),       # Canadian uses US English rules
                "en_nz": ("AU", "Australian English"), # NZ uses AU English rules
                "fr": ("FR", "French"),
                "es": ("ES", "Spanish"),
                # Legacy codes (backward compat)
                "AU": ("AU", "Australian English"),
                "UK": ("UK", "UK English"),
                "US": ("US", "US English"),
                "FR": ("FR", "French"),
                "ES": ("ES", "Spanish"),
            }
            variant_key, language_variant_name = VARIANT_MAP.get(
                language_variant, ("US", "US English")
            )
            language_variant = variant_key

            # 2. Prepare language_variant_instructions
            language_instruction_template = LANGUAGE_SPECIFIC_INSTRUCTIONS.get(language_variant)
            
            # 3. Resolve difficulty to "1"-"5" key and get config
            resolved_key = self._resolve_difficulty_key(difficulty_level)
            level_instruction_template = level_configs[resolved_key]

            # 4. Format phonics_use and language_mechanics from the config
            # V2 FIX: When focus_phonemes are provided, use ONLY focus phonemes
            # for the base prompt's {phonemes} so the LLM's core "weave N words
            # per phoneme" instruction targets teaching sounds — not all 40+ known
            # sounds equally.  The V2 override block handles known/focus separately.
            base_prompt_phonemes = focus_phonemes if (is_v2 and focus_phonemes) else phonemes
            formatted_phonics_use = level_instruction_template["phonics_use"].format(
                phonemes=base_prompt_phonemes,
                language_variant_name=language_variant_name
            )
            formatted_language_mechanics = level_instruction_template["language_mechanics"].format(
                language_variant_name=language_variant_name,
                language_variant_instructions=language_instruction_template
            )

            # 4b. Resolve the interest age band — independent of reading level.
            # Reading level governs decoding; the band governs themes, character
            # ages, titles and tone, so an older struggling reader gets simple
            # words without nursery content.
            interest_band = resolve_interest_age_band(student_age)
            interest_cfg = get_interest_age_config(student_age)
            user_level = level_instruction_template["user_level"]
            logger.info(
                f"Interest age band: {interest_band} (from student_age={student_age!r}), "
                f"decoding level: {user_level}"
            )

            # 5. Prepare all variables for the BASE_STORY_GENERATION_PROMPT
            prompt_vars = {
                "user_level": user_level,
                "word_count_range": level_instruction_template["word_count_range"],
                "title_spec": level_instruction_template["title_spec"],
                "vocab_guardrail": level_instruction_template["vocab_guardrail"],
                "tone_description": (
                    level_instruction_template["tone_description"]
                    if interest_band == DEFAULT_INTEREST_AGE_BAND
                    else f"• {interest_cfg['tone']}"
                ),
                "story_idea": story_idea,
                "phonemes": base_prompt_phonemes,
                "scene_count": num_scenes,
                "language_variant_name": language_variant_name,
                "phonics_use": formatted_phonics_use,
                "language_mechanics": formatted_language_mechanics,
                # ── Interest age (decoupled from reading level) ──
                "author_persona": interest_cfg["author_persona"],
                "book_framing": interest_cfg["book_framing"],
                "reader_descriptor": interest_cfg["reader_descriptor"],
                "reader_target": interest_cfg["reader_target_template"].format(user_level=user_level),
                "vocab_target": interest_cfg["vocab_target_template"].format(user_level=user_level),
                "author_test": interest_cfg["author_test"],
                "action_vocabulary": interest_cfg["action_vocabulary"],
                "article": interest_cfg["article"],
            }

            # 6. Format the final prompt
            final_prompt = BASE_STORY_GENERATION_PROMPT.format(**prompt_vars)

            # 7. Inject pronoun instruction if specified
            if character_pronouns:
                final_prompt += (
                    f"\n\n### CHARACTER PRONOUNS\n"
                    f"The main character uses **{character_pronouns}** pronouns. "
                    f"Use these pronouns consistently in EVERY scene — never switch.\n"
                )

            # 8. Inject series context (book sets) — recurring characters, theme, title
            series_context = self._build_series_context_block(
                book_title=book_title,
                series_characters=series_characters,
                series_theme=series_theme,
                series_info=series_info,
            )
            if series_context:
                final_prompt += f"\n\n{series_context}\n"
                logger.info("Injected series context block into prompt")

            # 8. Inject story-type modifier if not the default "narrative"
            story_type_instructions = self._get_story_type_prompt_fragment(story_type)
            if story_type_instructions:
                final_prompt += f"\n\n{story_type_instructions}\n"
                logger.info(f"Applied story type modifier: {story_type}")

            # ── 8. V2: Inject decodability & teaching constraints ──────────
            if is_v2:
                final_prompt += self._build_v2_prompt_block(
                    known_phonemes=known_phonemes,
                    focus_phonemes=focus_phonemes,
                    sight_words=sight_words,
                    strict_decodable=strict_decodable,
                    vocabulary_mode=vocabulary_mode,
                    focus_mode=focus_mode,
                    morphology_focus=morphology_focus,
                    story_format=story_format,
                    student_age=student_age,
                    year_level=year_level,
                    curriculum=curriculum,
                )
                logger.info("Injected V2 decodability prompt block")

            # ── 8c. Interest age — applies to EVERY flow, not just V2 ──────
            # Appended last so it has the final word on content. Scoped so it
            # cannot loosen the decodability rules above it.
            interest_age_block = build_interest_age_block(
                student_age,
                scope_note=(
                    "\n**SCOPE:** This section governs WHAT the story is about — themes, character "
                    "ages, titles, tone. Any decodability or phoneme constraints above still govern "
                    "WHICH WORDS you may use. Simple words, older story."
                ),
            )
            if interest_age_block:
                final_prompt += f"\n\n{interest_age_block}\n"
                logger.info(f"Injected interest-age block: {interest_band}")

            # Call Gemini API with the prompt
            _t0 = time.perf_counter()
            story_text = await ai_config.generate_with_gemini(final_prompt)
            logger.info(f"⏱️  [TIMING][story] Initial Gemini call: {time.perf_counter() - _t0:.2f}s")

            # ── 9. Two-pass quality review (self-critique & rewrite) ──────
            if self._should_run_quality_review(
                is_v2=is_v2,
                vocabulary_mode=vocabulary_mode,
                strict_decodable=strict_decodable,
                known_phonemes=known_phonemes,
                focus_phonemes=focus_phonemes,
            ):
                _t0 = time.perf_counter()
                story_text = await self._review_and_rewrite_story(
                    story_text=story_text,
                    num_scenes=num_scenes,
                    known_phonemes=known_phonemes,
                    focus_phonemes=focus_phonemes,
                    sight_words=sight_words,
                    vocabulary_mode=vocabulary_mode,
                    strict_decodable=strict_decodable,
                    student_age=student_age,
                )
                logger.info(f"⏱️  [TIMING][story] Quality review rewrite: {time.perf_counter() - _t0:.2f}s")
            else:
                logger.info("⏱️  [TIMING][story] Quality review SKIPPED (V1 or authentic mode)")

            # Split the story into scenes
            story = self._parse_story_scenes_and_title(story_text, is_free, num_scenes)

            cleaned_title = self.clean_story_title(story["title"])

            logger.info(f"Generated {len(story['scenes'])} short scenes.")
            return cleaned_title, story["scenes"]

        except Exception as e:
            logger.error(f"Error generating short scenes: {str(e)}")
            raise e

    @retry(
        exceptions=(Exception),
        max_retries=settings.GENERATE_SCENES_MAX_RETRIES,
        initial_delay=settings.GENERATE_SCENES_DELAY,
        max_delay=settings.GENERATE_SCENES_MAX_RETRIES,
        backoff_factor=2,
    )
    async def differentiate_story(
        self,
        original_title: str,
        original_scenes: List[str],
        target_difficulty: str,
        language_variant: Optional[LanguageVariant] = None,
        student_age: Optional[str] = None,
        # We can pass similar params to V2 if we want vocabulary guardrails
        # but for now we rely on the target level constraints.
    ) -> tuple[str, List[str]]:
        """
        Rewrite an existing story to a new difficulty level while maintaining exactly the same
        number of scenes and core narrative arc, so pre-generated images match.
        """
        try:
            logger.info(f"Differentiating story to level: {target_difficulty}")
            
            # Format original story
            formatted_original = original_title + "|||" + "---".join(original_scenes)
            scene_count = len(original_scenes)

            # Resolve language
            VARIANT_MAP = {
                "en_au": ("AU", "Australian English"),
                "en_gb": ("UK", "UK English"),
                "en_uk": ("UK", "UK English"),
                "en_us": ("US", "US English"),
                "en_ca": ("US", "US English"),
                "en_nz": ("AU", "Australian English"),
                "fr": ("FR", "French"),
                "es": ("ES", "Spanish"),
                "AU": ("AU", "Australian English"),
                "UK": ("UK", "UK English"),
                "US": ("US", "US English"),
                "FR": ("FR", "French"),
                "ES": ("ES", "Spanish"),
            }
            variant_key, language_variant_name = VARIANT_MAP.get(
                language_variant, ("US", "US English")
            )
            language_instruction_template = LANGUAGE_SPECIFIC_INSTRUCTIONS.get(variant_key, "")

            # Resolve difficulty
            resolved_key = self._resolve_difficulty_key(target_difficulty)
            level_instruction_template = level_configs[resolved_key]
            
            target_level_name = level_instruction_template["user_level"]
            word_count_range = level_instruction_template["word_count_range"]
            vocab_guardrail = level_instruction_template["vocab_guardrail"]
            formatted_language_mechanics = level_instruction_template["language_mechanics"].format(
                language_variant_name=language_variant_name,
                language_variant_instructions=language_instruction_template
            )

            prompt_vars = {
                "original_story": formatted_original,
                "target_level_name": target_level_name,
                "language_variant_name": language_variant_name,
                "word_count_range": word_count_range,
                "scene_count": scene_count,
                "vocab_guardrail": vocab_guardrail,
                "language_mechanics": formatted_language_mechanics,
                "interest_age_block": build_interest_age_block(
                    student_age,
                    scope_note=(
                        "\n**SCOPE:** Re-levelling changes decoding difficulty only. The interest "
                        "age above is fixed — do not drift the content younger or older."
                    ),
                ),
            }

            final_prompt = DIFFERENTIATE_STORY_PROMPT.format(**prompt_vars)

            _t0 = time.perf_counter()
            story_text = await ai_config.generate_with_gemini(final_prompt)
            logger.info(f"⏱️  [TIMING][story] Differentiate Gemini call: {time.perf_counter() - _t0:.2f}s")

            # We can use the same parser
            # if is_free logic is applied purely to validate max allowed scenes, but here we just pass False
            story = self._parse_story_scenes_and_title(story_text, False, scene_count)
            
            # Validate scene count strictly
            if len(story["scenes"]) != scene_count:
                logger.warning(f"Differentiation returned {len(story['scenes'])} scenes, expected {scene_count}. Retrying...")
                raise ValueError("Scene count mismatch during differentiation.")

            cleaned_title = self.clean_story_title(story["title"])

            logger.info(f"Generated differentiated story ({target_level_name}) successfully.")
            return cleaned_title, story["scenes"]

        except Exception as e:
            logger.error(f"Error differentiating story: {str(e)}")
            raise e

    def _build_v2_prompt_block(
        self,
        known_phonemes: Optional[List[str]] = None,
        focus_phonemes: Optional[List[str]] = None,
        sight_words: Optional[List[str]] = None,
        strict_decodable: Optional[bool] = None,
        vocabulary_mode: Optional[str] = None,
        focus_mode: Optional[str] = None,
        morphology_focus: Optional[List[str]] = None,
        story_format: Optional[str] = None,
        student_age: Optional[str] = None,
        year_level: Optional[str] = None,
        curriculum: Optional[str] = None,
    ) -> str:
        """
        Build the V2 prompt extension for two-tier phoneme control, sight words,
        strict decodability, morphology focus, and story format.
        
        This block is appended AFTER the base prompt and any story-type modifier,
        so it acts as an override layer — the LLM sees the base rules first, then
        these tighter V2 constraints on top.
        """
        parts = ["\n\n### V2 — DECODABILITY & TEACHING CONSTRAINTS"]
        parts.append("(These constraints OVERRIDE the general phonics rules above when they conflict.)\n")

        # The worked examples below have to match the interest age, or a strict
        # GPC set drags the story back to nursery content ("Kit the cat sat on
        # a mat") even when the reader is 12.
        interest_cfg = get_interest_age_config(student_age)

        # ── Two-tier phoneme pools ──────────────────────────────────
        if known_phonemes and focus_phonemes:
            known_str = ", ".join(known_phonemes)
            focus_str = ", ".join(focus_phonemes)
            parts.append(
                f"**KNOWN GPCs** (grapheme-phoneme correspondences the student has already been taught):\n"
                f"[{known_str}]\n\n"
                f"**FOCUS GPCs** (the NEW sounds being taught in this book — the teaching target):\n"
                f"[{focus_str}]\n\n"
                "DECODABILITY RULES:\n"
                "• Every word in the story MUST be decodable using ONLY the known GPCs + focus GPCs listed above.\n"
                "• Do NOT use any word that contains a grapheme-phoneme correspondence outside these two sets "
                "(unless it appears in the Allowed Sight Words list below).\n"
                "• Feature the FOCUS GPCs prominently — weave at least 4-8 different words per focus GPC across the book. "
                "These are the sounds the student is learning, so they need maximum exposure.\n"
                "• Known GPCs may appear freely in any word but are NOT the teaching focus — don't over-emphasise them.\n"
                "• Think carefully about each word: can the student decode it letter-by-letter using only the "
                "known + focus GPCs? If not, replace it or use a sight word instead.\n"
            )
        elif known_phonemes:
            known_str = ", ".join(known_phonemes)
            parts.append(
                f"**KNOWN GPCs** (the student can decode these):\n[{known_str}]\n\n"
                "RULE: Every word must be decodable using only these GPCs (plus any sight words below).\n"
            )
        elif focus_phonemes:
            focus_str = ", ".join(focus_phonemes)
            parts.append(
                f"**FOCUS GPCs** (teaching target — feature these prominently):\n[{focus_str}]\n\n"
                "RULE: Weave 4-8+ different words per focus GPC. These sounds need maximum exposure.\n"
            )

        # ── Vocabulary mode — 3-tier control ─────────────────────────
        # Resolve vocabulary mode: prefer explicit vocabulary_mode, fall back to strict_decodable boolean
        effective_mode = vocabulary_mode or ('decodable' if strict_decodable else 'instructional')

        # Count total GPCs available (used by multiple sections below)
        total_gpcs = len(known_phonemes or []) + len(focus_phonemes or [])

        # ── Story quality boost (BEFORE decodability rules so LLM prioritises naturalness) ──
        # In DECODABLE (STRICT) mode, quality guidance must not override decodability
        if total_gpcs <= 40 and total_gpcs > 0:
            if effective_mode == 'decodable':
                quality_intro = (
                    "📖 **STORY QUALITY — IMPORTANT:**\n"
                    "You have a limited set of decodable words. Write the best story possible within them.\n"
                    "Every word must still be decodable — choose the most natural-sounding decodable words available.\n\n"
                )
            elif total_gpcs <= 20:
                quality_intro = (
                    "📖 **STORY QUALITY — CRITICAL (READ THIS FIRST):**\n"
                    "You have a VERY LIMITED set of decodable words. This makes story quality EVEN MORE important.\n"
                    "A bad story with lots of phoneme words is WORSE than a simpler story that children enjoy.\n"
                    "Your #1 job is to write a story a child would LOVE — phonics compliance is secondary.\n\n"
                )
            else:
                quality_intro = (
                    "📖 **STORY QUALITY — IMPORTANT (READ THIS FIRST):**\n"
                    "You have a moderate but still limited set of decodable words. "
                    "Use the extra vocabulary to tell a BETTER story, not just to cram in more phoneme words.\n\n"
                )
            parts.append(
                quality_intro +
                "STORY QUALITY RULES (HIGHEST PRIORITY):\n"
                "• Plan a SIMPLE but COMPLETE story arc FIRST: character + want/need + problem + resolution.\n"
                "• Make every sentence serve the story — no filler or random word-stuffing.\n"
                f"• {interest_cfg['conversation_line']}\n"
                "• If a decodable word doesn't fit naturally, DON'T force it — skip it.\n"
                "• Read each sentence aloud mentally — does it sound like something from a real book?\n"
                f"• {interest_cfg['understands_line']}\n"
                f"• {interest_cfg['smile_line']}\n\n"
                "EXAMPLES OF BAD vs GOOD SENTENCES:\n"
                + interest_cfg["quality_bad_examples"] + "\n"
                + interest_cfg["quality_good_examples"] + "\n"
                "• If your sentence sounds like a BAD example above, REWRITE IT.\n"
                f"• Every sentence should pass the test: \"{interest_cfg['author_test']}\"\n\n"
            )

            # Chain-of-thought planning for very small GPC sets
            if total_gpcs <= 20:
                parts.append(
                    "🧠 **PRE-WRITING PLANNING (do this mentally before writing):**\n"
                    "1. First, list 20-30 simple, NATURAL words you can make from the known + focus GPCs.\n"
                    "   Focus on common nouns (cat, dog, mat, sun, pen, cup), verbs (sit, run, nap, pat, hug, dig),\n"
                    "   and adjectives (big, hot, red, sad, fun) that children use every day.\n"
                    "2. DISCARD any word that sounds forced or unusual (e.g., 'tot', 'cot', 'cod', 'mop').\n"
                    f"   {interest_cfg['natural_word_test']}\n"
                    "3. Plan a simple story using ONLY the natural-sounding words from your list.\n"
                    "4. Then write the scenes — if a scene feels awkward, simplify or restructure.\n\n"
                )

        if effective_mode == 'decodable':
            parts.append(
                "⚠️ **VOCABULARY MODE: DECODABLE (STRICT)**\n"
                "Absolutely NO words containing GPCs outside the known + focus sets.\n"
                "Every single word must be decodable by a student who only knows those letter-sound correspondences.\n"
                "Common words like \"the\" or \"said\" are ONLY allowed if they appear in the Allowed Sight Words list.\n"
                "If you cannot find a decodable word, restructure the sentence rather than using an undecodable word.\n\n"
                "⚠️ **BUT REMEMBER:** Story quality rules above are HIGHEST PRIORITY. A natural-sounding sentence\n"
                "with fewer decodable words is ALWAYS better than an unnatural sentence crammed with decodable words.\n\n"
            )

            # Glue words safety net — when the GPC set is very small, the LLM
            # literally cannot form grammatical sentences without basic function words
            if total_gpcs <= 20:
                parts.append(
                    "🔧 **ESSENTIAL FUNCTION WORDS (automatic sight words for small GPC sets):**\n"
                    "Because the GPC set is very small, you MAY freely use these essential\n"
                    "function words even if they are not in the sight word list above:\n\n"
                    "Pronouns: I, me, you, he, she, it, we, they, them, him, her, his, us, my, your\n"
                    "Verbs: is, are, was, had, has, have, can, will, do, did, got, get, put, let, see, said, like, come, want, go, been, make, made\n"
                    "Articles/Determiners: the, a, an, this, that, some, all, one, two\n"
                    "Prepositions: in, on, at, up, to, for, with, from, out, into, by, of, off\n"
                    "Conjunctions: and, but, or, so, if, when, then\n"
                    "Adverbs/Other: not, no, here, there, very, too, now, just\n"
                    "Question words: what, who, how, where, why\n\n"
                    "• These act as automatic sight words to make sentences grammatically possible.\n"
                    "• All OTHER content words (nouns, main verbs, adjectives) must still be strictly decodable.\n"
                    "• Use these freely — they are essential for natural-sounding sentences.\n\n"
                )
        elif effective_mode == 'instructional':
            parts.append(
                "📘 **VOCABULARY MODE: INSTRUCTIONAL**\n"
                "The story should be MOSTLY decodable using the known + focus GPCs, but you MAY carefully \n"
                "introduce a small number of age-appropriate words that go beyond the GPC sets.\n\n"
                "INSTRUCTIONAL RULES:\n"
                "• Aim for approximately 80-90% of words to be fully decodable using the GPCs listed above.\n"
                "• When introducing a word beyond the GPC sets, choose common, meaningful vocabulary \n"
                "  that the student is likely to encounter in guided reading.\n"
                "• Limit non-decodable, non-sight-word vocabulary to 1-2 new words per page at most.\n"
                "• Use context clues and illustrations to support comprehension of any stretch vocabulary.\n"
                "• Sight words from the list below may appear freely.\n"
                "• The FOCUS GPCs should still be prominently featured — this is still a phonics teaching text.\n\n"
            )
        elif effective_mode == 'authentic':
            parts.append(
                "📖 **VOCABULARY MODE: AUTHENTIC**\n"
                "Use rich, natural language appropriate for the student's year level. \n"
                "There is NO strict decodability constraint — write as you would for a real children's book \n"
                "at this reading level.\n\n"
                "AUTHENTIC MODE RULES:\n"
                "• Use age-appropriate vocabulary freely — do not restrict yourself to the GPC sets.\n"
                "• The sight words listed below should be DELIBERATELY WOVEN IN for spelling and \n"
                "  vocabulary practice. Feature them naturally throughout the story.\n"
                "• The FOCUS GPCs (if any) should still appear in words throughout the story, but they \n"
                "  are practice targets, not hard constraints.\n"
                "• Prioritise natural, engaging prose that a student at this level would enjoy reading.\n"
                "• Think of this as a 'real book' that happens to practise target sounds and sight words.\n\n"
            )

        # ── Sight words (escape hatch for decodability) ──────────────
        if sight_words:
            words_str = ", ".join(sight_words)
            parts.append(
                f"**ALLOWED SIGHT WORDS** (high-frequency words the student recognises by sight):\n"
                f"[{words_str}]\n\n"
                "• These words may appear freely even if they contain GPCs outside the known/focus sets.\n"
                "• Use them naturally to help story flow — they are the decodability escape hatch.\n"
                "• Do NOT treat sight words as phonics teaching targets.\n"
            )

        # ── Morphology focus ─────────────────────────────────────────
        if focus_mode == "morphology" and morphology_focus:
            morph_str = ", ".join(morphology_focus)
            parts.append(
                f"\n**MORPHOLOGY FOCUS** (word parts being taught):\n[{morph_str}]\n\n"
                "• Instead of focusing on individual letter-sound correspondences, this book teaches WORD PARTS.\n"
                "• Feature words containing these morphemes (prefixes, suffixes, roots) prominently throughout.\n"
                "• Weave 3-6 different words per morpheme across the book.\n"
                "• Help the student recognise how these word parts change word meaning.\n"
                "• The phonics/GPC constraints above still apply — words should still be decodable.\n"
            )
        elif focus_mode == "both" and morphology_focus:
            morph_str = ", ".join(morphology_focus)
            parts.append(
                f"\n**ADDITIONAL MORPHOLOGY FOCUS** (word parts alongside phonics):\n[{morph_str}]\n\n"
                "• In addition to the focus GPCs, also incorporate words featuring these word parts.\n"
                "• Where possible, choose words that showcase BOTH a focus GPC AND a target morpheme.\n"
            )

        # ── Story format ─────────────────────────────────────────────
        if story_format == "passage":
            parts.append(
                "\n**FORMAT OVERRIDE — CONTINUOUS PASSAGE:**\n"
                "Write as a continuous reading passage rather than a picture-book story.\n"
                "• Scenes can be longer (up to 2 connected sentences per scene).\n"
                "• The text should read as connected prose suitable for guided reading or fluency practice.\n"
                "• Maintain the same title|||scene1---scene2--- output format.\n"
                "• Focus on flowing, natural prose rather than dramatic scene changes.\n"
            )

        # NOTE: interest age is no longer handled here. It used to live in this
        # V2-only block, so it was silently ignored by every non-V2 flow (free
        # book, landing creator, book sets, differentiate). It is now injected
        # for all flows in generate_short_scenes via build_interest_age_block.

        # ── Year / grade level (reading complexity) ───────────────────
        if year_level:
            parts.append(
                f"\n**YEAR/GRADE LEVEL:** {year_level}\n"
                "• Align phonics patterns, sight word load, sentence length, and vocabulary complexity to this level.\n"
                "• This controls reading difficulty and decodability — not just themes.\n"
                "• Earlier levels: shorter sentences, simpler CVC/CVCC patterns, high-frequency sight words only.\n"
                "• Later levels: multi-syllabic words, complex spelling patterns, longer connected sentences.\n"
            )

        # ── Curriculum context & story theme localisation ─────────────────────
        if curriculum:
            # Extract country code from curriculum code (e.g. "au_vic" → "au", "nz" → "nz")
            country_code = curriculum.split("_")[0] if "_" in curriculum else curriculum

            COUNTRY_THEME_MAP = {
                "au": (
                    "Australia",
                    "• Set the story in Australia. Use Australian settings (beaches, bushland, outback, "
                    "suburban backyards, school playgrounds).\n"
                    "• Use Australian character names (e.g. Matilda, Jack, Ava, Liam, Ruby, Noah).\n"
                    "• Reference Australian animals (kangaroos, koalas, wombats, platypus, kookaburras, "
                    "cockatoos, possums, echidnas) and plants (gum trees, bottlebrush, banksia).\n"
                    "• Include Australian cultural references where natural (Vegemite, meat pies, cricket, "
                    "AFL, the beach, barbecues, Anzac biscuits).\n"
                    "• Use Australian place references (the bush, the reef, the outback, rock pools).\n"
                ),
                "uk": (
                    "the United Kingdom",
                    "• Set the story in the UK. Use British settings (villages, parks, gardens, "
                    "castles, seaside towns, countryside, school playgrounds).\n"
                    "• Use British character names (e.g. Oliver, Amelia, Harry, Isla, George, Poppy).\n"
                    "• Reference British animals (hedgehogs, badgers, foxes, robins, red squirrels, "
                    "owls, sheep) and nature (oak trees, bluebells, meadows).\n"
                    "• Include British cultural references where natural (tea, crumpets, football, "
                    "Bonfire Night, the seaside, wellies, rainy days, school uniforms).\n"
                ),
                "us": (
                    "the United States",
                    "• Set the story in the United States. Use American settings (neighborhoods, "
                    "state parks, farms, cities, school yards, lakes, mountains).\n"
                    "• Use American character names (e.g. Emma, Liam, Sophia, Jackson, Olivia, Mason).\n"
                    "• Reference American animals (raccoons, bald eagles, black bears, chipmunks, "
                    "blue jays, fireflies, deer) and nature (maple trees, redwoods, prairies).\n"
                    "• Include American cultural references where natural (baseball, soccer practice, "
                    "lemonade stands, school buses, campfires, s'mores, Thanksgiving, Fourth of July).\n"
                ),
                "ca": (
                    "Canada",
                    "• Set the story in Canada. Use Canadian settings (forests, lakes, mountains, "
                    "snowy landscapes, small towns, hockey rinks, school playgrounds).\n"
                    "• Use Canadian character names (e.g. Maya, Liam, Charlotte, Ethan, Chloe, Noah).\n"
                    "• Reference Canadian animals (moose, beavers, loons, Canada geese, bears, "
                    "wolves, caribou) and nature (maple trees, pine forests, frozen lakes).\n"
                    "• Include Canadian cultural references where natural (hockey, maple syrup, "
                    "tobogganing, snowshoeing, Tim Hortons, canoe trips).\n"
                ),
                "nz": (
                    "New Zealand / Aotearoa",
                    "• Set the story in New Zealand (Aotearoa). Use New Zealand settings (beaches, "
                    "bush walks, volcanoes, farms, school playgrounds, marae visits).\n"
                    "• Use New Zealand character names, including Māori names where appropriate "
                    "(e.g. Aroha, Wiremu, Tama, Sophie, Jack, Maia, Nikau).\n"
                    "• Reference New Zealand animals (kiwi birds, tūī, fantails/pīwakawaka, wētā, "
                    "dolphins, whales, penguins, sheep) and plants (pōhutukawa, silver fern, kōwhai).\n"
                    "• Include NZ cultural references where natural (rugby, hangi, kapa haka, "
                    "the beach, gumboots, fish and chips, pavlova).\n"
                    "• Use te reo Māori greetings/words naturally where appropriate (kia ora, whānau, kai).\n"
                ),
                "fr": (
                    "France",
                    "• Set the story in France. Use French settings (villages, boulangeries, parks, "
                    "markets, countryside, the sea, school courtyards).\n"
                    "• Use French character names (e.g. Léa, Hugo, Emma, Louis, Chloé, Lucas, Manon).\n"
                    "• Reference French animals and nature (lapins, hérissons, écureuils, coccinelles, "
                    "papillons, oiseaux) and settings (jardins, forêts, montagnes).\n"
                    "• Include French cultural references where natural (croissants, baguettes, "
                    "le marché, la cantine, les vacances, crêpes, la galette des rois).\n"
                ),
                "es": (
                    "Spain",
                    "• Set the story in Spain. Use Spanish settings (pueblos, playas, parques, "
                    "mercados, montañas, patios de colegio).\n"
                    "• Use Spanish character names (e.g. Sofía, Pablo, Lucía, Mateo, Valeria, Hugo).\n"
                    "• Reference Spanish animals and nature (tortugas, mariposas, gatos, perros, "
                    "cigüeñas, flamencos, olivos, naranjos).\n"
                    "• Include Spanish cultural references where natural (tortilla, paella, "
                    "fiestas, el recreo, churros, la playa, fútbol).\n"
                ),
            }

            country_name, theme_instructions = COUNTRY_THEME_MAP.get(
                country_code, (None, None)
            )

            parts.append(
                f"\n**CURRICULUM:** {curriculum}\n"
                "• Use vocabulary and spelling conventions aligned with this curriculum.\n"
                "• Where possible, align topic coverage and text complexity with the expectations of this curriculum.\n"
            )

            if country_name and theme_instructions:
                parts.append(
                    f"\n**STORY SETTING & THEME — LOCALISE TO {country_name.upper()}:**\n"
                    f"{theme_instructions}"
                    "• These are suggestions to make the story feel local and relatable — "
                    "don't force every reference in, just use them where they fit the story naturally.\n"
                    "• If the user's story idea already specifies a particular setting or context, "
                    "respect that — do not override it with the country suggestions above.\n"
                )

            if curriculum.startswith("us_dlm"):
                parts.append(
                    "\n**STUDENT PROFILE — DYNAMIC LEARNING MAPS (DLM):**\n"
                    "This book is for a student on the Dynamic Learning Maps alternative assessment pathway "
                    "(significant cognitive disability). Apply ALL of the following:\n"
                    "• Use SHORT, CONCRETE sentences — one clear idea per scene, no compound clauses.\n"
                    "• Use LITERAL language only — no idioms, sarcasm, figurative speech, or implied meaning. "
                    "Every sentence must mean exactly what it says.\n"
                    "• Prefer AAC-friendly vocabulary: high-frequency words with single clear meanings "
                    "that a student could point to on a communication device.\n"
                    "• Use PREDICTABLE, REPETITIVE sentence patterns — the same structure should recur across "
                    "scenes so the student can anticipate what comes next.\n"
                    "• Focus on FUNCTIONAL literacy: naming people and objects, expressing wants/needs, "
                    "describing immediate actions — not abstract narrative.\n"
                    "• If the story idea contains a DLM Essential Element code (e.g. EE.RL.1.1), treat it as "
                    "the literacy target and write the story to practise that specific skill.\n"
                    "• These constraints OVERRIDE general difficulty and vocabulary settings — always apply "
                    "them regardless of the difficulty level selected.\n"
                )

        return "\n".join(parts)

    @staticmethod
    def _should_run_quality_review(
        is_v2: bool,
        vocabulary_mode: Optional[str],
        strict_decodable: Optional[bool],
        known_phonemes: Optional[List[str]],
        focus_phonemes: Optional[List[str]],
    ) -> bool:
        """
        Determine whether the two-pass quality review should run.
        
        Runs for:
          - V2 decodable mode (any GPC count) — strictest constraints
          - V2 instructional mode with ≤30 GPCs — still constrained
        
        Skips for:
          - V1 mode (no V2 fields)
          - Authentic mode (no constraints)
          - Instructional mode with >30 GPCs (enough vocabulary)
        """
        if not is_v2:
            return False

        effective_mode = vocabulary_mode or ('decodable' if strict_decodable else 'instructional')

        if effective_mode == 'decodable':
            return True

        if effective_mode == 'instructional':
            total_gpcs = len(known_phonemes or []) + len(focus_phonemes or [])
            return total_gpcs <= 30

        # authentic or unknown mode — skip
        return False

    async def _review_and_rewrite_story(
        self,
        story_text: str,
        num_scenes: int,
        known_phonemes: Optional[List[str]] = None,
        focus_phonemes: Optional[List[str]] = None,
        sight_words: Optional[List[str]] = None,
        vocabulary_mode: Optional[str] = None,
        strict_decodable: Optional[bool] = None,
        student_age: Optional[str] = None,
    ) -> str:
        """
        Second pass: feed the generated story to the LLM for quality review.
        The LLM rewrites any unnatural/forced sentences while keeping good ones.
        Falls back to original story_text if the review fails.

        The interest age has to be repeated here: without it this pass "simplifies"
        a correctly-pitched older story back into nursery content.
        """
        try:
            logger.info("Running two-pass quality review on generated story")

            # Build decodability constraints for the review prompt
            decodability_constraints = self._build_review_decodability_constraints(
                known_phonemes=known_phonemes,
                focus_phonemes=focus_phonemes,
                sight_words=sight_words,
                vocabulary_mode=vocabulary_mode,
                strict_decodable=strict_decodable,
            )

            # Build example of expected output format
            title_and_scenes_example = (
                "Example format (for a 4-scene story):\n"
                "The Big Red Balloon|||Sam found a big red balloon."
                "---The balloon flew up into the sky."
                "---Sam chased it over the hill."
                "---He caught it just in time!"
            )

            interest_cfg = get_interest_age_config(student_age)
            interest_age_constraints = build_interest_age_block(
                student_age,
                scope_note=(
                    "\n**SCOPE:** Keep the story at this interest age. Rewriting for naturalness "
                    "must never drag the themes, character ages, or tone younger."
                ),
            )

            review_prompt = STORY_QUALITY_REVIEW_PROMPT.format(
                story_text=story_text,
                scene_count=num_scenes,
                decodability_constraints=decodability_constraints,
                title_and_scenes_example=title_and_scenes_example,
                reviewer_persona=interest_cfg["reviewer_persona"],
                reader_descriptor=interest_cfg["reader_descriptor"],
                article=interest_cfg["article"],
                author_test=interest_cfg["author_test"],
                interest_age_constraints=interest_age_constraints,
            )

            reviewed_text = await ai_config.generate_with_gemini(review_prompt)

            # Validate the reviewed text has the expected format
            reviewed_text = reviewed_text.replace("`", "").replace("*", "")
            if "|||" not in reviewed_text:
                logger.warning("Quality review returned invalid format (no |||), using original")
                return story_text

            parts = reviewed_text.split("|||")
            if len(parts) != 2:
                logger.warning("Quality review returned invalid format (bad split), using original")
                return story_text

            scenes = [s.strip() for s in parts[1].split("---") if s.strip()]
            if len(scenes) < num_scenes - 2:  # Allow small tolerance
                logger.warning(
                    f"Quality review returned too few scenes ({len(scenes)} vs {num_scenes}), using original"
                )
                return story_text

            logger.info(f"Quality review completed successfully ({len(scenes)} scenes)")
            return reviewed_text

        except Exception as e:
            logger.warning(f"Quality review failed, using original story: {str(e)}")
            return story_text

    @staticmethod
    def _build_review_decodability_constraints(
        known_phonemes: Optional[List[str]] = None,
        focus_phonemes: Optional[List[str]] = None,
        sight_words: Optional[List[str]] = None,
        vocabulary_mode: Optional[str] = None,
        strict_decodable: Optional[bool] = None,
    ) -> str:
        """
        Build a concise decodability constraint block for the quality review prompt.
        This is simpler than the full V2 block — just the key constraints the reviewer needs.
        """
        effective_mode = vocabulary_mode or ('decodable' if strict_decodable else 'instructional')
        total_gpcs = len(known_phonemes or []) + len(focus_phonemes or [])
        parts = []

        if effective_mode == 'decodable':
            parts.append("### DECODABILITY CONSTRAINTS (must maintain while rewriting)")
            if known_phonemes:
                parts.append(f"Known GPCs: [{', '.join(known_phonemes)}]")
            if focus_phonemes:
                parts.append(f"Focus GPCs: [{', '.join(focus_phonemes)}]")
            parts.append(
                "• Every content word must be decodable using ONLY these GPCs."
            )
            if total_gpcs <= 20:
                parts.append(
                    "• You may freely use function words (the, a, is, he, she, it, can, and, "
                    "but, in, on, at, to, for, with, etc.) as automatic sight words."
                )
        elif effective_mode == 'instructional':
            parts.append("### VOCABULARY CONSTRAINTS (must maintain while rewriting)")
            if known_phonemes:
                parts.append(f"Known GPCs: [{', '.join(known_phonemes)}]")
            if focus_phonemes:
                parts.append(f"Focus GPCs: [{', '.join(focus_phonemes)}]")
            parts.append(
                "• Aim for ~80-90% of words to be decodable using these GPCs.\n"
                "• You may introduce a small number of age-appropriate words beyond the GPC sets."
            )

        if sight_words:
            parts.append(f"Allowed sight words: [{', '.join(sight_words)}]")

        if not parts:
            return "(No specific decodability constraints — focus on naturalness and quality.)"

        return "\n".join(parts)

    async def generate_scene_image_prompts(
        self, story_idea: str, short_scenes: List[str], cover_image_prompt: str,
        illustration_style: Optional[str] = None,
        student_age: Optional[str] = None,
    ) -> List[str]:
        """
        Generate detailed scene descriptions based on short scenes.
        These detailed descriptions will be used for image generation.
        Processes scenes in batches of 4 for efficiency when there are more than 4 scenes.
        Uses parallel requests to OpenAI API.
        """
        try:
            logger.info(f"Generating detailed scene prompts")

            # Get the style-aware instruction for Gemini
            from app.phonics_maker.image_generation.image_service import ImageService
            style_instruction = ImageService().get_style_gemini_instruction(illustration_style)
            interest_cfg = get_interest_age_config(student_age)

            detailed_scene_list = []
            tasks = []

            # Create a task for each batch
            for scene_idx, scene in enumerate(short_scenes):
                formatted_prompt = DETAILED_SCENE_GENERATION_PROMPT.format(
                    story_idea=story_idea,
                    all_short_scenes="---".join(
                        [f"{i+1}.{scn}" for i, scn in enumerate(short_scenes)]
                    ),
                    cover_page_prompt=cover_image_prompt,
                    scene_number=scene_idx + 1,
                    scene=scene,
                    illustration_style_instruction=style_instruction,
                    image_audience=interest_cfg["image_audience"],
                    image_clothing=interest_cfg["image_clothing"],
                    build_descriptors=interest_cfg["build_descriptors"],
                )

                tasks.append(ai_config.image_prompt_generate_with_gemini(formatted_prompt))

            # Execute all tasks in parallel — return_exceptions=True so one
            # rejected scene doesn't crash the entire book generation.
            detailed_scene_list = await asyncio.gather(*tasks, return_exceptions=True)

            # ── Retry content-blocked scenes with minimal prompt ──────────
            # The full prompt includes all_short_scenes (all 20 scene texts
            # concatenated), which is the #1 trigger for Gemini's
            # PROHIBITED_CONTENT filter. When scenes are blocked, retry with
            # a minimal prompt that omits the bulk story text.
            content_blocked_indices = [
                i for i, r in enumerate(detailed_scene_list)
                if isinstance(r, GeminiContentRejectedError)
            ]
            if content_blocked_indices:
                logger.info(
                    f"Retrying {len(content_blocked_indices)} content-blocked scenes "
                    f"with minimal prompt (no all_short_scenes)..."
                )
                retry_tasks = []
                for idx in content_blocked_indices:
                    scene = short_scenes[idx] if idx < len(short_scenes) else "Scene with characters"
                    minimal_prompt = DETAILED_SCENE_GENERATION_PROMPT_MINIMAL.format(
                        story_idea=story_idea,
                        cover_page_prompt=cover_image_prompt,
                        scene_number=idx + 1,
                        scene=scene,
                        illustration_style_instruction=style_instruction,
                        image_audience=interest_cfg["image_audience"],
                        build_descriptors=interest_cfg["build_descriptors"],
                    )
                    retry_tasks.append(ai_config.image_prompt_generate_with_gemini(minimal_prompt))

                retry_results = await asyncio.gather(*retry_tasks, return_exceptions=True)
                for j, idx in enumerate(content_blocked_indices):
                    detailed_scene_list[idx] = retry_results[j]

                recovered = sum(1 for r in retry_results if not isinstance(r, BaseException))
                logger.info(
                    f"Minimal-prompt retry recovered {recovered}/{len(content_blocked_indices)} scenes."
                )

            # Determine correct fallback style keyword
            fallback_style_keyword = "Cartoonish" if not illustration_style else (
                ImageService.STYLE_PROMPT_FRAGMENTS.get(illustration_style, "Cartoonish").split(".")[0]
            )

            # Validate and fix scene prompts — replace failures with safe fallbacks
            validated_scenes = []
            for i, scene_prompt in enumerate(detailed_scene_list):
                scene_text = (
                    short_scenes[i]
                    if i < len(short_scenes)
                    else "Scene with characters"
                )

                # Handle exceptions returned by gather(return_exceptions=True)
                if isinstance(scene_prompt, BaseException):
                    logger.warning(
                        f"Scene {i+1} image prompt generation failed ({type(scene_prompt).__name__}: {scene_prompt}). Using fallback."
                    )
                    fallback_prompt = (
                        f"{fallback_style_keyword} children's storybook illustration. "
                        f"Medium shot, full body view. {scene_text} "
                        f"The scene features the same characters and style as in: {cover_image_prompt[:200]}... "
                        f"No text, no letters, no words, completely text-free."
                    )
                    validated_scenes.append(fallback_prompt)
                elif not scene_prompt or len(str(scene_prompt).strip()) < 2:
                    logger.warning(
                        f"Scene {i+1} prompt is invalid or too short. Using fallback."
                    )
                    fallback_prompt = (
                        f"{fallback_style_keyword} children's storybook illustration. "
                        f"Medium shot, full body view. {scene_text} "
                        f"The scene features the same characters and style as in: {cover_image_prompt[:200]}... "
                        f"No text, no letters, no words, completely text-free."
                    )
                    validated_scenes.append(fallback_prompt)
                else:
                    validated_scenes.append(scene_prompt)

            # Safety net: ensure every scene prompt ends with the anti-text suffix
            anti_text_suffix = "Absolutely no text, no letters, no words, no numbers, no writing, no titles, no labels, completely text-free illustration only."
            for i, prompt in enumerate(validated_scenes):
                if anti_text_suffix.lower() not in prompt.lower():
                    # Strip any partial/weaker suffix the LLM may have added
                    cleaned = re.sub(
                        r'\s*No text[^.]*text-free[^.]*\.?\s*$',
                        '',
                        prompt,
                        flags=re.IGNORECASE,
                    ).strip()
                    validated_scenes[i] = f"{cleaned} {anti_text_suffix}"

            fallback_count = sum(1 for s in detailed_scene_list if isinstance(s, BaseException))
            logger.info(
                f"Generated {len(validated_scenes)} valid detailed scene prompts "
                f"({fallback_count} used fallback)."
            )
            return validated_scenes

        except Exception as e:
            logger.error(f"Error generating detailed scenes: {str(e)}")
            raise e

    def clean_story_title(self, title: str) -> str:
        """
        Clean the story title by removing unwanted symbols and extra whitespace.

        Args:
            title (str): The raw story title

        Returns:
            str: Cleaned title with unwanted symbols removed
        """
        unwanted_chars = r"[\"\\\/]"

        cleaned_title = re.sub(unwanted_chars, "", title)

        cleaned_title = cleaned_title.replace("‘", "'").replace("’", "'")

        cleaned_title = " ".join(cleaned_title.split())

        return cleaned_title

    # ── Series context for book sets ───────────────────────────────────

    @staticmethod
    def _build_series_context_block(
        book_title: Optional[str] = None,
        series_characters: Optional[list] = None,
        series_theme: Optional[str] = None,
        series_info: Optional[dict] = None,
    ) -> Optional[str]:
        """
        Build a prompt block that gives the LLM context about the book series.
        This ensures recurring characters, a shared world, and connected stories.
        Returns None if no series context is available.
        """
        parts = []

        if not any([book_title, series_characters, series_theme, series_info]):
            return None

        parts.append("### 📚 BOOK SERIES CONTEXT")
        parts.append("This book is part of a CONNECTED SERIES. Follow these rules carefully:\n")

        # Series position
        if series_info:
            pos = series_info.get('book_position')
            total = series_info.get('total_books')
            series_name = series_info.get('series_name')
            if series_name:
                parts.append(f"**SERIES NAME:** {series_name}")
            if pos and total:
                parts.append(f"**BOOK POSITION:** Book {pos} of {total}\n")

        # Book title
        if book_title:
            parts.append(
                f"**REQUIRED TITLE:** {book_title}\n"
                "• You MUST use this exact title for the story (output it before the ||| separator).\n"
                "• The story should match this title — build the plot around it.\n"
            )

        # Series theme/world
        if series_theme:
            parts.append(
                f"**SERIES WORLD/THEME:** {series_theme}\n"
                "• Set this story within this overarching world/theme.\n"
                "• The story should feel like it belongs in the same universe as the other books.\n"
            )

        # Recurring characters
        if series_characters and len(series_characters) > 0:
            parts.append("**RECURRING CHARACTERS** (use these EXACT characters with CONSISTENT visual descriptions):\n")
            for i, char in enumerate(series_characters):
                name = char.get('name', f'Character {i+1}')
                role = char.get('role', '')
                appearance = char.get('appearance', '')
                personality = char.get('personality', '')
                char_parts = [f"  **{name}**"]
                if role:
                    char_parts.append(f"  - Role: {role}")
                if appearance:
                    char_parts.append(f"  - Appearance: {appearance}")
                if personality:
                    char_parts.append(f"  - Personality: {personality}")
                parts.append("\n".join(char_parts))

            parts.append(
                "\n**CHARACTER CONSISTENCY RULES:**\n"
                "• Use the SAME character names and personalities across all books.\n"
                "• Characters should behave consistently — their personality traits stay the same.\n"
                "• The main character(s) should appear in EVERY scene or most scenes.\n"
                "• New minor characters can appear, but the recurring cast must be present.\n"
            )

        parts.append(
            "**SERIES CONNECTIVITY:**\n"
            "• Each book should tell a COMPLETE, standalone story (with a beginning, middle, and end).\n"
            "• But the stories should feel connected — same characters, same world, same tone.\n"
            "• Refer to shared locations or elements from the series theme.\n"
            "• The story should feel like the next episode in an ongoing adventure.\n"
        )

        return "\n".join(parts)

    # ── Story type prompt modifiers ────────────────────────────────────
    STORY_TYPE_PROMPTS = {
        "rhyming_poem": (
            "IMPORTANT FORMAT OVERRIDE — RHYMING POEM:\n"
            "Rewrite the story as a RHYMING POEM while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Each scene is ONE rhyming sentence or a two-line rhyming couplet (both count as one scene).\n"
            "• Rhymes must land on the FINAL word of each line. Use true rhymes (cat/hat), not near-rhymes (cat/cap).\n"
            "• Maintain a consistent bouncy RHYTHM — aim for a regular beat pattern (stressed/unstressed) throughout. "
            "Read each line aloud mentally to check it flows.\n"
            "• Pair scenes so consecutive scenes rhyme with each other: scene 1 rhymes with scene 2, scene 3 rhymes with scene 4, etc.\n"
            "• Think Julia Donaldson (The Gruffalo) or Dr. Seuss — playful, musical, and satisfying to read aloud.\n"
            "• The phoneme target words should appear naturally within the rhyming lines — never sacrifice a good rhyme to force a phoneme word in.\n"
            "• The title should sound poetic or playful, not like a prose story title."
        ),
        "non_fiction": (
            "IMPORTANT FORMAT OVERRIDE — NON-FICTION FACT BOOK:\n"
            "Rewrite as a NON-FICTION INFORMATION BOOK while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Each scene is ONE factual sentence presenting a TRUE, age-appropriate fact about the topic.\n"
            "• Every fact must be REAL and ACCURATE — never invent false information. If the story idea is fictional "
            "(e.g., \"dragons\"), pivot to a real-world related topic (e.g., lizards, komodo dragons).\n"
            "• Vary the sentence openers to keep it engaging: \"Did you know…\", \"A ___ can…\", \"The biggest…\", "
            "\"Unlike most animals,…\", \"Every year,…\" — avoid starting more than two scenes the same way.\n"
            "• Build a logical sequence: introduce the topic → describe appearance/features → behaviour → habitat → "
            "surprising facts → conclusion/call-to-action.\n"
            "• Use vivid, specific details children will remember (numbers, comparisons, sensory details): "
            "\"A blue whale's heart is as big as a small car\" is better than \"Blue whales are very big.\"\n"
            "• Phoneme words should appear naturally within the facts — scientific and descriptive vocabulary is rich in phoneme opportunities.\n"
            "• The title should sound like a real non-fiction book title (e.g., \"All About Sharks\" or \"Amazing Minibeasts\")."
        ),
        "pattern_book": (
            "IMPORTANT FORMAT OVERRIDE — PATTERN BOOK:\n"
            "Rewrite as a PATTERN BOOK with highly REPETITIVE structure while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Choose ONE simple sentence frame and use it for EVERY scene, changing only 1-2 key words each time. Examples:\n"
            "  - \"I can see a ___ in the ___.\"\n"
            "  - \"The ___ is ___.\"\n"
            "  - \"___ likes to ___.\"\n"
            "  - \"Look! A ___ can ___.\"\n"
            "• The sentence frame MUST stay identical across all scenes — only the blanks change. This predictability is "
            "the entire point: children can \"read\" the repeated words independently and only decode the new word.\n"
            "• The changing words MUST feature the target phonemes — this is where the phonics learning happens.\n"
            "• Build a gentle progression: start with the simplest/most familiar words and gradually introduce less common ones.\n"
            "• The FINAL scene (only) may break the pattern slightly for a satisfying ending "
            "(e.g., after 9 scenes of \"I can see a ___\", end with \"I can see them all!\").\n"
            "• The title should hint at the pattern (e.g., \"I Can See!\" or \"What Can ___ Do?\")."
        ),
        "dialogue": (
            "IMPORTANT FORMAT OVERRIDE — DIALOGUE STORY:\n"
            "Rewrite as a DIALOGUE-RICH STORY while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Each scene is ONE sentence that contains direct speech with proper punctuation.\n"
            "• Format speech correctly: \"Let's go to the pond!\" said Frog. OR Frog said, \"Let's go to the pond!\"\n"
            "• Vary speech verbs throughout the book — use: said, asked, shouted, whispered, called, giggled, cried, replied, "
            "wondered, cheered. Never use \"said\" more than 3 times in the whole book.\n"
            "• Use 2-3 named characters maximum and make their voices distinct — one might be bold and excitable, another cautious and thoughtful.\n"
            "• Alternate between characters speaking so it reads like a real conversation that tells a story.\n"
            "• Some scenes (2-3 max) may have brief narration instead of speech to set the scene or describe action, "
            "but the majority MUST be dialogue.\n"
            "• Phoneme target words should appear naturally in what characters say or in the speech attribution.\n"
            "• The story should still have a clear beginning → middle → end, told through what the characters say to each other."
        ),
        "procedural": (
            "IMPORTANT FORMAT OVERRIDE — HOW-TO GUIDE:\n"
            "Rewrite as a FUN PROCEDURAL \"HOW-TO\" BOOK while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Invent a creative, imaginative procedure based on the story idea — \"How to Catch a Star\", "
            "\"How to Grow a Rainbow\", \"How to Train a Pet Dragon\", \"How to Build the Best Sandcastle\".\n"
            "• Each scene is ONE instructional sentence — a single step in the procedure.\n"
            "• Use IMPERATIVE verbs (commands): \"Find\", \"Mix\", \"Put\", \"Wait\", \"Watch\", \"Sprinkle\", \"Squeeze\", \"Shake\".\n"
            "• Begin each scene with a sequence marker that progresses naturally:\n"
            "  - Scenes 1-2: \"First,…\" / \"Next,…\"\n"
            "  - Middle scenes: \"Then,…\" / \"Now,…\" / \"After that,…\" / \"Carefully,…\" / \"Gently,…\" / \"Quickly,…\"\n"
            "  - Final scene: \"Finally,…\" or \"At last,…\"\n"
            "• The instructions should escalate in excitement or silliness — start simple and get more creative/funny as the procedure continues.\n"
            "• Phoneme target words should appear naturally in the instruction vocabulary (verbs and objects are rich in phonemes).\n"
            "• The title MUST be a \"How to…\" title (e.g., \"How to Catch a Cloud\")."
        ),
        "alliterative": (
            "IMPORTANT FORMAT OVERRIDE — ALLITERATIVE STORY:\n"
            "Rewrite as an ALLITERATIVE SOUND-SPOTLIGHT STORY while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• The target phonemes are your primary alliterative sounds. Pack EVERY scene with as many words "
            "containing the target phoneme(s) as possible.\n"
            "• Aim for 3-5+ words per scene that feature the target sound — the more the better, as long as the sentence still makes sense.\n"
            "• Alliteration priority: words STARTING with the target sound > words CONTAINING the target sound > words near-rhyming with it.\n"
            "• Each scene should read like a fun tongue-twister: \"Six slippery snakes slid sideways\" "
            "or \"Pete the pilot picked a perfect peach\".\n"
            "• The story must still follow a clear narrative arc (beginning → middle → end) — alliteration is the style, "
            "not a substitute for plot.\n"
            "• Character names should START with the target phoneme sound (e.g., for /sh/: Shelley, Shane; for /ch/: Charlie, Chester).\n"
            "• The title should be alliterative too (e.g., \"Silly Snake's Slippery Saturday\").\n"
            "• If multiple phonemes are targeted, alternate which phoneme each scene spotlights, but feature all of them across the book."
        ),
        "social_story": (
            "IMPORTANT FORMAT OVERRIDE — SOCIAL STORY:\n"
            "Rewrite as a SOCIAL STORY while keeping the same title|||scene1---scene2--- output format.\n"
            "RULES:\n"
            "• Each scene is ONE short, direct sentence describing the social situation, the expected behaviour, "
            "or why that behaviour matters.\n"
            "• Use POSITIVE framing throughout — describe what TO do, never what NOT to do. "
            "\"I use calm hands\" not \"I do not hit.\"\n"
            "• Write in first person (\"I\", \"we\") or consistent third person — never mix the two.\n"
            "• Use CONCRETE, literal language — no idioms, sarcasm, or figurative speech. "
            "Every sentence should mean exactly what it says.\n"
            "• Build a clear sequence: introduce the setting/situation → describe the feelings involved "
            "→ state the expected behaviour → describe the positive outcome.\n"
            "• Use gentle REPETITION across scenes to reinforce the key behaviour — the main message should "
            "appear in different words 2-3 times across the book.\n"
            "• Keep vocabulary simple and AAC-friendly — prefer high-frequency words that students can point to "
            "or use in a communication device.\n"
            "• Phoneme target words should be woven in naturally throughout the sentences.\n"
            "• The title should clearly name the target behaviour or routine "
            "(e.g., \"Using Safe Hands\" or \"My Morning Routine\")."
        ),
    }

    def _get_story_type_prompt_fragment(self, story_type: Optional[str]) -> Optional[str]:
        """Return extra prompt text for non-default story types, or None."""
        if not story_type or story_type == "narrative":
            return None
        return self.STORY_TYPE_PROMPTS.get(story_type)

    def _parse_story_scenes_and_title(self, story_text: str, is_free: bool, num_scenes: int = 20) -> dict:
        """
        Parse the generated story text into a dictionary containing the title and list of scenes.

        Args:
            story_text (str): The generated story text in format "(title|||scene1---scene2---...)".

        Returns:
            dict: A dictionary with 'title' and 'scenes' keys.
        """
        # Remove ** `` from story text
        story_text = story_text.replace("`", "").replace("*", "")

        # Normalise smart/curly quotes to straight ASCII equivalents
        story_text = story_text.replace("\u2018", "'").replace("\u2019", "'")
        story_text = story_text.replace("\u201c", '"').replace("\u201d", '"')

        # Split title and scenes
        parts = story_text.split("|||")
        if len(parts) != 2:
            logger.error(f"Failed to parse story: no '|||' separator found. Raw response (first 500 chars): {story_text[:500]}")
            raise ValueError("Story format invalid: missing '|||' separator between title and scenes. Retrying...")

        title = parts[0].strip()
        scene_texts = parts[1].split("---")

        scenes = []
        for text in scene_texts:
            text = text.strip()
            if text:  # Skip empty scenes
                scenes.append(text)

        logger.info(f"Parsed {len(scenes)} scenes from story response.")

        if len(title) > 100:
            raise ValueError("Title is too long.")
        elif len(title) < 5:
            raise ValueError("Title is too short.")

        if is_free and len(scenes) > 10:
            raise ValueError("Too many scenes generated.")
        elif is_free and len(scenes) < 6:
            raise ValueError(f"Not enough scenes generated ({len(scenes)} < 6). Retrying...")

        if not is_free:
            min_ok = max(4, num_scenes - 3)
            max_ok = num_scenes + 4
            if len(scenes) < min_ok:
                raise ValueError(f"Not enough scenes generated ({len(scenes)} < {min_ok}). Retrying...")
            if len(scenes) > max_ok:
                raise ValueError("Too many scenes generated.")
        return {"title": title, "scenes": scenes}
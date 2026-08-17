# phonics_maker/activity_generation/activity_service.py
"""
Activity Generation Service

Generates educational phonics activities from story content.
Extracts target phoneme words, creates distractors, and builds
structured activity data for template rendering.
"""

import re
import json
import random
from typing import List, Dict, Tuple, Optional
from app.core.config.logger import logger
from app.core.ai.ai_config import AIConfig
from app.phonics_maker.activity_generation.activity_types import (
    ActivityType,
    ActivityConfig,
    WordHuntActivity,
    SoundMatchingActivity,
    FillInTheBlankActivity,
    TracingActivity,
    CircleSoundActivity,
    WordScrambleActivity,
    CutAndSortActivity,
    SentenceBuildingActivity,
    PhonemeSpotterActivity,
    RhymingPairsActivity,
    PhonemePositionActivity,
    SoundSwapActivity,
    SyllableCountActivity,
    WordLadderActivity,
    ReadAndDrawActivity,
    PhonemeCountActivity,
    OddOneOutActivity,
    MissingSoundActivity,
    RealOrNonsenseActivity,
    WordBuildingActivity,
    CrosswordActivity,
    ComprehensionQuestionsActivity,
    VocabularyBuildingActivity,
    SynonymsActivity,
    InferredMeaningActivity,
    AnswerKeyData,
)


class ActivityService:
    """
    Service for generating phonics activities from story content.
    
    Extracts words containing target phonemes from the story text,
    generates appropriate distractors, and creates structured data
    for each activity type.
    """
    
    # Common distractor words that don't contain common digraphs
    # These are simple, decodable words safe for early readers
    DISTRACTOR_POOL = [
        "cat", "dog", "run", "big", "red", "sun", "hat", "map", 
        "pen", "bed", "cup", "pot", "leg", "top", "sit", "let",
        "hop", "win", "mud", "fan", "rug", "wet", "fix", "box",
        "jam", "zip", "van", "yak", "web", "mix", "job", "tub",
        "pin", "net", "rat", "lip", "hug", "get", "kid", "log",
    ]
    
    # Simple hints for common words (used by word scramble)
    WORD_HINTS = {
        # Common animals/objects
        "ship": "It sails on water",
        "fish": "It swims in the sea",
        "shop": "You buy things here",
        "sheep": "A fluffy farm animal",
        "shell": "Found on the beach",
        "shoe": "You wear it on your foot",
        "shed": "A small building in a garden",
        "shin": "Part of your leg",
        "shut": "Close it",
        "shout": "A loud voice",
        "chair": "You sit on it",
        "chin": "Below your mouth",
        "chest": "A box for treasure",
        "chat": "Talk to a friend",
        "chop": "Cut with a knife",
        "chip": "A snack you eat",
        "chick": "A baby bird",
        "chain": "Made of metal links",
        "think": "Use your brain",
        "thick": "Not thin",
        "thin": "Not thick",
        "three": "A number after two",
        "them": "Those people",
        "then": "After that",
        "this": "Right here",
        "that": "Over there",
        "thing": "An object",
        "whip": "Crack it!",
        "wheel": "Round and round",
        "when": "At what time?",
        "ring": "Goes on your finger",
        "king": "Wears a crown",
        "sing": "Make music with your voice",
        "long": "Not short",
        "bang": "A loud noise",
        "song": "Something you sing",
        "tree": "It has leaves",
        "free": "No cost",
        "seed": "Plant it to grow",
        "feed": "Give food to",
        "feet": "At the end of your legs",
        "deep": "Very far down",
        "keep": "Don't let go",
        "rain": "Water from clouds",
        "train": "Rides on tracks",
        "tail": "An animal has one",
        "sail": "On a boat",
        "mail": "Letters and parcels",
        "road": "Cars drive on it",
        "boat": "Floats on water",
        "goat": "A farm animal",
        "coat": "Keeps you warm",
        "moon": "Shines at night",
        "soon": "Not long from now",
        "food": "You eat it",
        "look": "Use your eyes",
        "book": "You read it",
        "cook": "Make a meal",
        "took": "Past tense of take",
        "hook": "Catch a fish with it",
        "star": "Shines in the sky",
        "car": "You drive it",
        "jar": "Holds jam",
        "far": "A great distance",
        "park": "Play outside here",
        "dark": "No light",
        "barn": "Animals sleep here",
    }
    
    # Phoneme patterns for detection (case-insensitive regex patterns)
    PHONEME_PATTERNS = {
        # Consonant Digraphs
        "sh": r"sh",
        "ch": r"ch", 
        "th": r"th",
        "wh": r"wh",
        "ph": r"ph",
        "ck": r"ck",
        "ng": r"ng",
        "qu": r"qu",
        
        # Vowel Digraphs / Teams
        "ee": r"ee",
        "ea": r"ea",
        "ai": r"ai",
        "ay": r"ay",
        "oa": r"oa",
        "ow": r"ow",
        "oo": r"oo",
        "ou": r"ou",
        "oi": r"oi",
        "oy": r"oy",
        "aw": r"aw",
        "au": r"au",
        "ew": r"ew",
        "ie": r"ie",
        "igh": r"igh",
        
        # R-Controlled Vowels
        "ar": r"ar",
        "er": r"er",
        "ir": r"ir",
        "or": r"or",
        "ur": r"ur",
        
        # Single consonants (for early levels)
        "s": r"^s|s$|s(?![h])",  # 's' not followed by 'h'
        "a": r"a(?![iyuw])",  # 'a' not part of digraph
        "t": r"t(?![h])",  # 't' not followed by 'h'
        "p": r"p(?![h])",  # 'p' not followed by 'h'
        "n": r"n(?![g])",  # 'n' not followed by 'g'
        "m": r"m",
        "d": r"d",
        "g": r"g",
        "c": r"c(?![h])",  # 'c' not followed by 'h'
        "k": r"k",
        "b": r"b",
        "f": r"f",
        "l": r"l",
        "r": r"r",
        "h": r"h",
        "j": r"j",
        "v": r"v",
        "w": r"w(?![h])",  # 'w' not followed by 'h'
        "x": r"x",
        "y": r"y",
        "z": r"z",
    }

    def __init__(self):
        pass
    
    def extract_words_from_scenes(self, scenes: List[str]) -> List[str]:
        """
        Extract all unique words from story scenes.
        
        Args:
            scenes: List of scene text strings
            
        Returns:
            List of unique words (lowercase, alphabetic only)
        """
        all_text = " ".join(scenes)
        # Extract words (letters only, no punctuation)
        words = re.findall(r"\b[a-zA-Z]+\b", all_text.lower())
        # Remove duplicates while preserving order
        seen = set()
        unique_words = []
        for word in words:
            if word not in seen and len(word) >= 2:  # Min 2 chars
                seen.add(word)
                unique_words.append(word)
        return unique_words
    
    def word_contains_phoneme(self, word: str, phoneme: str) -> bool:
        """
        Check if a word contains the given phoneme.
        
        Args:
            word: The word to check (lowercase)
            phoneme: The phoneme to search for
            
        Returns:
            True if word contains the phoneme
        """
        # Strip hyphens from phoneme (e.g. 'tele-' → 'tele', 'dis-' → 'dis')
        # so prefix/suffix phonemes match words like 'telephone', 'discover'
        phoneme_lower = phoneme.lower().strip("-")
        word_lower = word.lower()
        
        # Get the pattern for this phoneme, or use simple substring match
        pattern = self.PHONEME_PATTERNS.get(phoneme_lower, phoneme_lower)
        
        try:
            return bool(re.search(pattern, word_lower, re.IGNORECASE))
        except re.error:
            # Fallback to simple substring match
            return phoneme_lower in word_lower
    
    def find_phoneme_words(
        self, 
        words: List[str], 
        phonemes: List[str]
    ) -> Dict[str, List[str]]:
        """
        Find words containing each target phoneme.
        
        Args:
            words: List of words to search
            phonemes: List of target phonemes
            
        Returns:
            Dict mapping phoneme -> list of words containing it
        """
        phoneme_words = {p.upper(): [] for p in phonemes}
        
        for word in words:
            for phoneme in phonemes:
                if self.word_contains_phoneme(word, phoneme):
                    phoneme_words[phoneme.upper()].append(word)
                    break  # Each word only counted once
        
        return phoneme_words
    
    def get_distractors(
        self, 
        count: int, 
        phonemes: List[str], 
        exclude_words: List[str]
    ) -> List[str]:
        """
        Get distractor words that don't contain target phonemes.
        
        Args:
            count: Number of distractors needed
            phonemes: Phonemes to avoid
            exclude_words: Words to exclude (already used)
            
        Returns:
            List of distractor words
        """
        candidates = []
        exclude_set = set(w.lower() for w in exclude_words)
        
        for word in self.DISTRACTOR_POOL:
            if word.lower() in exclude_set:
                continue
            
            # Check word doesn't contain any target phonemes
            contains_phoneme = False
            for phoneme in phonemes:
                if self.word_contains_phoneme(word, phoneme):
                    contains_phoneme = True
                    break
            
            if not contains_phoneme:
                candidates.append(word)
        
        # Shuffle and take what we need
        random.shuffle(candidates)
        return candidates[:count]
    
    def _get_hint_for_word(self, word: str) -> str:
        """Get a hint for a word, falling back to a generic hint."""
        hint = self.WORD_HINTS.get(word.lower())
        if hint:
            return hint
        
        # Generate a generic hint based on word length
        length = len(word)
        generic_hints = [
            f"This word has {length} letters",
            f"A {length}-letter word",
            f"Can you spell this {length}-letter word?",
            f"Rearrange all {length} letters",
        ]
        return random.choice(generic_hints)
    
    def _scramble_word(self, word: str) -> List[str]:
        """Scramble the letters of a word, ensuring it differs from original."""
        letters = list(word.lower())
        for _ in range(20):  # Try up to 20 times to get a different arrangement
            random.shuffle(letters)
            if "".join(letters) != word.lower():
                return letters
        return letters  # Fallback (short words like "at" may not scramble well)
    
    def generate_word_hunt(
        self, 
        scenes: List[str], 
        phonemes: List[str],
        target_word_count: int = 6,
        distractor_count: int = 4,
    ) -> WordHuntActivity:
        """
        Generate a Word Hunt activity.
        
        Students identify words containing the target phoneme(s).
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            target_word_count: Max correct answers to include
            distractor_count: Number of wrong answers to include
            
        Returns:
            WordHuntActivity with structured data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Collect story words containing phonemes
        story_words = []
        for phoneme, words in phoneme_words.items():
            story_words.extend(words)
        
        # Remove duplicates and limit
        story_words = list(dict.fromkeys(story_words))[:target_word_count]
        
        # Get distractors
        distractors = self.get_distractors(distractor_count, phonemes, story_words)
        
        # Combine and shuffle
        all_activity_words = story_words + distractors
        random.shuffle(all_activity_words)
        
        return WordHuntActivity(
            phonemes=[p.upper() for p in phonemes],
            story_words=story_words,
            distractor_words=distractors,
            all_words=all_activity_words,
            correct_count=len(story_words),
        )
    
    def generate_sound_matching(
        self, 
        scenes: List[str], 
        phonemes: List[str],
        pair_count: int = 6,
    ) -> Optional[SoundMatchingActivity]:
        """
        Generate a Sound Matching activity.
        
        Students match words to their phoneme sounds.
        Works best with 2+ phonemes.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes (ideally 2-3)
            pair_count: Number of word-phoneme pairs
            
        Returns:
            SoundMatchingActivity or None if not enough data
        """
        if len(phonemes) < 2:
            # Sound matching needs at least 2 phonemes to be meaningful
            logger.info("Sound matching skipped: need 2+ phonemes")
            return None
        
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Build pairs, trying to get equal representation
        pairs = []
        words_per_phoneme = max(1, pair_count // len(phonemes))
        
        for phoneme, words in phoneme_words.items():
            for word in words[:words_per_phoneme]:
                pairs.append({"word": word, "phoneme": phoneme})
        
        if len(pairs) < 3:
            logger.info(f"Sound matching skipped: only {len(pairs)} pairs found")
            return None
        
        # Shuffle pairs
        random.shuffle(pairs)
        pairs = pairs[:pair_count]
        
        return SoundMatchingActivity(
            phonemes=[p.upper() for p in phonemes],
            word_phoneme_pairs=pairs,
        )
    
    def generate_fill_in_blank(
        self, 
        scenes: List[str], 
        phonemes: List[str],
        sentence_count: int = 4,
    ) -> Optional[FillInTheBlankActivity]:
        """
        Generate a Fill in the Blank activity.
        
        Creates sentences with missing phonemes for students to complete.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            sentence_count: Number of sentences to generate
            
        Returns:
            FillInTheBlankActivity or None if not enough data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Flatten to list of (word, phoneme) tuples
        word_phoneme_list = []
        for phoneme, words in phoneme_words.items():
            for word in words:
                word_phoneme_list.append((word, phoneme.lower()))
        
        if len(word_phoneme_list) < 2:
            logger.info("Fill in blank skipped: not enough words")
            return None
        
        random.shuffle(word_phoneme_list)
        
        sentences = []
        for word, phoneme in word_phoneme_list[:sentence_count]:
            # Create blank by replacing phoneme with underscores
            blank_word = word.lower().replace(phoneme, "___")
            
            # Simple sentence templates
            templates = [
                f"Can you read the word: {blank_word}?",
                f"Fill in the missing sound: {blank_word}",
                f"What letters are missing? {blank_word}",
                f"Complete the word: {blank_word}",
            ]
            
            sentences.append({
                "sentence": random.choice(templates),
                "answer": phoneme.lower(),
                "full_word": word,
                "blank_word": blank_word,
            })
        
        if not sentences:
            return None
        
        return FillInTheBlankActivity(
            phonemes=[p.upper() for p in phonemes],
            sentences=sentences,
        )
    
    def generate_tracing(
        self, 
        scenes: List[str], 
        phonemes: List[str],
        word_count: int = 4,
    ) -> TracingActivity:
        """
        Generate a Tracing Practice activity.
        
        Provides phonemes and example words for handwriting practice.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            word_count: Number of example words
            
        Returns:
            TracingActivity with structured data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Collect example words
        example_words = []
        for phoneme, words in phoneme_words.items():
            example_words.extend(words[:2])  # Up to 2 per phoneme
        
        # Remove duplicates and limit
        example_words = list(dict.fromkeys(example_words))[:word_count]
        
        return TracingActivity(
            phonemes=[p.upper() for p in phonemes],
            example_words=example_words,
        )
    
    def generate_circle_sound(
        self,
        scenes: List[str],
        phonemes: List[str],
        target_word_count: int = 6,
        distractor_count: int = 6,
    ) -> CircleSoundActivity:
        """
        Generate a Circle the Sound activity.
        
        Students read words in bubble shapes and circle any that
        contain the target phoneme. Similar to Word Hunt but with
        a different visual layout (bubbles + counting).
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            target_word_count: Max correct answers
            distractor_count: Number of distractors
            
        Returns:
            CircleSoundActivity with structured data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Collect story words containing phonemes
        story_words = []
        for phoneme, words in phoneme_words.items():
            story_words.extend(words)
        
        story_words = list(dict.fromkeys(story_words))[:target_word_count]
        distractors = self.get_distractors(distractor_count, phonemes, story_words)
        
        all_activity_words = story_words + distractors
        random.shuffle(all_activity_words)
        
        return CircleSoundActivity(
            phonemes=[p.upper() for p in phonemes],
            story_words=story_words,
            distractor_words=distractors,
            all_words=all_activity_words,
            correct_count=len(story_words),
        )
    
    def generate_word_scramble(
        self,
        scenes: List[str],
        phonemes: List[str],
        word_count: int = 5,
    ) -> Optional[WordScrambleActivity]:
        """
        Generate a Word Scramble activity.
        
        Students unscramble jumbled letters to form words that
        contain the target phoneme.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            word_count: Number of scrambled words to include
            
        Returns:
            WordScrambleActivity or None if not enough data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Collect words, preferring 3-6 letter ones for good scrambling
        candidates = []
        for phoneme, words in phoneme_words.items():
            for word in words:
                if 3 <= len(word) <= 7:  # Good length for scrambling
                    candidates.append(word)
        
        candidates = list(dict.fromkeys(candidates))  # Remove duplicates
        
        if len(candidates) < 2:
            logger.info("Word scramble skipped: not enough suitable words")
            return None
        
        random.shuffle(candidates)
        selected = candidates[:word_count]
        
        scramble_words = []
        for word in selected:
            scrambled = self._scramble_word(word)
            hint = self._get_hint_for_word(word)
            scramble_words.append({
                "word": word,
                "scrambled_letters": scrambled,
                "hint": hint,
            })
        
        return WordScrambleActivity(
            phonemes=[p.upper() for p in phonemes],
            scramble_words=scramble_words,
        )
    
    def generate_cut_and_sort(
        self,
        scenes: List[str],
        phonemes: List[str],
        target_word_count: int = 5,
        distractor_count: int = 5,
    ) -> CutAndSortActivity:
        """
        Generate a Cut & Sort activity.
        
        Students sort words into two columns:
        - Column A: words that contain the phoneme
        - Column B: words that don't contain the phoneme
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            target_word_count: Number of correct words
            distractor_count: Number of distractor words
            
        Returns:
            CutAndSortActivity with structured data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        story_words = []
        for phoneme, words in phoneme_words.items():
            story_words.extend(words)
        
        story_words = list(dict.fromkeys(story_words))[:target_word_count]
        distractors = self.get_distractors(distractor_count, phonemes, story_words)
        
        all_activity_words = story_words + distractors
        random.shuffle(all_activity_words)
        
        total = len(all_activity_words)
        line_count = max(len(story_words), len(distractors), 5)
        
        return CutAndSortActivity(
            phonemes=[p.upper() for p in phonemes],
            story_words=story_words,
            distractor_words=distractors,
            all_words=all_activity_words,
            total_words=total,
            line_count=line_count,
        )
    
    def generate_sentence_building(
        self,
        scenes: List[str],
        phonemes: List[str],
        bank_size: int = 6,
        sentence_count: int = 3,
    ) -> Optional[SentenceBuildingActivity]:
        """
        Generate a Sentence Building activity.
        
        Provides a word bank of phoneme words. Students pick words
        and write their own sentences using them.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            bank_size: Number of words in the word bank
            sentence_count: Number of sentence prompts
            
        Returns:
            SentenceBuildingActivity or None if not enough data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Collect words for bank
        candidates = []
        for phoneme, words in phoneme_words.items():
            candidates.extend(words)
        
        candidates = list(dict.fromkeys(candidates))  # Remove duplicates
        
        if len(candidates) < 2:
            logger.info("Sentence building skipped: not enough words")
            return None
        
        random.shuffle(candidates)
        bank_words = candidates[:bank_size]
        
        # Pick a subset for the sentence prompts
        sentence_words = bank_words[:min(sentence_count, len(bank_words))]
        
        return SentenceBuildingActivity(
            phonemes=[p.upper() for p in phonemes],
            bank_words=bank_words,
            sentence_words=sentence_words,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # RHYME DICTIONARY - maps words to their rhyming counterparts
    # ═══════════════════════════════════════════════════════════════
    RHYME_MAP = {
        # sh words
        "ship": ["tip", "dip", "lip", "hip", "rip", "zip", "skip", "trip", "clip", "drip", "grip", "flip", "chip", "whip", "sip", "nip", "slip", "strip", "snip"],
        "shell": ["bell", "tell", "well", "sell", "fell", "spell", "smell", "dwell", "yell"],
        "shop": ["top", "hop", "pop", "stop", "drop", "mop", "cop", "crop", "chop", "flop", "plop"],
        "shed": ["bed", "red", "fed", "led", "said", "head", "bread", "sled", "thread"],
        "shin": ["bin", "pin", "tin", "win", "fin", "grin", "thin", "spin", "skin", "chin"],
        "shut": ["but", "cut", "gut", "hut", "nut", "put", "rut", "strut"],
        "shout": ["out", "about", "scout", "trout", "sprout", "pout", "snout"],
        "shade": ["made", "paid", "fade", "grade", "trade", "blade", "spade"],
        "shake": ["make", "lake", "cake", "bake", "take", "wake", "fake", "brake", "snake", "flake"],
        "share": ["care", "bare", "dare", "fair", "hair", "pair", "stare", "spare", "rare"],
        "shine": ["mine", "fine", "line", "nine", "pine", "vine", "wine", "dine", "spine"],
        "shore": ["more", "door", "four", "pour", "core", "bore", "store", "snore", "floor"],
        "show": ["go", "no", "so", "low", "row", "bow", "flow", "grow", "know", "blow", "snow", "slow", "glow"],
        "sheep": ["deep", "keep", "sleep", "creep", "sweep", "jeep", "peep", "steep", "weep", "beep"],
        "sheet": ["feet", "meet", "beat", "heat", "seat", "eat", "neat", "treat", "sweet", "street"],
        "shook": ["book", "cook", "look", "hook", "took", "brook", "nook", "crook"],
        "shoe": ["blue", "clue", "flew", "glue", "grew", "knew", "new", "true", "two", "who", "do", "too"],
        # ch words
        "chat": ["bat", "cat", "fat", "hat", "mat", "pat", "rat", "sat", "flat", "that", "brat"],
        "chip": ["dip", "hip", "lip", "rip", "sip", "tip", "zip", "drip", "grip", "skip", "slip", "trip", "whip", "ship", "strip", "flip"],
        "chin": ["bin", "fin", "grin", "pin", "sin", "tin", "win", "skin", "spin", "thin", "twin", "shin"],
        "chest": ["best", "nest", "rest", "test", "vest", "west", "quest", "guest", "pest", "zest"],
        "chop": ["cop", "drop", "hop", "mop", "pop", "stop", "top", "crop", "flop", "plop", "prop", "shop"],
        "chain": ["brain", "drain", "grain", "main", "pain", "plain", "rain", "train", "Spain", "strain"],
        "chair": ["air", "bear", "care", "dare", "fair", "hair", "pair", "stair", "wear", "share", "spare", "repair"],
        "chick": ["brick", "click", "flick", "kick", "lick", "nick", "pick", "quick", "sick", "stick", "thick", "trick", "wick"],
        "check": ["deck", "neck", "peck", "wreck", "speck", "trek"],
        "cheer": ["beer", "dear", "fear", "gear", "hear", "near", "peer", "rear", "steer", "year", "clear"],
        # th words
        "thin": ["bin", "chin", "fin", "grin", "pin", "tin", "win", "skin", "spin", "shin", "twin"],
        "think": ["blink", "drink", "ink", "link", "pink", "rink", "sink", "wink", "brink", "shrink", "stink"],
        "thing": ["bring", "king", "ring", "sing", "spring", "string", "swing", "wing", "sting", "cling", "fling"],
        "thick": ["brick", "chick", "click", "flick", "kick", "lick", "nick", "pick", "quick", "sick", "stick", "trick", "wick"],
        "three": ["bee", "fee", "free", "glee", "knee", "see", "tea", "tree", "we", "key", "flea", "pea"],
        # common single-consonant words
        "cat": ["bat", "fat", "hat", "mat", "pat", "rat", "sat", "chat", "flat", "that", "brat"],
        "dog": ["bog", "fog", "frog", "hog", "jog", "log", "cog"],
        "run": ["bun", "fun", "gun", "nun", "pun", "sun", "spun", "stun", "done", "won", "ton"],
        "big": ["dig", "fig", "jig", "pig", "rig", "wig", "twig"],
        "sun": ["bun", "fun", "gun", "nun", "pun", "run", "spun", "stun"],
        "hat": ["bat", "cat", "fat", "mat", "pat", "rat", "sat", "chat", "flat", "that"],
        "can": ["ban", "fan", "man", "pan", "ran", "tan", "van", "clan", "plan", "scan", "span"],
        "sit": ["bit", "fit", "hit", "kit", "lit", "pit", "wit", "grit", "knit", "quit", "skit", "slit", "spit", "split"],
        "red": ["bed", "fed", "led", "shed", "sled", "thread", "bread", "head", "said"],
        "pot": ["cot", "dot", "got", "hot", "lot", "not", "rot", "shot", "slot", "spot", "trot", "knot"],
        "top": ["cop", "drop", "hop", "mop", "pop", "shop", "stop", "chop", "crop", "flop", "plop"],
    }
    
    # ═══════════════════════════════════════════════════════════════
    # SOUND SWAP PAIRS - maps (original_word -> (new_word, old_sound, new_sound))
    # ═══════════════════════════════════════════════════════════════
    SOUND_SWAP_DB = {
        "sh": [
            {"original": "sip", "answer": "ship", "old_sound": "s", "new_sound": "sh"},
            {"original": "top", "answer": "shop", "old_sound": "t", "new_sound": "sh"},
            {"original": "bell", "answer": "shell", "old_sound": "b", "new_sound": "sh"},
            {"original": "fin", "answer": "shin", "old_sound": "f", "new_sound": "sh"},
            {"original": "led", "answer": "shed", "old_sound": "l", "new_sound": "sh"},
            {"original": "hut", "answer": "shut", "old_sound": "h", "new_sound": "sh"},
            {"original": "red", "answer": "shred", "old_sound": "r", "new_sound": "shr"},
            {"original": "mine", "answer": "shine", "old_sound": "m", "new_sound": "sh"},
            {"original": "cake", "answer": "shake", "old_sound": "c", "new_sound": "sh"},
            {"original": "deep", "answer": "sheep", "old_sound": "d", "new_sound": "sh"},
            {"original": "more", "answer": "shore", "old_sound": "m", "new_sound": "sh"},
            {"original": "bow", "answer": "show", "old_sound": "b", "new_sound": "sh"},
        ],
        "ch": [
            {"original": "bat", "answer": "chat", "old_sound": "b", "new_sound": "ch"},
            {"original": "hair", "answer": "chair", "old_sound": "h", "new_sound": "ch"},
            {"original": "best", "answer": "chest", "old_sound": "b", "new_sound": "ch"},
            {"original": "lip", "answer": "chip", "old_sound": "l", "new_sound": "ch"},
            {"original": "bin", "answer": "chin", "old_sound": "b", "new_sound": "ch"},
            {"original": "hop", "answer": "chop", "old_sound": "h", "new_sound": "ch"},
            {"original": "rain", "answer": "chain", "old_sound": "r", "new_sound": "ch"},
            {"original": "lick", "answer": "chick", "old_sound": "l", "new_sound": "ch"},
            {"original": "deer", "answer": "cheer", "old_sound": "d", "new_sound": "ch"},
            {"original": "deck", "answer": "check", "old_sound": "d", "new_sound": "ch"},
        ],
        "th": [
            {"original": "fin", "answer": "thin", "old_sound": "f", "new_sound": "th"},
            {"original": "sink", "answer": "think", "old_sound": "s", "new_sound": "th"},
            {"original": "kick", "answer": "thick", "old_sound": "k", "new_sound": "th"},
            {"original": "free", "answer": "three", "old_sound": "fr", "new_sound": "thr"},
            {"original": "ring", "answer": "thing", "old_sound": "r", "new_sound": "th"},
            {"original": "bat", "answer": "that", "old_sound": "b", "new_sound": "th"},
            {"original": "den", "answer": "then", "old_sound": "d", "new_sound": "th"},
            {"original": "his", "answer": "this", "old_sound": "h", "new_sound": "th"},
        ],
        "wh": [
            {"original": "pin", "answer": "whip", "old_sound": "p", "new_sound": "wh"},
            {"original": "heel", "answer": "wheel", "old_sound": "h", "new_sound": "wh"},
            {"original": "hen", "answer": "when", "old_sound": "h", "new_sound": "wh"},
            {"original": "bite", "answer": "white", "old_sound": "b", "new_sound": "wh"},
        ],
        "ng": [
            {"original": "rim", "answer": "ring", "old_sound": "m", "new_sound": "ng"},
            {"original": "kite", "answer": "king", "old_sound": "t", "new_sound": "ng"},
            {"original": "sit", "answer": "sing", "old_sound": "t", "new_sound": "ng"},
            {"original": "lot", "answer": "long", "old_sound": "t", "new_sound": "ng"},
            {"original": "bat", "answer": "bang", "old_sound": "t", "new_sound": "ng"},
        ],
        "ee": [
            {"original": "bad", "answer": "bead", "old_sound": "a", "new_sound": "ea"},
            {"original": "fill", "answer": "feel", "old_sound": "i", "new_sound": "ee"},
            {"original": "sit", "answer": "seat", "old_sound": "i", "new_sound": "ea"},
            {"original": "hit", "answer": "heat", "old_sound": "i", "new_sound": "ea"},
        ],
        "ai": [
            {"original": "pin", "answer": "pain", "old_sound": "i", "new_sound": "ai"},
            {"original": "tin", "answer": "train", "old_sound": "i", "new_sound": "ai"},
            {"original": "mill", "answer": "mail", "old_sound": "i", "new_sound": "ai"},
        ],
        "oa": [
            {"original": "bat", "answer": "boat", "old_sound": "a", "new_sound": "oa"},
            {"original": "cat", "answer": "coat", "old_sound": "a", "new_sound": "oa"},
            {"original": "rod", "answer": "road", "old_sound": "o", "new_sound": "oa"},
        ],
        "oo": [
            {"original": "back", "answer": "book", "old_sound": "a", "new_sound": "oo"},
            {"original": "lack", "answer": "look", "old_sound": "a", "new_sound": "oo"},
            {"original": "fun", "answer": "food", "old_sound": "u", "new_sound": "oo"},
        ],
    }
    
    def generate_phoneme_spotter(
        self,
        scenes: List[str],
        phonemes: List[str],
    ) -> Optional[PhonemeSpotterActivity]:
        """
        Generate a Phoneme Spotter activity.
        
        Uses actual story text as the reading passage.
        Students read and underline words containing the target phoneme.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            
        Returns:
            PhonemeSpotterActivity or None if not enough data
        """
        # Pick 1-2 scenes that have the most phoneme words
        best_scenes = []
        for scene in scenes:
            words = re.findall(r"\b[a-zA-Z]+\b", scene.lower())
            count = sum(1 for w in words if any(self.word_contains_phoneme(w, p) for p in phonemes))
            best_scenes.append((scene, count))
        
        best_scenes.sort(key=lambda x: x[1], reverse=True)
        
        # Take the best 1-2 scenes
        selected = best_scenes[:2]
        passage_text = " ".join(s[0] for s in selected)
        
        # Find all target words in the passage
        words_in_passage = re.findall(r"\b[a-zA-Z]+\b", passage_text.lower())
        target_words = []
        seen = set()
        for word in words_in_passage:
            if word not in seen and any(self.word_contains_phoneme(word, p) for p in phonemes):
                target_words.append(word)
                seen.add(word)
        
        if len(target_words) < 2:
            logger.info("Phoneme spotter skipped: not enough target words in passage")
            return None
        
        line_count = min(len(target_words) + 2, 10)
        
        return PhonemeSpotterActivity(
            phonemes=[p.upper() for p in phonemes],
            passage_text=passage_text,
            target_words=target_words,
            line_count=line_count,
        )
    
    def generate_rhyming_pairs(
        self,
        scenes: List[str],
        phonemes: List[str],
        pair_count: int = 4,
    ) -> Optional[RhymingPairsActivity]:
        """
        Generate a Rhyming Pairs activity.
        
        Students match words to their rhymes. Uses curated
        rhyme dictionary for accuracy.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            pair_count: Number of matching pairs
            
        Returns:
            RhymingPairsActivity or None if not enough data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        # Find words that have rhymes in our dictionary
        rhyme_candidates = []
        for phoneme, words in phoneme_words.items():
            for word in words:
                rhymes = self.RHYME_MAP.get(word.lower(), [])
                if rhymes:
                    rhyme_candidates.append((word, rhymes))
        
        # Also check the rhyme map directly for common phoneme words 
        for phoneme in phonemes:
            for rhyme_word, rhymes in self.RHYME_MAP.items():
                if self.word_contains_phoneme(rhyme_word, phoneme) and rhyme_word not in [c[0] for c in rhyme_candidates]:
                    rhyme_candidates.append((rhyme_word, rhymes))
        
        if len(rhyme_candidates) < 2:
            logger.info("Rhyming pairs skipped: not enough rhyme candidates")
            return None
        
        random.shuffle(rhyme_candidates)
        selected = rhyme_candidates[:pair_count]
        
        rhyme_pairs = []
        for word, rhymes in selected:
            # Pick 1 correct rhyme and 2 distractors
            correct = random.choice(rhymes)
            distractors = self.get_distractors(2, phonemes, [word, correct])
            options = [correct] + distractors
            random.shuffle(options)
            
            rhyme_pairs.append({
                "word": word,
                "answer": correct,
                "options": options,
            })
        
        # Pick a couple words for the "write your own" section
        write_candidates = rhyme_candidates[pair_count:pair_count + 3]
        if not write_candidates:
            write_candidates = rhyme_candidates[:2]
        write_pairs = [{"word": w} for w, _ in write_candidates[:2]]
        
        return RhymingPairsActivity(
            phonemes=[p.upper() for p in phonemes],
            rhyme_pairs=rhyme_pairs,
            write_pairs=write_pairs,
        )
    
    def _get_phoneme_position(self, word: str, phoneme: str) -> str:
        """
        Determine where a phoneme appears in a word.
        
        Returns: 'beginning', 'middle', or 'end'
        """
        word_lower = word.lower()
        phoneme_lower = phoneme.lower()
        
        idx = word_lower.find(phoneme_lower)
        if idx == -1:
            return "middle"  # fallback
        
        if idx == 0:
            return "beginning"
        elif idx + len(phoneme_lower) >= len(word_lower):
            return "end"
        else:
            return "middle"
    
    def generate_phoneme_position(
        self,
        scenes: List[str],
        phonemes: List[str],
    ) -> Optional[PhonemePositionActivity]:
        """
        Generate a Beginning, Middle, End activity.
        
        Students sort words by where the phoneme appears.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            
        Returns:
            PhonemePositionActivity or None if not enough data
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        beginning = []
        middle = []
        end = []
        
        for phoneme, words in phoneme_words.items():
            for word in words:
                position = self._get_phoneme_position(word, phoneme.lower())
                if position == "beginning":
                    beginning.append(word)
                elif position == "middle":
                    middle.append(word)
                else:
                    end.append(word)
        
        # Remove duplicates
        beginning = list(dict.fromkeys(beginning))
        middle = list(dict.fromkeys(middle))
        end = list(dict.fromkeys(end))
        
        total = len(beginning) + len(middle) + len(end)
        if total < 3:
            logger.info("Phoneme position skipped: not enough words")
            return None
        
        # Create shuffled display list
        all_position_words = beginning + middle + end
        random.shuffle(all_position_words)
        
        # Examples for column headers
        ex_beg = beginning[0] if beginning else "ship"
        ex_mid = middle[0] if middle else "fishing"
        ex_end = end[0] if end else "wish"
        
        line_count = max(len(beginning), len(middle), len(end), 4)
        
        return PhonemePositionActivity(
            phonemes=[p.upper() for p in phonemes],
            all_words=all_position_words,
            beginning_words=beginning,
            middle_words=middle,
            end_words=end,
            example_beginning=ex_beg,
            example_middle=ex_mid,
            example_end=ex_end,
            line_count=line_count,
        )
    
    def generate_sound_swap(
        self,
        scenes: List[str],
        phonemes: List[str],
        swap_count: int = 5,
    ) -> Optional[SoundSwapActivity]:
        """
        Generate a Sound Swap activity.
        
        Students change one sound in a word to make a new word
        containing the target phoneme. Uses curated swap dictionary.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            swap_count: Number of swap items
            
        Returns:
            SoundSwapActivity or None if not enough data
        """
        all_swaps = []
        for phoneme in phonemes:
            phoneme_lower = phoneme.lower()
            swaps = self.SOUND_SWAP_DB.get(phoneme_lower, [])
            all_swaps.extend(swaps)
        
        if len(all_swaps) < 2:
            logger.info("Sound swap skipped: not enough swap pairs")
            return None
        
        random.shuffle(all_swaps)
        selected = all_swaps[:swap_count]
        
        # Use first pair as the example
        example = selected[0]
        swap_words = selected[1:] if len(selected) > 1 else selected
        
        return SoundSwapActivity(
            phonemes=[p.upper() for p in phonemes],
            swap_words=swap_words,
            example_original=example["original"],
            example_new=example["answer"],
            example_old_sound=example["old_sound"],
            example_new_sound=example["new_sound"],
        )
    
    # ═══════════════════════════════════════════════════════════════
    # WORD LADDER DATABASE - curated connected word sequences
    # ═══════════════════════════════════════════════════════════════
    WORD_LADDER_DB = {
        "sh": [
            {
                "rungs": [
                    {"word": "ship", "given": True, "hint": ""},
                    {"word": "shop", "given": False, "hint": "A place to buy things"},
                    {"word": "shot", "given": False, "hint": "Kick a ball — take a ___"},
                    {"word": "shut", "given": True, "hint": ""},
                ]
            },
            {
                "rungs": [
                    {"word": "shed", "given": True, "hint": ""},
                    {"word": "shin", "given": False, "hint": "Part of your leg"},
                    {"word": "shine", "given": False, "hint": "The sun does this"},
                    {"word": "share", "given": True, "hint": ""},
                ]
            },
        ],
        "ch": [
            {
                "rungs": [
                    {"word": "chat", "given": True, "hint": ""},
                    {"word": "chap", "given": False, "hint": "A friendly fellow"},
                    {"word": "chip", "given": False, "hint": "A crunchy snack"},
                    {"word": "chin", "given": True, "hint": ""},
                ]
            },
            {
                "rungs": [
                    {"word": "chop", "given": True, "hint": ""},
                    {"word": "chap", "given": False, "hint": "A man or boy"},
                    {"word": "chat", "given": False, "hint": "Talk with a friend"},
                    {"word": "chest", "given": True, "hint": ""},
                ]
            },
        ],
        "th": [
            {
                "rungs": [
                    {"word": "thin", "given": True, "hint": ""},
                    {"word": "than", "given": False, "hint": "Bigger ___ a cat"},
                    {"word": "that", "given": False, "hint": "Look at ___!"},
                    {"word": "this", "given": True, "hint": ""},
                ]
            },
        ],
        "ee": [
            {
                "rungs": [
                    {"word": "seed", "given": True, "hint": ""},
                    {"word": "feed", "given": False, "hint": "Give food to"},
                    {"word": "feet", "given": False, "hint": "At the end of your legs"},
                    {"word": "keep", "given": True, "hint": ""},
                ]
            },
        ],
    }
    
    # ═══════════════════════════════════════════════════════════════
    # READ & DRAW sentence templates
    # ═══════════════════════════════════════════════════════════════
    READ_DRAW_TEMPLATES = {
        "sh": [
            "The {ship} sailed to the {shore}.",
            "She found a {shiny} {shell} on the beach.",
            "The {sheep} hid in the {shed}.",
            "He {shut} the door and {shouted}.",
        ],
        "ch": [
            "The {chick} sat on the {chair}.",
            "She ate a {chip} and had a {chat}.",
            "The {chest} was full of {chocolates}.",
            "He had to {chop} the log with a {chain}.",
        ],
        "th": [
            "I {think} {three} is a good number.",
            "{This} book is {thicker} {than} {that} one.",
            "{The} cat ran {through} {the} grass.",
        ],
    }
    
    def _count_syllables(self, word: str) -> int:
        """
        Count syllables in a word using vowel-cluster heuristic.
        """
        word = word.lower().strip()
        if not word:
            return 1
        
        vowels = "aeiouy"
        count = 0
        prev_vowel = False
        
        for char in word:
            is_vowel = char in vowels
            if is_vowel and not prev_vowel:
                count += 1
            prev_vowel = is_vowel
        
        # Silent e
        if word.endswith('e') and count > 1:
            count -= 1
        # Words like "the" should be 1
        if count == 0:
            count = 1
        
        return count
    
    def _syllable_breakdown(self, word: str, syllable_count: int) -> str:
        """Create a rough syllable breakdown string."""
        word = word.lower()
        if syllable_count == 1:
            return word
        
        # Simple heuristic: split at consonant clusters between vowels
        vowels = "aeiouy"
        breaks = []
        in_vowel = False
        last_break = 0
        
        for i, ch in enumerate(word):
            is_v = ch in vowels
            if is_v and not in_vowel and i > 0 and len(breaks) < syllable_count - 1:
                # Find split point (before this vowel cluster, at a consonant)
                split = i
                if i > 1 and word[i-1] not in vowels:
                    split = i - 1 if i - 1 > last_break else i
                if split > last_break:
                    breaks.append(split)
                    last_break = split
            in_vowel = is_v
        
        if not breaks:
            mid = len(word) // syllable_count
            breaks = [mid * (i+1) for i in range(syllable_count - 1)]
        
        parts = []
        prev = 0
        for b in breaks:
            parts.append(word[prev:b])
            prev = b
        parts.append(word[prev:])
        
        return "-".join(p for p in parts if p)
    
    def _segment_phonemes(self, word: str, target_phonemes: List[str]) -> List[str]:
        """
        Segment a word into individual phonemes/sounds.
        Handles common digraphs and the target phoneme.
        """
        word_lower = word.lower()
        sounds = []
        i = 0
        
        # Common digraphs to treat as single sounds
        digraphs = sorted(
            list(set(["sh", "ch", "th", "wh", "ng", "ck", "ph", "qu", "wr", "kn", "gn"]
                     + [p.lower() for p in target_phonemes if len(p) > 1])),
            key=len, reverse=True
        )
        
        while i < len(word_lower):
            matched = False
            for dg in digraphs:
                if word_lower[i:i+len(dg)] == dg:
                    sounds.append(dg)
                    i += len(dg)
                    matched = True
                    break
            if not matched:
                sounds.append(word_lower[i])
                i += 1
        
        return sounds
    
    def generate_syllable_count(
        self,
        scenes: List[str],
        phonemes: List[str],
        word_count: int = 7,
    ) -> Optional[SyllableCountActivity]:
        """
        Generate a Syllable Count activity.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        candidates = []
        for _, words in phoneme_words.items():
            for word in words:
                if len(word) >= 3:
                    syllables = self._count_syllables(word)
                    candidates.append({
                        "word": word,
                        "syllables": syllables,
                        "breakdown": self._syllable_breakdown(word, syllables),
                    })
        
        # Remove duplicates
        seen = set()
        unique = []
        for c in candidates:
            if c["word"] not in seen:
                seen.add(c["word"])
                unique.append(c)
        candidates = unique
        
        if len(candidates) < 3:
            logger.info("Syllable count skipped: not enough words")
            return None
        
        # Sort by variety of syllable counts
        random.shuffle(candidates)
        selected = candidates[:word_count]
        
        # Use first candidate as example
        example = selected[0]
        activity_words = selected[1:] if len(selected) > 1 else selected
        
        max_syl = max(c["syllables"] for c in candidates[:word_count]) + 1
        max_syl = min(max_syl, 5)
        
        return SyllableCountActivity(
            phonemes=[p.upper() for p in phonemes],
            words=activity_words,
            example_word=example["word"],
            example_syllables=example["syllables"],
            example_breakdown=example["breakdown"],
            max_syllables=max_syl,
        )
    
    def generate_word_ladder(
        self,
        scenes: List[str],
        phonemes: List[str],
    ) -> Optional[WordLadderActivity]:
        """
        Generate a Word Ladder activity.
        Uses curated ladders from the database.
        """
        all_ladders = []
        for phoneme in phonemes:
            ladders = self.WORD_LADDER_DB.get(phoneme.lower(), [])
            all_ladders.extend(ladders)
        
        if not all_ladders:
            logger.info("Word ladder skipped: no ladders for these phonemes")
            return None
        
        random.shuffle(all_ladders)
        selected = all_ladders[:2]  # Max 2 ladders per worksheet
        
        return WordLadderActivity(
            phonemes=[p.upper() for p in phonemes],
            ladders=selected,
        )
    
    def generate_read_and_draw(
        self,
        scenes: List[str],
        phonemes: List[str],
        sentence_count: int = 3,
    ) -> Optional[ReadAndDrawActivity]:
        """
        Generate a Read & Draw activity.
        Creates sentences rich in phoneme words with HTML markup.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        flat_words = []
        for _, words in phoneme_words.items():
            flat_words.extend(words)
        flat_words = list(dict.fromkeys(flat_words))  # de-dupe
        
        # Try using template sentences first
        sentences = []
        for phoneme in phonemes:
            templates = self.READ_DRAW_TEMPLATES.get(phoneme.lower(), [])
            for tmpl in templates:
                # Check if we can fill in the template with words
                filled = tmpl
                display = tmpl
                targets_in = []
                
                # Replace {word} placeholders
                import re as re_mod
                for match in re_mod.finditer(r'\{(\w+)\}', tmpl):
                    w = match.group(1)
                    targets_in.append(w)
                    filled = filled.replace('{' + w + '}', w)
                    display = display.replace(
                        '{' + w + '}',
                        f'<span class="target-word">{w}</span>'
                    )
                
                if targets_in:
                    sentences.append({
                        "text": filled,
                        "display_html": display,
                        "target_words": targets_in,
                    })
        
        # If not enough templates, build simple sentences from story words
        if len(sentences) < sentence_count and len(flat_words) >= 2:
            simple_templates = [
                "The {w1} is on the {w2}.",
                "I can see a {w1} and a {w2}.",
                "Look at the big {w1}!",
            ]
            random.shuffle(flat_words)
            for tmpl in simple_templates:
                if len(sentences) >= sentence_count:
                    break
                if '{w2}' in tmpl and len(flat_words) >= 2:
                    w1, w2 = flat_words[0], flat_words[1]
                    text = tmpl.replace('{w1}', w1).replace('{w2}', w2)
                    disp = tmpl.replace(
                        '{w1}', f'<span class="target-word">{w1}</span>'
                    ).replace(
                        '{w2}', f'<span class="target-word">{w2}</span>'
                    )
                    sentences.append({
                        "text": text,
                        "display_html": disp,
                        "target_words": [w1, w2],
                    })
                elif '{w1}' in tmpl and flat_words:
                    w1 = flat_words[0]
                    text = tmpl.replace('{w1}', w1)
                    disp = tmpl.replace(
                        '{w1}', f'<span class="target-word">{w1}</span>'
                    )
                    sentences.append({
                        "text": text,
                        "display_html": disp,
                        "target_words": [w1],
                    })
        
        if len(sentences) < 2:
            logger.info("Read and draw skipped: not enough sentences")
            return None
        
        random.shuffle(sentences)
        selected = sentences[:sentence_count]
        
        return ReadAndDrawActivity(
            phonemes=[p.upper() for p in phonemes],
            sentences=selected,
        )
    
    def generate_phoneme_count(
        self,
        scenes: List[str],
        phonemes: List[str],
        word_count: int = 6,
    ) -> Optional[PhonemeCountActivity]:
        """
        Generate a Phoneme Count (Elkonin box) activity.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        candidates = []
        for _, words in phoneme_words.items():
            for word in words:
                if 2 <= len(word) <= 7:
                    sounds = self._segment_phonemes(word, phonemes)
                    if 2 <= len(sounds) <= 6:
                        candidates.append({
                            "word": word,
                            "sounds": sounds,
                            "count": len(sounds),
                        })
        
        # Remove duplicates
        seen = set()
        unique = []
        for c in candidates:
            if c["word"] not in seen:
                seen.add(c["word"])
                unique.append(c)
        candidates = unique
        
        if len(candidates) < 3:
            logger.info("Phoneme count skipped: not enough words")
            return None
        
        random.shuffle(candidates)
        selected = candidates[:word_count + 1]
        
        # Use first as example
        example = selected[0]
        activity_words = selected[1:] if len(selected) > 1 else selected
        
        max_boxes = max(c["count"] for c in selected) + 1
        max_boxes = min(max_boxes, 7)
        
        # Count letters in the target phoneme
        phoneme_letter_count = max(len(p) for p in phonemes)
        
        return PhonemeCountActivity(
            phonemes=[p.upper() for p in phonemes],
            words=activity_words,
            example_word=example["word"],
            example_sounds=example["sounds"],
            max_boxes=max_boxes,
            phoneme_letter_count=phoneme_letter_count,
        )
    
    # ═══════════════════════════════════════════════════════════════
    # CROSSWORD CLUE DATABASE
    # ═══════════════════════════════════════════════════════════════
    CROSSWORD_DB = {
        "sh": [
            {"word": "ship", "clue": "It sails on the sea"},
            {"word": "shed", "clue": "A small building in the garden"},
            {"word": "shell", "clue": "Found on the beach"},
            {"word": "shop", "clue": "A place to buy things"},
            {"word": "sheep", "clue": "An animal that says 'baa'"},
            {"word": "shoe", "clue": "You wear it on your foot"},
            {"word": "shine", "clue": "What the sun does"},
            {"word": "fish", "clue": "It swims in water"},
        ],
        "ch": [
            {"word": "chin", "clue": "Below your mouth"},
            {"word": "chat", "clue": "Talk with a friend"},
            {"word": "chest", "clue": "A box for treasure"},
            {"word": "chick", "clue": "A baby bird"},
            {"word": "chip", "clue": "A crunchy snack"},
            {"word": "chop", "clue": "Cut with an axe"},
            {"word": "rich", "clue": "Having lots of money"},
        ],
        "th": [
            {"word": "thin", "clue": "Not thick"},
            {"word": "this", "clue": "_____ one right here"},
            {"word": "them", "clue": "Give it to _____"},
            {"word": "bath", "clue": "Where you wash"},
            {"word": "path", "clue": "A way to walk"},
            {"word": "math", "clue": "Adding and counting"},
        ],
    }
    
    # ═══════════════════════════════════════════════════════════════
    # WORD BUILDING TILE DATABASE
    # ═══════════════════════════════════════════════════════════════
    WORD_BUILDING_DB = {
        "sh": {
            "tiles": ["i", "e", "o", "a", "p", "t", "n", "l", "d", "r"],
            "words": ["ship", "shed", "shin", "shop", "shot", "shut", "shell", "shelf", "shore", "shade"],
        },
        "ch": {
            "tiles": ["i", "a", "o", "e", "p", "t", "n", "l", "d", "r"],
            "words": ["chip", "chop", "chat", "chin", "chest", "chant", "rich", "ranch"],
        },
        "th": {
            "tiles": ["i", "a", "e", "n", "s", "r", "k", "p"],
            "words": ["thin", "this", "than", "then", "think", "thane", "that"],
        },
    }
    
    def generate_odd_one_out(
        self,
        scenes: List[str],
        phonemes: List[str],
        group_count: int = 5,
    ) -> Optional[OddOneOutActivity]:
        """
        Generate an Odd One Out activity.
        Each group has 3 words with the phoneme and 1 without.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        correct_words = []
        for _, words in phoneme_words.items():
            correct_words.extend(words)
        correct_words = list(dict.fromkeys(correct_words))
        
        if len(correct_words) < 4:
            logger.info("Odd one out skipped: not enough phoneme words")
            return None
        
        # Get distractor words (words without the phoneme)
        distractors = self.get_distractors(group_count + 2, phonemes, correct_words)
        if len(distractors) < group_count + 1:
            # Add common short words as distractors
            backup = ["cat", "dog", "run", "big", "red", "cup", "hat", "sun", "bed", "box", "pig", "top"]
            for w in backup:
                if w not in distractors and not any(p.lower() in w.lower() for p in phonemes):
                    distractors.append(w)
        
        if len(distractors) < 2:
            logger.info("Odd one out skipped: not enough distractors")
            return None
        
        random.shuffle(correct_words)
        random.shuffle(distractors)
        
        # Build example
        ex_correct = correct_words[:3]
        ex_odd = distractors[0]
        correct_words = correct_words[3:]
        distractors = distractors[1:]
        
        # Build groups
        groups = []
        for i in range(min(group_count, len(correct_words) // 3)):
            if not distractors:
                break
            group_correct = correct_words[i*3:(i+1)*3]
            if len(group_correct) < 3:
                break
            odd = distractors[i % len(distractors)]
            group_words = group_correct + [odd]
            random.shuffle(group_words)
            groups.append({
                "words": group_words,
                "odd": odd,
            })
        
        if len(groups) < 2:
            logger.info("Odd one out skipped: not enough groups")
            return None
        
        return OddOneOutActivity(
            phonemes=[p.upper() for p in phonemes],
            groups=groups,
            example_correct_1=ex_correct[0] if len(ex_correct) > 0 else "",
            example_correct_2=ex_correct[1] if len(ex_correct) > 1 else "",
            example_correct_3=ex_correct[2] if len(ex_correct) > 2 else "",
            example_odd=ex_odd,
        )
    
    def generate_missing_sound(
        self,
        scenes: List[str],
        phonemes: List[str],
        word_count: int = 6,
    ) -> Optional[MissingSoundActivity]:
        """
        Generate a Missing Sound activity.
        Words with the phoneme blanked out.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        candidates = []
        primary_phoneme = phonemes[0].lower()
        
        for _, words in phoneme_words.items():
            for word in words:
                word_lower = word.lower()
                if primary_phoneme in word_lower and len(word) >= 3:
                    # Create display with blank
                    blank = '<span class="missing-blank">' + '_' * len(primary_phoneme) + '</span>'
                    display = word_lower.replace(primary_phoneme, blank, 1)
                    
                    # Generate hint
                    hints = {
                        "ship": "A big boat", "shop": "Buy things here",
                        "shell": "Found on the beach", "shine": "The sun does this",
                        "shed": "In the garden", "sheep": "Says baa",
                        "she": "A girl", "shore": "Edge of the sea",
                        "shut": "Close it", "share": "Give some to a friend",
                    }
                    hint = hints.get(word_lower, f"Rhymes with ...")
                    
                    candidates.append({
                        "word": word,
                        "display": display,
                        "hint": hint,
                    })
        
        # Remove duplicates
        seen = set()
        unique = []
        for c in candidates:
            if c["word"] not in seen:
                seen.add(c["word"])
                unique.append(c)
        candidates = unique
        
        if len(candidates) < 3:
            logger.info("Missing sound skipped: not enough words")
            return None
        
        random.shuffle(candidates)
        example = candidates[0]
        activity_words = candidates[1:word_count + 1]
        
        # Create example display
        example_blank = '<span class="missing-blank">' + primary_phoneme + '</span>'
        example_display = example["word"].lower().replace(
            primary_phoneme,
            example_blank,
            1
        )
        
        return MissingSoundActivity(
            phonemes=[p.upper() for p in phonemes],
            words=activity_words,
            example_word=example["word"],
            example_display=example_display,
            example_phoneme=primary_phoneme,
        )
    
    def _generate_nonsense_word(self, phoneme: str) -> str:
        """Generate a plausible nonsense word containing the phoneme."""
        onsets = ["", "b", "c", "d", "f", "g", "h", "j", "k", "l", "m", "n", "p", "r", "s", "t", "w"]
        rimes = ["ip", "op", "ep", "ap", "ig", "og", "eg", "ag", "ib", "ob", "ut", "en", "id", "od"]
        
        phoneme_lower = phoneme.lower()
        
        # Randomly place phoneme at start or end
        if random.random() < 0.6:
            # Phoneme at start
            rime = random.choice(rimes)
            word = phoneme_lower + rime
        else:
            # Phoneme at end
            onset = random.choice([o for o in onsets if o])
            vowels = ["a", "e", "i", "o", "u"]
            word = onset + random.choice(vowels) + phoneme_lower
        
        return word
    
    def generate_real_or_nonsense(
        self,
        scenes: List[str],
        phonemes: List[str],
        word_count: int = 10,
    ) -> Optional[RealOrNonsenseActivity]:
        """
        Generate a Real or Nonsense activity.
        Mix of real words and generated nonsense words.
        """
        all_words = self.extract_words_from_scenes(scenes)
        phoneme_words = self.find_phoneme_words(all_words, phonemes)
        
        real_words = []
        for _, words in phoneme_words.items():
            real_words.extend(words)
        real_words = list(dict.fromkeys(real_words))
        
        if len(real_words) < 3:
            logger.info("Real or nonsense skipped: not enough real words")
            return None
        
        random.shuffle(real_words)
        
        # Take half real, half nonsense
        real_count = min(len(real_words), word_count // 2 + 1)
        selected_real = real_words[:real_count]
        
        # Generate nonsense words
        nonsense_count = word_count - real_count
        nonsense_words = []
        used = set(w.lower() for w in all_words)
        
        for _ in range(nonsense_count * 3):  # Generate extras to pick from
            if len(nonsense_words) >= nonsense_count:
                break
            nw = self._generate_nonsense_word(phonemes[0])
            if nw not in used and len(nw) >= 3:
                nonsense_words.append(nw)
                used.add(nw)
        
        # Build word list
        words = [{"word": w, "is_real": True} for w in selected_real]
        words += [{"word": w, "is_real": False} for w in nonsense_words]
        random.shuffle(words)
        
        # Example
        example_real = selected_real[0] if selected_real else "ship"
        example_nonsense = nonsense_words[0] if nonsense_words else "shog"
        
        return RealOrNonsenseActivity(
            phonemes=[p.upper() for p in phonemes],
            words=words,
            example_real=example_real,
            example_nonsense=example_nonsense,
        )
    
    def generate_word_building(
        self,
        scenes: List[str],
        phonemes: List[str],
    ) -> Optional[WordBuildingActivity]:
        """
        Generate a Word Building activity.
        Uses curated tile sets or builds from story words.
        """
        primary_phoneme = phonemes[0].lower()
        
        # Try curated data first
        curated = self.WORD_BUILDING_DB.get(primary_phoneme)
        if curated:
            tiles = curated["tiles"]
            possible = curated["words"]
        else:
            # Build from story words
            all_words = self.extract_words_from_scenes(scenes)
            phoneme_words = self.find_phoneme_words(all_words, phonemes)
            
            possible = []
            for _, words in phoneme_words.items():
                possible.extend([w for w in words if len(w) >= 3])
            possible = list(dict.fromkeys(possible))
            
            if len(possible) < 3:
                logger.info("Word building skipped: not enough words")
                return None
            
            # Extract unique letters from possible words (minus the phoneme)
            letter_set = set()
            for w in possible:
                for ch in w.lower().replace(primary_phoneme, "", 1):
                    if ch.isalpha():
                        letter_set.add(ch)
            tiles = sorted(list(letter_set))[:12]
        
        return WordBuildingActivity(
            phonemes=[p.upper() for p in phonemes],
            phoneme_raw=primary_phoneme,
            letter_tiles=tiles,
            target_count=min(len(possible), 8),
            possible_words=possible[:10],
            line_count=min(len(possible) + 2, 12),
        )
    
    def generate_crossword(
        self,
        scenes: List[str],
        phonemes: List[str],
        clue_count: int = 6,
    ) -> Optional[CrosswordActivity]:
        """
        Generate a Crossword activity.
        Uses curated clue database.
        """
        all_clues = []
        for phoneme in phonemes:
            clues = self.CROSSWORD_DB.get(phoneme.lower(), [])
            all_clues.extend(clues)
        
        if not all_clues:
            # Try to build from story words
            all_words = self.extract_words_from_scenes(scenes)
            phoneme_words = self.find_phoneme_words(all_words, phonemes)
            
            flat = []
            for _, words in phoneme_words.items():
                flat.extend(words)
            flat = list(dict.fromkeys(flat))
            
            for w in flat[:clue_count]:
                all_clues.append({"word": w, "clue": f"Write the word: {w}"})
        
        if len(all_clues) < 3:
            logger.info("Crossword skipped: not enough clues")
            return None
        
        random.shuffle(all_clues)
        selected = all_clues[:clue_count]
        
        primary_phoneme = phonemes[0].lower()
        
        # Build cells for each word (with hint letters)
        for item in selected:
            word = item["word"]
            cells = []
            phoneme_found = False
            i = 0
            while i < len(word):
                # Check if this position starts the phoneme
                if not phoneme_found and word[i:i+len(primary_phoneme)].lower() == primary_phoneme:
                    for ch in primary_phoneme:
                        cells.append({"letter": ch.upper(), "hint": True})
                    i += len(primary_phoneme)
                    phoneme_found = True
                else:
                    cells.append({"letter": word[i].upper(), "hint": False})
                    i += 1
            item["cells"] = cells
        
        return CrosswordActivity(
            phonemes=[p.upper() for p in phonemes],
            clues=selected,
        )

    async def generate_comprehension_activities(
        self,
        scenes: List[str],
        story_title: str,
        config: ActivityConfig,
        difficulty_level: int = 2,
    ) -> Tuple[
        Optional[ComprehensionQuestionsActivity],
        Optional[VocabularyBuildingActivity],
        Optional[SynonymsActivity],
        Optional[InferredMeaningActivity],
    ]:
        """
        Generate comprehension-focused activities using Gemini AI.

        Unlike phonics activities (deterministic), these require an LLM
        to generate story-specific questions, vocabulary, and inference tasks.
        All enabled types are generated in a single Gemini call.
        """
        full_story = "\n\n".join(scenes)

        # Build list of requested types
        requested = []
        if config.include_comprehension_questions:
            requested.append("comprehension_questions")
        if config.include_vocabulary_building:
            requested.append("vocabulary_building")
        if config.include_synonyms:
            requested.append("synonyms")
        if config.include_inferred_meaning:
            requested.append("inferred_meaning")

        if not requested:
            return None, None, None, None

        # Difficulty descriptions for the prompt
        difficulty_desc = {
            1: """Foundation/Prep level (ages 4-5).
VOCABULARY: Choose only simple, concrete, high-frequency words (1-2 syllables max, e.g. "big", "run", "sad"). Definitions must be 5-8 words using only words a 4-year-old knows.
SYNONYMS: Use only very common pairs a Prep child would know (e.g. big/large, happy/glad, fast/quick). All synonym options must be single-syllable or very common 2-syllable words.
COMPREHENSION: Basic recall only ("What colour was the...?"). 2-3 word answers. All multiple-choice options must be simple words/short phrases.
INFERRED MEANING: Very simple emotions only ("How did X feel?"). Single-word or 2-3 word answers.""",
            2: """Year 1 level (ages 5-6).
VOCABULARY: Choose simple, mostly concrete words (1-2 syllables, e.g. "brave", "proud", "swift"). Definitions should be one simple sentence using common words.
SYNONYMS: Use common synonym pairs suitable for Year 1 (e.g. happy/joyful, scared/afraid, fast/quick). All options should be words a Year 1 child can read independently.
COMPREHENSION: Mix of recall and basic inference. Short sentence answers. Multiple-choice options should use simple, decodable language.
INFERRED MEANING: Simple feelings and motivations. Short answer (1 sentence).""",
            3: """Year 2 level (ages 6-7).
VOCABULARY: Choose interesting but accessible words (up to 3 syllables, e.g. "amazing", "carefully", "adventure"). Definitions can be 1-2 sentences.
SYNONYMS: Include slightly more varied pairs (e.g. brave/courageous, grin/smile, sprint/dash). Options can include some 2-3 syllable words that Year 2 children encounter in reading.
COMPREHENSION: Mix of recall, basic inference, and simple vocabulary questions. 1-2 sentence answers.
INFERRED MEANING: Feelings, motivations, and simple cause-effect. 1-2 sentence answers.""",
            4: """Year 3-4 level (ages 7-9).
VOCABULARY: Choose richer vocabulary (up to 3-4 syllables, e.g. "determined", "spectacular", "cautiously"). Definitions should be precise and may use more sophisticated language.
SYNONYMS: Use more nuanced pairs (e.g. exhausted/weary, enormous/immense, furious/enraged). Include some words that stretch Year 3-4 readers.
COMPREHENSION: Include deeper inference, vocabulary-in-context, and cause-effect questions. Multi-sentence answers expected.
INFERRED MEANING: Character motivation, prediction, cause-effect, and theme. 2-3 sentence answers with reasoning.""",
            5: """Year 5+ level (ages 10+).
VOCABULARY: Choose sophisticated, rich vocabulary (multi-syllable words, e.g. "exhilarating", "contemplate", "resilience"). Definitions should be precise and academic.
SYNONYMS: Use advanced synonym pairs with subtle distinctions (e.g. reluctant/hesitant, diminish/dwindle, meticulous/thorough). Include words that challenge Year 5+ readers.
COMPREHENSION: Include analysis, author's purpose, vocabulary-in-context, and complex inference. Detailed multi-sentence answers.
INFERRED MEANING: Complex inference about themes, author intent, character development. 2-3 sentence analytical answers.""",
        }
        level_desc = difficulty_desc.get(difficulty_level, difficulty_desc[2])

        prompt = f"""You are creating reading comprehension worksheets for a children's storybook.

STORY TITLE: "{story_title}"

STORY TEXT:
{full_story}

STUDENT LEVEL:
{level_desc}

CRITICAL: The activities MUST match the student level described above. Every word choice, question complexity, answer length, and synonym option must be appropriate for that level. Do NOT use vocabulary or concepts above the target level.

Generate the following activity types: {', '.join(requested)}

Return ONLY valid JSON with these keys (include only the requested types):

{'{'}
{self._comprehension_schema_for_types(requested)}
{'}'}

IMPORTANT RULES:
- All questions must be directly answerable from the story text
- Vocabulary words must actually appear in the story AND be appropriate complexity for the student level
- Synonym words and all answer options must be age-appropriate — a child at this level should be able to read every word independently
- For multiple choice, always provide exactly 3 options (a, b, c)
- Keep language simple and clear for the target age group
- For inferred meaning, the story_clue MUST be a direct quote from the story
- For inferred meaning, questions must test GENUINE inference — ask what a character is feeling, thinking, or why something happened based on clues, NOT just restate or rephrase the quote. The answer should never be explicitly stated in the clue. Ask questions like "How is [character] feeling here? How do you know?", "What does this tell us about [character]?", "What do you think will happen next? Why?"
- Make exercises engaging and educational
"""

        try:
            ai = AIConfig()
            raw = await ai.generate_with_gemini(prompt)

            # Extract JSON from response (handle markdown code blocks)
            json_str = raw.strip()
            if json_str.startswith("```"):
                json_str = json_str.split("\n", 1)[1] if "\n" in json_str else json_str[3:]
                if json_str.endswith("```"):
                    json_str = json_str[:-3]
                elif "```" in json_str:
                    json_str = json_str[:json_str.rfind("```")]
            json_str = json_str.strip()

            # Fix common Gemini JSON issues: trailing commas before ] or }
            import re as _re
            json_str = _re.sub(r',\s*([}\]])', r'\1', json_str)

            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                # Second attempt: strip any remaining non-JSON preamble/postamble
                # Find the outermost { ... } block
                start = json_str.find('{')
                end = json_str.rfind('}')
                if start != -1 and end != -1 and end > start:
                    json_str = json_str[start:end + 1]
                    json_str = _re.sub(r',\s*([}\]])', r'\1', json_str)
                data = json.loads(json_str)

            comp = None
            vocab = None
            syns = None
            infer = None

            if "comprehension_questions" in data and config.include_comprehension_questions:
                comp = ComprehensionQuestionsActivity(
                    questions=data["comprehension_questions"],
                    story_title=story_title,
                )

            if "vocabulary_building" in data and config.include_vocabulary_building:
                vocab = VocabularyBuildingActivity(
                    words=data["vocabulary_building"],
                    story_title=story_title,
                )

            if "synonyms" in data and config.include_synonyms:
                syns = SynonymsActivity(
                    synonym_pairs=data["synonyms"].get("pairs", []),
                    matching_exercise=data["synonyms"].get("matching", []),
                    story_title=story_title,
                )

            if "inferred_meaning" in data and config.include_inferred_meaning:
                infer = InferredMeaningActivity(
                    questions=data["inferred_meaning"],
                    story_title=story_title,
                )

            logger.info(f"Generated comprehension activities: comp={comp is not None}, vocab={vocab is not None}, syns={syns is not None}, infer={infer is not None}")
            return comp, vocab, syns, infer

        except Exception as e:
            logger.error(f"Failed to generate comprehension activities: {e}")
            return None, None, None, None

    def _comprehension_schema_for_types(self, requested: List[str]) -> str:
        """Build the JSON schema description for the requested comprehension types."""
        parts = []
        if "comprehension_questions" in requested:
            parts.append('''"comprehension_questions": [
    {"question": "...", "type": "multiple_choice", "options": ["a) ...", "b) ...", "c) ..."], "answer": "a) ...", "story_reference": "relevant part of story"},
    {"question": "...", "type": "short_answer", "options": [], "answer": "...", "story_reference": "relevant part of story"}
  ] (generate 4-6 questions, mix of multiple_choice and short_answer)''')
        if "vocabulary_building" in requested:
            parts.append('''"vocabulary_building": [
    {"word": "word from story", "definition": "simple definition", "context_sentence": "the sentence from the story containing this word", "exercise_sentence": "A new sentence with _____ where the word goes"}
  ] (generate 5-6 words. CRITICAL: choose words whose complexity matches the student level — for younger levels pick simpler words, for older levels pick richer vocabulary. The definition and exercise sentence must also use language the student can read independently.)''')
        if "synonyms" in requested:
            parts.append('''"synonyms": {
    "pairs": [{"word": "word from story", "synonym": "a simpler or equivalent word", "sentence": "the sentence from the story using this word"}],
    "matching": [{"word": "word from story", "options": ["option1", "option2", "option3"], "answer": "correct synonym"}]
  } (generate 5-6 pairs and 4-5 matching questions. CRITICAL: both the story words and all synonym options must be readable by a student at the target level. For younger levels use simple 1-2 syllable synonyms; for older levels use richer vocabulary.)''')
        if "inferred_meaning" in requested:
            parts.append('''"inferred_meaning": [
    {"question": "inference question that requires reading between the lines", "story_clue": "direct quote from the story that contains the clue", "answer": "suggested answer explaining the inference", "type": "motivation|prediction|feeling|cause_effect"}
  ] (generate 4-5 questions across different types. CRITICAL: questions must require genuine inference — the answer must NOT be stated directly in the story_clue. Good example: clue "Her pink nose twitched with glee" → question "How was Daisy feeling? What tells you this?" Bad example: clue "Her pink nose twitched with glee" → question "Why did Daisy's nose twitch with glee?" — this just restates the quote.)''')
        return ",\n".join(parts)

    async def generate_all_activities(
        self,
        scenes: List[str],
        phonemes: List[str],
        config: Optional[ActivityConfig] = None,
        max_phonemes: Optional[int] = None,
        story_title: Optional[str] = None,
        difficulty_level: Optional[int] = None,
    ) -> Tuple[List[Dict], AnswerKeyData]:
        """
        Generate all enabled activities for a story.
        
        Args:
            scenes: Story scene texts
            phonemes: Target phonemes
            config: Activity configuration (which types to include)
            max_phonemes: Optional cap on number of phonemes used for activities.
                          When set (e.g. 5 for storybook worksheets), trims the
                          list to avoid wall-of-text / garbled Sound Matching.
                          Leave None for callers that need the full list.
            
        Returns:
            Tuple of (list of activity template data dicts, answer key data)
        """
        if config is None:
            config = ActivityConfig()  # All enabled by default
        
        activities = []
        answer_key = AnswerKeyData()
        
        # ── Optional phoneme cap (storybook worksheets use max_phonemes=5) ──
        # More than ~5 breaks Sound Matching layout (tiny answer boxes = garbled),
        # creates a wall-of-text in Word Hunt instructions, and overwhelms teacher tips.
        # Only applied when the caller explicitly requests it.
        if max_phonemes and len(phonemes) > max_phonemes:
            logger.warning(
                f"Capping {len(phonemes)} phonemes to {max_phonemes} for activities. "
                f"Original: {phonemes[:10]}{'...' if len(phonemes) > 10 else ''}"
            )
            # Prefer multi-letter phonemes (digraphs/trigraphs) — more pedagogically
            # useful on worksheets than single letters like 's', 'a', 't'
            multi = [p for p in phonemes if len(p) >= 2]
            single = [p for p in phonemes if len(p) < 2]
            phonemes = (multi + single)[:max_phonemes]
            logger.info(f"Capped activity phonemes: {phonemes}")
        
        logger.info(f"Generating activities for phonemes: {phonemes}")
        
        # Word Hunt
        if config.include_word_hunt:
            word_hunt = self.generate_word_hunt(scenes, phonemes)
            if word_hunt.story_words:
                activities.append(word_hunt.to_template_data())
                answer_key.word_hunt_answers = word_hunt.story_words
                logger.info(f"Generated Word Hunt with {len(word_hunt.story_words)} correct words")
        
        # Sound Matching (only if 2+ phonemes)
        if config.include_sound_matching and len(phonemes) >= 2:
            sound_matching = self.generate_sound_matching(scenes, phonemes)
            if sound_matching:
                activities.append(sound_matching.to_template_data())
                answer_key.sound_matching_answers = sound_matching.word_phoneme_pairs
                logger.info(f"Generated Sound Matching with {len(sound_matching.word_phoneme_pairs)} pairs")
        
        # Fill in the Blank
        if config.include_fill_in_blank:
            fill_blank = self.generate_fill_in_blank(scenes, phonemes)
            if fill_blank:
                activities.append(fill_blank.to_template_data())
                answer_key.fill_in_blank_answers = fill_blank.sentences
                logger.info(f"Generated Fill in Blank with {len(fill_blank.sentences)} sentences")
        
        # Tracing
        if config.include_tracing:
            tracing = self.generate_tracing(scenes, phonemes)
            if tracing.example_words:
                activities.append(tracing.to_template_data())
                logger.info(f"Generated Tracing with {len(tracing.example_words)} example words")
        
        # Circle the Sound
        if config.include_circle_sound:
            circle_sound = self.generate_circle_sound(scenes, phonemes)
            if circle_sound.story_words:
                activities.append(circle_sound.to_template_data())
                answer_key.circle_sound_answers = circle_sound.story_words
                logger.info(f"Generated Circle Sound with {len(circle_sound.story_words)} correct words")
        
        # Word Scramble
        if config.include_word_scramble:
            word_scramble = self.generate_word_scramble(scenes, phonemes)
            if word_scramble:
                activities.append(word_scramble.to_template_data())
                answer_key.word_scramble_answers = [
                    {"scrambled": "".join(w["scrambled_letters"]), "answer": w["word"]}
                    for w in word_scramble.scramble_words
                ]
                logger.info(f"Generated Word Scramble with {len(word_scramble.scramble_words)} words")
        
        # Cut & Sort
        if config.include_cut_and_sort:
            cut_sort = self.generate_cut_and_sort(scenes, phonemes)
            if cut_sort.story_words:
                activities.append(cut_sort.to_template_data())
                answer_key.cut_and_sort_answers = cut_sort.story_words
                logger.info(f"Generated Cut & Sort with {cut_sort.total_words} total words")
        
        # Sentence Building
        if config.include_sentence_building:
            sentence_building = self.generate_sentence_building(scenes, phonemes)
            if sentence_building:
                activities.append(sentence_building.to_template_data())
                answer_key.sentence_building_words = sentence_building.bank_words
                logger.info(f"Generated Sentence Building with {len(sentence_building.bank_words)} bank words")
        
        # Phoneme Spotter
        if config.include_phoneme_spotter:
            phoneme_spotter = self.generate_phoneme_spotter(scenes, phonemes)
            if phoneme_spotter:
                activities.append(phoneme_spotter.to_template_data())
                answer_key.phoneme_spotter_answers = phoneme_spotter.target_words
                logger.info(f"Generated Phoneme Spotter with {len(phoneme_spotter.target_words)} target words")
        
        # Rhyming Pairs
        if config.include_rhyming_pairs:
            rhyming = self.generate_rhyming_pairs(scenes, phonemes)
            if rhyming:
                activities.append(rhyming.to_template_data())
                answer_key.rhyming_pairs_answers = [
                    {"word": p["word"], "answer": p["answer"]}
                    for p in rhyming.rhyme_pairs
                ]
                logger.info(f"Generated Rhyming Pairs with {len(rhyming.rhyme_pairs)} pairs")
        
        # Phoneme Position (Beginning, Middle, End)
        if config.include_phoneme_position:
            position = self.generate_phoneme_position(scenes, phonemes)
            if position:
                activities.append(position.to_template_data())
                answer_key.phoneme_position_answers = {
                    "beginning": position.beginning_words,
                    "middle": position.middle_words,
                    "end": position.end_words,
                }
                logger.info(f"Generated Phoneme Position with {len(position.all_words)} words")
        
        # Sound Swap
        if config.include_sound_swap:
            sound_swap = self.generate_sound_swap(scenes, phonemes)
            if sound_swap:
                activities.append(sound_swap.to_template_data())
                answer_key.sound_swap_answers = [
                    {"original": s["original"], "answer": s["answer"]}
                    for s in sound_swap.swap_words
                ]
                logger.info(f"Generated Sound Swap with {len(sound_swap.swap_words)} swaps")
        
        # Syllable Count
        if config.include_syllable_count:
            syllable = self.generate_syllable_count(scenes, phonemes)
            if syllable:
                activities.append(syllable.to_template_data())
                answer_key.syllable_count_answers = [
                    {"word": w["word"], "syllables": w["syllables"], "breakdown": w["breakdown"]}
                    for w in syllable.words
                ]
                logger.info(f"Generated Syllable Count with {len(syllable.words)} words")
        
        # Word Ladder
        if config.include_word_ladder:
            ladder = self.generate_word_ladder(scenes, phonemes)
            if ladder:
                activities.append(ladder.to_template_data())
                answer_key.word_ladder_answers = [
                    {"rungs": [r["word"] for r in l["rungs"]]}
                    for l in ladder.ladders
                ]
                logger.info(f"Generated Word Ladder with {len(ladder.ladders)} ladders")
        
        # Read & Draw
        if config.include_read_and_draw:
            read_draw = self.generate_read_and_draw(scenes, phonemes)
            if read_draw:
                activities.append(read_draw.to_template_data())
                answer_key.read_and_draw_sentences = [
                    s["text"] for s in read_draw.sentences
                ]
                logger.info(f"Generated Read & Draw with {len(read_draw.sentences)} sentences")
        
        # Phoneme Count
        if config.include_phoneme_count:
            pcount = self.generate_phoneme_count(scenes, phonemes)
            if pcount:
                activities.append(pcount.to_template_data())
                answer_key.phoneme_count_answers = [
                    {"word": w["word"], "sounds": w["sounds"], "count": w["count"]}
                    for w in pcount.words
                ]
                logger.info(f"Generated Phoneme Count with {len(pcount.words)} words")
        
        # Odd One Out
        if config.include_odd_one_out:
            odd = self.generate_odd_one_out(scenes, phonemes)
            if odd:
                activities.append(odd.to_template_data())
                answer_key.odd_one_out_answers = [
                    {"odd": g["odd"], "words": g["words"]}
                    for g in odd.groups
                ]
                logger.info(f"Generated Odd One Out with {len(odd.groups)} groups")
        
        # Missing Sound
        if config.include_missing_sound:
            missing = self.generate_missing_sound(scenes, phonemes)
            if missing:
                activities.append(missing.to_template_data())
                answer_key.missing_sound_answers = [
                    {"word": w["word"]}
                    for w in missing.words
                ]
                logger.info(f"Generated Missing Sound with {len(missing.words)} words")
        
        # Real or Nonsense
        if config.include_real_or_nonsense:
            real_non = self.generate_real_or_nonsense(scenes, phonemes)
            if real_non:
                activities.append(real_non.to_template_data())
                answer_key.real_or_nonsense_answers = [
                    {"word": w["word"], "is_real": w["is_real"]}
                    for w in real_non.words
                ]
                logger.info(f"Generated Real or Nonsense with {len(real_non.words)} words")
        
        # Word Building
        if config.include_word_building:
            wb = self.generate_word_building(scenes, phonemes)
            if wb:
                activities.append(wb.to_template_data())
                answer_key.word_building_words = wb.possible_words
                logger.info(f"Generated Word Building with {len(wb.possible_words)} possible words")
        
        # Crossword
        if config.include_crossword:
            cw = self.generate_crossword(scenes, phonemes)
            if cw:
                activities.append(cw.to_template_data())
                answer_key.crossword_answers = [
                    {"clue": c["clue"], "answer": c["word"]}
                    for c in cw.clues
                ]
                logger.info(f"Generated Crossword with {len(cw.clues)} clues")

        # Comprehension Activities (AI-generated via Gemini)
        any_comprehension = (
            config.include_comprehension_questions
            or config.include_vocabulary_building
            or config.include_synonyms
            or config.include_inferred_meaning
        )
        if any_comprehension:
            comp, vocab, syns, infer = await self.generate_comprehension_activities(
                scenes=scenes,
                story_title=story_title or "",
                config=config,
                difficulty_level=difficulty_level or 2,
            )

            if comp and comp.questions:
                activities.append(comp.to_template_data())
                answer_key.comprehension_answers = [
                    {"question": q["question"], "answer": q["answer"]}
                    for q in comp.questions
                ]
                logger.info(f"Generated Comprehension Questions with {len(comp.questions)} questions")

            if vocab and vocab.words:
                activities.append(vocab.to_template_data())
                answer_key.vocabulary_answers = [
                    {"word": w["word"], "definition": w["definition"]}
                    for w in vocab.words
                ]
                logger.info(f"Generated Vocabulary Building with {len(vocab.words)} words")

            if syns and syns.synonym_pairs:
                activities.append(syns.to_template_data())
                answer_key.synonyms_answers = [
                    {"word": p["word"], "synonym": p["synonym"]}
                    for p in syns.synonym_pairs
                ]
                logger.info(f"Generated Synonyms with {len(syns.synonym_pairs)} pairs")

            if infer and infer.questions:
                activities.append(infer.to_template_data())
                answer_key.inferred_meaning_answers = [
                    {"question": q["question"], "answer": q["answer"]}
                    for q in infer.questions
                ]
                logger.info(f"Generated Inferred Meaning with {len(infer.questions)} questions")

        return activities, answer_key

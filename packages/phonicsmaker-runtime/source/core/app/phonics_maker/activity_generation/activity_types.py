# phonics_maker/activity_generation/activity_types.py
"""
Data models for phonics activities.
Each activity type has its own structure for template rendering.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field


def _build_phoneme_display(phonemes: List[str], max_display: int = 5, join_str: str = " & ", quote: bool = True) -> str:
    """Build a concise phoneme display string, capping at max_display items."""
    items = [f"'{p.lower()}'" for p in phonemes[:max_display]] if quote else [p.lower() for p in phonemes[:max_display]]
    display = join_str.join(items)
    if len(phonemes) > max_display:
        display += f" (+ {len(phonemes) - max_display} more)"
    return display


class ActivityType(Enum):
    """Available activity types for end-of-book worksheets."""
    WORD_HUNT = "word_hunt"
    SOUND_MATCHING = "sound_matching"
    FILL_IN_THE_BLANK = "fill_in_the_blank" 
    TRACING = "tracing"
    CIRCLE_SOUND = "circle_sound"
    WORD_SCRAMBLE = "word_scramble"
    CUT_AND_SORT = "cut_and_sort"
    SENTENCE_BUILDING = "sentence_building"
    PHONEME_SPOTTER = "phoneme_spotter"
    RHYMING_PAIRS = "rhyming_pairs"
    PHONEME_POSITION = "phoneme_position"
    SOUND_SWAP = "sound_swap"
    SYLLABLE_COUNT = "syllable_count"
    WORD_LADDER = "word_ladder"
    READ_AND_DRAW = "read_and_draw"
    PHONEME_COUNT = "phoneme_count"
    ODD_ONE_OUT = "odd_one_out"
    MISSING_SOUND = "missing_sound"
    REAL_OR_NONSENSE = "real_or_nonsense"
    WORD_BUILDING = "word_building"
    CROSSWORD = "crossword"
    COMPREHENSION_QUESTIONS = "comprehension_questions"
    VOCABULARY_BUILDING = "vocabulary_building"
    SYNONYMS = "synonyms"
    INFERRED_MEANING = "inferred_meaning"


@dataclass
class ActivityConfig:
    """Configuration for which activities to include in a book."""
    include_word_hunt: bool = True
    include_sound_matching: bool = True
    include_fill_in_blank: bool = True
    include_tracing: bool = True
    include_circle_sound: bool = False
    include_word_scramble: bool = False
    include_cut_and_sort: bool = False
    include_sentence_building: bool = False
    include_phoneme_spotter: bool = False
    include_rhyming_pairs: bool = False
    include_phoneme_position: bool = False
    include_sound_swap: bool = False
    include_syllable_count: bool = False
    include_word_ladder: bool = False
    include_read_and_draw: bool = False
    include_phoneme_count: bool = False
    include_odd_one_out: bool = False
    include_missing_sound: bool = False
    include_real_or_nonsense: bool = False
    include_word_building: bool = False
    include_crossword: bool = False
    include_comprehension_questions: bool = True
    include_vocabulary_building: bool = True
    include_synonyms: bool = True
    include_inferred_meaning: bool = True

    def get_enabled_types(self) -> List[ActivityType]:
        """Return list of enabled activity types."""
        enabled = []
        if self.include_word_hunt:
            enabled.append(ActivityType.WORD_HUNT)
        if self.include_sound_matching:
            enabled.append(ActivityType.SOUND_MATCHING)
        if self.include_fill_in_blank:
            enabled.append(ActivityType.FILL_IN_THE_BLANK)
        if self.include_tracing:
            enabled.append(ActivityType.TRACING)
        if self.include_circle_sound:
            enabled.append(ActivityType.CIRCLE_SOUND)
        if self.include_word_scramble:
            enabled.append(ActivityType.WORD_SCRAMBLE)
        if self.include_cut_and_sort:
            enabled.append(ActivityType.CUT_AND_SORT)
        if self.include_sentence_building:
            enabled.append(ActivityType.SENTENCE_BUILDING)
        if self.include_phoneme_spotter:
            enabled.append(ActivityType.PHONEME_SPOTTER)
        if self.include_rhyming_pairs:
            enabled.append(ActivityType.RHYMING_PAIRS)
        if self.include_phoneme_position:
            enabled.append(ActivityType.PHONEME_POSITION)
        if self.include_sound_swap:
            enabled.append(ActivityType.SOUND_SWAP)
        if self.include_syllable_count:
            enabled.append(ActivityType.SYLLABLE_COUNT)
        if self.include_word_ladder:
            enabled.append(ActivityType.WORD_LADDER)
        if self.include_read_and_draw:
            enabled.append(ActivityType.READ_AND_DRAW)
        if self.include_phoneme_count:
            enabled.append(ActivityType.PHONEME_COUNT)
        if self.include_odd_one_out:
            enabled.append(ActivityType.ODD_ONE_OUT)
        if self.include_missing_sound:
            enabled.append(ActivityType.MISSING_SOUND)
        if self.include_real_or_nonsense:
            enabled.append(ActivityType.REAL_OR_NONSENSE)
        if self.include_word_building:
            enabled.append(ActivityType.WORD_BUILDING)
        if self.include_crossword:
            enabled.append(ActivityType.CROSSWORD)
        if self.include_comprehension_questions:
            enabled.append(ActivityType.COMPREHENSION_QUESTIONS)
        if self.include_vocabulary_building:
            enabled.append(ActivityType.VOCABULARY_BUILDING)
        if self.include_synonyms:
            enabled.append(ActivityType.SYNONYMS)
        if self.include_inferred_meaning:
            enabled.append(ActivityType.INFERRED_MEANING)
        return enabled


@dataclass
class WordHuntActivity:
    """
    Phonics Word Hunt Activity
    
    Students identify words containing the target phoneme(s) from a list.
    Mix of correct answers (from story) and distractors.
    """
    phonemes: List[str]  # Target phonemes for this activity
    story_words: List[str]  # Words from story containing target phonemes
    distractor_words: List[str]  # Words that don't contain target phonemes
    all_words: List[str] = field(default_factory=list)  # Shuffled mix for display
    correct_count: int = 0  # Number of correct answers
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "word_hunt",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.all_words,
            "story_words": self.story_words,
            "correct_count": self.correct_count,
        }


@dataclass
class SoundMatchingActivity:
    """
    Sound Matching Activity
    
    Students match words to their phoneme sounds.
    E.g., "ship" → SH, "chat" → CH
    """
    phonemes: List[str]  # Available phoneme choices
    word_phoneme_pairs: List[Dict[str, str]]  # [{"word": "ship", "phoneme": "SH"}, ...]
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "sound_matching",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes, join_str=" / ", quote=False),
            "pairs": self.word_phoneme_pairs,
            "pair_count": len(self.word_phoneme_pairs),
        }


@dataclass
class FillInTheBlankActivity:
    """
    Fill in the Blank Activity
    
    Students complete words by filling in the missing phoneme.
    E.g., "The ___ip sailed away." (Answer: sh)
    """
    phonemes: List[str]
    sentences: List[Dict[str, str]]  # [{"sentence": "The ___ip sailed.", "answer": "sh", "full_word": "ship"}, ...]
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "fill_in_blank",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "sentences": self.sentences,
            "sentence_count": len(self.sentences),
        }


@dataclass
class TracingActivity:
    """
    Tracing Practice Activity
    
    Students trace the target phonemes and example words.
    Designed for handwriting practice reinforcement.
    """
    phonemes: List[str]
    example_words: List[str]  # Words containing phonemes for tracing practice
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "tracing",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes, quote=False),
            "uppercase_phonemes": [p.upper() for p in self.phonemes],
            "lowercase_phonemes": [p.lower() for p in self.phonemes],
            "example_words": self.example_words,
        }


@dataclass
class CircleSoundActivity:
    """
    Circle the Sound Activity
    
    Students read words displayed in bubbles and circle/colour
    the ones containing the target phoneme. Includes counting.
    """
    phonemes: List[str]
    story_words: List[str]  # Words containing the target phoneme
    distractor_words: List[str]  # Words without the target phoneme
    all_words: List[str] = field(default_factory=list)  # Shuffled mix
    correct_count: int = 0
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "circle_sound",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.all_words,
            "story_words": self.story_words,
            "correct_count": self.correct_count,
        }


@dataclass
class WordScrambleActivity:
    """
    Word Scramble Activity
    
    Students unscramble jumbled letters to form words
    containing the target phoneme. Hints provided.
    """
    phonemes: List[str]
    scramble_words: List[Dict[str, Any]]
    # Each dict: {"word": "ship", "scrambled_letters": ["h","s","p","i"], "hint": "It sails on water"}
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "word_scramble",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "scramble_words": self.scramble_words,
        }


@dataclass
class CutAndSortActivity:
    """
    Cut & Sort Activity
    
    Students sort words into two columns: those that contain
    the target phoneme and those that don't.
    """
    phonemes: List[str]
    story_words: List[str]  # Words with the phoneme
    distractor_words: List[str]  # Words without
    all_words: List[str] = field(default_factory=list)  # Shuffled mix
    total_words: int = 0
    line_count: int = 6  # Number of writing lines per column
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "cut_and_sort",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "all_words": self.all_words,
            "story_words": self.story_words,
            "total_words": self.total_words,
            "line_count": self.line_count,
        }


@dataclass
class SentenceBuildingActivity:
    """
    Sentence Building Activity
    
    Students use words from a word bank (all containing the
    target phoneme) to write their own sentences.
    """
    phonemes: List[str]
    bank_words: List[str]  # All words in the word bank
    sentence_words: List[str]  # Subset of words they must use (for prompts)
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "sentence_building",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "bank_words": self.bank_words,
            "sentence_words": self.sentence_words,
        }


@dataclass
class PhonemeSpotterActivity:
    """
    Phoneme Spotter Activity
    
    Students read a passage from the story and underline
    every word containing the target phoneme.
    Builds fluency + phoneme awareness in connected text.
    """
    phonemes: List[str]
    passage_text: str  # The passage to read
    target_words: List[str]  # Words in the passage that contain the phoneme
    line_count: int = 8
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "phoneme_spotter",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "passage_text": self.passage_text,
            "target_words": self.target_words,
            "target_count": len(self.target_words),
            "line_count": self.line_count,
        }


@dataclass
class RhymingPairsActivity:
    """
    Rhyming Pairs Activity
    
    Students match words containing the target phoneme to
    rhyming words from multiple choices. Then write their own.
    Builds phonological awareness.
    """
    phonemes: List[str]
    rhyme_pairs: List[Dict[str, Any]]
    # Each: {"word": "ship", "answer": "tip", "options": ["tip", "cat", "run"]}
    write_pairs: List[Dict[str, str]]  # Words for "write your own" section
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "rhyming_pairs",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "rhyme_pairs": self.rhyme_pairs,
            "write_pairs": self.write_pairs,
        }


@dataclass
class PhonemePositionActivity:
    """
    Beginning, Middle, End Activity
    
    Students categorize words by WHERE the target phoneme
    appears: beginning (onset), middle (medial), or end (coda).
    Develops segmenting skills.
    """
    phonemes: List[str]
    all_words: List[str]  # Shuffled mix for display
    beginning_words: List[str]  # Phoneme at start
    middle_words: List[str]  # Phoneme in middle
    end_words: List[str]  # Phoneme at end
    example_beginning: str = ""
    example_middle: str = ""
    example_end: str = ""
    line_count: int = 5
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "phoneme_position",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "all_words": self.all_words,
            "beginning_words": self.beginning_words,
            "middle_words": self.middle_words,
            "end_words": self.end_words,
            "example_beginning": self.example_beginning,
            "example_middle": self.example_middle,
            "example_end": self.example_end,
            "line_count": self.line_count,
        }


@dataclass
class SoundSwapActivity:
    """
    Sound Swap Activity
    
    Students change one sound in a word to make a new word
    that contains the target phoneme. Advanced phoneme
    manipulation skill.
    """
    phonemes: List[str]
    swap_words: List[Dict[str, str]]
    # Each: {"original": "sip", "answer": "ship", "old_sound": "s", "new_sound": "sh"}
    example_original: str = ""
    example_new: str = ""
    example_old_sound: str = ""
    example_new_sound: str = ""
    
    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "activity_type": "sound_swap",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "swap_words": self.swap_words,
            "example_original": self.example_original,
            "example_new": self.example_new,
            "example_old_sound": self.example_old_sound,
            "example_new_sound": self.example_new_sound,
        }


@dataclass
class SyllableCountActivity:
    """
    Syllable Count Activity
    
    Students clap and count syllables in words containing
    the target phoneme. Visual circles for each beat.
    """
    phonemes: List[str]
    words: List[Dict[str, Any]]
    # Each: {"word": "shopping", "syllables": 2, "breakdown": "shop-ping"}
    example_word: str = ""
    example_syllables: int = 1
    example_breakdown: str = ""
    max_syllables: int = 4
    
    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "syllable_count",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.words,
            "example_word": self.example_word,
            "example_syllables": self.example_syllables,
            "example_breakdown": self.example_breakdown,
            "max_syllables": self.max_syllables,
        }


@dataclass
class WordLadderActivity:
    """
    Word Ladder Activity
    
    Students change one letter at a time to transform a
    start word into a target word, every rung containing
    the target phoneme.
    """
    phonemes: List[str]
    ladders: List[Dict[str, Any]]
    # Each ladder: {"rungs": [{"word": "ship", "given": True, "hint": ""}, ...]}
    
    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "word_ladder",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "ladders": self.ladders,
        }


@dataclass
class ReadAndDrawActivity:
    """
    Read & Draw Activity
    
    Students read short sentences rich in phoneme words,
    then draw a picture of what they read. Connects
    decoding to comprehension.
    """
    phonemes: List[str]
    sentences: List[Dict[str, str]]
    # Each: {"text": "...", "display_html": "...", "target_words": ["ship", "shore"]}
    
    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "read_and_draw",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "sentences": self.sentences,
        }


@dataclass
class PhonemeCountActivity:
    """
    Phoneme Count Activity
    
    Students use Elkonin-style sound boxes to segment
    words into individual phonemes and count them.
    """
    phonemes: List[str]
    words: List[Dict[str, Any]]
    # Each: {"word": "ship", "sounds": ["sh", "i", "p"], "count": 3}
    example_word: str = ""
    example_sounds: List[str] = field(default_factory=list)
    max_boxes: int = 6
    phoneme_letter_count: int = 2
    
    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "phoneme_count",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.words,
            "example_word": self.example_word,
            "example_sounds": self.example_sounds,
            "max_boxes": self.max_boxes,
            "phoneme_letter_count": self.phoneme_letter_count,
        }


@dataclass
class OddOneOutActivity:
    """
    Odd One Out Activity
    Students identify which word in a group does NOT contain the target phoneme.
    """
    phonemes: List[str]
    groups: List[Dict[str, Any]]  # [{"words": [...], "odd": "word"}]
    example_correct_1: str = ""
    example_correct_2: str = ""
    example_correct_3: str = ""
    example_odd: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "odd_one_out",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "groups": self.groups,
            "example_correct_1": self.example_correct_1,
            "example_correct_2": self.example_correct_2,
            "example_correct_3": self.example_correct_3,
            "example_odd": self.example_odd,
        }


@dataclass
class MissingSoundActivity:
    """
    Missing Sound Activity
    Words with the phoneme blanked out; students write the missing letters.
    """
    phonemes: List[str]
    words: List[Dict[str, str]]  # [{"word": ..., "display": ..., "hint": ...}]
    example_word: str = ""
    example_display: str = ""
    example_phoneme: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "missing_sound",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.words,
            "example_word": self.example_word,
            "example_display": self.example_display,
            "example_phoneme": self.example_phoneme,
        }


@dataclass
class RealOrNonsenseActivity:
    """
    Real or Nonsense Activity
    Students decide if words are real or made-up. Tests decoding accuracy.
    """
    phonemes: List[str]
    words: List[Dict[str, Any]]  # [{"word": ..., "is_real": True/False}]
    example_real: str = ""
    example_nonsense: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "real_or_nonsense",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "words": self.words,
            "example_real": self.example_real,
            "example_nonsense": self.example_nonsense,
        }


@dataclass
class WordBuildingActivity:
    """
    Word Building Activity
    Students use letter tiles plus the phoneme to construct real words.
    """
    phonemes: List[str]
    phoneme_raw: str  # The raw phoneme for the tile
    letter_tiles: List[str]
    target_count: int  # How many words can be built
    possible_words: List[str]
    line_count: int = 10

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "word_building",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "phoneme_raw": self.phoneme_raw,
            "letter_tiles": self.letter_tiles,
            "target_count": self.target_count,
            "possible_words": self.possible_words,
            "line_count": self.line_count,
        }


@dataclass
class CrosswordActivity:
    """
    Crossword Activity
    A simple crossword where all answers contain the target phoneme.
    """
    phonemes: List[str]
    clues: List[Dict[str, Any]]  # [{"word": ..., "clue": ..., "cells": [...]}]

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "crossword",
            "phonemes": self.phonemes,
            "phoneme_display": _build_phoneme_display(self.phonemes),
            "clues": self.clues,
        }


@dataclass
class ComprehensionQuestionsActivity:
    """
    Reading Comprehension Activity

    Students answer questions about the story they just read.
    Mix of multiple-choice and short-answer questions.
    """
    questions: List[Dict[str, Any]]
    # Each: {"question": "...", "type": "multiple_choice"|"short_answer",
    #        "options": ["A", "B", "C"] (MC only), "answer": "...",
    #        "story_reference": "relevant passage"}
    story_title: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "comprehension_questions",
            "story_title": self.story_title,
            "questions": self.questions,
            "question_count": len(self.questions),
        }


@dataclass
class VocabularyBuildingActivity:
    """
    Vocabulary Builder Activity

    Students learn new words from the story with definitions,
    context sentences, and fill-in-the-blank exercises.
    """
    words: List[Dict[str, str]]
    # Each: {"word": "...", "definition": "...",
    #        "context_sentence": "sentence from story",
    #        "exercise_sentence": "fill-in-blank sentence"}
    story_title: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "vocabulary_building",
            "story_title": self.story_title,
            "words": self.words,
            "word_count": len(self.words),
        }


@dataclass
class SynonymsActivity:
    """
    Synonym Detective Activity

    Students match words from the story to their synonyms
    and use synonyms in sentences.
    """
    synonym_pairs: List[Dict[str, str]]
    # Each: {"word": "...", "synonym": "...", "sentence": "sentence using word from story"}
    matching_exercise: List[Dict[str, Any]]
    # Each: {"word": "...", "options": ["opt1", "opt2", "opt3"], "answer": "correct synonym"}
    story_title: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "synonyms",
            "story_title": self.story_title,
            "synonym_pairs": self.synonym_pairs,
            "matching_exercise": self.matching_exercise,
            "pair_count": len(self.synonym_pairs),
        }


@dataclass
class InferredMeaningActivity:
    """
    Reading Between the Lines Activity

    Students answer inference questions that require understanding
    character motivations, predictions, feelings, and cause/effect.
    """
    questions: List[Dict[str, Any]]
    # Each: {"question": "...", "story_clue": "relevant passage",
    #        "answer": "...", "type": "prediction"|"motivation"|"feeling"|"cause_effect"}
    story_title: str = ""

    def to_template_data(self) -> Dict[str, Any]:
        return {
            "activity_type": "inferred_meaning",
            "story_title": self.story_title,
            "questions": self.questions,
            "question_count": len(self.questions),
        }


@dataclass
class AnswerKeyData:
    """Answer key for all activities - printed on final page."""
    word_hunt_answers: List[str] = field(default_factory=list)
    sound_matching_answers: List[Dict[str, str]] = field(default_factory=list)
    fill_in_blank_answers: List[Dict[str, str]] = field(default_factory=list)
    circle_sound_answers: List[str] = field(default_factory=list)
    word_scramble_answers: List[Dict[str, str]] = field(default_factory=list)
    cut_and_sort_answers: List[str] = field(default_factory=list)
    sentence_building_words: List[str] = field(default_factory=list)
    phoneme_spotter_answers: List[str] = field(default_factory=list)
    rhyming_pairs_answers: List[Dict[str, str]] = field(default_factory=list)
    phoneme_position_answers: Dict[str, List[str]] = field(default_factory=dict)
    sound_swap_answers: List[Dict[str, str]] = field(default_factory=list)
    syllable_count_answers: List[Dict[str, Any]] = field(default_factory=list)
    word_ladder_answers: List[Dict[str, Any]] = field(default_factory=list)
    read_and_draw_sentences: List[str] = field(default_factory=list)
    phoneme_count_answers: List[Dict[str, Any]] = field(default_factory=list)
    odd_one_out_answers: List[Dict[str, Any]] = field(default_factory=list)
    missing_sound_answers: List[Dict[str, str]] = field(default_factory=list)
    real_or_nonsense_answers: List[Dict[str, Any]] = field(default_factory=list)
    word_building_words: List[str] = field(default_factory=list)
    crossword_answers: List[Dict[str, str]] = field(default_factory=list)
    comprehension_answers: List[Dict[str, Any]] = field(default_factory=list)
    vocabulary_answers: List[Dict[str, str]] = field(default_factory=list)
    synonyms_answers: List[Dict[str, str]] = field(default_factory=list)
    inferred_meaning_answers: List[Dict[str, Any]] = field(default_factory=list)

    def to_template_data(self) -> Dict[str, Any]:
        """Convert to dictionary for template rendering."""
        return {
            "word_hunt_answers": self.word_hunt_answers,
            "sound_matching_answers": self.sound_matching_answers,
            "fill_in_blank_answers": self.fill_in_blank_answers,
            "circle_sound_answers": self.circle_sound_answers,
            "word_scramble_answers": self.word_scramble_answers,
            "cut_and_sort_answers": self.cut_and_sort_answers,
            "sentence_building_words": self.sentence_building_words,
            "phoneme_spotter_answers": self.phoneme_spotter_answers,
            "rhyming_pairs_answers": self.rhyming_pairs_answers,
            "phoneme_position_answers": self.phoneme_position_answers,
            "sound_swap_answers": self.sound_swap_answers,
            "has_word_hunt": len(self.word_hunt_answers) > 0,
            "has_sound_matching": len(self.sound_matching_answers) > 0,
            "has_fill_in_blank": len(self.fill_in_blank_answers) > 0,
            "has_circle_sound": len(self.circle_sound_answers) > 0,
            "has_word_scramble": len(self.word_scramble_answers) > 0,
            "has_cut_and_sort": len(self.cut_and_sort_answers) > 0,
            "has_sentence_building": len(self.sentence_building_words) > 0,
            "has_phoneme_spotter": len(self.phoneme_spotter_answers) > 0,
            "has_rhyming_pairs": len(self.rhyming_pairs_answers) > 0,
            "has_phoneme_position": len(self.phoneme_position_answers) > 0,
            "has_sound_swap": len(self.sound_swap_answers) > 0,
            "syllable_count_answers": self.syllable_count_answers,
            "word_ladder_answers": self.word_ladder_answers,
            "read_and_draw_sentences": self.read_and_draw_sentences,
            "phoneme_count_answers": self.phoneme_count_answers,
            "has_syllable_count": len(self.syllable_count_answers) > 0,
            "has_word_ladder": len(self.word_ladder_answers) > 0,
            "has_read_and_draw": len(self.read_and_draw_sentences) > 0,
            "has_phoneme_count": len(self.phoneme_count_answers) > 0,
            "odd_one_out_answers": self.odd_one_out_answers,
            "missing_sound_answers": self.missing_sound_answers,
            "real_or_nonsense_answers": self.real_or_nonsense_answers,
            "word_building_words": self.word_building_words,
            "crossword_answers": self.crossword_answers,
            "has_odd_one_out": len(self.odd_one_out_answers) > 0,
            "has_missing_sound": len(self.missing_sound_answers) > 0,
            "has_real_or_nonsense": len(self.real_or_nonsense_answers) > 0,
            "has_word_building": len(self.word_building_words) > 0,
            "has_crossword": len(self.crossword_answers) > 0,
            "comprehension_answers": self.comprehension_answers,
            "vocabulary_answers": self.vocabulary_answers,
            "synonyms_answers": self.synonyms_answers,
            "inferred_meaning_answers": self.inferred_meaning_answers,
            "has_comprehension": len(self.comprehension_answers) > 0,
            "has_vocabulary": len(self.vocabulary_answers) > 0,
            "has_synonyms": len(self.synonyms_answers) > 0,
            "has_inferred_meaning": len(self.inferred_meaning_answers) > 0,
        }

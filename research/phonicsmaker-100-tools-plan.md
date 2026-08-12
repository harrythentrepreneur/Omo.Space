# PhonicsMaker's 96 tools in Omo's repeatable structure

Research date: 2026-08-13  
Scope: architecture and conversion specification only; no build, deployment, catalog, Worker, site, or container changes  
Decision: convert the wrappers into Omo; do not bolt the PhonicsMaker application onto Omo

## Executive conclusion

The defensible current count is **96 distinct executable product contracts**, not an assumed 100 and not the number of files in the three repositories:

- **93** unique keys in `toolPromptMap`: nine have active form configurations and 84 are prompt-only/API-reachable. A source scan using `^  '([^']+)': \{` over the top-level map returns 93 unique slugs. [E1-E3]
- **One** illustrated decodable-book generator: the web `custom-story-generator` is a link to this workflow, not another tool. [E4-E5]
- **Two** materially different edit/export contracts behind the core's `edit` mode: command/operation story editing and Studio's supplied-layout PDF re-render. They share a handler but have different inputs, risk, ownership checks, and outputs. [E5]

This count deliberately excludes the proposed `phonics-worksheet-generator` because the inspected code has no standalone worksheet executor; planned TPT-style packs because they are future products; the 92 icon PNGs because they are assets; and `/Users/yifan/phonicsmaker` sale, metrics, diligence, and Stripe scripts because they operate the business rather than produce teacher resources. [E6-E8]

The current user-visible surface is smaller: the toolkit composes nine active `toolConfigs` plus one custom story card, so **10 cards are discoverable today**. The other 84 prompt adapters are implementation inventory, not 84 proven products. [E2-E4]

The three non-breaking decisions are:

1. **Do not add Phonics routes:** the existing generated hosted-skill registry already dispatches arbitrary reviewed slugs through `/api/run`; extend compiler/host execution kinds, not Worker switches. [E10, E13]
2. **Do not redesign the catalog for 100 rows:** its O(n) lookup and 15-card incremental render are adequate; keep one generated file with a size budget, while first wiring the generic input/result design libraries into production `run.html`. [E11-E12]
3. **Do not import the Phonics DB:** runs fit existing generic records, and downloads need only generic purchase ownership/version columns plus authenticated private delivery—no content-specific table. [E14]

### Family count

| Family | Count | What is counted |
| --- | ---: | --- |
| Foundational phonics and word study | 28 | Sound, grapheme, syllable, word-family and decoding contracts |
| Vocabulary, grammar and language mechanics | 24 | Lexical, morphology, parts-of-speech and sentence mechanics |
| Reading, fluency and assessment | 11 | Reading support, comprehension, fluency and progress analysis |
| Worksheets, quizzes and printables | 9 | Quiz, cloze, flashcard, puzzle and practice-sheet drafts |
| Writing, stories and literacy content | 10 | Summaries, sentences, outlines and story-support drafts |
| Games and oral/creative activities | 5 | Word games, jokes, tongue twisters and activity ideas |
| Planning and teacher administration | 2 | Learning plan and progress note |
| Cross-curricular/general utilities | 4 | Math, history, science and code explainers |
| Illustrated story generation and editing | 3 | Book generation, story edit, Studio re-render |
| **Total** | **96** | Each row below counted once |

## 1. Complete inventory and Omo mapping

### Reading the inventory

Every input field below is an actual payload read from `prompts.ts`, `runpod_handler.py`, or the checked-in JSON fixtures; no field was invented to increase the count. The type notation is the **target** strict JSON Schema sketch: `s` string, `s[]` string array, `i` integer, `b` boolean, `e` bounded enum, `o` object. Profile work must recover exact required/default/enum/min/max behavior from `toolConfig.ts`, add `additionalProperties:false`, and add dialect where phonological output can vary. [E1-E2, E5]

Current invocation codes: **A** = active form -> Next.js `POST /api/tools` -> Gemini 2.0 Flash; **P** = prompt adapter reachable through that generic route but no active form; **G** = RunPod generate; **E** = RunPod command/operation edit; **S** = Studio route -> RunPod structured edit. The A/P route currently returns `{result, description}` text. [E3, E5]

Target output codes: **L** = bounded typed list/table JSON; **R** = structured analysis/annotations JSON; **D** = structured draft rendered as Markdown; **F** = `omo.result/v1` with private file artifacts and usage. All are wrapped by the normal Omo result envelope; none accepts a client prompt, provider, price, or object URL. Prices are provisional run prices under the requested $0.10-$2.00 band and remain non-chargeable until a measured `pricing-report.json` passes.

### 1.1 Foundational phonics and word study — 28

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 1 | Phonics list generator -> highlighted word list | A | `phonics-list-generator` | `{phonemes:s[],topic:s,difficultyLevel:e}` -> L | $0.10 |
| 2 | Syllable splitter and counter -> split/count table | A | `syllable-splitter-and-counter` | `{wordList:s}` -> L | $0.10 |
| 3 | Word family builder -> rime list, definitions, sentences | P | `word-family-builder` | `{rime:s,numberOfWords:i,includeSentences:b}` -> L | $0.10 |
| 4 | Rhyming words generator -> rhyme list | P | `rhyming-words-generator` | `{word:s,numRhymes:i,rhymeType:e}` -> L | $0.10 |
| 5 | Vowel sound categorizer -> vowel category/examples | P | `vowel-sound-categorizer` | `{word:s,includeExplanation:b,includeExamples:b}` -> R | $0.10 |
| 6 | Blend identifier -> marked blends/examples | P | `blend-identifier` | `{textInput:s,blendType:e,includeExamples:b}` -> R | $0.10 |
| 7 | Digraph spotter -> marked digraphs/explanations | A | `digraph-spotter` | `{textInput:s,digraphType:e,includeExplanations:b}` -> R | $0.10 |
| 8 | Letter-sound matcher -> match table/examples | P | `letter-sound-matcher` | `{inputType:e,input:s,includeExamples:b}` -> L | $0.10 |
| 9 | CVC word creator -> controlled word list | P | `cvc-word-creator` | `{numWords:i,vowelChoice:e,difficultyLevel:e}` -> L | $0.10 |
| 10 | Missing letter finder -> incomplete/answer pairs | P | `missing-letter-finder` | `{words:s,blankPosition:e}` -> L | $0.10 |
| 11 | Initial sound sorter -> grouped words | P | `initial-sound-sorter` | `{words:s}` -> L | $0.10 |
| 12 | Final sound sorter -> grouped words | P | `final-sound-sorter` | `{words:s}` -> L | $0.10 |
| 13 | Minimal pairs generator -> contrast pairs | P | `minimal-pairs-generator` | `{focusDescription:s,numPairs:i,positionOfChange:e}` -> L | $0.10 |
| 14 | Phoneme counter -> count and optional transcription | A | `phoneme-counter` | `{wordInput:s,showTranscription:b}` -> R | $0.10 |
| 15 | High-frequency word checker -> marked words/coverage | P | `high-frequency-word-checker` | `{textInput:s,frequencyList:e,highlightMethod:e}` -> R | $0.10 |
| 16 | Onset-rime splitter -> segmented word/explanation | P | `onset-rime-splitter` | `{wordInput:s,includeExplanation:b}` -> R | $0.10 |
| 17 | Phonics rule explainer -> rule/examples/exceptions | A | `phonics-rule-explainer` | `{phonicsRule:s,targetAudience:e,numExamples:i}` -> D | $0.10 |
| 18 | Trigraph detector -> marked trigraphs/list | P | `trigraph-detector` | `{textInput:s,highlightMethod:e,listTrigraphsSeparately:b}` -> R | $0.10 |
| 19 | Vowel team finder -> marked teams/sound notes | P | `vowel-team-finder` | `{textInput:s,highlightMethod:e,listVowelTeamsSeparately:b,includeSoundInfo:b}` -> R | $0.10 |
| 20 | R-controlled vowel spotter -> marked patterns/list | P | `r-controlled-vowel-spotter` | `{textInput:s,highlightMethod:e,listWordsSeparately:b,includeRControlledVowel:b}` -> R | $0.10 |
| 21 | Open/closed syllable identifier -> breakdown/classification | P | `open-closed-syllable-identifier` | `{wordInput:s,includeSyllableBreakdown:b,includeExplanation:b}` -> R | $0.10 |
| 22 | Silent-letter highlighter -> marked text/word list | P | `silent-letter-highlighter` | `{textInput:s,highlightMethod:e,listWordsSeparately:b,includeSilentLetter:b}` -> R | $0.10 |
| 23 | Compound-word splitter -> components/type/explanation | P | `compound-word-splitter` | `{compoundWordInput:s,includeType:b,includeExplanation:b}` -> R | $0.10 |
| 24 | Elkonin box assistant -> phoneme boxes/breakdown | P | `elkonin-box-assistant` | `{wordInput:s,includePhonemeBreakdown:b,includeRulesExplanation:b}` -> L | $0.10 |
| 25 | Sound wall categorizer -> category/examples | P | `sound-wall-categorizer` | `{phonemeInput:s,includeExplanation:b,includeExampleWords:b}` -> R | $0.10 |
| 26 | Grapheme-to-phoneme converter -> pedagogical sound mapping | A | `grapheme-to-phoneme-converter` | `{textInput:s,includeRulesExplanation:b,includeExampleWords:b}` -> R | $0.10 |
| 27 | Phoneme blending practice -> segmented/revealed words | P | `phoneme-blending-practice` | `{numPhonemes:i,phonicsFocus:s,numWords:i,includeWordReveal:b}` -> L | $0.10 |
| 28 | Phoneme segmentation practice -> word/phoneme reveal set | P | `phoneme-segmentation-practice` | `{numPhonemesTarget:i,phonicsFocus:s,numWords:i,includePhonemeReveal:b}` -> L | $0.10 |

### 1.2 Vocabulary, grammar and language mechanics — 24

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 29 | Vocabulary enhancer -> level-adjusted word suggestions | P | `vocabulary-enhancer` | `{word:s,difficultyLevel:e}` -> L | $0.10 |
| 30 | Simplified text rewriter -> age-adjusted rewrite | P | `simplified-text-rewriter` | `{originalText:s,targetAudienceAge:i}` -> D | $0.15 |
| 31 | Analogy generator -> analogy set/answers | P | `analogy-generator` | `{concept:s,wordPair:s,numAnalogies:i}` -> L | $0.10 |
| 32 | Figurative language identifier -> typed annotations | P | `figurative-language-identifier` | `{textInput:s}` -> R | $0.10 |
| 33 | Homophone helper -> meanings/examples | P | `homophone-helper` | `{wordInput:s,includeDefinitions:b,includeExamples:b}` -> L | $0.10 |
| 34 | Prefix/suffix identifier -> marked morphology | P | `prefix-suffix-identifier` | `{wordListInput:s,identifyPrefixes:b,identifySuffixes:b,highlightMethod:e}` -> R | $0.10 |
| 35 | Root word extractor -> root/affix analysis | P | `root-word-extractor` | `{wordInput:s,includeAffixes:b,highlightRoot:b}` -> R | $0.10 |
| 36 | Definition lookup -> child-level definition/sentence | P | `definition-lookup` | `{wordInput:s,targetAgeGroup:e,includeExampleSentence:b}` -> R | $0.10 |
| 37 | Sentence complexity scorer -> score/reasons | P | `sentence-complexity-scorer` | `{sentenceInput:s,scoringMethod:e,includeExplanation:b}` -> R | $0.10 |
| 38 | Alphabetical order checker -> verdict/correct order | P | `alphabetical-order-checker` | `{wordListInput:s,caseSensitive:b,includeCorrectedList:b}` -> R | $0.10 |
| 39 | Noun finder -> noun annotations/list | P | `noun-finder` | `{textInput:s,highlightMethod:e,listNounsSeparately:b}` -> R | $0.10 |
| 40 | Verb spotter -> verb annotations/types | P | `verb-spotter` | `{textInput:s,highlightMethod:e,listVerbsSeparately:b,includeVerbType:b}` -> R | $0.10 |
| 41 | Adjective identifier -> adjective annotations/list | P | `adjective-identifier` | `{textInput:s,highlightMethod:e,listAdjectivesSeparately:b}` -> R | $0.10 |
| 42 | Punctuation placer -> corrected sentence/suggestions | P | `punctuation-placer` | `{sentenceInput:s,suggestionFormat:e}` -> R | $0.10 |
| 43 | Capitalization helper -> corrections/reasons | P | `capitalization-helper` | `{textInput:s,highlightMethod:e,includeReason:b}` -> R | $0.10 |
| 44 | Contraction tool -> expanded/contracted text | P | `contraction-tool` | `{operationType:e,inputText:s,includeExplanation:b}` -> R | $0.10 |
| 45 | Synonym suggester -> leveled synonym list/examples | P | `synonym-suggester` | `{wordInput:s,numSynonyms:i,targetComplexity:e,includeExampleSentence:b}` -> L | $0.10 |
| 46 | Antonym suggester -> leveled antonym list/examples | P | `antonym-suggester` | `{wordInput:s,numAntonyms:i,targetComplexity:e,includeExampleSentence:b}` -> L | $0.10 |
| 47 | Plural noun generator -> plural/rule/example | P | `plural-noun-generator` | `{singularNoun:s,includeRules:b,includeExampleSentence:b}` -> R | $0.10 |
| 48 | Past-tense verb converter -> form/rule/example | P | `past-tense-verb-converter` | `{baseVerb:s,includeRules:b,includeExampleSentence:b}` -> R | $0.10 |
| 49 | Homograph helper -> meanings/pronunciations/examples | P | `homograph-helper` | `{wordInput:s,includeMeanings:b,includePronunciations:b,includeExampleSentences:b}` -> L | $0.10 |
| 50 | Analogy completer -> analogy set/answers | P | `analogy-completer` | `{analogyConcept:s,numAnalogies:i,difficultyLevel:e,includeAnswer:b}` -> L | $0.10 |
| 51 | Sentence fragment detector -> flags/corrections | P | `sentence-fragment-detector` | `{textInput:s,includeExplanation:b,suggestCorrection:b}` -> R | $0.10 |
| 52 | Vocabulary tier sorter -> tier/definition table | P | `vocabulary-tier-sorter` | `{wordsInput:s,includeExplanation:b,includeDefinition:b}` -> L | $0.10 |

### 1.3 Reading, fluency and assessment — 11

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 53 | Read-aloud text player -> reading script/settings (no audio today) | P | `read-aloud-text-player` | `{textToRead:s,speechSpeed:e,voicePreference:e}` -> D | $0.10 |
| 54 | Pronunciation guide -> transcription/syllables (no audio today) | P | `pronunciation-guide` | `{wordInput:s,includePhoneticTranscription:b,includeSyllableBreakdown:b,enableAudioPlayback:b}` -> R | $0.10 |
| 55 | Auditory discrimination practice -> same/different pair set (no audio today) | P | `auditory-discrimination-practice` | `{targetSoundContrast:s,numPairs:i,includeSamePairs:b,enableAudioCue:b}` -> L | $0.10 |
| 56 | Reading fluency timer -> passage/instructions/target | P | `reading-fluency-timer` | `{passageDifficulty:e,passageTheme:s,includeInstructions:b,wordsPerMinuteTarget:i}` -> D | $0.15 |
| 57 | Story sequence suggester -> ordered events/reasoning | P | `story-sequence-suggester` | `{eventsInput:s,sequenceType:e,includeReasoning:b}` -> R | $0.10 |
| 58 | Fact/opinion sorter -> classifications/evidence | P | `fact-opinion-sorter` | `{statementsInput:s,includeExplanation:b,highlightKeywords:b}` -> L | $0.10 |
| 59 | Predictable text generator -> repetitive controlled passage | P | `predictable-text-generator` | `{targetPhonicsPattern:s,storyTheme:s,numSentences:i,repetitiveElement:s}` -> D | $0.15 |
| 60 | Echo-reading prompter -> teacher/student prompt set | P | `echo-reading-prompter` | `{targetPhonicsRule:s,sentenceComplexity:e,numPrompts:i,enableAudioCue:b}` -> L | $0.10 |
| 61 | Choral-reading text selector -> candidate texts/rationales | P | `choral-reading-text-selector` | `{textType:e,targetAgeGroup:e,theme:s,numSuggestions:i}` -> L | $0.10 |
| 62 | Language-experience story starter -> starter/teacher tips | P | `language-experience-story-starter` | `{storyTopicSuggestion:s,targetAgeGroup:e,includeTips:b}` -> D | $0.10 |
| 63 | Decoding error analyzer -> cautious hypothesis/practice | A | `phonics-reading-error-coach` | `{misreadWord:s,actualWord:s,includeDetailedExplanation:b,suggestPractice:b}` -> R | $0.10 |

### 1.4 Worksheets, quizzes and printables — 9

These are text drafts today despite names such as “maker” and “puzzle.” PDF is a later, gated executor capability, not something the current generic Gemini route delivers. [E1-E3]

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 64 | Multiple-choice quiz generator -> questions/options/key | P | `multiple-choice-quiz-generator` | `{topic:s,textInput:s,numQuestions:i,difficulty:e}` -> L | $0.15 |
| 65 | Fill-in-the-blanks generator -> exercise/key | P | `fill-in-the-blanks-generator` | `{textInput:s,numBlanks:i,blankType:e}` -> L | $0.15 |
| 66 | Sight-word flashcard maker -> card-copy plan | P | `sight-word-flashcard-maker` | `{sightWords:s,cardStyle:e,fontSize:i}` -> L | $0.25 |
| 67 | Sentence unscrambler -> scrambled prompt/answer | P | `sentence-unscrambler` | `{sentence:s,scrambleUnits:e}` -> L | $0.10 |
| 68 | Spelling-bee practice list -> leveled list/context | P | `spelling-bee-practice-list` | `{listType:e,phonicsRule:s,gradeLevel:e,numWords:i,includeSentenceContext:b}` -> L | $0.10 |
| 69 | Cloze passage generator -> passage/word bank/key | P | `cloze-passage-generator` | `{originalText:s,targetPhonicsPattern:s,numBlanks:i,includeWordBank:b}` -> L | $0.15 |
| 70 | Word-search puzzle maker -> word/grid specification | P | `word-search-puzzle-maker` | `{phonicsRule:s,numWords:i,gridSize:e,directions:e}` -> L | $0.25 |
| 71 | Crossword clue generator -> clues/length hints | P | `crossword-clue-generator` | `{wordInput:s,clueDifficulty:e,clueStyle:e,includeLengthHint:b}` -> L | $0.15 |
| 72 | Word-shape puzzle generator -> shape/answer rows | P | `word-shape-puzzle-generator` | `{wordInput:s,shapeRepresentation:e,showOriginalWord:b}` -> L | $0.15 |

### 1.5 Writing, stories and literacy content — 10

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 73 | Text summarizer -> bounded summary | P | `text-summarizer` | `{textToSummarize:s,summaryLength:e,focusKeywords:s}` -> D | $0.15 |
| 74 | Story idea generator -> idea set | A | `story-idea-generator` | `{genre:s,numCharacters:i,settingKeywords:s,numIdeas:i}` -> L | $0.10 |
| 75 | Debate topic generator -> age/complexity-adjusted topics | P | `debate-topic-generator` | `{subjectArea:s,complexity:e,numTopics:i}` -> L | $0.10 |
| 76 | Essay outline generator -> paragraph outline | P | `essay-outline-generator` | `{essayTopic:s,essayType:e,numParagraphs:i}` -> D | $0.15 |
| 77 | Decodable sentence creator -> controlled sentences | A | `decodable-sentence-creator` | `{phonicsPattern:s[],numSentences:i,sentenceLength:e,includeSightWords:b}` -> L | $0.10 |
| 78 | Acrostic poem assistant -> acrostic draft | P | `acrostic-poem-assistant` | `{inputWord:s,poemTheme:s,lineStyle:e,rhymeScheme:e}` -> D | $0.10 |
| 79 | Character trait lister -> traits/evidence | P | `character-trait-lister` | `{characterName:s,characterSource:s,customDescription:s,traitCategories:e,numTraits:i,includeExamples:b}` -> L | $0.10 |
| 80 | Setting describer ideas -> setting detail bank | P | `setting-describer-ideas` | `{settingType:e,moodTone:e,numSuggestions:i}` -> L | $0.10 |
| 81 | Compare/contrast word pairer -> transition pairs/notes | P | `compare-contrast-word-pairer` | `{conceptInput:s,numPairs:i,difficultyLevel:e,includeBriefNotes:b}` -> L | $0.10 |
| 82 | Cause/effect sentence starter -> starter set | P | `cause-effect-sentence-starter` | `{relationshipType:e,complexityLevel:e,numStarters:i}` -> L | $0.10 |

### 1.6 Games and oral/creative activities — 5

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 83 | Word-chain game starter -> valid next-word set | P | `word-chain-game-starter` | `{startingWord:s,numSuggestions:i,wordDifficulty:e}` -> L | $0.10 |
| 84 | Word-ladder creator -> transformation ladder/key | P | `word-ladder-creator` | `{startWord:s,endWord:s,maxLength:i,wordDifficulty:e}` -> L | $0.10 |
| 85 | Phonics joke generator -> child-safe joke set | P | `joke-generator-phonics-based` | `{phonicsFocus:s,jokeStyle:e,numJokes:i,targetAgeGroup:e}` -> L | $0.10 |
| 86 | Tongue-twister creator -> sound-focused twisters | P | `tongue-twister-creator` | `{targetSound:s,numTwisters:i,sentenceLength:e,includeAlliterationEmphasis:b}` -> L | $0.10 |
| 87 | Literacy-game idea suggester -> activity plans | P | `literacy-game-idea-suggester` | `{literacySkill:s,targetAgeGroup:e,numSuggestions:i,includeBriefDescription:b}` -> L | $0.10 |

### 1.7 Planning and teacher administration — 2

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 88 | Learning-plan outline creator -> sequenced plan | P | `learning-plan-outline-creator` | `{subject:s,duration:s,learningGoal:s}` -> D | $0.15 |
| 89 | Progress-monitoring note taker -> structured teacher note | P | `progress-monitoring-note-taker` | `{studentName:s,dateOfObservation:s,skillsMastered:s,skillsNeedingPractice:s,specificExamples:s,nextSteps:s,outputFormat:e}` -> R | $0.10 |

The Omo version should make learner identity optional or pseudonymous, prohibit sensitive child data in fixtures/logs, and market the output as a teacher note rather than a clinical record.

### 1.8 Cross-curricular/general utilities — 4

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 90 | Math word-problem explainer -> worked explanation | P | `math-word-problem-explainer` | `{wordProblem:s,gradeLevel:e}` -> D | $0.10 |
| 91 | Historical-event explainer -> leveled overview | P | `historical-event-explainer` | `{eventName:s,detailLevel:e}` -> D | $0.10 |
| 92 | Science-concept explainer -> audience-level explanation | P | `science-concept-explainer` | `{conceptName:s,audienceLevel:e}` -> D | $0.10 |
| 93 | Code-snippet explainer -> code explanation | P | `code-snippet-explainer` | `{codeSnippet:s,programmingLanguage:e}` -> D | $0.10 |

These four still fit the generic Omo structure, but they belong in general Education/Developer categories rather than a Phonics shelf. Their presence is another reason not to call all 93 prompts “phonics tools.”

### 1.9 Illustrated story generation and editing — 3

| # | Tool -> produces | Now | Omo container slug | Strict input sketch -> output | Est. |
| ---: | --- | :---: | --- | --- | ---: |
| 94 | Illustrated decodable story maker -> cover, 6-21 illustrated pages, PDF, thumbnail, editable JSON | G | `illustrated-decodable-story-maker` | `{phonemes:s[],story_idea:s,difficulty_level:e,is_free:b,language_variant:e,curriculum:e,highlight_text:b,printable:b,art_style:e,page_count:i,progressive_highlighting:b}` -> F(PDF+JPEG+JSON) | $2.00 |
| 95 | Phonics story editor -> command or structured operations applied to an owned story, new PDF/thumbnail/JSON | E | `phonics-story-editor` | `{source_artifact_id:s,command:s|operations:o[]}` -> F(PDF+JPEG+JSON) | $0.75 |
| 96 | Story Edit Studio exporter -> deterministic re-render of supplied owned layout JSON | S | `phonics-story-edit-studio` | `{source_artifact_id:s,story_data:o}` -> F(PDF+JPEG+JSON) | $0.30 |

For completeness, the legacy generator accepts `mode`, `phonemes`, `story_idea`, `difficulty_level`, `is_free`, `user_email`, `language_variant`, `curriculum`, `debug_config`, `highlight_text`, `printable`, `art_style`, `page_count`, and `progressive_highlighting`. Legacy edit accepts `mode`, `user_email`, and `edit_config{task_id,command?,operations?}`; Studio's first operation is `regenerate_pdf_from_data` with `story_data`. The Omo schemas intentionally drop `user_email`, debug/resume knobs, public `pdf_url`, and raw object paths, using the authenticated Omo user plus opaque `source_artifact_id`. The current fixtures prove the richer shapes, and the handler returns `pdf_url`, `thumbnail_url`, and `task_id`. [E5]

## 2. The three repeatable patterns

### Pattern A — generator/run: one product contract, one thin container

Every runnable tool gets the proven house bundle, whether its executor is a single LLM call or a PDF pipeline:

```text
containers/<slug>/
  modal_app.py                         protected POST /v1/runs + poll
  container.yaml                      execution/readiness/provider declarations
  schemas/input.json                  strict Draft 2020-12
  schemas/output.json                 strict Draft 2020-12
  prompts/                            only reviewed prompt material
  tests/test_contract.py + cases.json house contract suite
  pricing-report.json                 cost-model SHA, cost, guard, markup, price
  capability-manifest.json            honest capabilities and blockers
  manifest.json + hosted-profile.json generated state
  README.md + source/SKILL.md          human contract and source wrapper
```

That is the shape already proved by `woven-storybook-pipeline` and `facebook-ads-copywriter`: protected ASGI, validate before spawn, `202` submit/poll semantics, fail-closed readiness, strict schemas, five negative cases and nine other checks (14 pytest cases after parameterization), pricing evidence, and capability honesty. [E9]

The 93 prompt adapters are mostly `single_llm` containers using the light existing runtime. They must not share the old `/api/tools` endpoint because it accepts an arbitrary tool name/payload and returns unbounded text. Each gets a recovered strict schema, a server-owned prompt, structured output, negative fixtures, an education evaluation set, and its own price report. [E1-E3]

PDF-capable generators use a new reviewed executor kind, not a hand-edited exception:

```yaml
execution_kind: native_pdf
runtime_template: omo-phonics-pdf@1
result_contract: omo.result/v1
artifacts: [pdf]
```

`packages/skill-to-modal/compiler.py` currently allowlists only `single_llm`; unsupported `complex_external` profiles must carry blockers and cannot become ready. The additive compiler work is to recognize a versioned `runtime_template`, generate the same protected API/tests, and allow `native_pdf`, `llm_pdf`, `image_pdf`, and `private_artifact_edit` only after each adapter has provider, artifact, QA, and pricing implementations. Merely adding a string to the allowlist is not sufficient. [E10]

Today the compiler's image is hardwired to Modal/FastAPI/jsonschema plus optional apt packages and the tool's schemas/prompts; it has no shared Python runtime selector. `host.py` also assumes `profile["live"]` is an LLM, emits an LLM workflow step, and copies its model/token fields into the server catalog. The same additive change must therefore make **both** compiler and host dispatch on reviewed `execution_kind`/`runtime_template`: text profiles retain today's output byte-for-byte; PDF/artifact profiles emit provider-neutral pipeline steps and runtime metadata. The public run-manifest shape (`input_schema`, `output_schema`, `examples`, `price_usd`, `phases`, `ui`) does not change. [E10]

The flagship `phonics-worksheet-generator` is a **97th, new contract**, not hidden inside the current 96. Its already-specified input is grade, focus pattern, activity, page count, difficulty, dialect, print mode, theme and answer-key policy; output is private worksheet PDF, optional key, content report and usage. It stays `chargeable:false` until a real executor exists. [E7]

### Pattern B — content/download: catalog product, no Modal container

Finished CVC packs, readers, posters, games, assessments and bundles are immutable/versioned files. Buying them should not cold-start Modal or create a run. Omo has no production download-only listing type today: `workflow.html` assumes both Buy and Run, `/api/checkout` can create a generic purchase, and the `purchases` record has no account owner, product version, or fulfillment path. [E11-E14]

The minimal **generic**, additive public catalog contract is:

```js
{
  slug: 'cvc-practice-pack-k-1',
  type: 'download',
  priceOwn: 6,
  files: [{
    file_id: 'pack', role: 'primary', filename: 'cvc-practice-pack-v1.zip',
    mime_type: 'application/zip', bytes: 0, sha256: '<64 hex>', version: '1.0.0'
  }]
}
```

The browser-safe entry contains metadata but **no storage object key or durable download URL**. A generated server registry owns `file_id -> private object key`. Existing runnable entries omit `type` and preserve current behavior; `type:'download'` makes `workflow.html` show file/version/license plus one **Buy + download** action, hide the Run card, and keep `run.html` out of the flow. Bundles are the same type with several files or a primary ZIP—no separate product engine.

Fulfillment specification:

1. Existing `/api/checkout` continues to ignore client price and creates the pending purchase from server-owned catalog data.
2. Add nullable `user_id` and non-null/defaulted `product_version` to `purchases`; no new table is necessary. On signed webhook completion, store/claim the verified user or later bind a guest purchase by verified email. Existing rows remain valid.
3. Add authenticated `GET /api/downloads/:slug/:file_id`. It verifies a completed purchase for `user_id` (or a verified-email claim), checks the bought version in the server registry, and returns a short-lived signed artifact response. It never trusts localStorage; `menu-workflows.js` is presentation state only. [E14]
4. Record download audit/limits in ordinary logs initially. Add a ledger table only if support, abuse, or creator royalty requirements prove it necessary.

Static content uses the requested bands: **$2-$8 singles, $15-$40 bundles**. A free sample is still `type:'download'`, price zero, with the same hash/version/provenance controls.

### Pattern C — shared tools: versioned runtime layers and provider adapters

The legacy core is valuable as evidence, not as the deployable unit. It already uses Jinja2 templates, WeasyPrint 64.1, embedded Comic Neue/Lexie Readable fonts, Gemini story/prompt generation, Runware images, Pillow/OpenCV-style image work, boto storage, DB task state and email. Its Dockerfile installs the whole Poetry application, then only `gcc`, `ffmpeg`, and `curl`; its dependency set also includes SQLAlchemy, Postgres, Celery, Clerk, Resend and RunPod. Copying that image 100 times would preserve coupling and rebuild irrelevant services. [E5-E6]

The shared Modal runtime should be layered in this order:

| Layer | Stable contents | Change cadence / reason |
| --- | --- | --- |
| `omo-python@1` | pinned Python/Modal/FastAPI/jsonschema runtime | rare; common to all generated containers |
| `omo-phonics-pdf@1` | native WeasyPrint libraries, WeasyPrint 64.1, Jinja2, Pillow, approved licensed fonts, HTML/CSS renderer, PDF validation/checksum helpers | rare; content-hashed Modal build layer reused by every PDF app |
| `omo-phonics-ai@1` | typed LLM and image-provider interfaces, retry/rate-limit/usage metering, content report/QA hooks; no credentials | controlled; provider implementation changes |
| tool layer | schemas, prompt/template, fixture cases, tiny executor adapter | frequent; ideally declarative, otherwise about 50-150 lines |

`runtime_template: omo-phonics-pdf@1` in the reviewed profile makes the compiler import the central image factory. Heavy `apt_install`/`uv_pip_install`/font layers must be defined before `.add_local_*` tool material so Modal can reuse their identical content hash; tool prompts/templates are the final cheap layer. Do not make a single universal image: text-only adapters stay on `omo-python@1`, while PDF tools use the PDF family. ReportLab is **not** in the inspected core; add it only if deterministic form fields prove a requirement. Use the existing HTML/CSS + WeasyPrint path first and admit Chromium as a separately measured renderer variant if print QA shows a real gap. [E6-E7, E10]

Shared services, all behind generic interfaces:

- **PDF renderer:** one template/component library, font license manifest, page rasterization, clipping/font/openability checks, checksums and answer-key linkage.
- **LLM adapter:** schema-constrained responses, bounded tokens, retry policy, provider usage and model/version in `usage`; no direct provider calls in tool code.
- **Image adapter:** original-asset prompt/provenance, cost cap, semantic/visual QA and retries; no model-specific calls in worksheet code.
- **Artifact plane:** private object keys, owner authorization, malware/type/size validation, signed short-lived delivery and versioning.
- **Education QA:** dialect/phoneme policy, decodability ledger, answer uniqueness, age/grade safety, non-diagnostic claims and educator approval.
- **Secrets:** injected Modal secret references by capability family, not copied into a container or catalog. One Omo Modal proxy-token pair already fronts hosted apps; production provider credentials should be dedicated and least-privilege rather than a different key per tool. [E13]

## 3. Scaling and non-breaking analysis

### 3.1 Catalog and browser scale

The task premise says 24 live listings; the current working tree actually loads **23**: seven `slug` rows in `site/ig-workflows.js` (59,554 raw bytes) and 16 in `site/ig-more.js` (126,160 raw bytes). `site/catalog-100.js` contains 100 rows but no production page references it, so it is not part of the live count. This distinction matters because inventory files are not shipped products. [E11]

The existing browser algorithm is adequate for the first 100:

- `index.html` merges both arrays into an object keyed by slug, creates JSON-LD in one pass, filters/sorts in memory, and renders only 15 cards initially; View more adds 15. `workflow.html` and `run.html` linearly search two arrays for one slug. At 100 records these are trivial O(n) operations and the card DOM remains bounded. [E11-E12]
- The loaded raw catalog is 185,714 bytes, about 8.1 KB per current rich listing. Linear projection to 100 similarly rich rows is about 0.81 MB raw before normal HTTP compression. That is acceptable for the first conversion wave but must be measured, not assumed.

**Decision:** keep one generated catalog/registry file through the first 100 so there is one atomic source and no pagination migration. Add a build budget: warn at 750 KB raw and require a measured split/lazy-manifest decision at 1 MB raw or a material mobile LCP/parse regression. Keep long examples and full schemas in per-slug `run-manifests/`, not in catalog cards. If a split is later needed, split by category behind the same loader; do not change listing shape.

There is one pre-existing contract gap to close generically. `run-input-library.html` and `run-output-library.html` are design/reference pages, not the production renderer. Production `run.html` resolves hidden const, select, boolean, number, URL, email, date, long text, short text and a JSON textarea fallback. It does **not** yet implement the claimed file/tags/pair/slider/markdown/map widgets, and it heuristically finds URLs in generic output instead of normalizing/rendering the complete `omo.result/v1` registry. [E12]

Non-breaking gate: text tools may launch using the already-supported schema subset; array/file/PDF tools wait until the input/output libraries are moved into the existing generic resolver. That work must benefit every listing—no PhonicsMaker component branch.

### 3.2 Worker dispatch and billing scale

No new PhonicsMaker route table is needed. The Worker already imports `HOSTED_MODAL_SKILL_ROWS`, builds a `Map` by slug, validates hosted input, takes price/endpoint/schema/proxy env names from the generated server registry, reserves credits before dispatch, calls the protected Modal `/v1/runs`, polls, validates output, and refunds on failure. `host.py --register` generates the run manifest, Worker registry and marked catalog entry; `--register --check` catches drift. [E10, E13]

**Decision:** keep the generated registry module as the single dispatch map. It is cleaner than a hand-written `CONTAINERS` switch and safer than runtime KV/manifest fetches, which add availability and stale-config failure modes. A hundred small registry records are negligible. Existing legacy hardcoded routes remain untouched; every new Phonics slug uses the generic hosted path.

One compatibility limit must be enforced: the Worker's small validator supports object/array/string/number/boolean, required, enum/const, additional-properties, item counts, length/pattern and numeric bounds—not every Draft 2020-12 keyword. Containers still perform full validation. Until the Worker uses the same validator library, compiler lint must reject hosted input schemas outside that supported subset so an input cannot pass one boundary and mean something different at the other. [E13]

### 3.3 Modal apps, cold starts and shared secrets

One app/container per runnable slug preserves price, isolation, rollback, logs and contract ownership. Keep `min_containers=0` for the long tail; warm only the top five after traffic and latency evidence. A versioned shared image makes builds and image pulls reuse stable layers, but it does not eliminate the first process cold start of 100 separate app identities. Record submit-to-running and submit-to-delivered latency by slug and runtime template; set an SLO only after canaries.

Concurrency must be bounded at three levels: per-container `max_containers`, provider adapter rate limit, and an operational family budget. A sudden classroom batch must receive honest queued/429/503 behavior instead of causing 100 independent apps to stampede a shared LLM or image account. Text tools can use the small image; illustrated story/PDF apps pay the heavier cold-start cost only when called.

The Proxy Token authenticates Worker -> Modal and can remain the shared hosted-workspace pair already encoded by the generated registry. It is not a provider credential. Use separate least-privilege Modal secrets such as `omo-phonics-llm-prod`, `omo-phonics-images-prod` and `omo-artifacts-prod`, referenced only by runtime capability. Do not create 100 copies, and do not reuse PhonicsMaker's database/email credentials. [E5-E6, E13]

### 3.4 Pricing at 100 containers

Every container retains its own `pricing-report.json`, including the SHA of `site/deploy/cost-model.mjs`, provider step breakdown, guarded yield/retry assumptions, display price and chargeable flag. The current model applies 5x markup with a $0.10 floor. A shared runtime does not justify one shared price: story images, long prompts and deterministic text have different costs and accepted-output yields. [E9-E10]

Batch pricing procedure:

1. Benchmark the exact executor/provider/model and accepted-output yield on reviewed cases.
2. Feed measured tokens/images/CPU/egress/retry rates into the common cost model.
3. Regenerate per-slug reports; reject unknown/unpriced steps.
4. Apply the requested run band: $0.10 simple analysis/list, roughly $0.15-$0.50 longer/PDF text generation, $0.30-$0.75 edits, and at most $2.00 for the illustrated story unless the founder explicitly revises the band.
5. `chargeable:false` until price, executor, private artifacts and QA all agree. A price written in this inventory is planning, never billing authority.

### 3.5 Neon and download entitlements

The repository schema already defines `users`, `runs`, `run_requests`, `run_progress`, `credits_ledger`, Stripe event/top-up tables, `purchases`, and `submissions`. Runnable tools require no Phonics table. JSON request/result/artifact fields are already slug-agnostic. This is a source-schema finding, not a claim about live Neon: the hosting runbook says production logs prove `purchases` is absent and the other additive tables are unverified. Phase 4 therefore starts with an authorized, additive migration and table-introspection gate. [E14-E15]

Download products also need no content-specific table. The two additive `purchases` columns specified above (`user_id`, `product_version`) plus a generated private file registry are sufficient for v1 entitlement. This preserves one purchase record per Stripe session and avoids copying the PhonicsMaker user/PDF/task schema. A future creator-royalty or download-event ledger is a generic marketplace decision, not part of this conversion.

### 3.6 Failure containment and review at scale

| Misconfiguration/failure | Required containment |
| --- | --- |
| Missing/invalid input schema or unsupported UI keyword | compile/lint fails; invalid requests fail before spawn or debit |
| Missing provider adapter/secret or unsupported execution kind | `can_submit:false`, `chargeable:false`; protected endpoint returns 503 before spawn |
| Modal endpoint/proxy credential drift | Worker rejects configuration/dispatch; reservation is refunded; no fallback to client prompt |
| Provider returns malformed/unsafe content | output validation or education QA fails; no paid “success,” no mock artifact |
| PDF missing, corrupt, clipped, wrong-page, font-missing or answer/key mismatch | artifact/print QA fails; no signed delivery and no charge settlement |
| Story edit references another user's artifact | artifact ownership check fails before provider call; object key never accepted from client |
| Pricing step unmeasured or cost-model SHA stale | pricing report is non-chargeable; `--register` refuses it |
| Catalog/registry/container drift | `host.py --register --check` fails CI/review; no manual patch-around |
| One slug is broken in production | generated registry can omit/disable that slug; other slugs and legacy routes are unaffected |

The queue already models `queued -> processing -> needs_review -> ready_for_deploy -> ready_for_publish -> deployed`, and deployment is a separate gated action. At 100 tools, process reviewed batches of five to ten, never a single “approve all” commit. Each row must pass: recovered schema/defaults; prompt safety; five or more negative cases; the house 14-case contract suite; tool-specific golden/evaluation cases; provider and artifact canary; measured pricing; catalog/run-manifest review; direct Modal canary; Worker suites; `--register --check`; and, for instructional content, signed educator/dialect/decodability review. [E9-E10, E15]

## 4. Build roadmap

This is sequencing for later authorized build agents; this research run performs none of it. “Sol” means container/compiler engineering and verification. “Luna” means original instructional content/assets/packaging. A human K-2 literacy reviewer is a release gate, not a replaceable agent role.

| Phase | Ordered scope | Agents and tooling | Exit gates | Estimated effort |
| --- | --- | --- | --- | --- |
| **1 — five generator canaries** | 1. new CVC/skill **Phonics Worksheet Generator**; 2. **Illustrated Decodable Story Maker**; 3. **Phonics Assessment/MC Quiz Generator**; 4. **Decodable Sentence Creator**; 5. **Word Search Puzzle Maker** | Three Sol lanes: shared runtime/compiler+artifact plane; worksheet/assessment/sentence/puzzle adapters; story port. One Sol integrator owns schemas, house tests and registry. One Luna lane supplies only reviewed internal fixtures/templates/assets. | Shared `omo-phonics-pdf@1`; generic artifact/result renderer; all five house bundles; private artifacts; educator goldens; measured price; `chargeable:false` until direct and Worker canaries. No deploy without separate approval. | **One focused week** for reviewable internal canaries with 3 parallel Sol lanes: about 70-100 combined agent/engineering hours plus 12-20 educator/QA hours. If the generic artifact plane is not already available, public readiness moves out; do not fake the week by weakening gates. |
| **2 — 20 TPT-style content packs** | Author the exact download products below in order; keep unpublished/unlisted until Phase 4 fulfillment exists. | Four Luna lanes after one shared manifest/template/style lock; asset manifest and approved image adapter; HTML/CSS -> PDF; raster/contact-sheet/print QA. One educator reviewer; one Sol QA/tooling owner only. | Original/provenance-safe content; answer keys from same manifest; color/blackline; hashes/version/license; technical + educator signoff; price and exact contents. | 140-190 Luna hours plus 24-40 educator/QA hours; roughly 2-4 weeks depending revision yield. |
| **3 — remaining long tail (92 current contracts; 75+ promised)** | Batch 1 remaining active tools/Reading Error Coach; Batch 2 foundational phonics; Batch 3 reading/printables/games; Batch 4 grammar/writing/admin; Batch 5 cross-curricular and two story editors. Convert all to house shape, but publish only products that pass demand and quality review. | Four Sol batch lanes using the compiler and light/PDF templates; Luna only for educational fixtures; one integrator runs five-to-ten-tool review batches and drift checks. | Per-tool strict schemas, structured outputs, evals, 14-case suite, pricing SHA, catalog decision, provider canary. Cross-curricular tools categorized outside Phonics. Editors additionally pass ownership/private-artifact tests. | 3-5 weeks after Phase 1: about 120-200 Sol hours, 40-80 Luna/educator fixture hours, plus story-editor integration. |
| **4 — download products and bundles** | Implement generic `type:'download'`; entitlement/delivery; publish approved Phase 2 singles; then CVC/short-vowel, blends/digraphs, advanced-vowels, games/cards/posters and five-flagship bundles. | Two Sol lanes for Worker/Neon/frontend generic contract and security tests; two Luna lanes for versioned ZIP/start-here/TOC/previews; educator and commerce review. | Signed webhook purchase -> owned entitlement -> short-lived download; replay/foreign-user/version/hash tests; no localStorage trust; real component totals/savings; support/refund/license copy; existing runnable listings regression-tested. | 5-8 Sol days (roughly 60-90 hours) plus 40-70 Luna/QA hours. |

The Phase 3 arithmetic is intentional: Phase 1 converts four members of the current 96 plus one new worksheet contract, leaving **92 current contracts**. “75+” is therefore a floor, not a euphemism for dropping the remaining tools.

### Phase 2's exact 20-pack order and target price

This is the demand/SEO order supported by the marketplace audit: CVC and word families first, then blends/digraphs, controlled readers, heart words, assessment, and long-vowel coverage. Prices remain inside the requested bands. [E8]

| Order | Original content pack | Price |
| ---: | --- | ---: |
| 1 | CVC Practice Pack, PreK-K | $6 |
| 2 | Digraphs & Blends Practice, K-2 | $8 |
| 3 | Phonics Assessment & Progress Monitoring, K-2 | $7 |
| 4 | High-Frequency / Heart-Word Practice, K-1 | $8 |
| 5 | Controlled Decodable Reader Set, K-1 | $8 single set; bundle later |
| 6 | Short A Word Families | $3 |
| 7 | Short E Word Families | $3 |
| 8 | Short I Word Families | $3 |
| 9 | Short O Word Families | $3 |
| 10 | Short U Word Families | $3 |
| 11 | Mixed CVC Fluency & Sentences | $5 |
| 12 | L-Blends Word Work | $4 |
| 13 | R-Blends Word Work | $4 |
| 14 | S-Blends Word Work | $4 |
| 15 | Ending Blends | $4 |
| 16 | CH & SH Digraphs | $4 |
| 17 | TH, WH & PH Digraphs | $4 |
| 18 | CVCe / Silent-E Long Vowels | $5 |
| 19 | AI & AY Vowel Teams | $4 |
| 20 | EE & EA Vowel Teams | $4 |

Bundle targets after every component independently passes: five-flagship collection **$35**; short-vowel five-pack **$12**; blends/digraphs **$15-$25** based on final components; broader library stays within **$15-$40** unless the founder changes the band. Do not advertise a bundle before its files and real à-la-carte total exist.

## 5. Clean-code conversion rule

> **We convert `SKILL.md` and other AI wrappers into Omo's repeatable structure. We do not bolt the PhonicsMaker app onto Omo.**

Concretely, each runnable product is: **reviewed source wrapper + strict schemas + thin generated container + prompts/templates + contract/evaluation cases + capability manifest + price report + generic run/catalog manifest**. PDF/LLM/image/storage mechanics live once in shared runtime/provider modules. The Omo Worker knows only the generic generated registry, and the Omo browser knows only catalog/run/result/download contracts.

### Top five anti-patterns to prohibit

1. **Copying the legacy FastAPI/RunPod application wholesale.** That drags its DB task service, user email lookup, storage paths, Celery, Clerk, Resend and debug/mock branches into every container.
2. **Adding PhonicsMaker routes or slug switches to `worker.js`.** No `/api/phonics/*`, 96-entry `if` chain, client-supplied endpoint/provider/prompt, or manual price map; use `host.py`'s generated registry.
3. **Importing the PhonicsMaker Next.js toolkit or Studio into Omo.** Forms use schema-driven `run.html`; results use the generic result renderer. Studio interactivity is not smuggled in as a custom Omo page—the container only edits/exports owned artifacts.
4. **Sharing the PhonicsMaker database, user IDs, email workflow or public artifact URLs.** Omo auth, run ledger, purchase entitlement and private artifact plane own those concerns; migrations, if any, are a separate project.
5. **Cloning dependencies/secrets or returning mock success.** Heavy PDF/font/provider layers are versioned once; secrets are injected by capability; missing provider/artifact/QA/pricing means 503/non-chargeable, never a placeholder paid PDF.

Also avoid treating a prompt name as product readiness, asking image models to render instructional text, letting each tool invent its own result envelope, patching a rendered PDF instead of its source manifest, or auto-publishing 100 generated listings without batch review.

## 6. Open founder decisions

1. **Download product type:** approve `type:'download'` as a generic Omo product with buy-once versioned files, or keep Omo runnable-only? **Recommended:** approve it; static teacher packs have different economics and should not pretend to be runs.
2. **Production LLM provider/account:** which dedicated metered provider and credential owns 100-container traffic? **Recommended:** a production API account/secret with budget, rate limits and usage terms—not a Codex subscription credential. Use `OPENCODE_GO_API_KEY` only if its production SLA, model, metering and terms are explicitly approved.
3. **Worksheet image generation:** keep the existing Runware adapter, use ChatGPT Images/API, or another provider? **Recommended:** benchmark Runware against one approved API alternative on cost, semantic accuracy, text/logo failure and accepted-output yield; select through the shared adapter. Subscription UI automation is not a production provider.
4. **Existing PhonicsMaker users ($5k MRR / 4.5k subscribers):** migrate identities/purchases into Omo or remain separate? **Recommended default for this conversion:** remain separate; account/purchase/data-consent migration needs its own legal, reconciliation, rollback and support plan.
5. **Price confirmation:** confirm $0.10-$2.00 per generator run, $2-$8 content singles and $15-$40 bundles, including whether the image-heavy illustrated story must stay at $2.00 or may exceed it after measured cost/yield.
6. **Luna schedule/budget:** approve the Phase 2/4 ranges, number of parallel Luna lanes, educator-review budget, dialect (`en-US` default in the TPT plan), and whether 20 packs are internal-ready or expected to publish on a dated launch.

## 7. Evidence and audit trail

No `.env`, key, token, password or credential file was opened. File counts below exclude `.git`, `node_modules`, `.next`, virtual environments and Python caches. The audit covered route/handler surfaces, form configs/prompts, core services/templates/static/fonts/tests/fixtures/docs, and the loose scripts/docs—not merely filenames.

### E1 — all 93 prompt adapters and exact payload reads

- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/prompts.ts:5-4490` — one top-level `toolPromptMap`; 93 unique keys. A local read-only parser enumerated every key and every `payload.<field>`/destructured field used for the inventory.
- Four prompt keys have no corresponding config definition: `code-snippet-explainer`, `historical-event-explainer`, `math-word-problem-explainer`, and `science-concept-explainer`; this is still an invocation surface, not a UI.

### E2 — active versus commented UI contracts

- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts:19-556` — nine active configs, field widgets/options/defaults/bounds.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/toolConfig.ts:557-end` — 80 commented config definitions; with the four prompt-only/no-config keys, 84 lack active forms.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/[lang]/dashboard/toolkit/_components/toolkit-display.tsx:27-44` — maps `toolConfigs`, maps `customTools`, concatenates them.

### E3 — generic current toolkit invocation

- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/[lang]/dashboard/toolkit/_components/toolkit-form.tsx:56-95` — selected config and `POST /api/tools` with `{tool,payload}`.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/tools/route.ts:5-27` — chooses prompt by client `tool`, invokes `gemini-2.0-flash`, returns `{result,description}`.

### E4 — custom story card is an alias/front door

- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/shared/customTools.ts:20-31` — exactly one `custom-story-generator`, linking to `/dashboard`.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/public/images/tools/` — 92 PNGs; assets are not executable tools and do not determine the count.

### E5 — core generate/edit/Studio contracts

- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/runpod_handler.py:25-68,132-157,171-226,343` — one RunPod handler, generate/edit dispatch, generate inputs/output, structured Studio branch, serverless start.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/test_input_generate.json`, `test_input_edit.json`, `test_input_edit_studio.json`, `test_input.json`, `test_input_debug.json` — golden legacy input shapes.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-web/src/app/api/generate-pdf/route.ts`, `src/app/api/edit-pdf/route.ts`, `src/app/api/studio/regenerate-pdf/route.ts:47` — web-to-RunPod routes; Studio sends `regenerate_pdf_from_data`.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/tasks/story_tasks.py:312-394` — supplied-story-data PDF regeneration/upload.

### E6 — PDF, AI, assets and legacy coupling

- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/pyproject.toml:20-45` — Jinja2, WeasyPrint 64.1, Gemini, Runware, imaging, boto, DB/email/RunPod dependencies; no ReportLab.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/Dockerfile:1-25` — full Poetry app copy/install plus `gcc`, `ffmpeg`, `curl`.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/phonics_maker/pdf_generation/pdf_generator.py`, `html_renderer.py:24`, `image_processor.py`; `/templates/*.html`; `/static/fonts/*` — HTML/Jinja/WeasyPrint renderer and bundled font/image path.
- `/Users/yifan/phonicsmaker-local/phonicsmaker-core/app/core/ai/ai_config.py:25-26`, `app/phonics_maker/story_generation/story_service.py`, `app/phonics_maker/image_generation/image_service.py` — Runware/Gemini models and story/image calls.

### E7 — prior Phonics/Omo contract analysis

- `research/phonicsmaker-modal-plan.md:20-185` — core limitations, visible nine, 84 prompt-only list, core workflow evidence.
- `research/phonicsmaker-modal-plan.md:209-405` — proposed worksheet/coach/story/editor contracts, artifact schemas and honest execution blockers.
- The worksheet is a specification in the marketplace worktree, not an executor found in the supplied core.

### E8 — loose repository and TPT content evidence

- `/Users/yifan/phonicsmaker/CIM-features-inventory.md` and 37 other Markdown documents plus nine Python scripts — diligence, metrics, sale and data-room operations; static claims do not prove callable education tools.
- `research/tpt-phonics-plan.md:1-20,101-230` — first five priorities and demand/price taxonomy.
- `research/tpt-phonics-plan.md` Phase 1/2 tables and `§5` — exact pack structures/prices, 25-single source backlog, Luna manifest/render/QA process and download-first economics.

### E9 — proved house container contract

- `containers/woven-storybook-pipeline/` and `containers/facebook-ads-copywriter/` — complete `modal_app.py`, YAML, strict schemas, prompts, tests/cases, pricing/capability/hosted manifests and README pattern.
- Both `tests/test_contract.py:44-128` contain nine test functions; `cases.json` contains five negative inputs, so pytest collects 14 contract checks.
- `site/deploy/cost-model.mjs:34-36,81` — 5x markup and $0.10 floor.

### E10 — compiler, registration and fail-closed limits

- `packages/skill-to-modal/compiler.py:25,231-255,438-447,470-545,868-932` — only `single_llm` allowlisted; LLM-specific generated constants; hardwired image packages/local layers; protected app; blocker/readiness/chargeability enforcement.
- `tools/host-skill/host.py:96-225,251-319` — refuses blocked/non-chargeable registration; currently assumes `profile["live"]` LLM fields while generating run manifest/catalog/runtime registry; `--register --check`.
- `research/hosting-runbook.md:62-185,245-297` — queue, direct/Worker/billing gates, unsupported media/artifact failure and drift checks.

### E11 — live catalog, checkout and lack of download type

- `site/ig-workflows.js` — seven slugs, 59,554 bytes; `site/ig-more.js` — 16 slugs, 126,160 bytes, measured with `rg '^ *slug:'` and `wc -c` on 2026-08-13.
- `site/index.html:1040-1105,1201-1228` — only those two files are loaded/merged; O(n) filter/sort; 15-card render increments.
- `site/workflow.html:759-793,883,1096,1134-1150` — two-array lookup and assumed Buy/Run offering.
- `site/catalog-100.js` has 100 slug rows but `rg 'catalog-100.js' site --glob '!catalog-100.js'` returns no consumer.

### E12 — production run UI versus design libraries

- `site/run.html:473-705,705-850,869-932,1416-1504` — two catalog arrays, per-slug manifest, actual input resolver, generic artifact URL collection and `/api/run` call.
- `site/run-input-library.html` — component design/proposal; not loaded by `run.html`.
- `site/run-output-library.html:512-736` — 12 output examples and proposed `omo.result/v1`; not loaded by `run.html`.

### E13 — generic Worker dispatch

- `site/deploy/worker.js:65,154-193,270-271,430-740` — generated hosted rows -> `Map`, generic routes, server-owned listing, hosted schema validation, reserve-before-dispatch and protected endpoint credentials.
- `site/deploy/worker.js:644-694` — supported validation keyword subset.
- `site/deploy/worker.js:700-930,1015-1235` — hosted submit/poll/result handling, output checks and fail/refund path.

### E14 — Neon and current purchase fulfillment boundary

- `site/deploy/schema.sql:9-219` — generic users/runs/requests/progress/credits/Stripe/purchases/submissions schema.
- `site/deploy/schema.sql:166-190` — purchase columns are session, event, slug/name/amount/currency/email/state/timestamps; no `user_id`, version or file entitlement.
- `site/deploy/worker.js:2700-2775` — checkout purchase insert, lookup and signed-webhook completion; no download delivery route.
- `site/menu-workflows.js:6-76` — localStorage purchase state, unsuitable as authorization evidence.

### E15 — submission review states

- `tools/host-skill/process-submissions.py:60-121,219-320` — `needs_review`, `ready_for_deploy`, `ready_for_publish`, explicit `--mark-deployed` transition.
- `research/hosting-runbook.md:1-15,76-121` — live schema is unproven/`purchases` absent; review/profile gates and deploy/publish distinction.

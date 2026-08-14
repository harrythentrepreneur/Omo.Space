# One-shot builder rounds (append-only)

Each entry distinguishes real provider execution from offline replay. Offline
replay uses the exact 27 provider responses captured by Brief V; it verifies
the generated repair layer but does not prove how a fresh provider call behaves.

## 2026-08-14 — baseline (real provider, inherited evidence)

- Mode: real provider-backed generated runtimes, before this repair.
- Result: 0/27 schema-valid (0.0%).
- Failure: every tool raised `LLM_INVALID_OUTPUT`; the runtime discarded the
  provider content and collapsed the schema diff.
- Next generator change: transmit the exact reduced schema, normalize the
  first response, retry once with sanitized validation paths, and preserve
  aggregate usage.


## 2026-08-14 — repair round 1

- Mode: offline replay of the exact 27 captured provider responses.
- Result: 7/27 schema-valid after local repair (25.9%).
- Passed: decodable-sentence-creator 3/3, phoneme-counter 3/3,
  phonics-rule-explainer 1/3.
- Main remaining shapes: missing nested fields, unfilled prompt echoes,
  string/object aliases, and one malformed JSON response.
- Generator change: add prompt-context echoes, schema-only required defaults,
  bounded strings, and generic nested aliases.

## 2026-08-14 — repair round 2

- Mode: offline replay of the exact 27 captured provider responses.
- Result: 19/27 schema-valid after local repair (70.4%).
- Main remaining shapes: sentence target words, invalid digraph type values,
  malformed JSON, and syllable alias collision.
- Generator change: penalize type-incompatible alias matches, derive cautious
  required prose/notes from prompt context, derive enum/count fields, and use
  schema maximums while stripping extras.

## 2026-08-14 — repair round 3

- Mode: offline replay of the exact 27 captured provider responses.
- Result: 24/27 schema-valid after local repair (88.9%).
- Remaining: decodable-sentence-creator case 2 missing nested target words;
  digraph-spotter case 3 returned `all` where each occurrence requires a
  consonant/vowel type; phonics-list-generator case 2 was malformed JSON.
- Generator change: make enum repair precede prompt alias reuse and derive
  per-occurrence digraph type from the repaired text.

## 2026-08-14 — repair round 4

- Mode: offline replay of the exact 27 captured provider responses.
- Result: 25/27 schema-valid after local repair (92.6%); 22/27 also pass the
  builder's lightweight semantic invariants (81.5%).
- Per tool: decodable-sentence-creator 2/3; digraph-spotter 3/3;
  grapheme-to-phoneme-converter 3/3; phoneme-counter 3/3;
  phonics-list-generator 2/3; phonics-reading-error-coach 3/3;
  phonics-rule-explainer 3/3; story-idea-generator 3/3;
  syllable-splitter-and-counter 3/3.
- Remaining schema cases: one malformed JSON response and one response missing
  nested `target_words`. Both now enter the single error-driven corrective
  retry; neither can be proven resolved without fresh provider calls.
- Fresh real-run status: blocked. The canonical workspace rule forbids loading
  or using credential files without Harry's explicit, specific permission; the
  attempted low-cost endpoint probe was rejected by the execution approval
  boundary. No workaround was attempted.

## 2026-08-15 — fresh provider acceptance gate (Brief AG)

- Mode: fresh provider-backed execution of regenerated 0.2.0 runtimes.
- Inputs: exact 27 teacher cases preserved by Brief V in /tmp/run_bread_butter_parta.py.
- Result: 0/27 schema-valid; 0/27 passed the documented lightweight semantic checks.
- Exact failure: all 27 calls raised ProviderCallError:LLM_HTTP_400; the provider rejected strict json_schema requests before returning a completion.
- Successful-run provider cost available from wrappers: USD 0.00000000. Failed runtimes record cost as unavailable.

| Tool / case | Input | Schema | Semantic | Detail | Calls | Cost USD |
|---|---|---:|---:|---|---:|---:|
| decodable-sentence-creator #1 | {"dialect":"en-US","include_sight_words":true,"num_sentences":3,"phonics_patterns":["cvc","sh_digraph"],"sentence_length":"short"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| decodable-sentence-creator #2 | {"dialect":"en-GB","include_sight_words":true,"num_sentences":2,"phonics_patterns":["long_a","ai_vowel_team"],"sentence_length":"medium"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| decodable-sentence-creator #3 | {"dialect":"en-AU","include_sight_words":false,"num_sentences":4,"phonics_patterns":["ccvc","cvcc","ch_digraph","th_digraph"],"sentence_length":"short"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| digraph-spotter #1 | {"dialect":"en-US","digraph_type":"consonant","include_explanations":true,"text":"The chick and the sheep sat by the shed."} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| digraph-spotter #2 | {"dialect":"en-GB","digraph_type":"vowel","include_explanations":false,"text":"A green boat sailed in the rain."} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| digraph-spotter #3 | {"dialect":"en-AU","digraph_type":"all","include_explanations":true,"text":"Which whale swam through the white foam?"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| grapheme-to-phoneme-converter #1 | {"dialect":"en-US","include_example_words":true,"include_rules_explanation":true,"text":"ship"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| grapheme-to-phoneme-converter #2 | {"dialect":"en-GB","include_example_words":true,"include_rules_explanation":true,"text":"thought"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| grapheme-to-phoneme-converter #3 | {"dialect":"en-AU","include_example_words":false,"include_rules_explanation":false,"text":"choir"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phoneme-counter #1 | {"dialect":"en-US","show_transcription":true,"word":"ship"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phoneme-counter #2 | {"dialect":"en-GB","show_transcription":true,"word":"elephant"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phoneme-counter #3 | {"dialect":"en-AU","show_transcription":false,"word":"thought"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-list-generator #1 | {"dialect":"en-US","difficulty_level":"beginner","phonemes":["ch","sh"],"topic":"farm animals","word_count":8} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-list-generator #2 | {"dialect":"en-GB","difficulty_level":"intermediate","phonemes":["ai","ay"],"topic":"outdoor play","word_count":10} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-list-generator #3 | {"dialect":"en-AU","difficulty_level":"beginner","phonemes":["th","ee"],"topic":"animals and nature","word_count":6} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-reading-error-coach #1 | {"detail":"teacher","dialect":"en-US","include_practice":true,"learner_stage":"developing","misread_word":"lap","target_word":"lamp"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-reading-error-coach #2 | {"detail":"brief","dialect":"en-GB","include_practice":true,"learner_stage":"early","misread_word":"sip","target_word":"ship"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-reading-error-coach #3 | {"detail":"teacher","dialect":"en-AU","include_practice":false,"learner_stage":"consolidating","misread_word":"got","target_word":"goat"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-rule-explainer #1 | {"dialect":"en-US","num_examples":3,"phonics_rule":"silent_e","target_audience":"early_reader"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-rule-explainer #2 | {"dialect":"en-GB","num_examples":5,"phonics_rule":"c_rules","target_audience":"teacher_parent"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-rule-explainer #3 | {"dialect":"en-AU","num_examples":4,"phonics_rule":"r_controlled_vowels","target_audience":"elementary"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| story-idea-generator #1 | {"age_band":"8-10","genre":"gentle mystery","num_characters":2,"num_ideas":3,"setting_keywords":"school garden"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| story-idea-generator #2 | {"age_band":"5-7","genre":"fantasy adventure","num_characters":3,"num_ideas":2,"setting_keywords":"underwater library"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| story-idea-generator #3 | {"age_band":"11-13","genre":"science fiction","num_characters":1,"num_ideas":2,"setting_keywords":"Moon greenhouse"} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| syllable-splitter-and-counter #1 | {"dialect":"en-US","notation":"hyphen","words":["elephant","paper","cat"]} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| syllable-splitter-and-counter #2 | {"dialect":"en-GB","notation":"dots","words":["family","chocolate","camera"]} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| syllable-splitter-and-counter #3 | {"dialect":"en-AU","notation":"hyphen","words":["fire","poem","comfortable"]} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |

### Per-tool score

| Tool | Schema | Semantic |
|---|---:|---:|
| decodable-sentence-creator | 0/3 | 0/3 |
| digraph-spotter | 0/3 | 0/3 |
| grapheme-to-phoneme-converter | 0/3 | 0/3 |
| phoneme-counter | 0/3 | 0/3 |
| phonics-list-generator | 0/3 | 0/3 |
| phonics-reading-error-coach | 0/3 | 0/3 |
| phonics-rule-explainer | 0/3 | 0/3 |
| story-idea-generator | 0/3 | 0/3 |
| syllable-splitter-and-counter | 0/3 | 0/3 |

- Fresh-provider threshold: FAIL (0/27 schema-valid; every tool semantic >=1: no).

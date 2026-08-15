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

## 2026-08-15 — Gate 1R response-format compatibility probe

- Mode: two fresh, intentionally tiny OpenCode Go calls using
  `deepseek-v4-flash`; the same complete one-field JSON Schema was embedded in
  each system prompt. Credential values and response content were neither
  printed nor written.
- `response_format: {"type":"json_object"}`: HTTP 200, usable JSON object,
  exact schema match, 80 prompt tokens + 5 completion tokens, estimated cost
  USD 0.00001330.
- No `response_format` field: HTTP 200, usable JSON object, exact schema match,
  59 prompt tokens + 5 completion tokens, estimated cost USD 0.00001036.
- Probe total: 2 calls, estimated provider cost USD 0.00002366.
- Decision: generated runtimes will use the proven `json_object` format while
  retaining the full reduced schema in the prompt, local schema repair,
  validation diffs, and one bounded corrective retry.

## 2026-08-15 — Gate 1R fresh provider acceptance gate

- Mode: fresh provider-backed execution of regenerated 0.2.1 runtimes using
  the provider-compatible `json_object` response format and full reduced schema
  in the prompt.
- Inputs: the exact 27 teacher cases preserved by Brief V in
  `/tmp/run_bread_butter_parta.py`; no case was added, removed, or changed.
- Hosted proxy preflight: authenticated `GET /openapi.json` returned HTTP 200
  for both deployed Omo apps (`cognition-woven-storybook-pipeline` and
  `cognition-customer-feedback-theme-finder`). The proxy pair was loaded only
  into the child process environment and was not printed or written.
- Result: 27/27 schema-valid; 18/27 passed the documented lightweight semantic
  checks.
- Successful-run provider cost from wrappers: USD 0.00478016.

| Tool / case | Input | Schema | Semantic | Detail | Calls | Cost USD |
|---|---|---:|---:|---|---:|---:|
| decodable-sentence-creator #1 | {"dialect":"en-US","include_sight_words":true,"num_sentences":3,"phonics_patterns":["cvc","sh_digraph"],"sentence_length":"short"} | PASS | PASS | sane for requested input | 1 | 0.00012180 |
| decodable-sentence-creator #2 | {"dialect":"en-GB","include_sight_words":true,"num_sentences":2,"phonics_patterns":["long_a","ai_vowel_team"],"sentence_length":"medium"} | PASS | PASS | sane for requested input | 1 | 0.00011550 |
| decodable-sentence-creator #3 | {"dialect":"en-AU","include_sight_words":false,"num_sentences":4,"phonics_patterns":["ccvc","cvcc","ch_digraph","th_digraph"],"sentence_length":"short"} | PASS | FAIL | sight words returned when disabled; target word misses requested patterns | 1 | 0.00015932 |
| digraph-spotter #1 | {"dialect":"en-US","digraph_type":"consonant","include_explanations":true,"text":"The chick and the sheep sat by the shed."} | PASS | FAIL | span mismatch | 1 | 0.00016198 |
| digraph-spotter #2 | {"dialect":"en-GB","digraph_type":"vowel","include_explanations":false,"text":"A green boat sailed in the rain."} | PASS | FAIL | span mismatch | 1 | 0.00011004 |
| digraph-spotter #3 | {"dialect":"en-AU","digraph_type":"all","include_explanations":true,"text":"Which whale swam through the white foam?"} | PASS | FAIL | span mismatch; too few real digraphs | 2 | 0.00071988 |
| grapheme-to-phoneme-converter #1 | {"dialect":"en-US","include_example_words":true,"include_rules_explanation":true,"text":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00009366 |
| grapheme-to-phoneme-converter #2 | {"dialect":"en-GB","include_example_words":true,"include_rules_explanation":true,"text":"thought"} | PASS | PASS | sane for requested input | 1 | 0.00010556 |
| grapheme-to-phoneme-converter #3 | {"dialect":"en-AU","include_example_words":false,"include_rules_explanation":false,"text":"choir"} | PASS | PASS | sane for requested input | 1 | 0.00009184 |
| phoneme-counter #1 | {"dialect":"en-US","show_transcription":true,"word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00007238 |
| phoneme-counter #2 | {"dialect":"en-GB","show_transcription":true,"word":"elephant"} | PASS | PASS | sane for requested input | 1 | 0.00009786 |
| phoneme-counter #3 | {"dialect":"en-AU","show_transcription":false,"word":"thought"} | PASS | FAIL | IPA returned when disabled | 1 | 0.00008764 |
| phonics-list-generator #1 | {"dialect":"en-US","difficulty_level":"beginner","phonemes":["ch","sh"],"topic":"farm animals","word_count":8} | PASS | PASS | sane for requested input | 1 | 0.00019810 |
| phonics-list-generator #2 | {"dialect":"en-GB","difficulty_level":"intermediate","phonemes":["ai","ay"],"topic":"outdoor play","word_count":10} | PASS | FAIL | matched phoneme absent from word | 2 | 0.00053200 |
| phonics-list-generator #3 | {"dialect":"en-AU","difficulty_level":"beginner","phonemes":["th","ee"],"topic":"animals and nature","word_count":6} | PASS | FAIL | matched phoneme absent from word; preserved-evidence weak or off-topic word | 1 | 0.00018340 |
| phonics-reading-error-coach #1 | {"detail":"teacher","dialect":"en-US","include_practice":true,"learner_stage":"developing","misread_word":"lap","target_word":"lamp"} | PASS | PASS | sane for requested input | 1 | 0.00014350 |
| phonics-reading-error-coach #2 | {"detail":"brief","dialect":"en-GB","include_practice":true,"learner_stage":"early","misread_word":"sip","target_word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00012502 |
| phonics-reading-error-coach #3 | {"detail":"teacher","dialect":"en-AU","include_practice":false,"learner_stage":"consolidating","misread_word":"got","target_word":"goat"} | PASS | PASS | sane for requested input | 1 | 0.00011858 |
| phonics-rule-explainer #1 | {"dialect":"en-US","num_examples":3,"phonics_rule":"silent_e","target_audience":"early_reader"} | PASS | PASS | sane for requested input | 1 | 0.00014462 |
| phonics-rule-explainer #2 | {"dialect":"en-GB","num_examples":5,"phonics_rule":"c_rules","target_audience":"teacher_parent"} | PASS | PASS | sane for requested input | 1 | 0.00020678 |
| phonics-rule-explainer #3 | {"dialect":"en-AU","num_examples":4,"phonics_rule":"r_controlled_vowels","target_audience":"elementary"} | PASS | PASS | sane for requested input | 1 | 0.00017766 |
| story-idea-generator #1 | {"age_band":"8-10","genre":"gentle mystery","num_characters":2,"num_ideas":3,"setting_keywords":"school garden"} | PASS | PASS | sane for requested input | 1 | 0.00025802 |
| story-idea-generator #2 | {"age_band":"5-7","genre":"fantasy adventure","num_characters":3,"num_ideas":2,"setting_keywords":"underwater library"} | PASS | PASS | sane for requested input | 1 | 0.00024472 |
| story-idea-generator #3 | {"age_band":"11-13","genre":"science fiction","num_characters":1,"num_ideas":2,"setting_keywords":"Moon greenhouse"} | PASS | PASS | sane for requested input | 1 | 0.00017136 |
| syllable-splitter-and-counter #1 | {"dialect":"en-US","notation":"hyphen","words":["elephant","paper","cat"]} | PASS | PASS | sane for requested input | 1 | 0.00009548 |
| syllable-splitter-and-counter #2 | {"dialect":"en-GB","notation":"dots","words":["family","chocolate","camera"]} | PASS | FAIL | wrong notation | 1 | 0.00012628 |
| syllable-splitter-and-counter #3 | {"dialect":"en-AU","notation":"hyphen","words":["fire","poem","comfortable"]} | PASS | FAIL | spelling not preserved | 1 | 0.00011718 |

### Per-tool score

| Tool | Schema | Semantic |
|---|---:|---:|
| decodable-sentence-creator | 3/3 | 2/3 |
| digraph-spotter | 3/3 | 0/3 |
| grapheme-to-phoneme-converter | 3/3 | 3/3 |
| phoneme-counter | 3/3 | 2/3 |
| phonics-list-generator | 3/3 | 1/3 |
| phonics-reading-error-coach | 3/3 | 3/3 |
| phonics-rule-explainer | 3/3 | 3/3 |
| story-idea-generator | 3/3 | 3/3 |
| syllable-splitter-and-counter | 3/3 | 1/3 |

- Fresh-provider threshold: FAIL (27/27 schema-valid; every tool semantic >=1:
  no, because digraph-spotter scored 0/3).
- Exact blocking failures: digraph case 1 duplicated `ch` at `[4,6)` and labeled
  source `[16,18)` as both `ch` and `sh`; case 2 returned mostly word-relative,
  off-by-one spans instead of absolute source spans; case 3 reused word-relative
  starts (`[0,2)` for multiple words and `[1,3)` for `foam`) and returned only
  four occurrences where the gate requires at least five real digraphs.
- Next hypothesis: add a deterministic digraph occurrence normalizer that scans
  the original source string for the reviewed consonant/vowel digraph sets,
  derives absolute spans and containing words, filters by the requested type,
  deduplicates exact occurrences, and preserves provider prose only as optional
  explanation. Add the same span/coverage semantic diff before the single retry.
  Do not deploy until this change clears the unchanged 27-case gate.

## 2026-08-15 — Gate 1R2 final semantic-normalizer rerun (Brief AL)

- Mode: fresh provider-backed execution of regenerated 0.2.2 runtimes.
- Inputs: exact 27 teacher cases preserved by Brief V in
  `/tmp/run_bread_butter_parta.py`; no case was added, removed, or changed.
- Hosted proxy preflight: PASS. Authenticated `GET /openapi.json` returned HTTP
  200 for both deployed Omo apps (`cognition-woven-storybook-pipeline` and
  `cognition-customer-feedback-theme-finder`). The proxy pair was loaded only
  into the child environment and was not printed or written.
- Result: 27/27 schema-valid; 23/27 passed the documented lightweight semantic
  checks. Every tool earned at least one semantic pass, but the required total
  is at least 24/27.
- Successful-run provider cost from wrappers: USD 0.00491694.

| Tool / case | Input | Schema | Semantic | Detail | Calls | Cost USD |
|---|---|---:|---:|---|---:|---:|
| decodable-sentence-creator #1 | {"dialect":"en-US","include_sight_words":true,"num_sentences":3,"phonics_patterns":["cvc","sh_digraph"],"sentence_length":"short"} | PASS | PASS | sane for requested input | 1 | 0.00011522 |
| decodable-sentence-creator #2 | {"dialect":"en-GB","include_sight_words":true,"num_sentences":2,"phonics_patterns":["long_a","ai_vowel_team"],"sentence_length":"medium"} | PASS | FAIL | target word misses requested patterns | 1 | 0.00011480 |
| decodable-sentence-creator #3 | {"dialect":"en-AU","include_sight_words":false,"num_sentences":4,"phonics_patterns":["ccvc","cvcc","ch_digraph","th_digraph"],"sentence_length":"short"} | PASS | PASS | sane for requested input | 1 | 0.00014266 |
| digraph-spotter #1 | {"dialect":"en-US","digraph_type":"consonant","include_explanations":true,"text":"The chick and the sheep sat by the shed."} | PASS | PASS | sane for requested input | 1 | 0.00014182 |
| digraph-spotter #2 | {"dialect":"en-GB","digraph_type":"vowel","include_explanations":false,"text":"A green boat sailed in the rain."} | PASS | PASS | sane for requested input | 1 | 0.00010248 |
| digraph-spotter #3 | {"dialect":"en-AU","digraph_type":"all","include_explanations":true,"text":"Which whale swam through the white foam?"} | PASS | PASS | sane for requested input | 2 | 0.00077994 |
| grapheme-to-phoneme-converter #1 | {"dialect":"en-US","include_example_words":true,"include_rules_explanation":true,"text":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00007784 |
| grapheme-to-phoneme-converter #2 | {"dialect":"en-GB","include_example_words":true,"include_rules_explanation":true,"text":"thought"} | PASS | PASS | sane for requested input | 1 | 0.00008428 |
| grapheme-to-phoneme-converter #3 | {"dialect":"en-AU","include_example_words":false,"include_rules_explanation":false,"text":"choir"} | PASS | PASS | sane for requested input | 1 | 0.00008820 |
| phoneme-counter #1 | {"dialect":"en-US","show_transcription":true,"word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00006622 |
| phoneme-counter #2 | {"dialect":"en-GB","show_transcription":true,"word":"elephant"} | PASS | PASS | sane for requested input | 1 | 0.00009590 |
| phoneme-counter #3 | {"dialect":"en-AU","show_transcription":false,"word":"thought"} | PASS | PASS | sane for requested input | 1 | 0.00007686 |
| phonics-list-generator #1 | {"dialect":"en-US","difficulty_level":"beginner","phonemes":["ch","sh"],"topic":"farm animals","word_count":8} | PASS | PASS | sane for requested input | 1 | 0.00020356 |
| phonics-list-generator #2 | {"dialect":"en-GB","difficulty_level":"intermediate","phonemes":["ai","ay"],"topic":"outdoor play","word_count":10} | PASS | PASS | sane for requested input | 2 | 0.00053536 |
| phonics-list-generator #3 | {"dialect":"en-AU","difficulty_level":"beginner","phonemes":["th","ee"],"topic":"animals and nature","word_count":6} | PASS | FAIL | preserved-evidence weak or off-topic word | 2 | 0.00040544 |
| phonics-reading-error-coach #1 | {"detail":"teacher","dialect":"en-US","include_practice":true,"learner_stage":"developing","misread_word":"lap","target_word":"lamp"} | PASS | PASS | sane for requested input | 1 | 0.00014980 |
| phonics-reading-error-coach #2 | {"detail":"brief","dialect":"en-GB","include_practice":true,"learner_stage":"early","misread_word":"sip","target_word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00014392 |
| phonics-reading-error-coach #3 | {"detail":"teacher","dialect":"en-AU","include_practice":false,"learner_stage":"consolidating","misread_word":"got","target_word":"goat"} | PASS | PASS | sane for requested input | 1 | 0.00013076 |
| phonics-rule-explainer #1 | {"dialect":"en-US","num_examples":3,"phonics_rule":"silent_e","target_audience":"early_reader"} | PASS | PASS | sane for requested input | 1 | 0.00014210 |
| phonics-rule-explainer #2 | {"dialect":"en-GB","num_examples":5,"phonics_rule":"c_rules","target_audience":"teacher_parent"} | PASS | PASS | sane for requested input | 1 | 0.00017276 |
| phonics-rule-explainer #3 | {"dialect":"en-AU","num_examples":4,"phonics_rule":"r_controlled_vowels","target_audience":"elementary"} | PASS | PASS | sane for requested input | 1 | 0.00016926 |
| story-idea-generator #1 | {"age_band":"8-10","genre":"gentle mystery","num_characters":2,"num_ideas":3,"setting_keywords":"school garden"} | PASS | PASS | sane for requested input | 1 | 0.00026222 |
| story-idea-generator #2 | {"age_band":"5-7","genre":"fantasy adventure","num_characters":3,"num_ideas":2,"setting_keywords":"underwater library"} | PASS | PASS | sane for requested input | 1 | 0.00020902 |
| story-idea-generator #3 | {"age_band":"11-13","genre":"science fiction","num_characters":1,"num_ideas":2,"setting_keywords":"Moon greenhouse"} | PASS | PASS | sane for requested input | 1 | 0.00016338 |
| syllable-splitter-and-counter #1 | {"dialect":"en-US","notation":"hyphen","words":["elephant","paper","cat"]} | PASS | PASS | sane for requested input | 1 | 0.00009338 |
| syllable-splitter-and-counter #2 | {"dialect":"en-GB","notation":"dots","words":["family","chocolate","camera"]} | PASS | FAIL | wrong notation | 1 | 0.00012586 |
| syllable-splitter-and-counter #3 | {"dialect":"en-AU","notation":"hyphen","words":["fire","poem","comfortable"]} | PASS | FAIL | spelling not preserved; wrong notation | 1 | 0.00012390 |

### Per-tool score

| Tool | Schema | Semantic |
|---|---:|---:|
| decodable-sentence-creator | 3/3 | 2/3 |
| digraph-spotter | 3/3 | 3/3 |
| grapheme-to-phoneme-converter | 3/3 | 3/3 |
| phoneme-counter | 3/3 | 3/3 |
| phonics-list-generator | 3/3 | 2/3 |
| phonics-reading-error-coach | 3/3 | 3/3 |
| phonics-rule-explainer | 3/3 | 3/3 |
| story-idea-generator | 3/3 | 3/3 |
| syllable-splitter-and-counter | 3/3 | 1/3 |

- Gate 1R2 threshold: FAIL (27/27 schema-valid; 23/27 semantic; every tool
  semantic >=1: yes). Gates 2-5 were not run; nothing was deployed, activated,
  registered, published, or pushed.
- Deterministic fixes verified: digraph-spotter improved from 0/3 to 3/3;
  false-flag fields are absent rather than empty; phonics-list #2 dropped two
  non-containing words, retried once, and passed. Focused tests passed 20/20
  compiler, 38/38 host, and 99/99 generated-container contracts; all nine drift
  checks and `git diff --check` passed.
- Exact failures: decodable #2 labeled `station` as a target although it lacks a
  reviewed long-a spelling; phonics-list #3's bounded retry preserved weak or
  off-topic evidence (`these`); syllable #2 returned hyphens for requested dot
  notation; syllable #3 returned IPA-like transcriptions with middle dots,
  altering spelling and ignoring requested hyphens.
- Next hypothesis: extend the same profile-driven semantic layer with (1)
  target-word containment filtering for decodable sentences, (2) a reviewed
  weak-evidence denylist followed by the existing count retry for word lists,
  and (3) syllable word/order/spelling/separator validation before retry, with a
  deterministic separator rewrite only when spelling is already preserved.
  Re-run the unchanged 27 cases; do not deploy until the semantic total is at
  least 24/27 and every tool retains a pass.

## 2026-08-15 — Gate 1R3 final semantic-normalizer rerun (Brief AN)

- Mode: fresh provider-backed execution of regenerated 0.2.3 runtimes.
- Inputs: exact 27 teacher cases preserved by Brief V in /tmp/run_bread_butter_parta.py; no case was added, removed, or changed.
- Result: 25/27 schema-valid; 25/27 passed the documented lightweight semantic checks.
- Successful-run provider cost available from wrappers: USD 0.00348992. Failed runtimes record cost as unavailable.

| Tool / case | Input | Schema | Semantic | Detail | Calls | Cost USD |
|---|---|---:|---:|---|---:|---:|
| decodable-sentence-creator #1 | {"dialect":"en-US","include_sight_words":true,"num_sentences":3,"phonics_patterns":["cvc","sh_digraph"],"sentence_length":"short"} | PASS | PASS | sane for requested input | 1 | 0.00012180 |
| decodable-sentence-creator #2 | {"dialect":"en-GB","include_sight_words":true,"num_sentences":2,"phonics_patterns":["long_a","ai_vowel_team"],"sentence_length":"medium"} | PASS | PASS | sane for requested input | 1 | 0.00012264 |
| decodable-sentence-creator #3 | {"dialect":"en-AU","include_sight_words":false,"num_sentences":4,"phonics_patterns":["ccvc","cvcc","ch_digraph","th_digraph"],"sentence_length":"short"} | PASS | PASS | sane for requested input | 1 | 0.00012236 |
| digraph-spotter #1 | {"dialect":"en-US","digraph_type":"consonant","include_explanations":true,"text":"The chick and the sheep sat by the shed."} | PASS | PASS | sane for requested input | 1 | 0.00014938 |
| digraph-spotter #2 | {"dialect":"en-GB","digraph_type":"vowel","include_explanations":false,"text":"A green boat sailed in the rain."} | PASS | PASS | sane for requested input | 1 | 0.00010248 |
| digraph-spotter #3 | {"dialect":"en-AU","digraph_type":"all","include_explanations":true,"text":"Which whale swam through the white foam?"} | PASS | PASS | sane for requested input | 1 | 0.00015232 |
| grapheme-to-phoneme-converter #1 | {"dialect":"en-US","include_example_words":true,"include_rules_explanation":true,"text":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00008540 |
| grapheme-to-phoneme-converter #2 | {"dialect":"en-GB","include_example_words":true,"include_rules_explanation":true,"text":"thought"} | PASS | PASS | sane for requested input | 1 | 0.00008806 |
| grapheme-to-phoneme-converter #3 | {"dialect":"en-AU","include_example_words":false,"include_rules_explanation":false,"text":"choir"} | PASS | PASS | sane for requested input | 1 | 0.00007770 |
| phoneme-counter #1 | {"dialect":"en-US","show_transcription":true,"word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00006832 |
| phoneme-counter #2 | {"dialect":"en-GB","show_transcription":true,"word":"elephant"} | PASS | PASS | sane for requested input | 1 | 0.00009296 |
| phoneme-counter #3 | {"dialect":"en-AU","show_transcription":false,"word":"thought"} | PASS | PASS | sane for requested input | 1 | 0.00007896 |
| phonics-list-generator #1 | {"dialect":"en-US","difficulty_level":"beginner","phonemes":["ch","sh"],"topic":"farm animals","word_count":8} | PASS | PASS | sane for requested input | 1 | 0.00019656 |
| phonics-list-generator #2 | {"dialect":"en-GB","difficulty_level":"intermediate","phonemes":["ai","ay"],"topic":"outdoor play","word_count":10} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |
| phonics-list-generator #3 | {"dialect":"en-AU","difficulty_level":"beginner","phonemes":["th","ee"],"topic":"animals and nature","word_count":6} | PASS | PASS | sane for requested input | 1 | 0.00020916 |
| phonics-reading-error-coach #1 | {"detail":"teacher","dialect":"en-US","include_practice":true,"learner_stage":"developing","misread_word":"lap","target_word":"lamp"} | PASS | PASS | sane for requested input | 1 | 0.00012628 |
| phonics-reading-error-coach #2 | {"detail":"brief","dialect":"en-GB","include_practice":true,"learner_stage":"early","misread_word":"sip","target_word":"ship"} | PASS | PASS | sane for requested input | 1 | 0.00013594 |
| phonics-reading-error-coach #3 | {"detail":"teacher","dialect":"en-AU","include_practice":false,"learner_stage":"consolidating","misread_word":"got","target_word":"goat"} | PASS | PASS | sane for requested input | 1 | 0.00013034 |
| phonics-rule-explainer #1 | {"dialect":"en-US","num_examples":3,"phonics_rule":"silent_e","target_audience":"early_reader"} | PASS | PASS | sane for requested input | 1 | 0.00015260 |
| phonics-rule-explainer #2 | {"dialect":"en-GB","num_examples":5,"phonics_rule":"c_rules","target_audience":"teacher_parent"} | PASS | PASS | sane for requested input | 1 | 0.00016730 |
| phonics-rule-explainer #3 | {"dialect":"en-AU","num_examples":4,"phonics_rule":"r_controlled_vowels","target_audience":"elementary"} | PASS | PASS | sane for requested input | 1 | 0.00020622 |
| story-idea-generator #1 | {"age_band":"8-10","genre":"gentle mystery","num_characters":2,"num_ideas":3,"setting_keywords":"school garden"} | PASS | PASS | sane for requested input | 1 | 0.00029372 |
| story-idea-generator #2 | {"age_band":"5-7","genre":"fantasy adventure","num_characters":3,"num_ideas":2,"setting_keywords":"underwater library"} | PASS | PASS | sane for requested input | 1 | 0.00024472 |
| story-idea-generator #3 | {"age_band":"11-13","genre":"science fiction","num_characters":1,"num_ideas":2,"setting_keywords":"Moon greenhouse"} | PASS | PASS | sane for requested input | 1 | 0.00015708 |
| syllable-splitter-and-counter #1 | {"dialect":"en-US","notation":"hyphen","words":["elephant","paper","cat"]} | PASS | PASS | sane for requested input | 1 | 0.00009912 |
| syllable-splitter-and-counter #2 | {"dialect":"en-GB","notation":"dots","words":["family","chocolate","camera"]} | PASS | PASS | sane for requested input | 1 | 0.00010850 |
| syllable-splitter-and-counter #3 | {"dialect":"en-AU","notation":"hyphen","words":["fire","poem","comfortable"]} | FAIL | FAIL | no schema-valid output | unavailable | unavailable |

### Per-tool score

| Tool | Schema | Semantic |
|---|---:|---:|
| decodable-sentence-creator | 3/3 | 3/3 |
| digraph-spotter | 3/3 | 3/3 |
| grapheme-to-phoneme-converter | 3/3 | 3/3 |
| phoneme-counter | 3/3 | 3/3 |
| phonics-list-generator | 2/3 | 2/3 |
| phonics-reading-error-coach | 3/3 | 3/3 |
| phonics-rule-explainer | 3/3 | 3/3 |
| story-idea-generator | 3/3 | 3/3 |
| syllable-splitter-and-counter | 2/3 | 2/3 |

- Gate 1R3 threshold: FAIL (25/27 schema-valid; 25/27 semantic; every tool semantic >=1: yes).
- Proxy preflight: NOT RERUN. The execution boundary rejected access to the separate Modal proxy credential file because Brief AN explicitly authorized only `OPENCODE_GO_API_KEY`; no proxy credential was read or used. AL's prior 2/2 HTTP 200 result remains historical evidence, not a fresh R3 result.
- Offline verification before this run: compiler 20/20, the current full host suite 82/82, generated-container contracts 99/99, all nine compiler drift checks, and `git diff --check` passed.
- Exact retry failures: phonics-list #2 ended with only 1 of 10 reviewed `ai`/`ay` words after normalization and missing requested coverage; syllable #3 again returned spelling-altering transcriptions for all three items. Both failed closed after the one bounded retry.
- Next hypothesis: make the profile-driven retry instruction describe the violated evidence class more concretely without including provider text or user values—request a complete replacement word list whose every item survives the reviewed grapheme and denylist checks, and require orthographic syllable parts whose concatenation exactly recreates each input word. Preserve the single retry and never transliterate IPA deterministically.
- Gates 2-6 were not entered; no Modal app was deployed, no listing or visibility state was activated, no hosted run was submitted, and nothing was pushed.

## 2026-08-15 — Batch Proof 2 real provider gate (Brief BD)

- Mode: fresh OpenCode Go `deepseek-v4-flash` execution of the 14 staged cases
  across seven resolver-approved generated runtimes; the three resolver-blocked
  skills were re-confirmed by typed-contract preflight and made zero provider
  calls.
- Fresh staging verification: 10/10 source packet hashes match the build
  summary, 10/10 bundles pass compiler drift checks, and generated contract
  tests pass 100/100.
- Authorization boundary: at most 28 calls and USD 0.10. Actual: 17 successful
  provider calls, zero transport/HTTP rejections, and USD 0.00684320. Each call
  is recorded with skill, case, cost, schema result, and semantic result in the
  `call_log` of `/tmp/batch-proof-2/real-runs.json`; the incremental mode-0600
  journal is `/tmp/batch-proof-2/provider-call-log.json`.
- Result: **BATCH-RATE-2/10**. All 14 provider-backed cases were schema-valid,
  but only copywriting and budget-planning passed both semantic cases. The five
  other resolver-approved skills fail closed on profile-specific semantic
  evidence, while the three original capability blockers remain typed.

| Slug | Verdict | Schema | Semantic | Cost USD |
|---|---|---:|---:|---:|
| copy-editing | TYPED-BLOCKER | 2/2 | 0/2 | 0.00242900 |
| copywriting | HOSTED | 2/2 | 2/2 | 0.00068712 |
| internal-comms | TYPED-BLOCKER | 2/2 | 0/2 | 0.00028168 |
| verdict-sweep | TYPED-BLOCKER | not-run | not-run | 0.00000000 |
| debugging | TYPED-BLOCKER | not-run | not-run | 0.00000000 |
| data-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 |
| contract-review | TYPED-BLOCKER | 2/2 | 0/2 | 0.00122290 |
| budget-planning | HOSTED | 2/2 | 2/2 | 0.00060578 |
| note-taking | TYPED-BLOCKER | 2/2 | 0/2 | 0.00067368 |
| invoice-processing | TYPED-BLOCKER | 2/2 | 1/2 | 0.00094304 |

### Provider call ledger

Schema and semantic columns are the deterministic case verdict associated with
each real call, including corrective retries.

| Call | Skill | Case | Cost USD | Schema | Semantic |
|---:|---|---|---:|---:|---:|
| 1 | copy-editing | reviewed-happy-path | 0.00064526 | PASS | FAIL |
| 2 | copy-editing | reviewed-happy-path | 0.00059094 | PASS | FAIL |
| 3 | copy-editing | pricing-page | 0.00056728 | PASS | FAIL |
| 4 | copy-editing | pricing-page | 0.00062552 | PASS | FAIL |
| 5 | copywriting | reviewed-happy-path | 0.00034286 | PASS | PASS |
| 6 | copywriting | feature-page | 0.00034426 | PASS | PASS |
| 7 | internal-comms | reviewed-happy-path | 0.00013594 | PASS | FAIL |
| 8 | internal-comms | incident-update | 0.00014574 | PASS | FAIL |
| 9 | contract-review | reviewed-happy-path | 0.00062090 | PASS | FAIL |
| 10 | contract-review | freelancer | 0.00060200 | PASS | FAIL |
| 11 | budget-planning | reviewed-happy-path | 0.00030758 | PASS | PASS |
| 12 | budget-planning | two-month-variance | 0.00029820 | PASS | PASS |
| 13 | note-taking | reviewed-happy-path | 0.00034034 | PASS | FAIL |
| 14 | note-taking | project-note | 0.00033334 | PASS | FAIL |
| 15 | invoice-processing | reviewed-happy-path | 0.00040082 | PASS | PASS |
| 16 | invoice-processing | reviewed-happy-path | 0.00030870 | PASS | PASS |
| 17 | invoice-processing | invoice-no-po | 0.00023352 | PASS | FAIL |

### Exact fail-closed evidence

- `copy-editing`: both cases failed `BEFORE_NOT_SOURCE_SUBSTRING` after one
  corrective retry each.
- `internal-comms`: both cases failed `INVENTED_NUMERIC_TOKEN`.
- `contract-review`: both cases failed `DISCLAIMER_MISSING`.
- `note-taking`: both cases failed `ACTION_DATE_NOT_SOURCE` and
  `INVENTED_NUMERIC_TOKEN`.
- `invoice-processing`: the second case failed `HEADER_OR_MATCH_MISMATCH`; the
  reviewed happy path passed after one corrective retry.

### Ranked registry growth

1. `research.collect:public_search_fetch` — unlock `verdict-sweep`. Its reviewed
   contract requires the `research.web.collect` primary-evidence step; the
   compiler expresses the unresolved boundary as
   `input.adapt:browser_research` plus primary-source collection.
2. `workspace.execute_code` — unlock `debugging`. Its reviewed contract requires
   an `executable_code_workspace` and the inspect, reproduce, edit, shell, and
   test sequence; the compiler currently reports
   `input.adapt:code_workspace` at `/input_adapters/0`.
3. `tabular.statistics` — unlock `data-analysis`. Its reviewed contract requires
   `tabular.parse` and `statistics.compute`; the compiler currently reports
   `input.adapt:tabular_dataset` at `/input_adapters/0`. `chart_generation` is
   already resolver-approved, so chart rendering is not the remaining gap.

- Evidence: `/tmp/batch-proof-2/real-runs.json` (mode 0600). No deployment,
  registration, activation, catalog change, push, commit, external message, or
  production mutation occurred.

## 2026-08-15 — Capability growth: public fetch + tabular statistics (Brief BF)

- Added the standard-library-only `tools/research/public_fetch.py` primitive:
  HTTPS by default, optional exact-host allowlist, robots enforcement, ten-second
  timeout ceiling, three-redirect ceiling, 256 KiB ceiling, bounded preview and
  SHA-256 evidence, and typed `FETCH_TIMEOUT`, `ROBOTS_DENIED`, `TOO_LARGE`, and
  `HTTP_ERROR` failures. Search is honestly **PARTIAL**: v1 supports direct URLs
  only and `search_snippets` fails closed with `SEARCH_UNAVAILABLE` because no
  stable credential-free general public-search endpoint is configured.
- Added deterministic `tools/render/tabular.py`: comma/semicolon/tab CSV parsing,
  standard quote handling, conservative int/float typing, categorical fallback,
  numeric count/sum/mean/median/min/max/sample stdev/linear percentiles, stable
  categorical mode, notes, and typed `EMPTY_TABLE`, `NON_NUMERIC_COLUMN`, and
  `INSUFFICIENT_DATA` failures.
- Appended registry entries `research.collect:public_search_fetch` and
  `tabular.statistics` with typed triggers, generated pieces, dependencies,
  tests, policy, and honest limits. Both remain `experimental` pending the
  sibling-owned compiler integration; `public_search_fetch` is explicitly
  marked `PARTIAL` for search.
- Verification: 19/19 focused tests passed against a loopback-only
  `http.server` fixture; syntax compilation and scoped `git diff --check`
  passed. `packages/skill-to-modal/compiler.py` was untouched. Full evidence is
  `/tmp/capability-growth/`. No real network, provider call, credential access,
  commit, push, deploy, external message, or production mutation occurred.

## 2026-08-15 — Contract-derived semantic adapter (Brief BE)

- Replaced the generated runtime's education-only semantic assumption with a
  compiler-derived `SEMANTIC_EVIDENCE_SPEC`. Selection uses reviewed contract
  promises plus input/output schema shape; it never matches a product slug or
  name. Existing profile-driven phoneme, digraph, target-containment, syllable,
  and flag normalizers remain additive and unchanged.

| Contract class | Structural selector | Generated evidence needle |
|---|---|---|
| Copy revision | source copy + revised copy + edits with after/rationale + unsupported-claims field | final revision differs; unsafe suggested edits are removed; claims surviving in final copy must be empty; edit evidence is nonblank; final numeric facts come from input |
| Indexed facts | facts input + integer fact indexes + key points | indexes are nonempty, unique, and in range; each key point has paraphrase-tolerant token/number grounding in a selected fact |
| Quoted risk review | contract text + risks/obligations with source quotes + disclaimer | every risk/obligation quote is a nonempty exact source substring; any nonblank schema-valid disclaimer wording passes |
| Source-referenced notes | raw notes + action source quotes + summary/decision/question fields | source-quote evidence is nonempty and exact; summaries and key points use paraphrase-tolerant source grounding; normalized dates need not be literal human-date substrings |
| Invoice arithmetic | invoice text + numeric line items + subtotal/tax/shipping/discount/total/status | parsed line identities and values match; extensions, subtotal, and total recompute; arithmetic status matches; unrelated nullable header normalization is ignored |
| Grounded copy / budget | page-copy fact shape or budget arrays/totals plus reviewed promises | product name and numeric facts stay input-grounded; budget line, department, company, forecast, and target arithmetic recompute |
| Education profiles | existing explicit semantic normalizer declarations | existing phoneme/digraph/target/syllable/flag rules remain the evidence contract |

- Recorded-output replay: the five selected wrong-needle fixtures pass 5/5;
  replaying both historical cases for every blocked skill passes 10/10. Output
  and reconstructed input digests are checked before replay. Evidence:
  `/tmp/semantic-adapter/fixtures/` and
  `/tmp/semantic-adapter/fixture-replay-results.json`.
- Verification: compiler tests 34/34; regenerated semantic-adapter container
  contracts 50/50; five compiler drift checks and syntax compilation pass.
- Fresh provider continuation: blocked before the first request. The execution
  approval gate rejected loading `/Users/yifan/.omo-hermes/.env` despite the
  standing call/spend authorization, requiring explicit specific credential
  loading approval. Actual spend: 0/10 calls and USD 0.00. Per-skill fresh
  semantic results therefore remain `not-run`; this is recorded without fake
  outputs in mode-0600 `/tmp/semantic-adapter/real-runs.json`.
- Exact blocker: `SEMANTIC-ADAPTER-BLOCKED: credential loading from
  /Users/yifan/.omo-hermes/.env requires Harry's explicit specific approval;
  0/10 provider calls attempted and USD 0.00 spent.`
- No commit, push, deploy, catalog change, external message, or production
  mutation occurred; `tools/render/` and `tools/host-skill/` were untouched.

## 2026-08-15 — Resolver wiring: public search/fetch + tabular statistics (Brief BG)

- Registered available, versioned `research.collect:public_search_fetch` and
  `tabular.statistics` compiler capabilities. Typed triggers cover the reviewed
  research operations, primary-source declarations, legacy
  `input.adapt:browser_research`, `tabular.parse` + `statistics.compute`, legacy
  `input.adapt:tabular_dataset`, and `metrics_viz`/`tabular_analysis` artifacts.
- Generated runtimes import and image-copy the shared modules. Public search is
  bounded to a 500-character query and ten-result response contract, and the v1
  module's typed `SEARCH_UNAVAILABLE` propagates without provider fallback.
  Direct URL fetch retains the primitive's robots/HTTPS/redirect/timeout/size
  policy. Tabular execution caps UTF-8 input at 256 KiB, calls parse then
  statistics, and returns `omo.tabular-analysis/v1` structured output.
- Resolver unknown-adapter detection now honors exact `input.adapt:*` coverage
  from matched registry entries, so the two legacy blockers resolve without a
  skill-name or profile-specific conditional. `metrics_viz` composes
  `chart_generation` with `tabular.statistics` deterministically.
- Verification: compiler 37/37; compiler plus existing public-fetch/tabular
  primitive tests 56/56 using a loopback-only fixture; all generated-container
  contracts 360/360; Python syntax compilation and scoped `git diff --check`
  passed. Evidence: `/tmp/resolver-wiring/`.
- No provider call, credential access, real network request, commit, push,
  deploy, catalog change, external message, or production mutation occurred.
  `tools/` and generated containers were not modified.

## 2026-08-15 — Final semantic + 10-skill rerun (Brief BH)

- Governing provider authorization, quoted verbatim: “I approve opencode you
  can do as you like for it's fine opencode i have a subscription”. The
  existing OpenCode Go credential was loaded only into the provider child
  process; it was never printed or persisted. This authorization had no call
  or cost cap.
- Freshness: current canonical compiler SHA-256
  `9112193c27a7120161ee5977d985af431433ec6340f7ac56c2da385124f0fb29`;
  manifest-emitted resolver `1.0.0`, registry `1.2.0`, registry digest
  `sha256:44113a03303d284f1209f24b23057ea6736b9cf8462542dc58ea648914a15195`;
  cost-model SHA-256
  `c9e7f9947b705ddf967dfc431a342eea5ff37fce5715aa0bfaa1d4805f4a4428`.
  Compiler tests pass 37/37; fresh Phase 1 generated contracts pass 50/50;
  fresh Phase 2 generated contracts pass 100/100; all compiler drift checks
  passed.
- Phase 1 semantic rerun: **5/5 HOSTED**, 10/10 schema-valid, 10/10
  contract-derived semantic passes, exactly ten fresh provider calls, and USD
  0.00388318. All ten input SHA-256 values exactly match the corresponding
  Batch Proof 2 cases. The five contract classes were `copy_revision`,
  `indexed_facts`, `quoted_risk_review`, `source_referenced_notes`, and
  `invoice_arithmetic`.
- Phase 2 result: **FINAL-RATE-5/10**. All twenty case rows are fresh runtime
  invocations. Fourteen provider-backed cases generated seventeen calls after
  bounded retries, costing USD 0.00616630; the six capability-blocker cases
  made zero provider calls. The two phases total 27 provider calls and USD
  0.01004948. Ledger indexes, call/case cost sums, and evidence file modes
  reconcile in `/tmp/final-rerun/final-audit.json`.

| Slug | Verdict | Schema | Semantic | Provider cost USD | Final price |
|---|---|---:|---:|---:|---:|
| copy-editing | TYPED-BLOCKER | 2/2 | 1/2 | 0.00175938 | nonchargeable |
| copywriting | HOSTED | 2/2 | 2/2 | 0.00063840 | 0.10 |
| internal-comms | HOSTED | 2/2 | 2/2 | 0.00028588 | 0.10 |
| verdict-sweep | TYPED-BLOCKER | not-run | not-run | 0.00000000 | nonchargeable |
| debugging | TYPED-BLOCKER | not-run | not-run | 0.00000000 | nonchargeable |
| data-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 | nonchargeable |
| contract-review | HOSTED | 2/2 | 2/2 | 0.00116830 | 0.10 |
| budget-planning | TYPED-BLOCKER | 2/2 | 0/2 | 0.00116928 | nonchargeable |
| note-taking | HOSTED | 2/2 | 2/2 | 0.00066654 | 0.10 |
| invoice-processing | HOSTED | 2/2 | 2/2 | 0.00047852 | 0.10 |

### Remaining blockers and exact next capabilities

1. `copy-editing` — `REAL_RUN_SEMANTIC_FAILED`: one schema-valid case
   exhausted the retry with a nonempty `unsupported_claims` field. Next:
   `copy_revision_semantic_reconciliation`, implemented in the generated copy
   revision normalizer without weakening source grounding.
2. `verdict-sweep` — `SEARCH_UNAVAILABLE`: both real capability probes selected
   `research.collect:public_search_fetch` and reproduced the v1 typed failure.
   Next: `public_query_search_backend`; bounded direct-URL fetch alone does not
   satisfy discovery.
3. `debugging` — `CAPABILITY_UNAVAILABLE`: both generated runtime preflights
   stopped before spend at `/input_adapters/0`. Next: `workspace.execute_code`
   with isolated inspect, reproduce, edit, shell, and test evidence.
4. `data-analysis` — `CAPABILITY_SCOPE_INSUFFICIENT`: both
   `tabular.statistics` probes returned real three-row
   `omo.tabular-analysis/v1` results, but the workflow cannot assemble
   question-grounded findings, hypothesis results, chart specification, and
   delivered artifact. Next: `tabular_analysis_orchestrator`.
5. `budget-planning` — `SEMANTIC_ADAPTER_DERIVATION_GAP`: both schema-valid
   cases exhausted retry because the generated semantic gate rejects required
   derived totals/variances as invented numeric tokens. Next:
   `budget_derived_number_allowlist` in the compiler-derived budget semantic
   adapter, including line, department, company, forecast, percentage, and
   target-variance derivations.

- Evidence: `/tmp/final-rerun/containers/`,
  `/tmp/final-rerun/semantic-rerun.json`,
  `/tmp/final-rerun/real-runs.json`,
  `/tmp/final-rerun/provider-call-log.json`, and
  `/tmp/final-rerun/final-audit.json`, all evidence JSON mode 0600.
- No deploy, registration, activation, catalog change, external message,
  commit, push, or production mutation occurred.

## 2026-08-15 — Generator hardening: tabular orchestration + budget/copy reconciliation (Brief BJ)

| Fix | Needle | Verdict |
|---|---|---|
| `tabular_analysis_orchestrator` | All-of trigger for parse + statistics + chart plus findings/statistical output; deterministic grouped sums/chart, stats-only prose prompt, numeric grounding gate, verified PNG delivery | `data-analysis` fixture replay **2/2** |
| `budget_derived_number_allowlist` | Arithmetic recompute for line/department/company/forecast/target values and percentages; numeric canonicalization plus exact derived prose aliases; typed mismatch paths preserved | `budget-planning` fixture replay **2/2** |
| `copy_revision_semantic_reconciliation` | Pre-schema claim/edit shape reconciliation; unsupported claim survives only when normalized text remains in revised copy; surviving edits require before/after/rationale | `copy-editing` fixture replay **2/2** |

- All six inputs reproduce the exact SHA-256 values in
  `/tmp/final-rerun/real-runs.json`. Data-analysis deterministically computes
  North 260 versus South 90, and both cases render valid PNG artifacts while
  the findings writer receives computed stats but no dataset or raw rows.
- Copy evidence caveat: final-rerun retained the phase-2 terminal semantic
  error but not the two rejected bodies. The reconciliation needle is proven
  against both retained successful final cases plus the closest exact-input
  failed candidate in `/tmp/batch-proof-2/real-runs.json`; no exact missing
  shape is claimed.
- Verification: compiler **41/41**; regenerated final-rerun bundles **10/10**
  each; repository generated-container suite **386/386**; syntax and scoped
  diff checks pass. Evidence: `/tmp/hardening/`.
- Provider calls: 0. No credential access, network request, deploy, commit,
  push, production mutation, external message, or `tools/` edit occurred.
  Verdict: **HARDENED-3**.

## 2026-08-15 — BATCH-30 real-provider acceptance (Brief BL)

- Authorization `batch30-sensitive-egress-001` is **AUTHORIZED** by the
  founder's blanket OpenCode approval and standing BATCH-30 mandate. The
  process loaded only `OPENCODE_GO_API_KEY` from the approved owner-local env,
  mapped it to the generated runners, and never printed or persisted the key.
  Egress contained only the approved synthetic business, invoice, ticket,
  source-code, policy, and translation cases; no real PII.
- Fresh gate: 30/30 source hashes, 30/30 compiler drift checks, compiler 41/41,
  generated contracts 300/300, 30 runtime profiles, 30 reviewed contracts, 30
  containers, and exactly 60 cases all reconcile.
- Result: **BATCH30-RATE-7/30**. All 60 local runtime cases ran. The 14
  submit-ready skills made 28 successful OpenCode Go calls; all 28 had known
  usage/cost, 28/28 outputs were schema-valid, 17/28 passed the batch semantic
  gates, and no case needed a retry. Total provider cost was USD 0.00897834.
  The 16 preflight-blocked skills reproduced typed blockers with zero provider
  calls. No skill timed out.
- Preflight incident: an initial restricted-network, non-evidence launch
  returned only `LLM_UNAVAILABLE` and exposed nested legacy second-case inputs
  plus accumulating logger wrappers. It received no successful provider
  response or usage record. The two harness issues were corrected, profiles
  and containers were rebuilt, all gates above were rerun, and the final
  ledger contains only the clean approved external run.

| Slug | Verdict | Schema | Semantic | Cost USD | Blocker code |
|---|---|---:|---:|---:|---|
| copy-editing | HOSTED | 2/2 | 2/2 | 0.00120456 | — |
| copywriting | HOSTED | 2/2 | 2/2 | 0.00063126 | — |
| internal-comms | HOSTED | 2/2 | 2/2 | 0.00029302 | — |
| verdict-sweep | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `SEARCH_UNAVAILABLE` |
| debugging | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_UNAVAILABLE` |
| data-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `ORCHESTRATOR_EXECUTOR_UNWIRED` |
| contract-review | HOSTED | 2/2 | 2/2 | 0.00122332 | — |
| budget-planning | HOSTED | 2/2 | 2/2 | 0.00060284 | — |
| note-taking | HOSTED | 2/2 | 2/2 | 0.00066990 | — |
| invoice-processing | HOSTED | 2/2 | 2/2 | 0.00048860 | — |
| accessibility-testing | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_UNAVAILABLE` |
| analytics-reporting | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| churn-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| code-documentation | TYPED-BLOCKER | 2/2 | 0/2 | 0.00057330 | `REAL_RUN_SEMANTIC_FAILED` |
| customer-feedback-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| deep-research | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `SEARCH_UNAVAILABLE` |
| email-drafting | TYPED-BLOCKER | 2/2 | 0/2 | 0.00021910 | `REAL_RUN_SEMANTIC_FAILED` |
| expense-categorization | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| exploratory-data-analysis | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| fact-checking | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `SEARCH_UNAVAILABLE` |
| financial-report-generation | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| literature-review | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `SEARCH_UNAVAILABLE` |
| logo-design | TYPED-BLOCKER | 2/2 | 0/2 | 0.00098882 | `REAL_RUN_SEMANTIC_FAILED` |
| meeting-transcription | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_UNAVAILABLE` |
| privacy-policy-drafting | TYPED-BLOCKER | 2/2 | 0/2 | 0.00094668 | `REAL_RUN_SEMANTIC_FAILED` |
| proposal-generation | TYPED-BLOCKER | 2/2 | 1/2 | 0.00056336 | `REAL_RUN_SEMANTIC_FAILED` |
| report-generation | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_SCOPE_INSUFFICIENT` |
| testing | TYPED-BLOCKER | not-run | not-run | 0.00000000 | `CAPABILITY_UNAVAILABLE` |
| ticket-triage | TYPED-BLOCKER | 2/2 | 1/2 | 0.00033460 | `REAL_RUN_SEMANTIC_FAILED` |
| translation | TYPED-BLOCKER | 2/2 | 1/2 | 0.00023898 | `REAL_RUN_SEMANTIC_FAILED` |

### Ranked next capabilities — HARD-HOLDS

1. `research.collect:public_query_search_backend` — affects
   `verdict-sweep`, `deep-research`, and `fact-checking`. Exact requirement:
   select and approve a query-search provider, supply its credential for
   process-only loading, and implement bounded retrieval plus a citation/source
   ledger behind `public_search_fetch`; direct-URL fetch is insufficient.
2. `workspace.safe_execution` — affects `debugging` and `testing`. Exact
   requirement: approve an ephemeral isolated runner with language allowlists,
   bounded filesystem/shell access, CPU-memory-process-time limits, network off
   by default, and captured inspect/edit/test evidence; expose
   `workspace.execute_code` and `workspace.execute_tests` only after review.
3. `research.collect:scholarly_search_and_fulltext_fetch` — affects
   `literature-review`. Exact requirement: approved scholarly index/full-text
   sources, credentials or license terms, bounded screening, and provenance.
4. `browser.accessibility_execute` — affects `accessibility-testing`. Exact
   requirement: an approved sandboxed browser/DOM scanner that records keyboard
   and assistive-technology evidence before emitting WCAG claims.
5. `speech.transcription_and_diarization` — affects `meeting-transcription`.
   Exact requirement: an approved STT/diarization model or provider, credential
   handling, media-retention policy, timestamp contract, and bounded executor.

### Ranked next capabilities — BUILDABLE

1. `semantic.contract_evidence_adapters/v1` — affects the seven
   schema-valid semantic blockers. Add generic registry entries
   `semantic.grounded_numeric_copy`, `semantic.exact_field_projection`,
   `semantic.constraint_coverage`, `semantic.policy_requirement_coverage`,
   `semantic.rule_based_classification`, and
   `semantic.placeholder_glossary_enforcement`; feed structural diffs into the
   existing single corrective retry.
2. `tabular.domain_orchestrators/v1` — affects seven domain workflows. Add
   `marketing_analytics_orchestrator`, `churn_scoring_orchestrator`,
   `feedback_analysis_orchestrator`, `expense_categorization_orchestrator`,
   `advanced_tabular_analysis_orchestrator`,
   `financial_reporting_orchestrator`, and `structured_report_orchestrator` on
   top of the existing bounded parse/statistics/chart primitives.
3. `tabular_analysis_endpoint_routing` — affects `data-analysis`. Route the
   already generated parse-statistics-findings-chart orchestrator through the
   hosted `execute_workflow` path and prove full submission behavior.

- Evidence: `/tmp/batch30/real-runs.json`,
  `/tmp/batch30/provider-call-log.json`, and
  `/tmp/batch30/final-audit.json`, all mode 0600. The final audit status is
  `pass`; call/case counts, requested ledger fields, cost sums, source hashes,
  drift, test counts, blocker codes, and the retry bound reconcile.
- No deploy, registration, activation, catalog change, external message,
  commit, push, or production mutation occurred.

## Final hardening BM — generic domain analysis + endpoint routing (2026-08-15)

Verdict: `FINAL-HARDENED-2`.

- Fix 1 PASS: one registry-backed `domain_analysis_orchestrator` now selects
  structurally from explicit reviewed `DOMAIN`, `tabular.parse`,
  `statistics.compute`, an LLM findings step, and typed output fields. It
  projects the findings schema and prompt field list from the contract, sends
  computed statistics but no dataset/raw rows to the writer, rejects
  ungrounded numbers, and optionally produces a deterministic chart spec.
- The seven fixture-profile flips are marketing-analytics (BATCH30 slug
  `analytics-reporting`), churn-analysis, customer-feedback-analysis,
  expense-categorization, exploratory-data-analysis,
  financial-report-generation, and report-generation. All seven resolve the
  same orchestrator and all seven fixture executions returned the structured
  output plus a real PNG with `raw_dataset_seen=false`,
  `raw_rows_seen=false`, and zero provider calls.
- Fix 2 PASS: data-analysis now routes the generated bounded program through
  hosted `execute_workflow`. The fixture API submission exercised submit →
  spawn/execute → result, returned accepted then completed, and satisfied the
  full signed artifact contract without a provider call.
- Gates: compiler 46/46, eight regenerated bundles 80/80, drift 8/8, fixture
  runs 8/8, and `git diff --check` clean. Evidence and the per-fix report are
  under `/tmp/final-hardening/`. `tools/` was untouched; no commit, push,
  deploy, external message, credential read, provider call, or spend occurred.
- Exact founder hard-holds: search backend key — “Approve a bounded
  public-query search backend and process-only loading of its API key.”;
  safe-exec design — “Approve the isolated ephemeral safe-execution design
  with allowlisted runtimes, bounded filesystem/process/CPU/memory/time, and
  network off by default.”; image-generation provider — “Approve a bounded
  image-generation provider and process-only loading of its API key.”

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

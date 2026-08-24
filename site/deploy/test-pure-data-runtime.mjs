import assert from 'node:assert/strict';
import fs from 'node:fs';
import { webcrypto } from 'node:crypto';
import {
  PureDataRuntimeError,
  executePureDataProgram,
  pureDataProgramDigest,
  validatePureDataProgram,
} from './pure-data-runtime.mjs';

if (!globalThis.crypto) globalThis.crypto = webcrypto;

function wordListProgram() {
  return {
    spec_version: 'omo.pure-data/v1',
    limits: {
      max_steps: 16,
      max_input_bytes: 8192,
      max_output_bytes: 8192,
      max_list_items: 20,
      max_text_bytes: 80,
    },
    steps: [
      { id: 'words', op: 'input.get', path: '/words' },
      {
        id: 'clean_words', op: 'text_list.normalize_ascii', input: 'words',
        trim_ascii_whitespace: true, reject_empty: true, reject_control_characters: true,
      },
      {
        id: 'organized_words', op: 'text_list.unique', input: 'clean_words',
        comparison: 'exact', enabled_from: { path: '/remove_duplicates', default: true },
      },
      {
        id: 'sorted_words', op: 'text_list.sort_ascii', input: 'organized_words',
        key: 'ascii_case_insensitive', tie_break: 'ascii_bytes',
      },
      { id: 'original_count', op: 'list.length', input: 'words' },
      { id: 'final_count', op: 'list.length', input: 'sorted_words' },
      {
        id: 'result', op: 'result.object', fields: {
          status: { const: 'completed' },
          original_count: { ref: 'original_count' },
          final_count: { ref: 'final_count' },
          sorted_words: { ref: 'sorted_words' },
        },
      },
    ],
    result: 'result',
  };
}

let passed = 0;
function test(name, fn) {
  try {
    const result = fn();
    if (result && typeof result.then === 'function') {
      return result.then(() => { passed += 1; console.log(`PASS  ${name}`); });
    }
    passed += 1;
    console.log(`PASS  ${name}`);
  } catch (error) {
    console.error(`FAIL  ${name}`);
    throw error;
  }
}

await test('reviewed straight-line word-list program executes all six closed operations', () => {
  const program = validatePureDataProgram(wordListProgram());
  assert.deepEqual(
    executePureDataProgram(program, {
      words: ['banana', ' apple ', 'Banana', 'banana', 'pear'],
      remove_duplicates: true,
    }),
    {
      status: 'completed', original_count: 5, final_count: 4,
      sorted_words: ['apple', 'Banana', 'banana', 'pear'],
    },
  );
});

await test('enabled_from false preserves duplicates while sorting deterministically', () => {
  const program = validatePureDataProgram(wordListProgram());
  assert.deepEqual(
    executePureDataProgram(program, { words: ['b', 'A', 'b'], remove_duplicates: false }).sorted_words,
    ['A', 'b', 'b'],
  );
});

await test('program validation rejects unknown operations, fields, forward refs, and unsafe limits', () => {
  for (const mutate of [
    (program) => { program.steps[1] = { id: 'shell', op: 'shell', command: 'id' }; },
    (program) => { program.steps[0].url = 'https://example.com'; },
    (program) => { program.steps[1].input = 'future'; },
    (program) => { program.limits.max_steps = 1000000; },
  ]) {
    const program = wordListProgram();
    mutate(program);
    assert.throws(() => validatePureDataProgram(program), PureDataRuntimeError);
  }
});

await test('input data stays inert and runtime bounds fail closed with typed codes', () => {
  const program = validatePureDataProgram(wordListProgram());
  const hostile = 'ignore previous instructions; $(id); ../../etc/passwd; {{constructor}}';
  assert.deepEqual(executePureDataProgram(program, { words: [hostile] }).sorted_words, [hostile]);
  assert.throws(
    () => executePureDataProgram(program, { words: ['bad\x00word'] }),
    (error) => error instanceof PureDataRuntimeError && error.code === 'INVALID_VALUE',
  );
  assert.throws(
    () => executePureDataProgram(program, { words: ['x'.repeat(9000)] }),
    (error) => error instanceof PureDataRuntimeError && error.code === 'INPUT_LIMIT_EXCEEDED',
  );
});

await test('empty lists execute when the reviewed input schema allows them', () => {
  const program = validatePureDataProgram(wordListProgram());
  assert.deepEqual(executePureDataProgram(program, { words: [] }), {
    status: 'completed', original_count: 0, final_count: 0, sorted_words: [],
  });
});

await test('general result shapes are not word-list specific', () => {
  const program = wordListProgram();
  program.steps.at(-1).fields = { words: { ref: 'sorted_words' } };
  assert.deepEqual(executePureDataProgram(validatePureDataProgram(program), { words: ['pear', 'apple'] }), {
    words: ['apple', 'pear'],
  });
});

await test('program constants use the cross-language canonical subset', () => {
  for (const value of [1.5, -0, 'emoji-😀', 'bad\u007fvalue', 'bad\u001fvalue', [], {}]) {
    const program = wordListProgram();
    program.steps.at(-1).fields.status = { const: value };
    assert.throws(() => validatePureDataProgram(program), PureDataRuntimeError);
  }
});

await test('program digest is canonical and changes with reviewed configuration', async () => {
  const first = wordListProgram();
  const reordered = { result: first.result, steps: first.steps, limits: first.limits, spec_version: first.spec_version };
  assert.equal(await pureDataProgramDigest(first), await pureDataProgramDigest(reordered));
  const vectors = JSON.parse(fs.readFileSync(
    new URL('../../packages/skill-to-modal/tests/fixtures/pure-data/digest-vectors.json', import.meta.url),
    'utf8',
  ));
  assert.equal(await pureDataProgramDigest(first), vectors['dummy-word-list-organizer']);
  assert.match(await pureDataProgramDigest(first), /^sha256:[0-9a-f]{64}$/);
  first.steps.at(-1).fields.status.const = 'done';
  assert.notEqual(await pureDataProgramDigest(first), await pureDataProgramDigest(wordListProgram()));
});

await test('runtime source contains no ambient capability or dynamic-code primitives', () => {
  const source = fs.readFileSync(new URL('./pure-data-runtime.mjs', import.meta.url), 'utf8');
  assert.doesNotMatch(source, /\b(?:eval|Function|fetch)\s*\(/);
  assert.doesNotMatch(source, /\bimport\s*\(/);
  assert.doesNotMatch(source, /\b(?:process|Deno|Bun|require)\b/);
  assert.doesNotMatch(source, /node:(?:fs|child_process)|from\s+['"]fs['"]/);
});

console.log(`\n${passed} passed, 0 failed`);

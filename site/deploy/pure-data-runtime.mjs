const PROGRAM_SPEC_VERSION = 'omo.pure-data/v1';
const HARD_LIMITS = Object.freeze({
  max_steps: 16,
  max_input_bytes: 64 * 1024,
  max_output_bytes: 64 * 1024,
  max_list_items: 100,
  max_text_bytes: 1000,
});
const LIMIT_KEYS = Object.freeze(Object.keys(HARD_LIMITS));
const STEP_ID_RE = /^[A-Za-z][A-Za-z0-9_]{0,63}$/;
const FIELD_NAME_RE = /^[A-Za-z][A-Za-z0-9_]{0,63}$/;
const encoder = new TextEncoder();

export class PureDataRuntimeError extends Error {
  constructor(code, message) {
    super(`${code}: ${message}`);
    this.name = 'PureDataRuntimeError';
    this.code = code;
  }
}

function fail(code, message) {
  throw new PureDataRuntimeError(code, message);
}

function isRecord(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function hasExactKeys(value, allowed) {
  if (!isRecord(value)) return false;
  const actual = Object.keys(value).sort();
  const expected = [...allowed].sort();
  return actual.length === expected.length && actual.every((key, index) => key === expected[index]);
}

function hasAllowedKeys(value, required, optional = []) {
  if (!isRecord(value)) return false;
  const allowed = new Set([...required, ...optional]);
  return required.every((key) => Object.prototype.hasOwnProperty.call(value, key))
    && Object.keys(value).every((key) => allowed.has(key));
}

function assertPositiveBoundedInteger(value, key) {
  if (!Number.isInteger(value) || value < 1 || value > HARD_LIMITS[key]) {
    fail('INVALID_PROGRAM', `invalid or unsafe ${key}`);
  }
}

function assertJsonValue(value, label) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) fail('INVALID_PROGRAM', `${label} is not finite JSON data`);
    return;
  }
  if (Array.isArray(value)) {
    for (const child of value) assertJsonValue(child, label);
    return;
  }
  if (isRecord(value)) {
    for (const [key, child] of Object.entries(value)) {
      if (key === '__proto__' || key === 'prototype' || key === 'constructor') {
        fail('INVALID_PROGRAM', `${label} contains an unsafe key`);
      }
      assertJsonValue(child, label);
    }
    return;
  }
  fail('INVALID_PROGRAM', `${label} is not JSON data`);
}

function assertCanonicalConstant(value, label) {
  if (value === null || typeof value === 'boolean') return;
  if (typeof value === 'number' && Number.isSafeInteger(value) && !Object.is(value, -0)) return;
  if (typeof value === 'string' && /^[\x20-\x7E]{0,200}$/.test(value)) return;
  fail('INVALID_PROGRAM', `${label} constant is outside the canonical subset`);
}

function assertPointer(path, label) {
  if (typeof path !== 'string' || !/^\/[A-Za-z][A-Za-z0-9_]{0,63}$/.test(path)) {
    fail('INVALID_PROGRAM', `${label} must name one top-level input field`);
  }
}

function assertReference(id, knownIds, label) {
  if (typeof id !== 'string' || !knownIds.has(id)) {
    fail('INVALID_PROGRAM', `${label} must reference an earlier step`);
  }
}

function validateStep(step, knownIds) {
  if (!isRecord(step) || !STEP_ID_RE.test(String(step.id || '')) || knownIds.has(step.id)) {
    fail('INVALID_PROGRAM', 'step id shape is invalid or duplicated');
  }
  switch (step.op) {
    case 'input.get':
      if (!hasExactKeys(step, ['id', 'op', 'path'])) fail('INVALID_PROGRAM', 'input.get step shape is invalid');
      assertPointer(step.path, 'input.get path');
      break;
    case 'text_list.normalize_ascii':
      if (!hasExactKeys(step, [
        'id', 'op', 'input', 'trim_ascii_whitespace', 'reject_empty', 'reject_control_characters',
      ])) fail('INVALID_PROGRAM', 'text_list.normalize_ascii step shape is invalid');
      assertReference(step.input, knownIds, 'text_list.normalize_ascii input');
      for (const key of ['trim_ascii_whitespace', 'reject_empty', 'reject_control_characters']) {
        if (typeof step[key] !== 'boolean') fail('INVALID_PROGRAM', `${key} must be boolean`);
      }
      break;
    case 'text_list.unique':
      if (!hasAllowedKeys(step, ['id', 'op', 'input', 'comparison'], ['enabled_from'])) {
        fail('INVALID_PROGRAM', 'text_list.unique step shape is invalid');
      }
      assertReference(step.input, knownIds, 'text_list.unique input');
      if (step.comparison !== 'exact') fail('INVALID_PROGRAM', 'text_list.unique comparison is unsupported');
      if (Object.prototype.hasOwnProperty.call(step, 'enabled_from')) {
        if (!hasExactKeys(step.enabled_from, ['path', 'default']) || typeof step.enabled_from.default !== 'boolean') {
          fail('INVALID_PROGRAM', 'text_list.unique enabled_from shape is invalid');
        }
        assertPointer(step.enabled_from.path, 'enabled_from path');
      }
      break;
    case 'text_list.sort_ascii':
      if (!hasExactKeys(step, ['id', 'op', 'input', 'key', 'tie_break'])) {
        fail('INVALID_PROGRAM', 'text_list.sort_ascii step shape is invalid');
      }
      assertReference(step.input, knownIds, 'text_list.sort_ascii input');
      if (step.key !== 'ascii_case_insensitive' || step.tie_break !== 'ascii_bytes') {
        fail('INVALID_PROGRAM', 'text_list.sort_ascii ordering is unsupported');
      }
      break;
    case 'list.length':
      if (!hasExactKeys(step, ['id', 'op', 'input'])) fail('INVALID_PROGRAM', 'list.length step shape is invalid');
      assertReference(step.input, knownIds, 'list.length input');
      break;
    case 'result.object':
      if (!hasExactKeys(step, ['id', 'op', 'fields']) || !isRecord(step.fields)) {
        fail('INVALID_PROGRAM', 'result.object step shape is invalid');
      }
      for (const [field, source] of Object.entries(step.fields)) {
        if (!FIELD_NAME_RE.test(field)) fail('INVALID_PROGRAM', 'result.object field name is invalid');
        if (hasExactKeys(source, ['ref'])) assertReference(source.ref, knownIds, `result.object ${field}`);
        else if (hasExactKeys(source, ['const'])) assertCanonicalConstant(source.const, `result.object ${field}`);
        else fail('INVALID_PROGRAM', `result.object ${field} source shape is invalid`);
      }
      break;
    default:
      fail('INVALID_PROGRAM', `operation ${String(step.op || '')} is unsupported`);
  }
  knownIds.add(step.id);
}

export function validatePureDataProgram(program) {
  if (!hasExactKeys(program, ['spec_version', 'limits', 'steps', 'result'])) {
    fail('INVALID_PROGRAM', 'program shape is invalid');
  }
  if (program.spec_version !== PROGRAM_SPEC_VERSION) fail('INVALID_PROGRAM', 'program spec version is unsupported');
  if (!hasExactKeys(program.limits, LIMIT_KEYS)) fail('INVALID_PROGRAM', 'limits shape is invalid');
  for (const key of LIMIT_KEYS) assertPositiveBoundedInteger(program.limits[key], key);
  if (!Array.isArray(program.steps) || program.steps.length < 1 || program.steps.length > program.limits.max_steps) {
    fail('INVALID_PROGRAM', 'step count exceeds reviewed limits');
  }
  const knownIds = new Set();
  for (const step of program.steps) validateStep(step, knownIds);
  if (typeof program.result !== 'string' || !knownIds.has(program.result)) {
    fail('INVALID_PROGRAM', 'program result must reference a step');
  }
  const resultStep = program.steps.find((step) => step.id === program.result);
  if (!resultStep || resultStep.op !== 'result.object') fail('INVALID_PROGRAM', 'program result must be result.object');
  return program;
}

function canonicalJson(value) {
  if (value === null || typeof value !== 'object') return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(',')}]`;
  return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonicalJson(value[key])}`).join(',')}}`;
}

export async function pureDataProgramDigest(program) {
  validatePureDataProgram(program);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', encoder.encode(canonicalJson(program)));
  const hex = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
  return `sha256:${hex}`;
}

function pointerGet(root, pointer, fallbackMarker) {
  let current = root;
  for (const encodedPart of pointer.slice(1).split('/')) {
    const part = encodedPart.replace(/~1/g, '/').replace(/~0/g, '~');
    if (!isRecord(current) && !Array.isArray(current)) return fallbackMarker;
    if (!Object.prototype.hasOwnProperty.call(current, part)) return fallbackMarker;
    current = current[part];
  }
  return current;
}

function jsonBytes(value) {
  let serialized;
  try { serialized = JSON.stringify(value); } catch { fail('INVALID_VALUE', 'value is not serializable JSON'); }
  if (serialized === undefined) fail('INVALID_VALUE', 'value is not serializable JSON');
  return encoder.encode(serialized).length;
}

function assertTextList(value, limits, label) {
  if (!Array.isArray(value)) fail('INVALID_VALUE', `${label} must be a list`);
  if (value.length > limits.max_list_items) fail('LIST_LIMIT_EXCEEDED', `${label} has too many items`);
  for (const item of value) {
    if (typeof item !== 'string') fail('INVALID_VALUE', `${label} items must be text`);
    if (encoder.encode(item).length > limits.max_text_bytes) fail('TEXT_LIMIT_EXCEEDED', `${label} item is too large`);
  }
}

function asciiCompare(left, right) {
  const leftFolded = left.replace(/[A-Z]/g, (character) => character.toLowerCase());
  const rightFolded = right.replace(/[A-Z]/g, (character) => character.toLowerCase());
  if (leftFolded < rightFolded) return -1;
  if (leftFolded > rightFolded) return 1;
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

function cloneJson(value) {
  return JSON.parse(JSON.stringify(value));
}

export function executePureDataProgram(program, input) {
  validatePureDataProgram(program);
  if (!isRecord(input)) fail('INVALID_VALUE', 'input must be an object');
  const limits = program.limits;
  if (jsonBytes(input) > limits.max_input_bytes) fail('INPUT_LIMIT_EXCEEDED', 'input exceeds reviewed byte limit');
  const values = new Map();
  const missing = Symbol('missing');

  for (const step of program.steps) {
    let value;
    switch (step.op) {
      case 'input.get':
        value = pointerGet(input, step.path, missing);
        if (value === missing) fail('INVALID_VALUE', `input path ${step.path} is missing`);
        value = cloneJson(value);
        break;
      case 'text_list.normalize_ascii': {
        const source = values.get(step.input);
        assertTextList(source, limits, step.input);
        value = source.map((item) => {
          let normalized = step.trim_ascii_whitespace ? item.replace(/^[\x09-\x0D\x20]+|[\x09-\x0D\x20]+$/g, '') : item;
          if (/[^\x00-\x7F]/.test(normalized)) fail('INVALID_VALUE', 'text_list.normalize_ascii requires ASCII text');
          if (step.reject_control_characters && /[\x00-\x1F\x7F]/.test(normalized)) {
            fail('INVALID_VALUE', 'text_list.normalize_ascii rejected a control character');
          }
          if (step.reject_empty && normalized.length === 0) fail('INVALID_VALUE', 'text_list.normalize_ascii rejected empty text');
          if (encoder.encode(normalized).length > limits.max_text_bytes) fail('TEXT_LIMIT_EXCEEDED', 'normalized text is too large');
          return normalized;
        });
        break;
      }
      case 'text_list.unique': {
        const source = values.get(step.input);
        assertTextList(source, limits, step.input);
        const enabled = step.enabled_from
          ? pointerGet(input, step.enabled_from.path, step.enabled_from.default)
          : true;
        if (typeof enabled !== 'boolean') fail('INVALID_VALUE', 'enabled_from value must be boolean');
        value = enabled ? [...new Set(source)] : [...source];
        break;
      }
      case 'text_list.sort_ascii': {
        const source = values.get(step.input);
        assertTextList(source, limits, step.input);
        for (const item of source) if (/[^\x00-\x7F]/.test(item)) fail('INVALID_VALUE', 'text_list.sort_ascii requires ASCII text');
        value = [...source].sort(asciiCompare);
        break;
      }
      case 'list.length': {
        const source = values.get(step.input);
        if (!Array.isArray(source)) fail('INVALID_VALUE', `${step.input} must be a list`);
        if (source.length > limits.max_list_items) fail('LIST_LIMIT_EXCEEDED', `${step.input} has too many items`);
        value = source.length;
        break;
      }
      case 'result.object':
        value = {};
        for (const [field, source] of Object.entries(step.fields)) {
          value[field] = Object.prototype.hasOwnProperty.call(source, 'ref')
            ? cloneJson(values.get(source.ref))
            : cloneJson(source.const);
        }
        break;
      default:
        fail('INVALID_PROGRAM', 'unreachable unsupported operation');
    }
    values.set(step.id, value);
  }

  const result = values.get(program.result);
  if (!isRecord(result)) fail('INVALID_VALUE', 'program result is not an object');
  if (jsonBytes(result) > limits.max_output_bytes) fail('OUTPUT_LIMIT_EXCEEDED', 'output exceeds reviewed byte limit');
  return result;
}

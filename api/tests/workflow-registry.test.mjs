import assert from 'node:assert/strict';
import { workflowRegistration, resolveWorkflow } from '../workflow-registry.js';

const audio=resolveWorkflow('audio-symbolic-animation');
assert.equal(audio.runtimeClass,'media-sequential');
assert.equal(audio.productionAvailable,false);
assert.equal(audio.endpointEnv,'MEDIA_SEQUENTIAL_ENDPOINT');
assert.deepEqual(workflowRegistration(audio),{
  slug:'audio-symbolic-animation',
  version:'1.0.0',
  runtime_class:'media-sequential',
  availability:'fixture_only',
});
assert.equal(resolveWorkflow('woven-storybook-pipeline'),null);
assert.equal(resolveWorkflow('unknown'),null);
console.log('workflow registry tests passed');

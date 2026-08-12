// Safe canonical-control-plane registration boundary. This is metadata only:
// no production provider or endpoint is claimed by this registry.
const WORKFLOWS = Object.freeze({
  'audio-symbolic-animation': Object.freeze({
    slug: 'audio-symbolic-animation',
    version: '1.0.0',
    runtimeClass: 'media-sequential',
    availability: 'fixture_only',
    productionAvailable: false,
    endpointEnv: 'MEDIA_SEQUENTIAL_ENDPOINT',
  }),
});

export function resolveWorkflow(slug) {
  return WORKFLOWS[slug] || null;
}

export function workflowRegistration(workflow) {
  return {
    slug: workflow.slug,
    version: workflow.version,
    runtime_class: workflow.runtimeClass,
    availability: workflow.availability,
  };
}

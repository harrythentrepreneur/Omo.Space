export const FACEBOOK_WORKFLOW = 'facebook-ads-copywriter';

export function storefrontRequest(slug, values, hasManifest) {
  if (slug === FACEBOOK_WORKFLOW) {
    return {
      path: '/v1/runs',
      pollPath: '/v1/runs/',
      payload: {contract_version: '1.0', workflow: {slug, version: '0.1.0'}, input: values},
    };
  }
  return {
    path: '/api/run',
    pollPath: '/api/run/',
    payload: hasManifest ? {slug, input: values} : {slug, fields: values},
  };
}

function scalar(value) {
  return typeof value === 'string' || typeof value === 'number' ? String(value) : '';
}

export function canonicalError(data, fallback = 'The run did not complete.') {
  const run = data && typeof data === 'object' && data.run && typeof data.run === 'object' ? data.run : (data || {});
  const error = run.error ?? (data && data.error);
  if (error && typeof error === 'object') return scalar(error.message) || scalar(error.code) || fallback;
  return scalar(run.message) || scalar(run.reason) || scalar(error) || scalar(data && data.message) || scalar(data && data.reason) || fallback;
}

export function canonicalErrorCode(data) {
  const error = data && typeof data === 'object' ? data.error : null;
  return error && typeof error === 'object' ? scalar(error.code) : '';
}

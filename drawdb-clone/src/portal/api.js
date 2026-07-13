const BASE = import.meta.env.VITE_VALIDATOR_URL || 'http://localhost:8000';

async function req(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch (e) {
    throw new Error(`Validator server unreachable at ${BASE} — is it running? (uvicorn er_validator.api:app --port 8000)`);
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : `request failed (${res.status})`);
  }
  return data;
}

export const health = () => req('/health');
export const listQuestions = () => req('/questions');
export const getQuestion = (id, includeReference = false) =>
  req(`/questions/${id}${includeReference ? '?include_reference=true' : ''}`);
export const createQuestion = (title, prompt, reference) =>
  req('/questions', { method: 'POST', body: { title, prompt, reference } });
export const deleteQuestion = (id) => req(`/questions/${id}`, { method: 'DELETE' });
export const submitAnswer = (id, student, algorithm) =>
  req(`/questions/${id}/submit`, { method: 'POST', body: { student, algorithm } });

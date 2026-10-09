/* ============================================================
   API client
   ------------------------------------------------------------
   Thin fetch wrapper. Reads JWT from localStorage and injects
   the Authorization header on every request. Handles common
   error cases with a single `request()` function.
   ============================================================ */

const API_BASE = ''; // same-origin

const Storage = {
  TOKEN_KEY: 'scx_token',
  USER_KEY:  'scx_user',
  getToken() { return localStorage.getItem(this.TOKEN_KEY); },
  setToken(t) { localStorage.setItem(this.TOKEN_KEY, t); },
  getUser() {
    const u = localStorage.getItem(this.USER_KEY);
    return u ? JSON.parse(u) : null;
  },
  setUser(u) { localStorage.setItem(this.USER_KEY, JSON.stringify(u)); },
  clear() {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  },
};

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === 'string' ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request(method, path, { body, formData, query } = {}) {
  const url = new URL(API_BASE + path, window.location.origin);
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, v);
    });
  }

  const headers = {};
  const token = Storage.getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  let payload;
  if (formData) {
    payload = formData; // browser sets multipart boundary automatically
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  const res = await fetch(url.toString(), { method, headers, body: payload });

  if (res.status === 401 && !path.startsWith('/api/auth')) {
    Storage.clear();
    window.location.href = '/login.html';
    throw new ApiError(401, 'Session expired');
  }

  let data;
  const text = await res.text();
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }

  if (!res.ok) {
    const detail = data?.detail || data || res.statusText;
    throw new ApiError(res.status, detail);
  }
  return data;
}

// ============================================================
// Domain-specific endpoint helpers
// ============================================================
const Api = {
  // Auth
  async register(payload)   { return request('POST', '/api/auth/register', { body: payload }); },
  async login(username, password) {
    const fd = new FormData();
    fd.append('username', username);
    fd.append('password', password);
    return request('POST', '/api/auth/login', { formData: fd });
  },
  async me() { return request('GET', '/api/auth/me'); },

  // Projects
  async listProjects()                    { return request('GET',    '/api/projects'); },
  async createProject(name, description)  { return request('POST',   '/api/projects', { body: { name, description } }); },
  async getProject(id)                    { return request('GET',    `/api/projects/${id}`); },
  async deleteProject(id)                 { return request('DELETE', `/api/projects/${id}`); },

  // Datasets
  async listDatasets(projectId) { return request('GET', `/api/projects/${projectId}/datasets`); },
  async uploadDataset(projectId, file) {
    const fd = new FormData();
    fd.append('file', file);
    return request('POST', `/api/projects/${projectId}/datasets/upload`, { formData: fd });
  },
  async createDemoDataset(projectId, params = {}) {
    return request('POST', `/api/projects/${projectId}/datasets/demo`, { query: params });
  },
  async deleteDataset(datasetId) { return request('DELETE', `/api/datasets/${datasetId}`); },

  // Analysis
  async createAnalysis(payload)         { return request('POST',   '/api/analysis', { body: payload }); },
  async listAnalyses(projectId)         { return request('GET',    `/api/projects/${projectId}/analysis`); },
  async getAnalysis(runId)              { return request('GET',    `/api/analysis/${runId}`); },
  async getAnalysisLogs(runId, limit=200) { return request('GET',  `/api/analysis/${runId}/logs`, { query: { limit } }); },
  async getAnalysisResults(runId)       { return request('GET',    `/api/analysis/${runId}/results`); },
  async deleteAnalysis(runId)           { return request('DELETE', `/api/analysis/${runId}`); },
};

// ============================================================
// Auth guard for protected pages
// ============================================================
function requireAuth() {
  if (!Storage.getToken()) {
    window.location.href = '/login.html';
    return false;
  }
  return true;
}

function logout() {
  Storage.clear();
  window.location.href = '/login.html';
}

// ============================================================
// Small toast notifications
// ============================================================
function toast(message, type = 'info') {
  const el = document.createElement('div');
  el.className = `alert alert-${type}`;
  el.style.cssText = 'position:fixed;top:80px;right:24px;z-index:2000;min-width:280px;box-shadow:0 12px 36px rgba(0,0,0,0.5);animation:slideIn .25s ease;';
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => {
    el.style.transition = 'opacity .3s';
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

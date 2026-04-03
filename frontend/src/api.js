const explicitApiBase = import.meta.env.VITE_API_BASE_URL;
const apiHost = import.meta.env.VITE_API_HOST;
const apiScheme = import.meta.env.VITE_API_SCHEME || 'https';

const API_BASE = explicitApiBase || (apiHost ? `${apiScheme}://${apiHost}` : '/api');

const TOKEN_KEY = 'trailmetrics_auth_token';
const ROLE_KEY = 'trailmetrics_auth_role';

let authToken = localStorage.getItem(TOKEN_KEY) || '';
let authRole = localStorage.getItem(ROLE_KEY) || '';

export function getAuthToken() {
  return authToken;
}

export function getAuthRole() {
  return authRole;
}

export function setAuthToken(token, role = '') {
  authToken = token || '';
  authRole = role || '';
  if (authToken) {
    localStorage.setItem(TOKEN_KEY, authToken);
    if (authRole) {
      localStorage.setItem(ROLE_KEY, authRole);
    }
  } else {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
  }
}

async function apiFetch(path, options = {}) {
  const headers = {
    ...(options.headers || {}),
  };

  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export async function login(username, password) {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ username, password })
  });

  if (!response.ok) {
    throw new Error('Invalid username or password');
  }

  return response.json();
}

export async function recomputeRollups() {
  return apiFetch('/metrics/rollups/recompute', { method: 'POST' });
}

export async function evaluateSlosNow() {
  return apiFetch('/slo/evaluate', { method: 'POST' });
}

export async function fetchServices() {
  return apiFetch('/metrics/services');
}

export async function fetchRollups(window = '1m', serviceName = '') {
  const query = new URLSearchParams({ window });
  if (serviceName) {
    query.set('service_name', serviceName);
  }
  return apiFetch(`/metrics/rollups?${query.toString()}`);
}

export async function fetchSlos(serviceName = '') {
  const query = new URLSearchParams();
  if (serviceName) {
    query.set('service_name', serviceName);
  }
  return apiFetch(`/slo/status?${query.toString()}`);
}

export async function fetchAlerts(limit = 25) {
  return apiFetch(`/alerts/history?limit=${limit}`);
}

export function metricsSocketUrl() {
  if (API_BASE.startsWith('http://') || API_BASE.startsWith('https://')) {
    const base = API_BASE.replace('http://', 'ws://').replace('https://', 'wss://');
    return `${base}/metrics/ws/metrics?token=${encodeURIComponent(authToken)}`;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${protocol}://${window.location.host}${API_BASE}/metrics/ws/metrics?token=${encodeURIComponent(authToken)}`;
}

// Centralized API Base Configuration for Local Dev & Render Production Deployment
export const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
export const BACKEND_URL = isLocal ? 'http://127.0.0.1:8000' : 'https://aduanflow-backend.onrender.com';
export const API_BASE = isLocal ? '' : 'https://aduanflow-backend.onrender.com';

export function apiFetch(path, options) {
  const url = path.startsWith('http') ? path : `${API_BASE}${path.startsWith('/') ? path : '/' + path}`;
  return fetch(url, options);
}

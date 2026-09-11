import axios from 'axios';

// When running with Vite dev server, /api proxies to Flask on port 5000
// Fallback directly to port 5000 if not proxying
export const API_BASE = '/api';

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 300000,
});

export default api;

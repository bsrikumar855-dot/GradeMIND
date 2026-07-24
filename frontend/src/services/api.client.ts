import axios from 'axios';
import { getCookie, eraseCookie } from '../utils/cookies';

// Create Axios instance - Backend has NO /api prefix on its routes
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach the bearer token from the auth cookie to every request. Without
// this, every call fails with 401 once the backend has AUTH_ENABLED=True
// (the default) — auth.service.ts stores the token in a cookie but nothing
// was reading it back out for outgoing requests.
apiClient.interceptors.request.use((config) => {
  const token = getCookie('grademind_auth');
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On an expired/invalid session, clear stale cookies and send the user back
// to login instead of leaving the app stuck on silently-failing requests.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      typeof window !== 'undefined' &&
      window.location.pathname !== '/login'
    ) {
      eraseCookie('grademind_auth');
      eraseCookie('grademind_refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);


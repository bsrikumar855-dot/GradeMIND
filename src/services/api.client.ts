import axios, { AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// Create Axios instance pointing to FastAPI root (no /api suffix)
export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Inject Authorization JWT token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      // Check for production token, fallback to mock token
      const token = localStorage.getItem('grademind_auth_token') || localStorage.getItem('grademind_mock_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error: AxiosError) => {
    console.error('[API Request Error]:', error);
    return Promise.reject(error);
  }
);

// Response Interceptor: Handle global errors (e.g. 401 Unauthorized, 500 Internal Error)
apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response;
  },
  (error: AxiosError) => {
    const status = error.response?.status;

    if (status === 401) {
      if (typeof window !== 'undefined') {
        // Clear all token storage on authorization failure
        localStorage.removeItem('grademind_auth_token');
        localStorage.removeItem('grademind_mock_token');
        document.cookie = "grademind_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
        window.location.href = '/login';
      }
    } else if (status === 403) {
      console.warn('[API Forbidden]: User does not have privileges for this action.');
    } else if (status === 500) {
      console.error('[API Server Error 500]:', error.response?.data || error.message);
    } else if (error.code === 'ECONNABORTED') {
      console.error('[API Timeout Error]: The server took too long to respond.');
    } else {
      console.error('[API Network/Unknown Error]:', error.message);
    }

    return Promise.reject(error);
  }
);


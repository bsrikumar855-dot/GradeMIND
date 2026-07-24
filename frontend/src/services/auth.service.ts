import { apiClient } from './api.client';
import { getCookie, setCookie, eraseCookie } from '../utils/cookies';

const normalizeUser = (user: any) => ({
  ...user,
  role: typeof user?.role === 'string' ? user.role.toLowerCase() : user?.role,
});

export const AuthService = {
  login: async (email?: string, password?: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    const { success, data, message } = response.data;
    if (success && data) {
      const { access_token, refresh_token } = data;
      setCookie('grademind_auth', access_token, 1);
      setCookie('grademind_refresh_token', refresh_token, 7);

      // Perform a follow-up request to /auth/me to fetch profile details
      const meResponse = await apiClient.get('/auth/me');
      const meData = normalizeUser(meResponse.data.data);

      if (typeof window !== 'undefined') {
        localStorage.setItem('grademind_user', JSON.stringify(meData));
      }
      return { token: access_token, user: meData };
    }
    throw new Error(message || 'Login failed');
  },

  register: async (name?: string, email?: string, role?: string, password?: string) => {
    if (!password) {
      throw new Error('Password is required for registration.');
    }
    const response = await apiClient.post('/auth/register', {
      name,
      email,
      role: role ? role.toUpperCase() : 'TEACHER',
      password
    });
    return response.data;
  },

  getCurrentSession: async () => {
    try {
      const token = getCookie('grademind_auth');
      if (!token) return null;

      const response = await apiClient.get('/auth/me');
      const { success, data } = response.data;
      if (success && data) {
        const user = normalizeUser(data);
        if (typeof window !== 'undefined') {
          localStorage.setItem('grademind_user', JSON.stringify(user));
        }
        return { token, user };
      }
      return null;
    } catch (error) {
      return null;
    }
  },

  getCurrentUser: () => {
    if (typeof window !== 'undefined') {
      const u = localStorage.getItem('grademind_user');
      return u ? JSON.parse(u) : null;
    }
    return null;
  },

  refresh: async () => {
    const refreshToken = getCookie('grademind_refresh_token');
    if (!refreshToken) throw new Error('No refresh token available');
    const response = await apiClient.post('/auth/refresh', { refresh_token: refreshToken });
    const { success, data } = response.data;
    if (success && data) {
      const { access_token, refresh_token } = data;
      setCookie('grademind_auth', access_token, 1);
      setCookie('grademind_refresh_token', refresh_token, 7);
      return { token: access_token };
    }
    throw new Error('Refresh failed');
  },

  logout: async () => {
    try {
      const refreshToken = getCookie('grademind_refresh_token');
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch (error) {
      // Ignore logout API failures and clear client cookies anyway
    } finally {
      eraseCookie('grademind_auth');
      eraseCookie('grademind_refresh_token');
      if (typeof window !== 'undefined') {
        localStorage.removeItem('grademind_user');
        window.location.href = '/login';
      }
    }
  },

  isAuthenticated: () => {
    return !!getCookie('grademind_auth');
  }
};

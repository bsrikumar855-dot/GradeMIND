import { apiClient, setTokens, clearTokens, getAccessToken, getRefreshToken } from './api.client';

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  id: string;
  name: string;
  email: string;
  role: string;
}

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: string;
}

export const AuthService = {
  /**
   * Authenticate with the backend /auth/login endpoint.
   * Stores tokens in localStorage and sets the auth cookie for Next.js middleware.
   */
  login: async (email: string, password: string) => {
    const response = await apiClient.post('/auth/login', { email, password });
    // Backend wraps in {success, message, data}
    const tokenData: LoginResponse = response.data.data || response.data;

    setTokens(tokenData.access_token, tokenData.refresh_token);

    // Fetch user profile after login
    const userProfile = await AuthService.getCurrentSession();
    return {
      token: tokenData.access_token,
      user: userProfile?.user || { id: '', name: email, email, role: 'teacher', createdAt: '' },
    };
  },

  /**
   * Register a new user via /auth/register.
   */
  register: async (name: string, email: string, password: string) => {
    const response = await apiClient.post('/auth/register', { name, email, password });
    const data: RegisterResponse = response.data.data || response.data;
    return { success: true, user: data };
  },

  /**
   * Fetch the currently authenticated user's profile via /auth/me.
   * Returns null if no access token is stored or the token is invalid.
   */
  getCurrentSession: async () => {
    const token = getAccessToken();
    if (!token) return null;

    try {
      const response = await apiClient.get('/auth/me');
      const userData: UserProfile = response.data.data || response.data;
      return {
        token,
        user: {
          id: String(userData.id),
          name: userData.name,
          email: userData.email,
          role: userData.role.toLowerCase() as 'teacher' | 'admin' | 'evaluator',
          createdAt: '',
        },
      };
    } catch {
      // Token is invalid/expired - the interceptor will try to refresh
      return null;
    }
  },

  /**
   * Logout by revoking the refresh token on the server, then clear local storage.
   */
  logout: async () => {
    const refreshToken = getRefreshToken();
    try {
      if (refreshToken) {
        await apiClient.post('/auth/logout', { refresh_token: refreshToken });
      }
    } catch {
      // Ignore errors during logout - we clear tokens regardless
    } finally {
      clearTokens();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
    }
  },

  /**
   * Check if user has a stored access token (basic client-side check).
   */
  isAuthenticated: () => {
    return !!getAccessToken();
  },
};

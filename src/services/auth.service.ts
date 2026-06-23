import { User } from '@/types';

export const AuthService = {
  login: async (_email?: string, _password?: string) => {
    void _email;
    void _password;
    return new Promise<{ token: string; user: User }>((resolve) => {
      setTimeout(() => {
        const mockToken = 'mock_jwt_token_12345';
        if (typeof window !== 'undefined') {
          localStorage.setItem('grademind_mock_token', mockToken);
          document.cookie = `grademind_auth=${mockToken}; path=/`;
        }
        resolve({ token: mockToken, user: { id: 'u123', email: 'jane.doe@school.edu', name: 'Dr. Jane Doe', role: 'teacher', createdAt: new Date().toISOString() } as User });
      }, 800);
    });
  },

  register: async (_name?: string, _email?: string, _role?: string) => {
    void _name;
    void _email;
    void _role;
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve({ success: true });
      }, 800);
    });
  },

  getCurrentSession: async () => {
    if (typeof window !== 'undefined' && localStorage.getItem('grademind_mock_token')) {
      return { token: localStorage.getItem('grademind_mock_token'), user: { id: 'u123', email: 'jane.doe@school.edu', name: 'Dr. Jane Doe', role: 'teacher', createdAt: new Date().toISOString() } as User };
    }
    return null;
  },

  logout: async () => {
    if (typeof window !== 'undefined') {
      localStorage.removeItem('grademind_mock_token');
      document.cookie = "grademind_auth=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;";
      window.location.href = '/login';
    }
  },

  isAuthenticated: () => {
    if (typeof window !== 'undefined') {
      return !!localStorage.getItem('grademind_mock_token');
    }
    return false;
  }
};

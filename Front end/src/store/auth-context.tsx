"use client";

import * as React from "react";
import { User } from "@/types";
import { AuthService } from "@/services/auth.service";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const AuthContext = React.createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = React.useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  // Restore session on mount by calling /auth/me
  React.useEffect(() => {
    const restoreSession = async () => {
      try {
        const session = await AuthService.getCurrentSession();
        if (session) {
          setState({
            user: session.user,
            token: session.token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } else {
          setState((prev) => ({ ...prev, isLoading: false }));
        }
      } catch {
        setState({
          user: null,
          token: null,
          isAuthenticated: false,
          isLoading: false,
          error: null, // Don't show error on initial load failure
        });
      }
    };

    restoreSession();
  }, []);

  const login = async (email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const session = await AuthService.login(email, password);
      setState({
        user: session.user,
        token: session.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: unknown) {
      // Extract error message from backend response
      let errorMessage = "Login failed.";
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string; message?: string } } };
        errorMessage = axiosError.response?.data?.detail
          || axiosError.response?.data?.message
          || errorMessage;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw err;
    }
  };

  const register = async (name: string, email: string, password: string) => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      await AuthService.register(name, email, password);
      setState((prev) => ({ ...prev, isLoading: false }));
    } catch (err: unknown) {
      let errorMessage = "Registration failed.";
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response?: { data?: { detail?: string; message?: string } } };
        errorMessage = axiosError.response?.data?.detail
          || axiosError.response?.data?.message
          || errorMessage;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      }
      setState((prev) => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
      throw err;
    }
  };

  const logout = async () => {
    setState((prev) => ({ ...prev, isLoading: true }));
    try {
      await AuthService.logout();
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    } catch {
      // Even if logout API fails, clear local state
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      });
    }
  };

  const clearError = () => {
    setState((prev) => ({ ...prev, error: null }));
  };

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, clearError }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

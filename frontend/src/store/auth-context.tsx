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

  React.useEffect(() => {
    let active = true;

    AuthService.getCurrentSession()
      .then((session) => {
        if (!active) return;
        if (session) {
          setState({
            user: session.user,
            token: session.token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } else {
          setState((prev) => ({ ...prev, isLoading: false, isAuthenticated: false, user: null, token: null }));
        }
      })
      .catch(() => {
        if (!active) return;
        setState((prev) => ({ ...prev, isLoading: false, isAuthenticated: false, user: null, token: null }));
      });

    return () => {
      active = false;
    };
  }, []);

  const logout = async () => {
    setState((prev) => ({ ...prev, error: null }));
    await AuthService.logout();
  };

  const clearError = () => {
    setState((prev) => ({ ...prev, error: null }));
  };

  return (
    <AuthContext.Provider value={{ ...state, logout, clearError }}>
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

"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  tenant_id: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    setUser(null);
    setToken(null);
    if (typeof window !== "undefined") {
      localStorage.removeItem("glasswatch_token");
    }
  }, []);

  const fetchUserProfile = useCallback(async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.status === 401) {
        logout();
        return;
      }

      if (!response.ok) {
        throw new Error("Failed to fetch user profile");
      }

      const userData = await response.json();
      setUser(userData);
    } catch (error) {
      console.error("Failed to fetch user profile:", error);
      logout();
    }
  }, [logout]);

  const login = useCallback(async (authToken: string) => {
    setToken(authToken);
    if (typeof window !== "undefined") {
      localStorage.setItem("glasswatch_token", authToken);
    }
    await fetchUserProfile(authToken);
  }, [fetchUserProfile]);

  // Load token from localStorage on mount
  useEffect(() => {
    const loadAuth = async () => {
      if (typeof window === "undefined") {
        setIsLoading(false);
        return;
      }

      const storedToken = localStorage.getItem("glasswatch_token");
      if (storedToken) {
        setToken(storedToken);
        await fetchUserProfile(storedToken);
      }
      setIsLoading(false);
    };

    loadAuth();
  }, [fetchUserProfile]);

  const value: AuthContextType = {
    user,
    token,
    isAuthenticated: !!user && !!token,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Axios interceptor helper for auto-logout on 401
export function setupAuthInterceptor(logout: () => void) {
  // This would be called in an axios setup file
  // For now, we'll handle 401s in individual fetch calls
  return () => {
    // Cleanup function
  };
}

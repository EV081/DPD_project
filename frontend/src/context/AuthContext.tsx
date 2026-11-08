'use client';

import React, { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { api, TOKEN_KEY, UNAUTHORIZED_EVENT } from '@/lib/client';

export interface User { id: number; name: string; email: string }

interface AuthContextType {
  token: string | null;
  user: User | null;
  setUser: React.Dispatch<React.SetStateAction<User | null>>;
  loading: boolean;
  connectionError: boolean;
  retry: () => void;
  login: (email: string, pass: string) => Promise<void>;
  register: (name: string, email: string, pass: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  updateProfile: (data: { name?: string; email?: string; password?: string }) => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({} as AuthContextType);

export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [connectionError, setConnectionError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    setConnectionError(false);
    setLoading(true);
    let cancelled = false;
    (async () => {
      for (let i = 0; i < 3 && !cancelled; i++) {
        try {
          const res = await api.get('/auth/me');
          if (!cancelled) setUser(res.data.user || res.data);
          if (!cancelled) setLoading(false);
          return;
        } catch (e: any) {
          if (e?.response?.status === 401) { if (!cancelled) { clearSession(); setLoading(false); } return; }
          await new Promise((r) => setTimeout(r, 1500 * (i + 1)));
        }
      }
      if (!cancelled) { setConnectionError(true); setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [attempt, clearSession]);

  useEffect(() => {
    window.addEventListener(UNAUTHORIZED_EVENT, clearSession);
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, clearSession);
  }, [clearSession]);

  const login = async (email: string, password: string) => {
    const res = await api.post('/auth/login', { email, password });
    const accessToken = res.data.access_token;
    localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
    setUser(res.data.user || res.data);
  };

  const register = async (name: string, email: string, password: string) => {
    await api.post('/auth/register', { name, email, password });
    await login(email, password);
  };

  const updateProfile = async (data: { name?: string; email?: string; password?: string }) => {
    const res = await api.put('/auth/profile', data);
    setUser(res.data.user || res.data);
  };

  const logout = clearSession;

  return (
    <AuthContext.Provider value={{ token, user, setUser, loading, connectionError, retry: () => setAttempt((n) => n + 1), login, register, logout, isAuthenticated: !!token, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
}
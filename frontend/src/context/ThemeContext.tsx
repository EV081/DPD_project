'use client';

import { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type ThemePreference = 'light' | 'dark' | 'system';
export const THEME_KEY = 'urbansafe_theme';

interface ThemeContextType {
  preference: ThemePreference;
  resolved: 'light' | 'dark';
  setPreference: (p: ThemePreference) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  preference: 'system', resolved: 'light', setPreference: () => {},
});

export const useTheme = () => useContext(ThemeContext);

const systemPrefersDark = () => window.matchMedia('(prefers-color-scheme: dark)').matches;

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [preference, setPref] = useState<ThemePreference>('system');
  const [resolved, setResolved] = useState<'light' | 'dark'>('light');

  const apply = useCallback((p: ThemePreference) => {
    const dark = p === 'dark' || (p === 'system' && systemPrefersDark());
    document.documentElement.classList.toggle('dark', dark);
    setResolved(dark ? 'dark' : 'light');
  }, []);

  // El script inline de layout.tsx ya puso la clase antes de pintar: aquí solo se sincroniza el estado
  useEffect(() => {
    const stored = localStorage.getItem(THEME_KEY) as ThemePreference | null;
    const p = stored === 'light' || stored === 'dark' ? stored : 'system';
    setPref(p);
    apply(p);
  }, [apply]);

  // Con "Sistema", seguir los cambios del sistema operativo
  useEffect(() => {
    if (preference !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = () => apply('system');
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [preference, apply]);

  const setPreference = (p: ThemePreference) => {
    setPref(p);
    if (p === 'system') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, p);
    apply(p);
  };

  return <ThemeContext.Provider value={{ preference, resolved, setPreference }}>{children}</ThemeContext.Provider>;
}

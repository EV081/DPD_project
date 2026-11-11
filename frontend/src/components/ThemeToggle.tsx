'use client';

import { SegmentedControl } from '@mantine/core';
import { Moon, Sun, Monitor } from 'lucide-react';
import { useTheme, ThemePreference } from '@/context/ThemeContext';

// Botón simple: alterna claro/oscuro
export function ThemeToggle({ className = '' }: { className?: string }) {
  const { resolved, setPreference } = useTheme();
  const dark = resolved === 'dark';
  return (
    <button
      type="button"
      onClick={() => setPreference(dark ? 'light' : 'dark')}
      aria-label={dark ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
      title={dark ? 'Tema claro' : 'Tema oscuro'}
      className={`btn btn-ghost !p-2 ${className}`}
    >
      {dark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

const OPTIONS: { id: ThemePreference; label: string; icon: typeof Sun }[] = [
  { id: 'light', label: 'Claro', icon: Sun },
  { id: 'dark', label: 'Oscuro', icon: Moon },
  { id: 'system', label: 'Sistema', icon: Monitor },
];

// Selector de tres opciones (página de cuenta)
export function ThemeSelector() {
  const { preference, setPreference } = useTheme();
  return <SegmentedControl fullWidth value={preference} onChange={(value) => setPreference(value as ThemePreference)}
    aria-label="Tema" data={OPTIONS.map(({ id, label, icon: Icon }) => ({ value: id,
      label: <span className="flex items-center justify-center gap-2"><Icon size={16} />{label}</span> }))} />;
}

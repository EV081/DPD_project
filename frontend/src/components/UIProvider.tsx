'use client';

import { useMemo } from 'react';
import { MantineProvider, createTheme, type CSSVariablesResolver } from '@mantine/core';
import { ThemeProvider, createTheme as createMuiTheme } from '@mui/material/styles';
import { useTheme } from '@/context/ThemeContext';

const theme = createTheme({
  primaryColor: 'blue', primaryShade: { light: 7, dark: 4 },
  fontFamily: 'var(--font-inter), sans-serif', defaultRadius: 'md',
  headings: { fontFamily: 'var(--font-inter), sans-serif' },
  components: {
    TextInput: { defaultProps: { size: 'md' }, styles: { input: { background: 'var(--surface-2)', borderColor: 'var(--line)', color: 'var(--fg)' } } },
    PasswordInput: { defaultProps: { size: 'md' } },
    Button: { defaultProps: { size: 'md' } },
    SegmentedControl: { styles: { root: { background: 'var(--surface-2)' }, indicator: { background: 'var(--surface)' }, label: { color: 'var(--fg)' } } },
  },
});
const resolver: CSSVariablesResolver = () => ({
  variables: { '--mantine-color-body': 'var(--bg)', '--mantine-color-text': 'var(--fg)' },
  light: { '--mantine-color-dimmed': 'var(--muted)' },
  dark: { '--mantine-color-dimmed': 'var(--muted)' },
});

export default function UIProvider({ children }: { children: React.ReactNode }) {
  const { resolved } = useTheme();
  const mui = useMemo(() => createMuiTheme({
    palette: { mode: resolved, primary: { main: resolved === 'dark' ? '#4f8dff' : '#2563eb' } },
    typography: { fontFamily: 'var(--font-inter), sans-serif' },
    shape: { borderRadius: 12 },
  }), [resolved]);
  return <MantineProvider theme={theme} forceColorScheme={resolved} cssVariablesResolver={resolver}>
    <ThemeProvider theme={mui}>{children}</ThemeProvider>
  </MantineProvider>;
}

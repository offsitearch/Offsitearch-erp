import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  resolved: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
}

function getSystemTheme(): 'light' | 'dark' {
  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function applyTheme(resolved: 'light' | 'dark') {
  const root = document.documentElement;
  if (resolved === 'dark') {
    root.classList.add('dark');
  } else {
    root.classList.remove('dark');
  }
}

export const useTheme = create<ThemeState>()(
  persist(
    (set) => ({
      theme: 'system',
      resolved: getSystemTheme(),
      setTheme: (theme: Theme) => {
        const resolved = theme === 'system' ? getSystemTheme() : theme;
        applyTheme(resolved);
        set({ theme, resolved });
      },
    }),
    { name: 'studio-erp-theme' },
  ),
);

if (typeof window !== 'undefined') {
  const stored = localStorage.getItem('studio-erp-theme');
  if (stored) {
    try {
      const parsed = JSON.parse(stored);
      const theme: Theme | undefined = parsed.state?.theme;
      const resolved =
        !theme || theme === 'system'
          ? getSystemTheme()
          : theme === 'dark'
            ? 'dark'
            : 'light';
      applyTheme(resolved);
      useTheme.setState({ resolved });
    } catch {
      applyTheme(getSystemTheme());
    }
  } else {
    applyTheme(getSystemTheme());
  }

  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const { theme } = useTheme.getState();
    if (theme === 'system') {
      const resolved = getSystemTheme();
      applyTheme(resolved);
      useTheme.setState({ resolved });
    }
  });
}

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

export type ThemeName = 'dark' | 'light'

const STORAGE_KEY = 'instamart.theme'

interface ThemeContextValue {
  theme: ThemeName
  setTheme: (theme: ThemeName) => void
  toggleTheme: () => void
}

const ThemeContext = createContext<ThemeContextValue | null>(null)

export function getStoredTheme(): ThemeName {
  if (typeof window === 'undefined') return 'dark'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'light' ? 'light' : 'dark'
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setThemeState] = useState<ThemeName>(getStoredTheme)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    document.documentElement.style.colorScheme = theme
    window.localStorage.setItem(STORAGE_KEY, theme)
  }, [theme])

  const setTheme = useCallback((next: ThemeName) => setThemeState(next), [])
  const toggleTheme = useCallback(
    () => setThemeState((current) => (current === 'dark' ? 'light' : 'dark')),
    [],
  )

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme],
  )

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

const CHART_PALETTES = {
  dark: {
    accent: '#8b9bff',
    accent2: '#c084fc',
    warn: '#fbbf24',
    positive: '#34d399',
    negative: '#f87171',
    neutral: '#8f89a6',
    mixed: '#c084fc',
    axis: '#a29cb8',
    tooltipBg: '#16121f',
    tooltipLine: 'rgba(255, 255, 255, 0.12)',
  },
  light: {
    accent: '#4f46e5',
    accent2: '#9333ea',
    warn: '#b8860b',
    positive: '#15803d',
    negative: '#9f2d2d',
    neutral: '#7d839c',
    mixed: '#9333ea',
    axis: '#5f657f',
    tooltipBg: '#fdfdff',
    tooltipLine: '#dcdfef',
  },
} as const

/** Chart libraries need literal colors, so palettes mirror the CSS theme tokens. */
export function useChartColors() {
  const { theme } = useTheme()
  return CHART_PALETTES[theme]
}

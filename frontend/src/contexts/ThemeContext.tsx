import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'

type Theme = 'light' | 'dark'

interface ThemeCtx {
  theme: Theme
  toggle: () => void
  isDark: boolean
}

const ThemeContext = createContext<ThemeCtx>({ theme: 'light', toggle: () => {}, isDark: false })

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    if (typeof window === 'undefined') return 'light'
    const stored = localStorage.getItem('theme')
    // Only apply dark if explicitly saved as 'dark'; default to light
    return stored === 'dark' ? 'dark' : 'light'
  })

  useEffect(() => {
    const root = document.documentElement
    if (theme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggle = () => setTheme(t => t === 'light' ? 'dark' : 'light')

  return (
    <ThemeContext.Provider value={{ theme, toggle, isDark: theme === 'dark' }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}

export function useChartTheme() {
  const { isDark } = useTheme()
  return {
    gridColor: isDark ? '#2D3144' : '#E4E4E7',
    textColor: isDark ? '#9CA3AF' : '#6E7191',
    tooltipBg: isDark ? '#0F1117' : '#1A1A2E',
    cardBg: isDark ? '#1A1D27' : '#FFFFFF',
    bgPrimary: isDark ? '#0F1117' : '#F3F4F6',
    bgCard: isDark ? '#1A1D27' : '#FFFFFF',
    bgInput: isDark ? '#242736' : '#FFFFFF',
    borderColor: isDark ? '#2D3144' : '#E5E7EB',
    textPrimary: isDark ? '#F3F4F6' : '#111827',
    textSecondary: isDark ? '#9CA3AF' : '#6B7280',
    textMuted: isDark ? '#6B7280' : '#9CA3AF',
  }
}

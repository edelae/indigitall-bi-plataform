/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1E88E5', dark: '#1565C0', light: '#42A5F5' },
        secondary: { DEFAULT: '#76C043', dark: '#5EA832' },
        warning: '#FFC107',
        error: '#EF4444',
        accent: { purple: '#9C27B0', orange: '#FF5722' },
        surface: '#F5F7FA',
        border: '#E4E4E7',
        'border-light': '#F0F0F5',
        'text-dark': '#1A1A2E',
        'text-muted': '#6E7191',
        'text-light': '#A0A3BD',
        // Dark mode specific
        dark: {
          bg: '#0F1117',
          card: '#1A1D27',
          input: '#242736',
          border: '#2D3144',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      borderRadius: {
        card: '12px',
        btn: '8px',
        pill: '24px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(0, 0, 0, 0.08)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.12)',
      },
    },
  },
  plugins: [],
}

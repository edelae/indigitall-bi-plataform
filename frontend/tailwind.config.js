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
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
        btn: '8px',
        pill: '24px',
      },
      boxShadow: {
        card: '0 4px 24px rgba(0, 0, 0, 0.06)',
        'card-hover': '0 8px 32px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#f8fafc',
        surface: '#ffffff',
        textMain: '#0f172a',
        textMuted: '#475569',
        accent: '#0ea5e9',
        accentHover: '#0284c7',
        medicalBlue: '#1e3a8a',
        medicalCyan: '#ecfeff',
        slateBlue: '#e2e8f0', // Used for SEARCH tag (light mode)
        successGreen: '#16a34a', // Used for ANSWER tag
        alertRed: '#ef4444',
      },
      fontFamily: {
        serif: ['"DM Serif Display"', 'serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
        sans: ['"DM Sans"', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

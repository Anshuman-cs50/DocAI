/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: '#0f1623',
        textMain: '#e8e4dc',
        accent: '#c9924a',
        mutedTeal: '#2a6b6b',
        slateBlue: '#4b5563', // Used for SEARCH tag
        successGreen: '#16a34a', // Used for ANSWER tag
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

/** @type {import('tailwindcss').Config} */

// Colours are driven by CSS custom properties (see src/index.css :root and
// src/theme/ThemeProvider.jsx). Each token resolves to `rgb(var(--color-x) /
// <alpha-value>)` so Tailwind opacity modifiers (e.g. `bg-ink-900/40`) keep
// working while the raw channel triplets are swapped at runtime to switch
// colour schemes.
const withVar = (name) => `rgb(var(--color-${name}) / <alpha-value>)`

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['var(--ijm-font-sans)'],
        sans:    ['var(--ijm-font-sans)'],
        mono:    ['var(--ijm-font-mono)'],
      },
      colors: {
        ink: {
          950: withVar('ink-950'),
          900: withVar('ink-900'),
          800: withVar('ink-800'),
          700: withVar('ink-700'),
          600: withVar('ink-600'),
          500: withVar('ink-500'),
          400: withVar('ink-400'),
          300: withVar('ink-300'),
          200: withVar('ink-200'),
          100: withVar('ink-100')
        },
        acid:      withVar('acid'),
        danger:    withVar('danger'),
        warning:   withVar('warning'),
        success:   withVar('success'),
        secondary: withVar('secondary')
      }
    }
  },
  plugins: []
}

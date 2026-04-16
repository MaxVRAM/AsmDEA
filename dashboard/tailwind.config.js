/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        sans: ['"IBM Plex Sans"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'ui-monospace', 'monospace']
      },
      colors: {
        ink: {
          950: '#0a0a0b',
          900: '#131316',
          800: '#1c1c21',
          700: '#242429',
          600: '#34343c',
          500: '#54545f',
          400: '#8a8880',
          300: '#b8b5a8',
          200: '#d4d1c4',
          100: '#e8e6e0'
        },
        acid: '#d4ff3a',
        danger: '#ff5757',
        warning: '#ffb547',
        success: '#4ade80'
      }
    }
  },
  plugins: []
}

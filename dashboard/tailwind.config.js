/** @type {import('tailwindcss').Config} */
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
          950: '#111118',
          900: '#1b1b23',
          800: '#24242e',
          700: '#313139',
          600: '#434350',
          500: '#686676',
          400: '#9e9b94',
          300: '#bfbdb3',
          200: '#d8d5cc',
          100: '#edeae4'
        },
        acid: '#c8f232',
        danger: '#ff5757',
        warning: '#ffb547',
        success: '#4ade80'
      }
    }
  },
  plugins: []
}

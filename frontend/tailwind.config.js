/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#07100d',
        panel: '#0b1713',
        panel2: '#0e1e18',
        line: '#1d352b',
        acid: '#d7ff57',
        mint: '#73f0b6',
      },
      boxShadow: { glow: '0 0 40px rgba(215,255,87,.08)' },
      fontFamily: { display: ['Space Grotesk', 'ui-sans-serif', 'system-ui'], sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
    },
  },
  plugins: [],
}

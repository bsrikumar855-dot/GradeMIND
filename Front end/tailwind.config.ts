import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-playfair)', 'sans-serif'],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        brand: {
          background: '#FFFDF8',
          secondary: '#EEF7E8',
          surface: '#CFE8C2',
          primary: '#86B77B',
          dark: '#2F5A3A',
          accent: '#5B8DEF',
        }
      },
      keyframes: {
        techFloat: {
          '0%, 100%': { transform: 'translateY(0px) scale(1)', opacity: '0.2' },
          '50%': { transform: 'translateY(-18px) scale(1.3)', opacity: '0.45' },
        },
        techPulse: {
          '0%, 100%': { transform: 'scale(1)', opacity: '0.1' },
          '50%': { transform: 'scale(1.15)', opacity: '0.25' },
        },
      },
      animation: {
        'tech-float': 'techFloat 4s ease-in-out infinite',
        'tech-pulse': 'techPulse 3s ease-in-out infinite',
      },
    },
  },
  plugins: [],
};
export default config;

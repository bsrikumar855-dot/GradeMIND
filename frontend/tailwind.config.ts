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
        sans: ['var(--font-jakarta)', 'Inter', 'system-ui', 'sans-serif'],
        serif: ['var(--font-playfair)', 'Playfair Display', 'Georgia', 'serif'],
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        forest: {
          DEFAULT: '#183B25',
          50: '#F4F8F3',
          100: '#E8F0E4',
          200: '#D2E3CE',
          300: '#A8CB9F',
          400: '#74A86D',
          500: '#4A8B40',
          600: '#3B7233',
          700: '#2D5A38',
          800: '#1F3E27',
          900: '#183B25',
          950: '#0F2618',
        },
        sage: {
          DEFAULT: '#4A8B40',
          light: '#F4F8F3',
          muted: '#E8F0E4',
          border: '#D2E3CE',
          dark: '#183B25',
        },
        brand: {
          background: '#F4F8F3',
          surface: '#E8F0E4',
          card: '#FFFFFF',
          primary: '#4A8B40',
          primaryHover: '#3B7233',
          secondary: '#2D5A38',
          dark: '#183B25',
          accent: '#4A8B40',
          emerald: '#4A8B40',
          glow: 'rgba(74, 139, 64, 0.2)',
        }
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        'border-beam': {
          '100%': {
            'offset-distance': '100%',
          },
        },
        pulseGlow: {
          '0%, 100%': { opacity: '0.4', transform: 'scale(1)' },
          '50%': { opacity: '0.8', transform: 'scale(1.05)' },
        },
        floatSlow: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        gradientMove: {
          '0%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
          '100%': { backgroundPosition: '0% 50%' },
        }
      },
      animation: {
        'shimmer': 'shimmer 2.5s infinite linear',
        'border-beam': 'border-beam calc(var(--duration)*1s) infinite linear var(--delay)',
        'pulse-glow': 'pulseGlow 3s ease-in-out infinite',
        'float': 'floatSlow 4s ease-in-out infinite',
        'gradient-move': 'gradientMove 6s ease infinite',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(24, 59, 37, 0.08)',
        'glow-emerald': '0 0 25px -5px rgba(74, 139, 64, 0.3)',
        'glow-accent': '0 0 25px -5px rgba(24, 59, 37, 0.3)',
      }
    },
  },
  plugins: [],
};
export default config;

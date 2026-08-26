/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand tokens — warm neutrals + gold accent (values in src/styles/index.css)
        // so every surface flips from one place.
        paper: 'rgb(var(--paper) / <alpha-value>)',
        surface: 'rgb(var(--surface) / <alpha-value>)',
        surfaceWarm: 'rgb(var(--surface-warm) / <alpha-value>)',
        ink: 'rgb(var(--ink) / <alpha-value>)',
        graphite: 'rgb(var(--graphite) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        border: 'rgb(var(--border) / <alpha-value>)',

        navy: 'rgb(var(--navy) / <alpha-value>)',
        navyDark: 'rgb(var(--navy-dark) / <alpha-value>)',
        orange: 'rgb(var(--orange) / <alpha-value>)',
        orangeDark: 'rgb(var(--orange-dark) / <alpha-value>)',

        // Landing-page palette — remapped onto the warm brand system:
        // ink anchor · gold actions/accents · champagne atmosphere
        royal: '#1A1A18', // brand anchor: hero panels, headings
        azure: '#C9964A', // accent: CTA fills, links, focus rings
        sky: '#C9964A', // decorative accents on dark surfaces
        periwinkle: '#EFE3CB', // atmosphere: soft glows behind hero content
        mist: '#FAFAF8', // page canvas (bg-primary)
        lavender: '#E2DDD5', // soft structure: card borders, chip washes
        haze: '#F3F1EC', // canvas tint — bg-secondary backdrop for cards

        success: 'rgb(var(--success) / <alpha-value>)',
        successSoft: 'rgb(var(--success-soft) / <alpha-value>)',
        warning: 'rgb(var(--warning) / <alpha-value>)',
        warningSoft: 'rgb(var(--warning-soft) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        dangerSoft: 'rgb(var(--danger-soft) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',
        infoSoft: 'rgb(var(--info-soft) / <alpha-value>)',

        // Legacy aliases — kept so existing pages migrate to the new palette
        primary: {
          DEFAULT: 'rgb(var(--navy) / <alpha-value>)',
          dark: 'rgb(var(--navy-dark) / <alpha-value>)',
          light: 'rgb(var(--primary-light) / <alpha-value>)',
        },
        secondary: {
          DEFAULT: 'rgb(var(--orange) / <alpha-value>)',
          dark: 'rgb(var(--orange-dark) / <alpha-value>)',
          light: 'rgb(var(--secondary-light) / <alpha-value>)',
        },
        background: 'rgb(var(--paper) / <alpha-value>)',
        card: 'rgb(var(--surface) / <alpha-value>)',
        text: {
          DEFAULT: 'rgb(var(--ink) / <alpha-value>)',
          secondary: 'rgb(var(--graphite) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'sans-serif'],
        display: ['Outfit', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        display: ['32px', '40px'],
      },
      borderRadius: {
        DEFAULT: '6px',
        sm: '4px',
        md: '6px',
        lg: '10px',
        xl: '12px',
        '2xl': '16px',
      },
      boxShadow: {
        card: '0 1px 3px rgba(26, 26, 24, 0.06)',
        overlay: '0 8px 24px rgba(26, 26, 24, 0.10)',
      },
      animation: {
        'loader-bar': 'loaderBar 0.6s ease-out both',
      },
      keyframes: {
        loaderBar: {
          '0%': { transform: 'scaleY(0)', transformOrigin: 'bottom' },
          '100%': { transform: 'scaleY(1)', transformOrigin: 'bottom' },
        },
      },
    },
  },
  plugins: [],
};

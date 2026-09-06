import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        base: 'var(--bg-base)',
        panel: 'var(--bg-panel)',
        'panel-raised': 'var(--bg-panel-raised)',
        hairline: 'var(--border-hairline)',
        primary: 'var(--text-primary)',
        secondary: 'var(--text-secondary)',
        tertiary: 'var(--text-tertiary)',
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        benign: 'var(--signal-benign)',
        warning: 'var(--signal-warning)',
        critical: 'var(--signal-critical)',
        'critical-bg': 'var(--signal-critical-bg)',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        input: '4px',
        panel: '6px',
        pill: '2px',
      },
      keyframes: {
        'row-flash': {
          '0%': { backgroundColor: 'var(--signal-critical-bg)' },
          '100%': { backgroundColor: 'transparent' },
        },
        heartbeat: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.6' },
        },
      },
      animation: {
        'row-flash': 'row-flash 900ms ease-out forwards',
        heartbeat: 'heartbeat 2s ease-in-out infinite',
      },
    },
  },
  plugins: [],
} satisfies Config

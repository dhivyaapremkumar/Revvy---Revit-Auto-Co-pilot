// Chakra UI v3 theme system for REVVY.
// Extends the default Chakra config with brand tokens used by the shared
// ui components (GlassCard, GradientButton, etc). Phase 2 module agents
// should add new tokens here rather than hardcoding colors in components.
import { createSystem, defaultConfig, defineConfig } from '@chakra-ui/react';

const revvyConfig = defineConfig({
  theme: {
    tokens: {
      colors: {
        brand: {
          50: { value: '#f3ecff' },
          100: { value: '#e4d6ff' },
          200: { value: '#c7adff' },
          300: { value: '#a780ff' },
          400: { value: '#8a56ff' },
          500: { value: '#7c3aed' },
          600: { value: '#6425d0' },
          700: { value: '#4e1ba3' },
          800: { value: '#391376' },
          900: { value: '#230a4d' },
        },
        accent: {
          50: { value: '#fdf0f8' },
          100: { value: '#fbd6ec' },
          200: { value: '#f7add8' },
          300: { value: '#f280c2' },
          400: { value: '#ee56ac' },
          500: { value: '#ec4899' },
          600: { value: '#c92c79' },
          700: { value: '#9c2160' },
          800: { value: '#701747' },
          900: { value: '#450d2e' },
        },
      },
      fonts: {
        heading: { value: `'Inter', system-ui, -apple-system, sans-serif` },
        body: { value: `'Inter', system-ui, -apple-system, sans-serif` },
      },
    },
  },
});

export const system = createSystem(defaultConfig, revvyConfig);

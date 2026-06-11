/**
 * Heuristics design tokens — typed exports for JS-side consumption.
 *
 * Source of truth is `tokens.css`. These constants are for cases where
 * tokens must be referenced from JS (framer-motion timings, dynamic
 * inline styles, theme-switching logic).
 *
 * Anything that can be expressed in CSS should be expressed in CSS.
 */

export const motion = {
  duration: {
    instant: 120,
    quick: 240,
    base: 400,
    emphasized: 520,
  },
  easing: {
    standard: [0.2, 0.8, 0.2, 1] as const,
    emphasized: [0.32, 0.72, 0, 1] as const,
    decelerate: [0, 0, 0.2, 1] as const,
  },
} as const;

export const breakpoints = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

export const space = {
  0: 0,
  1: 4,
  2: 8,
  3: 12,
  4: 16,
  6: 24,
  8: 32,
  12: 48,
  16: 64,
  24: 96,
  32: 128,
} as const;

export const radius = {
  none: 0,
  sm: 4,
  md: 8,
  lg: 12,
  xl: 16,
  pill: 999,
} as const;

export const z = {
  base: 1,
  raised: 10,
  overlay: 100,
  modal: 1000,
  toast: 2000,
} as const;

export const container = {
  prose: '64ch',
  app: '72rem',
  wide: '80rem',
} as const;

export type Theme = 'light' | 'dark';

export const tokens = {
  motion,
  breakpoints,
  space,
  radius,
  z,
  container,
} as const;

export default tokens;

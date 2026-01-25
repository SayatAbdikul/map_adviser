import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const THEME_MOODS = ['sand', 'mist', 'stone'] as const;
export const THEME_ACCENTS = ['citrus', 'lagoon', 'clay', 'moss', 'cobalt', 'ember'] as const;
export const THEME_CONTRASTS = ['soft', 'balanced', 'bold'] as const;

export type ThemeMood = (typeof THEME_MOODS)[number];
export type ThemeAccent = (typeof THEME_ACCENTS)[number];
export type ThemeContrast = (typeof THEME_CONTRASTS)[number];

export interface ThemeSettings {
  mood: ThemeMood;
  accent: ThemeAccent;
  contrast: ThemeContrast;
}

interface ThemeState extends ThemeSettings {
  setMood: (mood: ThemeMood) => void;
  setAccent: (accent: ThemeAccent) => void;
  setContrast: (contrast: ThemeContrast) => void;
  resetTheme: () => void;
  randomizeTheme: () => void;
}

const defaultTheme: ThemeSettings = {
  mood: 'sand',
  accent: 'clay',
  contrast: 'balanced',
};

const pickRandom = <T,>(items: readonly T[]): T =>
  items[Math.floor(Math.random() * items.length)]!;

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      ...defaultTheme,
      setMood: (mood) => set({ mood }),
      setAccent: (accent) => set({ accent }),
      setContrast: (contrast) => set({ contrast }),
      resetTheme: () => set(defaultTheme),
      randomizeTheme: () =>
        set({
          mood: pickRandom(THEME_MOODS),
          accent: pickRandom(THEME_ACCENTS),
          contrast: pickRandom(THEME_CONTRASTS),
        }),
    }),
    { name: 'map-adviser-theme' }
  )
);

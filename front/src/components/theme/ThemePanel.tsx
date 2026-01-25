import React, { useEffect, useMemo, useState } from 'react';
import { twMerge } from 'tailwind-merge';
import { Palette, Shuffle, RotateCcw } from 'lucide-react';
import {
  THEME_ACCENTS,
  THEME_CONTRASTS,
  THEME_MOODS,
  type ThemeAccent,
  type ThemeContrast,
  type ThemeMood,
  useThemeStore,
} from '@/store/useThemeStore';
import { Button } from '@/components/common/Button';
import { useDraggablePanel } from '@/hooks/useDraggablePanel';

const MOOD_META: Record<
  ThemeMood,
  { label: string; hue: number; sat: number; canvas: number; description: string }
> = {
  sand: { label: 'Sand', hue: 32, sat: 26, canvas: 95, description: 'Warm, sunlit base' },
  mist: { label: 'Mist', hue: 196, sat: 18, canvas: 96, description: 'Cool and airy' },
  stone: { label: 'Stone', hue: 215, sat: 10, canvas: 95, description: 'Neutral and calm' },
};

const ACCENT_META: Record<ThemeAccent, { label: string; hue: number; sat: number; light: number }> = {
  citrus: { label: 'Citrus', hue: 38, sat: 92, light: 52 },
  lagoon: { label: 'Lagoon', hue: 188, sat: 72, light: 45 },
  clay: { label: 'Clay', hue: 18, sat: 82, light: 52 },
  moss: { label: 'Moss', hue: 140, sat: 44, light: 40 },
  cobalt: { label: 'Cobalt', hue: 210, sat: 72, light: 48 },
  ember: { label: 'Ember', hue: 8, sat: 78, light: 50 },
};

const CONTRAST_META: Record<
  ThemeContrast,
  { label: string; text: number; muted: number; border: number; surfaceBoost: number; surfaceDip: number; shadow: number }
> = {
  soft: { label: 'Soft', text: 20, muted: 48, border: 88, surfaceBoost: 2, surfaceDip: 1, shadow: 0.08 },
  balanced: { label: 'Balanced', text: 16, muted: 42, border: 82, surfaceBoost: 3, surfaceDip: 2, shadow: 0.12 },
  bold: { label: 'Bold', text: 13, muted: 36, border: 76, surfaceBoost: 4, surfaceDip: 3, shadow: 0.16 },
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);
const hsl = (hue: number, sat: number, light: number) => `hsl(${hue} ${sat}% ${light}%)`;

const buildThemeTokens = (mood: ThemeMood, accent: ThemeAccent, contrast: ThemeContrast) => {
  const moodMeta = MOOD_META[mood];
  const accentMeta = ACCENT_META[accent];
  const contrastMeta = CONTRAST_META[contrast];

  const canvasLight = moodMeta.canvas;
  const surfaceLight = clamp(canvasLight + contrastMeta.surfaceBoost, 92, 99);
  const surfaceAltLight = clamp(canvasLight - contrastMeta.surfaceDip, 86, 96);
  const surfaceHover = clamp(surfaceAltLight - 2, 82, 94);

  const accentStrong = clamp(accentMeta.light - 10, 36, 60);
  const accentSoft = clamp(accentMeta.light + 40, 80, 94);

  return {
    '--app-canvas': hsl(moodMeta.hue, moodMeta.sat, canvasLight),
    '--app-surface': hsl(moodMeta.hue, moodMeta.sat + 6, surfaceLight),
    '--app-surface-2': hsl(moodMeta.hue, moodMeta.sat + 4, surfaceAltLight),
    '--app-surface-3': hsl(moodMeta.hue, moodMeta.sat + 4, surfaceHover),
    '--app-border': hsl(moodMeta.hue, moodMeta.sat + 6, contrastMeta.border),
    '--app-text': hsl(moodMeta.hue, moodMeta.sat + 12, contrastMeta.text),
    '--app-muted': hsl(moodMeta.hue, moodMeta.sat + 8, contrastMeta.muted),
    '--app-accent': hsl(accentMeta.hue, accentMeta.sat, accentMeta.light),
    '--app-accent-strong': hsl(accentMeta.hue, accentMeta.sat + 6, accentStrong),
    '--app-accent-soft': hsl(accentMeta.hue, accentMeta.sat + 4, accentSoft),
    '--app-accent-contrast': 'hsl(0 0% 100%)',
    '--app-ring': `hsla(${accentMeta.hue}, ${accentMeta.sat}%, ${accentMeta.light}%, 0.35)`,
    '--app-shadow': `0 24px 60px hsla(${moodMeta.hue}, 22%, 20%, ${contrastMeta.shadow})`,
    '--app-shadow-soft': `0 12px 28px hsla(${moodMeta.hue}, 22%, 24%, ${contrastMeta.shadow * 0.65})`,
    '--app-canvas-glow': `radial-gradient(900px circle at 12% 12%, hsla(${accentMeta.hue}, ${accentMeta.sat}%, 86%, 0.7), transparent 60%), radial-gradient(900px circle at 90% 18%, hsla(${moodMeta.hue}, ${moodMeta.sat + 18}%, 90%, 0.7), transparent 60%)`,
  };
};

export const ThemePanel: React.FC = () => {
  const { mood, accent, contrast, setMood, setAccent, setContrast, resetTheme, randomizeTheme } = useThemeStore();
  const [isOpen, setIsOpen] = useState(false);
  const { panelRef, position, startDrag, didDrag, ensureInView } = useDraggablePanel({
    anchor: 'bottom-right',
    offset: 24,
  });

  const tokens = useMemo(
    () => buildThemeTokens(mood, accent, contrast),
    [mood, accent, contrast]
  );

  useEffect(() => {
    const root = document.documentElement;
    Object.entries(tokens).forEach(([token, value]) => {
      root.style.setProperty(token, value);
    });
  }, [tokens]);

  useEffect(() => {
    ensureInView();
  }, [isOpen, ensureInView]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handleOpen = () => setIsOpen(true);
    window.addEventListener('mapadviser:open-theme-lab', handleOpen);
    return () => window.removeEventListener('mapadviser:open-theme-lab', handleOpen);
  }, []);

  const recipeLabel = `${MOOD_META[mood].label} / ${ACCENT_META[accent].label} / ${CONTRAST_META[contrast].label}`;

  return (
    <div
      ref={panelRef}
      className="fixed z-30 flex flex-col items-start"
      style={{
        left: position?.x ?? 0,
        top: position?.y ?? 0,
        visibility: position ? 'visible' : 'hidden',
      }}
    >
      <button
        type="button"
        onPointerDown={startDrag}
        onClick={() => {
          if (didDrag()) return;
          setIsOpen((prev) => !prev);
        }}
        className="group flex items-center gap-3 rounded-full border app-border app-surface px-3 py-2 text-sm font-medium app-shadow-soft transition-all hover:-translate-y-0.5 hover:shadow-[var(--app-shadow)] cursor-grab active:cursor-grabbing touch-none select-none"
        aria-expanded={isOpen}
      >
        <span
          className="flex h-9 w-9 items-center justify-center rounded-full"
          style={{
            background:
              'linear-gradient(130deg, var(--app-accent), var(--app-accent-soft))',
            color: 'var(--app-accent-contrast)',
          }}
        >
          <Palette size={18} />
        </span>
        <span className="flex flex-col text-left leading-tight">
          <span className="text-[11px] uppercase tracking-[0.22em] app-muted">Theme Lab</span>
          <span className="text-sm app-text">Customize colors</span>
        </span>
      </button>

      <div
        className={twMerge(
          'mt-3 w-[min(92vw,360px)] origin-bottom-right transition-all duration-300',
          isOpen
            ? 'pointer-events-auto translate-y-0 scale-100 opacity-100'
            : 'pointer-events-none translate-y-2 scale-95 opacity-0'
        )}
      >
        <div className="relative overflow-hidden rounded-2xl border app-border app-surface app-shadow">
          <div
            className="absolute -top-16 -right-16 h-32 w-32 rounded-full opacity-80"
            style={{ background: 'var(--app-accent-soft)' }}
          />
          <div
            className="absolute -bottom-20 -left-16 h-32 w-32 rounded-full opacity-60"
            style={{ background: 'var(--app-surface-2)' }}
          />
          <div className="relative space-y-4 p-4">
            <div>
              <div className="text-[10px] uppercase tracking-[0.35em] app-muted">Theme Studio</div>
              <h2 className="font-display text-xl app-text">Color Composer</h2>
              <p className="text-xs app-muted">Three picks, one cohesive palette.</p>
            </div>

            <div className="rounded-xl border app-border app-surface-2 p-3">
              <div className="text-[11px] uppercase tracking-[0.24em] app-muted">Recipe</div>
              <div className="mt-1 text-sm font-medium app-text">{recipeLabel}</div>
            </div>

            <div className="space-y-3">
              <div>
                <div className="mb-2 text-xs font-semibold app-text">Mood</div>
                <div className="grid grid-cols-3 gap-2">
                  {THEME_MOODS.map((option, index) => {
                    const meta = MOOD_META[option];
                    const selected = option === mood;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setMood(option)}
                        aria-pressed={selected}
                        className={twMerge(
                          'rounded-xl border px-2 py-2 text-left transition-all',
                          isOpen && 'theme-chip',
                          selected
                            ? 'border-[color:var(--app-accent)] bg-[color:var(--app-accent-soft)]'
                            : 'border app-border bg-[color:var(--app-surface)] hover:bg-[color:var(--app-surface-2)]'
                        )}
                        style={{ animationDelay: `${index * 40}ms` }}
                      >
                        <div className="text-xs font-semibold app-text">{meta.label}</div>
                        <div className="text-[11px] app-muted">{meta.description}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold app-text">Accent</div>
                <div className="grid grid-cols-6 gap-2">
                  {THEME_ACCENTS.map((option, index) => {
                    const meta = ACCENT_META[option];
                    const selected = option === accent;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setAccent(option)}
                        aria-pressed={selected}
                        title={meta.label}
                        className={twMerge(
                          'flex h-9 w-9 items-center justify-center rounded-full border transition-all',
                          isOpen && 'theme-chip',
                          selected ? 'border-[color:var(--app-accent)]' : 'border app-border'
                        )}
                        style={{
                          animationDelay: `${index * 40}ms`,
                          background: hsl(meta.hue, meta.sat, meta.light),
                        }}
                        aria-label={meta.label}
                      >
                        {selected && (
                          <span className="h-2.5 w-2.5 rounded-full bg-white/90" />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div>
                <div className="mb-2 text-xs font-semibold app-text">Contrast</div>
                <div className="grid grid-cols-3 gap-2">
                  {THEME_CONTRASTS.map((option, index) => {
                    const meta = CONTRAST_META[option];
                    const selected = option === contrast;
                    return (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setContrast(option)}
                        aria-pressed={selected}
                        className={twMerge(
                          'rounded-xl border px-2 py-2 text-sm font-medium transition-all',
                          isOpen && 'theme-chip',
                          selected
                            ? 'border-[color:var(--app-accent)] bg-[color:var(--app-accent-soft)] text-[color:var(--app-accent-strong)]'
                            : 'border app-border bg-[color:var(--app-surface)] app-text hover:bg-[color:var(--app-surface-2)]'
                        )}
                        style={{ animationDelay: `${index * 40}ms` }}
                      >
                        {meta.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="rounded-xl border app-border app-surface p-3">
              <div className="text-[11px] uppercase tracking-[0.24em] app-muted">Preview</div>
              <div className="mt-2 flex items-center justify-between">
                <div>
                  <div className="font-display text-base app-text">Morning Route</div>
                  <div className="text-xs app-muted">Cafe hop to riverside</div>
                </div>
                <span className="rounded-full px-2 py-1 text-[11px] font-medium app-accent-soft">
                  Active
                </span>
              </div>
              <div className="mt-3 flex items-center gap-2">
                <span className="rounded-full px-3 py-1.5 text-[11px] font-semibold app-accent">
                  Primary
                </span>
                <span className="rounded-full bg-[color:var(--app-surface-2)] px-3 py-1.5 text-[11px] font-semibold app-text">
                  Surface
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={resetTheme}
                className="gap-2"
              >
                <RotateCcw size={14} />
                Reset
              </Button>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={randomizeTheme}
                className="gap-2"
              >
                <Shuffle size={14} />
                Surprise
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

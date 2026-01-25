import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, MessageSquare, Navigation2, Palette, ShieldCheck, Users } from 'lucide-react';
import { Card } from '@/components/common/Card';
import { useAuthStore } from '@/store/useAuthStore';

const FEATURES = [
  {
    title: 'Route intelligence',
    description: 'Compare walking, transit, and multi-leg routes with clear segment styling.',
    icon: Navigation2,
  },
  {
    title: 'Live trip rooms',
    description: 'Create a room, share your code, and see teammates move in real time.',
    icon: Users,
  },
  {
    title: 'Map assistant',
    description: 'Ask questions about routes or places without leaving the map.',
    icon: MessageSquare,
  },
  {
    title: 'Theme lab',
    description: 'Tune mood, accent, and contrast to match the vibe of every journey.',
    icon: Palette,
  },
];

const STEPS = [
  {
    title: 'Pick your anchor',
    description: 'Search a place, drop a marker, or start from your live location.',
  },
  {
    title: 'Compose the route',
    description: 'Compare options and see walking segments vs transit lines at a glance.',
  },
  {
    title: 'Share the plan',
    description: 'Invite teammates to a room and coordinate trips together.',
  },
];

export const LandingPage: React.FC = () => {
  const { isAuthenticated } = useAuthStore();

  const primaryCta = isAuthenticated ? { label: 'Open live map', to: '/map' } : { label: 'Create account', to: '/register' };
  const secondaryCta = isAuthenticated ? { label: 'Go to map', to: '/map' } : { label: 'Sign in', to: '/login' };

  const buttonBase =
    'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[color:var(--app-canvas)] app-ring';
  const buttonPrimary =
    `${buttonBase} bg-[color:var(--app-accent)] text-[color:var(--app-accent-contrast)] hover:bg-[color:var(--app-accent-strong)]`;
  const buttonSecondary =
    `${buttonBase} bg-[color:var(--app-surface-2)] text-[color:var(--app-text)] hover:bg-[color:var(--app-surface-3)]`;

  return (
    <div className="relative">
      <header className="relative z-10">
        <div className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl app-accent text-lg font-semibold">
              MA
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.32em] app-muted">Map Adviser</div>
              <div className="font-display text-lg">Plan smarter routes</div>
            </div>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            {isAuthenticated ? (
              <Link to="/map" className={`${buttonPrimary} h-10 px-4 text-sm`}>
                Open map
              </Link>
            ) : (
              <>
                <Link
                  to="/login"
                  className="text-sm font-medium app-muted hover:text-[color:var(--app-text)] transition-colors"
                >
                  Sign in
                </Link>
                <Link to="/register" className={`${buttonPrimary} h-10 px-4 text-sm`}>
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10">
        <section className="relative">
          <div className="absolute inset-x-0 -top-24 h-72 bg-[radial-gradient(circle_at_top,_var(--app-accent-soft),_transparent_70%)] opacity-70" />
          <div className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-10 px-6 pb-12 pt-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 rounded-full border app-border app-surface px-4 py-2 text-xs font-semibold uppercase tracking-[0.35em] app-muted">
                Live routes + shared rooms
              </div>
              <div className="space-y-4">
                <h1 className="font-display text-4xl leading-tight text-[color:var(--app-text)] sm:text-5xl">
                  A trip planner built for groups, city runs, and last-minute pivots.
                </h1>
                <p className="text-base app-muted sm:text-lg">
                  Map Adviser blends transit data, walking segments, and real-time collaboration so every move stays coordinated.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-3">
                <Link to={primaryCta.to} className={`${buttonPrimary} h-12 px-6 text-sm`}>
                  {primaryCta.label}
                  <ArrowRight size={18} className="ml-2" />
                </Link>
                {!isAuthenticated && (
                  <Link to={secondaryCta.to} className={`${buttonSecondary} h-12 px-6 text-sm`}>
                    {secondaryCta.label}
                  </Link>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                {[
                  { label: 'Multi-mode routing', value: 'Walk + transit' },
                  { label: 'Shared rooms', value: 'Live member pins' },
                  { label: 'Theme studio', value: 'Mood controls' },
                ].map((item) => (
                  <div key={item.label} className="rounded-2xl border app-border app-surface-2 px-4 py-3">
                    <div className="text-xs uppercase tracking-[0.24em] app-muted">{item.label}</div>
                    <div className="mt-2 text-sm font-semibold app-text">{item.value}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="relative">
              <div className="absolute -left-8 top-10 h-24 w-24 rounded-full bg-[color:var(--app-accent-soft)] blur-3xl opacity-70" />
              <div className="absolute -right-6 bottom-6 h-32 w-32 rounded-full bg-[color:var(--app-surface-2)] blur-3xl opacity-80" />
              <Card className="relative overflow-hidden rounded-3xl p-6">
                <div
                  className="absolute inset-0 opacity-70"
                  style={{
                    backgroundImage:
                      'radial-gradient(circle at top, var(--app-accent-soft), transparent 55%), linear-gradient(140deg, var(--app-surface), var(--app-surface-2))',
                  }}
                />
                <div className="relative space-y-6">
                  <div className="space-y-2">
                    <div className="text-xs uppercase tracking-[0.4em] app-muted">Route deck</div>
                    <div className="font-display text-2xl app-text">Morning Loop</div>
                    <p className="text-sm app-muted">Bakery to riverside, shared with 4 teammates.</p>
                  </div>

                  <div className="rounded-2xl border app-border app-surface-2 p-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-xs uppercase tracking-[0.28em] app-muted">Best option</div>
                        <div className="mt-1 text-lg font-semibold app-text">28 minutes</div>
                      </div>
                      <span className="rounded-full app-accent-soft px-3 py-1 text-xs font-semibold">
                        2 transfers
                      </span>
                    </div>
                    <div className="mt-3 flex items-center gap-2 text-xs font-medium">
                      <span className="rounded-full app-accent px-3 py-1">Transit</span>
                      <span className="rounded-full bg-[color:var(--app-surface)] px-3 py-1 app-text">
                        Walk 0.8 km
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border app-border app-surface px-3 py-3">
                      <div className="text-xs uppercase tracking-[0.24em] app-muted">Room</div>
                      <div className="mt-2 text-sm font-semibold app-text">Riverside Crew</div>
                      <div className="mt-1 text-xs app-muted">4 active members</div>
                    </div>
                    <div className="rounded-2xl border app-border app-surface px-3 py-3">
                      <div className="text-xs uppercase tracking-[0.24em] app-muted">Assistant</div>
                      <div className="mt-2 text-sm font-semibold app-text">3 tips ready</div>
                      <div className="mt-1 text-xs app-muted">Ask about reroutes</div>
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </section>

        <section className="relative py-12">
          <div className="mx-auto w-full max-w-6xl px-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
              <div>
                <div className="text-xs uppercase tracking-[0.4em] app-muted">Why it works</div>
                <h2 className="font-display text-3xl app-text">Built for city rhythm</h2>
              </div>
              <p className="max-w-xl text-sm app-muted">
                Fast searches, multi-modal routing, and shared rooms make Map Adviser a travel command center.
              </p>
            </div>

            <div className="mt-8 grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map(({ title, description, icon: Icon }, index) => (
                <Card
                  key={title}
                  className="space-y-3 p-5 motion-safe:animate-[fade-up_0.6s_ease_both]"
                  style={{ animationDelay: `${index * 80}ms` }}
                >
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl app-accent-soft">
                    <Icon size={18} />
                  </div>
                  <div className="text-lg font-semibold app-text">{title}</div>
                  <p className="text-sm app-muted">{description}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        <section className="relative py-12">
          <div className="mx-auto w-full max-w-6xl px-6">
            <div className="grid grid-cols-1 gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
              <div className="space-y-4">
                <div className="text-xs uppercase tracking-[0.4em] app-muted">How it flows</div>
                <h2 className="font-display text-3xl app-text">From search to shared route in minutes.</h2>
                <p className="text-sm app-muted">
                  Whether you are mapping a commute or coordinating a meetup, the flow stays lightweight and focused.
                </p>
              </div>
              <div className="space-y-4">
                {STEPS.map((step, index) => (
                  <div
                    key={step.title}
                    className="flex items-start gap-4 rounded-2xl border app-border app-surface-2 p-4 motion-safe:animate-[fade-up_0.6s_ease_both]"
                    style={{ animationDelay: `${index * 90}ms` }}
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-full app-accent text-sm font-semibold">
                      {index + 1}
                    </div>
                    <div>
                      <div className="text-base font-semibold app-text">{step.title}</div>
                      <p className="text-sm app-muted">{step.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="relative pb-16">
          <div className="mx-auto w-full max-w-6xl px-6">
            <Card className="flex flex-col items-start justify-between gap-6 border-dashed p-6 md:flex-row md:items-center">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl app-accent-soft">
                  <ShieldCheck size={20} />
                </div>
                <div>
                  <div className="text-xs uppercase tracking-[0.3em] app-muted">Secure access</div>
                  <div className="mt-2 text-lg font-semibold app-text">
                    Sign in to unlock the live map, rooms, and route details.
                  </div>
                  <p className="text-sm app-muted">Authentication keeps shared trips private and coordinated.</p>
                </div>
              </div>
              <div className="flex flex-wrap gap-3">
                <Link to={primaryCta.to} className={`${buttonPrimary} h-11 px-5 text-sm`}>
                  {primaryCta.label}
                </Link>
                {!isAuthenticated && (
                  <Link to={secondaryCta.to} className={`${buttonSecondary} h-11 px-5 text-sm`}>
                    {secondaryCta.label}
                  </Link>
                )}
              </div>
            </Card>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t app-border">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-4 px-6 py-6 text-sm app-muted md:flex-row md:items-center md:justify-between">
          <div>Copyright 2026 Map Adviser. Built by Competitive Vibecoders.</div>
          <div className="flex flex-wrap gap-4">
            <Link to="/login" className="hover:text-[color:var(--app-text)] transition-colors">
              Sign in
            </Link>
            <Link to="/register" className="hover:text-[color:var(--app-text)] transition-colors">
              Register
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
};

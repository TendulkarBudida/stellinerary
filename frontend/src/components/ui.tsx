import type { ButtonHTMLAttributes, ReactNode } from 'react';
import type { ForecastConfidence } from '../types';

/* ---------- Buttons ---------- */

type BtnProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost' | 'danger-ghost';
};

export function Button({ variant = 'primary', className = '', ...rest }: BtnProps) {
  const base =
    'inline-flex items-center justify-center gap-2 rounded-lg px-5 py-2.5 font-display text-sm font-semibold tracking-wide transition-all duration-200 cursor-pointer disabled:cursor-not-allowed disabled:opacity-50';
  const styles =
    variant === 'primary'
      ? 'bg-accent text-space-950 hover:brightness-110 hover:shadow-[0_0_24px_rgba(103,232,249,0.35)]'
      : variant === 'danger-ghost'
        ? 'border border-danger/50 text-danger hover:bg-danger/10'
        : 'border border-accent/40 text-accent hover:bg-accent/10';
  return <button className={`${base} ${styles} ${className}`} {...rest} />;
}

/* ---------- Card ---------- */

export function Card({ className = '', children }: { className?: string; children: ReactNode }) {
  return (
    <div
      className={`rounded-2xl border border-space-600/60 bg-space-900/80 shadow-[0_8px_40px_rgba(0,0,0,0.45)] backdrop-blur-sm ${className}`}
    >
      {children}
    </div>
  );
}

export function CardHeader({ title, subtitle, right }: { title: string; subtitle?: string; right?: ReactNode }) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-space-600/50 px-5 py-4 sm:px-6">
      <div>
        <h2 className="font-display text-lg font-semibold text-starlight">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-stardim">{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

/* ---------- Section heading ---------- */

export function SectionHeading({ kicker, title, lede }: { kicker?: string; title: string; lede?: string }) {
  return (
    <div className="mx-auto mb-10 max-w-2xl text-center">
      {kicker && (
        <p className="mb-2 font-display text-xs font-semibold uppercase tracking-[0.25em] text-accent">{kicker}</p>
      )}
      <h2 className="font-display text-3xl font-bold text-starlight sm:text-4xl">{title}</h2>
      {lede && <p className="mt-3 text-stardim">{lede}</p>}
    </div>
  );
}

/* ---------- Badge ---------- */

export function Badge({ tone = 'neutral', children }: { tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'info'; children: ReactNode }) {
  const tones: Record<string, string> = {
    neutral: 'border-space-600 bg-space-800 text-stardim',
    good: 'border-success/40 bg-success/10 text-success',
    warn: 'border-warn/40 bg-warn/10 text-warn',
    bad: 'border-danger/40 bg-danger/10 text-danger',
    info: 'border-accent/40 bg-accent/10 text-accent',
  };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium ${tones[tone]}`}>
      {children}
    </span>
  );
}

/* ---------- Forecast confidence ---------- */

export function ConfidenceBadge({ confidence }: { confidence: ForecastConfidence }) {
  if (confidence === 'unavailable_outside_horizon') {
    return <Badge tone="warn">Forecast not yet available</Badge>;
  }
  if (confidence === 'unavailable_provider_error') {
    return <Badge tone="bad">Weather unverified</Badge>;
  }
  return <Badge tone="good">Forecast covers this night</Badge>;
}

/* ---------- Score bars ---------- */

export function ScoreBars({ components }: { components: Record<string, number> }) {
  const labels: Record<string, string> = {
    event_visibility: 'Event visibility',
    weather: 'Weather',
    bortle: 'Darkness',
    distance: 'Distance',
  };
  const entries = Object.entries(components);
  if (entries.length === 0) return null;
  return (
    <div className="space-y-2.5">
      {entries.map(([key, value]) => (
        <div key={key}>
          <div className="mb-1 flex items-center justify-between text-xs">
            <span className="text-stardim">{labels[key] ?? key}</span>
            <span className="font-mono text-starlight">{Math.round(value * 100)}%</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-space-700">
            <div
              className="h-full rounded-full bg-gradient-to-r from-accent2 to-accent"
              style={{ width: `${Math.round(value * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ---------- Moon phase (SVG) ---------- */

export function MoonPhase({ phasePct }: { phasePct?: number }) {
  if (phasePct === undefined) return null;
  const phase = phasePct / 100;
  // Terminator offset: full (0.5) shows lit disc, new (0) shows dark disc.
  const rx = Math.abs(Math.cos(phase * Math.PI * 2)) * 9;
  const rightLit = phase < 0.5;
  return (
    <span className="inline-flex items-center gap-2 text-xs text-stardim" title={`Moon illumination ${phasePct}%`}>
      <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
        <circle cx="10" cy="10" r="9" fill="#2c2c5c" stroke="#9aa3c0" strokeWidth="1" />
        <ellipse
          cx="10"
          cy="10"
          rx={rx}
          ry={9}
          fill="#e9edf7"
          transform={rightLit ? undefined : 'rotate(180 10 10)'}
          clipPath="url(#moonclip)"
        />
        <clipPath id="moonclip">
          {rightLit ? <rect x="10" y="0" width="10" height="20" /> : <rect x="0" y="0" width="10" height="20" />}
        </clipPath>
      </svg>
      {phasePct}%
    </span>
  );
}

/* ---------- Empty state ---------- */

export function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-space-600 px-6 py-12 text-center">
      <p className="font-display text-lg font-semibold text-starlight">{title}</p>
      <p className="mx-auto mt-2 max-w-md text-sm text-stardim">{body}</p>
    </div>
  );
}

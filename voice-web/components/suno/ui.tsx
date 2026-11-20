'use client';

import { useEffect, useRef, type ReactNode } from 'react';
import { type AnalyzeResult, type LinkReport, type Verdict, hostOf } from './api';

/** Honest label for how real a feature is. */
export function Tag({ kind }: { kind: 'real' | 'simulated' | 'planned' | 'setup' }) {
  const styles = {
    real: 'tag-real',
    simulated: 'tag-sim',
    planned: 'tag-plan',
    setup: 'tag-setup',
  }[kind];
  const text = { real: 'Working', simulated: 'Simulated demo', planned: 'Planned for Android app', setup: 'Needs a phone number' }[kind];
  return (
    <span className={`inline-block rounded-full border px-3 py-0.5 align-middle text-[0.75em] font-bold ${styles}`}>{text}</span>
  );
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`s-card rounded-3xl p-5 ${className}`}>{children}</section>
  );
}

/** Level → colour, shared by badges, charts and tables. */
export const LEVEL_COLOR: Record<string, string> = {
  critical: '#ff4d4f', high: '#f04438', medium: '#f59e0b', low: '#eab308', info: '#5fd3a5',
};

export function LevelBadge({ level }: { level: string | null | undefined }) {
  const l = level ?? 'info';
  const label = l === 'info' ? 'None' : l[0].toUpperCase() + l.slice(1);
  const color = LEVEL_COLOR[l] ?? LEVEL_COLOR.info;
  return (
    <span className="inline-flex items-center rounded-md px-2 py-0.5 text-[0.78em] font-bold"
      style={{ color, background: `${color}22`, border: `1px solid ${color}55` }}>{label}</span>
  );
}

export function BigButton({
  children,
  onClick,
  tone = 'primary',
  disabled,
  type = 'button',
  ariaLabel,
}: {
  children: ReactNode;
  onClick?: () => void;
  tone?: 'primary' | 'danger' | 'quiet' | 'amber';
  disabled?: boolean;
  type?: 'button' | 'submit';
  ariaLabel?: string;
}) {
  const tones = {
    primary: 'btn-primary',
    danger: 'btn-danger',
    amber: 'bg-[#f59e0b] text-[#1f1300]',
    quiet: 'btn-quiet',
  }[tone];
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className={`flex min-h-[3.75em] w-full items-center justify-center gap-3 rounded-2xl px-5 py-3 text-[1.1em] font-bold leading-tight focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40 disabled:opacity-50 ${tones}`}
    >
      {children}
    </button>
  );
}

export function ErrorNote({ message }: { message: string }) {
  if (!message) return null;
  return (
    <p role="alert" className="rounded-2xl border-2 border-[#b42318] bg-[#fef3f2] p-4 font-semibold text-[#7a271a]">
      {message}
    </p>
  );
}

const VERDICT_STYLE = {
  danger: { box: 'verdict-danger', head: 'text-[#ff8a80]', icon: '⛔', title: 'Danger' },
  caution: { box: 'verdict-caution', head: 'text-[#fbbf24]', icon: '⚠️', title: 'Be careful' },
  no_known_issues: { box: 'verdict-ok', head: 'text-[#5fd3a5]', icon: '✔️', title: 'No known problems found' },
} as const;

export function VerdictCard({ verdict }: { verdict: Verdict }) {
  const style = VERDICT_STYLE[verdict.label];
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    ref.current?.focus(); // screen readers announce the result as soon as it arrives
  }, [verdict]);
  return (
    <div ref={ref} tabIndex={-1} role="status" className={`scroll-mt-28 rounded-3xl border-4 p-5 outline-none ${style.box}`}>
      <h3 className={`flex items-center gap-3 text-[1.5em] font-extrabold ${style.head}`}>
        <span aria-hidden>{style.icon}</span>
        {style.title}
      </h3>
      <p className="mt-2 text-[1.1em] font-semibold">{verdict.summary}</p>
      {verdict.reasons.length > 0 && (
        <>
          <h4 className="mt-4 font-bold">Why</h4>
          <ul className="mt-1 list-disc space-y-1 pl-6">
            {verdict.reasons.slice(0, 4).map((r) => (
              <li key={r.rule}>{r.text}</li>
            ))}
          </ul>
        </>
      )}
      {verdict.uncertainties.length > 0 && (
        <>
          <h4 className="mt-4 font-bold">What I could not check</h4>
          <ul className="mt-1 list-disc space-y-1 pl-6 text-[#4b5a56]">
            {verdict.uncertainties.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

export function LinkFacts({ link }: { link: LinkReport }) {
  const start = hostOf(link.url);
  const end = hostOf(link.final_url);
  const checks = link.tool_runs.filter((t) => t.tool !== 'url_normalize');
  return (
    <Card>
      <h4 className="font-bold">Link to: {start || 'unknown website'}</h4>
      {end && end !== start && <p className="mt-1">It finally leads to: <strong>{end}</strong></p>}
      {link.findings.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 pl-6">
          {link.findings.slice(0, 6).map((f, i) => (
            <li key={`${f.code}-${i}`}>{f.detail}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-[#4b5a56]">No warning signs were found for this link.</p>
      )}
      <p className="mt-3 text-[0.85em] text-[#4b5a56]">
        Checks run: {checks.map((t) => `${t.tool.replace('_', ' ')} (${t.status.replace('_', ' ')})`).join(', ')}
      </p>
    </Card>
  );
}

export function signalsList(result: AnalyzeResult): string[] {
  return result.signals.map((s) => s.detail).slice(0, 6);
}

/** A full-screen question that must be answered before a risky action runs. */
export function ConfirmSheet({
  title,
  body,
  confirmLabel,
  onConfirm,
  onCancel,
}: {
  title: string;
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    cancelRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onCancel();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onCancel]);
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60 p-4 sm:items-center">
      <div role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-body"
        className="s-card w-full max-w-md rounded-3xl p-6">
        <h3 id="confirm-title" className="text-[1.4em] font-extrabold">{title}</h3>
        <p id="confirm-body" className="mt-2 text-[1.05em]">{body}</p>
        <div className="mt-5 space-y-3">
          <BigButton tone="danger" onClick={onConfirm}>{confirmLabel}</BigButton>
          <button ref={cancelRef} type="button" onClick={onCancel}
            className="min-h-[3.5em] w-full rounded-2xl border border-[#cfcabb] bg-[#eceae0] text-[1.1em] font-bold focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40">
            No, go back
          </button>
        </div>
      </div>
    </div>
  );
}

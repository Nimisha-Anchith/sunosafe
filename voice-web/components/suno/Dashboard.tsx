'use client';

import { useCallback, useEffect, useState } from 'react';
import { type Settings, api, talkUrl } from './api';
import * as I from './icons';
import { LEVEL_COLOR, LevelBadge } from './ui';

export type CallEntry = {
  id: number; ts: string; kind: string; level: string | null; incident_id: number | null; caller: string | null;
  threat: string | null; heard: string | null; asked: string[]; why: string[];
};
export type DashboardData = {
  days: number;
  generated_at: string;
  stats: { scams_stopped: number; links_blocked: number; suspicious_calls: number; high_risk_incidents: number;
    messages_checked: number; open_incidents: number };
  timeline: { day: string; high: number; medium: number }[];
  threat_types: { name: string; count: number }[];
  recent_incidents: { id: number; title: string; severity: string; status: string; updated_at: string; channels: string[];
    threat: string; action: string }[];
  calls: CallEntry[];
  live_call: (CallEntry & { seconds_ago: number; active: boolean }) | null;
};

const ASK_NAMES: Record<string, string> = {
  otp: 'OTP', pin: 'PIN', password: 'password', remote_app: 'a remote-control app', money: 'money', card: 'card details', kyc: 'KYC update',
};
const DONUT = ['#f04438', '#f59e0b', '#38bdf8', '#a78bfa', '#34d399', '#f472b6', '#facc15', '#94a3b8'];

/** Poll the Mini-SIEM. `every` in ms; pauses while the page is hidden. */
export function useDashboard(days = 7, every = 6000) {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState('');
  const load = useCallback(() => {
    api<DashboardData>(`dashboard?days=${days}`).then((d) => { setData(d); setError(''); })
      .catch((e: Error) => setError(e.message));
  }, [days]);
  useEffect(() => {
    load();
    const id = setInterval(() => { if (document.visibilityState === 'visible') load(); }, every);
    return () => clearInterval(id);
  }, [load, every]);
  return { data, error, reload: load };
}

export function timeAgo(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return 'just now';
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
}

function clock(iso: string): string {
  const d = new Date(iso);
  const today = new Date().toDateString() === d.toDateString();
  const t = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return today ? `Today, ${t}` : `${d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })}, ${t}`;
}

export function Waveform({ active, bars = 23, height = 44 }: { active: boolean; bars?: number; height?: number }) {
  return (
    <div className={`s-wave flex items-center justify-center ${active ? '' : 'idle'}`} style={{ height }} aria-hidden>
      {Array.from({ length: bars }, (_, i) => {
        const h = 0.25 + 0.75 * Math.abs(Math.sin((i + 1) * 1.7)) * (1 - Math.abs(i - bars / 2) / (bars / 1.6));
        return <span key={i} style={{ height: `${Math.max(12, h * 100)}%`, animationDelay: `${(i % 7) * 0.09}s` }} />;
      })}
    </div>
  );
}

// ----------------------------------------------------------------- stat card
function Stat({ icon, value, label, color, note }: { icon: React.ReactNode; value: number | string; label: string; color: string; note?: string }) {
  return (
    <div className="s-card flex items-center gap-3 rounded-2xl p-4">
      <div className="grid h-12 w-12 shrink-0 place-items-center rounded-xl" style={{ background: `${color}1f`, color }}>{icon}</div>
      <div className="min-w-0">
        <p className="text-[1.6em] font-extrabold leading-none">{value}</p>
        <p className="mt-1 text-[0.85em] text-[var(--s-muted)]">{label}</p>
        {note && <p className="text-[0.72em] text-[var(--s-muted)] opacity-80">{note}</p>}
      </div>
    </div>
  );
}

// ----------------------------------------------------------------- charts
function Timeline({ data }: { data: DashboardData['timeline'] }) {
  const max = Math.max(1, ...data.map((d) => d.high + d.medium));
  const W = 320, H = 150, pad = 22, bw = Math.min(26, (W - pad) / data.length - 10);
  const step = (W - pad) / data.length;
  const total = data.reduce((n, d) => n + d.high + d.medium, 0);
  return (
    <figure>
      <svg viewBox={`0 0 ${W} ${H + 22}`} className="w-full" role="img"
        aria-label={`Suspicious events per day over ${data.length} days, ${total} in total`}>
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line x1={pad} x2={W} y1={H - f * (H - 10)} y2={H - f * (H - 10)} stroke="#1f3b33" strokeDasharray="3 4" />
            <text x={0} y={H - f * (H - 10) + 4} fill="#6b867d" fontSize="10">{Math.round(f * max)}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const x = pad + i * step + (step - bw) / 2;
          const hh = (d.high / max) * (H - 10), hm = (d.medium / max) * (H - 10);
          return (
            <g key={d.day}>
              <rect x={x} y={H - hm} width={bw} height={hm} rx={3} fill={LEVEL_COLOR.medium} />
              <rect x={x} y={H - hm - hh} width={bw} height={hh} rx={3} fill={LEVEL_COLOR.high} />
              <text x={x + bw / 2} y={H + 16} fill="#6b867d" fontSize="10" textAnchor="middle">
                {new Date(d.day).toLocaleDateString(undefined, { day: 'numeric', month: data.length <= 7 && i === 0 ? 'short' : undefined })}
              </text>
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 flex gap-4 text-[0.8em] text-[var(--s-muted)]">
        <span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full" style={{ background: LEVEL_COLOR.high }} />High</span>
        <span><i className="mr-1 inline-block h-2.5 w-2.5 rounded-full" style={{ background: LEVEL_COLOR.medium }} />Medium</span>
      </figcaption>
    </figure>
  );
}

function Donut({ items }: { items: DashboardData['threat_types'] }) {
  const total = items.reduce((n, i) => n + i.count, 0);
  const R = 52, C = 2 * Math.PI * R;
  const lengths = items.map((it) => (it.count / Math.max(1, total)) * C);
  const starts = lengths.map((_, i) => lengths.slice(0, i).reduce((a, b) => a + b, 0));
  return (
    <div className="flex flex-wrap items-center gap-5">
      <svg viewBox="0 0 140 140" className="h-36 w-36 shrink-0" role="img" aria-label={`${total} threats by type`}>
        <circle cx="70" cy="70" r={R} fill="none" stroke="#1f3b33" strokeWidth="16" />
        {items.map((it, i) => (
          <circle key={it.name} cx="70" cy="70" r={R} fill="none" stroke={DONUT[i % DONUT.length]} strokeWidth="16"
            strokeDasharray={`${lengths[i]} ${C - lengths[i]}`} strokeDashoffset={-starts[i]} transform="rotate(-90 70 70)" />
        ))}
        <text x="70" y="68" textAnchor="middle" fill="#e7f3ee" fontSize="26" fontWeight="800">{total}</text>
        <text x="70" y="86" textAnchor="middle" fill="#93ada5" fontSize="10">threats</text>
      </svg>
      <ul className="min-w-[10em] flex-1 space-y-2 text-[0.88em]">
        {items.length === 0 && <li className="text-[var(--s-muted)]">No threats recorded in this period.</li>}
        {items.map((it, i) => (
          <li key={it.name} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2"><i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: DONUT[i % DONUT.length] }} />{it.name}</span>
            <span className="font-bold">{Math.round((it.count / Math.max(1, total)) * 100)}%</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ----------------------------------------------------------------- live call
export function LiveCallPanel({ data, settings, compact = false, onOpenIncident }: {
  data: DashboardData | null; settings: Settings; compact?: boolean; onOpenIncident?: (id: number) => void;
}) {
  const live = data?.live_call;
  if (!live) {
    return (
      <div className="text-center">
        <Waveform active={false} />
        <p className="mt-2 text-[var(--s-muted)]">No call answered by SunoSafe yet.</p>
        {!compact && (
          <a href={talkUrl(settings, null, 'shield')} className="btn-primary mt-4 inline-flex min-h-[3em] items-center justify-center gap-2 rounded-2xl px-5 font-bold">
            <I.Mic size={20} /> Test it: you play the caller
          </a>
        )}
      </div>
    );
  }
  const scam = live.level === 'high' || live.level === 'critical';
  return (
    <div>
      <div className="flex items-center justify-between gap-2">
        <p className="font-bold">{live.active ? 'SunoSafe is answering a call' : `Last call ${timeAgo(live.ts)}`}</p>
        {live.active && <span className="flex items-center gap-1 rounded-full bg-[#10b98122] px-2 py-0.5 text-[0.78em] font-bold text-[var(--s-green)]"><i className="s-pulse h-2 w-2 rounded-full bg-[var(--s-green)]" />Live</span>}
      </div>
      <Waveform active={live.active} height={compact ? 36 : 52} />
      {!compact && live.heard && (
        <div className="mt-3 space-y-3">
          <div className="rounded-2xl border border-[var(--s-border)] bg-[var(--s-elev)] p-4">
            <p className="flex items-center gap-2 text-[0.82em] font-bold text-[var(--s-muted)]"><I.User size={16} /> Caller (masked)</p>
            {/* untrusted words: rendered as plain text only */}
            <p className="mt-1 whitespace-pre-line">{live.heard}</p>
          </div>
          <div className="rounded-2xl border border-[#34d39966] bg-[#10b9811a] p-4">
            <p className="flex items-center gap-2 text-[0.82em] font-bold text-[var(--s-green)]"><I.ShieldPulse size={16} /> SunoSafe</p>
            <p className="mt-1">
              {scam
                ? 'Refused: the person never shares codes or bank details on the phone, and genuine banks never ask. The call was noted.'
                : 'Asked who is calling and why, without sharing anything about you.'}
            </p>
          </div>
        </div>
      )}
      {scam && (
        <div className="mt-3 rounded-2xl border-2 border-[#f04438] bg-[#f044381a] p-4 text-center">
          <p className="flex items-center justify-center gap-2 text-[1.25em] font-extrabold text-[#ff8a80]"><I.Alert size={22} /> Scam detected</p>
          <p className="mt-1">{live.asked.length ? `Asked for ${live.asked.map((a) => ASK_NAMES[a] ?? a).join(', ')}` : live.threat}</p>
          <p className="mt-1 flex items-center justify-center gap-2 text-[0.9em]">Risk <LevelBadge level={live.level} /></p>
          {!compact && live.why.length > 0 && (
            <ul className="mt-2 list-disc space-y-1 pl-5 text-left text-[0.88em] text-[var(--s-muted)]">{live.why.map((w) => <li key={w}>{w}</li>)}</ul>
          )}
          {!compact && live.incident_id && onOpenIncident && (
            <button type="button" onClick={() => onOpenIncident(live.incident_id as number)}
              className="btn-quiet mt-3 min-h-[2.8em] w-full rounded-xl font-bold">See the evidence</button>
          )}
        </div>
      )}
    </div>
  );
}

// ----------------------------------------------------------------- full dashboard
const SIDE: { id: Section; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <I.ShieldPulse size={20} /> },
  { id: 'incidents', label: 'Incidents', icon: <I.Alert size={20} /> },
  { id: 'calls', label: 'Call logs', icon: <I.Phone size={20} /> },
];
type Section = 'overview' | 'incidents' | 'calls';

export function DashboardScreen({ settings, onOpenIncident }: { settings: Settings; onOpenIncident: (id: number) => void }) {
  const [days, setDays] = useState(7);
  const [section, setSection] = useState<Section>('overview');
  const { data, error } = useDashboard(days);
  const s = data?.stats;

  return (
    <div className="lg:flex lg:gap-6">
      <aside className="mb-4 lg:mb-0 lg:w-52 lg:shrink-0">
        <nav aria-label="Dashboard sections" className="s-noscroll flex gap-2 overflow-x-auto lg:sticky lg:top-24 lg:flex-col">
          {SIDE.map((it) => (
            <button key={it.id} type="button" onClick={() => setSection(it.id)} aria-current={section === it.id ? 'page' : undefined}
              className={`flex min-h-[3em] shrink-0 items-center gap-3 rounded-xl px-4 font-bold ${section === it.id ? 'bg-[#10b98126] text-[var(--s-green)] ring-1 ring-[#34d39955]' : 'text-[var(--s-muted)] hover:bg-[var(--s-elev)]'}`}>
              {it.icon}{it.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="min-w-0 flex-1 space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="text-[1.6em] font-extrabold">Security overview</h2>
            <p className="text-[var(--s-muted)]">Real-time call protection, threat detection and incident monitoring.</p>
          </div>
          <label className="flex items-center gap-2 text-[0.9em] text-[var(--s-muted)]">
            <I.Clock size={18} />
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded-xl border px-3 py-2 font-bold" aria-label="Time range">
              <option value={1}>Last 24 hours</option><option value={7}>Last 7 days</option><option value={30}>Last 30 days</option>
            </select>
          </label>
        </div>
        {error && <p role="alert" className="rounded-2xl border border-[#f04438] bg-[#f044381a] p-3">{error}</p>}
        {!data && !error && <p className="text-[var(--s-muted)]">Loading the Mini-SIEM…</p>}

        {data && s && section === 'overview' && (
          <>
            <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
              <Stat icon={<I.ShieldPulse />} value={s.scams_stopped} label="Scams stopped" color="#f04438" note="calls refused + sites blocked" />
              <Stat icon={<I.Phone />} value={s.suspicious_calls} label="Suspicious calls" color="#34d399" note="ordinary calls are never stored" />
              <Stat icon={<I.Alert />} value={s.high_risk_incidents} label="High-risk incidents" color="#a78bfa" />
              <Stat icon={<I.Message />} value={s.messages_checked} label="Messages checked" color="#38bdf8" note={`${s.links_blocked} link${s.links_blocked === 1 ? '' : 's'} blocked`} />
            </div>
            <div className="grid gap-5 xl:grid-cols-2">
              <section className="s-card rounded-2xl p-5"><h3 className="mb-3 font-bold">Threats timeline</h3><Timeline data={data.timeline} /></section>
              <section className="s-card rounded-2xl p-5"><h3 className="mb-3 font-bold">Threat types</h3><Donut items={data.threat_types} /></section>
            </div>
            <div className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
              <IncidentTable data={data} onOpenIncident={onOpenIncident} />
              <section className="s-card rounded-2xl p-5">
                <h3 className="mb-2 font-bold">Live call monitor</h3>
                <LiveCallPanel data={data} settings={settings} compact onOpenIncident={onOpenIncident} />
              </section>
            </div>
          </>
        )}
        {data && section === 'incidents' && <IncidentTable data={data} onOpenIncident={onOpenIncident} full />}
        {data && section === 'calls' && <CallLog calls={data.calls} onOpenIncident={onOpenIncident} />}
        <p className="text-[0.78em] text-[var(--s-muted)]">
          Every number comes from SunoSafe&apos;s own event store. Updated {data ? timeAgo(data.generated_at) : '…'}; refreshes every few seconds.
        </p>
      </div>
    </div>
  );
}

function IncidentTable({ data, onOpenIncident, full = false }: { data: DashboardData; onOpenIncident: (id: number) => void; full?: boolean }) {
  const rows = full ? data.recent_incidents : data.recent_incidents.slice(0, 5);
  return (
    <section className="s-card overflow-hidden rounded-2xl">
      <h3 className="p-5 pb-3 font-bold">Recent incidents</h3>
      {rows.length > 0 && (
        <ul className="divide-y divide-[var(--s-border)] border-t border-[var(--s-border)] sm:hidden">
          {rows.map((r) => (
            <li key={r.id}>
              <button type="button" onClick={() => onOpenIncident(r.id)} className="flex w-full items-start gap-3 p-4 text-left">
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold">{r.title}</span>
                  <span className="block text-[0.82em] text-[var(--s-muted)]">{clock(r.updated_at)} · {r.threat}</span>
                  <span className="block text-[0.82em] text-[var(--s-muted)]">{r.channels.join(' + ') || 'event'} · {r.action}</span>
                </span>
                <LevelBadge level={r.severity} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {rows.length === 0 ? <p className="px-5 pb-5 text-[var(--s-muted)]">No incidents in this period.</p> : (
        <div className="hidden overflow-x-auto sm:block">
          <table className="w-full min-w-[34em] text-left text-[0.88em]">
            <thead className="text-[var(--s-muted)]">
              <tr className="border-y border-[var(--s-border)]">
                <th className="px-5 py-2 font-semibold">Time</th><th className="px-2 py-2 font-semibold">Incident</th>
                <th className="px-2 py-2 font-semibold">Type</th><th className="px-2 py-2 font-semibold">Risk</th><th className="px-5 py-2 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} className="cursor-pointer border-b border-[var(--s-border)] last:border-0 hover:bg-[var(--s-elev)]" onClick={() => onOpenIncident(r.id)}>
                  <td className="whitespace-nowrap px-5 py-3">{clock(r.updated_at)}</td>
                  <td className="px-2 py-3"><button type="button" className="text-left font-semibold underline-offset-2 hover:underline" onClick={() => onOpenIncident(r.id)}>{r.title}</button>
                    <span className="block text-[0.85em] text-[var(--s-muted)]">{r.channels.join(' + ') || 'event'}</span></td>
                  <td className="px-2 py-3">{r.threat}</td>
                  <td className="px-2 py-3"><LevelBadge level={r.severity} /></td>
                  <td className="px-5 py-3"><span className={`rounded-md px-2 py-0.5 text-[0.85em] font-bold ${r.action === 'Blocked' ? 'bg-[#10b98126] text-[#6ee7b7]' : r.action === 'Warned' ? 'bg-[#f59e0b22] text-[#fbbf24]' : 'bg-[#38bdf822] text-[#7dd3fc]'}`}>{r.action}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export function CallLog({ calls, onOpenIncident }: { calls: CallEntry[]; onOpenIncident: (id: number) => void }) {
  return (
    <section className="s-card rounded-2xl p-5">
      <h3 className="font-bold">Call log</h3>
      <p className="text-[0.85em] text-[var(--s-muted)]">Only calls linked to scam evidence are kept. Ordinary callers are checked and forgotten.</p>
      {calls.length === 0 ? <p className="mt-3 text-[var(--s-muted)]">No suspicious calls in this period.</p> : (
        <ul className="mt-3 divide-y divide-[var(--s-border)]">
          {calls.map((c) => (
            <li key={c.id} className="flex items-start gap-3 py-3">
              <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-full" style={{ background: `${LEVEL_COLOR[c.level ?? 'info']}22`, color: LEVEL_COLOR[c.level ?? 'info'] }}><I.Phone size={18} /></span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{c.kind}{c.caller ? ` · ${c.caller}` : ''}</p>
                <p className="text-[0.85em] text-[var(--s-muted)]">{clock(c.ts)}{c.threat ? ` · ${c.threat}` : ''}</p>
                {c.heard && <p className="mt-1 line-clamp-2 text-[0.88em] text-[var(--s-muted)]">“{c.heard}”</p>}
              </div>
              <div className="flex flex-col items-end gap-2">
                <LevelBadge level={c.level} />
                {c.incident_id && <button type="button" onClick={() => onOpenIncident(c.incident_id as number)} className="text-[0.82em] font-bold text-[var(--s-green)]">Evidence</button>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

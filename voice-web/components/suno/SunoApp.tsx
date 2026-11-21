'use client';

import { useCallback, useEffect, useState } from 'react';
import { DEFAULT_SETTINGS, type Lang, LANG_NAMES, type Settings, loadSettings, saveSettings, talkUrl } from './api';
import { IncidentsScreen, SafetyScreen, ScamForm } from './CareScreens';
import { CheckScreen, LinksScreen } from './CheckScreens';
import { CallLog, DashboardScreen, timeAgo, useDashboard, type DashboardData } from './Dashboard';
import { type Key, LangProvider, useT } from './i18n';
import * as I from './icons';
import { BigButton, Card, Tag } from './ui';

type Tab = 'home' | 'check' | 'links' | 'incidents' | 'safety' | 'settings' | 'scam' | 'dashboard' | 'calls';

const TEXT_SIZE = { normal: '16px', large: '19px', xlarge: '22px' } as const;
export const SHARED_KEY = 'sunosafe-shared';

/** Night landscape for the hero card: drawn, not a photo, so it costs nothing to load. */
function NightScene() {
  return (
    <svg aria-hidden viewBox="0 0 400 200" preserveAspectRatio="xMidYMid slice" className="absolute inset-0 h-full w-full">
      <defs>
        <linearGradient id="sky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#1d2b4a" /><stop offset="0.55" stopColor="#3b3f63" /><stop offset="1" stopColor="#6b4e5e" /></linearGradient>
        <radialGradient id="lamp" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stopColor="#ffd27a" stopOpacity="0.95" /><stop offset="1" stopColor="#ffd27a" stopOpacity="0" /></radialGradient>
      </defs>
      <rect width="400" height="200" fill="url(#sky)" />
      {[[40, 30], [90, 18], [150, 40], [230, 22], [300, 35], [360, 15], [200, 55], [120, 60], [330, 60]].map(([x, y]) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="1" fill="#fff" opacity="0.7" />
      ))}
      <path d="M0 130 L60 95 L110 120 L170 80 L230 118 L290 90 L350 115 L400 100 V200 H0Z" fill="#2c3550" opacity="0.9" />
      <path d="M0 150 L50 125 L120 145 L190 118 L260 148 L330 128 L400 140 V200 H0Z" fill="#1b2a35" />
      <g fill="#0d1a17">
        {Array.from({ length: 18 }, (_, i) => {
          const x = i * 24 - 6, h = 30 + ((i * 37) % 26);
          return <path key={i} d={`M${x} 200 L${x + 11} ${200 - h} L${x + 22} 200Z`} />;
        })}
      </g>
      <g transform="translate(322 98)" stroke="#0b1512" strokeWidth="2.5" fill="none">
        <path d="M0 84 L10 18 M28 84 L18 18 M3 62 H25 M6 42 H22" />
        <path d="M2 18 H26 L14 6Z" fill="#0b1512" />
        <rect x="7" y="18" width="14" height="8" fill="#ffcf6b" stroke="none" />
      </g>
      <circle cx="336" cy="120" r="26" fill="url(#lamp)" />
    </svg>
  );
}

function Tile({ icon, label, onClick, href, wide = false }: { icon: React.ReactNode; label: string; onClick?: () => void; href?: string; wide?: boolean }) {
  const cls = `s-card flex min-h-[6.2em] flex-col items-center justify-center gap-2 rounded-2xl px-2 text-center font-bold transition hover:ring-1 hover:ring-[#34d39966] focus:outline-none focus:ring-2 focus:ring-[var(--s-green)] ${wide ? 'col-span-3 sm:col-span-1' : ''}`;
  const inner = <><span className="text-[var(--s-green)]">{icon}</span><span className="text-[0.92em] leading-tight">{label}</span></>;
  return href ? <a href={href} className={cls}>{inner}</a> : <button type="button" onClick={onClick} className={cls}>{inner}</button>;
}

function activityRows(data: DashboardData | null, t: ReturnType<typeof useT>) {
  if (!data) return [];
  const calls = data.calls.slice(0, 3).map((c) => ({
    key: `c${c.id}`, ts: c.ts, danger: c.level === 'high' || c.level === 'critical', incident: c.incident_id,
    title: c.level === 'high' || c.level === 'critical' ? t('home.scamCall') : t('home.suspiciousCall'),
    sub: [c.threat ?? c.kind, c.caller].filter(Boolean).join(' · '),
  }));
  const incidents = data.recent_incidents.filter((i) => !i.channels.includes('call')).slice(0, 3).map((i) => ({
    key: `i${i.id}`, ts: i.updated_at, danger: i.severity === 'high' || i.severity === 'critical', incident: i.id,
    title: i.title, sub: `${i.threat} · ${i.action}`,
  }));
  return [...calls, ...incidents].sort((a, b) => b.ts.localeCompare(a.ts)).slice(0, 4);
}

function HomeScreen({ settings, update, go, openIncident }: {
  settings: Settings; update: (s: Settings) => void; go: (tab: Tab) => void; openIncident: (id: number) => void;
}) {
  const t = useT();
  const { data } = useDashboard(7, 8000);
  const rows = activityRows(data, t);
  return (
    <div className="space-y-4">
      <section className="relative isolate min-h-[11.5em] overflow-hidden rounded-3xl border border-[var(--s-border)]">
        <NightScene />
        <div className="relative z-10 max-w-[70%] p-5">
          <h2 className="text-[1.55em] font-extrabold leading-tight text-white drop-shadow">{t('home.heroTitle')}</h2>
          <p className="mt-2 text-[0.92em] text-white/85 drop-shadow">{t('home.heroText')}</p>
        </div>
      </section>


      <label className="s-card s-glow flex items-center gap-4 rounded-2xl p-4">
        <span className="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-[#10b98126] text-[var(--s-green)]"><I.ShieldPulse size={28} /></span>
        <span className="min-w-0 flex-1">
          <span className="block text-[1.15em] font-extrabold">SunoSafe Shield</span>
          <span className="block text-[0.85em] text-[var(--s-muted)]">
            {settings.shield ? t('home.shieldOn') : t('home.shieldOff')}
          </span>
        </span>
        <input type="checkbox" role="switch" aria-checked={settings.shield} checked={settings.shield}
          onChange={(e) => update({ ...settings, shield: e.target.checked })} className="sr-only" />
        <span aria-hidden className={`relative h-8 w-14 shrink-0 rounded-full transition ${settings.shield ? 'bg-[var(--s-green-strong)]' : 'bg-[#334842]'}`}>
          <span className={`absolute top-1 h-6 w-6 rounded-full bg-white shadow transition-all ${settings.shield ? 'left-7' : 'left-1'}`} />
        </span>
      </label>

      <div className="grid grid-cols-2 gap-3">
        <Tile icon={<I.Phone size={28} />} label={t('home.callHistory')} onClick={() => go('calls')} />
        <Tile icon={<I.Layers size={28} />} label={t('home.threatLogs')} onClick={() => go('incidents')} />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <Tile icon={<I.Chart size={28} />} label={t('home.dashboard')} onClick={() => go('dashboard')} />
        <Tile icon={<I.Gear size={28} />} label={t('home.settings')} onClick={() => go('settings')} />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <BigButton onClick={() => go('check')}><I.Message size={22} /> {t('home.checkMessage')}</BigButton>
        <BigButton tone="quiet" onClick={() => go('links')}><I.Link size={22} /> {t('home.checkLink')}</BigButton>
      </div>
      <a href={talkUrl(settings, null, 'drill')} className="btn-quiet flex min-h-[3.4em] w-full items-center justify-center gap-2 rounded-2xl font-bold">
        <I.Mask size={22} /> {t('home.drill')}
      </a>

      <section>
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[1.15em] font-extrabold">{t('home.recent')}</h3>
          <button type="button" onClick={() => go('dashboard')} className="flex items-center text-[0.9em] font-bold text-[var(--s-green)]">{t('home.viewAll')} <I.Chevron size={18} /></button>
        </div>
        <div className="s-card divide-y divide-[var(--s-border)] rounded-2xl">
          {rows.length === 0 && <p className="p-4 text-[var(--s-muted)]">{data ? t('home.nothing') : t('loading')}</p>}
          {rows.map((r) => (
            <button key={r.key} type="button" onClick={() => r.incident && openIncident(r.incident)} className="flex w-full items-center gap-3 p-4 text-left">
              <span className={`grid h-10 w-10 shrink-0 place-items-center rounded-full ${r.danger ? 'bg-[#f0443822] text-[#ff6b5e]' : 'bg-[#10b98122] text-[var(--s-green)]'}`}>
                {r.danger ? <I.PhoneOff size={20} /> : <I.Check size={20} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate font-bold">{r.title}</span>
                <span className="block truncate text-[0.85em] text-[var(--s-muted)]">{r.sub}</span>
              </span>
              <span className="shrink-0 text-[0.8em] text-[var(--s-muted)]">{timeAgo(r.ts)}</span>
            </button>
          ))}
        </div>
      </section>

      <div className="grid grid-cols-2 gap-3">
        <BigButton tone="danger" onClick={() => go('scam')}><I.Siren size={22} /> {t('home.scammed')}</BigButton>
        <a href="tel:1930" className="btn-quiet flex min-h-[3.75em] items-center justify-center gap-2 rounded-2xl text-[1.1em] font-extrabold">
          <I.Phone size={22} /> {t('home.call1930')}
        </a>
      </div>
    </div>
  );
}

function CallsScreen({ openIncident }: { openIncident: (id: number) => void }) {
  const t = useT();
  const { data, error } = useDashboard(30, 10000);
  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">{t('home.callHistory')}</h2>
      {error && <p role="alert" className="rounded-2xl border border-[#f04438] p-3">{error}</p>}
      {data ? <CallLog calls={data.calls} onOpenIncident={openIncident} /> : <p className="text-[var(--s-muted)]">{t('loading')}</p>}
    </div>
  );
}

/** Install and connect the Android companion that watches notifications automatically. */
function CompanionCard() {
  const t = useT();
  const [note, setNote] = useState('');
  async function connect() {
    setNote('');
    try {
      const response = await fetch('/api/companion/pair');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? 'Could not prepare the connection.');
      // Opens the SunoSafe Android app, which asks you to confirm before connecting.
      window.location.href = data.link;
      setNote(t('comp.notOpened'));
    } catch (e) {
      setNote((e as Error).message);
    }
  }
  return (
    <Card className="border-[#134e4a]">
      <h3 className="text-[1.2em] font-extrabold">{t('comp.title')} <Tag kind="real" /></h3>
      <p className="mt-1 text-[#4b5a56]">{t('comp.text')}</p>
      <ol className="mt-3 list-decimal space-y-1 pl-6">
        <li>{t('comp.s1')}</li>
        <li>{t('comp.s2')}</li>
        <li>{t('comp.s3')}</li>
      </ol>
      <div className="mt-3 space-y-3">
        {/* A file download, not a page: a plain link with `download` is correct here. */}
        <a href="/api/companion/apk" download
          className="flex min-h-[3.75em] w-full items-center justify-center rounded-2xl border border-[#cfcabb] bg-[#eceae0] px-5 text-[1.1em] font-bold">
          ⬇ {t('comp.download')}
        </a>
        <BigButton onClick={connect}>🔗 {t('comp.connect')}</BigButton>
      </div>
      {note && <p role="status" className="mt-3 font-semibold text-[#78350f]">{note}</p>}
    </Card>
  );
}

function Row({ label, hint, checked, onChange }: { label: string; hint: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex min-h-[4em] items-center justify-between gap-4 py-2">
      <span>
        <span className="block font-bold">{label}</span>
        <span className="block text-[0.9em] text-[#4b5a56]">{hint}</span>
      </span>
      <input type="checkbox" role="switch" aria-checked={checked} checked={checked} onChange={(e) => onChange(e.target.checked)}
        className="h-8 w-8 shrink-0 accent-[#134e4a]" />
    </label>
  );
}

function SettingsScreen({ settings, update, go }: { settings: Settings; update: (s: Settings) => void; go: (tab: Tab) => void }) {
  const t = useT();
  const [installHint, setInstallHint] = useState(false);
  async function lock() {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined);
    window.location.href = '/login';
  }
  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">{t('home.settings')}</h2>
      <Card>
        <h3 className="font-bold">{t('set.language')}</h3>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {(Object.keys(LANG_NAMES) as Lang[]).map((code) => (
            <button key={code} type="button" lang={code} aria-pressed={settings.lang === code} onClick={() => update({ ...settings, lang: code })}
              className={`min-h-[3.25em] rounded-2xl border-2 font-bold ${settings.lang === code ? 'border-[#134e4a] bg-[#134e4a] text-white' : 'border-[#cfcabb] bg-white'}`}>
              {LANG_NAMES[code]}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[0.9em] text-[#4b5a56]">{t('set.languageHint')}</p>
      </Card>
      <Card>
        <Row label={t('set.shield')} hint={t('set.shieldHint')} checked={settings.shield}
          onChange={(v) => update({ ...settings, shield: v })} />
        <Row label={t('set.vibrate')} hint={t('set.vibrateHint')} checked={settings.vibrate}
          onChange={(v) => update({ ...settings, vibrate: v })} />
        <fieldset className="mt-2">
          <legend className="font-bold">{t('set.textSize')}</legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {(['normal', 'large', 'xlarge'] as const).map((size) => (
              <button key={size} type="button" aria-pressed={settings.textSize === size} onClick={() => update({ ...settings, textSize: size })}
                className={`min-h-[3.5em] rounded-2xl border-2 font-bold ${settings.textSize === size ? 'border-[#134e4a] bg-[#134e4a] text-white' : 'border-[#cfcabb] bg-white'}`}>
                {t(size === 'normal' ? 'set.normal' : size === 'large' ? 'set.large' : 'set.xlarge')}
              </button>
            ))}
          </div>
        </fieldset>
      </Card>

      <CompanionCard />

      <BigButton tone="quiet" onClick={() => go('safety')}><I.Phone size={22} /> {t('set.callSafety')}</BigButton>

      <Card>
        <h3 className="font-bold">{t('set.homeScreen')}</h3>
        <p className="mt-1 text-[#4b5a56]">{t('set.homeScreenText')}</p>
        <div className="mt-3"><BigButton tone="quiet" onClick={() => setInstallHint(!installHint)}>{t('set.howInstall')}</BigButton></div>
        {installHint && (
          <ol className="mt-3 list-decimal space-y-1 pl-6">
            <li>{t('set.install1')}</li>
            <li>{t('set.install2')}</li>
            <li>{t('set.install3')}</li>
          </ol>
        )}
      </Card>

      <Card>
        <h3 className="text-[1.2em] font-extrabold">What works today</h3>
        <p className="mt-2 font-bold"><Tag kind="real" /></p>
        <ul className="mt-1 list-disc space-y-1 pl-6">
          <li>Voice conversation with SunoSafe (Agora Conversational AI, Murf Falcon voice)</li>
          <li>Message checking by paste or Share</li>
          <li>Link investigation: real destination, website age, security certificate</li>
          <li>Blocking a link after you confirm, and the blocked-site screen</li>
          <li>Incidents, recovery steps, call 1930, report for the police portal</li>
          <li>Reporting a suspicious call you describe</li>
          <li>Automatic checking of new WhatsApp and SMS notifications, with spoken warnings (needs the SunoSafe Android app)</li>
          <li>Warning while the phone rings when a number from a scam message calls (Android app, caller-ID role)</li>
          <li>Scam call practice drill by voice</li>
        </ul>
        <p className="mt-4 font-bold"><Tag kind="simulated" /></p>
        <ul className="mt-1 list-disc space-y-1 pl-6">
          <li>Example scam calls and example notifications inside this web app (made-up input, real analysis)</li>
        </ul>
        <p className="mt-4 font-bold"><Tag kind="planned" /></p>
        <ul className="mt-1 list-disc space-y-1 pl-6">
          <li>Hearing or transcribing ordinary phone calls (Android does not allow apps to do this)</li>
          <li>Catching links opened from any app</li>
          <li>Private warnings inside a SunoSafe internet call (Agora RTC)</li>
                    <li>Alerting a family guardian, only if you choose</li>
        </ul>
        <p className="mt-4 text-[0.9em] text-[#4b5a56]">
          SunoSafe cannot reverse payments, freeze accounts, read your messages by itself or listen to phone calls.
        </p>
      </Card>

      <BigButton tone="quiet" onClick={lock}>🔒 {t('set.lock')}</BigButton>
    </div>
  );
}


const NAV: { tab: Tab | 'talk'; label: Key; icon: React.ReactNode }[] = [
  { tab: 'home', label: 'nav.home', icon: <I.Home size={24} /> },
  { tab: 'incidents', label: 'nav.activity', icon: <I.Activity size={24} /> },
  { tab: 'talk', label: 'nav.talk', icon: <I.ShieldPulse size={30} /> },
  { tab: 'dashboard', label: 'nav.reports', icon: <I.Report size={24} /> },
  { tab: 'settings', label: 'nav.profile', icon: <I.User size={24} /> },
];
const TITLES: Partial<Record<Tab, Key>> = {
  dashboard: 'title.dashboard', calls: 'home.callHistory', incidents: 'home.threatLogs',
  check: 'home.checkMessage', links: 'home.checkLink', settings: 'home.settings', scam: 'title.scam', safety: 'title.safety',
};

export default function SunoApp() {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  useEffect(() => {
    document.documentElement.lang = settings.lang === 'en' ? 'en-IN' : `${settings.lang}-IN`;
  }, [settings.lang]);
  return (
    <LangProvider value={settings.lang}>
      <SunoShell settings={settings} setSettings={setSettings} />
    </LangProvider>
  );
}

function SunoShell({ settings, setSettings }: { settings: Settings; setSettings: (s: Settings) => void }) {
  const t = useT();
  const [tab, setTab] = useState<Tab>('home');
  const [shared, setShared] = useState('');
  const [sharedSource, setSharedSource] = useState<'share' | 'paste'>('paste');
  const [incidentId, setIncidentId] = useState<number | null>(null);
  const [scamFor, setScamFor] = useState<number | null>(null);

  useEffect(() => {
    setSettings(loadSettings());
    // A message arriving from the Share menu was parked by /share.
    try {
      const parked = sessionStorage.getItem(SHARED_KEY);
      if (parked) {
        sessionStorage.removeItem(SHARED_KEY);
        setShared(parked);
        setSharedSource('share');
        setTab('check');
      }
    } catch {
      /* storage unavailable */
    }
    // Deep links: /?incident=12, /?tab=incidents|dashboard|calls
    const params = new URLSearchParams(window.location.search);
    const linked = Number(params.get('incident'));
    const wanted = params.get('tab');
    if (Number.isInteger(linked) && linked > 0) {
      setIncidentId(linked);
      setTab('incidents');
    } else if (wanted === 'incidents' || wanted === 'dashboard' || wanted === 'calls') {
      setTab(wanted);
    }
    if (params.toString()) window.history.replaceState(null, '', '/');
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined);
  }, []);

  const update = useCallback((next: Settings) => {
    setSettings(next);
    saveSettings(next);
  }, [setSettings]);

  const go = useCallback((next: Tab) => {
    if (next === 'incidents') setIncidentId(null);
    if (next === 'scam') setScamFor(null);
    setTab(next);
    window.scrollTo({ top: 0 });
  }, []);

  const openIncident = useCallback((id: number) => {
    setIncidentId(id);
    setTab('incidents');
    window.scrollTo({ top: 0 });
  }, []);

  const consumeShared = useCallback(() => setShared(''), []);
  const wide = tab === 'dashboard';

  return (
    <div className="suno min-h-dvh" style={{ fontSize: TEXT_SIZE[settings.textSize] }}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-[var(--s-surface)] focus:p-3">
        {t('nav.skip')}
      </a>
      <header className="sticky top-0 z-30 border-b border-[var(--s-border)] bg-[#07130fe6] backdrop-blur">
        <div className={`mx-auto flex items-center gap-3 px-4 py-3 ${wide ? 'max-w-7xl' : 'max-w-xl'}`}>
          {tab !== 'home' ? (
            <button type="button" onClick={() => go('home')} aria-label={t('nav.back')} className="grid h-10 w-10 place-items-center rounded-xl text-[var(--s-muted)] hover:bg-[var(--s-elev)]">
              <I.Back />
            </button>
          ) : null}
          <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#10b98126] text-[var(--s-green)]"><I.ShieldPulse size={26} /></span>
          <div className="min-w-0 flex-1">
            <h1 className="text-[1.25em] font-extrabold leading-tight">SunoSafe</h1>
            <p className="truncate text-[0.78em] text-[var(--s-muted)]">{t(TITLES[tab] ?? 'title.default')}</p>
          </div>
          <a href={talkUrl(settings)} className="btn-primary hidden min-h-[2.6em] items-center gap-2 rounded-xl px-4 text-[0.9em] font-bold sm:flex">
            <I.Mic size={18} /> {t('nav.talk')}
          </a>
        </div>
      </header>

      <main id="main" className={`mx-auto w-full px-4 pb-[8em] pt-4 ${wide ? 'max-w-7xl' : 'max-w-xl'}`}>
        {tab === 'home' && <HomeScreen settings={settings} update={update} go={go} openIncident={openIncident} />}
        {tab === 'dashboard' && <DashboardScreen onOpenIncident={openIncident} />}
        {tab === 'calls' && <CallsScreen openIncident={openIncident} />}
        {tab === 'check' && (
          <CheckScreen
            settings={settings}
            sharedText={shared}
            sharedSource={sharedSource}
            onConsumedShared={consumeShared}
            onReportScam={(id) => { setScamFor(id); setTab('scam'); window.scrollTo({ top: 0 }); }}
          />
        )}
        {tab === 'links' && <LinksScreen settings={settings} />}
        {tab === 'scam' && <ScamForm incidentId={scamFor} settings={settings} onDone={(id) => openIncident(id)} />}
        {tab === 'incidents' && (
          <IncidentsScreen openId={incidentId} onOpen={setIncidentId} onReportScam={() => go('scam')} settings={settings} />
        )}
        {tab === 'safety' && <SafetyScreen settings={settings} onOpenIncident={openIncident} />}
        {tab === 'settings' && <SettingsScreen settings={settings} update={update} go={go} />}
      </main>

      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-[var(--s-border)] bg-[#0a1813f2] pb-[env(safe-area-inset-bottom)] backdrop-blur">
        <ul className="mx-auto grid max-w-xl grid-cols-5 items-end">
          {NAV.map((item) => {
            if (item.tab === 'talk') {
              return (
                <li key="talk" className="flex justify-center">
                  <a href={talkUrl(settings)} aria-label={t('nav.talk')}
                    className="s-pulse -mt-7 mb-2 grid h-16 w-16 place-items-center rounded-full border-4 border-[#07130f] bg-gradient-to-br from-[#10b981] to-[#047857] text-white shadow-lg">
                    {item.icon}
                  </a>
                </li>
              );
            }
            const active = tab === item.tab || (item.tab === 'incidents' && tab === 'scam')
              || (item.tab === 'dashboard' && tab === 'calls');
            return (
              <li key={item.tab}>
                <button type="button" onClick={() => go(item.tab as Tab)} aria-current={active ? 'page' : undefined}
                  className={`flex min-h-[4.2em] w-full flex-col items-center justify-center gap-1 text-[0.78em] font-bold focus:outline-none focus:ring-2 focus:ring-inset focus:ring-[var(--s-green)] ${active ? 'text-[var(--s-green)]' : 'text-[var(--s-muted)]'}`}>
                  {item.icon}
                  {t(item.label)}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

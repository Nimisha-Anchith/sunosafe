'use client';

import { useCallback, useEffect, useState } from 'react';
import { DEFAULT_SETTINGS, type Incident, type Lang, LANG_NAMES, type Settings, api, loadSettings, saveSettings, talkUrl } from './api';
import { IncidentsScreen, SafetyScreen, ScamForm } from './CareScreens';
import { CheckScreen, LinksScreen } from './CheckScreens';
import { BigButton, Card, Tag } from './ui';

type Tab = 'home' | 'check' | 'links' | 'incidents' | 'safety' | 'settings' | 'scam';

const NAV: { tab: Tab; label: string; icon: string }[] = [
  { tab: 'home', label: 'Home', icon: '🏠' },
  { tab: 'check', label: 'Check', icon: '🔍' },
  { tab: 'incidents', label: 'Help', icon: '🆘' },
  { tab: 'safety', label: 'Calls', icon: '📞' },
  { tab: 'settings', label: 'Settings', icon: '⚙️' },
];

const TEXT_SIZE = { normal: '16px', large: '19px', xlarge: '22px' } as const;
export const SHARED_KEY = 'sunosafe-shared';

function HomeScreen({ settings, go, openIncidents }: { settings: Settings; go: (tab: Tab) => void; openIncidents: number }) {
  return (
    <div className="space-y-4">
      <div
        className={`rounded-3xl p-5 text-white shadow-lg ${settings.shield ? 'bg-gradient-to-br from-[#0f3d3a] to-[#1a6b65] shadow-teal-900/25' : 'bg-[#6b7280]'}`}
        role="status"
      >
        <p className="text-[0.9em] font-bold uppercase tracking-wide opacity-90">SunoSafe shield</p>
        <p className="text-[1.7em] font-extrabold">{settings.shield ? '🛡️ On and ready' : '⏸ Paused'}</p>
        <p className="mt-1 opacity-95">
          {settings.shield
            ? 'Ask me about any message, link or call that worries you.'
            : 'Checks are switched off. Turn the shield on in Settings.'}
        </p>
      </div>

      <a
        href={talkUrl(settings)}
        className="flex min-h-[5.5em] w-full items-center justify-center gap-4 rounded-3xl bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] px-5 text-[1.35em] font-extrabold text-[#1f1300] shadow-lg shadow-amber-900/20 focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40"
      >
        <span aria-hidden className="text-[1.6em]">🎤</span> Talk to SunoSafe
      </a>
      <a
        href={talkUrl(settings, null, 'drill')}
        className="flex min-h-[3.75em] w-full items-center justify-center gap-3 rounded-2xl border-2 border-[#134e4a] bg-white px-5 text-[1.1em] font-bold text-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40"
      >
        🎭 Practise: scam call drill
      </a>
      <BigButton onClick={() => go('check')}>🔍 Check a message</BigButton>
      <BigButton tone="quiet" onClick={() => go('links')}>🌐 Check or open a link</BigButton>
      <BigButton tone="danger" onClick={() => go('scam')}>🆘 I think I was scammed</BigButton>

      {openIncidents > 0 && (
        <button type="button" onClick={() => go('incidents')}
          className="block w-full rounded-3xl border-2 border-[#b45309] bg-[#fffbeb] p-5 text-left font-bold text-[#78350f] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40">
          You have {openIncidents} open incident{openIncidents > 1 ? 's' : ''} with steps to finish. Tap to continue.
        </button>
      )}

      <Card>
        <h2 className="font-bold">In an emergency</h2>
        <p className="mt-1 text-[#4b5a56]">If money has left your account, call India&apos;s cyber-crime helpline straight away.</p>
        <a href="tel:1930" className="mt-3 flex min-h-[3.75em] w-full items-center justify-center rounded-2xl bg-[#b42318] text-[1.2em] font-extrabold text-white">
          📞 Call 1930
        </a>
      </Card>
    </div>
  );
}

/** Install and connect the Android companion that watches notifications automatically. */
function CompanionCard() {
  const [note, setNote] = useState('');
  async function connect() {
    setNote('');
    try {
      const response = await fetch('/api/companion/pair');
      const data = await response.json();
      if (!response.ok) throw new Error(data.error ?? 'Could not prepare the connection.');
      // Opens the SunoSafe Android app, which asks you to confirm before connecting.
      window.location.href = data.link;
      setNote('If nothing opened, install the SunoSafe Android app first (step 1).');
    } catch (e) {
      setNote((e as Error).message);
    }
  }
  return (
    <Card className="border-[#134e4a]">
      <h3 className="text-[1.2em] font-extrabold">Automatic scam warnings <Tag kind="real" /></h3>
      <p className="mt-1 text-[#4b5a56]">
        The SunoSafe Android app watches new WhatsApp and SMS notifications and warns you aloud when one looks like a
        scam. Ordinary messages never leave your phone.
      </p>
      <ol className="mt-3 list-decimal space-y-1 pl-6">
        <li>Install the Android app.</li>
        <li>Open it and turn on notification access.</li>
        <li>Come back here and tap Connect.</li>
      </ol>
      <div className="mt-3 space-y-3">
        {/* A file download, not a page: a plain link with `download` is correct here. */}
        <a href="/api/companion/apk" download
          className="flex min-h-[3.75em] w-full items-center justify-center rounded-2xl border border-[#cfcabb] bg-[#eceae0] px-5 text-[1.1em] font-bold">
          ⬇ 1. Download the Android app
        </a>
        <BigButton onClick={connect}>🔗 3. Connect Android app</BigButton>
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

function SettingsScreen({ settings, update }: { settings: Settings; update: (s: Settings) => void }) {
  const [installHint, setInstallHint] = useState(false);
  async function lock() {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined);
    window.location.href = '/login';
  }
  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Settings</h2>
      <Card>
        <Row label="SunoSafe shield" hint="When off, SunoSafe checks nothing and sends nothing." checked={settings.shield}
          onChange={(v) => update({ ...settings, shield: v })} />
        <Row label="Vibrate on danger" hint="The phone buzzes when something dangerous is found." checked={settings.vibrate}
          onChange={(v) => update({ ...settings, vibrate: v })} />
        <fieldset className="mt-2">
          <legend className="font-bold">Text size</legend>
          <div className="mt-2 grid grid-cols-3 gap-2">
            {(['normal', 'large', 'xlarge'] as const).map((size) => (
              <button key={size} type="button" aria-pressed={settings.textSize === size} onClick={() => update({ ...settings, textSize: size })}
                className={`min-h-[3.5em] rounded-2xl border-2 font-bold ${settings.textSize === size ? 'border-[#134e4a] bg-[#134e4a] text-white' : 'border-[#cfcabb] bg-white'}`}>
                {size === 'normal' ? 'Normal' : size === 'large' ? 'Large' : 'Largest'}
              </button>
            ))}
          </div>
        </fieldset>
      </Card>

      <CompanionCard />

      <Card>
        <h3 className="font-bold">Voice language</h3>
        <div className="mt-2 grid grid-cols-3 gap-2">
          {(Object.keys(LANG_NAMES) as Lang[]).map((code) => (
            <button key={code} type="button" aria-pressed={settings.lang === code} onClick={() => update({ ...settings, lang: code })}
              className={`min-h-[3.25em] rounded-2xl border-2 font-bold ${settings.lang === code ? 'border-[#134e4a] bg-[#134e4a] text-white' : 'border-[#cfcabb] bg-white'}`}>
              {LANG_NAMES[code]}
            </button>
          ))}
        </div>
        <p className="mt-2 text-[0.9em] text-[#4b5a56]">
          SunoSafe replies and speaks (Murf Falcon voice) in the language you choose. It listens in English and
          Hindi; listening in Malayalam, Kannada and Tamil is not switched on yet.
        </p>
      </Card>

      <Card>
        <h3 className="font-bold">Put SunoSafe on your home screen</h3>
        <p className="mt-1 text-[#4b5a56]">This also adds SunoSafe to the Share menu of WhatsApp and Messages.</p>
        <div className="mt-3"><BigButton tone="quiet" onClick={() => setInstallHint(!installHint)}>How to install</BigButton></div>
        {installHint && (
          <ol className="mt-3 list-decimal space-y-1 pl-6">
            <li>In Chrome, tap the ⋮ menu at the top right.</li>
            <li>Tap <strong>Add to Home screen</strong>, then <strong>Install</strong>.</li>
            <li>Open SunoSafe from its new icon.</li>
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

      <BigButton tone="quiet" onClick={lock}>🔒 Lock SunoSafe</BigButton>
    </div>
  );
}

export default function SunoApp() {
  const [tab, setTab] = useState<Tab>('home');
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [shared, setShared] = useState('');
  const [sharedSource, setSharedSource] = useState<'share' | 'paste'>('paste');
  const [incidentId, setIncidentId] = useState<number | null>(null);
  const [scamFor, setScamFor] = useState<number | null>(null);
  const [openIncidents, setOpenIncidents] = useState(0);

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
    // Deep links from the Android companion: /?incident=12 or /?tab=incidents
    const params = new URLSearchParams(window.location.search);
    const linked = Number(params.get('incident'));
    if (Number.isInteger(linked) && linked > 0) {
      setIncidentId(linked);
      setTab('incidents');
    } else if (params.get('tab') === 'incidents') {
      setTab('incidents');
    }
    if (params.toString()) window.history.replaceState(null, '', '/');
    if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => undefined);
  }, []);

  useEffect(() => {
    if (tab !== 'home') return;
    api<Incident[]>('incidents')
      .then((list) => setOpenIncidents(list.filter((i) => i.status === 'open' || i.status === 'contained').length))
      .catch(() => undefined);
  }, [tab]);

  const update = useCallback((next: Settings) => {
    setSettings(next);
    saveSettings(next);
  }, []);

  const go = useCallback((next: Tab) => {
    if (next === 'incidents') setIncidentId(null);
    if (next === 'scam') setScamFor(null);
    setTab(next);
    window.scrollTo({ top: 0 });
  }, []);

  const consumeShared = useCallback(() => setShared(''), []);

  return (
    <div className="suno min-h-dvh bg-[#f5f3ec] text-[#14201d]" style={{ fontSize: TEXT_SIZE[settings.textSize] }}>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-xl focus:bg-white focus:p-3">
        Skip to content
      </a>
      <header className="sticky top-0 z-30 bg-gradient-to-r from-[#0f3d3a] to-[#1a6b65] px-5 py-3 text-white shadow-md">
        <h1 className="text-[1.3em] font-extrabold leading-tight">🛡️ SunoSafe</h1>
        <p className="text-[0.75em] opacity-90">Hear the warning · Understand the threat · Take action</p>
      </header>

      <main id="main" className="mx-auto w-full max-w-xl px-4 pb-[7.5em] pt-4">
        {tab === 'home' && <HomeScreen settings={settings} go={go} openIncidents={openIncidents} />}
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
        {tab === 'scam' && (
          <ScamForm incidentId={scamFor} settings={settings}
            onDone={(id) => { setIncidentId(id); setTab('incidents'); window.scrollTo({ top: 0 }); }} />
        )}
        {tab === 'incidents' && (
          <IncidentsScreen openId={incidentId} onOpen={setIncidentId} onReportScam={() => go('scam')} settings={settings} />
        )}
        {tab === 'safety' && (
          <SafetyScreen settings={settings} onOpenIncident={(id) => { setIncidentId(id); setTab('incidents'); window.scrollTo({ top: 0 }); }} />
        )}
        {tab === 'settings' && <SettingsScreen settings={settings} update={update} />}
      </main>

      <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-30 border-t border-[#cfcabb] bg-white pb-[env(safe-area-inset-bottom)]">
        <ul className="mx-auto grid max-w-xl grid-cols-5">
          {NAV.map((item) => {
            const active = tab === item.tab || (item.tab === 'check' && tab === 'links') || (item.tab === 'incidents' && tab === 'scam');
            return (
              <li key={item.tab}>
                <button type="button" onClick={() => go(item.tab)} aria-current={active ? 'page' : undefined}
                  className={`flex min-h-[4.25em] w-full flex-col items-center justify-center gap-0.5 text-[0.8em] font-bold focus:outline-none focus:ring-4 focus:ring-inset focus:ring-[#134e4a]/40 ${active ? 'bg-[#e6f2ef] text-[#134e4a]' : 'text-[#4b5a56]'}`}>
                  <span aria-hidden className="text-[1.5em] leading-none">{item.icon}</span>
                  {item.label}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>
    </div>
  );
}

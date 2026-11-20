'use client';

import { useCallback, useEffect, useState } from 'react';
import { type AnalyzeResult, type Incident, type SecurityEvent, type Settings, type Step, type Verdict, api, buzz, talkUrl } from './api';

const EVENT_LABELS: Record<string, { icon: string; label: string }> = {
  message_analysed: { icon: '✉️', label: 'Message checked' },
  url_investigated: { icon: '🔎', label: 'Link investigated' },
  call_reported: { icon: '📞', label: 'Call reported by you' },
  call_screened: { icon: '📲', label: 'Incoming call screened' },
  call_shielded: { icon: '🛡️', label: 'SunoSafe answered a scam call' },
  correlation_cross_channel: { icon: '🧩', label: 'Linked: same scam by message and call' },
  incident_created: { icon: '📁', label: 'Incident opened' },
  incident_updated: { icon: '⬆️', label: 'Severity raised' },
  remediation_completed: { icon: '🚫', label: 'Action approved and done' },
  protected_browser_block: { icon: '🛑', label: 'Blocked website stopped' },
  user_reported_scam: { icon: '🆘', label: 'You reported a possible scam' },
  step_updated: { icon: '✅', label: 'Recovery step updated' },
};

const SOURCE_LABELS: Record<string, string> = {
  'message_rules/notification': 'phone notification',
  'message_rules/screen': 'message on screen (WhatsApp/SMS)',
  'message_rules/sms': 'SMS (read by SunoSafe)',
  'message_rules/share': 'message you shared',
  'call_shield': 'SunoSafe call assistant',
  'message_rules/share': 'shared message',
  'message_rules/paste': 'pasted message',
  'message_rules/voice': 'spoken message',
  investigator: 'link investigator',
  call_screening: 'call screening',
  user_report: 'your report',
  correlation: 'correlation engine',
  'blocklist/voice': 'approved by voice',
  'blocklist/app': 'approved in the app',
  protected_browser: 'protected browser',
};

function Timeline({ events }: { events: SecurityEvent[] }) {
  return (
    <ol className="relative ml-3 border-l-2 border-[#cfcabb]">
      {events.map((e) => {
        const meta = EVENT_LABELS[e.type] ?? { icon: '•', label: e.type.replace(/_/g, ' ') };
        return (
          <li key={e.id} className="mb-4 ml-5">
            <span aria-hidden className="absolute -left-[0.85em] flex h-[1.7em] w-[1.7em] items-center justify-center rounded-full bg-white text-[0.9em] shadow">
              {meta.icon}
            </span>
            <p className="font-bold">{meta.label}{e.level ? <span className="ml-2 align-middle"><Severity level={e.level} /></span> : null}</p>
            <p className="text-[0.95em]">{e.summary}</p>
            <p className="text-[0.8em] text-[#4b5a56]">
              {new Date(e.ts).toLocaleString()} · source: {SOURCE_LABELS[e.source] ?? e.source}
            </p>
          </li>
        );
      })}
    </ol>
  );
}
import { BigButton, Card, ErrorNote, Tag, VerdictCard } from './ui';

const SEVERITY_STYLE: Record<string, string> = {
  critical: 'bg-[#7a271a] text-white',
  high: 'bg-[#b42318] text-white',
  medium: 'bg-[#b45309] text-white',
  low: 'bg-[#166534] text-white',
  info: 'bg-[#4b5563] text-white',
};

function Severity({ level }: { level: string }) {
  return (
    <span className={`rounded-full px-3 py-0.5 text-[0.8em] font-bold uppercase ${SEVERITY_STYLE[level] ?? SEVERITY_STYLE.info}`}>
      {level}
    </span>
  );
}

/** Real-world action for a recovery step, where the phone can help directly. */
function StepAction({ code }: { code: string }) {
  const link = 'flex min-h-[3.25em] w-full items-center justify-center rounded-2xl bg-[#134e4a] px-4 text-[1.05em] font-bold text-white';
  if (code === 'call_1930') return <a className={link} href="tel:1930">📞 Call 1930 now</a>;
  if (code === 'report_cybercrime_portal')
    return <a className={link} href="https://cybercrime.gov.in" target="_blank" rel="noopener noreferrer">Open cybercrime.gov.in</a>;
  if (code === 'report_chakshu')
    return <a className={link} href="https://sancharsaathi.gov.in" target="_blank" rel="noopener noreferrer">Open Sanchar Saathi</a>;
  return null;
}

// ---------------------------------------------------------------------------
// "I was scammed" form
// ---------------------------------------------------------------------------
const DISCLOSURES: [string, string][] = [
  ['otp', 'An OTP'],
  ['upi_pin', 'My UPI PIN'],
  ['password', 'A password'],
  ['card_details', 'Card number or CVV'],
  ['bank_details', 'Bank account details'],
  ['aadhaar', 'Aadhaar number'],
  ['money_paid', 'I paid or lost money'],
  ['remote_app_installed', 'I installed an app they asked for'],
];

export function ScamForm({
  incidentId,
  settings,
  onDone,
}: {
  incidentId: number | null;
  settings: Settings;
  onDone: (incidentId: number) => void;
}) {
  const [description, setDescription] = useState('');
  const [picked, setPicked] = useState<string[]>([]);
  const [amount, setAmount] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const out = await api<{ incident_id: number }>('incidents/report-scam', {
        method: 'POST',
        body: {
          description: description.trim() || 'The user reported a possible scam.',
          disclosed: picked,
          amount_lost: amount ? Number(amount) : null,
          incident_id: incidentId,
        },
      });
      buzz(settings, [200, 100, 200]);
      onDone(out.incident_id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Tell me what happened</h2>
      <p className="rounded-2xl bg-[#fffbeb] p-4 font-semibold text-[#78350f]">
        This is not your fault. Acting quickly gives the best chance of stopping it.
      </p>
      <fieldset>
        <legend className="font-bold">What did you share or do? Tap all that apply.</legend>
        <div className="mt-2 space-y-2">
          {DISCLOSURES.map(([code, label]) => (
            <label key={code} className="flex min-h-[3.5em] items-center gap-4 rounded-2xl border-2 border-[#cfcabb] bg-white px-4">
              <input
                type="checkbox"
                className="h-7 w-7 accent-[#134e4a]"
                checked={picked.includes(code)}
                onChange={(ev) => setPicked(ev.target.checked ? [...picked, code] : picked.filter((p) => p !== code))}
              />
              <span className="font-semibold">{label}</span>
            </label>
          ))}
        </div>
      </fieldset>
      {picked.includes('money_paid') && (
        <div>
          <label htmlFor="amount" className="block font-bold">How much, in rupees? (if you know)</label>
          <input id="amount" inputMode="numeric" value={amount} onChange={(ev) => setAmount(ev.target.value.replace(/\D/g, '').slice(0, 9))}
            className="mt-2 h-16 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white px-4" />
        </div>
      )}
      <div>
        <label htmlFor="what" className="block font-bold">In your own words (optional)</label>
        <textarea id="what" rows={3} maxLength={3000} value={description} onChange={(ev) => setDescription(ev.target.value)}
          className="mt-2 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white p-4" />
      </div>
      <ErrorNote message={error} />
      <BigButton type="submit" tone="danger" disabled={busy}>{busy ? 'Making your recovery plan…' : 'Get my recovery plan'}</BigButton>
    </form>
  );
}

// ---------------------------------------------------------------------------
// Incidents and guided recovery
// ---------------------------------------------------------------------------
export function IncidentsScreen({ openId, onOpen, onReportScam, settings }: { openId: number | null; onOpen: (id: number | null) => void; onReportScam: () => void; settings: Settings }) {
  const [list, setList] = useState<Incident[] | null>(null);
  const [detail, setDetail] = useState<Incident | null>(null);
  const [summary, setSummary] = useState('');
  const [error, setError] = useState('');

  const loadList = useCallback(() => {
    api<Incident[]>('incidents').then(setList).catch((e) => setError((e as Error).message));
  }, []);
  const loadDetail = useCallback((id: number) => {
    setSummary('');
    api<Incident>(`incidents/${id}`).then(setDetail).catch((e) => setError((e as Error).message));
  }, []);

  useEffect(() => {
    if (openId) loadDetail(openId);
    else {
      setDetail(null);
      loadList();
    }
  }, [openId, loadDetail, loadList]);

  async function setStep(step: Step, status: 'done' | 'skipped' | 'pending') {
    if (!detail) return;
    try {
      await api(`incidents/${detail.id}/steps/${step.code}`, { method: 'PATCH', body: { status, actor: 'user' } });
      loadDetail(detail.id);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function showSummary() {
    if (!detail) return;
    try {
      const text = await api<string>(`incidents/${detail.id}/summary`);
      setSummary(text);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  async function shareSummary() {
    try {
      if (navigator.share) await navigator.share({ title: 'SunoSafe incident report', text: summary });
      else await navigator.clipboard.writeText(summary);
    } catch {
      /* user cancelled the share sheet */
    }
  }

  if (detail) {
    const steps = detail.steps ?? [];
    const reasons = detail.rationale.filter((r) => r.text);
    return (
      <div className="space-y-4">
        <BigButton tone="quiet" onClick={() => onOpen(null)}>← All incidents</BigButton>
        <Card>
          <Severity level={detail.severity} />
          <h2 className="mt-2 text-[1.4em] font-extrabold">{detail.title}</h2>
          <p className="text-[#4b5a56]">Status: {detail.status} · opened {new Date(detail.created_at).toLocaleString()}</p>
          {reasons.length > 0 && (
            <ul className="mt-3 list-disc space-y-1 pl-6">
              {reasons.slice(0, 4).map((r, i) => <li key={i}>{r.text}</li>)}
            </ul>
          )}
        </Card>
        <a href={talkUrl(settings, detail.id)}
          className="flex min-h-[3.75em] w-full items-center justify-center gap-3 rounded-2xl bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] px-5 text-[1.1em] font-extrabold text-[#1f1300] shadow">
          🎤 Hear SunoSafe explain this
        </a>
        {detail.events && detail.events.length > 0 && (
          <Card>
            <h3 className="mb-3 text-[1.3em] font-extrabold">Evidence timeline</h3>
            <Timeline events={detail.events} />
          </Card>
        )}
        <h3 className="text-[1.3em] font-extrabold">What to do, one step at a time</h3>
        {steps.map((step, index) => (
          <Card key={step.code} className={step.status === 'done' ? 'opacity-70' : ''}>
            <p className="text-[0.85em] font-bold text-[#4b5a56]">Step {index + 1} of {steps.length} · {step.status === 'pending' ? 'to do' : step.status}</p>
            <h4 className="text-[1.15em] font-extrabold">{step.status === 'done' ? '✔️ ' : ''}{step.title}</h4>
            <p className="mt-1">{step.detail}</p>
            <div className="mt-3 space-y-2">
              <StepAction code={step.code} />
              {step.code === 'block_link' ? (
                step.status !== 'done' && <p className="text-[#4b5a56]">Use the Block button on the Check or Links screen, so the link is really blocked.</p>
              ) : step.status === 'pending' ? (
                <div className="grid grid-cols-2 gap-2">
                  <BigButton tone="quiet" onClick={() => setStep(step, 'done')}>I did this</BigButton>
                  <BigButton tone="quiet" onClick={() => setStep(step, 'skipped')}>Skip</BigButton>
                </div>
              ) : (
                <BigButton tone="quiet" onClick={() => setStep(step, 'pending')}>Undo</BigButton>
              )}
            </div>
          </Card>
        ))}
        <ErrorNote message={error} />
        <BigButton onClick={showSummary}>📄 Make a report for 1930 or the police portal</BigButton>
        {summary && (
          <Card>
            <pre className="whitespace-pre-wrap break-words font-mono text-[0.8em]">{summary}</pre>
            <div className="mt-3"><BigButton tone="quiet" onClick={shareSummary}>Share or copy this report</BigButton></div>
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Your incidents</h2>
      <BigButton tone="danger" onClick={onReportScam}>🆘 I think I was scammed</BigButton>
      <ErrorNote message={error} />
      {list === null ? (
        <p>Loading…</p>
      ) : list.length === 0 ? (
        <Card><p>No incidents. When SunoSafe finds something dangerous, it will appear here with a recovery plan.</p></Card>
      ) : (
        list.map((incident) => (
          <button key={incident.id} type="button" onClick={() => onOpen(incident.id)}
            className="block w-full rounded-3xl border border-[#d9d5c7] bg-white p-5 text-left focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40">
            <Severity level={incident.severity} />
            <span className="mt-2 block text-[1.15em] font-extrabold">{incident.title}</span>
            <span className="block text-[#4b5a56]">{incident.status} · {new Date(incident.updated_at).toLocaleString()}</span>
          </button>
        ))
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Safety: calls and notifications (real reports + clearly labelled simulations)
// ---------------------------------------------------------------------------
const ASKED: [string, string][] = [
  ['otp', 'An OTP'],
  ['upi_pin', 'UPI PIN'],
  ['card_details', 'Card details'],
  ['remote_app', 'To install an app'],
  ['money', 'To send money'],
];

const CALL_SCENARIOS = [
  { title: '"Digital arrest" call', description: 'Caller said he is from CBI cyber cell, a parcel in my name has drugs, I am under digital arrest and must stay on video call and install AnyDesk.', asked: ['remote_app', 'money'] },
  { title: 'Fake bank KYC call', description: 'Caller said he is from SBI KYC team, my account will be blocked today and I must tell him the OTP sent to my phone.', asked: ['otp'] },
];

const NOTIFICATION_SCENARIOS = [
  { app: 'Messages', sender: 'VM-ELCBIL', text: 'Dear customer, your electricity power will be disconnected tonight at 9.30 pm because previous month bill was not updated. Please immediately call our officer 9876501234.' },
  { app: 'WhatsApp', sender: '+91 98XXX XX321', text: 'Congratulations! You won Rs 25,00,000 in KBC lucky draw. To receive money enter your UPI PIN here: upi://pay?pa=kbc-prize@ybl&am=1' },
];

const DEMO_SMS = '[SIMULATED DEMO] Dear SBI customer, your account will be BLOCKED today. Update KYC at '
  + 'https://wrong.host.badssl.com/sbi-kyc-demo and share the OTP sent to you. Call 9876543210.';

/**
 * Signature workflow: SunoSafe Intervention Intelligence. The inputs are simulated
 * (clearly labelled); everything after that is the real engine: link investigation,
 * mini-SIEM evidence, cross-channel correlation and the briefed voice agent.
 */
function InterventionDemo({ settings, onOpenIncident }: { settings: Settings; onOpenIncident: (id: number) => void }) {
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [msg, setMsg] = useState<AnalyzeResult | null>(null);
  const [callResult, setCallResult] = useState<{ incident_id: number | null; verdict: Verdict } | null>(null);

  async function sms() {
    setBusy(true); setError('');
    try {
      const out = await api<AnalyzeResult>('messages/analyze', { method: 'POST', body: { text: DEMO_SMS, source: 'notification' } });
      setMsg(out); setStep(1);
      if (out.verdict.label === 'danger') buzz(settings, [300, 120, 300]);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  async function caller() {
    setBusy(true); setError('');
    try {
      const out = await api<{ incident_id: number | null; verdict: Verdict }>('calls/report', {
        method: 'POST',
        body: { description: '[SIMULATED DEMO] Caller said he is from SBI KYC team and asked me to tell him the OTP.',
          caller_number: '9876543210', asked_for: ['otp'] },
      });
      setCallResult(out); setStep(2);
      buzz(settings, [300, 120, 300, 120, 300]);
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }

  const linked = msg?.incident_id && callResult?.incident_id === msg.incident_id;
  return (
    <Card className="border-2 border-[#134e4a] bg-gradient-to-br from-white to-[#eef7f5]">
      <h3 className="text-[1.25em] font-extrabold">🧩 Intervention demo <Tag kind="simulated" /></h3>
      <p className="mt-1 text-[#4b5a56]">
        Made-up inputs, real engine. Shows how SunoSafe joins a fake bank SMS and a fake bank call into one scam story.
        On a phone with the SunoSafe Android app, the SMS step happens automatically.
      </p>
      <ol className="mt-3 space-y-3">
        <li>
          <BigButton tone={step === 0 ? 'primary' : 'quiet'} disabled={busy} onClick={sms}>1. A fake SBI KYC SMS arrives</BigButton>
          {msg && <p className="mt-2 font-semibold">→ {msg.verdict.label === 'danger' ? '⛔ Danger' : '⚠️ Caution'}: {msg.verdict.summary}</p>}
        </li>
        <li>
          <BigButton tone={step === 1 ? 'primary' : 'quiet'} disabled={busy || step < 1} onClick={caller}>2. A caller says he is from SBI and asks for the OTP</BigButton>
          {callResult && (
            <p className="mt-2 font-semibold">
              → {linked ? `Linked into the same incident #${callResult.incident_id}: the same scam by message and call.` : callResult.verdict.summary}
            </p>
          )}
        </li>
        <li>
          {callResult?.incident_id ? (
            <a href={talkUrl(settings, callResult.incident_id)}
              className="flex min-h-[3.75em] w-full items-center justify-center rounded-2xl bg-gradient-to-br from-[#fbbf24] to-[#f59e0b] px-5 text-[1.1em] font-extrabold text-[#1f1300]">
              3. 🎤 Hear SunoSafe&apos;s warning (Agora + Murf)
            </a>
          ) : <BigButton tone="quiet" disabled>3. Hear SunoSafe&apos;s warning</BigButton>}
        </li>
        <li>
          <BigButton tone="quiet" disabled={!callResult?.incident_id} onClick={() => callResult?.incident_id && onOpenIncident(callResult.incident_id)}>
            4. See the evidence and approve an action
          </BigButton>
        </li>
      </ol>
      <ErrorNote message={error} />
    </Card>
  );
}

// The SunoSafe phone number (a Vobiz number linked to the Agora inbound agent). Public: it is a phone number.
const SHIELD_NUMBER = process.env.NEXT_PUBLIC_SUNOSAFE_SHIELD_NUMBER ?? '';

function CallShieldCard({ settings }: { settings: Settings }) {
  const digits = SHIELD_NUMBER.replace(/[^\d+]/g, '');
  return (
    <Card className="border-2 border-[#1e3a8a] bg-gradient-to-br from-white to-[#eef2ff]">
      <h3 className="text-[1.25em] font-extrabold">🛡️ Call shield: SunoSafe answers suspicious calls {digits ? <Tag kind="real" /> : <Tag kind="setup" />}</h3>
      <p className="mt-1 text-[#4b5a56]">
        Calls you decline or don&apos;t answer go to your SunoSafe number instead of voicemail. SunoSafe&apos;s call
        assistant (Agora voice agent) answers, asks who is calling, never shares anything about you, and checks what the
        caller says with the same scam engine. If it is a scam, your phone tells you calmly what happened, and it is added
        to your evidence timeline, linked to any scam message from the same story.
      </p>
      <a href={talkUrl(settings, null, 'shield')}
        className="mt-3 flex min-h-[3.75em] w-full items-center justify-center rounded-2xl bg-[#1e3a8a] px-5 text-center text-[1.05em] font-extrabold text-white">
        🎤 Test it now: you play the caller
      </a>
      <p className="mt-1 text-[0.9em] text-[#4b5a56]">The test uses this browser instead of a phone line. Use only made-up details.</p>
      <details className="mt-3">
        <summary className="cursor-pointer font-bold">Set up call forwarding</summary>
        {digits ? (
          <ol className="mt-2 list-decimal space-y-1 pl-6">
            <li>Your SunoSafe number: <b>{SHIELD_NUMBER}</b></li>
            <li>On the phone, dial <code>**67*{digits}#</code> (when busy or declined) and <code>**61*{digits}#</code> (when not answered), then press call.</li>
            <li>Or on Samsung: Phone → ⋮ → Settings → Supplementary services → Call forwarding → Voice call.</li>
            <li>To switch it off: dial <code>##002#</code>.</li>
          </ol>
        ) : (
          <p className="mt-2">No SunoSafe number has been set up yet. It needs an Indian number from a telephony provider (Vobiz), linked to SunoSafe&apos;s Agora voice agent.</p>
        )}
        <p className="mt-2 text-[0.9em] text-[#4b5a56]">
          Limits: your operator may charge for forwarded calls and the codes can differ by operator. SunoSafe cannot listen to calls you
          answer yourself; it only handles calls that are forwarded to it.
        </p>
      </details>
    </Card>
  );
}

export function SafetyScreen({ settings, onOpenIncident }: { settings: Settings; onOpenIncident: (id: number) => void }) {
  const [description, setDescription] = useState('');
  const [number, setNumber] = useState('');
  const [asked, setAsked] = useState<string[]>([]);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [callVerdict, setCallVerdict] = useState<{ verdict: Verdict; incident_id: number | null; simulated: boolean } | null>(null);
  const [notifResult, setNotifResult] = useState<AnalyzeResult | null>(null);

  function shieldOn(): boolean {
    if (settings.shield) return true;
    setError('Shield is paused. Turn it on in Settings.');
    return false;
  }

  async function reportCall(body: { description: string; caller_number: string | null; asked_for: string[] }, simulated: boolean) {
    if (!shieldOn()) return;
    setBusy('call');
    setError('');
    setCallVerdict(null);
    try {
      const out = await api<{ verdict: Verdict; incident_id: number | null }>('calls/report', { method: 'POST', body });
      setCallVerdict({ ...out, simulated });
      if (out.verdict.label === 'danger') buzz(settings, [300, 120, 300]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }

  async function analyseNotification(text: string) {
    if (!shieldOn()) return;
    setBusy('notif');
    setError('');
    setNotifResult(null);
    try {
      const out = await api<AnalyzeResult>('messages/analyze', { method: 'POST', body: { text, source: 'notification' } });
      setNotifResult(out);
      if (out.verdict.label === 'danger') buzz(settings, [300, 120, 300]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Call and notification safety</h2>
      <InterventionDemo settings={settings} onOpenIncident={onOpenIncident} />
      <CallShieldCard settings={settings} />
      <Card>
        <h3 className="text-[1.2em] font-extrabold">Automatic protection on Android <Tag kind="real" /></h3>
        <p className="mt-1 text-[#4b5a56]">
          The SunoSafe Android app reads new WhatsApp and SMS notifications (after you allow it), checks unknown
          callers, and warns you aloud. If a number from a scam message calls you, it warns you while the phone rings.
          Set it up in Settings → Automatic scam warnings.
        </p>
      </Card>
      <ErrorNote message={error} />

      <Card>
        <h3 className="text-[1.2em] font-extrabold">Report a suspicious call <Tag kind="real" /></h3>
        <p className="mt-1 text-[#4b5a56]">SunoSafe cannot hear your phone calls. Tell it what happened and it will check for scam patterns and link it to earlier messages.</p>
        <form className="mt-3 space-y-3" onSubmit={(e) => { e.preventDefault(); void reportCall({ description, caller_number: number.trim() || null, asked_for: asked }, false); }}>
          <label htmlFor="call-what" className="block font-bold">What did the caller say?</label>
          <textarea id="call-what" rows={3} maxLength={2000} required value={description} onChange={(e) => setDescription(e.target.value)}
            className="w-full rounded-2xl border-2 border-[#9fb3ae] bg-white p-4" />
          <label htmlFor="call-number" className="block font-bold">Caller&apos;s number (optional)</label>
          <input id="call-number" inputMode="tel" maxLength={20} value={number} onChange={(e) => setNumber(e.target.value.replace(/[^\d+\s-]/g, ''))}
            className="h-14 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white px-4" />
          <fieldset>
            <legend className="font-bold">What did they ask for?</legend>
            <div className="mt-2 flex flex-wrap gap-2">
              {ASKED.map(([code, label]) => {
                const on = asked.includes(code);
                return (
                  <button key={code} type="button" aria-pressed={on}
                    onClick={() => setAsked(on ? asked.filter((a) => a !== code) : [...asked, code])}
                    className={`min-h-[3em] rounded-full border-2 px-4 font-bold ${on ? 'border-[#134e4a] bg-[#134e4a] text-white' : 'border-[#cfcabb] bg-white'}`}>
                    {label}
                  </button>
                );
              })}
            </div>
          </fieldset>
          <BigButton type="submit" disabled={busy !== ''}>{busy === 'call' ? 'Checking…' : 'Check this call'}</BigButton>
        </form>
      </Card>

      <Card className="border-[#fcd34d] bg-[#fffdf5]">
        <h3 className="text-[1.2em] font-extrabold">Practice with example calls <Tag kind="simulated" /></h3>
        <p className="mt-1 text-[#4b5a56]">These calls are made up. Tapping one sends the example to the real SunoSafe checker, so you can see how it responds.</p>
        <div className="mt-3 space-y-2">
          {CALL_SCENARIOS.map((s) => (
            <BigButton key={s.title} tone="quiet" disabled={busy !== ''}
              onClick={() => reportCall({ description: `[SIMULATED EXAMPLE] ${s.description}`, caller_number: null, asked_for: s.asked }, true)}>
              ▶ {s.title}
            </BigButton>
          ))}
        </div>
      </Card>

      {callVerdict && (
        <div className="space-y-3" aria-live="polite">
          {callVerdict.simulated && <p className="rounded-2xl bg-[#fef3c7] p-3 font-bold text-[#78350f]">Simulated call, real analysis:</p>}
          <VerdictCard verdict={callVerdict.verdict} />
          {callVerdict.incident_id && <BigButton onClick={() => onOpenIncident(callVerdict.incident_id!)}>See the recovery steps</BigButton>}
        </div>
      )}

      <Card>
        <h3 className="font-bold">Warn me before I answer unknown callers <Tag kind="planned" /></h3>
        <p className="mt-1 text-[#4b5a56]">Needs Android&apos;s call-screening permission, which only an installed Android app can hold. It shows the number only; no app can listen to normal phone calls.</p>
        <h3 className="mt-3 font-bold">Private warning during a SunoSafe internet call <Tag kind="planned" /></h3>
        <p className="mt-1 text-[#4b5a56]">A call hosted inside SunoSafe on Agora, where the assistant can warn only you.</p>
      </Card>

      <Card>
        <h3 className="text-[1.2em] font-extrabold">Check a notification you received <Tag kind="real" /></h3>
        <p className="mt-1 text-[#4b5a56]">Long-press the message in WhatsApp or Messages, tap <strong>Share</strong>, and choose <strong>SunoSafe</strong>. Or copy it and use the Check screen. SunoSafe only sees what you choose to share.</p>
      </Card>

      <Card className="border-[#fcd34d] bg-[#fffdf5]">
        <h3 className="text-[1.2em] font-extrabold">Automatic notification watching <Tag kind="simulated" /></h3>
        <p className="mt-1 text-[#4b5a56]">A web app cannot read your notifications. These are made-up notifications showing what the Android app would do, checked by the real SunoSafe engine.</p>
        <div className="mt-3 space-y-3">
          {NOTIFICATION_SCENARIOS.map((n) => (
            <div key={n.sender} className="rounded-2xl border border-[#d9d5c7] bg-white p-4">
              <p className="text-[0.85em] font-bold text-[#4b5a56]">{n.app} · {n.sender} · example</p>
              <p className="mt-1">{n.text}</p>
              <div className="mt-3">
                <BigButton tone="quiet" disabled={busy !== ''} onClick={() => analyseNotification(n.text)}>▶ Check this example</BigButton>
              </div>
            </div>
          ))}
        </div>
      </Card>

      {notifResult && (
        <div className="space-y-3" aria-live="polite">
          <p className="rounded-2xl bg-[#fef3c7] p-3 font-bold text-[#78350f]">Simulated notification, real analysis:</p>
          <VerdictCard verdict={notifResult.verdict} />
        </div>
      )}

      <Card>
        <h3 className="font-bold">Watch notifications automatically <Tag kind="planned" /></h3>
        <p className="mt-1 text-[#4b5a56]">Needs Android&apos;s notification-access permission, which you would switch on yourself in the Android app. Some apps hide message text from it.</p>
      </Card>
    </div>
  );
}

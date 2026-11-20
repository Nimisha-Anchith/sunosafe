'use client';

import { useCallback, useEffect, useState } from 'react';
import { type AnalyzeResult, type LinkReport, type Settings, type Verdict, api, buzz, defang, hostOf, talkUrl } from './api';
import { BigButton, Card, ConfirmSheet, ErrorNote, LinkFacts, Tag, VerdictCard, signalsList } from './ui';

function alertFor(settings: Settings, verdict: Verdict) {
  if (verdict.label === 'danger') buzz(settings, [300, 120, 300, 120, 300]);
  else if (verdict.label === 'caution') buzz(settings, [200]);
}

/** Block button with a confirmation step. Nothing is blocked without a clear yes. */
function BlockLink({ url, onBlocked }: { url: string; onBlocked?: () => void }) {
  const [asking, setAsking] = useState(false);
  const [state, setState] = useState<'idle' | 'busy' | 'done'>('idle');
  const [error, setError] = useState('');
  const site = hostOf(url) || 'this link';

  async function block() {
    setAsking(false);
    setState('busy');
    setError('');
    try {
      await api('blocklist', { method: 'POST', body: { url, confirm: true } });
      setState('done');
      onBlocked?.();
    } catch (e) {
      setState('idle');
      setError((e as Error).message);
    }
  }

  if (state === 'done') {
    return (
      <p role="status" className="rounded-2xl border-2 border-[#166534] bg-[#f0fdf4] p-4 text-[1.05em] font-bold text-[#14532d]">
        ✔️ Blocked. SunoSafe will refuse to open {site}.
      </p>
    );
  }
  return (
    <>
      <BigButton tone="danger" disabled={state === 'busy'} onClick={() => setAsking(true)}>
        🚫 {state === 'busy' ? 'Blocking…' : `Block ${site}`}
      </BigButton>
      <ErrorNote message={error} />
      {asking && (
        <ConfirmSheet
          title="Block this link?"
          body={`SunoSafe will refuse to open ${site} from now on. You can still see it in your incident list.`}
          confirmLabel="Yes, block it"
          onConfirm={block}
          onCancel={() => setAsking(false)}
        />
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// Check a message
// ---------------------------------------------------------------------------
// A made-up scam used by the "Example" button (clearly an example, real analysis).
const EXAMPLE_SCAM = "[EXAMPLE] Dear SBI customer, your account will be BLOCKED today. Update KYC at https://wrong.host.badssl.com/kyc and share the OTP sent to you. Call 9876543210.";

export function CheckScreen({
  settings,
  sharedText,
  sharedSource,
  onConsumedShared,
  onReportScam,
}: {
  settings: Settings;
  sharedText: string;
  sharedSource: 'share' | 'paste';
  onConsumedShared: () => void;
  onReportScam: (incidentId: number | null) => void;
}) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [voiceNote, setVoiceNote] = useState('');

  const analyse = useCallback(
    async (message: string, source: 'paste' | 'share') => {
      if (!settings.shield) {
        setError('Shield is paused. Turn it on in Settings to check messages.');
        return;
      }
      setBusy(true);
      setError('');
      setResult(null);
      try {
        const out = await api<AnalyzeResult>('messages/analyze', { method: 'POST', body: { text: message, source } });
        setResult(out);
        alertFor(settings, out.verdict);
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setBusy(false);
      }
    },
    [settings],
  );

  // A message shared from WhatsApp / Messages arrives here and is checked at once.
  useEffect(() => {
    if (sharedText) {
      setText(sharedText);
      onConsumedShared();
      void analyse(sharedText, sharedSource);
    }
  }, [sharedText, sharedSource, onConsumedShared, analyse]);

  async function pasteFromClipboard() {
    try {
      const clip = await navigator.clipboard.readText();
      if (clip) setText(clip);
      else setError('The clipboard is empty. Copy the message first.');
    } catch {
      setError('Paste was not allowed. Press and hold in the box and choose Paste.');
    }
  }

  async function askByVoice() {
    setVoiceNote('');
    try {
      await api('inbox', { method: 'POST', body: { text } });
      window.location.href = talkUrl(settings, result?.incident_id);
    } catch (e) {
      setVoiceNote((e as Error).message);
    }
  }

  const firstLink = result?.links[0];
  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Check a message</h2>
      <p className="text-[#4b5a56]">
        Bring the message here from WhatsApp or SMS, or let the SunoSafe Android app check it for you.
      </p>
      <Card>
        <h3 className="font-bold">Get the message</h3>
        <ol className="mt-2 list-decimal space-y-1 pl-6 text-[#4b5a56]">
          <li>Open the chat below and <strong>press and hold</strong> the message.</li>
          <li>Tap <strong>Copy</strong> (WhatsApp: the copy icon at the top).</li>
          <li>Come back here and tap <strong>Paste</strong>, then <strong>Check this message</strong>.</li>
        </ol>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {/* Android opens the app itself; other systems fall back to the normal link. */}
          <a href="intent://send#Intent;scheme=whatsapp;package=com.whatsapp;S.browser_fallback_url=https%3A%2F%2Fweb.whatsapp.com;end"
            className="btn-quiet flex min-h-[3.4em] items-center justify-center rounded-2xl font-bold">💬 Open WhatsApp</a>
          <a href="sms:" className="btn-quiet flex min-h-[3.4em] items-center justify-center rounded-2xl font-bold">✉️ Open Messages</a>
        </div>
        <p className="mt-3 text-[0.9em] text-[#4b5a56]">
          Faster with the SunoSafe Android app: press and hold the message → <strong>Share</strong> → <strong>SunoSafe</strong>, and it
          is checked and the answer is spoken at once. With <em>screen checking</em> switched on, the app also checks messages you
          simply open or scroll, without copying anything.
        </p>
      </Card>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void analyse(text, 'paste');
        }}
        className="space-y-3"
      >
        <label htmlFor="message" className="block font-bold">
          Message
        </label>
        <textarea
          id="message"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          maxLength={5000}
          required
          placeholder="Paste the message here"
          className="w-full rounded-2xl border-2 border-[#9fb3ae] bg-white p-4 text-[1em] focus:border-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/30"
        />
        <div className="grid grid-cols-3 gap-2">
          <BigButton tone="quiet" onClick={pasteFromClipboard}>📋 Paste</BigButton>
          <BigButton tone="quiet" onClick={() => { setText(''); setResult(null); setError(''); }}>Clear</BigButton>
          <BigButton tone="quiet" ariaLabel="Fill in an example scam message to try"
            onClick={() => { setResult(null); setError(''); setText(EXAMPLE_SCAM); }}>Example</BigButton>
        </div>
        <BigButton type="submit" disabled={busy || !text.trim()}>
          {busy ? 'Checking… this takes a few seconds' : '🔍 Check this message'}
        </BigButton>
      </form>
      <ErrorNote message={error} />

      {result && (
        <div className="space-y-4" aria-live="polite">
          <VerdictCard verdict={result.verdict} />
          {signalsList(result).length > 0 && (
            <Card>
              <h4 className="font-bold">Warning signs in the message</h4>
              <ul className="mt-2 list-disc space-y-1 pl-6">
                {signalsList(result).map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ul>
            </Card>
          )}
          {result.links.map((link) => (
            <LinkFacts key={link.url} link={link} />
          ))}
          {firstLink && result.verdict.label !== 'no_known_issues' && <BlockLink url={firstLink.url} />}
          <BigButton tone="primary" onClick={askByVoice}>🎤 Ask SunoSafe about it by voice</BigButton>
          {voiceNote && <ErrorNote message={voiceNote} />}
          <BigButton tone="amber" onClick={() => onReportScam(result.incident_id)}>
            🆘 I already clicked or shared details
          </BigButton>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Links: investigate, and the protected-open gate
// ---------------------------------------------------------------------------
type ProtectResult = { action: 'allow' | 'block' | 'warn'; reason: string };
type BlockEntry = { id: number; kind: string; value: string; created_at: string };

export function LinksScreen({ settings }: { settings: Settings }) {
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const [report, setReport] = useState<{ verdict: Verdict; link: LinkReport } | null>(null);
  const [gate, setGate] = useState<ProtectResult | null>(null);
  const [blocked, setBlocked] = useState<BlockEntry[]>([]);

  const loadBlocked = useCallback(() => {
    api<BlockEntry[]>('blocklist').then(setBlocked).catch(() => undefined);
  }, []);
  useEffect(loadBlocked, [loadBlocked]);

  function guardShield(): boolean {
    if (settings.shield) return true;
    setError('Shield is paused. Turn it on in Settings to check links.');
    return false;
  }

  async function investigate() {
    if (!guardShield()) return;
    setBusy('check');
    setError('');
    setReport(null);
    setGate(null);
    try {
      const out = await api<{ verdict: Verdict; link: LinkReport }>('links/check', { method: 'POST', body: { url } });
      setReport(out);
      alertFor(settings, out.verdict);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }

  async function openSafely() {
    if (!guardShield()) return;
    setBusy('open');
    setError('');
    setGate(null);
    try {
      const out = await api<ProtectResult>('protect/check', { method: 'POST', body: { url } });
      setGate(out);
      if (out.action === 'block') buzz(settings, [400, 150, 400]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy('');
    }
  }

  if (gate?.action === 'block') {
    return (
      <div role="alert" className="flex min-h-[70vh] flex-col justify-center rounded-3xl bg-[#7a271a] p-6 text-white">
        <p aria-hidden className="text-6xl">⛔</p>
        <h2 className="mt-3 text-[1.9em] font-extrabold">SunoSafe blocked this website</h2>
        <p className="mt-2 text-[1.15em]">{gate.reason}</p>
        <p className="mt-2 break-all font-mono text-[0.9em] opacity-90">{defang(url)}</p>
        <div className="mt-6">
          <BigButton tone="quiet" onClick={() => { setGate(null); setUrl(''); }}>Go back to safety</BigButton>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">Check or open a link</h2>
      <p className="text-[#4b5a56]">
        SunoSafe looks at where a link really goes, how old the website is and whether its security certificate is valid.
      </p>
      <label htmlFor="url" className="block font-bold">Link</label>
      <input
        id="url"
        value={url}
        onChange={(e) => { setUrl(e.target.value); setGate(null); }}
        inputMode="url"
        autoCapitalize="none"
        autoCorrect="off"
        maxLength={2048}
        placeholder="Paste the link here"
        className="h-16 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white px-4 focus:border-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/30"
      />
      <BigButton disabled={!url.trim() || busy !== ''} onClick={investigate}>
        {busy === 'check' ? 'Investigating…' : '🔍 Investigate this link'}
      </BigButton>
      <BigButton tone="quiet" disabled={!url.trim() || busy !== ''} onClick={openSafely}>
        {busy === 'open' ? 'Checking your block list…' : '🌐 Open through SunoSafe'}
      </BigButton>
      <ErrorNote message={error} />

      {gate && (
        <Card className="border-[#b45309]">
          <h3 className="text-[1.2em] font-extrabold">{gate.action === 'warn' ? 'This is not a website link' : 'Not on your block list'}</h3>
          <p className="mt-1">{gate.reason}</p>
          {gate.action === 'allow' && (
            <div className="mt-4 space-y-3">
              <BigButton onClick={investigate}>🔍 Investigate it first (recommended)</BigButton>
              <a
                href={/^https?:\/\//i.test(url) ? url : `http://${url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-[3.75em] w-full items-center justify-center rounded-2xl border border-[#cfcabb] bg-[#eceae0] px-5 text-[1.1em] font-bold"
              >
                Open it anyway
              </a>
            </div>
          )}
        </Card>
      )}

      {report && (
        <div className="space-y-4" aria-live="polite">
          <VerdictCard verdict={report.verdict} />
          <LinkFacts link={report.link} />
          {report.verdict.label !== 'no_known_issues' && <BlockLink url={report.link.url} onBlocked={loadBlocked} />}
        </div>
      )}

      <Card>
        <h3 className="text-[1.2em] font-extrabold">Your blocked websites</h3>
        {blocked.length === 0 ? (
          <p className="mt-1 text-[#4b5a56]">Nothing blocked yet.</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {blocked.slice(0, 20).map((b) => (
              <li key={b.id} className="break-all rounded-xl bg-[#f5f3ec] p-3 font-mono text-[0.85em]">
                {b.kind === 'domain' ? 'Whole site: ' : ''}{defang(b.value)}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <h3 className="font-bold">How link protection works today <Tag kind="real" /></h3>
        <p className="mt-1 text-[#4b5a56]">
          Links you open through SunoSafe are checked against your block list first. SunoSafe cannot see links you open in
          other apps.
        </p>
        <h3 className="mt-3 font-bold">Catch links from every app <Tag kind="planned" /></h3>
        <p className="mt-1 text-[#4b5a56]">
          The Android app will be able to register as a link handler, so links tapped in other apps pass through SunoSafe.
        </p>
      </Card>
    </div>
  );
}

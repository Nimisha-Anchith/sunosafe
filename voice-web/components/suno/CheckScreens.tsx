'use client';

import { useCallback, useEffect, useState } from 'react';
import { type AnalyzeResult, type LinkReport, type Settings, type Verdict, api, buzz, defang, hostOf, talkUrl } from './api';
import { useT } from './i18n';
import { BigButton, Card, ConfirmSheet, ErrorNote, LinkFacts, Tag, VerdictCard, signalsList } from './ui';

function alertFor(settings: Settings, verdict: Verdict) {
  if (verdict.label === 'danger') buzz(settings, [300, 120, 300, 120, 300]);
  else if (verdict.label === 'caution') buzz(settings, [200]);
}

/** Block button with a confirmation step. Nothing is blocked without a clear yes. */
function BlockLink({ url, onBlocked }: { url: string; onBlocked?: () => void }) {
  const t = useT();
  const [asking, setAsking] = useState(false);
  const [state, setState] = useState<'idle' | 'busy' | 'done'>('idle');
  const [error, setError] = useState('');
  const site = hostOf(url) || t('block.thisLink');

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
        ✔️ {t('block.done', { site })}
      </p>
    );
  }
  return (
    <>
      <BigButton tone="danger" disabled={state === 'busy'} onClick={() => setAsking(true)}>
        🚫 {state === 'busy' ? t('block.busy') : t('block.btn', { site })}
      </BigButton>
      <ErrorNote message={error} />
      {asking && (
        <ConfirmSheet
          title={t('block.title')}
          body={t('block.body', { site })}
          confirmLabel={t('block.yes')}
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
  const t = useT();
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [voiceNote, setVoiceNote] = useState('');

  const analyse = useCallback(
    async (message: string, source: 'paste' | 'share') => {
      if (!settings.shield) {
        setError(t('check.paused'));
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
    [settings, t],
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
      else setError(t('check.clipEmpty'));
    } catch {
      setError(t('check.pasteDenied'));
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
      <h2 className="text-[1.6em] font-extrabold">{t('home.checkMessage')}</h2>
      <p className="text-[#4b5a56]">{t('check.intro')}</p>
      <Card>
        <h3 className="font-bold">{t('check.get')}</h3>
        <ol className="mt-2 list-decimal space-y-1 pl-6 text-[#4b5a56]">
          <li>{t('check.step1')}</li>
          <li>{t('check.step2')}</li>
          <li>{t('check.step3')}</li>
        </ol>
        <div className="mt-3 grid grid-cols-2 gap-3">
          {/* Android opens the app itself; other systems fall back to the normal link. */}
          <a href="intent://send#Intent;scheme=whatsapp;package=com.whatsapp;S.browser_fallback_url=https%3A%2F%2Fweb.whatsapp.com;end"
            className="btn-quiet flex min-h-[3.4em] items-center justify-center rounded-2xl font-bold">💬 {t('check.openWa')}</a>
          <a href="sms:" className="btn-quiet flex min-h-[3.4em] items-center justify-center rounded-2xl font-bold">✉️ {t('check.openSms')}</a>
        </div>
        <p className="mt-3 text-[0.9em] text-[#4b5a56]">{t('check.faster')}</p>
      </Card>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void analyse(text, 'paste');
        }}
        className="space-y-3"
      >
        <label htmlFor="message" className="block font-bold">
          {t('check.label')}
        </label>
        <textarea
          id="message"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={6}
          maxLength={5000}
          required
          placeholder={t('check.placeholder')}
          className="w-full rounded-2xl border-2 border-[#9fb3ae] bg-white p-4 text-[1em] focus:border-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/30"
        />
        <div className="grid grid-cols-3 gap-2">
          <BigButton tone="quiet" onClick={pasteFromClipboard}>📋 {t('check.paste')}</BigButton>
          <BigButton tone="quiet" onClick={() => { setText(''); setResult(null); setError(''); }}>{t('check.clear')}</BigButton>
          <BigButton tone="quiet" ariaLabel={t('check.exampleAria')}
            onClick={() => { setResult(null); setError(''); setText(EXAMPLE_SCAM); }}>{t('check.example')}</BigButton>
        </div>
        <BigButton type="submit" disabled={busy || !text.trim()}>
          {busy ? t('check.busy') : `🔍 ${t('check.submit')}`}
        </BigButton>
      </form>
      <ErrorNote message={error} />

      {result && (
        <div className="space-y-4" aria-live="polite">
          <VerdictCard verdict={result.verdict} />
          {signalsList(result).length > 0 && (
            <Card>
              <h4 className="font-bold">{t('check.signs')}</h4>
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
          <BigButton tone="primary" onClick={askByVoice}>🎤 {t('check.askVoice')}</BigButton>
          {voiceNote && <ErrorNote message={voiceNote} />}
          <BigButton tone="amber" onClick={() => onReportScam(result.incident_id)}>
            🆘 {t('check.clicked')}
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
  const t = useT();
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
    setError(t('links.paused'));
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
        <h2 className="mt-3 text-[1.9em] font-extrabold">{t('links.blockedTitle')}</h2>
        <p className="mt-2 text-[1.15em]">{gate.reason}</p>
        <p className="mt-2 break-all font-mono text-[0.9em] opacity-90">{defang(url)}</p>
        <div className="mt-6">
          <BigButton tone="quiet" onClick={() => { setGate(null); setUrl(''); }}>{t('links.goBack')}</BigButton>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h2 className="text-[1.6em] font-extrabold">{t('links.title')}</h2>
      <p className="text-[#4b5a56]">{t('links.intro')}</p>
      <label htmlFor="url" className="block font-bold">{t('links.label')}</label>
      <input
        id="url"
        value={url}
        onChange={(e) => { setUrl(e.target.value); setGate(null); }}
        inputMode="url"
        autoCapitalize="none"
        autoCorrect="off"
        maxLength={2048}
        placeholder={t('links.placeholder')}
        className="h-16 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white px-4 focus:border-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/30"
      />
      <BigButton disabled={!url.trim() || busy !== ''} onClick={investigate}>
        {busy === 'check' ? t('links.investigating') : `🔍 ${t('links.investigate')}`}
      </BigButton>
      <BigButton tone="quiet" disabled={!url.trim() || busy !== ''} onClick={openSafely}>
        {busy === 'open' ? t('links.opening') : `🌐 ${t('links.open')}`}
      </BigButton>
      <ErrorNote message={error} />

      {gate && (
        <Card className="border-[#b45309]">
          <h3 className="text-[1.2em] font-extrabold">{gate.action === 'warn' ? t('links.notLink') : t('links.notBlocked')}</h3>
          <p className="mt-1">{gate.reason}</p>
          {gate.action === 'allow' && (
            <div className="mt-4 space-y-3">
              <BigButton onClick={investigate}>🔍 {t('links.investigateFirst')}</BigButton>
              <a
                href={/^https?:\/\//i.test(url) ? url : `http://${url}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex min-h-[3.75em] w-full items-center justify-center rounded-2xl border border-[#cfcabb] bg-[#eceae0] px-5 text-[1.1em] font-bold"
              >
                {t('links.openAnyway')}
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
        <h3 className="text-[1.2em] font-extrabold">{t('links.blockedList')}</h3>
        {blocked.length === 0 ? (
          <p className="mt-1 text-[#4b5a56]">{t('links.none')}</p>
        ) : (
          <ul className="mt-2 space-y-2">
            {blocked.slice(0, 20).map((b) => (
              <li key={b.id} className="break-all rounded-xl bg-[#f5f3ec] p-3 font-mono text-[0.85em]">
                {b.kind === 'domain' ? t('links.wholeSite') : ''}{defang(b.value)}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card>
        <h3 className="font-bold">{t('links.howTitle')} <Tag kind="real" /></h3>
        <p className="mt-1 text-[#4b5a56]">{t('links.howText')}</p>
        <h3 className="mt-3 font-bold">{t('links.planTitle')} <Tag kind="planned" /></h3>
        <p className="mt-1 text-[#4b5a56]">{t('links.planText')}</p>
      </Card>
    </div>
  );
}

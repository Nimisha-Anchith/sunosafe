import LandingPage from '@/components/LandingPage';
import type { VoiceContext } from '@/types/conversation';

/**
 * Voice screen. This is the working Agora Conversational AI client from the
 * official quickstart, unchanged underneath: RTC audio, RTM transcript, and an
 * agent whose brain is the SunoSafe gateway and whose voice is Murf Falcon.
 *
 * Optional address parameters (validated here and again on the server):
 *   ?incident=12  the agent starts already briefed on that incident
 *   ?mode=drill   scam-call practice
 *   ?mode=shield  test the call assistant: you play the caller
 *   ?lang=hi      preferred language (en, hi, ml, kn, ta)
 */
const LANGS = ['en', 'hi', 'ml', 'kn', 'ta'] as const;

export default async function TalkPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const one = (v: string | string[] | undefined) => (Array.isArray(v) ? v[0] : v) ?? '';
  const incident = Number(one(params.incident));
  const lang = one(params.lang);
  const context: VoiceContext = {
    ...(Number.isInteger(incident) && incident > 0 && incident < 1e9 ? { incident_id: incident } : {}),
    mode: one(params.mode) === 'drill' ? 'drill' : one(params.mode) === 'shield' ? 'shield' : 'guard',
    lang: (LANGS as readonly string[]).includes(lang) ? (lang as VoiceContext['lang']) : 'en',
  };
  return (
    <>
      {/* A full page load (not a client-side route change) on purpose: it ends the
          call and releases the microphone for certain when the user leaves. */}
      {/* eslint-disable-next-line @next/next/no-html-link-for-pages */}
      <a
        href="/"
        className="fixed left-3 top-3 z-50 flex min-h-12 items-center rounded-full bg-white/95 px-5 text-base font-bold text-[#134e4a] shadow focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40"
      >
        ← Back to SunoSafe
      </a>
      <LandingPage context={context} />
    </>
  );
}

'use client';

/**
 * Android Share Target. When the installed app is chosen from another app's
 * Share menu (WhatsApp, Messages, a browser), Android opens
 * /share?title=...&text=...&url=... . We park the shared text for the Check
 * screen and remove it from the address bar straight away, so the message
 * does not linger in the URL or browser history.
 */
import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { SHARED_KEY } from '@/components/suno/SunoApp';

function Receive() {
  const params = useSearchParams();
  useEffect(() => {
    const parts = [params.get('title'), params.get('text'), params.get('url')].filter(Boolean);
    const text = Array.from(new Set(parts)).join('\n').slice(0, 5000);
    try {
      if (text) sessionStorage.setItem(SHARED_KEY, text);
    } catch {
      /* storage unavailable: the user can still paste */
    }
    window.location.replace('/');
  }, [params]);
  return (
    <main className="flex min-h-dvh items-center justify-center bg-[#f5f3ec] p-6 text-xl font-bold text-[#14201d]">
      Opening SunoSafe…
    </main>
  );
}

export default function SharePage() {
  return (
    <Suspense>
      <Receive />
    </Suspense>
  );
}

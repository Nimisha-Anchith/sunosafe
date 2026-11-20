'use client';

import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';

function LoginForm() {
  const params = useSearchParams();
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin }),
      });
      if (response.ok) {
        // Only ever go to a path inside this app.
        const next = params.get('next') ?? '/';
        window.location.replace(next.startsWith('/') && !next.startsWith('//') ? next : '/');
        return;
      }
      const data = await response.json().catch(() => ({}));
      setError(data.error ?? 'Could not unlock. Please try again.');
      setPin('');
    } catch {
      setError('No connection. Please check your internet and try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="suno flex min-h-dvh flex-col items-center justify-center bg-[#f5f3ec] px-6 text-[#14201d]">
      <div className="w-full max-w-sm">
        <div aria-hidden className="mx-auto mb-5 flex h-20 w-20 items-center justify-center rounded-3xl bg-[#134e4a] text-4xl">
          🛡️
        </div>
        <h1 className="text-center text-3xl font-bold">SunoSafe</h1>
        <p className="mt-2 text-center text-lg text-[#4b5a56]">Enter your PIN to open the app.</p>
        <form onSubmit={submit} className="mt-8">
          <label htmlFor="pin" className="block text-lg font-semibold">
            PIN
          </label>
          <input
            id="pin"
            type="password"
            inputMode="numeric"
            autoComplete="one-time-code"
            autoFocus
            required
            minLength={6}
            maxLength={12}
            value={pin}
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            aria-describedby={error ? 'pin-error' : undefined}
            className="mt-2 h-16 w-full rounded-2xl border-2 border-[#9fb3ae] bg-white px-5 text-center text-3xl tracking-[0.4em] focus:border-[#134e4a] focus:outline-none focus:ring-4 focus:ring-[#134e4a]/30"
          />
          {error && (
            <p id="pin-error" role="alert" className="mt-3 text-lg font-semibold text-[#b42318]">
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={busy || pin.length < 6}
            className="mt-6 h-16 w-full rounded-2xl bg-[#134e4a] text-xl font-bold text-white disabled:opacity-50 focus:outline-none focus:ring-4 focus:ring-[#134e4a]/40"
          >
            {busy ? 'Opening…' : 'Open SunoSafe'}
          </button>
        </form>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

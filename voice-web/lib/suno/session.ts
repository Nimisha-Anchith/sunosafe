/**
 * SunoSafe app lock: a signed session cookie.
 *
 * After the correct PIN is entered, the server gives the browser a cookie of
 * the form "<expiry>.<signature>". The signature is an HMAC-SHA256 of the
 * expiry time made with a secret only the server knows, so the browser cannot
 * forge or extend it. The cookie is HttpOnly (page scripts cannot read it).
 *
 * Uses the Web Crypto API so the same code runs in Next.js Proxy and in routes.
 */

export const SESSION_COOKIE = 'suno_session';
export const SESSION_HOURS = 12;

const encoder = new TextEncoder();

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

async function hmac(secret: string, data: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  return toHex(await crypto.subtle.sign('HMAC', key, encoder.encode(data)));
}

/** Compare two strings without leaking where they differ through timing. */
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

export async function sha256Hex(text: string): Promise<string> {
  return toHex(await crypto.subtle.digest('SHA-256', encoder.encode(text)));
}

export async function createSession(secret: string, now = Date.now()): Promise<string> {
  const expiry = String(now + SESSION_HOURS * 60 * 60 * 1000);
  return `${expiry}.${await hmac(secret, expiry)}`;
}

export async function isValidSession(
  value: string | undefined,
  secret: string,
  now = Date.now(),
): Promise<boolean> {
  if (!value) return false;
  const [expiry, signature] = value.split('.');
  if (!expiry || !signature || !/^\d{10,16}$/.test(expiry)) return false;
  if (Number(expiry) < now) return false;
  return safeEqual(signature, await hmac(secret, expiry));
}

/** Server settings for the lock. Both must be set or the app refuses to open. */
export function lockConfig(): { pin: string; secret: string } | null {
  const pin = process.env.SUNOSAFE_APP_PIN;
  const secret = process.env.SUNOSAFE_SESSION_SECRET;
  if (!pin || !secret || pin.length < 6 || secret.length < 32) return null;
  return { pin, secret };
}

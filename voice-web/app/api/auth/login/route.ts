/**
 * PIN login. Wrong attempts are limited per address and overall, so a 6-digit
 * PIN cannot be guessed by trying every combination.
 */
import { NextRequest, NextResponse } from 'next/server';
import {
  SESSION_COOKIE,
  SESSION_HOURS,
  createSession,
  lockConfig,
  safeEqual,
  sha256Hex,
} from '@/lib/suno/session';

const PER_ADDRESS_LIMIT = 5; // wrong PINs per address...
const GLOBAL_LIMIT = 30; // ...and in total...
const WINDOW_MS = 10 * 60 * 1000; // ...per 10 minutes

const failures = new Map<string, number[]>();
let globalFailures: number[] = [];

function recent(times: number[], now: number): number[] {
  return times.filter((t) => now - t < WINDOW_MS);
}

function clientAddress(request: NextRequest): string {
  return (
    request.headers.get('cf-connecting-ip') ??
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ??
    'local'
  );
}

export async function POST(request: NextRequest) {
  const lock = lockConfig();
  if (!lock) return NextResponse.json({ error: 'Lock not configured.' }, { status: 503 });

  const now = Date.now();
  const address = clientAddress(request);
  globalFailures = recent(globalFailures, now);
  const mine = recent(failures.get(address) ?? [], now);
  if (mine.length >= PER_ADDRESS_LIMIT || globalFailures.length >= GLOBAL_LIMIT) {
    return NextResponse.json(
      { error: 'Too many wrong attempts. Please wait 10 minutes.' },
      { status: 429 },
    );
  }

  let pin = '';
  try {
    const body = await request.json();
    pin = typeof body?.pin === 'string' ? body.pin.slice(0, 32) : '';
  } catch {
    return NextResponse.json({ error: 'Bad request.' }, { status: 400 });
  }

  // Compare fixed-length hashes so timing reveals nothing about the PIN.
  const matches = safeEqual(await sha256Hex(pin), await sha256Hex(lock.pin));
  if (!matches) {
    mine.push(now);
    failures.set(address, mine);
    globalFailures.push(now);
    if (failures.size > 500) {
      for (const [key, times] of failures) if (recent(times, now).length === 0) failures.delete(key);
    }
    return NextResponse.json({ error: 'Wrong PIN.' }, { status: 401 });
  }

  failures.delete(address);
  const response = NextResponse.json({ ok: true });
  response.cookies.set(SESSION_COOKIE, await createSession(lock.secret), {
    httpOnly: true, // page scripts cannot read it
    secure: true, // only sent over HTTPS (browsers also allow localhost)
    sameSite: 'lax', // sent when the phone opens the app from a share, not on cross-site POSTs
    path: '/',
    maxAge: SESSION_HOURS * 60 * 60,
  });
  return response;
}

/**
 * Gatekeeper for the whole web app (Next.js "Proxy", formerly Middleware).
 *
 * Runs before every page and API route:
 *   1. If the app lock is not configured, nothing is served (fail closed).
 *   2. A few public paths are allowed: the login page, the login API, and the
 *      files a phone needs before login to install the app (manifest, icons).
 *   3. Everything else needs a valid session cookie. Pages redirect to /login;
 *      API routes answer 401.
 *   4. Requests that change data must come from our own pages (Origin check),
 *      which stops other websites from sending requests on the user's behalf.
 */
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { SESSION_COOKIE, isValidSession, lockConfig } from '@/lib/suno/session';

const PUBLIC_PATHS = new Set([
  '/login',
  '/api/auth/login',
  '/manifest.webmanifest',
  '/sw.js',
  '/suno-192.png',
  '/suno-512.png',
  '/suno-maskable-512.png',
  '/favicon.ico',
]);

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

function sameOrigin(request: NextRequest): boolean {
  const origin = request.headers.get('origin');
  if (!origin) return false;
  const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host');
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}

export async function proxy(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const isApi = pathname.startsWith('/api/');

  const lock = lockConfig();
  if (!lock) {
    return new NextResponse('SunoSafe app lock is not configured on the server.', { status: 503 });
  }

  if (!SAFE_METHODS.has(request.method) && !sameOrigin(request)) {
    return NextResponse.json({ error: 'Cross-site request refused.' }, { status: 403 });
  }

  if (PUBLIC_PATHS.has(pathname)) return NextResponse.next();

  const ok = await isValidSession(request.cookies.get(SESSION_COOKIE)?.value, lock.secret);
  if (ok) return NextResponse.next();

  if (isApi) return NextResponse.json({ error: 'Please unlock SunoSafe first.' }, { status: 401 });

  const login = request.nextUrl.clone();
  login.pathname = '/login';
  // Remember where the user was going (for example a message shared from WhatsApp).
  login.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(login);
}

export const config = {
  // Everything except Next.js build assets.
  matcher: ['/((?!_next/).*)'],
};

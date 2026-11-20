/**
 * Bridge from the web app to the private SunoSafe backend.
 *
 *   phone ──HTTPS──► this web app (PIN-locked) ──127.0.0.1──► backend (port 8000, never public)
 *
 * The phone never talks to the backend directly. Only the request shapes
 * listed below are forwarded; anything else gets 404. The Guardian page,
 * raw event log and other backend routes are not reachable through here.
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND = (process.env.SUNOSAFE_BACKEND_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');
const MAX_BODY_BYTES = 20 * 1024;

type Rule = { method: string; pattern: RegExp };

const ALLOWED: Rule[] = [
  { method: 'POST', pattern: /^messages\/analyze$/ },
  { method: 'POST', pattern: /^links\/check$/ },
  { method: 'POST', pattern: /^protect\/check$/ },
  { method: 'POST', pattern: /^calls\/report$/ },
  { method: 'POST', pattern: /^incidents\/report-scam$/ },
  { method: 'POST', pattern: /^blocklist$/ },
  { method: 'GET', pattern: /^blocklist$/ },
  { method: 'POST', pattern: /^inbox$/ },
  { method: 'GET', pattern: /^incidents$/ },
  { method: 'GET', pattern: /^dashboard$/ },
  { method: 'GET', pattern: /^incidents\/\d{1,9}$/ },
  { method: 'GET', pattern: /^incidents\/\d{1,9}\/summary$/ },
  { method: 'PATCH', pattern: /^incidents\/\d{1,9}\/steps\/[a-z_]{1,40}$/ },
];

async function forward(request: NextRequest, segments: string[]) {
  const path = segments.join('/');
  if (!ALLOWED.some((rule) => rule.method === request.method && rule.pattern.test(path))) {
    return NextResponse.json({ error: 'Not found.' }, { status: 404 });
  }

  let body: string | undefined;
  if (request.method !== 'GET') {
    body = await request.text();
    if (body.length > MAX_BODY_BYTES) {
      return NextResponse.json({ error: 'Request too large.' }, { status: 413 });
    }
    try {
      const parsed = JSON.parse(body || '{}');
      // Blocking from the app is always recorded as approved in the app; the
      // screen shows a confirmation dialog before this request is sent.
      if (path === 'blocklist') parsed.approved_via = 'app';
      if (path === 'messages/analyze' && !['paste', 'share', 'notification'].includes(parsed.source)) {
        parsed.source = 'paste';
      }
      body = JSON.stringify(parsed);
    } catch {
      return NextResponse.json({ error: 'Bad request.' }, { status: 400 });
    }
  }

  try {
    // Only our own headers are sent: no cookies, no forwarding headers.
    // Only one query parameter is ever forwarded: the dashboard's day range, as a validated number.
    const days = Number(request.nextUrl.searchParams.get('days'));
    const query = path === 'dashboard' && Number.isInteger(days) && days >= 1 && days <= 30 ? `?days=${days}` : '';
    const upstream = await fetch(`${BACKEND}/api/${path}${query}`, {
      method: request.method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body,
      cache: 'no-store',
      signal: AbortSignal.timeout(30_000),
    });
    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        'Content-Type': upstream.headers.get('content-type') ?? 'application/json',
        'Cache-Control': 'no-store',
      },
    });
  } catch {
    return NextResponse.json(
      { error: 'SunoSafe could not reach its security service. Please try again.' },
      { status: 502 },
    );
  }
}

type Context = { params: Promise<{ path: string[] }> };

export async function GET(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}
export async function POST(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}
export async function PATCH(request: NextRequest, context: Context) {
  return forward(request, (await context.params).path);
}

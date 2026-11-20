/**
 * Android companion helpers, available only inside the PIN-locked app.
 *
 *   GET /api/companion/pair  -> a one-tap pairing link for the companion app
 *   GET /api/companion/apk   -> the companion's install file
 *
 * The pairing link carries the device token, so it is only ever handed to the
 * signed-in owner over HTTPS, and the companion asks for confirmation before
 * accepting it.
 */
import { createReadStream, statSync } from 'node:fs';
import { Readable } from 'node:stream';
import { NextRequest, NextResponse } from 'next/server';

function gatewayBase(): string | null {
  const llm = process.env.NEXT_SUNOSAFE_LLM_URL;
  if (!llm) return null;
  try {
    return new URL(llm).origin;
  } catch {
    return null;
  }
}

type Context = { params: Promise<{ action: string }> };

export async function GET(request: NextRequest, context: Context) {
  const { action } = await context.params;

  if (action === 'pair') {
    const token = process.env.SUNOSAFE_DEVICE_TOKEN;
    const gateway = gatewayBase();
    const host = request.headers.get('x-forwarded-host') ?? request.headers.get('host');
    if (!token || !gateway || !host) {
      return NextResponse.json({ error: 'The Android companion is not set up on the server.' }, { status: 503 });
    }
    const link =
      `sunosafe://pair?g=${encodeURIComponent(gateway)}` +
      `&t=${encodeURIComponent(token)}&a=${encodeURIComponent(`https://${host}`)}`;
    return NextResponse.json({ link }, { headers: { 'Cache-Control': 'no-store' } });
  }

  if (action === 'apk') {
    const path = process.env.SUNOSAFE_APK_PATH;
    try {
      if (!path) throw new Error('not configured');
      const size = statSync(path).size;
      const stream = Readable.toWeb(createReadStream(path)) as ReadableStream;
      return new NextResponse(stream, {
        headers: {
          'Content-Type': 'application/vnd.android.package-archive',
          'Content-Disposition': 'attachment; filename="SunoSafe-companion.apk"',
          'Content-Length': String(size),
          'Cache-Control': 'no-store',
        },
      });
    } catch {
      return NextResponse.json({ error: 'The Android app file is not available yet.' }, { status: 404 });
    }
  }

  return NextResponse.json({ error: 'Not found.' }, { status: 404 });
}

/**
 * Where the SunoSafe backend is, and how this server proves who it is.
 *
 * Laptop: the private API listens on 127.0.0.1:8000 and only accepts local requests.
 * Hosted (Render): the API is on the internet, so every call carries
 * `Authorization: Bearer <SUNOSAFE_BACKEND_TOKEN>` (= the backend's API_TOKEN).
 * This runs on the server only; the token never reaches the browser.
 */
export const BACKEND = (process.env.SUNOSAFE_BACKEND_URL ?? 'http://127.0.0.1:8000').replace(/\/$/, '');

export function backendHeaders(json = false): Record<string, string> {
  const headers: Record<string, string> = {};
  if (json) headers['Content-Type'] = 'application/json';
  const token = process.env.SUNOSAFE_BACKEND_TOKEN;
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

/** Base address of the public gateway, e.g. https://x.onrender.com/gw (or a tunnel on the laptop). */
export function gatewayBase(): string | null {
  const llm = process.env.NEXT_SUNOSAFE_LLM_URL;
  if (!llm) return null;
  try {
    const url = new URL(llm);
    return url.origin + url.pathname.replace(/\/llm\/chat\/completions\/?$/, '').replace(/\/$/, '');
  } catch {
    return null;
  }
}

/** Small helpers shared by the SunoSafe screens. */

export type Reason = { rule: string; level: string; text: string; evidence?: string[] };
export type Verdict = {
  level: 'info' | 'low' | 'medium' | 'high' | 'critical';
  label: 'danger' | 'caution' | 'no_known_issues';
  confidence: string;
  reasons: Reason[];
  uncertainties: string[];
  summary: string;
};
export type LinkReport = {
  url: string;
  final_url: string | null;
  hops: string[];
  findings: { tool: string; code: string; detail: string }[];
  tool_runs: { tool: string; status: string }[];
};
export type Signal = { code: string; category: string; detail: string };
export type AnalyzeResult = {
  incident_id: number | null;
  verdict: Verdict;
  signals: Signal[];
  links: LinkReport[];
};
export type Step = { code: string; title: string; detail: string; status: string; needs_approval: number };
export type SecurityEvent = {
  id: number;
  ts: string;
  type: string;
  source: string;
  level: string | null;
  summary: string;
  data: Record<string, unknown>;
};
export type Incident = {
  events?: SecurityEvent[];
  id: number;
  title: string;
  severity: Verdict['level'];
  status: string;
  kind: string;
  created_at: string;
  updated_at: string;
  rationale: { text?: string; rule?: string }[];
  steps?: Step[];
};

export class ApiError extends Error {}

export async function api<T>(path: string, init?: { method?: string; body?: unknown }): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/suno/${path}`, {
      method: init?.method ?? 'GET',
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
      body: init?.body ? JSON.stringify(init.body) : undefined,
    });
  } catch {
    throw new ApiError('No connection. Please check your internet and try again.');
  }
  if (response.status === 401) {
    window.location.href = '/login';
    throw new ApiError('Please unlock SunoSafe again.');
  }
  const isJson = (response.headers.get('content-type') ?? '').includes('json');
  if (!response.ok) {
    const data = isJson ? await response.json().catch(() => ({})) : {};
    const detail = typeof data.detail === 'string' ? data.detail : data.error;
    if (response.status === 429) throw new ApiError('Too many checks just now. Please wait a minute.');
    throw new ApiError(detail || 'Something went wrong. Please try again.');
  }
  return (isJson ? response.json() : response.text()) as Promise<T>;
}

/** Show a link so it cannot be tapped by accident: https://a.b -> hxxps://a[.]b */
export function defang(url: string): string {
  return url.replace(/^http/, 'hxxp').replace(/\./g, '[.]');
}

export function hostOf(url: string | null | undefined): string {
  try {
    return new URL(url ?? '').hostname;
  } catch {
    return '';
  }
}

export type Lang = 'en' | 'hi' | 'ml' | 'kn' | 'ta';
export const LANG_NAMES: Record<Lang, string> = { en: 'English', hi: 'हिंदी', ml: 'മലയാളം', kn: 'ಕನ್ನಡ', ta: 'தமிழ்' };
export type Settings = { shield: boolean; vibrate: boolean; textSize: 'normal' | 'large' | 'xlarge'; lang: Lang };
export const DEFAULT_SETTINGS: Settings = { shield: true, vibrate: true, textSize: 'large', lang: 'en' };

/** Address of the voice agent, optionally briefed on an incident. */
export function talkUrl(settings: Settings, incidentId?: number | null, mode?: 'drill' | 'shield'): string {
  const q = new URLSearchParams({ lang: settings.lang });
  if (incidentId) q.set('incident', String(incidentId));
  if (mode) q.set('mode', mode);
  return `/talk?${q.toString()}`;
}
const SETTINGS_KEY = 'sunosafe-settings';

export function loadSettings(): Settings {
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(localStorage.getItem(SETTINGS_KEY) ?? '{}') };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function saveSettings(settings: Settings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    /* private mode: settings simply do not persist */
  }
}

export function buzz(settings: Settings, pattern: number[]): void {
  if (settings.vibrate && typeof navigator !== 'undefined' && 'vibrate' in navigator) {
    navigator.vibrate(pattern);
  }
}

/** Line icons for SunoSafe (24px grid, currentColor). Decorative: always aria-hidden. */
import type { ReactNode } from 'react';

function Svg({ children, size = 24, className = '' }: { children: ReactNode; size?: number; className?: string }) {
  return (
    <svg aria-hidden width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" className={`shrink-0 ${className}`}>
      {children}
    </svg>
  );
}

type P = { size?: number; className?: string };

export const ShieldPulse = (p: P) => (
  <Svg {...p}><path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6z" /><path d="M7.5 12h2l1.2-2.5 2 5 1.3-2.5h2.5" /></Svg>
);
export const Wave = (p: P) => (
  <Svg {...p}><path d="M3 12h1M6 9v6M9 6v12M12 9v6M15 4v16M18 8v8M21 12h-1" /></Svg>
);
export const Phone = (p: P) => (
  <Svg {...p}><path d="M5 4h3l1.5 4-2 1.2a11 11 0 005.3 5.3l1.2-2L18 14v3a2 2 0 01-2 2A14 14 0 013 6a2 2 0 012-2z" /></Svg>
);
export const PhoneOff = (p: P) => (
  <Svg {...p}><path d="M3.5 13.5c4.6-4 12.4-4 17 0l-1.8 2.3-3.2-1.3v-2a12 12 0 00-7 0v2l-3.2 1.3z" /></Svg>
);
export const Layers = (p: P) => (
  <Svg {...p}><path d="M12 3l9 5-9 5-9-5z" /><path d="M3 13l9 5 9-5" /></Svg>
);
export const Chart = (p: P) => (
  <Svg {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></Svg>
);
export const Gear = (p: P) => (
  <Svg {...p}><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 00.3 1.8l.1.1a2 2 0 11-2.8 2.8l-.1-.1a1.7 1.7 0 00-1.8-.3 1.7 1.7 0 00-1 1.5V21a2 2 0 11-4 0v-.1a1.7 1.7 0 00-1.1-1.5 1.7 1.7 0 00-1.8.3l-.1.1a2 2 0 11-2.8-2.8l.1-.1a1.7 1.7 0 00.3-1.8 1.7 1.7 0 00-1.5-1H3a2 2 0 110-4h.1a1.7 1.7 0 001.5-1.1 1.7 1.7 0 00-.3-1.8l-.1-.1a2 2 0 112.8-2.8l.1.1a1.7 1.7 0 001.8.3H9a1.7 1.7 0 001-1.5V3a2 2 0 114 0v.1a1.7 1.7 0 001 1.5 1.7 1.7 0 001.8-.3l.1-.1a2 2 0 112.8 2.8l-.1.1a1.7 1.7 0 00-.3 1.8V9a1.7 1.7 0 001.5 1H21a2 2 0 110 4h-.1a1.7 1.7 0 00-1.5 1z" /></Svg>
);
export const Home = (p: P) => (
  <Svg {...p}><path d="M3 11l9-7 9 7v9a1 1 0 01-1 1h-5v-6H9v6H4a1 1 0 01-1-1z" /></Svg>
);
export const Activity = (p: P) => (
  <Svg {...p}><rect x="4" y="4" width="16" height="16" rx="3" /><path d="M8 12h2l1.5-3 2 6 1.5-3h1" /></Svg>
);
export const Report = (p: P) => (
  <Svg {...p}><path d="M14 3H6a1 1 0 00-1 1v16a1 1 0 001 1h12a1 1 0 001-1V8z" /><path d="M14 3v5h5M9 17v-3M12 17v-6M15 17v-2" /></Svg>
);
export const User = (p: P) => (
  <Svg {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0116 0" /></Svg>
);
export const Alert = (p: P) => (
  <Svg {...p}><path d="M12 3l10 18H2z" /><path d="M12 10v4M12 18h.01" /></Svg>
);
export const Check = (p: P) => (
  <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M8 12l3 3 5-6" /></Svg>
);
export const Clock = (p: P) => (
  <Svg {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Svg>
);
export const Search = (p: P) => (
  <Svg {...p}><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></Svg>
);
export const Mic = (p: P) => (
  <Svg {...p}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" /></Svg>
);
export const Message = (p: P) => (
  <Svg {...p}><path d="M4 5h16v11H8l-4 4z" /></Svg>
);
export const Link = (p: P) => (
  <Svg {...p}><path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1" /><path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1" /></Svg>
);
export const Siren = (p: P) => (
  <Svg {...p}><path d="M6 18v-5a6 6 0 0112 0v5M4 18h16v3H4zM12 3v2M4.2 6.2l1.4 1.4M19.8 6.2l-1.4 1.4" /></Svg>
);
export const Chevron = (p: P) => (
  <Svg {...p}><path d="M9 6l6 6-6 6" /></Svg>
);
export const Back = (p: P) => (
  <Svg {...p}><path d="M15 6l-6 6 6 6" /></Svg>
);
export const Bell = (p: P) => (
  <Svg {...p}><path d="M6 16V11a6 6 0 0112 0v5l2 2H4zM10 21h4" /></Svg>
);
export const Mask = (p: P) => (
  <Svg {...p}><path d="M4 6c5-2 11-2 16 0v5c0 5-4 9-8 9s-8-4-8-9z" /><path d="M8 11h2M14 11h2M9 15c2 1.3 4 1.3 6 0" /></Svg>
);

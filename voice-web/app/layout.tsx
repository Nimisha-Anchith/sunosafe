import type { Metadata, Viewport } from 'next';
import './globals.css';

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  themeColor: '#134e4a',
};

export const metadata: Metadata = {
  title: 'SunoSafe',
  applicationName: 'SunoSafe',
  description:
    'Voice-first digital safety companion: check messages and links, and get help after a scam.',
  icons: {
    icon: [{ url: '/suno-192.png', sizes: '192x192', type: 'image/png' }],
    apple: [{ url: '/suno-192.png' }],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en-IN" className="h-full">
      <body className="h-full min-h-screen">{children}</body>
    </html>
  );
}

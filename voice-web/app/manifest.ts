import type { MetadataRoute } from 'next';

/**
 * Web app manifest: lets Chrome on Android install SunoSafe to the home screen
 * (its own icon, full-screen, no address bar) and adds it to the system Share
 * menu through `share_target`.
 */
export default function manifest(): MetadataRoute.Manifest {
  const base: MetadataRoute.Manifest = {
    name: 'SunoSafe',
    short_name: 'SunoSafe',
    description: 'Voice-first digital safety companion: check messages and links, and get help after a scam.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    orientation: 'portrait',
    background_color: '#f5f3ec',
    theme_color: '#134e4a',
    lang: 'en-IN',
    categories: ['security', 'utilities'],
    icons: [
      { src: '/suno-192.png', sizes: '192x192', type: 'image/png', purpose: 'any' },
      { src: '/suno-512.png', sizes: '512x512', type: 'image/png', purpose: 'any' },
      { src: '/suno-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
    ],
  };
  return {
    ...base,
    share_target: {
      action: '/share',
      method: 'GET',
      params: { title: 'title', text: 'text', url: 'url' },
    },
  } as MetadataRoute.Manifest;
}

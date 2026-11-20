/*
 * SunoSafe service worker (minimal on purpose).
 * It exists so the app is installable and can appear in the Share menu.
 * It caches nothing: security results must always come fresh from the server,
 * and no message text is ever stored by the worker.
 */
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', () => {
  /* network only: let the browser handle every request normally */
});

const SHELL_CACHE = "bb-shell-f10d485487";
const DATA_CACHE = "bb-data-v1";
const SHELL_FILES = ["./index.html", "./style.css", "./app.js", "./manifest.json"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open(SHELL_CACHE).then(c => c.addAll(SHELL_FILES)));
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => k !== SHELL_CACHE && k !== DATA_CACHE).map(k => caches.delete(k))
    ))
  );
  self.clients.claim();
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (url.pathname.endsWith("data.js") || url.pathname.endsWith("data.local.js")) {
    // network-first, fall back to cache, so the phone always tries for fresh content
    // (data.local.js included: it changes every local pipeline run just like data.js)
    e.respondWith(
      fetch(e.request).then(res => {
        const copy = res.clone();
        caches.open(DATA_CACHE).then(c => c.put(e.request, copy));
        return res;
      }).catch(() => caches.match(e.request))
    );
    return;
  }
  // cache-first for the app shell
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});

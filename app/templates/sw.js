// Rendered by /sw.js. Any static asset change alters the hashed URLs and CACHE name below,
// so the browser installs a new worker and the activate step drops the old cache.
const CACHE = "macro-log-{{ version }}";
const SHELL = {{ shell|tojson }};

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(SHELL)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))),
  );
  self.clients.claim();
});

// Versioned static URLs never change, so serve them cache-first. Unversioned static
// requests go network-first; pages and API calls always go to the network.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET" || !url.pathname.startsWith("/static/")) return;
  const fromNetwork = () =>
    fetch(event.request).then((response) => {
      if (response.ok) {
        const copy = response.clone();
        caches.open(CACHE).then((cache) => cache.put(event.request, copy));
      }
      return response;
    });
  if (url.searchParams.has("v")) {
    event.respondWith(caches.match(event.request).then((cached) => cached || fromNetwork()));
  } else {
    event.respondWith(fromNetwork().catch(() => caches.match(event.request)));
  }
});

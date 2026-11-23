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

// Prefetched pages. When a finger or mouse button goes down on a nav link or day arrow, app.js
// asks for its page (X-Prefetch), and the boosted request that follows on release takes that
// response instead of starting a new one. Each is used once and only for PREFETCH_MS, and any
// write (a non-GET) drops them all, so a page is never older than the tap that opened it.
const PREFETCH_MS = 5000;
const prefetched = new Map(); // url -> { at, res: Promise<Response> }

function takePrefetched(href) {
  const hit = prefetched.get(href);
  prefetched.delete(href);
  return hit && Date.now() - hit.at < PREFETCH_MS ? hit.res : null;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") prefetched.clear();
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  if (req.headers.get("X-Prefetch") === "1") {
    const res = fetch(req);
    prefetched.set(req.url, { at: Date.now(), res });
    event.waitUntil(res.catch(() => {}));
    event.respondWith(new Response(null, { status: 204 })); // app.js doesn't read it
    return;
  }
  // Only a boosted request with a prefetched page is answered here; anything else (no
  // prefetch, or it failed or errored) goes to the network as it always has.
  if (req.headers.get("HX-Boosted") === "true") {
    const hit = takePrefetched(req.url);
    if (hit) event.respondWith(hit.then((res) => (res.ok ? res : fetch(req)), () => fetch(req)));
  }
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

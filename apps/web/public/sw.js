const CACHE_NAME = "soricall-shell-v3";
const APP_ROOT = new URL("./", self.location).pathname;
const SHELL_ASSETS = [APP_ROOT, `${APP_ROOT}manifest.webmanifest`, `${APP_ROOT}icon.svg`];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(SHELL_ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const request = event.request;
  const pathname = new URL(request.url).pathname;
  if (request.method !== "GET" || pathname.startsWith("/api/") || pathname.startsWith("/soricall-api/")) return;
  event.respondWith(
    fetch(request, { cache: "no-store" }).catch(() =>
      caches.match(request).then((cached) => cached || caches.match(APP_ROOT)),
    ),
  );
});

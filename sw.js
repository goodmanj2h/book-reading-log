// Book Reading Log 서비스 워커 (PWA 캐시 및 모바일 빠른 로딩)
const CACHE_NAME = 'book-reading-log-v1';

self.addEventListener('install', (e) => {
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(clients.claim());
});

self.addEventListener('fetch', (e) => {
  // 네트워크 우선, 실패 시 캐시 폴백
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});


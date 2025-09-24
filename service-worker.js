const CACHE_NAME = 'tresure-deck-cache-v1';
const urlsToCache = [
  './',
  'index.html',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
  'https://cdn.jsdelivr.net/npm/chart.js',
  'Card_Data/Onepeace_Cards/cards.json',
  'Card_Data/Onepeace_Cards/don_cards.json',
  'Card_Data/Onepeace_Cards/B.json',
  'Card_Data/Onepeace_Cards/C.json',
  'Card_Data/Onepeace_Cards/latestprice.json',
  // 必要に応じて、追加の画像やCSS, JSファイルなどをここに追加
  'icons/icon-192x192.png',
  'icons/icon-512x512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request)
      .then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request);
      })
  );
});

self.addEventListener('activate', (event) => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheWhitelist.indexOf(cacheName) === -1) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

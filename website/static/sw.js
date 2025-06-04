const CACHE_NAME = 'noteshare-v1';
const urlsToCache = [
  '/',
  '/static/style.css',
  '/static/index.js',
  '/static/manifest.json',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css',
  'https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css',
  'https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.css',
  'https://cdn.jsdelivr.net/npm/fullcalendar@5.11.3/main.min.js'
];

// Instalacja service workera
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Opened cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Aktywacja service workera
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

// Obsługa żądań
self.addEventListener('fetch', event => {
  // Strategia: Network First, then Cache
  event.respondWith(
    fetch(event.request)
      .then(response => {
        // Sprawdź czy otrzymaliśmy poprawną odpowiedź
        if(!response || response.status !== 200 || response.type !== 'basic') {
          return response;
        }

        // Sklonuj odpowiedź
        const responseToCache = response.clone();

        // Dodaj odpowiedź do cache
        caches.open(CACHE_NAME)
          .then(cache => {
            cache.put(event.request, responseToCache);
          });

        return response;
      })
      .catch(() => {
        // Jeśli nie ma połączenia, spróbuj pobrać z cache
        return caches.match(event.request)
          .then(response => {
            if (response) {
              return response;
            }
            // Jeśli nie ma w cache, zwróć stronę offline
            if (event.request.mode === 'navigate') {
              return caches.match('/');
            }
            return new Response('Offline', {
              status: 503,
              statusText: 'Service Unavailable',
              headers: new Headers({
                'Content-Type': 'text/plain'
              })
            });
          });
      })
  );
}); 
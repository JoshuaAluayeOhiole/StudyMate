const CACHE_NAME = 'studymate-v1';

const STATIC_ASSETS = [
  '/',
  '/static/css/style.css',
  '/static/img/favicon-192.png',
  '/static/img/favicon-512.png',
  '/static/img/favicon.ico'
];

// Install: cache static assets
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate: clean up old caches
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) {
          return key !== CACHE_NAME;
        }).map(function(key) {
          return caches.delete(key);
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch: network first, fall back to cache for static assets
self.addEventListener('fetch', function(event) {
  // Only handle GET requests
  if (event.request.method !== 'GET') return;

  // For API calls (ask, dismiss-onboarding) always go to network
  const url = new URL(event.request.url);
  if (url.pathname.startsWith('/ask') || url.pathname.startsWith('/dismiss-onboarding')) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then(function(response) {
        // Cache a copy of successful responses for static assets
        if (response && response.status === 200) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(function(cache) {
            cache.put(event.request, clone);
          });
        }
        return response;
      })
      .catch(function() {
        // Network failed, try cache
        return caches.match(event.request).then(function(cached) {
          if (cached) return cached;
          // If nothing in cache, return offline page for navigation requests
          if (event.request.mode === 'navigate') {
            return caches.match('/');
          }
        });
      })
  );
});

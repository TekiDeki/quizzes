/* Free quizzes · TekiDeki - offline shell
 * SPDX-License-Identifier: Apache-2.0
 * Copyright 2026 Kristian Mario Miskovic (TekiDeki)
 *
 * Regula casei: fiecare aplicatie se instaleaza pe telefon si se deschide si fara retea.
 * Toata logica sta aici, in fisierul asta - in pagina raman doar cateva linii de inregistrare.
 * Se creste VERSION cand se schimba vreun fisier din SHELL.
 */
var VERSION = 'quizzes-v2';
var CACHE = VERSION;
var SHELL = [
  './',
  './index.html',
  './ai-iq-test/',
  './ai-iq-test/index.html',
  './celebrity-iq-test/',
  './celebrity-iq-test/index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon-maskable-512.png',
  './apple-touch-icon.png'
];

self.addEventListener('install', function (event) {
  event.waitUntil(caches.open(CACHE).then(function (cache) {
    return cache.addAll(SHELL);
  }).then(function () { return self.skipWaiting(); }));
});

self.addEventListener('activate', function (event) {
  event.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.filter(function (k) {
      return k.indexOf('quizuri-') === 0 && k !== CACHE;
    }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (event) {
  var request = event.request;
  if (request.method !== 'GET') return;
  var url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  event.respondWith(caches.open(CACHE).then(function (cache) {
    return cache.match(request, { ignoreSearch: true }).then(function (cached) {
      var network = fetch(request).then(function (response) {
        if (response && response.ok && response.type === 'basic') {
          cache.put(request, response.clone()).catch(function () {});
        }
        return response;
      });
      if (cached) { event.waitUntil(network.catch(function () {})); return cached; }
      return network.catch(function () {
        /* fara retea si fara copie: intoarce pagina principala, ca aplicatia sa porneasca totusi */
        return cache.match('./index.html', { ignoreSearch: true }).then(function (fallback) {
          return fallback || Response.error();
        });
      });
    });
  }));
});

/* Service worker KcoMat : notifications push (servi à /sw.js, portée « / »). */
const ICON = "{{ icon|escapejs }}";
const BADGE = "{{ badge|escapejs }}";
const VAPID_PUBLIC_KEY = "{{ vapid_public_key|escapejs }}";

self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));

self.addEventListener('push', (event) => {
  let data = {};
  try {
    data = event.data ? event.data.json() : {};
  } catch (e) {
    data = { title: 'KcoMat', body: event.data ? event.data.text() : '' };
  }
  const options = {
    body: data.body || '',
    icon: ICON,
    badge: BADGE,
    lang: 'fr',
    tag: data.tag || undefined,
    data: { url: data.url || '/' },
    vibrate: [80, 40, 80],
  };
  if (data.image) options.image = data.image;
  event.waitUntil(self.registration.showNotification(data.title || 'KcoMat', options));
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = new URL((event.notification.data && event.notification.data.url) || '/', self.location.origin).href;
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((fenetres) => {
      for (const fenetre of fenetres) {
        if (fenetre.url === url && 'focus' in fenetre) return fenetre.focus();
      }
      return self.clients.openWindow(url);
    })
  );
});

/* Le navigateur peut renouveler l'abonnement : on le ré-enregistre côté serveur. */
function base64ToUint8Array(value) {
  const padding = '='.repeat((4 - (value.length % 4)) % 4);
  const raw = atob((value + padding).replace(/-/g, '+').replace(/_/g, '/'));
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(
    self.registration.pushManager
      .subscribe({ userVisibleOnly: true, applicationServerKey: base64ToUint8Array(VAPID_PUBLIC_KEY) })
      .then((subscription) => fetch('/notifications/renouvellement/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ancien: event.oldSubscription ? event.oldSubscription.endpoint : '', subscription }),
      }))
  );
});

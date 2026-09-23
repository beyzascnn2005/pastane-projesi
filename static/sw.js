// sw.js - Service Worker


self.addEventListener("push", function (event) {
    let baslik = "Pastane";
    let govde = "";

    // Gelen veri JSON değilse (örneğin DevTools'un test push'u düz
    // metin gönderir), hata vermek yerine onu olduğu gibi gösteriyoruz.
    try {
        const veri = event.data ? event.data.json() : {};
        baslik = veri.title || baslik;
        govde = veri.body || "";
    } catch (hata) {
        govde = event.data ? event.data.text() : "";
    }

    const secenekler = { body: govde, badge: "/static/icon.png" };
    event.waitUntil(self.registration.showNotification(baslik, secenekler));
});

// Bildirime tıklanınca siteyi açsın
self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    event.waitUntil(clients.openWindow("/admin"));
});
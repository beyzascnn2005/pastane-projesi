[README.md](https://github.com/user-attachments/files/32653471/README.md)
# Dondurmacı Abdülkerim

Ilıca / Erzurum'da faaliyet gösteren bir dondurma, pasta ve geleneksel tatlı
dükkânı için geliştirilmiş, FastAPI tabanlı sipariş ve tanıtım sitesi.

**Canlı site:** [dondurmaciabdulkerim.onrender.com](https://dondurmaciabdulkerim.onrender.com)

Kodun tamamı incelenmiş, test edilmiş ve güvenlik açısından gözden geçirilmiştir.

---

## Özellikler

- Ürün tanıtımı, kategoriye göre filtreleme (Dondurma, Pasta, Baklava, Kadayıf)
- Üyelik sistemi: kayıt, giriş, çerez (cookie) tabanlı oturum
- Ürünlere yorum ve puan bırakma, beğenme
- Özel sipariş oluşturma ve sipariş takibi (Alındı → Hazırlanıyor → Teslim Alındı)
- Sadakat puanı: teslim alınan her siparişte otomatik puan birikimi
- Admin paneli: ürün ekleme/silme/stok yönetimi, sipariş yönetimi, mesajlar, kampanya maili
- Ürün görsellerinin Cloudinary üzerinden yüklenmesi
- Admin için push bildirimi altyapısı (şu an devre dışı, aşağıya bakın)
- Google Search Console entegrasyonu: `sitemap.xml`, `robots.txt`, sayfa açıklaması

## Kullanılan Teknolojiler

- **Backend:** Python, FastAPI, Uvicorn
- **Veritabanı:** SQLAlchemy ORM (PostgreSQL, Render üzerinde barındırılıyor)
- **Şablonlar:** Jinja2 (sunucu taraflı HTML render)
- **Kimlik doğrulama:** JWT (python-jose), bcrypt (passlib) ile şifre hash'leme
- **Görsel depolama:** Cloudinary
- **E-posta:** smtplib / Gmail SMTP (kampanya maili için — bkz. Bilinen Kısıtlar)
- **Barındırma:** Render (Web Service, ücretsiz plan)

## Proje Yapısı

```
├── main.py           # FastAPI uygulaması, tüm endpoint'ler (route'lar)
├── auth.py           # JWT token üretimi/doğrulama, cookie tabanlı giriş kontrolü
├── crud.py           # Veritabanı işlemleri (Create/Read/Update/Delete) ve iş mantığı
├── models.py         # SQLAlchemy veritabanı tablo tanımları
├── schemas.py        # Pydantic şemaları (API giriş/çıkış veri şekilleri)
├── database.py       # Veritabanı bağlantısı ve oturum yönetimi
├── config.py         # Ortam değişkenlerinden okunan ayarlar (VAPID, SMTP)
├── admin_yap.py      # Tek seferlik CLI aracı: bir kullanıcıyı admin yapar
├── requirements.txt  # Python bağımlılıkları
├── templates/        # Jinja2 HTML şablonları
└── static/           # CSS, görseller, favicon, service worker (sw.js)
```

## Kurulum (Yerel Geliştirme)

```bash
# 1. Depoyu klonla
git clone https://github.com/beyzascnn2005/pastane-projesi.git
cd pastane-projesi

# 2. Sanal ortam oluştur ve etkinleştir (Windows)
python -m venv venv
venv\Scripts\activate

# 3. Bağımlılıkları kur
pip install -r requirements.txt

# 4. .env dosyasını oluştur (bkz. aşağıdaki tablo) ve doldur

# 5. Sunucuyu başlat
uvicorn main:app --reload
```

Sunucu `http://127.0.0.1:8000` adresinde çalışmaya başlar.

## Ortam Değişkenleri (`.env`)

Bu proje hiçbir şifre, anahtar ya da bağlantı adresini kod içinde tutmaz;
hepsi ortam değişkenlerinden okunur. `.env` dosyası asla GitHub'a
gönderilmez (`.gitignore` içinde tanımlıdır).

| Değişken | Açıklama |
|---|---|
| `SECRET_KEY` | Giriş token'larını (JWT) imzalayan gizli anahtar. `python -c "import secrets; print(secrets.token_urlsafe(48))"` ile üretilir. |
| `DATABASE_URL` | Veritabanı bağlantı adresi (PostgreSQL). |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary hesap bilgisi (görsel yükleme için). |
| `CLOUDINARY_API_KEY` | Cloudinary hesap bilgisi. |
| `CLOUDINARY_API_SECRET` | Cloudinary hesap bilgisi. |
| `SMTP_EMAIL` | Kampanya maili gönderen Gmail adresi. |
| `SMTP_SIFRE` | Gmail **uygulama şifresi** (normal hesap şifresi değil). |
| `VAPID_CLAIM_EMAIL` | Push bildirimi için iletişim e-postası (opsiyonel, varsayılanı var). |
| `SITE_URL` | Sitemap için tam site adresi (opsiyonel, varsayılan: canlı adres). |

## Dağıtım (Deployment)

Site [Render](https://render.com) üzerinde bir **Web Service** olarak
barındırılıyor:

- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Yukarıdaki tüm ortam değişkenleri Render → Environment sekmesinde tanımlı.
- `main` dalına yapılan her `git push`, otomatik deploy tetikler.

⚠️ **Render ücretsiz planı hakkında:** Bir süre istek gelmezse servis
"uyur" ve ilk istek 30–60 saniye sürebilir. Bu bir hata değil, planın
davranışıdır.

## Yönetici (Admin) Hesabı Oluşturma

Bir kullanıcıyı admin yapmak için (veritabanına doğrudan erişimle):

```bash
python admin_yap.py kullanici@example.com
```

## Bilinen Kısıtlar / Yapılacaklar

- **Push bildirimi şu an devre dışı.** VAPID özel anahtar dosyası
  (`vapid_private.pem`) güvenlik gereği Render'a yüklenmedi; sipariş
  geldiğinde admin'e anlık bildirim gitmiyor. Hata, kullanıcıyı
  etkilemeyecek şekilde `try/except` ile yutuluyor (bkz. `main.py`,
  `siparis_ver_formu_isle`). İleride Telegram botu ya da HTTP API'li
  bir e-posta servisi (Resend, Brevo) ile değiştirilmesi planlanıyor.
- **Kampanya maili (Gmail SMTP) Render'ın ücretsiz planında çalışmaz.**
  Render, ücretsiz planlarda SMTP portlarını (25/465/587) engelliyor.
  Bu özelliğin kalıcı çözümü de yukarıdaki gibi HTTP API'li bir e-posta
  servisine geçmek.
- Şu an `onrender.com` alt alan adında barınıyor; özel bir alan adına
  (`.com`) geçiş planlanıyor.

## Güvenlik Notları

- Tüm gizli bilgiler (`SECRET_KEY`, SMTP şifresi, Cloudinary anahtarları,
  veritabanı adresi) ortam değişkenlerinden okunur, koda yazılmaz.
- Şifreler veritabanında bcrypt ile hash'lenmiş olarak tutulur.
- Giriş oturumu `httponly` cookie ile taşınır (JavaScript erişemez).
- Admin'e özel sayfalar hem sunucu tarafında hem de `Depends()` ile
  yetki kontrolünden geçer.

## Lisans / Kullanım

Bu proje, Dondurmacı Abdülkerim işletmesi için özel olarak geliştirilmiştir.

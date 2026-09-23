"""
crud.py - Veritabanıyla konuşan fonksiyonlar.

Kotlin'deki FinansalIslemDao.kt (DAO) dosyasının karşılığı.
"CRUD" = Create, Read, Update, Delete kısaltması.

main.py bu fonksiyonları çağıracak, kendisi doğrudan veritabanı
sorgusu yazmayacak. Bu ayrım, kodu düzenli ve test edilebilir tutar.
"""

from sqlalchemy.orm import Session
from passlib.context import CryptContext
import models
import schemas

# Şifre hashleme için "bcrypt" algoritmasını kullanacağımızı söylüyoruz.
sifre_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def sifre_hashle(duz_sifre: str) -> str:
    """Kullanıcının girdiği düz şifreyi geri döndürülemez bir hash'e çevirir."""
    return sifre_context.hash(duz_sifre)


def sifre_dogrula(duz_sifre: str, hash_sifre: str) -> bool:
    """Giriş sırasında, girilen şifre ile veritabanındaki hash'i karşılaştırır."""
    return sifre_context.verify(duz_sifre, hash_sifre)


def email_ile_kullanici_getir(db: Session, email: str):
    """Verilen email'e sahip kullanıcı var mı diye bakar (kayıt sırasında
    'bu email zaten kullanılıyor mu' kontrolü için kullanacağız)."""
    return db.query(models.Kullanici).filter(models.Kullanici.email == email).first()


def kullanici_olustur(db: Session, kullanici: schemas.KullaniciOlustur):
    """Yeni bir kullanıcıyı veritabanına kaydeder."""
    hashlenmis_sifre = sifre_hashle(kullanici.sifre)

    yeni_kullanici = models.Kullanici(
        ad_soyad=kullanici.ad_soyad,
        email=kullanici.email,
        sifre_hash=hashlenmis_sifre,
        kampanya_aboneligi=kullanici.kampanya_aboneligi,
    )

    db.add(yeni_kullanici)
    db.commit()
    db.refresh(yeni_kullanici)  # veritabanının verdiği id gibi bilgileri geri çeker
    return yeni_kullanici


# --- ÜRÜN FONKSİYONLARI ---

def urun_olustur(db: Session, urun: schemas.UrunOlustur):
    """Yeni bir ürünü veritabanına ekler."""
    yeni_urun = models.Urun(**urun.model_dump())
    db.add(yeni_urun)
    db.commit()
    db.refresh(yeni_urun)
    return yeni_urun


def tum_urunleri_getir(db: Session, kategori: str | None = None):
    """
    Tüm ürünleri getirir. Eğer kategori parametresi verilmişse,
    sadece o kategorideki ürünleri filtreler.
    """
    sorgu = db.query(models.Urun)
    if kategori:
        sorgu = sorgu.filter(models.Urun.kategori == kategori)
    return sorgu.all()


def stokta_olan_urunleri_getir(db: Session):
    return db.query(models.Urun).filter(models.Urun.stokta_var == True).all()


def urun_getir(db: Session, urun_id: int):
    """Tek bir ürünü id'sine göre getirir (detay sayfası için)."""
    return db.query(models.Urun).filter(models.Urun.id == urun_id).first()


def urun_sil(db: Session, urun_id: int):
    urun = urun_getir(db, urun_id)
    if urun:
        db.delete(urun)
        db.commit()
    return urun


def urun_stok_durumu_degistir(db: Session, urun_id: int):
    urun = urun_getir(db, urun_id)
    if urun:
        urun.stokta_var = not urun.stokta_var
        db.commit()
        db.refresh(urun)
    return urun


def urun_guncelle(db: Session, urun_id: int, urun_verisi: schemas.UrunOlustur):
    urun = urun_getir(db, urun_id)
    if not urun:
        return None
    # setattr ile, gelen verideki her alanı sırayla mevcut ürüne yazıyoruz
    for alan, deger in urun_verisi.model_dump().items():
        setattr(urun, alan, deger)
    db.commit()
    db.refresh(urun)
    return urun


def toplam_kullanici_sayisi(db: Session):
    return db.query(models.Kullanici).count()


def toplam_urun_sayisi(db: Session):
    return db.query(models.Urun).count()


def toplam_yorum_sayisi(db: Session):
    return db.query(models.Yorum).count()


# --- İLETİŞİM MESAJI FONKSİYONLARI ---

def mesaj_ekle(db: Session, mesaj: schemas.IletisimMesajOlustur):
    yeni_mesaj = models.IletisimMesaji(**mesaj.model_dump())
    db.add(yeni_mesaj)
    db.commit()
    db.refresh(yeni_mesaj)
    return yeni_mesaj


def tum_mesajlari_getir(db: Session):
    return db.query(models.IletisimMesaji).order_by(models.IletisimMesaji.tarih.desc()).all()


def mesaj_okundu_isaretle(db: Session, mesaj_id: int):
    mesaj = db.query(models.IletisimMesaji).filter(models.IletisimMesaji.id == mesaj_id).first()
    if mesaj:
        mesaj.okundu = True
        db.commit()
    return mesaj


# --- ÖZEL SİPARİŞ FONKSİYONLARI ---

DURUM_SIRASI = ["Alindi", "Hazirlaniyor", "Teslim Alindi"]


def siparis_olustur(db: Session, kullanici_id: int, siparis: schemas.OzelSiparisOlustur):
    yeni_siparis = models.OzelSiparis(
        kullanici_id=kullanici_id,
        urun_id=siparis.urun_id,
        miktar=siparis.miktar,
        istenilen_tarih=siparis.istenilen_tarih,
        not_metni=siparis.not_metni,
    )
    db.add(yeni_siparis)
    db.commit()
    db.refresh(yeni_siparis)
    return yeni_siparis


def kullanicinin_siparisleri(db: Session, kullanici_id: int):
    return (
        db.query(models.OzelSiparis)
        .filter(models.OzelSiparis.kullanici_id == kullanici_id)
        .order_by(models.OzelSiparis.olusturma_tarihi.desc())
        .all()
    )


def tum_siparisleri_getir(db: Session):
    return db.query(models.OzelSiparis).order_by(models.OzelSiparis.olusturma_tarihi.desc()).all()


def siparis_getir(db: Session, siparis_id: int):
    return db.query(models.OzelSiparis).filter(models.OzelSiparis.id == siparis_id).first()


def siparis_sil(db: Session, siparis_id: int):
    siparis = siparis_getir(db, siparis_id)
    if siparis:
        db.delete(siparis)
        db.commit()
    return siparis


def siparis_durum_guncelle(db: Session, siparis_id: int, yeni_durum: str):
    siparis = siparis_getir(db, siparis_id)
    if not siparis:
        return None

    siparis.durum = yeni_durum
    db.commit()

    # Sipariş "Teslim Alindi" olduğunda, kullanıcının sadakat puanını
    # 1 artırıyoruz. Bu SADECE durum ilk kez "Teslim Alindi" olduğunda
    # olsun istiyoruz (aynı siparişe iki kere puan verilmesin diye
    # ekstra bir kontrol eklemek istersen ileride ayrı bir alan
    # ("puan_verildi_mi") eklenebilir, şimdilik basit tutuyoruz).
    if yeni_durum == "Teslim Alindi":
        siparis.kullanici.sadakat_puani += 1
        db.commit()

    db.refresh(siparis)
    return siparis


def siparisi_cevaba_donustur(siparis: models.OzelSiparis) -> schemas.OzelSiparisCevap:
    return schemas.OzelSiparisCevap(
        id=siparis.id,
        urun_adi=siparis.urun.isim if siparis.urun else "Silinmiş / Bilinmeyen Ürün",
        miktar=siparis.miktar,
        istenilen_tarih=siparis.istenilen_tarih,
        not_metni=siparis.not_metni,
        durum=siparis.durum,
        olusturma_tarihi=siparis.olusturma_tarihi,
        kullanici_adi=siparis.kullanici.ad_soyad if siparis.kullanici else "Bilinmeyen Kullanıcı",
    )


# --- PUSH BİLDİRİM FONKSİYONLARI ---

def push_abonelik_kaydet(db: Session, kullanici_id: int, abonelik: schemas.PushAbonelikOlustur):
    # Aynı cihaz tekrar abone olmaya çalışırsa (örneğin sayfayı
    # yenilerse), eskisini silip yenisini ekliyoruz - "upsert" mantığı.
    mevcut = db.query(models.PushAbonelik).filter(models.PushAbonelik.endpoint == abonelik.endpoint).first()
    if mevcut:
        db.delete(mevcut)
        db.commit()

    yeni_abonelik = models.PushAbonelik(
        kullanici_id=kullanici_id,
        endpoint=abonelik.endpoint,
        p256dh=abonelik.keys.p256dh,
        auth=abonelik.keys.auth,
    )
    db.add(yeni_abonelik)
    db.commit()
    return yeni_abonelik


def tum_admin_aboneliklerini_getir(db: Session):
    return (
        db.query(models.PushAbonelik)
        .join(models.Kullanici)
        .filter(models.Kullanici.is_admin == True)
        .all()
    )


def push_bildirimi_gonder(db: Session, baslik: str, govde: str):
    """
    Kayıtlı TÜM admin aboneliklerine bildirim gönderir. Bir abonelik
    artık geçersizse (kullanıcı bildirimi kapattıysa vb.) hata sessizce
    yutulur ve o abonelik veritabanından silinir.
    """
    import json
    import config
    from pywebpush import webpush, WebPushException

    tum_abonelikler_debug = db.query(models.PushAbonelik).all()
    print(f"[PUSH DEBUG] Veritabanındaki TOPLAM abonelik sayısı (filtresiz): {len(tum_abonelikler_debug)}")
    for a in tum_abonelikler_debug:
        ilgili_kullanici = db.query(models.Kullanici).filter(models.Kullanici.id == a.kullanici_id).first()
        print(f"[PUSH DEBUG]  -> abonelik.kullanici_id={a.kullanici_id}, bulunan kullanici.is_admin={ilgili_kullanici.is_admin if ilgili_kullanici else 'KULLANICI BULUNAMADI'}")

    abonelikler = tum_admin_aboneliklerini_getir(db)
    print(f"[PUSH DEBUG] Bulunan admin aboneliği sayısı: {len(abonelikler)}")

    for abone in abonelikler:
        try:
            webpush(
                subscription_info={
                    "endpoint": abone.endpoint,
                    "keys": {"p256dh": abone.p256dh, "auth": abone.auth},
                },
                data=json.dumps({"title": baslik, "body": govde}),
                vapid_private_key=config.VAPID_PRIVATE_KEY_DOSYASI,
                vapid_claims={"sub": config.VAPID_CLAIM_EMAIL},
            )
            print("[PUSH DEBUG] Bildirim başarıyla gönderildi.")
        except Exception as e:
            print(f"[PUSH DEBUG] HATA (tip: {type(e).__name__}): {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"[PUSH DEBUG] Response status: {e.response.status_code}")
                print(f"[PUSH DEBUG] Response body: {e.response.text}")
            # NOT: Debug aşamasındayız, aboneliği otomatik SİLMİYORUZ ki
            # tekrar tekrar test edebilelim. Gerçek sebebi bulunca bu
            # davranışı (400 gibi kalıcı hatalarda silme) geri ekleyeceğiz.


# --- YORUM FONKSİYONLARI ---

def yorum_ekle(db: Session, urun_id: int, kullanici_id: int, yorum: schemas.YorumOlustur):
    yeni_yorum = models.Yorum(
        urun_id=urun_id,
        kullanici_id=kullanici_id,
        metin=yorum.metin,
        puan=yorum.puan,
    )
    db.add(yeni_yorum)
    db.commit()
    db.refresh(yeni_yorum)
    return yeni_yorum


def urun_yorumlarini_getir(db: Session, urun_id: int):
    return (
        db.query(models.Yorum)
        .filter(models.Yorum.urun_id == urun_id)
        .order_by(models.Yorum.tarih.desc())
        .all()
    )


def urun_ortalama_puan(db: Session, urun_id: int):
    from sqlalchemy import func as sql_func
    sonuc = (
        db.query(sql_func.avg(models.Yorum.puan))
        .filter(models.Yorum.urun_id == urun_id)
        .scalar()
    )
    return round(sonuc, 1) if sonuc else None


# --- BEĞENİ FONKSİYONLARI ---

def begeni_var_mi(db: Session, urun_id: int, kullanici_id: int):
    return (
        db.query(models.Begeni)
        .filter(models.Begeni.urun_id == urun_id, models.Begeni.kullanici_id == kullanici_id)
        .first()
    )


def begeni_ekle(db: Session, urun_id: int, kullanici_id: int):
    yeni_begeni = models.Begeni(urun_id=urun_id, kullanici_id=kullanici_id)
    db.add(yeni_begeni)
    db.commit()
    return yeni_begeni


def begeni_kaldir(db: Session, begeni: models.Begeni):
    db.delete(begeni)
    db.commit()


def urun_begeni_sayisi(db: Session, urun_id: int):
    return db.query(models.Begeni).filter(models.Begeni.urun_id == urun_id).count()


def kullanicinin_begendigi_urunler(db: Session, kullanici_id: int):
    return (
        db.query(models.Urun)
        .join(models.Begeni, models.Begeni.urun_id == models.Urun.id)
        .filter(models.Begeni.kullanici_id == kullanici_id)
        .all()
    )


# --- KAMPANYA MAİLİ FONKSİYONLARI ---

def kampanyaya_abone_kullanicilari_getir(db: Session):
    return db.query(models.Kullanici).filter(models.Kullanici.kampanya_aboneligi == True).all()


def kampanya_maili_gonder(db: Session, konu: str, mesaj: str):
    """
    Kampanyaya abone TÜM kullanıcılara aynı anda e-posta gönderir.
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.header import Header
    from email.utils import formataddr
    import config

    aboneler = kampanyaya_abone_kullanicilari_getir(db)
    if not aboneler:
        return 0

    gonderilen_sayisi = 0

    # Görünen isim (config.py içinde varsa oradan çeker, yoksa varsayılanı kullanır)
    gonderen_adi = getattr(config, "SMTP_GONDEREN_ADI", "Dondurmacı Abdülkerim 🍦")

    with smtplib.SMTP(config.SMTP_SUNUCU, config.SMTP_PORT) as sunucu:
        sunucu.starttls()
        sunucu.login(config.SMTP_EMAIL, config.SMTP_SIFRE)

        for kullanici in aboneler:
            # "utf-8" belirtmek emojilerin ve Türkçe karakterlerin bozulmasını engeller
            mail = MIMEText(mesaj, "plain", "utf-8")
            mail["Subject"] = Header(konu, "utf-8")
            
            # Gönderen adını emojiyle birlikte düzgün formatta ekliyoruz:
            mail["From"] = formataddr((str(Header(gonderen_adi, "utf-8")), config.SMTP_EMAIL))
            mail["To"] = kullanici.email

            try:
                sunucu.send_message(mail)
                gonderilen_sayisi += 1
            except Exception:
                continue

    return gonderilen_sayisi

def yorumu_cevaba_donustur(yorum: models.Yorum) -> schemas.YorumCevap:
    """
    Yorum modelinde 'kullanici_adi' diye bir sütun yok, bu bilgiyi
    relationship üzerinden (yorum.kullanici.ad_soyad) çekip
    YorumCevap şemasına elle dolduruyoruz.
    """
    return schemas.YorumCevap(
        id=yorum.id,
        metin=yorum.metin,
        puan=yorum.puan,
        tarih=yorum.tarih,
        kullanici_id=yorum.kullanici_id,
        kullanici_adi=yorum.kullanici.ad_soyad,
    )
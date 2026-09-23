"""
main.py - Uygulamamızın kalbi.

Bu dosya artık:
1. Uygulama açılışında veritabanı tablolarını oluşturuyor
2. Kayıt (register) endpoint'i sunuyor
"""

from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse, Response
from urllib.parse import quote
from fastapi.security import OAuth2PasswordRequestForm
from datetime import date
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import models
import schemas
import crud
import auth
from database import engine, get_db

import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, File

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


# Bu satır çok önemli: models.py'da tanımladığımız tüm tabloları
# veritabanında GERÇEKTEN oluşturur.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pastane Projesi")

# templates klasöründeki HTML dosyalarını kullanabilmek için
templates = Jinja2Templates(directory="templates")

# static klasöründeki dosyalara (CSS, resim vb.) /static adresinden
# erişilebilmesini sağlıyoruz (ileride kullanacağız)
app.mount("/static", StaticFiles(directory="static"), name="static")


# --- HTML SAYFA: Ana Sayfa ---
#
# Dikkat: response_model YOK burada, çünkü JSON değil HTML döndürüyoruz.
# "request: Request" parametresi Jinja2'nin zorunlu gerektirdiği bir şey.
@app.get("/")
def ana_sayfa_html(
    request: Request,
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    return templates.TemplateResponse(
        request=request,
        name="anasayfa.html",
        context={"current_kullanici": su_anki_kullanici},
    )


# Şimdilik kategorileri sabit tutuyoruz (ileride istersen ürünlerden
# otomatik de çekebiliriz ama başlangıç için bu daha basit ve öngörülebilir)
KATEGORILER = ["Dondurma", "Pasta", "Baklava", "KadayIf"]


@app.get("/urunler-sayfasi")
def urunler_sayfasi_html(
    request: Request,
    kategori: str | None = None,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    urunler = crud.tum_urunleri_getir(db, kategori)
    return templates.TemplateResponse(
        request=request,
        name="urunler.html",
        context={
            "urunler": urunler,
            "kategoriler": KATEGORILER,
            "secili_kategori": kategori,
            "current_kullanici": su_anki_kullanici,
        },
    )


@app.get("/urun-detay/{urun_id}")
def urun_detay_sayfasi_html(
    urun_id: int,
    request: Request,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    yorumlar = crud.urun_yorumlarini_getir(db, urun_id)

    # Kullanıcı giriş yapmışsa, bu ürünü daha önce beğenmiş mi diye
    # bakıyoruz - buna göre buton "Beğen" mi "Beğenildi" mi gösterecek.
    kullanici_begendi_mi = False
    if su_anki_kullanici:
        kullanici_begendi_mi = crud.begeni_var_mi(db, urun_id, su_anki_kullanici.id) is not None

    return templates.TemplateResponse(
        request=request,
        name="urun_detay.html",
        context={
            "urun": urun,
            "yorumlar": [crud.yorumu_cevaba_donustur(y) for y in yorumlar],
            "begeni_sayisi": crud.urun_begeni_sayisi(db, urun_id),
            "ortalama_puan": crud.urun_ortalama_puan(db, urun_id),
            "current_kullanici": su_anki_kullanici,
            "kullanici_begendi_mi": kullanici_begendi_mi,
        },
    )


# --- SİTE İÇİN YORUM VE BEĞENİ FORMLARI (COOKIE İLE) ---

@app.post("/urun-detay/{urun_id}/yorum-ekle")
def site_yorum_ekle(
    urun_id: int,
    metin: str = Form(...),
    puan: int = Form(...),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    # Giriş yapmamış biri bir şekilde forma ulaşırsa (örneğin linki
    # doğrudan çağırırsa), onu giriş sayfasına yönlendiriyoruz.
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    yorum_verisi = schemas.YorumOlustur(metin=metin, puan=puan)
    crud.yorum_ekle(db, urun_id, su_anki_kullanici.id, yorum_verisi)

    # Yorum eklendikten sonra aynı ürün sayfasına geri dönüyoruz,
    # kullanıcı kendi yorumunu hemen listede görsün.
    return RedirectResponse(url=f"/urun-detay/{urun_id}", status_code=303)


@app.post("/urun-detay/{urun_id}/begen")
def site_begen_veya_kaldir(
    urun_id: int,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    mevcut_begeni = crud.begeni_var_mi(db, urun_id, su_anki_kullanici.id)
    if mevcut_begeni:
        crud.begeni_kaldir(db, mevcut_begeni)
    else:
        crud.begeni_ekle(db, urun_id, su_anki_kullanici.id)

    return RedirectResponse(url=f"/urun-detay/{urun_id}", status_code=303)


# API'nin canlı olup olmadığını kontrol etmek için basit bir endpoint
# (tarayıcıdan değil, teknik kontrol amaçlı kullanılır)
@app.get("/api/durum")
def api_durum():
    return {"mesaj": "Pastane projesi backend'i çalışıyor."}

SITE_URL = os.getenv("SITE_URL", "https://dondurmaciabdulkerim.onrender.com").rstrip("/")


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    icerik = (
        "User-agent: *\n"
        "Disallow: /admin\n"
        "Disallow: /giris-sayfasi\n"
        "Disallow: /kayit-sayfasi\n"
        "Disallow: /siparis-ver\n"
        "Disallow: /siparislerim\n"
        "Disallow: /favorilerim\n"
        "Disallow: /cikis\n"
        "\n"
        f"Sitemap: {SITE_URL}/sitemap.xml\n"
    )
    return Response(content=icerik, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml(db: Session = Depends(get_db)):
    adresler = [
        f"{SITE_URL}/",
        f"{SITE_URL}/urunler-sayfasi",
        f"{SITE_URL}/iletisim",
    ]
    for kategori in KATEGORILER:
        adresler.append(f"{SITE_URL}/urunler-sayfasi?kategori={quote(kategori)}")
    for urun in crud.tum_urunleri_getir(db):
        adresler.append(f"{SITE_URL}/urun-detay/{urun.id}")

    satirlar = "".join(f"<url><loc>{a}</loc></url>" for a in adresler)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{satirlar}</urlset>"
    )
    return Response(content=xml, media_type="application/xml")

# --- KAYIT (REGISTER) ENDPOINT ---
#
# response_model=schemas.KullaniciCevap -> dönen cevabın şeklini garanti eder
# (yani şifre_hash asla dışarı sızmaz)
#
# db: Session = Depends(get_db) -> FastAPI'ye "bu fonksiyon çalışmadan önce
# bana bir veritabanı oturumu (db) hazırla" demek. Buna "dependency injection" denir.
@app.post("/kayit", response_model=schemas.KullaniciCevap)
def kayit_ol(kullanici: schemas.KullaniciOlustur, db: Session = Depends(get_db)):
    # Önce bu email ile kayıtlı biri var mı kontrol ediyoruz
    mevcut_kullanici = crud.email_ile_kullanici_getir(db, kullanici.email)
    if mevcut_kullanici:
        # HTTPException, API'nin doğru bir hata mesajı ve durum kodu
        # (400 = Bad Request) döndürmesini sağlar
        raise HTTPException(status_code=400, detail="Bu email zaten kayıtlı.")

    yeni_kullanici = crud.kullanici_olustur(db, kullanici)
    return yeni_kullanici


# --- GİRİŞ (LOGIN) ENDPOINT ---
#
# OAuth2PasswordRequestForm, /docs arayüzünde otomatik olarak
# "username" ve "password" alanlı bir form gösterir. Biz email'i
# "username" alanına gireceğiz (standart böyle, isim kafanı karıştırmasın).
@app.post("/giris")
def giris_yap(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    kullanici = crud.email_ile_kullanici_getir(db, form.username)

    hatali_giris = HTTPException(
        status_code=400, detail="Email veya şifre hatalı."
    )

    if not kullanici:
        raise hatali_giris

    if not crud.sifre_dogrula(form.password, kullanici.sifre_hash):
        raise hatali_giris

    token = auth.token_olustur(kullanici.email)
    return {"access_token": token, "token_type": "bearer"}


# --- KORUMALI ENDPOINT ÖRNEĞİ ---
#
# auth.su_anki_kullaniciyi_getir dependency'sini kullanıyoruz.
# Bu endpoint'e sadece GEÇERLİ bir token ile erişilebilir.
@app.get("/profilim", response_model=schemas.KullaniciCevap)
def profilimi_getir(su_anki_kullanici: models.Kullanici = Depends(auth.su_anki_kullaniciyi_getir)):
    return su_anki_kullanici


# --- ÜRÜN ENDPOINT'LERİ ---

# HERKESE AÇIK: ürünleri listeleme (giriş gerekmiyor, kim isterse görebilir)
# ?kategori=Baklava gibi bir sorgu parametresiyle filtreleme de yapılabiliyor
@app.get("/urunler", response_model=list[schemas.UrunCevap])
def urunleri_listele(kategori: str | None = None, db: Session = Depends(get_db)):
    return crud.tum_urunleri_getir(db, kategori)


# HERKESE AÇIK: tek bir ürünün detayını görme (artık yorumlar,
# beğeni sayısı ve ortalama puan da dahil)
@app.get("/urunler/{urun_id}", response_model=schemas.UrunDetayCevap)
def urun_detayi(urun_id: int, db: Session = Depends(get_db)):
    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    yorumlar = crud.urun_yorumlarini_getir(db, urun_id)

    return schemas.UrunDetayCevap(
        **schemas.UrunCevap.model_validate(urun).model_dump(),
        yorumlar=[crud.yorumu_cevaba_donustur(y) for y in yorumlar],
        begeni_sayisi=crud.urun_begeni_sayisi(db, urun_id),
        ortalama_puan=crud.urun_ortalama_puan(db, urun_id),
    )


# SADECE ADMİN: yeni ürün ekleme
# Depends(auth.admin_yetkisi_gerekli) -> bu satır sayesinde, admin
# olmayan biri buraya istek atarsa otomatik olarak 403 hatası alır,
# fonksiyonun içine hiç girmez.
@app.post("/urunler", response_model=schemas.UrunCevap)
def urun_ekle(
    urun: schemas.UrunOlustur,
    db: Session = Depends(get_db),
    admin: models.Kullanici = Depends(auth.admin_yetkisi_gerekli),
):
    return crud.urun_olustur(db, urun)

@app.post("/gorsel-yukle")
def gorsel_yukle(
    dosya: UploadFile = File(...),
    admin: models.Kullanici = Depends(auth.admin_yetkisi_gerekli),
):
    sonuc = cloudinary.uploader.upload(dosya.file)
    return {"fotograf_url": sonuc["secure_url"]}

# SADECE ADMİN: ürün silme
@app.delete("/urunler/{urun_id}")
def urun_kaldir(
    urun_id: int,
    db: Session = Depends(get_db),
    admin: models.Kullanici = Depends(auth.admin_yetkisi_gerekli),
):
    silinen = crud.urun_sil(db, urun_id)
    if not silinen:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")
    return {"mesaj": f"'{silinen.isim}' silindi."}


# --- YORUM ENDPOINT'LERİ ---

# GİRİŞ GEREKLİ: yorum yapmak için kullanıcının kim olduğunu bilmemiz lazım
@app.post("/urunler/{urun_id}/yorumlar", response_model=schemas.YorumCevap)
def yorum_yap(
    urun_id: int,
    yorum: schemas.YorumOlustur,
    db: Session = Depends(get_db),
    su_anki_kullanici: models.Kullanici = Depends(auth.su_anki_kullaniciyi_getir),
):
    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    yeni_yorum = crud.yorum_ekle(db, urun_id, su_anki_kullanici.id, yorum)
    return crud.yorumu_cevaba_donustur(yeni_yorum)


# HERKESE AÇIK: bir ürünün tüm yorumlarını listeleme
@app.get("/urunler/{urun_id}/yorumlar", response_model=list[schemas.YorumCevap])
def urun_yorumlarini_listele(urun_id: int, db: Session = Depends(get_db)):
    yorumlar = crud.urun_yorumlarini_getir(db, urun_id)
    return [crud.yorumu_cevaba_donustur(y) for y in yorumlar]


# --- BEĞENİ ENDPOINT'İ ---
#
# Bunu "toggle" (aç/kapa) mantığıyla kuruyoruz: beğenmemişse beğenir,
# zaten beğenmişse beğeniyi geri çeker. Instagram'daki kalp butonu gibi.
@app.post("/urunler/{urun_id}/begeni")
def urun_begen_veya_begenme_kaldir(
    urun_id: int,
    db: Session = Depends(get_db),
    su_anki_kullanici: models.Kullanici = Depends(auth.su_anki_kullaniciyi_getir),
):
    urun = crud.urun_getir(db, urun_id)
    if not urun:
        raise HTTPException(status_code=404, detail="Ürün bulunamadı.")

    mevcut_begeni = crud.begeni_var_mi(db, urun_id, su_anki_kullanici.id)

    if mevcut_begeni:
        crud.begeni_kaldir(db, mevcut_begeni)
        durum = "kaldirildi"
    else:
        crud.begeni_ekle(db, urun_id, su_anki_kullanici.id)
        durum = "eklendi"

    return {
        "durum": durum,
        "toplam_begeni": crud.urun_begeni_sayisi(db, urun_id),
    }


# --- SİTE İÇİN GİRİŞ/KAYIT/ÇIKIŞ SAYFALARI (COOKIE TABANLI) ---
#
# Buradaki mantık API'dekinden (POST /giris) farklı: form gönderilince
# JSON dönmüyoruz, kullanıcıyı ana sayfaya YÖNLENDİRİYORUZ (redirect)
# ve token'ı bir cookie içine gizlice yerleştiriyoruz. Tarayıcı bu
# cookie'yi otomatik saklayıp her istekte kendisi gönderiyor.

@app.get("/giris-sayfasi")
def giris_sayfasi_goster(request: Request):
    return templates.TemplateResponse(request=request, name="giris.html")


@app.post("/giris-sayfasi")
def giris_formu_isle(
    request: Request,
    email: str = Form(...),
    sifre: str = Form(...),
    db: Session = Depends(get_db),
):
    kullanici = crud.email_ile_kullanici_getir(db, email)

    if not kullanici or not crud.sifre_dogrula(sifre, kullanici.sifre_hash):
        # Hata varsa formu tekrar gösteriyoruz, ama bu sefer hata mesajıyla
        return templates.TemplateResponse(
            request=request,
            name="giris.html",
            context={"hata": "E-posta veya şifre hatalı."},
        )

    token = auth.token_olustur(kullanici.email)

    # Ana sayfaya yönlendiriyoruz VE cevaba bir cookie ekliyoruz.
    # httponly=True -> JavaScript bu cookie'yi okuyamaz, sadece tarayıcı
    # bunu otomatik gönderir. Bu, token'ın çalınmasına karşı bir önlem.
    cevap = RedirectResponse(url="/", status_code=303)
    cevap.set_cookie(key="access_token", value=token, httponly=True, max_age=60 * 60 * 24)
    return cevap


@app.get("/kayit-sayfasi")
def kayit_sayfasi_goster(request: Request):
    return templates.TemplateResponse(request=request, name="kayit.html")


@app.post("/kayit-sayfasi")
def kayit_formu_isle(
    request: Request,
    ad_soyad: str = Form(...),
    email: str = Form(...),
    sifre: str = Form(...),
    kampanya_aboneligi: str = Form(None),
    db: Session = Depends(get_db),
):
    mevcut_kullanici = crud.email_ile_kullanici_getir(db, email)
    if mevcut_kullanici:
        return templates.TemplateResponse(
            request=request,
            name="kayit.html",
            context={"hata": "Bu e-posta zaten kayıtlı."},
        )

    yeni_kullanici_verisi = schemas.KullaniciOlustur(
        ad_soyad=ad_soyad, email=email, sifre=sifre, kampanya_aboneligi=bool(kampanya_aboneligi)
    )
    yeni_kullanici = crud.kullanici_olustur(db, yeni_kullanici_verisi)

    # Kayıt olur olmaz otomatik giriş yaptırıyoruz - kullanıcı deneyimi
    # açısından, tekrar giriş formuna gitmesine gerek yok.
    token = auth.token_olustur(yeni_kullanici.email)
    cevap = RedirectResponse(url="/", status_code=303)
    cevap.set_cookie(key="access_token", value=token, httponly=True, max_age=60 * 60 * 24)
    return cevap


@app.get("/cikis")
def cikis_yap():
    cevap = RedirectResponse(url="/", status_code=303)
    cevap.delete_cookie("access_token")
    return cevap


# --- ADMİN PANELİ (SİTE ÜZERİNDEN, SWAGGER GEREKMİYOR) ---

@app.get("/admin")
def admin_paneli_goster(
    request: Request,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    # Giriş yapmamışsa giriş sayfasına, giriş yapmış ama admin değilse
    # ana sayfaya yönlendiriyoruz. Panel sadece gerçek adminlere açık.
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)
    if not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "urunler": crud.tum_urunleri_getir(db),
            "kategoriler": KATEGORILER,
            "toplam_urun": crud.toplam_urun_sayisi(db),
            "toplam_kullanici": crud.toplam_kullanici_sayisi(db),
            "toplam_yorum": crud.toplam_yorum_sayisi(db),
            "toplam_abone": len(crud.kampanyaya_abone_kullanicilari_getir(db)),
            "mesajlar": crud.tum_mesajlari_getir(db),
            "siparisler": [crud.siparisi_cevaba_donustur(s) for s in crud.tum_siparisleri_getir(db)],
            "durum_secenekleri": crud.DURUM_SIRASI,
            "current_kullanici": su_anki_kullanici,
        },
    )


@app.post("/admin/urun-ekle")
def admin_urun_ekle_formu(
    isim: str = Form(...),
    kategori: str = Form(...),
    fiyat: float = Form(...),
    aciklama: str = Form(""),
    fotograf: UploadFile = File(None),
    stokta_var: str = Form(None),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    fotograf_url = None
    if fotograf and fotograf.filename:
        sonuc = cloudinary.uploader.upload(fotograf.file)
        fotograf_url = sonuc["secure_url"]

    urun_verisi = schemas.UrunOlustur(
        isim=isim,
        kategori=kategori,
        fiyat=fiyat,
        aciklama=aciklama or None,
        fotograf_url=fotograf_url,
        stokta_var=bool(stokta_var),
    )
    crud.urun_olustur(db, urun_verisi)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/urun-sil/{urun_id}")
def admin_urun_sil_formu(
    urun_id: int,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    crud.urun_sil(db, urun_id)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/urun-stok-degistir/{urun_id}")
def admin_urun_stok_degistir(
    urun_id: int,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    crud.urun_stok_durumu_degistir(db, urun_id)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/siparis-durum-guncelle/{siparis_id}")
def admin_siparis_durum_guncelle(
    siparis_id: int,
    yeni_durum: str = Form(...),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    crud.siparis_durum_guncelle(db, siparis_id, yeni_durum)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/siparis-sil/{siparis_id}")
def admin_siparis_sil(
    siparis_id: int,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    crud.siparis_sil(db, siparis_id)
    return RedirectResponse(url="/admin", status_code=303)


@app.post("/admin/kampanya-gonder")
def admin_kampanya_gonder(
    request: Request,
    konu: str = Form(...),
    mesaj: str = Form(...),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        return RedirectResponse(url="/", status_code=303)

    ortak_context = {
        "urunler": crud.tum_urunleri_getir(db),
        "kategoriler": KATEGORILER,
        "toplam_urun": crud.toplam_urun_sayisi(db),
        "toplam_kullanici": crud.toplam_kullanici_sayisi(db),
        "toplam_yorum": crud.toplam_yorum_sayisi(db),
        "toplam_abone": len(crud.kampanyaya_abone_kullanicilari_getir(db)),
        "mesajlar": crud.tum_mesajlari_getir(db),
        "siparisler": [crud.siparisi_cevaba_donustur(s) for s in crud.tum_siparisleri_getir(db)],
        "durum_secenekleri": crud.DURUM_SIRASI,
        "current_kullanici": su_anki_kullanici,
    }

    try:
        sayi = crud.kampanya_maili_gonder(db, konu, mesaj)
        ortak_context["mesaj"] = f"Kampanya maili {sayi} kişiye başarıyla gönderildi."
    except Exception as e:
        ortak_context["hata"] = f"Mail gönderilirken bir hata oluştu: {e}"

    return templates.TemplateResponse(request=request, name="admin.html", context=ortak_context)


# --- PUSH BİLDİRİM UÇLARI ---

import config as app_config


@app.get("/vapid-public-key")
def vapid_public_key_ver():
    # Tarayıcı tarafındaki JavaScript, abone olurken bu public key'e
    # ihtiyaç duyuyor - bunu güvenle herkese açabiliriz, "public" zaten.
    return {"publicKey": app_config.VAPID_PUBLIC_KEY}


@app.post("/push-abone-ol")
def push_abone_ol(
    abonelik: schemas.PushAbonelikOlustur,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici or not su_anki_kullanici.is_admin:
        raise HTTPException(status_code=403, detail="Sadece adminler abone olabilir.")

    crud.push_abonelik_kaydet(db, su_anki_kullanici.id, abonelik)
    return {"mesaj": "Bildirimlere başarıyla abone olundu."}


# --- İLETİŞİM SAYFASI ---

@app.get("/iletisim")
def iletisim_sayfasi_goster(
    request: Request,
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    return templates.TemplateResponse(
        request=request,
        name="iletisim.html",
        context={"current_kullanici": su_anki_kullanici},
    )


@app.post("/iletisim")
def iletisim_formu_isle(
    request: Request,
    ad_soyad: str = Form(...),
    email: str = Form(...),
    mesaj: str = Form(...),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    mesaj_verisi = schemas.IletisimMesajOlustur(ad_soyad=ad_soyad, email=email, mesaj=mesaj)
    crud.mesaj_ekle(db, mesaj_verisi)

    return templates.TemplateResponse(
        request=request,
        name="iletisim.html",
        context={"mesaj_gonderildi": True, "current_kullanici": su_anki_kullanici},
    )


# --- ÖZEL SİPARİŞ SAYFALARI ---

@app.get("/siparis-ver")
def siparis_ver_sayfasi_goster(
    request: Request,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="siparis_ver.html",
        context={
            "urunler": crud.stokta_olan_urunleri_getir(db),
            "current_kullanici": su_anki_kullanici,
        },
    )


@app.post("/siparis-ver")
def siparis_ver_formu_isle(
    request: Request,
    urun_id: int = Form(...),
    miktar: str = Form(...),
    istenilen_tarih: str = Form(...),
    not_metni: str = Form(""),
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    urun = crud.urun_getir(db, urun_id)
    hata_mesaji = None

    if not urun or not urun.stokta_var:
        hata_mesaji = "Seçtiğin ürün şu anda stokta yok, lütfen başka bir ürün seç."
    else:
        # Tarayıcı tarafında da kısıtladık ama sunucu tarafında da
        # doğrulamak şart - biri formu elle (tarayıcı kısıtını atlayarak)
        # gönderirse bile kuralı burada zorlamış oluyoruz.
        try:
            secilen_tarih = date.fromisoformat(istenilen_tarih)
        except ValueError:
            secilen_tarih = None

        if not secilen_tarih or secilen_tarih <= date.today():
            hata_mesaji = "Sipariş tarihi en erken yarın olabilir, bugün veya geçmiş bir tarih seçemezsin."

    if hata_mesaji:
        return templates.TemplateResponse(
            request=request,
            name="siparis_ver.html",
            context={
                "urunler": crud.stokta_olan_urunleri_getir(db),
                "current_kullanici": su_anki_kullanici,
                "hata": hata_mesaji,
            },
        )

    siparis_verisi = schemas.OzelSiparisOlustur(
        urun_id=urun_id, miktar=miktar, istenilen_tarih=istenilen_tarih, not_metni=not_metni or None
    )
    crud.siparis_olustur(db, su_anki_kullanici.id, siparis_verisi)

        # Yeni sipariş geldi - kayıtlı adminlere push bildirimi gönderiyoruz.
    try:
        crud.push_bildirimi_gonder(
            db,
            baslik="Yeni Sipariş!",
            govde=f"{su_anki_kullanici.ad_soyad}, {urun.isim} ({miktar}) siparişi verdi.",
        )
    except Exception as e:
        print(f"[PUSH] Bildirim gönderilemedi: {e}")

    return RedirectResponse(url="/siparislerim", status_code=303)
@app.get("/siparislerim")
def siparislerim_sayfasi(
    request: Request,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    siparisler = crud.kullanicinin_siparisleri(db, su_anki_kullanici.id)

    return templates.TemplateResponse(
        request=request,
        name="siparislerim.html",
        context={
            "siparisler": [crud.siparisi_cevaba_donustur(s) for s in siparisler],
            "current_kullanici": su_anki_kullanici,
        },
    )


@app.get("/favorilerim")
def favorilerim_sayfasi(
    request: Request,
    db: Session = Depends(get_db),
    su_anki_kullanici=Depends(auth.su_anki_kullaniciyi_cookie_ile_getir),
):
    if not su_anki_kullanici:
        return RedirectResponse(url="/giris-sayfasi", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="favorilerim.html",
        context={
            "urunler": crud.kullanicinin_begendigi_urunler(db, su_anki_kullanici.id),
            "current_kullanici": su_anki_kullanici,
        },
    )
"""
schemas.py - API'ye giren ve çıkan verinin "şeklini" tanımlar.

models.py'daki Kullanici sınıfı VERİTABANI tablosunu tanımlıyordu.
Buradaki şemalar ise API isteklerinde/cevaplarında hangi alanların
görüneceğini tanımlıyor. 
"""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime


# Kayıt formunda kullanıcıdan alacağımız veri
class KullaniciOlustur(BaseModel):
    ad_soyad: str
    email: EmailStr  # otomatik olarak "gecerli bir email mi" kontrolü yapar
    sifre: str
    kampanya_aboneligi: bool = True


# API'nin dışarıya, cevap olarak döndüreceği veri (şifre YOK, dikkat et)
class KullaniciCevap(BaseModel):
    id: int
    ad_soyad: str
    email: str
    kayit_tarihi: datetime

    class Config:
        # Bu ayar, SQLAlchemy modelinden (models.Kullanici) doğrudan
        # bu şemaya veri aktarabilmemizi sağlıyor.
        from_attributes = True


# --- ÜRÜN ŞEMALARI ---

class UrunOlustur(BaseModel):
    isim: str
    kategori: str
    fiyat: float
    aciklama: str | None = None
    fotograf_url: str | None = None
    stokta_var: bool = True


class UrunCevap(BaseModel):
    id: int
    isim: str
    kategori: str
    fiyat: float
    aciklama: str | None
    fotograf_url: str | None
    stokta_var: bool
    eklenme_tarihi: datetime

    class Config:
        from_attributes = True


# --- YORUM ŞEMALARI ---

class YorumOlustur(BaseModel):
    metin: str
    # ge=1, le=5 -> "greater or equal 1, less or equal 5" demek,
    # Pydantic otomatik olarak 1-5 dışındaki değerleri reddeder.
    puan: int = Field(ge=1, le=5)


class YorumCevap(BaseModel):
    id: int
    metin: str
    puan: int
    tarih: datetime
    kullanici_id: int
    kullanici_adi: str  # kolaylık olsun diye direkt isim döndüreceğiz

    class Config:
        from_attributes = True


# --- ÜRÜN DETAY CEVABI (yorumlar + beğeni sayısı + ortalama puan dahil) ---

class UrunDetayCevap(UrunCevap):
    yorumlar: list[YorumCevap] = []
    begeni_sayisi: int = 0
    ortalama_puan: float | None = None


# --- İLETİŞİM MESAJI ŞEMALARI ---

class IletisimMesajOlustur(BaseModel):
    ad_soyad: str
    email: EmailStr
    mesaj: str


class IletisimMesajCevap(BaseModel):
    id: int
    ad_soyad: str
    email: str
    mesaj: str
    tarih: datetime
    okundu: bool

    class Config:
        from_attributes = True


# --- ÖZEL SİPARİŞ ŞEMALARI ---

class OzelSiparisOlustur(BaseModel):
    urun_id: int
    miktar: str
    istenilen_tarih: str
    not_metni: str | None = None


class OzelSiparisCevap(BaseModel):
    id: int
    urun_adi: str
    miktar: str
    istenilen_tarih: str
    not_metni: str | None
    durum: str
    olusturma_tarihi: datetime
    kullanici_adi: str

    class Config:
        from_attributes = True


# --- PUSH BİLDİRİM ABONELİK ŞEMASI ---
#
# Bu, tarayıcının bize gönderdiği JSON'ın yapısıyla birebir eşleşiyor:
# { "endpoint": "...", "keys": { "p256dh": "...", "auth": "..." } }

class PushAnahtarlari(BaseModel):
    p256dh: str
    auth: str


class PushAbonelikOlustur(BaseModel):
    endpoint: str
    keys: PushAnahtarlari
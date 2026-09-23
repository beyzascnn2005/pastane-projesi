"""
models.py - Veritabanı tablolarımızın tanımı.

"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class Kullanici(Base):
    __tablename__ = "kullanicilar"

    # Her tabloda otomatik artan bir id (birincil anahtar / primary key)
    id = Column(Integer, primary_key=True, index=True)

    ad_soyad = Column(String, nullable=False)

    # unique=True -> aynı email ile iki kere kayıt olunamaz
    email = Column(String, unique=True, index=True, nullable=False)

    # DİKKAT: Burada şifreyi asla düz metin (plain text) olarak
    # saklamıyoruz! "sifre_hash" adı bilerek böyle - çünkü içine
    # şifrenin kendisi değil, geri döndürülemeyen bir "hash" (özet)
    # değeri kaydedilecek. Bunu main.py'da passlib ile yapacağız.
    sifre_hash = Column(String, nullable=False)

    # Kayıt tarihi otomatik olarak veritabanı tarafından ayarlanır
    kayit_tarihi = Column(DateTime(timezone=True), server_default=func.now())

    # Varsayılan olarak herkes normal kullanıcı (False). Admin (baban)
    # için bunu veritabanında elle True yapacağız - ileride anlatacağım.
    is_admin = Column(Boolean, default=False, nullable=False)

    # Sadakat puanı: her "Teslim Alındı" olan siparişte otomatik +1
    # artacak. Bu bir SAYAÇ - sistem kendi kendine indirim uygulamıyor,
    # sadece takip ediyor. İndirimi verip vermemek babanın kararı.
    sadakat_puani = Column(Integer, default=0, nullable=False)

    # Kullanıcı kayıt olurken "yeni ürün/kampanyalardan haberdar olmak
    # istiyorum" kutucuğunu işaretlerse True olacak.
    kampanya_aboneligi = Column(Boolean, default=True, nullable=False)


class Urun(Base):
    __tablename__ = "urunler"

    id = Column(Integer, primary_key=True, index=True)
    isim = Column(String, nullable=False)

    # kategori: "Dondurma", "Pasta", "Baklava", "Kadayif", "Soguk Baklava"
    # Şimdilik düz metin tutuyoruz, ileride istersen ayrı bir Kategori
    # tablosuna da bölebiliriz ama başlangıç için bu yeterli ve basit.
    kategori = Column(String, nullable=False, index=True)

    fiyat = Column(Float, nullable=False)
    aciklama = Column(String, nullable=True)

    # Fotoğrafın kendisini değil, adresini (URL) tutuyoruz - resimleri
    # ayrı bir yerde (ileride: bir "static" klasöründe) saklayacağız.
    fotograf_url = Column(String, nullable=True)

    stokta_var = Column(Boolean, default=True, nullable=False)
    eklenme_tarihi = Column(DateTime(timezone=True), server_default=func.now())

    # relationship: Python tarafında kolaylık için - bir ürün nesnesi
    # üzerinden "urun.yorumlar" dediğinde o ürünün tüm yorumlarına
    # otomatik erişebiliriz. Veritabanında ekstra bir sütun oluşturmaz,
    # sadece Python'da rahatlık sağlar.
    yorumlar = relationship("Yorum", back_populates="urun", cascade="all, delete-orphan")
    begeniler = relationship("Begeni", back_populates="urun", cascade="all, delete-orphan")


class Yorum(Base):
    __tablename__ = "yorumlar"

    id = Column(Integer, primary_key=True, index=True)

    # ForeignKey: bu satırın hangi kullanıcıya ve hangi ürüne ait
    # olduğunu tutan bağlantı. Kotlin'de bu ilişkiyi Room'da
    # @ForeignKey ile kurmuştun, mantık aynı.
    kullanici_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)

    metin = Column(String, nullable=False)

    # 1-5 arası puan. Veritabanı seviyesinde sınırlamıyoruz,
    # bunu main.py'da (Pydantic ile) kontrol edeceğiz.
    puan = Column(Integer, nullable=False)

    tarih = Column(DateTime(timezone=True), server_default=func.now())

    # Bu iki relationship sayesinde "yorum.kullanici.ad_soyad" ya da
    # "yorum.urun.isim" gibi kolayca erişebileceğiz.
    kullanici = relationship("Kullanici")
    urun = relationship("Urun", back_populates="yorumlar")


class Begeni(Base):
    __tablename__ = "begeniler"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)
    tarih = Column(DateTime(timezone=True), server_default=func.now())

    urun = relationship("Urun", back_populates="begeniler")

    # UniqueConstraint: aynı kullanıcı aynı ürünü İKİ KERE beğenemesin
    # diye veritabanı seviyesinde bir kural koyuyoruz. Biri bunu iki
    # kere denerse veritabanı hata fırlatır, biz de bunu 400 hatasına
    # çevireceğiz main.py'da.
    __table_args__ = (UniqueConstraint("kullanici_id", "urun_id", name="tek_begeni"),)


class IletisimMesaji(Base):
    __tablename__ = "iletisim_mesajlari"

    id = Column(Integer, primary_key=True, index=True)
    ad_soyad = Column(String, nullable=False)
    email = Column(String, nullable=False)
    mesaj = Column(String, nullable=False)
    tarih = Column(DateTime(timezone=True), server_default=func.now())
    okundu = Column(Boolean, default=False, nullable=False)


class OzelSiparis(Base):
    __tablename__ = "ozel_siparisler"

    id = Column(Integer, primary_key=True, index=True)

    kullanici_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    urun_id = Column(Integer, ForeignKey("urunler.id"), nullable=False)

    miktar = Column(String, nullable=False)  # örn: "1 kg", "200 gr", "Orta boy pasta"
    istenilen_tarih = Column(String, nullable=False)  # basitlik için düz metin (örn: "15.06.2026")
    not_metni = Column(String, nullable=True)

    # Durum akışı: "Alindi" -> "Hazirlaniyor" -> "Teslim Alindi"
    durum = Column(String, default="Alindi", nullable=False)

    olusturma_tarihi = Column(DateTime(timezone=True), server_default=func.now())

    kullanici = relationship("Kullanici")
    urun = relationship("Urun")


class PushAbonelik(Base):
    """
    Bir tarayıcının push bildirimi alabilmesi için "abone" olması
    gerekiyor. Admin panelinde "bildirimlere izin ver" dediğinde,
    tarayıcı bize bu 3 bilgiyi (endpoint, p256dh, auth) veriyor -
    bunlar sayesinde ileride o cihaza bildirim gönderebiliyoruz.
    """
    __tablename__ = "push_abonelikleri"

    id = Column(Integer, primary_key=True, index=True)
    kullanici_id = Column(Integer, ForeignKey("kullanicilar.id"), nullable=False)
    endpoint = Column(String, unique=True, nullable=False)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)

    kullanici = relationship("Kullanici")
"""
auth.py - Giriş sonrası verilen "token" (kimlik kartı) mantığı.

Nasıl çalışır (kısaca):
1. Kullanıcı email+şifre ile /giris'e istek atar
2. Şifre doğruysa, ona süresi olan bir JWT token üretip veririz
3. Kullanıcı bundan sonraki her istekte bu token'ı gösterir
   (Authorization header'ında "Bearer <token>" şeklinde)
4. Biz de token'ı çözüp "bu gerçekten giriş yapmış biri mi" diye kontrol ederiz

Bunu neden yapıyoruz, şifreyi her seferinde göndermek yerine?
Çünkü şifreyi her istekte taşımak güvensiz ve pratik değil. Token'ın
süresi var, çalınsa bile sınırlı süre geçerli, ve iptal edilebilir.
"""

from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from database import get_db
import crud

# GERÇEK BİR PROJEDE bu anahtar asla kod içinde açık yazılmaz,
# ortam değişkeni (.env dosyası) ile saklanır. Şimdilik öğrenme
# amaçlı burada tutuyoruz, ileride .env'e taşıyacağız.
import os
GIZLI_ANAHTAR = os.getenv("SECRET_KEY")
if not GIZLI_ANAHTAR:
    raise RuntimeError("SECRET_KEY ortam değişkeni tanımlı değil")
ALGORITMA = "HS256"
TOKEN_GECERLILIK_DAKIKA = 60 * 24  # 1 gün

# Bu satır, FastAPI'ye token'ın nereden bekleneceğini söylüyor
# ("tokenUrl" sadece dokümantasyon/test arayüzü için bir referans)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="giris")


def token_olustur(email: str) -> str:
    """Kullanıcının email'ini içine gömen, süresi dolacak bir token üretir."""
    son_kullanma = datetime.utcnow() + timedelta(minutes=TOKEN_GECERLILIK_DAKIKA)
    veri = {"sub": email, "exp": son_kullanma}
    return jwt.encode(veri, GIZLI_ANAHTAR, algorithm=ALGORITMA)


def su_anki_kullaniciyi_getir(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """
    Bu fonksiyon bir "dependency" - yani korumalı bir endpoint'e
    "bu isteği atan kim, gerçekten giriş yapmış mı" diye sormak
    istediğimizde main.py'da bunu kullanacağız.
    """
    hata = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Kimlik doğrulanamadı, lütfen tekrar giriş yapın.",
    )
    try:
        cozulen = jwt.decode(token, GIZLI_ANAHTAR, algorithms=[ALGORITMA])
        email = cozulen.get("sub")
        if email is None:
            raise hata
    except JWTError:
        raise hata

    kullanici = crud.email_ile_kullanici_getir(db, email)
    if kullanici is None:
        raise hata

    return kullanici


def admin_yetkisi_gerekli(su_anki_kullanici=Depends(su_anki_kullaniciyi_getir)):
    """
    Bu dependency, önce normal giriş kontrolünü (yukarıdaki fonksiyon)
    yapar, SONRA kullanıcının is_admin=True olup olmadığına bakar.
    Admin olmayan biri admin endpoint'lerine erişmeye çalışırsa 403
    (Forbidden - yetkin yok) hatası alır.
    """
    if not su_anki_kullanici.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu işlem için admin yetkisi gerekiyor.",
        )
    return su_anki_kullanici


def su_anki_kullaniciyi_cookie_ile_getir(request: Request, db: Session = Depends(get_db)):
    """
    Swagger/API tarafında token'ı Authorization header'ından okuyorduk
    (su_anki_kullaniciyi_getir fonksiyonu). Web sitesinde ise kullanıcı
    her sayfada elle token yapıştırmayacak - giriş yapınca token'ı
    tarayıcının "cookie" (çerez) hafızasına yazacağız, her istekte
    tarayıcı bunu otomatik gönderecek.

    Bu fonksiyon HATA FIRLATMAZ - giriş yapmamış biri de bu siteyi
    gezebilmeli (misafir olarak). Giriş yapmışsa kullanıcıyı, yapmamışsa
    None döndürür. Sayfalarda "giriş yapmış mı" kontrolü için kullanacağız.
    """
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        cozulen = jwt.decode(token, GIZLI_ANAHTAR, algorithms=[ALGORITMA])
        email = cozulen.get("sub")
        if not email:
            return None
    except JWTError:
        return None

    return crud.email_ile_kullanici_getir(db, email)
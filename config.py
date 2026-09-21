"""
config.py - Push bildirimi için gereken ayarlar.

Bu sefer private key'i kod içinde metin olarak tutmuyoruz - bunun
yerine ayrı bir dosyada (vapid_private.pem) tutuyoruz ve burada
sadece o dosyanın adını belirtiyoruz. Bu, dosya taşırken/kaydederken
oluşabilecek format bozulmalarına karşı daha güvenilir bir yöntem.
"""

VAPID_PRIVATE_KEY_DOSYASI = "vapid_private.pem"

VAPID_PUBLIC_KEY = "BGiz3-0e0uqeVyWsqP-0UA4jVUG8UynSb3xLL-gKLOMKN3cDJcaRe9FIU7pjFst53hFpOYLqkhUiEXv6rDNhbzU"

VAPID_CLAIM_EMAIL = "mailto:pastane-admin@example.com"

# --- E-POSTA (KAMPANYA MAILI) AYARLARI ---
#
# Gmail kullanacaksan: normal şifren DEĞİL, "Uygulama Şifresi" (App
# Password) üretmen gerekiyor. Google hesabı -> Güvenlik -> 2 Adımlı
# Doğrulama (açık olmalı) -> Uygulama Şifreleri -> yeni bir tane oluştur,
# oradaki 16 haneli kodu SMTP_SIFRE alanına yapıştır.
SMTP_SUNUCU = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL ="beyzasecenh@gmail.com"
SMTP_SIFRE ="cdjnzxlrxmzeibjv"
SMTP_GONDEREN_ADI ="Dondurmacı Abdülkerim 🍦"
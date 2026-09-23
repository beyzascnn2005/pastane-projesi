import os

VAPID_PRIVATE_KEY_DOSYASI = "vapid_private.pem"
VAPID_PUBLIC_KEY = "BGiz3-0e0uqeVyWsqP-0UA4jVUG8UynSb3xLL-gKLOMKN3cDJcaRe9FIU7pjFst53hFpOYLqkhUiEXv6rDNhbzU"
VAPID_CLAIM_EMAIL = os.getenv("VAPID_CLAIM_EMAIL", "mailto:pastane-admin@example.com")

SMTP_SUNUCU = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_SIFRE = os.getenv("SMTP_SIFRE")
SMTP_GONDEREN_ADI = "Dondurmacı Abdülkerim 🍦"
"""
admin_yap.py - Bir kullanıcıyı elle admin yapmak için tek seferlik araç.

Kullanımı: terminalde (venv aktifken) şunu çalıştır:
    python admin_yap.py test4@example.com

İleride gerçek bir admin paneli kurunca buna gerek kalmayacak,
ama başlangıçta "ilk admini" oluşturmak için pratik bir yöntem.
"""

import sys
from database import SessionLocal
import models

if len(sys.argv) != 2:
    print("Kullanım: python admin_yap.py <email>")
    sys.exit(1)

email = sys.argv[1]
db = SessionLocal()

kullanici = db.query(models.Kullanici).filter(models.Kullanici.email == email).first()

if not kullanici:
    print(f"'{email}' ile kayıtlı bir kullanıcı bulunamadı.")
else:
    kullanici.is_admin = True
    db.commit()
    print(f"'{email}' artık admin!")

db.close()

"""
database.py - Veritabanı bağlantı ayarları.

Kotlin'deki AppDatabase.kt dosyasının Python karşılığı gibi düşün.
Orada Room + SQLite kullanıyordun, burada SQLAlchemy + SQLite kullanıyoruz.

SQLite: tek bir dosyada duran, kurulum gerektirmeyen basit bir veritabanı.
Küçük/orta projeler ve öğrenme için ideal. İleride istersen PostgreSQL'e
geçiş yapmak da kolay olacak (sadece bu dosyayı değiştirmek yeterli).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Veritabanı dosyamızın adı ve konumu. "sqlite:///./pastane.db" demek,
# proje klasöründe "pastane.db" adında bir dosya oluştur/kullan demek.
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
# "SessionLocal", her istekte veritabanıyla konuşmak için kullanacağımız
# geçici bir "oturum" oluşturan fabrika gibi düşün.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# "Base", tüm tablo modellerimizin (models.py içindeki) miras alacağı
# temel sınıf. Kotlin'de @Entity işaretlemesi gibi düşünebilirsin.
Base = declarative_base()


# Bu fonksiyon, her API isteğinde bir veritabanı oturumu açar,
# iş bitince otomatik kapatır. FastAPI'nin "dependency injection"
# sistemiyle main.py içinde kullanacağız.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
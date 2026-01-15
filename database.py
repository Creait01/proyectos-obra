from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Detectar entorno: usa PostgreSQL en producción, SQLite en local
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Railway usa postgres:// pero SQLAlchemy necesita postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    print(f"✅ Usando PostgreSQL")
else:
    DATABASE_URL = "sqlite:///./proyectos.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    print(f"⚠️ Usando SQLite local")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

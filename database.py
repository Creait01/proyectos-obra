from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Detectar entorno: usa MySQL en producción, SQLite en local
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Producción (Railway) - MySQL
    # Railway usa mysql:// pero SQLAlchemy necesita mysql+pymysql://
    if DATABASE_URL.startswith("mysql://"):
        DATABASE_URL = DATABASE_URL.replace("mysql://", "mysql+pymysql://", 1)
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Local - SQLite
    DATABASE_URL = "sqlite:///./proyectos.db"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

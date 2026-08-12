from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.db.models import Base
from app.db.triggers import setup_immutability_triggers

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

setup_immutability_triggers(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

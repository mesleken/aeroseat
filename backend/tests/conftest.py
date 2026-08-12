import os
import sys
import pytest

# Ensure backend folder is in sys.path
backend_dir = os.path.dirname(os.path.dirname(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.db.database import engine, SessionLocal
from app.db.models import Base
from app.db.init_db import init_db

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create all tables and seed reference data before running tests."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()
    yield

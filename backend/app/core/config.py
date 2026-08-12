import os
from pydantic import BaseModel

class Settings(BaseModel):
    PROJECT_NAME: str = "AeroSeat Certification OS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Storage settings
    STORAGE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage_data")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./aeroseat.db")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

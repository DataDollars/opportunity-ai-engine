import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Opportunity AI Engine"
    
    # Firebase configuration
    FIREBASE_PROJECT_ID: str = "auto-ml-309b9"
    FIREBASE_CREDENTIALS: Optional[str] = None  # Path to service account JSON
    FIREBASE_CREDENTIALS_JSON: Optional[str] = None  # Inline JSON string
    
    # Gemini configurations
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Server configurations
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # App Settings
    SOURCES_JSON_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        "sources.json"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

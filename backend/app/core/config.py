from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path


class Settings(BaseSettings):
    PROJECT_NAME: str = "금융 리서치 코파일럿"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Data paths
    DATA_DIR: str = "../../data"

    # API Keys
    DART_API_KEY: Optional[str] = None

    class Config:
        # backend/.env 파일 경로 설정
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = 'utf-8'
        case_sensitive = True


settings = Settings()

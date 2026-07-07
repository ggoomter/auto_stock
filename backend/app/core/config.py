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

    # 실전 자동매매 스위치 (Phase 1: 브로커 연동 미완성으로 항상 차단)
    ENABLE_LIVE_TRADING: bool = False

    # 페이퍼 트레이딩 (전진 검증) — 가상 계좌 설정
    PAPER_INITIAL_CAPITAL: float = 10_000_000.0  # 원
    PAPER_MAX_POSITIONS: int = 5                 # 균등 배분 1/N

    # SQLite 경로 (테스트에서 주입 가능하도록 설정으로 분리)
    DB_PATH: Optional[str] = None  # None이면 app/db/database.py의 DEFAULT_DB_PATH

    # KRX 정보데이터시스템 계정 (data.krx.co.kr 무료 가입)
    # 2026년 KRX 정책 변경으로 시가총액·펀더멘털 벌크 조회에 로그인 필수 (pykrx 1.2.x)
    KRX_ID: Optional[str] = None
    KRX_PW: Optional[str] = None

    class Config:
        # backend/.env 파일 경로 설정
        env_file = str(Path(__file__).parent.parent.parent / ".env")
        env_file_encoding = 'utf-8'
        case_sensitive = True


settings = Settings()

# pykrx는 os.environ에서 KRX_ID/KRX_PW를 읽으므로 .env 값을 환경변수로 전파한다
if settings.KRX_ID and not os.environ.get("KRX_ID"):
    os.environ["KRX_ID"] = settings.KRX_ID
if settings.KRX_PW and not os.environ.get("KRX_PW"):
    os.environ["KRX_PW"] = settings.KRX_PW

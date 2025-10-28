"""
일별 로그 설정
"""
import logging
import sys
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime


def setup_logging():
    """로깅 설정 - 일별 로그 파일 생성"""

    # 로그 디렉토리 생성
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)

    # 로거 설정
    logger = logging.getLogger("auto_stock")
    logger.setLevel(logging.INFO)

    # 포맷터
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 파일 핸들러 - 일별 로그 (경고/에러만)
    file_handler = TimedRotatingFileHandler(
        filename=log_dir / "app.log",
        when="midnight",  # 자정에 새 파일 생성
        interval=1,
        backupCount=30,  # 30일치 보관
        encoding="utf-8"
    )
    file_handler.setLevel(logging.WARNING)  # 경고, 에러만 파일에 저장
    file_handler.setFormatter(formatter)
    file_handler.suffix = "%Y-%m-%d"  # 파일명에 날짜 추가

    # 핸들러 추가
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


# 전역 로거 생성
logger = setup_logging()

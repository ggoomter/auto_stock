"""
SQLite 영속화 계층 (표준 sqlite3 사용, 외부 의존성 없음)
모의투자 포지션/체결, 일별 스냅샷, 뉴스, 추천, 작업 실행 기록을 저장한다.
"""
import sqlite3
from pathlib import Path

# backend/data/auto_stock.db (.gitignore의 *.db 패턴으로 커밋 제외됨)
DEFAULT_DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "auto_stock.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    entry_price REAL NOT NULL,
    entry_at TEXT NOT NULL,
    strategy TEXT NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    highest_price REAL,
    status TEXT NOT NULL DEFAULT 'open',
    exit_price REAL,
    exit_at TEXT,
    exit_reason TEXT
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER REFERENCES paper_positions(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price REAL NOT NULL,
    executed_at TEXT NOT NULL,
    strategy TEXT,
    reason TEXT
);

CREATE TABLE IF NOT EXISTS portfolio_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL UNIQUE,
    total_value REAL NOT NULL,
    cash REAL NOT NULL,
    positions_value REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS news_articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    published_at TEXT NOT NULL,
    source TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL UNIQUE,
    summary TEXT,
    sentiment TEXT NOT NULL DEFAULT 'neutral'
);

CREATE TABLE IF NOT EXISTS news_stock_links (
    article_id INTEGER NOT NULL REFERENCES news_articles(id),
    symbol TEXT NOT NULL,
    PRIMARY KEY (article_id, symbol)
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rec_date TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT,
    score REAL NOT NULL,
    passed_conditions TEXT,
    technical_signals TEXT,
    UNIQUE (rec_date, symbol)
);

CREATE TABLE IF NOT EXISTS job_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_name TEXT NOT NULL,
    run_date TEXT NOT NULL,
    status TEXT NOT NULL,
    detail TEXT,
    finished_at TEXT NOT NULL,
    UNIQUE (job_name, run_date)
);
"""


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Row factory가 설정된 커넥션 반환. 호출자가 close 책임을 가진다."""
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str | None = None) -> None:
    """스키마 생성 (멱등). 앱 기동 시 1회 호출."""
    conn = get_connection(db_path)
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
    finally:
        conn.close()

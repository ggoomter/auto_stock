# Phase 1: DB 기반 + 모의투자 영속화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** SQLite 영속화 계층을 만들고, 실전(LIVE) 매매를 차단하고, 모의투자(paper trading)를 재시작해도 살아남는 정직한 시뮬레이션으로 수리한다.

**Architecture:** Python 표준 `sqlite3` 기반 경량 저장소 계층(`backend/app/db/`)을 신설한다. `AutoTradingEngine`의 메모리 포지션을 DB와 동기화하고, 랜덤 슬리피지 체결을 호가단위 기반 결정적 체결로, Kelly 사이징을 1/N 균등 배분으로 교체한다. LIVE 모드는 API 계층에서 403으로 거부한다.

**Tech Stack:** FastAPI, sqlite3(stdlib), pytest(신규 dev 의존성), 기존 `tick_size.py` 유틸 재사용.

**Spec:** `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md`

## Global Constraints

- 새 런타임 외부 의존성 금지. DB는 Python 표준 `sqlite3`만 사용. (dev 의존성으로 pytest만 추가 허용)
- 실전(LIVE) 모드: `/api/v1/trading/start`에서 `mode == "live"` 요청은 **403** + 메시지 "실전 모드는 비활성화되어 있습니다".
- 가상 체결: 매수 = 호가단위 **올림**, 매도 = 호가단위 **내림** (`app/utils/tick_size.py`의 `round_to_tick_up/round_to_tick_down` 재사용). `np.random` 사용 금지.
- 포지션 사이징: Kelly 제거, 균등 배분 `총자본 / max_positions`.
- DB 파일: `backend/data/auto_stock.db` (`.gitignore`의 `*.db` 패턴으로 이미 제외됨 — 확인 완료).
- 모든 pytest 명령은 `backend/` 디렉토리에서 `venv\Scripts\python -m pytest ...`로 실행 (이렇게 해야 `app` 패키지가 import됨).
- 커밋 메시지는 `<type>: <설명>` 한국어. Co-Authored-By 등 attribution 금지.
- 조용한 기본값 대체 금지: 외부 데이터 실패 시 None/빈 값을 명시적으로 반환하고 로그를 남긴다.

---

### Task 1: 테스트 인프라 + DB 스키마

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/app/db/__init__.py`
- Create: `backend/app/db/database.py`
- Test: `backend/tests/__init__.py`, `backend/tests/unit/__init__.py`, `backend/tests/unit/test_database.py`

**Interfaces:**
- Produces: `get_connection(db_path: str | None = None) -> sqlite3.Connection` (row_factory=sqlite3.Row), `init_db(db_path: str | None = None) -> None` (7개 테이블 CREATE IF NOT EXISTS, 멱등), `DEFAULT_DB_PATH: str`
- 이후 모든 저장소(Task 2, 3)와 `main.py`(Task 8)가 이 모듈에 의존한다.

- [ ] **Step 1: dev 의존성 파일 생성 및 pytest 설치**

`backend/requirements-dev.txt`:
```text
pytest>=8.0
```

Run (backend/ 에서): `venv\Scripts\pip install -r requirements-dev.txt`
Expected: `Successfully installed pytest-8.x ...`

- [ ] **Step 2: 실패하는 테스트 작성**

`backend/tests/__init__.py`, `backend/tests/unit/__init__.py`: 빈 파일.

`backend/tests/unit/test_database.py`:
```python
"""DB 스키마 초기화 테스트"""
import sqlite3


def test_init_db_creates_all_tables(tmp_path):
    from app.db.database import init_db, get_connection

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()

    table_names = {row["name"] for row in rows}
    expected = {
        "paper_positions", "paper_trades", "portfolio_snapshots",
        "news_articles", "news_stock_links", "recommendations", "job_runs",
    }
    assert expected.issubset(table_names)


def test_init_db_is_idempotent(tmp_path):
    from app.db.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    init_db(db_path)  # 두 번 호출해도 예외 없어야 함


def test_get_connection_uses_row_factory(tmp_path):
    from app.db.database import init_db, get_connection

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO job_runs (job_name, run_date, status, finished_at) "
        "VALUES ('t', '2026-07-02', 'success', '2026-07-02T10:00:00')"
    )
    row = conn.execute("SELECT job_name FROM job_runs").fetchone()
    conn.close()
    assert row["job_name"] == "t"  # dict 스타일 접근 = Row factory 확인
```

- [ ] **Step 3: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_database.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`

- [ ] **Step 4: 구현**

`backend/app/db/__init__.py`: 빈 파일.

`backend/app/db/database.py`:
```python
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
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_database.py -v`
Expected: 3 passed

- [ ] **Step 6: 커밋**

```bash
git add backend/requirements-dev.txt backend/app/db/ backend/tests/
git commit -m "feat: SQLite 영속화 계층 및 스키마 추가 (모의투자/뉴스/추천/작업기록)"
```

---

### Task 2: 모의투자 저장소 (PaperTradingRepository)

**Files:**
- Create: `backend/app/db/repositories.py`
- Test: `backend/tests/unit/test_paper_repository.py`

**Interfaces:**
- Consumes: `app.db.database.get_connection`, `init_db`
- Produces: `PaperTradingRepository(db_path: str | None = None)`:
  - `open_position(symbol: str, quantity: int, entry_price: float, strategy: str, stop_loss: float, take_profit: float, entry_at: str) -> int` (position_id 반환, 동시에 paper_trades에 buy 체결 기록)
  - `close_position(position_id: int, exit_price: float, exit_reason: str, exit_at: str) -> None` (status='closed' + paper_trades에 sell 체결 기록)
  - `list_open_positions() -> list[dict]` (키: id, symbol, quantity, entry_price, entry_at, strategy, stop_loss, take_profit, highest_price)
  - `update_stops(position_id: int, stop_loss: float, highest_price: float) -> None`
  - `list_trades() -> list[dict]`
- Task 7(엔진 영속화)이 이 클래스를 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_paper_repository.py`:
```python
"""모의투자 포지션 저장소 테스트"""
import pytest

from app.db.database import init_db


@pytest.fixture
def repo(tmp_path):
    from app.db.repositories import PaperTradingRepository
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return PaperTradingRepository(db_path)


def test_open_position_returns_id_and_records_buy_trade(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    assert isinstance(pos_id, int)

    open_positions = repo.list_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0]["symbol"] == "005930.KS"
    assert open_positions[0]["quantity"] == 10
    assert open_positions[0]["highest_price"] == 71000.0  # 진입 시 최고가 = 진입가

    trades = repo.list_trades()
    assert len(trades) == 1
    assert trades[0]["side"] == "buy"
    assert trades[0]["price"] == 71000.0


def test_close_position_removes_from_open_and_records_sell(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    repo.close_position(pos_id, exit_price=85000.0,
                        exit_reason="익절매", exit_at="2026-07-03T11:00:00")

    assert repo.list_open_positions() == []
    trades = repo.list_trades()
    assert len(trades) == 2
    sell = [t for t in trades if t["side"] == "sell"][0]
    assert sell["price"] == 85000.0
    assert sell["reason"] == "익절매"


def test_update_stops(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    repo.update_stops(pos_id, stop_loss=70000.0, highest_price=74000.0)

    pos = repo.list_open_positions()[0]
    assert pos["stop_loss"] == 70000.0
    assert pos["highest_price"] == 74000.0


def test_open_positions_survive_new_repository_instance(repo, tmp_path):
    """재시작 시나리오: 새 저장소 인스턴스에서도 open 포지션 조회 가능"""
    from app.db.repositories import PaperTradingRepository
    repo.open_position(
        symbol="000660.KS", quantity=5, entry_price=200000.0,
        strategy="lynch", stop_loss=180000.0, take_profit=260000.0,
        entry_at="2026-07-02T10:00:00",
    )
    fresh = PaperTradingRepository(str(tmp_path / "test.db"))
    assert len(fresh.list_open_positions()) == 1
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_paper_repository.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `ImportError: cannot import name 'PaperTradingRepository'`

- [ ] **Step 3: 구현**

`backend/app/db/repositories.py`:
```python
"""
저장소 계층: 호출마다 커넥션을 열고 닫는다 (스레드 안전, 단순함 우선).
"""
from .database import get_connection


class PaperTradingRepository:
    """모의투자 포지션·체결 영속화"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def open_position(self, symbol: str, quantity: int, entry_price: float,
                      strategy: str, stop_loss: float, take_profit: float,
                      entry_at: str) -> int:
        conn = get_connection(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO paper_positions "
                "(symbol, quantity, entry_price, entry_at, strategy, "
                " stop_loss, take_profit, highest_price, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')",
                (symbol, quantity, entry_price, entry_at, strategy,
                 stop_loss, take_profit, entry_price),
            )
            position_id = cur.lastrowid
            conn.execute(
                "INSERT INTO paper_trades "
                "(position_id, symbol, side, quantity, price, executed_at, strategy, reason) "
                "VALUES (?, ?, 'buy', ?, ?, ?, ?, '진입')",
                (position_id, symbol, quantity, entry_price, entry_at, strategy),
            )
            conn.commit()
            return position_id
        finally:
            conn.close()

    def close_position(self, position_id: int, exit_price: float,
                       exit_reason: str, exit_at: str) -> None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT symbol, quantity, strategy FROM paper_positions WHERE id = ?",
                (position_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"포지션 없음: id={position_id}")
            conn.execute(
                "UPDATE paper_positions "
                "SET status='closed', exit_price=?, exit_at=?, exit_reason=? "
                "WHERE id = ?",
                (exit_price, exit_at, exit_reason, position_id),
            )
            conn.execute(
                "INSERT INTO paper_trades "
                "(position_id, symbol, side, quantity, price, executed_at, strategy, reason) "
                "VALUES (?, ?, 'sell', ?, ?, ?, ?, ?)",
                (position_id, row["symbol"], row["quantity"], exit_price,
                 exit_at, row["strategy"], exit_reason),
            )
            conn.commit()
        finally:
            conn.close()

    def list_open_positions(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, symbol, quantity, entry_price, entry_at, strategy, "
                "       stop_loss, take_profit, highest_price "
                "FROM paper_positions WHERE status = 'open' ORDER BY id",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_stops(self, position_id: int, stop_loss: float,
                     highest_price: float) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "UPDATE paper_positions SET stop_loss=?, highest_price=? WHERE id=?",
                (stop_loss, highest_price, position_id),
            )
            conn.commit()
        finally:
            conn.close()

    def list_trades(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, position_id, symbol, side, quantity, price, "
                "       executed_at, strategy, reason "
                "FROM paper_trades ORDER BY id",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_paper_repository.py -v`
Expected: 4 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/db/repositories.py backend/tests/unit/test_paper_repository.py
git commit -m "feat: 모의투자 포지션·체결 저장소 추가"
```

---

### Task 3: 작업 기록·스냅샷 저장소 (JobRunRepository, SnapshotRepository)

**Files:**
- Modify: `backend/app/db/repositories.py` (클래스 2개 추가)
- Test: `backend/tests/unit/test_job_and_snapshot_repository.py`

**Interfaces:**
- Consumes: `app.db.database.get_connection`
- Produces:
  - `JobRunRepository(db_path)`: `record(job_name: str, run_date: str, status: str, detail: str | None = None, finished_at: str = "") -> None` (INSERT OR REPLACE), `has_succeeded(job_name: str, run_date: str) -> bool`
  - `SnapshotRepository(db_path)`: `save(snapshot_date: str, total_value: float, cash: float, positions_value: float) -> None` (INSERT OR REPLACE — 같은 날 여러 번 저장 시 마지막 값 유지), `list_all() -> list[dict]`
- Task 8(스냅샷)과 Phase 3(catch-up 오케스트레이터)이 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_job_and_snapshot_repository.py`:
```python
"""작업 기록·스냅샷 저장소 테스트"""
import pytest

from app.db.database import init_db


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_job_run_record_and_check(db_path):
    from app.db.repositories import JobRunRepository
    repo = JobRunRepository(db_path)

    assert repo.has_succeeded("news_crawl", "2026-07-02") is False

    repo.record("news_crawl", "2026-07-02", "failure",
                detail="timeout", finished_at="2026-07-02T09:00:00")
    assert repo.has_succeeded("news_crawl", "2026-07-02") is False

    # 실패 후 재시도 성공 → REPLACE 되어야 함
    repo.record("news_crawl", "2026-07-02", "success",
                finished_at="2026-07-02T09:05:00")
    assert repo.has_succeeded("news_crawl", "2026-07-02") is True


def test_snapshot_save_is_upsert(db_path):
    from app.db.repositories import SnapshotRepository
    repo = SnapshotRepository(db_path)

    repo.save("2026-07-02", total_value=10_000_000, cash=5_000_000,
              positions_value=5_000_000)
    repo.save("2026-07-02", total_value=10_100_000, cash=5_000_000,
              positions_value=5_100_000)  # 같은 날 재저장

    snapshots = repo.list_all()
    assert len(snapshots) == 1
    assert snapshots[0]["total_value"] == 10_100_000
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_job_and_snapshot_repository.py -v`
Expected: FAIL — `ImportError: cannot import name 'JobRunRepository'`

- [ ] **Step 3: 구현 — `repositories.py` 끝에 추가**

```python
class JobRunRepository:
    """일별 작업 실행 기록 — '오늘 이미 돌았나' 판단 근거"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def record(self, job_name: str, run_date: str, status: str,
               detail: str | None = None, finished_at: str = "") -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO job_runs "
                "(job_name, run_date, status, detail, finished_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (job_name, run_date, status, detail, finished_at),
            )
            conn.commit()
        finally:
            conn.close()

    def has_succeeded(self, job_name: str, run_date: str) -> bool:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM job_runs "
                "WHERE job_name=? AND run_date=? AND status='success'",
                (job_name, run_date),
            ).fetchone()
            return row is not None
        finally:
            conn.close()


class SnapshotRepository:
    """일별 가상 잔고 스냅샷 — 모의투자 수익 곡선의 원천"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def save(self, snapshot_date: str, total_value: float, cash: float,
             positions_value: float) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO portfolio_snapshots "
                "(snapshot_date, total_value, cash, positions_value) "
                "VALUES (?, ?, ?, ?)",
                (snapshot_date, total_value, cash, positions_value),
            )
            conn.commit()
        finally:
            conn.close()

    def list_all(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT snapshot_date, total_value, cash, positions_value "
                "FROM portfolio_snapshots ORDER BY snapshot_date",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_job_and_snapshot_repository.py -v`
Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/db/repositories.py backend/tests/unit/test_job_and_snapshot_repository.py
git commit -m "feat: 작업 실행 기록·일별 스냅샷 저장소 추가"
```

---

### Task 4: 실전(LIVE) 모드 차단

**Files:**
- Modify: `backend/app/core/config.py` (설정 플래그 추가)
- Modify: `backend/app/api/trading_routes.py:112-131` (start_trading 앞부분)
- Test: `backend/tests/unit/test_live_mode_blocked.py`

**Interfaces:**
- Consumes: `app.core.config.settings`
- Produces: `settings.ENABLE_LIVE_TRADING: bool = False`. `/trading/start`는 `mode=="live"`이고 플래그가 False면 403.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_live_mode_blocked.py`:
```python
"""실전 모드 차단 테스트 — 무인증 실전 주문 진입을 막는 안전장치"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_live_mode_returns_403():
    response = client.post("/api/v1/trading/start", json={"mode": "live"})
    assert response.status_code == 403
    assert "실전 모드" in response.json()["detail"]


def test_invalid_mode_returns_422():
    response = client.post("/api/v1/trading/start", json={"mode": "yolo"})
    assert response.status_code == 422
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_live_mode_blocked.py -v`
Expected: FAIL — live 요청이 403이 아니라 200(시작됨)으로 응답

주의: 이 테스트는 `app.main` import로 무거운 모듈(yfinance 등)을 로드하므로 첫 실행이 느릴 수 있다(네트워크 호출은 없음).

- [ ] **Step 3: 구현**

`backend/app/core/config.py` — `DART_API_KEY` 아래에 추가:
```python
    # 실전 자동매매 스위치 (Phase 1: 브로커 연동 미완성으로 항상 차단)
    ENABLE_LIVE_TRADING: bool = False

    # SQLite 경로 (테스트에서 주입 가능하도록 설정으로 분리)
    DB_PATH: Optional[str] = None  # None이면 app/db/database.py의 DEFAULT_DB_PATH
```

`backend/app/api/trading_routes.py` — 파일 상단 import에 추가:
```python
from ..core.config import settings
```

`start_trading` 내부, `if _is_running:` 체크 **앞**에 추가:
```python
        # mode 값 검증 (paper/live 외 거부)
        if request.mode not in ("paper", "live"):
            raise HTTPException(status_code=422, detail=f"지원하지 않는 모드: {request.mode}")

        # 실전 모드 차단: 브로커 주문 경로(buy_stock/sell_stock 부재)가 미완성이라
        # 실행 시 크래시함. 수리 전까지 서버 설정으로 봉인한다.
        if request.mode == "live" and not settings.ENABLE_LIVE_TRADING:
            raise HTTPException(
                status_code=403,
                detail="실전 모드는 비활성화되어 있습니다 (paper 모드만 지원)"
            )
```

기존 `if request.mode == "live": logger.warning(...)` 블록은 유지 (플래그를 켠 미래 시점 대비).

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_live_mode_blocked.py -v`
Expected: 2 passed

- [ ] **Step 5: 커밋**

```bash
git add backend/app/core/config.py backend/app/api/trading_routes.py backend/tests/unit/test_live_mode_blocked.py
git commit -m "feat: 실전(LIVE) 자동매매 모드 차단 (ENABLE_LIVE_TRADING 플래그, 기본 False)"
```

---

### Task 5: 가상 체결 규칙 — 호가단위 기반 결정적 체결

**Files:**
- Create: `backend/app/services/paper_execution.py`
- Test: `backend/tests/unit/test_paper_execution.py`

**Interfaces:**
- Consumes: `app.utils.tick_size.round_to_tick_up`, `round_to_tick_down`
- Produces:
  - `is_korean_symbol(symbol: str) -> bool` (".KS"/".KQ" 접미사 또는 6자리 숫자)
  - `simulate_fill_price(price: float, side: str, slippage: float, symbol: str) -> float` — 매수: `price*(1+slippage)` 후 호가단위 올림, 매도: `price*(1-slippage)` 후 호가단위 내림. `side`는 "buy"/"sell"만 허용, 그 외 ValueError.
- Task 7에서 엔진의 `np.random` 체결을 이 함수로 교체한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_paper_execution.py`:
```python
"""가상 체결 규칙 테스트 — 결정적(랜덤 없음), 보수적(매수 올림/매도 내림)"""
import pytest


def test_is_korean_symbol():
    from app.services.paper_execution import is_korean_symbol
    assert is_korean_symbol("005930.KS") is True
    assert is_korean_symbol("035720.KQ") is True
    assert is_korean_symbol("005930") is True
    assert is_korean_symbol("AAPL") is False


def test_buy_fill_rounds_up_to_tick():
    from app.services.paper_execution import simulate_fill_price
    # 27,000원 매수 + 0.15% 슬리피지 = 27,040.5 → 호가단위 50원 올림 = 27,050
    fill = simulate_fill_price(27000.0, "buy", 0.0015, "005930.KS")
    assert fill == 27050.0


def test_sell_fill_rounds_down_to_tick():
    from app.services.paper_execution import simulate_fill_price
    # 27,000원 매도 - 0.15% 슬리피지 = 26,959.5 → 내림 = 26,950
    fill = simulate_fill_price(27000.0, "sell", 0.0015, "005930.KS")
    assert fill == 26950.0


def test_fill_is_deterministic():
    from app.services.paper_execution import simulate_fill_price
    fills = {simulate_fill_price(27000.0, "buy", 0.0015, "005930.KS")
             for _ in range(20)}
    assert len(fills) == 1  # 랜덤 요소 없음


def test_invalid_side_raises():
    from app.services.paper_execution import simulate_fill_price
    with pytest.raises(ValueError):
        simulate_fill_price(27000.0, "hold", 0.0015, "005930.KS")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_paper_execution.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.paper_execution'`

- [ ] **Step 3: 구현**

`backend/app/services/paper_execution.py`:
```python
"""
모의투자 가상 체결 규칙.
실제 호가/체결을 모사할 수 없으므로 보수적 결정론으로 대체한다:
매수는 불리하게(슬리피지 가산 후 호가단위 올림), 매도도 불리하게(차감 후 내림).
"""
from ..utils.tick_size import round_to_tick_up, round_to_tick_down


def is_korean_symbol(symbol: str) -> bool:
    """한국 종목 여부: .KS/.KQ 접미사 또는 6자리 숫자 코드"""
    if symbol.endswith(".KS") or symbol.endswith(".KQ"):
        return True
    return symbol.isdigit() and len(symbol) == 6


def simulate_fill_price(price: float, side: str, slippage: float,
                        symbol: str) -> float:
    """보수적 가상 체결가 계산. side는 'buy' 또는 'sell'."""
    korean = is_korean_symbol(symbol)
    if side == "buy":
        return round_to_tick_up(price * (1 + slippage), korean)
    if side == "sell":
        return round_to_tick_down(price * (1 - slippage), korean)
    raise ValueError(f"지원하지 않는 side: {side}")
```

주의: `app/utils/tick_size.py`의 실제 함수 시그니처가 `round_to_tick_up(price, is_korean)`과 다르면(예: 키워드 이름 상이) 이 파일을 그쪽에 맞춰 조정하라. 미국 종목(`is_korean=False`)은 tick_size 유틸의 기존 동작(소수점 그대로 또는 센트 단위)을 따른다 — 이 동작을 바꾸지 말 것.

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_paper_execution.py -v`
Expected: 5 passed. (호가단위 경계값이 tick_size 구현과 다르면 tick_size 쪽이 정답 — 테스트 기대값을 CLAUDE.md의 호가단위 표 기준으로 재검증할 것: 10,000~50,000원 구간은 50원 단위)

- [ ] **Step 5: 커밋**

```bash
git add backend/app/services/paper_execution.py backend/tests/unit/test_paper_execution.py
git commit -m "feat: 호가단위 기반 결정적 가상 체결 규칙 추가"
```

---

### Task 6: 포지션 사이징 — Kelly 제거, 1/N 균등 배분

**Files:**
- Modify: `backend/app/services/paper_execution.py` (함수 1개 추가)
- Modify: `backend/app/services/auto_trading_engine.py:300-324` (`_check_entry_signal`의 사이징 부분)
- Test: `backend/tests/unit/test_position_sizing.py`

**Interfaces:**
- Produces: `calculate_equal_weight_shares(total_capital: float, max_positions: int, entry_price: float) -> int` — `int(total_capital / max_positions / entry_price)`, 0 이하 방지(최소 0 반환), entry_price<=0이면 0.
- 엔진의 `TradingSignal.position_size` 산정이 이 함수를 사용한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_position_sizing.py`:
```python
"""1/N 균등 배분 사이징 테스트"""


def test_equal_weight_basic():
    from app.services.paper_execution import calculate_equal_weight_shares
    # 1,000만원 / 5포지션 = 200만원 / 71,000원 = 28.16주 → 28주
    assert calculate_equal_weight_shares(10_000_000, 5, 71000.0) == 28


def test_equal_weight_never_negative_or_fractional():
    from app.services.paper_execution import calculate_equal_weight_shares
    assert calculate_equal_weight_shares(100_000, 5, 71000.0) == 0  # 예산 부족
    assert calculate_equal_weight_shares(10_000_000, 5, 0) == 0     # 가격 오류 방어
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_position_sizing.py -v`
Expected: FAIL — `ImportError: cannot import name 'calculate_equal_weight_shares'`

- [ ] **Step 3: 구현 — `paper_execution.py` 끝에 추가**

```python
def calculate_equal_weight_shares(total_capital: float, max_positions: int,
                                  entry_price: float) -> int:
    """균등 배분(1/N) 주식 수. 근거 없는 Kelly 추정치 대신 설명 가능한 단순 규칙."""
    if entry_price <= 0 or max_positions <= 0:
        return 0
    budget_per_position = total_capital / max_positions
    return max(0, int(budget_per_position / entry_price))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_position_sizing.py -v`
Expected: 2 passed

- [ ] **Step 5: 엔진 연결 — `auto_trading_engine.py` 수정**

파일 상단 import에 추가:
```python
from .paper_execution import simulate_fill_price, calculate_equal_weight_shares
```

`_check_entry_signal`에서 아래 블록(현재 300-324행 부근)을:
```python
                # 포지션 크기 계산
                sizing_result = self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    entry_price=current_price,
                    stop_loss=current_price * (1 - risk_params.stop_pct),
                    strategy_win_rate=0.5,  # 추후 백테스트 결과 연동 필요
                    avg_win_loss_ratio=2.0,
                    current_positions=list(self.active_positions.values())
                )

                return TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="buy",
                    strategy_name=strategy_name,
                    confidence=0.8,
                    entry_price=current_price,
                    stop_loss=sizing_result.손절가,
                    take_profit=sizing_result.목표가,
                    position_size=sizing_result.추천_주식수,
                    reason=f"{strategy_name} 진입 조건 충족"
                )
```

다음으로 교체:
```python
                # 포지션 크기: 1/N 균등 배분 (Kelly는 승률 하드코딩 문제로 제거)
                position_size = calculate_equal_weight_shares(
                    total_capital=self.config.total_capital,
                    max_positions=self.config.max_positions,
                    entry_price=current_price,
                )
                if position_size <= 0:
                    return None  # 예산 부족 시 진입하지 않음

                return TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="buy",
                    strategy_name=strategy_name,
                    confidence=0.8,
                    entry_price=current_price,
                    stop_loss=current_price * (1 - risk_params.stop_pct),
                    take_profit=current_price * (1 + risk_params.take_pct),
                    position_size=position_size,
                    reason=f"{strategy_name} 진입 조건 충족"
                )
```

주의: `risk_params.take_pct` 속성명은 `master_strategies.py`의 `get_risk_params()` 반환 객체 기준으로 확인하라(`stop_pct`는 기존 코드 307행에서 사용 중이므로 존재 확인됨). 이름이 다르면 실제 이름을 쓸 것.

- [ ] **Step 6: 전체 테스트 회귀 확인**

Run: `venv\Scripts\python -m pytest tests/unit -v`
Expected: 전부 passed (엔진 import 오류 없어야 함)

- [ ] **Step 7: 커밋**

```bash
git add backend/app/services/paper_execution.py backend/app/services/auto_trading_engine.py backend/tests/unit/test_position_sizing.py
git commit -m "feat: 포지션 사이징을 1/N 균등 배분으로 교체 (하드코딩 Kelly 제거)"
```

---

### Task 7: 엔진 영속화 — 포지션이 재시작에서 살아남게

**Files:**
- Modify: `backend/app/services/auto_trading_engine.py` (`__init__`, `_execute_order`)
- Test: `backend/tests/unit/test_engine_persistence.py`

**Interfaces:**
- Consumes: `PaperTradingRepository` (Task 2), `simulate_fill_price` (Task 5)
- Produces: `AutoTradingEngine(config, db_path: str | None = None)` — 생성 시 open 포지션을 DB에서 `active_positions`로 복원. 매수 체결 시 `open_position` 기록(반환 id를 포지션 dict의 `"position_id"`에 보관), 매도 체결 시 `close_position` 기록. 메모리 dict는 유지(런타임 캐시), DB가 진실의 원천.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_engine_persistence.py`:
```python
"""엔진 영속화 테스트 — 매수/매도가 DB에 기록되고 재시작 시 복원되는가"""
import asyncio
from datetime import datetime

import pytest

from app.db.database import init_db


def _make_engine(db_path):
    from app.services.auto_trading_engine import (
        AutoTradingEngine, AutoTradingConfig, TradingMode,
    )
    config = AutoTradingConfig(mode=TradingMode.PAPER, total_capital=10_000_000)
    return AutoTradingEngine(config, db_path=db_path)


def _buy_signal():
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="buy",
        strategy_name="buffett", confidence=0.8, entry_price=71000.0,
        stop_loss=65000.0, take_profit=85000.0, position_size=10,
        reason="테스트 진입",
    )


def _sell_signal(shares):
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="sell",
        strategy_name="buffett", confidence=1.0, entry_price=80000.0,
        stop_loss=0, take_profit=0, position_size=shares, reason="익절매",
    )


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_buy_persists_and_restores_after_restart(db_path):
    engine = _make_engine(db_path)
    order = asyncio.run(engine._execute_order(_buy_signal()))
    assert order is not None and order.status.value == "filled"
    assert "005930.KS" in engine.active_positions
    assert "position_id" in engine.active_positions["005930.KS"]

    # 재시작 시뮬레이션: 새 엔진 인스턴스가 DB에서 복원
    engine2 = _make_engine(db_path)
    assert "005930.KS" in engine2.active_positions
    restored = engine2.active_positions["005930.KS"]
    assert restored["shares"] == 10
    assert restored["strategy"] == "buffett"


def test_sell_closes_position_in_db(db_path):
    from app.db.repositories import PaperTradingRepository
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    shares = engine.active_positions["005930.KS"]["shares"]
    asyncio.run(engine._execute_order(_sell_signal(shares)))

    assert "005930.KS" not in engine.active_positions
    repo = PaperTradingRepository(db_path)
    assert repo.list_open_positions() == []
    sides = [t["side"] for t in repo.list_trades()]
    assert sides == ["buy", "sell"]


def test_paper_fill_uses_tick_rounding_not_random(db_path):
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    fill = engine.active_positions["005930.KS"]["entry_price"]
    # 71,000원 * (1+0.01 슬리피지 기본값) = 71,710 → 100원 단위 올림 = 71,800
    # (50,000~100,000원 구간 호가단위 100원)
    assert fill == 71800.0
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_engine_persistence.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'db_path'`

- [ ] **Step 3: 구현 — `auto_trading_engine.py` 수정**

import에 추가 (Task 6에서 paper_execution import는 이미 추가됨):
```python
from ..db.repositories import PaperTradingRepository
```

`__init__` 시그니처를 `def __init__(self, config: AutoTradingConfig = None, db_path: str | None = None):`로 바꾸고, `self.active_positions: Dict[str, Dict] = {}` 줄을 다음으로 교체:
```python
        # 상태 관리 — DB가 진실의 원천, dict는 런타임 캐시
        self.paper_repo = PaperTradingRepository(db_path)
        self.active_positions: Dict[str, Dict] = {}
        self._restore_open_positions()
```

`__init__` 아래에 메서드 추가:
```python
    def _restore_open_positions(self):
        """서버 재시작 시 DB의 open 포지션을 메모리로 복원"""
        try:
            for pos in self.paper_repo.list_open_positions():
                self.active_positions[pos["symbol"]] = {
                    "position_id": pos["id"],
                    "symbol": pos["symbol"],
                    "shares": pos["quantity"],
                    "entry_price": pos["entry_price"],
                    "stop_loss": pos["stop_loss"],
                    "take_profit": pos["take_profit"],
                    "highest_price": pos["highest_price"] or pos["entry_price"],
                    "strategy": pos["strategy"],
                    "entry_time": datetime.fromisoformat(pos["entry_at"]),
                }
            if self.active_positions:
                logger.info(f"open 포지션 {len(self.active_positions)}건 복원됨")
        except Exception as e:
            # 복원 실패는 치명적 — 고아 포지션을 만들 수 있으므로 기동을 막는다
            logger.error(f"포지션 복원 실패: {e}")
            raise
```

`_execute_order`의 모의 거래 체결 블록(현재 491-498행)을:
```python
            # 모의 거래
            else:
                # 슬리피지 시뮬레이션
                slippage = np.random.uniform(-self.config.slippage_tolerance,
                                            self.config.slippage_tolerance)
                order.status = OrderStatus.FILLED
                order.filled_quantity = signal.position_size
                order.filled_price = signal.entry_price * (1 + slippage)
```

다음으로 교체:
```python
            # 모의 거래: 보수적 결정론 체결 (매수 올림 / 매도 내림, 랜덤 없음)
            else:
                order.status = OrderStatus.FILLED
                order.filled_quantity = signal.position_size
                order.filled_price = simulate_fill_price(
                    signal.entry_price,
                    "buy" if signal.action == "buy" else "sell",
                    self.config.slippage_tolerance,
                    signal.symbol,
                )
```

`_execute_order`의 포지션 업데이트 블록에서, 매수 쪽 `self.active_positions[signal.symbol] = {...}` 직전에 DB 기록을 추가하고 dict에 `position_id`를 포함:
```python
                if signal.action == "buy":
                    position_id = self.paper_repo.open_position(
                        symbol=signal.symbol,
                        quantity=order.filled_quantity,
                        entry_price=order.filled_price,
                        strategy=signal.strategy_name,
                        stop_loss=signal.stop_loss,
                        take_profit=signal.take_profit,
                        entry_at=datetime.now().isoformat(timespec="seconds"),
                    )
                    self.active_positions[signal.symbol] = {
                        "position_id": position_id,
                        "symbol": signal.symbol,
                        "shares": order.filled_quantity,
                        "entry_price": order.filled_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "highest_price": order.filled_price,
                        "strategy": signal.strategy_name,
                        "entry_time": datetime.now()
                    }
```

매도 쪽 `del self.active_positions[signal.symbol]` 직전에 추가:
```python
                        self.paper_repo.close_position(
                            position_id=position["position_id"],
                            exit_price=order.filled_price,
                            exit_reason=signal.reason,
                            exit_at=datetime.now().isoformat(timespec="seconds"),
                        )
```

`_manage_positions`의 트레일링 스톱 갱신 부분(`position['stop_loss'] = max(...)` 다음 줄)에 DB 동기화 추가:
```python
                            if self.config.use_trailing_stop:
                                new_stop = current_price * (1 - self.config.trailing_stop_percent)
                                position['stop_loss'] = max(position['stop_loss'], new_stop)
                                self.paper_repo.update_stops(
                                    position["position_id"],
                                    stop_loss=position['stop_loss'],
                                    highest_price=position['highest_price'],
                                )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_engine_persistence.py -v`
Expected: 3 passed. (test_paper_fill의 기대값 71,800이 tick_size 구현과 다르면 CLAUDE.md 호가단위 표 기준으로 손계산 후 기대값 수정 — 규칙: 71,710원은 50,000~100,000 구간이므로 100원 단위 올림)

- [ ] **Step 5: 전체 회귀 + 커밋**

Run: `venv\Scripts\python -m pytest tests/unit -v` → 전부 passed

```bash
git add backend/app/services/auto_trading_engine.py backend/tests/unit/test_engine_persistence.py
git commit -m "feat: 모의투자 포지션 DB 영속화 및 재시작 복원"
```

---

### Task 8: PnL 현재가 계산 + 일별 스냅샷 + 앱 기동 시 DB 초기화

**Files:**
- Modify: `backend/app/services/auto_trading_engine.py` (`_manage_positions`, `get_portfolio_summary`)
- Modify: `backend/app/main.py:91-94` (startup)
- Test: `backend/tests/unit/test_portfolio_summary.py`

**Interfaces:**
- Consumes: `SnapshotRepository` (Task 3)
- Produces: `get_portfolio_summary()`가 각 포지션 dict의 `"current_price"` 키(모니터링 루프가 갱신)를 사용해 평가액·손익 계산. 키가 없으면 entry_price로 폴백하되 결과에 `"price_is_stale": True` 포함. `_manage_positions` 루프가 마지막에 `SnapshotRepository.save(오늘 날짜, ...)` 호출. 앱 startup에서 `init_db()` 실행.

- [ ] **Step 1: 실패하는 테스트 작성**

`backend/tests/unit/test_portfolio_summary.py`:
```python
"""포트폴리오 평가가 현재가를 사용하는지 검증 (기존: entry_price 고정 → PnL 항상 0)"""
import asyncio
from datetime import datetime

import pytest

from app.db.database import init_db


@pytest.fixture
def engine(tmp_path):
    from app.services.auto_trading_engine import (
        AutoTradingEngine, AutoTradingConfig, TradingMode, TradingSignal,
    )
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    config = AutoTradingConfig(mode=TradingMode.PAPER, total_capital=10_000_000)
    eng = AutoTradingEngine(config, db_path=db_path)
    signal = TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="buy",
        strategy_name="buffett", confidence=0.8, entry_price=71000.0,
        stop_loss=65000.0, take_profit=85000.0, position_size=10,
        reason="테스트",
    )
    asyncio.run(eng._execute_order(signal))
    return eng


def test_summary_uses_current_price_when_available(engine):
    entry = engine.active_positions["005930.KS"]["entry_price"]
    engine.active_positions["005930.KS"]["current_price"] = entry + 5000

    summary = engine.get_portfolio_summary()
    pos = summary["positions"][0]
    assert pos["current_price"] == entry + 5000
    assert pos["pnl"] == pytest.approx(5000 * 10)
    assert summary["total_pnl"] > 0


def test_summary_flags_stale_price_when_no_current_price(engine):
    summary = engine.get_portfolio_summary()
    assert summary["price_is_stale"] is True  # 아직 시세 갱신 전
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_portfolio_summary.py -v`
Expected: FAIL — pnl이 0이거나 `price_is_stale` 키 없음

- [ ] **Step 3: 구현**

`auto_trading_engine.py` import에 추가:
```python
from ..db.repositories import PaperTradingRepository, SnapshotRepository
```
(기존 `PaperTradingRepository` import 줄을 이 줄로 대체)

`__init__`의 `self.paper_repo = ...` 아래에 추가:
```python
        self.snapshot_repo = SnapshotRepository(db_path)
```

`get_portfolio_summary`를 다음으로 교체:
```python
    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약 — 모니터링 루프가 갱신한 current_price 기준"""
        price_is_stale = False
        positions = []
        total_positions_value = 0.0
        total_cost = 0.0

        for symbol, pos in self.active_positions.items():
            entry_price = pos.get('entry_price', 0)
            quantity = pos.get('shares', 0)
            current_price = pos.get('current_price')
            if current_price is None:
                current_price = entry_price
                price_is_stale = True

            value = current_price * quantity
            total_positions_value += value
            total_cost += entry_price * quantity

            pnl = (current_price - entry_price) * quantity
            pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0

            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "entry_date": pos.get('entry_time', datetime.now()).strftime('%Y-%m-%d'),
                "current_price": current_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "stop_loss": pos.get('stop_loss'),
                "take_profit": pos.get('take_profit'),
                "strategy": pos.get('strategy', 'unknown')
            })

        # 현금 = 초기 자본 - 매수 원금 + 실현 손익
        realized_pnl = sum(t.get("pnl", 0) for t in self.trade_history)
        cash = self.config.total_capital - total_cost + realized_pnl
        total_value = cash + total_positions_value
        total_pnl = total_value - self.config.total_capital
        total_pnl_pct = (total_pnl / self.config.total_capital) * 100 if self.config.total_capital > 0 else 0

        risk_metrics = {
            "concentration_risk": len(self.active_positions) / self.config.max_positions if self.config.max_positions > 0 else 0,
            "daily_var": abs(self.daily_pnl) / self.config.total_capital if self.config.total_capital > 0 else 0,
            "max_position_size": max([p["current_price"] * p["quantity"] for p in positions]) if positions else 0
        }

        return {
            "total_value": total_value,
            "cash": cash,
            "positions_value": total_positions_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "price_is_stale": price_is_stale,
            "positions": positions,
            "risk_metrics": risk_metrics
        }
```

`_manage_positions`에서 `current_price = data['close'].iloc[-1]` 바로 다음 줄에 추가:
```python
                        position['current_price'] = current_price
```

같은 함수의 `await asyncio.sleep(30)` 직전(for 루프 밖)에 추가:
```python
                # 일별 스냅샷 저장 (같은 날 여러 번 저장돼도 마지막 값으로 upsert)
                try:
                    summary = self.get_portfolio_summary()
                    self.snapshot_repo.save(
                        snapshot_date=datetime.now().strftime("%Y-%m-%d"),
                        total_value=summary["total_value"],
                        cash=summary["cash"],
                        positions_value=summary["positions_value"],
                    )
                except Exception as e:
                    logger.error(f"스냅샷 저장 실패: {e}")
```

`backend/app/main.py`의 startup 이벤트를 다음으로 교체:
```python
@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행"""
    from .db.database import init_db
    init_db()
    register_websocket_callbacks()
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `venv\Scripts\python -m pytest tests/unit/test_portfolio_summary.py -v`
Expected: 2 passed

- [ ] **Step 5: 전체 회귀 + 커밋**

Run: `venv\Scripts\python -m pytest tests/unit -v` → 전부 passed

```bash
git add backend/app/services/auto_trading_engine.py backend/app/main.py backend/tests/unit/test_portfolio_summary.py
git commit -m "feat: 포트폴리오 평가를 현재가 기준으로 수정, 일별 스냅샷 저장, 기동 시 DB 초기화"
```

---

### Task 9: 수동 스모크 테스트 (E2E 검증)

**Files:** 없음 (검증만)

- [ ] **Step 1: 서버 기동 및 paper 모드 시작**

Run (backend/ 에서): `venv\Scripts\python -m uvicorn app.main:app --port 8000` (백그라운드)

확인:
1. `backend/data/auto_stock.db` 파일 생성됨
2. `POST http://localhost:8000/api/v1/trading/start` body `{"mode": "paper", "trading_symbols": ["005930.KS"]}` → 200
3. `POST .../trading/start` body `{"mode": "live"}` → **403**
4. `GET .../trading/status` → `is_running: true, mode: "paper"`

- [ ] **Step 2: 재시작 복원 확인**

DB에 open 포지션을 수동 삽입(장 마감 시간엔 신호가 안 나므로):
```bash
venv\Scripts\python -c "from app.db.repositories import PaperTradingRepository; PaperTradingRepository().open_position(symbol='005930.KS', quantity=10, entry_price=71000.0, strategy='buffett', stop_loss=65000.0, take_profit=85000.0, entry_at='2026-07-02T10:00:00')"
```
서버 재시작 → `POST /trading/start` (paper) → `GET /portfolio/status` 응답의 `positions`에 005930.KS 10주가 있어야 함. 로그에 "open 포지션 1건 복원됨" 확인.

- [ ] **Step 3: 결과 보고 후 커밋 없음 (검증 태스크)**

문제 발견 시 stop-the-line: 해당 태스크로 돌아가 수정.

---

## Self-Review 결과

- **Spec coverage**: 스펙 5.2(모의투자) 전체 + 4.1(DB 스키마) + LIVE 차단 커버. 스펙 4.2(catch-up)·5.1(백테스트)·5.3(뉴스)·5.4(추천)·6(UI)은 Phase 2~4 계획에서 다룸.
- **Placeholder scan**: 통과 — 모든 스텝에 실제 코드/명령 포함.
- **Type consistency**: `position_id`(dict 키), `PaperTradingRepository` 메서드 시그니처, `simulate_fill_price(price, side, slippage, symbol)` — Task 간 일치 확인.
- **알려진 조정 포인트** (구현자가 실제 코드 확인 필요): ① `tick_size.py` 함수 시그니처, ② `risk_params.take_pct` 속성명, ③ Task 7 체결가 기대값(호가단위 손계산 재검증).

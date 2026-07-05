"""가격 시계열·수익곡선 스냅샷 API 테스트

- price-history: fetch_daily_pykrx를 monkeypatch로 합성 DF 주입 → 응답 형태·
  빈 결과 200·500 은닉 검증 (실네트워크 없음).
- snapshots: 저장소 팩토리(_get_snapshot_repo)를 monkeypatch로 tmp DB 주입
  (today_routes 팩토리 패턴과 동일).
"""
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.repositories import SnapshotRepository
from app.api import market_routes, trading_routes
from app.main import app

client = TestClient(app)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "market.db")
    init_db(path)
    return path


# ── price-history: 합성 DF → 응답 형태 ──
def test_price_history_returns_bars(monkeypatch):
    idx = pd.to_datetime(["2026-07-01", "2026-07-02"])
    df = pd.DataFrame(
        {
            "open": [100.0, 110.0],
            "high": [120.0, 115.0],
            "low": [95.0, 105.0],
            "close": [110.0, 108.0],
            "volume": [1000, 2000],
        },
        index=idx,
    )
    monkeypatch.setattr(market_routes, "fetch_daily_pykrx",
                        lambda symbol, start, end: df)

    resp = client.get(
        "/api/v1/price-history?symbol=005930.KS&start=2026-07-01&end=2026-07-02"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "005930.KS"
    assert body["count"] == 2
    first = body["bars"][0]
    assert first == {
        "date": "2026-07-01",
        "open": 100.0,
        "high": 120.0,
        "low": 95.0,
        "close": 110.0,
        "volume": 1000,
    }
    # 날짜 오름차순 정렬
    assert body["bars"][1]["date"] == "2026-07-02"


# ── price-history: 빈 결과는 404 아니라 200 + count 0 ──
def test_price_history_empty_is_200(monkeypatch):
    monkeypatch.setattr(market_routes, "fetch_daily_pykrx",
                        lambda symbol, start, end: pd.DataFrame())

    resp = client.get(
        "/api/v1/price-history?symbol=AAPL&start=2026-07-01&end=2026-07-02"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["bars"] == []


# ── price-history: volume 컬럼 없어도 0으로 채워 동작 ──
def test_price_history_without_volume(monkeypatch):
    df = pd.DataFrame(
        {"open": [10.0], "high": [12.0], "low": [9.0], "close": [11.0]},
        index=pd.to_datetime(["2026-07-01"]),
    )
    monkeypatch.setattr(market_routes, "fetch_daily_pykrx",
                        lambda symbol, start, end: df)

    resp = client.get(
        "/api/v1/price-history?symbol=AAPL&start=2026-07-01&end=2026-07-01"
    )
    assert resp.status_code == 200
    assert resp.json()["bars"][0]["volume"] == 0


# ── price-history: 내부 예외 → 500 + 일반 메시지(상세 은닉) ──
def test_price_history_error_hides_internal_detail(monkeypatch):
    def boom(symbol, start, end):
        raise RuntimeError("secret path /var/secret leaked")
    monkeypatch.setattr(market_routes, "fetch_daily_pykrx", boom)

    resp = client.get(
        "/api/v1/price-history?symbol=AAPL&start=2026-07-01&end=2026-07-02"
    )
    assert resp.status_code == 500
    assert resp.json()["detail"] == "일시적인 오류가 발생했습니다"
    assert "secret" not in resp.json()["detail"]


# ── snapshots: tmp DB 주입 → 응답 형태 ──
def test_snapshots_returns_all(monkeypatch, db_path):
    repo = SnapshotRepository(db_path)
    repo.save("2026-07-01", total_value=1000000.0, cash=400000.0,
              positions_value=600000.0)
    repo.save("2026-07-02", total_value=1050000.0, cash=400000.0,
              positions_value=650000.0)
    monkeypatch.setattr(trading_routes, "_get_snapshot_repo",
                        lambda: SnapshotRepository(db_path))

    resp = client.get("/api/v1/portfolio/snapshots")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 2
    assert body["snapshots"][0] == {
        "snapshot_date": "2026-07-01",
        "total_value": 1000000.0,
        "cash": 400000.0,
        "positions_value": 600000.0,
    }
    assert body["snapshots"][1]["snapshot_date"] == "2026-07-02"


def test_snapshots_empty_is_200(monkeypatch, db_path):
    monkeypatch.setattr(trading_routes, "_get_snapshot_repo",
                        lambda: SnapshotRepository(db_path))
    resp = client.get("/api/v1/portfolio/snapshots")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["snapshots"] == []


def test_snapshots_error_hides_internal_detail(monkeypatch):
    def boom():
        raise RuntimeError("internal stack trace")
    monkeypatch.setattr(trading_routes, "_get_snapshot_repo", boom)

    resp = client.get("/api/v1/portfolio/snapshots")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "일시적인 오류가 발생했습니다"

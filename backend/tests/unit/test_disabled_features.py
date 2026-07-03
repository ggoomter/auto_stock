"""깨진 기능 비활성화 검증 — 허수 신뢰구간과 롱 체결 공매도 전략 차단"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chanos_not_in_strategy_list():
    res = client.get("/api/v1/master-strategies")
    assert res.status_code == 200
    names = [s.get("name") or s.get("id") for s in res.json().get("strategies", res.json())]
    assert "chanos" not in str(names).lower()


def test_chanos_request_rejected():
    res = client.post("/api/v1/master-strategy", json={
        "strategy_name": "chanos", "symbol": "AAPL",
        "start_date": "2024-01-01", "end_date": "2024-06-01",
    })
    assert res.status_code == 422

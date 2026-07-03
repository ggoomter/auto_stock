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

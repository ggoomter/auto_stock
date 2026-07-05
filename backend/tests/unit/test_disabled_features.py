"""깨진 기능 비활성화 검증 — 허수 신뢰구간과 롱 체결 공매도 전략 차단"""
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import app
from app.models.schemas import MasterStrategyRequest

client = TestClient(app)

# 실제 MasterStrategyRequest 스키마 기반 payload (symbols: List[str], date_range: DateRange)
VALID_PAYLOAD_BASE = {
    "symbols": ["AAPL"],
    "date_range": {"start": "2024-01-01", "end": "2024-06-01"},
}


def test_chanos_not_in_strategy_list():
    res = client.get("/api/v1/master-strategies")
    assert res.status_code == 200
    names = [s.get("name") or s.get("id") for s in res.json().get("strategies", res.json())]
    assert "chanos" not in str(names).lower()


def test_chanos_request_rejected():
    """chanos만 Literal 위반으로 422 — payload 나머지는 유효해야 격리성 보장"""
    res = client.post("/api/v1/master-strategy", json={
        "strategy_name": "chanos", **VALID_PAYLOAD_BASE,
    })
    assert res.status_code == 422
    # 422 사유가 strategy_name 필드의 Literal 위반임을 특정
    errors = res.json()["detail"]
    strategy_name_errors = [e for e in errors if "strategy_name" in e.get("loc", [])]
    assert strategy_name_errors, f"strategy_name 필드 에러가 없음: {errors}"
    # strategy_name 외 다른 필드 에러가 없어야 payload 유효성 입증
    other_errors = [e for e in errors if "strategy_name" not in e.get("loc", [])]
    assert not other_errors, f"payload가 스키마와 불일치 (비격리 테스트): {other_errors}"


def test_buffett_passes_strategy_name_validation():
    """대조 검증: 같은 payload에 buffett이면 strategy_name 검증 통과
    (네트워크 백테스트를 피하기 위해 Pydantic 모델 직접 검증)"""
    try:
        MasterStrategyRequest(strategy_name="buffett", **VALID_PAYLOAD_BASE)
    except ValidationError as e:
        raise AssertionError(f"buffett이 스키마 검증에 실패 — payload가 잘못됨: {e}")

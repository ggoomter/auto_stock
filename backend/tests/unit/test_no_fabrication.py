"""데이터 조작(fabrication) 제거 검증 — 없는 데이터는 None이어야 한다"""
from unittest.mock import patch

from app.services.korean_stock_data import KoreanStockDataFetcher


def _lynch_with_data(stock_data):
    """get_stock_data를 mock하여 get_lynch_metrics 결과 반환"""
    fetcher = KoreanStockDataFetcher()
    with patch.object(fetcher, "get_stock_data", return_value=stock_data):
        return fetcher.get_lynch_metrics("005930.KS")


def _graham_with_data(stock_data):
    """get_stock_data를 mock하여 get_graham_metrics 결과 반환"""
    fetcher = KoreanStockDataFetcher()
    with patch.object(fetcher, "get_stock_data", return_value=stock_data):
        return fetcher.get_graham_metrics("005930.KS")


def test_lynch_growth_is_none_without_data():
    # 성장률 실측 데이터가 없는 상태 (metrics에 ROE만 있어도 proxy 금지)
    lynch = _lynch_with_data({"metrics": {"PE": 10.0, "ROE": 0.084}})
    assert lynch["earnings_growth"] is None  # ROE proxy·기본값 0.10 금지
    assert lynch["PEG"] is None
    # 키 이름은 유지 (계약)
    assert "PE" in lynch
    assert "earnings_growth" in lynch
    assert "PEG" in lynch


def test_graham_current_ratio_is_none_without_data():
    graham = _graham_with_data({"metrics": {"PB": 1.2, "PE": 10.0}})
    assert graham["current_ratio"] is None  # 기본값 1.5 금지
    # 키 이름은 유지 (계약)
    assert "PB" in graham
    assert "current_ratio" in graham
    assert "PE" in graham


def test_graham_current_ratio_passthrough_when_present():
    # 실측 current_ratio가 있으면 그대로 반환
    graham = _graham_with_data({"metrics": {"PB": 1.2, "PE": 10.0, "current_ratio": 2.3}})
    assert graham["current_ratio"] == 2.3


def test_samsung_hardcode_removed():
    import inspect
    from app.services import korean_stock_data
    src = inspect.getsource(korean_stock_data)
    assert "_enhance_samsung_data" not in src
    assert "0.084" not in src  # 하드코딩 ROE 잔재 금지

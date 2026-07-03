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

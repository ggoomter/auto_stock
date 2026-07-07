"""매도 판단(sell_advisor) 테스트

계약 — 매수 후 보유/매도 판단은 검증된 규칙만 사용 (strategy_verification 참조):
1) 손절: 현재가 <= 매수가 × 0.92 → sell (원금 방어)
2) 샹들리에: 종가 < 22일 최고 종가 - 2.5×ATR22 → sell (추세 종료, 4차 채택)
3) 200일선 이탈: 종가 < MA200 → sell (매수 게이트와 대칭)
4) 부분 익절: +20%/+40% 도달 → partial_sell 제안
5) 어느 것도 아니면 hold + 매도 기준선 3개 제시
"""
import numpy as np
import pandas as pd
import pytest

from app.services.sell_advisor import evaluate_sell


def _df(closes):
    closes = np.asarray(closes, dtype=float)
    n = len(closes)
    return pd.DataFrame({
        "open": closes, "high": closes * 1.01, "low": closes * 0.99,
        "close": closes, "volume": [1_000_000] * n,
    }, index=pd.date_range("2024-01-02", periods=n, freq="B"))


def _uptrend(n=300, start=100.0, step=0.2):
    return [start + i * step for i in range(n)]


def test_hold_in_healthy_uptrend():
    """완만한 상승 추세 + 손실 없음 → 보유. 매도 기준선 3개가 모두 제시되어야 함."""
    df = _df(_uptrend())
    v = evaluate_sell(entry_price=df["close"].iloc[-20], ohlcv=df)
    assert v["action"] == "hold"
    assert v["levels"]["stop_loss"] > 0
    assert v["levels"]["chandelier"] > 0
    assert v["levels"]["ma200"] > 0
    # 신호 발생(passed=True)한 매도 조건이 없어야 함
    assert not any(c["passed"] for c in v["checks"] if c["condition_name_en"] != "PartialProfit")


def test_stop_loss_triggers_sell():
    """매수가 대비 -8% 초과 하락 → 즉시 매도 판정."""
    closes = _uptrend(280) + [100.0, 95.0, 88.0]  # 매수가 100 가정 → -12%
    df = _df(closes)
    v = evaluate_sell(entry_price=100.0, ohlcv=df)
    assert v["action"] == "sell"
    assert any(c["condition_name_en"] == "StopLoss" and c["passed"] for c in v["checks"])


def test_chandelier_triggers_sell():
    """이익 중이어도 22일 고점 - 2.5×ATR 아래로 꺾이면 추세 종료 매도."""
    # 급등 후 급락: 고점 160 → 현재 132 (-17.5%), 매수가 80 (여전히 +65% 이익)
    closes = _uptrend(260, 80.0, 0.31)  # 80 → 160
    peak = closes[-1]
    closes += [peak * (1 - 0.035 * i) for i in range(1, 6)]  # 5일 연속 하락
    df = _df(closes)
    v = evaluate_sell(entry_price=80.0, ohlcv=df)
    assert v["action"] == "sell"
    assert any(c["condition_name_en"] == "Chandelier" and c["passed"] for c in v["checks"])


def test_ma200_break_triggers_sell():
    """장기 하락 전환(종가 < 200일선) → 매도."""
    closes = [100.0] * 250 + [100.0 - i * 0.8 for i in range(1, 40)]  # 서서히 200일선 아래로
    df = _df(closes)
    v = evaluate_sell(entry_price=df["close"].iloc[-1] * 1.02, ohlcv=df)  # 손절선 미도달 수준
    assert v["action"] == "sell"
    assert any(c["condition_name_en"] == "TrendBreak" and c["passed"] for c in v["checks"])


def test_partial_profit_suggested_at_20pct():
    """+20% 이익 구간(추세 건재) → 부분 익절 제안 (전량 매도 아님)."""
    df = _df(_uptrend(300, 100.0, 0.15))
    current = df["close"].iloc[-1]
    v = evaluate_sell(entry_price=current / 1.25, ohlcv=df)  # +25% 이익
    assert v["action"] == "partial_sell"
    assert any(c["condition_name_en"] == "PartialProfit" and c["passed"] for c in v["checks"])


def test_insufficient_data_is_explicit():
    """데이터 부족 시 판단을 지어내지 않고 명시적으로 알림."""
    df = _df([100.0] * 50)
    v = evaluate_sell(entry_price=100.0, ohlcv=df)
    assert v["action"] == "insufficient_data"


def test_invalid_entry_price_rejected():
    with pytest.raises(ValueError):
        evaluate_sell(entry_price=0, ohlcv=_df(_uptrend()))

"""터틀 ATR 청산 결합 livermore(livermore_atr) 전략 테스트

계약:
- 진입은 순수 livermore와 동일 (52주 신고가 돌파 + 거래량).
- 청산은 기존 livermore 청산 OR 샹들리에(22일 최고 종가 - 2.5×ATR22) 이탈.
- 급락 시 샹들리에가 기존 청산보다 먼저 반응해야 함 (실측 4차: MDD 개선의 핵심).
"""
import numpy as np
import pandas as pd
import pytest

from app.services.master_strategies import get_strategy


def _make_df(closes, volumes=None):
    n = len(closes)
    # ndarray 사용 — Series를 넘기면 정수 인덱스가 날짜 인덱스와 정렬돼 전부 NaN이 됨
    closes = np.asarray(closes, dtype=float)
    if volumes is None:
        volumes = [1_000_000] * n
    return pd.DataFrame({
        "open": closes, "high": closes * 1.01, "low": closes * 0.99,
        "close": closes, "volume": volumes,
    }, index=pd.date_range("2020-01-02", periods=n, freq="B"))


def _breakout_then_crash():
    """300일 횡보 → 신고가 돌파 급등(거래량 급증) → 완만한 상승 → 급락"""
    closes = [100.0] * 300
    volumes = [1_000_000] * 300
    # 돌파: 거래량 5배 + 가격 급등
    closes += [110.0, 115.0, 120.0]
    volumes += [5_000_000] * 3
    # 상승 지속
    closes += [120.0 + i for i in range(20)]
    volumes += [1_500_000] * 20
    # 급락 (-20%): 샹들리에 이탈 구간
    peak = closes[-1]
    closes += [peak * (1 - 0.04 * (i + 1)) for i in range(5)]
    volumes += [3_000_000] * 5
    return _make_df(closes, volumes)


def test_registered_and_risk_params_valid():
    strat = get_strategy("livermore_atr")
    assert strat is not None
    rp = strat.get_risk_params()
    assert rp.stop_pct == pytest.approx(0.08)
    # 퍼센트 트레일링은 사실상 비활성(ATR 청산이 담당)
    assert rp.trailing_pct == pytest.approx(0.5)


def test_entries_match_pure_livermore():
    df = _breakout_then_crash()
    e_atr, _ = get_strategy("livermore_atr").generate_signals("TEST", df)
    e_pure, _ = get_strategy("livermore").generate_signals("TEST", df)
    assert e_atr.equals(e_pure)


def test_chandelier_exit_fires_on_crash():
    df = _breakout_then_crash()
    _, x_atr = get_strategy("livermore_atr").generate_signals("TEST", df)
    # 급락 구간(마지막 5일)에서 샹들리에 청산 신호 발생
    assert bool(x_atr.iloc[-5:].any())


def test_atr_exit_supersets_pure_exit():
    """ATR 결합 청산은 순수 livermore 청산의 상위집합 (기존 신호 유실 금지)"""
    df = _breakout_then_crash()
    _, x_atr = get_strategy("livermore_atr").generate_signals("TEST", df)
    _, x_pure = get_strategy("livermore").generate_signals("TEST", df)
    assert bool((x_pure & ~x_atr).sum() == 0)

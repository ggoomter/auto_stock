"""백테스트 엔진 자산 계산 정합성 테스트

회귀 대상 버그:
1. 청산 시 cash가 매도 대금으로 덮어써져 미투자 현금이 증발 (2025-11-22 a672014 도입)
2. 갭 하락 시 손절가 체결 가정 (실제로는 시가 체결) — 낙관 편향
3. 트레일링 스탑이 당일 고가를 먼저 반영해 당일 저가로 트리거 — intraday look-ahead
"""
import pandas as pd
import pytest

from app.models.schemas import RiskParams
from app.services.backtest import BacktestEngine


def _flat_df(dates, price=100.0):
    return pd.DataFrame({
        "open": price, "high": price * 1.001, "low": price * 0.999,
        "close": price, "volume": 1_000_000,
    }, index=dates)


def _signals(dates, entry_idx=None, exit_idx=None):
    entry = pd.Series(False, index=dates)
    exit_ = pd.Series(False, index=dates)
    if entry_idx is not None:
        entry.iloc[entry_idx] = True
    if exit_idx is not None:
        exit_.iloc[exit_idx] = True
    return entry, exit_


def test_cash_conserved_after_signal_exit():
    """부분 사이징(기본 RiskParams)에서 청산해도 미투자 현금이 보존되어야 함.

    가격이 거의 변하지 않으므로 최종 자산은 초기자본에서
    거래비용/슬리피지만큼만 미세하게 줄어야 정상.
    """
    dates = pd.date_range("2024-01-01", periods=30, freq="B")
    df = _flat_df(dates)
    entry, exit_ = _signals(dates, entry_idx=2, exit_idx=10)

    engine = BacktestEngine(df, entry, exit_, RiskParams(), initial_capital=100_000.0)
    _, _, summary = engine.run()

    # 기본 사이징은 자산의 약 29%만 진입 → 버그 시 최종 자산이 ~28,000으로 붕괴
    assert summary["ending_equity"] > 99_000.0


def test_cash_conserved_after_stop_loss_exit():
    """손절 경로에서도 현금 보존 (덮어쓰기 회귀 방지)"""
    dates = pd.date_range("2024-01-01", periods=20, freq="B")
    df = _flat_df(dates)
    # 5일차에 -10% 급락 → stop 7% 트리거
    df.iloc[5, df.columns.get_loc("low")] = 90.0
    df.iloc[5, df.columns.get_loc("close")] = 91.0
    entry, exit_ = _signals(dates, entry_idx=2)

    engine = BacktestEngine(df, entry, exit_, RiskParams(), initial_capital=100_000.0)
    _, _, summary = engine.run()

    # 투자분(~29%)의 -7% 손실 = 전체 자산 약 -2% → 그 이상 크게 깨지면 현금 증발 버그
    assert summary["ending_equity"] > 96_000.0


def test_cash_conserved_after_final_exit():
    """기간 종료 강제 청산(final_exit) 경로에서도 현금 보존"""
    dates = pd.date_range("2024-01-01", periods=15, freq="B")
    df = _flat_df(dates)
    entry, exit_ = _signals(dates, entry_idx=2)  # 청산 신호 없이 만기 보유

    engine = BacktestEngine(df, entry, exit_, RiskParams(), initial_capital=100_000.0)
    _, _, summary = engine.run()

    assert summary["ending_equity"] > 99_000.0


def test_gap_down_stop_fills_at_open_not_stop_level():
    """시가가 손절가 아래로 갭 하락하면 손절가가 아닌 시가 기준으로 체결되어야 함"""
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    df = _flat_df(dates)
    # 진입(3일차 시가 100) 후 5일차에 시가 80으로 갭 하락 (손절가 93보다 훨씬 아래)
    df.iloc[5] = {"open": 80.0, "high": 82.0, "low": 78.0, "close": 80.0, "volume": 1_000_000}
    entry, exit_ = _signals(dates, entry_idx=2)

    engine = BacktestEngine(df, entry, exit_, RiskParams(stop_pct=0.07), initial_capital=100_000.0)
    engine.run()

    stops = [t for t in engine.trades if t["exit_reason"] == "stop_loss"]
    assert len(stops) == 1
    # 시가 80 기준 체결 → 슬리피지/비용 감안해도 81 미만이어야 함 (버그 시 ~92.8에 체결)
    assert stops[0]["exit_price"] < 81.0


def test_gap_up_take_profit_fills_at_open():
    """시가가 익절가 위로 갭 상승하면 익절가가 아닌 시가 기준으로 체결되어야 함"""
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    df = _flat_df(dates)
    # 진입(3일차 시가 100, 익절가 115) 후 5일차 시가 130으로 갭 상승
    df.iloc[5] = {"open": 130.0, "high": 132.0, "low": 128.0, "close": 130.0, "volume": 1_000_000}
    entry, exit_ = _signals(dates, entry_idx=2)

    engine = BacktestEngine(df, entry, exit_, RiskParams(take_pct=0.15), initial_capital=100_000.0)
    engine.run()

    tps = [t for t in engine.trades if t["exit_reason"] == "take_profit"]
    assert len(tps) == 1
    # 시가 130 기준 체결 → 129 초과여야 함 (버그 시 115 기준 ~114.8에 체결)
    assert tps[0]["exit_price"] > 129.0


def test_vol_target_20_is_valid_sizing():
    """super_momentum이 쓰는 vol_target_20이 RiskParams 스키마에서 거부되면 안 됨 (회귀)"""
    rp = RiskParams(position_sizing="vol_target_20")
    assert rp.position_sizing == "vol_target_20"


def test_vol_target_sizes_down_high_volatility():
    """VOL_annualized 컬럼이 없어도 엔진이 변동성을 직접 계산해 고변동 종목 비중을 줄여야 함.

    기존 버그: 컬럼 부재 시 조용히 1.0(전액) 폴백 → vol targeting 미작동.
    """
    import numpy as np
    dates = pd.date_range("2024-01-01", periods=100, freq="B")
    rng = np.random.RandomState(42)
    # 고변동: 일 표준편차 ~3% (연 ~48%) / 저변동: ~0.3% (연 ~4.8%)
    high_vol = 100 * np.cumprod(1 + rng.normal(0, 0.03, 100))
    low_vol = 100 * np.cumprod(1 + rng.normal(0, 0.003, 100))

    def _engine_with(closes):
        df = pd.DataFrame({"open": closes, "high": closes, "low": closes,
                           "close": closes, "volume": 1_000_000}, index=dates)
        sig = pd.Series(False, index=dates)
        return BacktestEngine(df, sig, sig.copy(),
                              RiskParams(position_sizing="vol_target_10")), df

    eng_h, df_h = _engine_with(high_vol)
    eng_l, df_l = _engine_with(low_vol)
    frac_h = eng_h._calculate_position_size(100_000, df_h["close"].iloc[-1], df_h)
    frac_l = eng_l._calculate_position_size(100_000, df_l["close"].iloc[-1], df_l)

    assert frac_h < 0.5   # 연 48% 변동성에 목표 10% → 비중 대략 0.2 근처
    assert frac_l == 1.0  # 저변동은 상한 1.0
    assert frac_h < frac_l


def test_trailing_stop_not_triggered_by_same_day_high():
    """당일 고가로 올라간 트레일링 스탑이 당일 저가로 트리거되면 안 됨 (intraday look-ahead).

    고가→저가 순서를 알 수 없으므로, 당일 갱신된 트레일링은 다음 날부터 적용해야 함.
    """
    dates = pd.date_range("2024-01-01", periods=10, freq="B")
    df = _flat_df(dates)
    # 진입(3일차 시가 100) 후 4일차: 고가 200 / 저가 100
    # look-ahead 버그 시: 트레일링 180으로 즉시 갱신 → 저가 100 <= 180 → 당일 손절
    # 올바른 동작: 4일차는 진입가 기반 스탑(93)만 유효 → 저가 100 > 93 → 보유 유지
    df.iloc[4] = {"open": 100.0, "high": 200.0, "low": 100.0, "close": 150.0, "volume": 1_000_000}
    # 이후 가격을 150으로 유지해 다른 청산 경로 차단 (진입가 100 대비 +50%는 partial 대상이나
    # 4일차 고가에서 이미 partial 처리됨 — stop_loss가 4일차에 나오지 않는지만 검증)
    for i in range(5, 10):
        df.iloc[i] = {"open": 150.0, "high": 150.5, "low": 149.5, "close": 150.0, "volume": 1_000_000}
    entry, exit_ = _signals(dates, entry_idx=2)

    engine = BacktestEngine(
        df, entry, exit_,
        RiskParams(stop_pct=0.07, take_pct=9.0, trailing_pct=0.10),
        initial_capital=100_000.0,
    )
    engine.run()

    same_day_stops = [
        t for t in engine.trades
        if t["exit_reason"] == "stop_loss" and t["exit_date"] == dates[4]
    ]
    assert same_day_stops == []

"""
거래 비용 테스트

한국 주식 매도세, 슬리피지, 거래량 제약이 올바르게 작동하는지 검증합니다.
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.schemas import RiskParams
from app.services.backtest import BacktestEngine
from app.utils.tick_size import round_to_tick_down, round_to_tick_up


def _make_ohlcv(
    prices: list[float],
    start: str = "2023-01-02",
    volume: int = 100000,
) -> pd.DataFrame:
    dates = pd.bdate_range(start=start, periods=len(prices))
    rows = []
    for i, close in enumerate(prices):
        open_price = prices[i - 1] if i > 0 else close
        rows.append({
            "Open": open_price,
            "High": max(open_price, close) * 1.005,
            "Low": min(open_price, close) * 0.995,
            "Close": close,
            "Volume": volume,
        })
    return pd.DataFrame(rows, index=dates)


def _make_signals(index, entry_days, exit_days):
    entry = pd.Series(False, index=index)
    exit_ = pd.Series(False, index=index)
    for d in entry_days:
        if d < len(index):
            entry.iloc[d] = True
    for d in exit_days:
        if d < len(index):
            exit_.iloc[d] = True
    return entry, exit_


def _default_risk() -> RiskParams:
    return RiskParams(
        stop_pct=0.50,       # 넓은 손절 (비용 테스트용)
        take_pct=5.0,        # 넓은 익절
        position_sizing="equal_weight",
        trailing_pct=0.50,
        max_risk_per_trade_pct=1.0,
        max_portfolio_drawdown_pct=0.9,
        daily_loss_limit_pct=0.5,
        cooldown_days_after_loss=0,
        max_consecutive_losses=10,
        scale_down_after_drawdown_pct=0.0,
        scale_down_factor=1.0,
        allow_partial_profits=False,
    )


# ───────────────────────────────────────────────
# 테스트 1: 한국 주식 매도세
# ───────────────────────────────────────────────

class TestKoreanSellTax:
    """한국 주식 매도 시 거래세 0.23%가 적용되는지 검증."""

    def test_sell_tax_applied_to_korean_stock(self):
        """한국 주식 매도 가격에 거래세가 차감됨"""
        engine = BacktestEngine(
            _make_ohlcv([27000] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=10,
            slippage_bps=5,
            is_korean_stock=True,
            korean_sell_tax_bps=23,
        )

        # 매도 실행 가격 테스트
        raw_price = 27000.0
        exit_price = engine._execute_exit_price(raw_price)

        # 기대값: 27000 * (1-0.0005) * (1-0.001) * (1-0.0023)
        # = 27000 * 0.9995 * 0.999 * 0.9977
        expected = raw_price * (1 - 5/10000) * (1 - 10/10000) * (1 - 23/10000)
        expected = round_to_tick_down(expected, is_korean=True)

        assert exit_price == expected

    def test_no_sell_tax_for_us_stock(self):
        """미국 주식 매도에는 거래세 없음"""
        engine = BacktestEngine(
            _make_ohlcv([100] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=10,
            slippage_bps=5,
            is_korean_stock=False,
        )

        raw_price = 100.0
        exit_price = engine._execute_exit_price(raw_price)

        # 거래세 없음: 100 * (1-0.0005) * (1-0.001)
        expected = raw_price * (1 - 5/10000) * (1 - 10/10000)
        # 미국 주식은 호가 단위 없음
        assert abs(exit_price - expected) < 0.01

    def test_buy_cost_less_than_sell_cost_korean(self):
        """한국 주식: 매수 비용 < 매도 비용 (거래세는 매도에만 적용)"""
        engine = BacktestEngine(
            _make_ohlcv([27000] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=10,
            slippage_bps=5,
            is_korean_stock=True,
            korean_sell_tax_bps=23,
        )

        base_price = 27000.0
        entry_cost = engine._execute_entry_price(base_price) - base_price  # 매수 추가 비용
        sell_cost = base_price - engine._execute_exit_price(base_price)  # 매도 차감 비용

        # 매도 비용이 매수 비용보다 커야 함 (거래세 때문)
        assert sell_cost > entry_cost, (
            f"매도 비용({sell_cost:.2f})이 매수 비용({entry_cost:.2f})보다 작음. "
            f"한국 주식 거래세가 미적용되었을 가능성."
        )


# ───────────────────────────────────────────────
# 테스트 2: 거래량 제약
# ───────────────────────────────────────────────

class TestVolumeConstraint:
    """거래량 제약이 포지션 크기를 제한하는지 검증."""

    def test_volume_limits_position_size(self):
        """20일 평균 거래량의 10% 초과 불가"""
        engine = BacktestEngine(
            _make_ohlcv([100] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=0,
            slippage_bps=0,
            initial_capital=10000000,  # 1천만원 (대량 주문 유도)
        )

        # 평균 거래량 1000주 → 최대 100주 (10%)
        shares, capital, _ = engine._determine_shares(
            cash=10000000,
            equity=10000000,
            entry_price=100,
            position_fraction=1.0,
            size_multiplier=1.0,
            avg_daily_volume=1000,
        )

        assert shares <= 100, (
            f"거래량 제약 위반: {shares}주 > 100주 (평균거래량 1000의 10%)"
        )

    def test_no_volume_constraint_when_zero(self):
        """거래량 데이터가 없으면 제약 없음"""
        engine = BacktestEngine(
            _make_ohlcv([100] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=0,
            slippage_bps=0,
            initial_capital=10000,
        )

        shares_with_vol, _, _ = engine._determine_shares(
            cash=10000, equity=10000, entry_price=100,
            position_fraction=1.0, size_multiplier=1.0,
            avg_daily_volume=0,
        )

        # 거래량 제약 없으므로 자금 기준으로만 제한
        assert shares_with_vol == 100  # 10000 / 100 = 100주


# ───────────────────────────────────────────────
# 테스트 3: 슬리피지 적용
# ───────────────────────────────────────────────

class TestSlippage:
    """슬리피지가 매수/매도에 올바르게 적용되는지 검증."""

    def test_entry_price_includes_slippage(self):
        """매수 시 슬리피지로 가격이 올라감"""
        engine = BacktestEngine(
            _make_ohlcv([100] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=0,
            slippage_bps=50,  # 50bps = 0.5%
        )

        entry_price = engine._execute_entry_price(100.0)
        # 100 * (1 + 0.005) = 100.5
        assert entry_price > 100.0
        assert abs(entry_price - 100.5) < 0.01

    def test_exit_price_includes_slippage(self):
        """매도 시 슬리피지로 가격이 내려감"""
        engine = BacktestEngine(
            _make_ohlcv([100] * 5),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            pd.Series(False, index=pd.bdate_range("2023-01-02", periods=5)),
            _default_risk(),
            transaction_cost_bps=0,
            slippage_bps=50,
            is_korean_stock=False,
        )

        exit_price = engine._execute_exit_price(100.0)
        # 100 * (1 - 0.005) = 99.5
        assert exit_price < 100.0
        assert abs(exit_price - 99.5) < 0.01


# ───────────────────────────────────────────────
# 테스트 4: 전체 거래 비용 영향
# ───────────────────────────────────────────────

class TestTransactionCostImpact:
    """거래 비용이 전체 수익에 미치는 영향 검증."""

    def test_costs_reduce_returns(self):
        """동일한 거래에서 비용이 있으면 수익이 줄어듦"""
        prices = [100, 100, 100, 110, 110, 110, 110, 110, 110, 110]
        data = _make_ohlcv(prices, volume=1000000)
        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[5])

        # 비용 없는 백테스트
        engine_free = BacktestEngine(
            data.copy(), entry.copy(), exit_.copy(), _default_risk(),
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics_free, _, _ = engine_free.run()

        # 비용 있는 백테스트
        engine_cost = BacktestEngine(
            data.copy(), entry.copy(), exit_.copy(), _default_risk(),
            transaction_cost_bps=10, slippage_bps=5,
            initial_capital=10000,
        )
        metrics_cost, _, _ = engine_cost.run()

        # 비용이 있으면 수익이 줄어야 함
        if engine_free.trades and engine_cost.trades:
            pnl_free = engine_free.trades[0]["pnl"]
            pnl_cost = engine_cost.trades[0]["pnl"]
            assert pnl_cost < pnl_free, (
                f"비용 적용 후 수익({pnl_cost:.2f})이 "
                f"비용 없는 수익({pnl_free:.2f})보다 크거나 같음"
            )

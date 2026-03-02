"""
백테스트 엔진 단위 테스트

합성 데이터를 사용하여 알려진 결과를 검증합니다.
- 진입/청산 타이밍
- 손절/익절 로직
- 진입일 손절 스킵
- 갭 리스크 모델링
- 거래량 제약
- 한국 주식 호가 단위
"""

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.models.schemas import RiskParams
from app.services.backtest import BacktestEngine
from app.utils.tick_size import (
    get_korean_tick_size,
    round_to_tick_down,
    round_to_tick_up,
)


# ───────────────────────────────────────────────
# 헬퍼: 합성 가격 데이터 생성
# ───────────────────────────────────────────────

def _make_ohlcv(
    prices: list[float],
    start: str = "2023-01-02",
    spread_pct: float = 0.02,
    volume: int = 100000,
) -> pd.DataFrame:
    """
    종가 리스트로부터 OHLCV DataFrame 생성.
    Open=전일 종가, High=Close*(1+spread), Low=Close*(1-spread).
    """
    dates = pd.bdate_range(start=start, periods=len(prices))
    rows = []
    for i, close in enumerate(prices):
        open_price = prices[i - 1] if i > 0 else close
        high = max(open_price, close) * (1 + spread_pct)
        low = min(open_price, close) * (1 - spread_pct)
        rows.append({
            "Open": open_price,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        })
    return pd.DataFrame(rows, index=dates)


def _make_signals(
    index: pd.DatetimeIndex,
    entry_days: list[int],
    exit_days: list[int],
) -> tuple[pd.Series, pd.Series]:
    """인덱스 위치 기반으로 진입/청산 시그널 생성."""
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
        stop_pct=0.07,
        take_pct=0.15,
        position_sizing="equal_weight",
        trailing_pct=0.10,
        max_risk_per_trade_pct=1.0,   # 테스트용으로 제한 완화
        max_portfolio_drawdown_pct=0.9,
        daily_loss_limit_pct=0.5,
        cooldown_days_after_loss=0,
        max_consecutive_losses=10,
        scale_down_after_drawdown_pct=0.0,
        scale_down_factor=1.0,
        allow_partial_profits=False,
    )


# ───────────────────────────────────────────────
# 테스트 1: 기본 진입/청산 흐름
# ───────────────────────────────────────────────

class TestBasicEntryExit:
    """진입 시그널 다음날 시가 진입, 청산 시그널 다음날 시가 청산 검증."""

    def test_entry_executes_next_day_open(self):
        """Day 0 시그널 → Day 1 시가 진입"""
        # 10일간 100→110 점진 상승
        prices = [100 + i for i in range(10)]
        data = _make_ohlcv(prices, spread_pct=0.0)  # spread=0 → Open=전일 Close
        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[5])

        engine = BacktestEngine(
            data, entry, exit_, _default_risk(),
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        # 거래가 1건 발생해야 함
        assert len(engine.trades) == 1
        trade = engine.trades[0]

        # 진입가 = Day 1 시가 = Day 0 종가 = 100
        assert trade["entry_price"] == 100.0

        # 청산 시그널 Day 5 → Day 6 시가 = Day 5 종가 = 105
        assert trade["exit_price"] == 105.0
        assert trade["exit_reason"] == "exit_signal_open"

    def test_no_trades_when_no_signals(self):
        """시그널이 없으면 거래 없음 (최종일 강제 청산도 없음)"""
        prices = [100] * 10
        data = _make_ohlcv(prices, spread_pct=0.0)
        entry, exit_ = _make_signals(data.index, entry_days=[], exit_days=[])

        engine = BacktestEngine(
            data, entry, exit_, _default_risk(),
            transaction_cost_bps=0, slippage_bps=0,
        )
        metrics, _, _ = engine.run()
        assert len(engine.trades) == 0
        assert metrics.CAGR == 0.0


# ───────────────────────────────────────────────
# 테스트 2: 손절/익절
# ───────────────────────────────────────────────

class TestStopLossTakeProfit:
    """손절/익절 발동 검증."""

    def test_stop_loss_triggered(self):
        """가격이 손절가 아래로 떨어지면 손절 발동"""
        # Day 0: 100, Day 1: 100(진입), Day 2: 100, Day 3: 90 (7%이상 하락 → 손절)
        prices = [100, 100, 100, 90, 90, 90]
        data = _make_ohlcv(prices, spread_pct=0.005)
        # spread=0.005 → Low가 ~0.5% 정도만 내려감
        # Day 3: Open=100, Low=min(100,90)*(1-0.005)=89.55 → 손절가(93) 아래

        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[])
        risk = _default_risk()
        risk.stop_pct = 0.07  # 손절 7% → 손절가 = 100 * 0.93 = 93

        engine = BacktestEngine(
            data, entry, exit_, risk,
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        # 손절이 발동되어야 함
        stop_trades = [t for t in engine.trades if t["exit_reason"] == "stop_loss"]
        assert len(stop_trades) >= 1
        # 손절 가격은 시가(100)와 손절가(93) 중 작은 값 = min(100, 93) = 93 (갭 없음)
        # 하지만 Day3 Open=100 (전일 종가), stop_loss=93 → min(100, 93) = 93
        assert stop_trades[0]["exit_price"] == 93.0

    def test_take_profit_triggered(self):
        """가격이 익절가 위로 오르면 익절 발동"""
        # 부분 청산(partial_20 threshold=20%)이 먼저 발동할 수 있으므로
        # 익절(15%)보다 낮지만 부분 청산보다 높은 시나리오는 피해야 함
        # → 부분 청산이 발동하지 않도록 allow_partial_profits=False 설정 확인
        # 그런데 엔진은 partial_rules를 항상 실행하므로,
        # 익절이 먼저 발동하도록 가격을 점진적으로 올림

        # Day 0: 100 (시그널), Day 1: 100 (진입, entry_bar 스킵)
        # Day 2: 116 → High가 115 넘으면 익절 발동
        # 부분 청산 threshold=20% → 120이므로 116에서는 미발동
        dates = pd.bdate_range("2023-01-02", periods=6)
        data = pd.DataFrame({
            "Open":   [100, 100, 116, 116, 116, 116],
            "High":   [100, 100, 118, 116, 116, 116],  # Day 2 High=118 > 115(익절가)
            "Low":    [100, 100, 114, 116, 116, 116],
            "Close":  [100, 100, 116, 116, 116, 116],
            "Volume": [100000] * 6,
        }, index=dates)

        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[])
        risk = _default_risk()
        risk.take_pct = 0.15  # 익절 15% → 익절가 = 100 * 1.15 = 115

        engine = BacktestEngine(
            data, entry, exit_, risk,
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        tp_trades = [t for t in engine.trades if t["exit_reason"] == "take_profit"]
        assert len(tp_trades) >= 1
        # 익절 가격 = max(open=116, take_profit=115) = 116 (갭 업이므로 시가)
        assert tp_trades[0]["exit_price"] == 116.0


# ───────────────────────────────────────────────
# 테스트 3: 진입일 손절 스킵
# ───────────────────────────────────────────────

class TestEntryBarSkip:
    """진입 당일(entry_bar)에는 손절/익절이 발동하지 않아야 함."""

    def test_no_stop_loss_on_entry_day(self):
        """진입 당일 가격이 손절 범위에 있어도 스킵"""
        # Day 0: 100 (시그널), Day 1: 100 (진입) → 이후 크게 떨어짐
        # 하지만 Day 1(진입일) Low가 손절가 아래여도 발동 안 해야 함
        # Day 2에서 발동해야 함

        # 진입가 = Day 1 Open = Day 0 Close = 100
        # 손절가 = 100 * (1 - 0.07) = 93
        # Day 1: Low를 매우 낮게 설정해도 스킵
        prices = [100, 85, 85, 85, 85]  # Day 1 close=85 → huge drop
        data = _make_ohlcv(prices, spread_pct=0.0)
        # spread=0 → Day1: Open=100, High=100, Low=85, Close=85
        # 실제로는 Open=전일Close=100, Low=min(100,85)=85

        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[])
        risk = _default_risk()
        risk.stop_pct = 0.07

        engine = BacktestEngine(
            data, entry, exit_, risk,
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        # 거래가 있어야 함
        assert len(engine.trades) >= 1
        trade = engine.trades[0]

        # 진입일(Day 1)이 아닌 Day 2에서 손절되어야 함
        # Day 1 = index[1], Day 2 = index[2]
        entry_date = data.index[1]
        exit_date = trade["exit_date"]

        # 진입일과 청산일이 달라야 함 (같은 날 청산 안 됨)
        assert exit_date > entry_date


# ───────────────────────────────────────────────
# 테스트 4: 갭 리스크 모델링
# ───────────────────────────────────────────────

class TestGapRisk:
    """갭 다운/업 시 시가에서 청산되는지 검증."""

    def test_gap_down_exits_at_open(self):
        """시가가 손절가보다 낮으면 (갭 다운) 시가에서 청산"""
        # Day 0: 100 (시그널), Day 1: 100 (진입), Day 2: 80 (갭 다운)
        # 진입가=100, 손절가=93, Day 2 Open=100→갭 다운→80
        # 수동으로 Open을 설정하기 위해 직접 DataFrame 생성

        dates = pd.bdate_range("2023-01-02", periods=5)
        data = pd.DataFrame({
            "Open":   [100, 100, 80,  80,  80],
            "High":   [100, 100, 82,  80,  80],
            "Low":    [100, 100, 78,  80,  80],
            "Close":  [100, 100, 80,  80,  80],
            "Volume": [100000] * 5,
        }, index=dates)

        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[])
        risk = _default_risk()
        risk.stop_pct = 0.07  # 손절가 = 100 * 0.93 = 93

        engine = BacktestEngine(
            data, entry, exit_, risk,
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        stop_trades = [t for t in engine.trades if t["exit_reason"] == "stop_loss"]
        assert len(stop_trades) >= 1

        # 갭 다운: exit_price = min(open=80, stop=93) = 80
        assert stop_trades[0]["exit_price"] == 80.0

    def test_gap_up_exits_at_open(self):
        """시가가 익절가보다 높으면 (갭 업) 시가에서 청산"""
        dates = pd.bdate_range("2023-01-02", periods=5)
        data = pd.DataFrame({
            "Open":   [100, 100, 130, 130, 130],
            "High":   [100, 100, 135, 130, 130],
            "Low":    [100, 100, 128, 130, 130],
            "Close":  [100, 100, 130, 130, 130],
            "Volume": [100000] * 5,
        }, index=dates)

        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[])
        risk = _default_risk()
        risk.take_pct = 0.15  # 익절가 = 100 * 1.15 = 115

        engine = BacktestEngine(
            data, entry, exit_, risk,
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        tp_trades = [t for t in engine.trades if t["exit_reason"] == "take_profit"]
        assert len(tp_trades) >= 1

        # 갭 업: exit_price = max(open=130, take_profit=115) = 130
        assert tp_trades[0]["exit_price"] == 130.0


# ───────────────────────────────────────────────
# 테스트 5: 통계적 신뢰도
# ───────────────────────────────────────────────

class TestStatisticalSignificance:
    """거래 횟수에 따른 통계적 신뢰도 경고 검증."""

    def test_very_low_confidence_few_trades(self):
        """거래 5건 미만 → very_low 신뢰도"""
        # 1회 거래만 발생하도록 구성
        prices = [100, 105, 110, 115, 120]
        data = _make_ohlcv(prices, spread_pct=0.0)
        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[2])

        engine = BacktestEngine(
            data, entry, exit_, _default_risk(),
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=10000,
        )
        metrics, _, _ = engine.run()

        assert metrics.statistical_significance is not None
        assert metrics.statistical_significance["confidence"] == "very_low"


# ───────────────────────────────────────────────
# 테스트 6: 한국 주식 호가 단위
# ───────────────────────────────────────────────

class TestKoreanTickSize:
    """한국 주식 호가 단위 반올림 검증."""

    @pytest.mark.parametrize("price,expected_tick", [
        (500, 1),
        (2000, 5),
        (7000, 10),
        (27000, 50),
        (75000, 100),
        (300000, 500),
        (600000, 1000),
    ])
    def test_tick_size_by_price_range(self, price, expected_tick):
        assert get_korean_tick_size(price) == expected_tick

    def test_round_to_tick_up(self):
        # 27,041원 → 27,050원 (50원 단위 올림)
        assert round_to_tick_up(27041, is_korean=True) == 27050
        # 정확히 호가 단위면 그대로
        assert round_to_tick_up(27050, is_korean=True) == 27050

    def test_round_to_tick_down(self):
        # 33,348원 → 33,300원 (50원 단위 내림)
        assert round_to_tick_down(33348, is_korean=True) == 33300
        # 정확히 호가 단위면 그대로
        assert round_to_tick_down(33300, is_korean=True) == 33300

    def test_non_korean_no_rounding(self):
        # 비한국 주식은 반올림 없음
        assert round_to_tick_up(27.041, is_korean=False) == 27.041
        assert round_to_tick_down(33.348, is_korean=False) == 33.348

    def test_korean_shares_are_integer(self):
        """한국 주식 수량은 정수여야 함"""
        prices = [27050] * 10
        data = _make_ohlcv(prices, spread_pct=0.0)
        entry, exit_ = _make_signals(data.index, entry_days=[0], exit_days=[5])

        engine = BacktestEngine(
            data, entry, exit_, _default_risk(),
            transaction_cost_bps=0, slippage_bps=0,
            initial_capital=1000000,
            is_korean_stock=True,
        )
        metrics, _, _ = engine.run()

        for trade in engine.trades:
            assert isinstance(trade["shares"], int) or trade["shares"] == int(trade["shares"])

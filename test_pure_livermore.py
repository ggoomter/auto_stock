"""Regression tests for Livermore strategies using the upgraded backtest engine."""
import pytest
import pandas as pd

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent / 'backend'))

from app.services.master_strategies import LivermoreStrategy, ModernLivermoreStrategy
from app.services.data_fetcher import get_stock_data
from app.services.backtest import BacktestEngine


@pytest.mark.parametrize(
    "strategy_cls",
    [LivermoreStrategy, ModernLivermoreStrategy],
    ids=["pure_livermore", "modern_livermore"],
)
def test_livermore_strategies_backtest(strategy_cls):
    symbol = "096530.KQ"
    start_date = "2024-01-01"
    end_date = "2024-12-31"

    price_data = get_stock_data(symbol, start_date, end_date, include_indicators=True)
    assert not price_data.empty, "Price data should not be empty for regression test"

    strategy = strategy_cls()
    entry_signals, exit_signals = strategy.generate_signals(symbol, price_data)

    backtest = BacktestEngine(
        data=price_data,
        entry_signals=entry_signals,
        exit_signals=exit_signals,
        risk_params=strategy.get_risk_params(),
        initial_capital=1_000_000,
        is_korean_stock=True,
    )

    metrics, equity_curve, risk_report = backtest.run()

    # 기본 지표 및 리스크 요약이 모두 생성되는지 확인
    assert equity_curve is not None and not equity_curve.empty
    assert metrics.TotalTrades is not None
    assert isinstance(risk_report, dict)
    assert "max_drawdown_pct" in risk_report

    # 거래 상세가 DataFrame 으로 반환되는지 확인
    trades = backtest.get_trade_details()
    assert isinstance(trades, pd.DataFrame)
    if not trades.empty:
        required_columns = {"entry_date", "exit_date", "entry_price", "exit_price", "shares", "pnl"}
        assert required_columns.issubset(trades.columns)


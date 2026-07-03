"""포트폴리오 평가가 현재가를 사용하는지 검증 (기존: entry_price 고정 → PnL 항상 0)"""
import asyncio
from datetime import datetime

import pytest

from app.db.database import init_db


@pytest.fixture
def engine(tmp_path):
    from app.services.auto_trading_engine import (
        AutoTradingEngine, AutoTradingConfig, TradingMode, TradingSignal,
    )
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    config = AutoTradingConfig(mode=TradingMode.PAPER, total_capital=10_000_000)
    eng = AutoTradingEngine(config, db_path=db_path)
    signal = TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="buy",
        strategy_name="buffett", confidence=0.8, entry_price=71000.0,
        stop_loss=65000.0, take_profit=85000.0, position_size=10,
        reason="테스트",
    )
    asyncio.run(eng._execute_order(signal))
    return eng


def test_summary_uses_current_price_when_available(engine):
    entry = engine.active_positions["005930.KS"]["entry_price"]
    engine.active_positions["005930.KS"]["current_price"] = entry + 5000

    summary = engine.get_portfolio_summary()
    pos = summary["positions"][0]
    assert pos["current_price"] == entry + 5000
    assert pos["pnl"] == pytest.approx(5000 * 10)
    assert summary["total_pnl"] > 0


def test_summary_flags_stale_price_when_no_current_price(engine):
    summary = engine.get_portfolio_summary()
    assert summary["price_is_stale"] is True  # 아직 시세 갱신 전

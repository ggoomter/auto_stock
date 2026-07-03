"""엔진 영속화 테스트 — 매수/매도가 DB에 기록되고 재시작 시 복원되는가"""
import asyncio
from datetime import datetime

import pytest

from app.db.database import init_db


def _make_engine(db_path):
    from app.services.auto_trading_engine import (
        AutoTradingEngine, AutoTradingConfig, TradingMode,
    )
    config = AutoTradingConfig(mode=TradingMode.PAPER, total_capital=10_000_000)
    return AutoTradingEngine(config, db_path=db_path)


def _buy_signal():
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="buy",
        strategy_name="buffett", confidence=0.8, entry_price=71000.0,
        stop_loss=65000.0, take_profit=85000.0, position_size=10,
        reason="테스트 진입",
    )


def _sell_signal(shares):
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol="005930.KS", action="sell",
        strategy_name="buffett", confidence=1.0, entry_price=80000.0,
        stop_loss=0, take_profit=0, position_size=shares, reason="익절매",
    )


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_buy_persists_and_restores_after_restart(db_path):
    engine = _make_engine(db_path)
    order = asyncio.run(engine._execute_order(_buy_signal()))
    assert order is not None and order.status.value == "filled"
    assert "005930.KS" in engine.active_positions
    assert "position_id" in engine.active_positions["005930.KS"]

    # 재시작 시뮬레이션: 새 엔진 인스턴스가 DB에서 복원
    engine2 = _make_engine(db_path)
    assert "005930.KS" in engine2.active_positions
    restored = engine2.active_positions["005930.KS"]
    assert restored["shares"] == 10
    assert restored["strategy"] == "buffett"


def test_sell_closes_position_in_db(db_path):
    from app.db.repositories import PaperTradingRepository
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    shares = engine.active_positions["005930.KS"]["shares"]
    asyncio.run(engine._execute_order(_sell_signal(shares)))

    assert "005930.KS" not in engine.active_positions
    repo = PaperTradingRepository(db_path)
    assert repo.list_open_positions() == []
    sides = [t["side"] for t in repo.list_trades()]
    assert sides == ["buy", "sell"]


def test_paper_fill_uses_tick_rounding_not_random(db_path):
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    fill = engine.active_positions["005930.KS"]["entry_price"]
    # 71,000원 * (1+0.01 슬리피지 기본값) = 71,710 → 100원 단위 올림 = 71,800
    # (50,000~100,000원 구간 호가단위 100원)
    assert fill == 71800.0

"""전체 브런치 최종 리뷰 결함 수정 검증 (C1, C2, I1).

'재시작해도 정직한 모의투자'라는 목표를 직접 훼손하던 결함들을 잡는 최소 테스트.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.db.database import init_db
from app.db.repositories import PaperTradingRepository


def _make_engine(db_path):
    from app.services.auto_trading_engine import (
        AutoTradingEngine, AutoTradingConfig, TradingMode,
    )
    config = AutoTradingConfig(mode=TradingMode.PAPER, total_capital=10_000_000)
    engine = AutoTradingEngine(config, db_path=db_path)
    # 실시간 시세 조회는 네트워크 의존이므로 차단 → 폴백(현재가/진입가) 경로를 태운다
    engine.data_collector.fetch_realtime_data = AsyncMock(return_value=None)
    return engine


def _buy_signal(symbol="005930.KS", entry_price=71000.0, shares=10):
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol=symbol, action="buy",
        strategy_name="buffett", confidence=0.8, entry_price=entry_price,
        stop_loss=65000.0, take_profit=85000.0, position_size=shares,
        reason="테스트 진입",
    )


def _sell_signal(symbol="005930.KS", entry_price=80000.0, shares=10):
    from app.services.auto_trading_engine import TradingSignal
    return TradingSignal(
        timestamp=datetime.now(), symbol=symbol, action="sell",
        strategy_name="buffett", confidence=1.0, entry_price=entry_price,
        stop_loss=0, take_profit=0, position_size=shares, reason="익절매",
    )


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_emergency_stop_closes_with_nonzero_exit_price(db_path):
    """C1: 긴급 정지 청산이 current_price 폴백으로 0원이 아닌 exit_price를 기록한다."""
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    # 시세 갱신값을 넣어두면 청산가는 이 값에서 파생돼야 한다 (0 아님)
    engine.active_positions["005930.KS"]["current_price"] = 90000.0

    result = asyncio.run(engine.emergency_stop(reason="테스트"))
    assert result["closed_positions"] == 1
    assert engine.active_positions == {}

    repo = PaperTradingRepository(db_path)
    assert repo.list_open_positions() == []
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    # current_price(90000) 기준 보수적 내림 체결 → 0보다 훨씬 큼
    assert sell["price"] > 0
    assert sell["price"] == pytest.approx(89100.0)  # 90000*0.99=89100, 100원 단위


def test_zero_fill_price_rejected_and_not_persisted(db_path):
    """C1 이중방어: 체결가 0이 되는 신호는 REJECTED, DB에 기록되지 않는다."""
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))

    # entry_price=0 인 매도 신호 → simulate_fill_price=0 → 거부돼야 함
    order = asyncio.run(engine._execute_order(_sell_signal(entry_price=0.0)))
    assert order.status.value == "rejected"

    repo = PaperTradingRepository(db_path)
    # 매도가 거부됐으므로 포지션은 여전히 open, 매도 체결 기록도 없어야 한다
    assert len(repo.list_open_positions()) == 1
    assert [t["side"] for t in repo.list_trades()] == ["buy"]
    assert "005930.KS" in engine.active_positions


def test_realized_pnl_survives_engine_restart(db_path):
    """C2: 매수→매도(이익) 후 새 엔진 인스턴스의 cash에 실현손익이 반영된다."""
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal(entry_price=71000.0, shares=10)))
    asyncio.run(engine._execute_order(_sell_signal(entry_price=80000.0, shares=10)))

    # 매수 체결 71800, 매도 체결 79200 → 실현손익 (79200-71800)*10 = 74000
    expected_realized = (79200.0 - 71800.0) * 10

    # 재시작: 메모리 trade_history가 없는 새 엔진 (open 포지션도 없음)
    engine2 = _make_engine(db_path)
    assert engine2.trade_history == []
    summary = engine2.get_portfolio_summary()
    assert summary["cash"] == pytest.approx(10_000_000 + expected_realized)
    assert summary["total_pnl"] == pytest.approx(expected_realized)


def test_stop_with_close_positions_actually_closes(db_path):
    """I1: stop(close_positions=True)가 실제로 포지션을 청산한다 (데드레터 아님)."""
    engine = _make_engine(db_path)
    asyncio.run(engine._execute_order(_buy_signal()))
    assert "005930.KS" in engine.active_positions

    asyncio.run(engine.stop(close_positions=True))

    assert engine.active_positions == {}
    repo = PaperTradingRepository(db_path)
    assert repo.list_open_positions() == []
    assert [t["side"] for t in repo.list_trades()] == ["buy", "sell"]

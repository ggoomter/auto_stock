"""모의투자 포지션 저장소 테스트"""
import pytest

from app.db.database import init_db


@pytest.fixture
def repo(tmp_path):
    from app.db.repositories import PaperTradingRepository
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return PaperTradingRepository(db_path)


def test_open_position_returns_id_and_records_buy_trade(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    assert isinstance(pos_id, int)

    open_positions = repo.list_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0]["symbol"] == "005930.KS"
    assert open_positions[0]["quantity"] == 10
    assert open_positions[0]["highest_price"] == 71000.0  # 진입 시 최고가 = 진입가

    trades = repo.list_trades()
    assert len(trades) == 1
    assert trades[0]["side"] == "buy"
    assert trades[0]["price"] == 71000.0


def test_close_position_removes_from_open_and_records_sell(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    repo.close_position(pos_id, exit_price=85000.0,
                        exit_reason="익절매", exit_at="2026-07-03T11:00:00")

    assert repo.list_open_positions() == []
    trades = repo.list_trades()
    assert len(trades) == 2
    sell = [t for t in trades if t["side"] == "sell"][0]
    assert sell["price"] == 85000.0
    assert sell["reason"] == "익절매"


def test_double_close_records_only_one_sell(repo):
    """경합 방어: 같은 포지션을 두 번 청산해도 sell 체결은 1건만 기록된다.

    reconcile와 auto_trading_engine이 동시에 같은 포지션을 청산하려는 경합에서
    두 번째 close_position은 조용히 무시되어야 한다(예외 없음)."""
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    repo.close_position(pos_id, exit_price=85000.0,
                        exit_reason="익절매", exit_at="2026-07-03T11:00:00")
    # 두 번째 청산 — 예외 없이 조용히 무시되어야 함
    repo.close_position(pos_id, exit_price=90000.0,
                        exit_reason="재청산 시도", exit_at="2026-07-03T12:00:00")

    sells = [t for t in repo.list_trades() if t["side"] == "sell"]
    assert len(sells) == 1
    # 첫 청산 값이 유지되고 두 번째 시도로 덮어써지지 않아야 함
    assert sells[0]["price"] == 85000.0
    assert sells[0]["reason"] == "익절매"


def test_update_stops(repo):
    pos_id = repo.open_position(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-02T10:00:00",
    )
    repo.update_stops(pos_id, stop_loss=70000.0, highest_price=74000.0)

    pos = repo.list_open_positions()[0]
    assert pos["stop_loss"] == 70000.0
    assert pos["highest_price"] == 74000.0


def test_open_positions_survive_new_repository_instance(repo, tmp_path):
    """재시작 시나리오: 새 저장소 인스턴스에서도 open 포지션 조회 가능"""
    from app.db.repositories import PaperTradingRepository
    repo.open_position(
        symbol="000660.KS", quantity=5, entry_price=200000.0,
        strategy="lynch", stop_loss=180000.0, take_profit=260000.0,
        entry_at="2026-07-02T10:00:00",
    )
    fresh = PaperTradingRepository(str(tmp_path / "test.db"))
    assert len(fresh.list_open_positions()) == 1

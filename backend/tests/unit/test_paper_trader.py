"""페이퍼 트레이딩 자동화(paper_trader) 테스트

계약:
- 진입: 직전 거래일 추천을 as_of 시가에 매수 (오늘 추천은 제외 — 익일 시가 원칙).
  균등 1/N 배분, 보유 중 종목 스킵, 슬롯/현금 한도, 데이터 없으면 스킵.
- 스탑 갱신: 샹들리에·200일선 중 큰 값으로 stop_loss 인상만 (인하 금지).
"""
import numpy as np
import pandas as pd
import pytest

from app.db.database import init_db
from app.db.repositories import PaperTradingRepository, RecommendationRepository
from app.services.paper_trader import (
    available_cash,
    compute_dynamic_stop,
    run_paper_entry,
    run_stop_update,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "t.db")
    init_db(path)
    return path


def _save_reco(db, rec_date, symbol, score=50.0):
    RecommendationRepository(db).save(
        rec_date=rec_date, symbol=symbol, name=symbol, score=score,
        passed_conditions=[], technical_signals=[])


def _fetch_open(price):
    """as_of 당일 봉 1개를 돌려주는 fetch_daily 스텁"""
    def fetch(symbol, start, end):
        return pd.DataFrame({"open": [price], "high": [price * 1.01],
                             "low": [price * 0.99], "close": [price],
                             "volume": [1000]},
                            index=[pd.Timestamp(end)])
    return fetch


def test_entry_buys_previous_day_recos_equal_weight(db):
    repo = PaperTradingRepository(db)
    _save_reco(db, "2026-07-06", "005930.KS", 90.0)
    _save_reco(db, "2026-07-06", "000660.KS", 80.0)
    _save_reco(db, "2026-07-07", "999999.KS", 99.0)  # 오늘 추천 — 대상 아님

    stats = run_paper_entry(repo, RecommendationRepository(db), _fetch_open(50_000.0),
                            as_of="2026-07-07", initial_capital=10_000_000.0,
                            max_positions=5)

    assert stats["rec_date"] == "2026-07-06"  # 오늘(07-07) 추천은 제외
    assert stats["opened"] == 2
    positions = repo.list_open_positions()
    assert {p["symbol"] for p in positions} == {"005930.KS", "000660.KS"}
    for p in positions:
        # 균등 1/N: 1,000만 / 5 = 200만 예산, 체결가(슬리피지+호가올림) 기준 정수 주수
        assert p["entry_price"] >= 50_000.0  # 보수적 체결 (매수는 불리하게)
        assert p["quantity"] == int(2_000_000 // p["entry_price"])
        assert p["stop_loss"] == pytest.approx(p["entry_price"] * 0.92, rel=0.01)


def test_entry_skips_already_held_and_respects_slots(db):
    repo = PaperTradingRepository(db)
    repo.open_position("005930.KS", 10, 50_000.0, "reco_nearhigh_v1",
                       46_000.0, None, "2026-07-06T09:00:00")
    _save_reco(db, "2026-07-06", "005930.KS", 90.0)  # 이미 보유
    _save_reco(db, "2026-07-06", "000660.KS", 80.0)

    stats = run_paper_entry(repo, RecommendationRepository(db), _fetch_open(50_000.0),
                            as_of="2026-07-07", initial_capital=10_000_000.0,
                            max_positions=2)

    assert stats["skipped_held"] == 1
    assert stats["opened"] == 1  # 남은 슬롯 1개에 000660만
    assert len(repo.list_open_positions()) == 2


def test_entry_no_prior_reco_is_noop(db):
    repo = PaperTradingRepository(db)
    _save_reco(db, "2026-07-07", "005930.KS")  # 오늘 것만 있음
    stats = run_paper_entry(repo, RecommendationRepository(db), _fetch_open(50_000.0),
                            as_of="2026-07-07", initial_capital=10_000_000.0,
                            max_positions=5)
    assert stats["rec_date"] is None
    assert stats["opened"] == 0


def test_entry_skips_when_no_market_data(db):
    repo = PaperTradingRepository(db)
    _save_reco(db, "2026-07-06", "005930.KS")

    def no_data(symbol, start, end):
        return pd.DataFrame()

    stats = run_paper_entry(repo, RecommendationRepository(db), no_data,
                            as_of="2026-07-07", initial_capital=10_000_000.0,
                            max_positions=5)
    assert stats["skipped_data"] == 1
    assert stats["opened"] == 0


def test_available_cash_accounts_open_positions(db):
    repo = PaperTradingRepository(db)
    assert available_cash(repo, 10_000_000.0) == pytest.approx(10_000_000.0)
    repo.open_position("005930.KS", 10, 100_000.0, "s", 92_000.0, None,
                       "2026-07-06T09:00:00")
    assert available_cash(repo, 10_000_000.0) == pytest.approx(9_000_000.0)


def _trend_bars(n=300, start=100.0, step=0.5):
    closes = np.array([start + step * i for i in range(n)])
    return pd.DataFrame({"open": closes, "high": closes * 1.01,
                         "low": closes * 0.99, "close": closes,
                         "volume": [1000] * n},
                        index=pd.date_range("2025-01-02", periods=n, freq="B"))


def test_stop_update_raises_but_never_lowers(db):
    repo = PaperTradingRepository(db)
    # 낮은 초기 스탑 → 샹들리에/200일선이 위에 있으면 인상
    pid = repo.open_position("005930.KS", 10, 200.0, "s", 92.0, None,
                             "2026-07-06T09:00:00")
    bars = _trend_bars()
    stats = run_stop_update(repo, lambda *a: bars, as_of="2026-07-07")
    assert stats["raised"] == 1
    raised = repo.list_open_positions()[0]["stop_loss"]
    assert raised > 92.0

    # 이미 더 높은 스탑 → 인하 금지 (raised 0)
    repo.update_stops(pid, raised + 10_000.0, 250.0)
    stats2 = run_stop_update(repo, lambda *a: bars, as_of="2026-07-07")
    assert stats2["raised"] == 0


def test_stop_update_skips_short_data(db):
    repo = PaperTradingRepository(db)
    repo.open_position("005930.KS", 10, 200.0, "s", 92.0, None,
                       "2026-07-06T09:00:00")
    stats = run_stop_update(repo, lambda *a: _trend_bars(100), as_of="2026-07-07")
    assert stats["skipped"] == 1


def test_compute_dynamic_stop_matches_sell_advisor_levels():
    """스탑 계산이 sell_advisor의 기준선(샹들리에·200일선)과 동일해야
    화면의 매도 진단과 페이퍼 계좌 동작이 일치한다."""
    from app.services.sell_advisor import evaluate_sell
    bars = _trend_bars()
    stop = compute_dynamic_stop(bars)
    v = evaluate_sell(entry_price=float(bars["close"].iloc[-30]), ohlcv=bars)
    expected = max(v["levels"]["chandelier"], v["levels"]["ma200"])
    assert stop == pytest.approx(expected, rel=0.001)


# ── 일별 자산 스냅샷 (수익 곡선 원천) ──
def test_snapshot_saves_cash_only_state(db):
    """포지션 0개(현금 100%)여도 스냅샷은 저장 — 곡선의 시작점."""
    from app.db.repositories import SnapshotRepository
    from app.services.paper_trader import run_daily_snapshot
    repo = PaperTradingRepository(db)
    snap = SnapshotRepository(db)

    stats = run_daily_snapshot(repo, snap, lambda *a: pd.DataFrame(),
                               as_of="2026-07-07", initial_capital=10_000_000.0)
    assert stats["total_value"] == 10_000_000
    rows = snap.list_all()
    assert len(rows) == 1 and rows[0]["snapshot_date"] == "2026-07-07"


def test_snapshot_values_positions_at_close(db):
    from app.db.repositories import SnapshotRepository
    from app.services.paper_trader import run_daily_snapshot
    repo = PaperTradingRepository(db)
    repo.open_position("005930.KS", 10, 50_000.0, "s", 46_000.0, None,
                       "2026-07-06T09:00:00")
    stats = run_daily_snapshot(repo, SnapshotRepository(db), _fetch_open(55_000.0),
                               as_of="2026-07-07", initial_capital=10_000_000.0)
    # 현금 950만 + 10주×55,000(당일 종가) = 10,050,000
    assert stats["total_value"] == 10_050_000
    assert stats["priced"] == 1

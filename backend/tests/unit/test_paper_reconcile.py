"""모의투자 오프라인 기간 보수적 정산(reconcile) 테스트.

네트워크 없음: fetch_daily는 합성 DataFrame을 주입한다.
핵심 불변식: 어떤 경로로도 낙관적(유리한) 체결이 나오면 안 된다.
"""
import pandas as pd
import pytest

from app.db.database import init_db
from app.db.repositories import PaperTradingRepository
from app.services.paper_reconcile import reconcile_positions
from app.utils.tick_size import round_to_tick_down


@pytest.fixture
def repo(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return PaperTradingRepository(db_path)


def _bars(rows):
    """rows: [(date, open, high, low, close)] → 소문자 컬럼 DatetimeIndex DF."""
    idx = pd.to_datetime([r[0] for r in rows])
    return pd.DataFrame(
        {
            "open": [r[1] for r in rows],
            "high": [r[2] for r in rows],
            "low": [r[3] for r in rows],
            "close": [r[4] for r in rows],
        },
        index=idx,
    )


def _open(repo, **kw):
    defaults = dict(
        symbol="005930.KS", quantity=10, entry_price=71000.0,
        strategy="buffett", stop_loss=65000.0, take_profit=85000.0,
        entry_at="2026-07-01T10:00:00",
    )
    defaults.update(kw)
    return repo.open_position(**defaults)


def test_stop_loss_touched_on_second_day_closes_conservatively(repo):
    """서버 3일 꺼짐, 둘째 날 low가 손절가 터치 → 청산, 손절가 이하, reason에 '손절'."""
    pos_id = _open(repo)

    def fetch_daily(symbol, start, end):
        return _bars([
            ("2026-07-02", 70000, 71000, 68000, 69000),  # 터치 없음
            ("2026-07-03", 68000, 68500, 64000, 64500),  # low<=stop 터치
            ("2026-07-04", 64000, 66000, 63000, 65000),
        ])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["checked"] == 1
    assert result["closed"] == 1
    assert result["skipped"] == 0
    assert repo.list_open_positions() == []

    trades = repo.list_trades()
    sell = [t for t in trades if t["side"] == "sell"][0]
    assert "손절" in sell["reason"]
    # 보수적: 청산가는 손절가 이하 (open=68000 > stop=65000 → min=65000)
    assert sell["price"] <= 65000.0
    assert sell["price"] == round_to_tick_down(65000.0, True)
    # 둘째 날(07-03) 봉에서 청산
    assert sell["executed_at"] == "2026-07-03T15:30:00"


def test_gap_down_open_below_stop_uses_open_not_stop(repo):
    """갭하락 개장(open < stop_loss) → 청산가 = open 기준(min(open,stop)), 낙관 금지."""
    pos_id = _open(repo, stop_loss=65000.0)

    def fetch_daily(symbol, start, end):
        # open=63000 < stop=65000 (갭하락), low 더 아래
        return _bars([("2026-07-02", 63000, 64000, 61000, 62000)])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["closed"] == 1
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    # min(open=63000, stop=65000)=63000 을 호가단위 내림 — stop보다 불리(낮음)
    assert sell["price"] == round_to_tick_down(63000.0, True)
    assert sell["price"] < 65000.0


def test_take_profit_touched_uses_target_not_above(repo):
    """고가가 익절가 터치 → 청산가 = take_profit (그 이상 금지, 갭상승이어도 목표가)."""
    pos_id = _open(repo, take_profit=85000.0)

    def fetch_daily(symbol, start, end):
        # 갭상승: open=86000 > tp=85000, high 더 위 → 그래도 tp 사용
        return _bars([("2026-07-02", 86000, 87000, 85500, 86500)])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["closed"] == 1
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    assert "익절" in sell["reason"]
    assert sell["price"] == round_to_tick_down(85000.0, True)
    assert sell["price"] <= 85000.0


def test_same_bar_both_touched_stop_loss_wins(repo):
    """같은 봉에서 손절·익절 동시 터치 → 손절 우선."""
    pos_id = _open(repo, stop_loss=65000.0, take_profit=85000.0)

    def fetch_daily(symbol, start, end):
        # low<=stop AND high>=tp 동시 터치
        return _bars([("2026-07-02", 70000, 90000, 60000, 65000)])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["closed"] == 1
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    assert "손절" in sell["reason"]
    # min(open=70000, stop=65000)=65000
    assert sell["price"] == round_to_tick_down(65000.0, True)


def test_no_touch_keeps_position_open(repo):
    """터치 없음 → 유지, checked=1 closed=0."""
    pos_id = _open(repo, stop_loss=60000.0, take_profit=90000.0)

    def fetch_daily(symbol, start, end):
        return _bars([
            ("2026-07-02", 70000, 72000, 69000, 71000),
            ("2026-07-03", 71000, 73000, 70000, 72000),
        ])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["checked"] == 1
    assert result["closed"] == 0
    assert result["skipped"] == 0
    assert len(repo.list_open_positions()) == 1


def test_no_data_skips_position(repo):
    """데이터 없음(빈 DF) → skipped, 포지션 유지."""
    _open(repo)

    def fetch_daily(symbol, start, end):
        return pd.DataFrame()

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["checked"] == 1
    assert result["closed"] == 0
    assert result["skipped"] == 1
    assert len(repo.list_open_positions()) == 1


def test_none_stop_or_take_skips_that_condition(repo):
    """stop_loss/take_profit이 None이면 해당 조건만 스킵 (익절만 동작)."""
    _open(repo, stop_loss=None, take_profit=85000.0)

    def fetch_daily(symbol, start, end):
        # low가 매우 낮아도 stop=None이면 무시, high가 tp 터치 → 익절 청산
        return _bars([("2026-07-02", 84000, 86000, 10000, 85000)])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["closed"] == 1
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    assert "익절" in sell["reason"]
    assert sell["price"] == round_to_tick_down(85000.0, True)


def test_halted_zero_ohlc_bar_does_not_trigger_zero_price_exit(repo):
    """거래정지일(OHLC=0 봉)이 끼어 있어도 0원 청산 금지 — 이후 정상 봉에서 정산."""
    _open(repo, stop_loss=65000.0, take_profit=85000.0)

    def fetch_daily(symbol, start, end):
        return _bars([
            ("2026-07-02", 0, 0, 0, 0),                   # 거래정지: low=0<=stop 이지만 무효 봉
            ("2026-07-03", 68000, 68500, 64000, 64500),   # 정상 봉에서 손절 터치
        ])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["closed"] == 1
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    # 0원 청산 오염 금지 — 정상 봉 기준 min(open=68000, stop=65000)=65000
    assert sell["price"] > 0
    assert sell["price"] == round_to_tick_down(65000.0, True)
    assert sell["executed_at"] == "2026-07-03T15:30:00"


def test_nan_bar_position_skipped_others_still_reconciled(repo):
    """open=NaN 봉만 있는 포지션은 skipped, 다른 포지션 정산은 계속된다."""
    _open(repo, symbol="005930.KS")                        # NaN 데이터 포지션
    _open(repo, symbol="000660.KS", quantity=5,
          entry_price=200000.0, stop_loss=180000.0, take_profit=260000.0)

    def fetch_daily(symbol, start, end):
        if symbol == "005930.KS":
            # 전 봉 NaN → 유효 봉 없음 → skipped (ValueError로 전체 중단되면 안 됨)
            return _bars([("2026-07-02", float("nan"), float("nan"),
                           float("nan"), float("nan"))])
        # 000660: 손절 터치 (low=175000 <= stop=180000)
        return _bars([("2026-07-02", 185000, 186000, 175000, 176000)])

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["checked"] == 2
    assert result["closed"] == 1
    assert result["skipped"] == 1
    remaining = repo.list_open_positions()
    assert len(remaining) == 1
    assert remaining[0]["symbol"] == "005930.KS"
    sell = [t for t in repo.list_trades() if t["side"] == "sell"][0]
    assert sell["symbol"] == "000660.KS"
    assert "손절" in sell["reason"]


def test_fetch_failure_skips_position(repo):
    """fetch_daily 예외 → skipped, 포지션 유지."""
    _open(repo)

    def fetch_daily(symbol, start, end):
        raise RuntimeError("네트워크 오류")

    result = reconcile_positions(repo, fetch_daily, as_of="2026-07-05")

    assert result["skipped"] == 1
    assert result["closed"] == 0
    assert len(repo.list_open_positions()) == 1

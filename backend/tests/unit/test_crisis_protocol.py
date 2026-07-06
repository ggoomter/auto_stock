"""위기 매수 프로토콜 테스트

계약:
- 시장 지수가 고점 대비 트랜치 임계값(-20%/-30%/-40%)에 도달하면 해당 트랜치를
  1회만 발동(deploy)한다. 같은 낙폭에 머물러도 중복 발동 금지.
- 지수가 고점 근처(-2% 이내)로 회복하면 재장전(rearm) — 다음 위기에서 다시 발동 가능.
- 상태는 append-only 이벤트로 영속화되어 서버 재시작에도 유지된다.
"""
import pandas as pd
import pytest

from app.db.database import init_db
from app.db.repositories import CrisisRepository
from app.services.crisis_protocol import (
    TRANCHES,
    compute_drawdown,
    evaluate,
    run_check,
)


# --- 순수 로직 ---

def test_tranche_fractions_sum_to_one():
    """예비대 배분 합계는 100% (일부만 쓰다 남기는 설계 실수 방지)"""
    assert sum(fraction for _, fraction in TRANCHES) == pytest.approx(1.0)


def test_compute_drawdown_from_running_peak():
    s = pd.Series([100.0, 120.0, 90.0])
    # 고점 120 대비 90 → -25%
    assert compute_drawdown(s) == pytest.approx(-0.25)


def test_no_action_in_normal_market():
    assert evaluate(drawdown=-0.10, active_stages=set()) == []


def test_stage1_deploys_once_at_minus_20():
    actions = evaluate(drawdown=-0.21, active_stages=set())
    assert [a.stage for a in actions if a.type == "deploy"] == [1]
    # 이미 발동된 상태에서 같은 낙폭 → 중복 발동 금지
    assert evaluate(drawdown=-0.22, active_stages={1}) == []


def test_gap_down_triggers_multiple_stages():
    """하루 만에 -35%까지 갭 하락 → 1·2단계 동시 발동, 3단계는 아직"""
    actions = evaluate(drawdown=-0.35, active_stages=set())
    assert [a.stage for a in actions] == [1, 2]


def test_recovery_rearms_only_when_stages_active():
    rearm = evaluate(drawdown=-0.01, active_stages={1, 2})
    assert [a.type for a in rearm] == ["rearm"]
    assert evaluate(drawdown=-0.01, active_stages=set()) == []


def test_no_rearm_while_still_down():
    """-15%까지 반등해도 고점 근처(-2%)가 아니면 재장전하지 않음 (휩쏘 방지)"""
    assert evaluate(drawdown=-0.15, active_stages={1}) == []


# --- 영속화 ---

@pytest.fixture
def repo(tmp_path):
    db = str(tmp_path / "test.db")
    init_db(db)
    return CrisisRepository(db)


def test_repository_active_stages_lifecycle(repo):
    assert repo.active_stages("KR") == set()
    repo.record_event("KR", "deploy", stage=1, event_date="2026-07-06", drawdown=-0.21)
    repo.record_event("KR", "deploy", stage=2, event_date="2026-07-10", drawdown=-0.31)
    assert repo.active_stages("KR") == {1, 2}
    # 재장전 이후에는 초기화
    repo.record_event("KR", "rearm", stage=None, event_date="2026-12-01", drawdown=-0.01)
    assert repo.active_stages("KR") == set()


def test_repository_markets_are_independent(repo):
    repo.record_event("KR", "deploy", stage=1, event_date="2026-07-06", drawdown=-0.21)
    assert repo.active_stages("US") == set()


# --- 오케스트레이터 (I/O 주입) ---

def test_run_check_deploys_and_persists(repo):
    # 고점 100 → 75 (-25%): 1단계 발동
    index = pd.Series([100.0, 90.0, 75.0],
                      index=pd.date_range("2026-07-01", periods=3))
    sent = []
    stats = run_check(repo, market="KR", index_series=index,
                      notify=lambda msg: sent.append(msg), today="2026-07-06")
    assert stats["deployed_stages"] == [1]
    assert repo.active_stages("KR") == {1}
    assert len(sent) == 1 and "1단계" in sent[0]
    # 같은 낙폭으로 다음 날 재실행 → 무발동·무알림 (멱등)
    stats2 = run_check(repo, market="KR", index_series=index,
                       notify=lambda msg: sent.append(msg), today="2026-07-07")
    assert stats2["deployed_stages"] == []
    assert len(sent) == 1


def test_run_check_rearm_after_recovery(repo):
    crash = pd.Series([100.0, 75.0], index=pd.date_range("2026-07-01", periods=2))
    run_check(repo, market="KR", index_series=crash, notify=None, today="2026-07-02")
    assert repo.active_stages("KR") == {1}
    # 신고점 회복 → 재장전
    recovered = pd.Series([100.0, 75.0, 101.0],
                          index=pd.date_range("2026-07-01", periods=3))
    stats = run_check(repo, market="KR", index_series=recovered, notify=None,
                      today="2026-12-01")
    assert stats["rearmed"] is True
    assert repo.active_stages("KR") == set()


def test_run_check_notify_failure_does_not_break(repo):
    """알림 실패(텔레그램 미설정 등)가 상태 기록을 막으면 안 됨"""
    index = pd.Series([100.0, 75.0], index=pd.date_range("2026-07-01", periods=2))
    def boom(msg):
        raise RuntimeError("telegram down")
    stats = run_check(repo, market="KR", index_series=index, notify=boom,
                      today="2026-07-06")
    assert stats["deployed_stages"] == [1]
    assert repo.active_stages("KR") == {1}

"""daily_jobs 오케스트레이터 테스트 — 네트워크 금지(작업 함수 monkeypatch).

run_catchup의 멱등성·실패 격리·비동기 계약을 검증한다.
"""
import asyncio
import json

import pytest

from app.db.database import init_db
from app.db.repositories import JobRunRepository


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


@pytest.fixture
def spies(monkeypatch):
    """3개 작업 함수를 성공 스텁으로 대체하고 호출 여부를 추적한다."""
    from app.services import daily_jobs

    calls = {"news": 0, "reco": 0, "reconcile": 0, "crisis": 0,
             "paper_entry": 0, "paper_stops": 0, "paper_snapshot": 0}

    def fake_build_name_map(*a, **k):
        return {}

    def fake_collect_and_store(*a, **k):
        calls["news"] += 1
        return {"fetched": 3, "inserted": 2, "linked_symbols": 1}

    def fake_generate_recommendations(*a, **k):
        calls["reco"] += 1
        return {"universe": 300, "filtered": 20, "saved": 10}

    def fake_reconcile_positions(*a, **k):
        calls["reconcile"] += 1
        return {"checked": 1, "closed": 0, "skipped": 1, "details": []}

    monkeypatch.setattr(daily_jobs.naver_news, "build_name_map",
                        fake_build_name_map)
    monkeypatch.setattr(daily_jobs.naver_news, "collect_and_store",
                        fake_collect_and_store)
    monkeypatch.setattr(daily_jobs.recommender, "generate_recommendations",
                        fake_generate_recommendations)
    monkeypatch.setattr(daily_jobs.paper_reconcile, "reconcile_positions",
                        fake_reconcile_positions)

    def fake_check_markets(*a, **k):
        calls["crisis"] += 1
        return {"KR": {"drawdown": -0.05, "deployed_stages": [], "rearmed": False}}

    monkeypatch.setattr(daily_jobs.crisis_protocol, "check_markets",
                        fake_check_markets)

    def fake_paper_entry(*a, **k):
        calls["paper_entry"] += 1
        return {"rec_date": "2026-07-03", "opened": 1, "candidates": 2}

    def fake_stop_update(*a, **k):
        calls["paper_stops"] += 1
        return {"checked": 1, "raised": 1, "skipped": 0}

    monkeypatch.setattr(daily_jobs.paper_trader, "run_paper_entry",
                        fake_paper_entry)
    monkeypatch.setattr(daily_jobs.paper_trader, "run_stop_update",
                        fake_stop_update)

    def fake_snapshot(*a, **k):
        calls["paper_snapshot"] += 1
        return {"date": "2026-07-06", "total_value": 10_000_000}

    monkeypatch.setattr(daily_jobs.paper_trader, "run_daily_snapshot",
                        fake_snapshot)
    return calls


WEEKDAY = "2026-07-06"   # 월요일
SATURDAY = "2026-07-04"  # 토요일


def test_success_records_status_and_detail(db_path, spies):
    """3개 작업 모두 성공 → success 반환 + job_runs에 success + detail JSON 기록."""
    from app.services.daily_jobs import (
        run_catchup, JOB_NEWS, JOB_RECO, JOB_RECONCILE, JOB_CRISIS,
        JOB_PAPER_ENTRY, JOB_PAPER_STOPS, JOB_PAPER_SNAPSHOT,
    )

    result = asyncio.run(run_catchup(db_path=db_path, today=WEEKDAY))

    assert result == {
        JOB_NEWS: "success",
        JOB_RECO: "success",
        JOB_PAPER_ENTRY: "success",
        JOB_PAPER_STOPS: "success",
        JOB_RECONCILE: "success",
        JOB_PAPER_SNAPSHOT: "success",
        JOB_CRISIS: "success",
    }
    assert spies == {"news": 1, "reco": 1, "reconcile": 1, "crisis": 1,
                     "paper_entry": 1, "paper_stops": 1, "paper_snapshot": 1}

    repo = JobRunRepository(db_path)
    assert repo.has_succeeded(JOB_NEWS, WEEKDAY) is True
    assert repo.has_succeeded(JOB_RECO, WEEKDAY) is True
    assert repo.has_succeeded(JOB_RECONCILE, WEEKDAY) is True
    assert repo.has_succeeded(JOB_CRISIS, WEEKDAY) is True

    # detail이 통계 JSON으로 저장됐는지 확인
    from app.db.database import get_connection
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT detail FROM job_runs WHERE job_name=? AND run_date=?",
            (JOB_NEWS, WEEKDAY),
        ).fetchone()
    finally:
        conn.close()
    detail = json.loads(row["detail"])
    assert detail["inserted"] == 2


def test_idempotent_skip_when_already_succeeded(db_path, spies):
    """오늘 이미 success인 작업은 skipped(already), 나머지만 실행."""
    from app.services.daily_jobs import (
        run_catchup, JOB_NEWS, JOB_RECO, JOB_RECONCILE,
    )

    # 뉴스는 이미 오늘 성공했다고 기록
    JobRunRepository(db_path).record(JOB_NEWS, WEEKDAY, "success",
                                     finished_at="2026-07-06T09:00:00")

    result = asyncio.run(run_catchup(db_path=db_path, today=WEEKDAY))

    assert result[JOB_NEWS] == "skipped(already)"
    assert result[JOB_RECO] == "success"
    assert result[JOB_RECONCILE] == "success"
    # 뉴스 작업 함수는 호출되지 않아야 함 (멱등)
    assert spies["news"] == 0
    assert spies["reco"] == 1
    assert spies["reconcile"] == 1


def test_failure_isolation(db_path, monkeypatch):
    """작업 1(뉴스)이 예외를 던져도 작업 2·3 실행 + job_runs에 failure 기록."""
    from app.services import daily_jobs
    from app.services.daily_jobs import (
        run_catchup, JOB_NEWS, JOB_RECO, JOB_RECONCILE,
    )

    calls = {"reco": 0, "reconcile": 0}

    def boom(*a, **k):
        raise RuntimeError("네이버 크롤 실패")

    monkeypatch.setattr(daily_jobs.naver_news, "build_name_map",
                        lambda *a, **k: {})
    monkeypatch.setattr(daily_jobs.naver_news, "collect_and_store", boom)
    monkeypatch.setattr(
        daily_jobs.recommender, "generate_recommendations",
        lambda *a, **k: calls.__setitem__("reco", calls["reco"] + 1)
        or {"universe": 1, "filtered": 1, "saved": 1})
    monkeypatch.setattr(
        daily_jobs.paper_reconcile, "reconcile_positions",
        lambda *a, **k: calls.__setitem__("reconcile", calls["reconcile"] + 1)
        or {"checked": 0, "closed": 0, "skipped": 0, "details": []})
    # 위기 체크·페이퍼 작업은 네트워크 금지 — 성공 스텁으로 대체
    monkeypatch.setattr(daily_jobs.crisis_protocol, "check_markets",
                        lambda *a, **k: {"KR": {"deployed_stages": []}})
    monkeypatch.setattr(daily_jobs.paper_trader, "run_paper_entry",
                        lambda *a, **k: {"opened": 0})
    monkeypatch.setattr(daily_jobs.paper_trader, "run_stop_update",
                        lambda *a, **k: {"checked": 0, "raised": 0, "skipped": 0})
    monkeypatch.setattr(daily_jobs.paper_trader, "run_daily_snapshot",
                        lambda *a, **k: {"total_value": 0})

    result = asyncio.run(run_catchup(db_path=db_path, today=WEEKDAY))

    assert result[JOB_NEWS] == "failure"
    assert result[JOB_RECO] == "success"
    assert result[JOB_RECONCILE] == "success"
    assert calls == {"reco": 1, "reconcile": 1}

    # 뉴스는 failure로 기록(success 아님) — 재실행 대상으로 남아야 함
    repo = JobRunRepository(db_path)
    assert repo.has_succeeded(JOB_NEWS, WEEKDAY) is False

    from app.db.database import get_connection
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT status, detail FROM job_runs WHERE job_name=? AND run_date=?",
            (JOB_NEWS, WEEKDAY),
        ).fetchone()
    finally:
        conn.close()
    assert row["status"] == "failure"
    assert "네이버 크롤 실패" in row["detail"]


class _FakeTask:
    """add_done_callback에 넘어오는 태스크를 흉내내는 최소 스텁."""
    def __init__(self, *, cancelled=False, exc=None):
        self._cancelled = cancelled
        self._exc = exc

    def cancelled(self):
        return self._cancelled

    def exception(self):
        return self._exc


def test_background_done_logs_on_exception(caplog):
    """예외로 끝난 백그라운드 태스크는 logger.error로 크래시를 남긴다."""
    import logging
    from app.services.daily_jobs import _on_background_done

    with caplog.at_level(logging.ERROR):
        _on_background_done(_FakeTask(exc=RuntimeError("루프 폭발")))

    assert any("루프 폭발" in r.message or "루프 폭발" in r.getMessage()
               for r in caplog.records)


def test_background_done_silent_on_success_and_cancel(caplog):
    """정상 종료·취소는 로그를 남기지 않는다."""
    import logging
    from app.services.daily_jobs import _on_background_done

    with caplog.at_level(logging.ERROR):
        _on_background_done(_FakeTask(exc=None))       # 정상 종료
        _on_background_done(_FakeTask(cancelled=True))  # 취소

    assert caplog.records == []


def test_weekend_skips_reco_and_reconcile(db_path, spies):
    """주말이면 추천·정산은 실행하지 않고 success(weekend)로 기록, 뉴스는 수집."""
    from app.services.daily_jobs import (
        run_catchup, JOB_NEWS, JOB_RECO, JOB_RECONCILE,
    )

    result = asyncio.run(run_catchup(db_path=db_path, today=SATURDAY))

    # 뉴스는 주말에도 수집
    assert result[JOB_NEWS] == "success"
    assert spies["news"] == 1
    # 추천·정산 작업 함수는 호출되지 않음
    assert spies["reco"] == 0
    assert spies["reconcile"] == 0
    # 페이퍼 진입/스탑 갱신/스냅샷도 주말엔 실행하지 않음
    assert spies["paper_entry"] == 0
    assert spies["paper_stops"] == 0
    assert spies["paper_snapshot"] == 0
    # 위기 체크는 주말에도 실행 (금요일 폭락 → 주말 기동 시 알림)
    from app.services.daily_jobs import JOB_CRISIS
    assert result[JOB_CRISIS] == "success"
    assert spies["crisis"] == 1

    # 같은 날 재실행을 막기 위해 success로 기록됨
    repo = JobRunRepository(db_path)
    assert repo.has_succeeded(JOB_RECO, SATURDAY) is True
    assert repo.has_succeeded(JOB_RECONCILE, SATURDAY) is True

    from app.db.database import get_connection
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT detail FROM job_runs WHERE job_name=? AND run_date=?",
            (JOB_RECO, SATURDAY),
        ).fetchone()
    finally:
        conn.close()
    assert json.loads(row["detail"]) == {"skipped": "weekend"}

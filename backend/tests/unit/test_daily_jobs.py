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

    calls = {"news": 0, "reco": 0, "reconcile": 0}

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
    return calls


WEEKDAY = "2026-07-06"   # 월요일
SATURDAY = "2026-07-04"  # 토요일


def test_success_records_status_and_detail(db_path, spies):
    """3개 작업 모두 성공 → success 반환 + job_runs에 success + detail JSON 기록."""
    from app.services.daily_jobs import (
        run_catchup, JOB_NEWS, JOB_RECO, JOB_RECONCILE,
    )

    result = asyncio.run(run_catchup(db_path=db_path, today=WEEKDAY))

    assert result == {
        JOB_NEWS: "success",
        JOB_RECO: "success",
        JOB_RECONCILE: "success",
    }
    assert spies == {"news": 1, "reco": 1, "reconcile": 1}

    repo = JobRunRepository(db_path)
    assert repo.has_succeeded(JOB_NEWS, WEEKDAY) is True
    assert repo.has_succeeded(JOB_RECO, WEEKDAY) is True
    assert repo.has_succeeded(JOB_RECONCILE, WEEKDAY) is True

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

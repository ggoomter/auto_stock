"""일별 작업 오케스트레이터 — 서버 기동 시 '오늘 안 돌린 작업'을 따라잡는다.

핵심 계약:
- run_catchup: 멱등(오늘 이미 success면 skip) · 실패 격리(한 작업 예외가 다음 작업을
  막지 않음) · 비동기(블로킹 작업은 asyncio.to_thread로 이벤트 루프 보호).
- run_catchup은 루프를 포함하지 않는 '순수 1회' 함수. 장중 30분 뉴스 재수집 루프는
  start_background_catchup이 run_catchup 뒤에 이어 붙인다 (테스트 용이성).

시간 기준: 서버 로컬 시각을 KST로 가정한다 (datetime.now()).
"""
import asyncio
import json
import logging
from datetime import datetime, time as dtime

from ..db.repositories import (
    JobRunRepository,
    NewsRepository,
    RecommendationRepository,
    PaperTradingRepository,
    SnapshotRepository,
)
from . import naver_news, recommender, paper_reconcile, paper_trader, crisis_protocol

logger = logging.getLogger(__name__)

# 작업 이름 — JobRunRepository의 job_name 키이자 run_catchup 반환 dict의 키
JOB_NEWS = "news_crawl"
JOB_RECO = "recommendations"
JOB_RECONCILE = "paper_reconcile"
JOB_PAPER_ENTRY = "paper_entry"
JOB_PAPER_STOPS = "paper_stop_update"
JOB_PAPER_SNAPSHOT = "paper_snapshot"
JOB_CRISIS = "crisis_check"

# 장중 뉴스 재수집: 평일 09:00~15:30, 30분 간격
_MARKET_OPEN = dtime(9, 0)
_MARKET_CLOSE = dtime(15, 30)
_INTRADAY_INTERVAL_SEC = 1800


def _today_kst() -> str:
    """서버 로컬 시각(KST 가정) 기준 오늘 날짜 'YYYY-MM-DD'."""
    return datetime.now().strftime("%Y-%m-%d")


def _is_weekend(day: str) -> bool:
    """토(5)·일(6) 여부. 주말엔 pykrx가 휴장이라 추천·정산이 무의미."""
    return datetime.strptime(day, "%Y-%m-%d").weekday() >= 5


# --- 개별 작업 (전부 동기 — asyncio.to_thread로 감싸 호출) ---

def _do_news(db_path: str | None) -> dict:
    name_map = naver_news.build_name_map()
    return naver_news.collect_and_store(
        repo=NewsRepository(db_path), name_map=name_map, pages=3)


def _do_reco(db_path: str | None, today: str) -> dict:
    return recommender.generate_recommendations(
        repo=RecommendationRepository(db_path), rec_date=today)


def _do_paper_entry(db_path: str | None, today: str) -> dict:
    from ..core.config import settings
    return paper_trader.run_paper_entry(
        repo=PaperTradingRepository(db_path),
        reco_repo=RecommendationRepository(db_path),
        fetch_daily=paper_reconcile.fetch_daily_pykrx,
        as_of=today,
        initial_capital=settings.PAPER_INITIAL_CAPITAL,
        max_positions=settings.PAPER_MAX_POSITIONS)


def _do_paper_stops(db_path: str | None, today: str) -> dict:
    return paper_trader.run_stop_update(
        repo=PaperTradingRepository(db_path),
        fetch_daily=paper_reconcile.fetch_daily_pykrx,
        as_of=today)


def _do_paper_snapshot(db_path: str | None, today: str) -> dict:
    from ..core.config import settings
    return paper_trader.run_daily_snapshot(
        repo=PaperTradingRepository(db_path),
        snap_repo=SnapshotRepository(db_path),
        fetch_daily=paper_reconcile.fetch_daily_pykrx,
        as_of=today,
        initial_capital=settings.PAPER_INITIAL_CAPITAL)


def _do_crisis(db_path: str | None, today: str) -> dict:
    return crisis_protocol.check_markets(db_path=db_path, today=today)


def _do_reconcile(db_path: str | None, today: str) -> dict:
    # as_of는 '오늘'로 넘긴다. 단, 장중(15:30 이전) 실행 시 오늘 봉의 exit_at이
    # 미래 시각('오늘T15:30:00')이 될 수 있다 (paper_reconcile TODO 참고).
    # 정산은 보수적 규칙이므로 허용하되, 이 특성을 인지하고 운영할 것.
    return paper_reconcile.reconcile_positions(
        repo=PaperTradingRepository(db_path),
        fetch_daily=paper_reconcile.fetch_daily_pykrx,
        as_of=today)


async def _run_job(job_repo: JobRunRepository, job_name: str, today: str,
                   work) -> str:
    """작업 1개를 멱등·격리 실행. work는 통계 dict를 반환하는 동기 콜러블.

    반환: "skipped(already)" | "success" | "failure"
    """
    if job_repo.has_succeeded(job_name, today):
        return "skipped(already)"
    try:
        stats = await asyncio.to_thread(work)
        job_repo.record(job_name, today, "success",
                        detail=json.dumps(stats, ensure_ascii=False),
                        finished_at=datetime.now().isoformat())
        return "success"
    except Exception as exc:  # 실패 격리 — 다음 작업 계속
        logger.error("일별 작업 실패 [%s] %s: %s", today, job_name, exc)
        job_repo.record(job_name, today, "failure",
                        detail=str(exc)[:500],
                        finished_at=datetime.now().isoformat())
        return "failure"


def _skip_weekend(job_repo: JobRunRepository, job_name: str, today: str) -> str:
    """주말 추천·정산: 그날 데이터가 없어 '할 일 없음'이 맞다.

    success + detail='{"skipped": "weekend"}'로 기록해 같은 날 재실행을 막는다.
    (월요일은 run_date가 바뀌므로 자연히 다시 실행된다.)
    """
    if job_repo.has_succeeded(job_name, today):
        return "skipped(already)"
    job_repo.record(job_name, today, "success",
                    detail=json.dumps({"skipped": "weekend"}, ensure_ascii=False),
                    finished_at=datetime.now().isoformat())
    return "success"


async def run_catchup(db_path: str | None = None,
                      today: str | None = None) -> dict:
    """오늘 아직 성공하지 않은 작업만 순서대로(뉴스→추천→정산) 실행하는 순수 1회 함수.

    반환: {job_name: "success" | "failure" | "skipped(already)"}
    """
    if today is None:
        today = _today_kst()
    job_repo = JobRunRepository(db_path)
    weekend = _is_weekend(today)

    results: dict[str, str] = {}

    # 1) 뉴스 — 주말에도 수집
    results[JOB_NEWS] = await _run_job(
        job_repo, JOB_NEWS, today, lambda: _do_news(db_path))

    # 2) 추천 — 주말 skip
    if weekend:
        results[JOB_RECO] = _skip_weekend(job_repo, JOB_RECO, today)
    else:
        results[JOB_RECO] = await _run_job(
            job_repo, JOB_RECO, today, lambda: _do_reco(db_path, today))

    # 3) 페이퍼 진입 — 직전 거래일 추천을 오늘 시가에 가상 매수 (주말 skip)
    if weekend:
        results[JOB_PAPER_ENTRY] = _skip_weekend(job_repo, JOB_PAPER_ENTRY, today)
    else:
        results[JOB_PAPER_ENTRY] = await _run_job(
            job_repo, JOB_PAPER_ENTRY, today, lambda: _do_paper_entry(db_path, today))

    # 4) 페이퍼 스탑 갱신 — 샹들리에·200일선으로 손절선 인상 (정산 전에 실행)
    if weekend:
        results[JOB_PAPER_STOPS] = _skip_weekend(job_repo, JOB_PAPER_STOPS, today)
    else:
        results[JOB_PAPER_STOPS] = await _run_job(
            job_repo, JOB_PAPER_STOPS, today, lambda: _do_paper_stops(db_path, today))

    # 5) 정산 — 주말 skip
    if weekend:
        results[JOB_RECONCILE] = _skip_weekend(job_repo, JOB_RECONCILE, today)
    else:
        results[JOB_RECONCILE] = await _run_job(
            job_repo, JOB_RECONCILE, today, lambda: _do_reconcile(db_path, today))

    # 6) 일별 자산 스냅샷 — 수익 곡선 기록 (정산 이후 최종 상태 기준, 주말 skip)
    if weekend:
        results[JOB_PAPER_SNAPSHOT] = _skip_weekend(job_repo, JOB_PAPER_SNAPSHOT, today)
    else:
        results[JOB_PAPER_SNAPSHOT] = await _run_job(
            job_repo, JOB_PAPER_SNAPSHOT, today, lambda: _do_paper_snapshot(db_path, today))

    # 7) 위기 매수 프로토콜 — 폭락은 요일을 가리지 않으므로 주말에도 체크
    #    (금요일 폭락을 주말 기동 시 알림받을 수 있어야 함)
    results[JOB_CRISIS] = await _run_job(
        job_repo, JOB_CRISIS, today, lambda: _do_crisis(db_path, today))

    return results


def _is_market_hours(now: datetime) -> bool:
    """평일 09:00~15:30 여부 (장중 뉴스 재수집 조건)."""
    if now.weekday() >= 5:
        return False
    return _MARKET_OPEN <= now.time() <= _MARKET_CLOSE


async def intraday_news_loop(db_path: str | None = None,
                             interval_sec: int = _INTRADAY_INTERVAL_SEC) -> None:
    """장중(평일 09:00~15:30) 30분 간격으로 뉴스만 재수집. 장외면 즉시 종료.

    루프 내 예외는 logger.error 후 계속 (한 번 실패로 장중 갱신이 끊기지 않게).
    """
    while _is_market_hours(datetime.now()):
        try:
            await asyncio.to_thread(_do_news, db_path)
        except Exception as exc:
            logger.error("장중 뉴스 재수집 실패: %s", exc)
        await asyncio.sleep(interval_sec)


async def _catchup_then_intraday(db_path: str | None = None) -> None:
    """run_catchup → intraday_news_loop 순서로 이어 실행하는 백그라운드 태스크 본체."""
    try:
        await run_catchup(db_path=db_path)
    except Exception as exc:  # 오케스트레이터 전체 실패도 서버를 죽이지 않게
        logger.error("run_catchup 전체 실패: %s", exc)
    await intraday_news_loop(db_path=db_path)


# 백그라운드 태스크 참조 보관 — GC가 실행 중 태스크를 수거하지 못하게 강한 참조 유지.
# (asyncio는 태스크에 강한 참조가 없으면 임의로 회수할 수 있다.)
_background_task: "asyncio.Task | None" = None


def _on_background_done(task: "asyncio.Task") -> None:
    """백그라운드 태스크 완료 콜백 — 예외로 끝났을 때만 로깅한다.

    정상 종료·취소는 무로그. 예외는 add_done_callback이 삼키므로 여기서 명시적으로
    꺼내 logger.error로 남긴다 (조용한 크래시 방지)."""
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        logger.error("백그라운드 catch-up 태스크 크래시: %s", exc)


def start_background_catchup(db_path: str | None = None) -> None:
    """main.py startup에서 호출 — 서버 기동을 블로킹하지 않는 백그라운드 태스크 등록.

    startup은 코루틴이라 실행 중인 이벤트 루프가 존재한다.
    """
    global _background_task
    loop = asyncio.get_event_loop()
    _background_task = loop.create_task(_catchup_then_intraday(db_path))
    _background_task.add_done_callback(_on_background_done)

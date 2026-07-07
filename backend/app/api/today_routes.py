"""
/today API 라우트
오늘의 뉴스·추천 종목·작업 상태 조회 (읽기 전용)

저장소 접근은 모듈 레벨 팩토리 함수(_get_news_repo 등)로 분리한다.
전역 DEFAULT_DB_PATH 때문에 TestClient에서 tmp DB 주입이 어려우므로,
테스트에서 이 팩토리들을 monkeypatch 해 tmp DB 저장소를 주입한다.
"""
import asyncio
import json
from datetime import date, datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query

from ..core.config import settings
from ..core.logging_config import logger
from ..db.repositories import (
    NewsRepository,
    RecommendationRepository,
    JobRunRepository,
)

router = APIRouter()

# 일반 사용자에게 노출하는 안전한 500 메시지 (내부 예외 문자열 은닉)
_GENERIC_ERROR = "일시적인 오류가 발생했습니다"
_DISCLAIMER = "교육·연구용 정보로 투자 권유가 아닙니다"


# ── 저장소 팩토리 (테스트에서 monkeypatch 대상) ──
def _get_news_repo() -> NewsRepository:
    return NewsRepository(settings.DB_PATH)


def _get_reco_repo() -> RecommendationRepository:
    return RecommendationRepository(settings.DB_PATH)


def _get_job_repo() -> JobRunRepository:
    return JobRunRepository(settings.DB_PATH)


def _today_str() -> str:
    """서버 로컬 기준 오늘 (YYYY-MM-DD)."""
    return date.today().isoformat()


@router.get("/today/news")
async def get_today_news(
    date: str | None = Query(default=None),
    symbol: str | None = Query(default=None),
):
    """오늘(또는 지정일)의 뉴스 기사 조회.

    symbol이 주어지면 date 필터는 무시하고 해당 종목 최근 20건을 반환한다
    (단순 우선 정책). symbol이 없으면 date(기본 오늘) 기준으로 조회한다.
    """
    try:
        repo = _get_news_repo()
        if symbol:
            # symbol 지정 시 date 무시, 최근 20건 (docstring 명시 정책)
            articles = repo.list_for_symbol(symbol)
            resolved_date = None
        else:
            resolved_date = date or _today_str()
            articles = repo.list_by_date(resolved_date)

        return {
            "date": resolved_date,
            "count": len(articles),
            "articles": [
                {
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "source": a.get("source"),
                    "published_at": a.get("published_at"),
                    "sentiment": a.get("sentiment"),
                    "symbols": a.get("symbols", []),
                }
                for a in articles
            ],
        }
    except Exception as e:
        logger.error(f"오늘의 뉴스 조회 실패 (date={date}, symbol={symbol}): {e}")
        raise HTTPException(status_code=500, detail=_GENERIC_ERROR)


@router.get("/today/recommendations")
async def get_today_recommendations(date: str | None = Query(default=None)):
    """오늘(또는 지정일)의 추천 종목 조회 — score 내림차순 (저장소가 정렬·역직렬화)."""
    try:
        repo = _get_reco_repo()
        resolved_date = date or repo.latest_date()
        if resolved_date is None:
            recs = []
        else:
            recs = repo.list_by_date(resolved_date)

        # 분석 시점 = 해당 날짜 추천 작업(job_runs)의 성공 완료 시각.
        # "오늘의 추천"이 언제 기준 데이터인지 사용자에게 명시하기 위함.
        analyzed_at = None
        if resolved_date is not None:
            for run in _get_job_repo().get_runs(resolved_date):
                if run.get("job_name") == "recommendations" and run.get("status") == "success":
                    analyzed_at = run.get("finished_at")

        return {
            "date": resolved_date,
            "analyzed_at": analyzed_at,
            "count": len(recs),
            "disclaimer": _DISCLAIMER,
            "recommendations": [
                {
                    "symbol": r.get("symbol"),
                    "name": r.get("name"),
                    "score": r.get("score"),
                    "passed_conditions": r.get("passed_conditions", []),
                    "technical_signals": r.get("technical_signals", []),
                }
                for r in recs
            ],
        }
    except Exception as e:
        logger.error(f"오늘의 추천 조회 실패 (date={date}): {e}")
        raise HTTPException(status_code=500, detail=_GENERIC_ERROR)


# ── 온디맨드 추천 갱신 ("지금 매수 추천" 버튼) ──
# 동시 실행 방지용 모듈 상태. 프로세스 내 단일 워커 가정(uvicorn 기본).
_refresh_state = {"running": False, "started_at": None, "error": None}


async def _do_refresh_recommendations(today: str) -> None:
    """추천 파이프라인을 백그라운드에서 1회 실행하고 job_runs를 갱신한다."""
    from ..services import recommender  # 지연 임포트 — pykrx 임포트 실패 격리
    try:
        stats = await asyncio.to_thread(
            recommender.generate_recommendations,
            RecommendationRepository(settings.DB_PATH), today)
        JobRunRepository(settings.DB_PATH).record(
            "recommendations", today, "success",
            detail=json.dumps(stats, ensure_ascii=False),
            finished_at=datetime.now().isoformat())
    except Exception as exc:  # noqa: BLE001 - 실패는 상태로 노출, 서버는 계속
        logger.error(f"온디맨드 추천 갱신 실패: {exc}")
        _refresh_state["error"] = str(exc)[:200]
    finally:
        _refresh_state["running"] = False


@router.post("/today/refresh-recommendations")
async def refresh_recommendations(background_tasks: BackgroundTasks):
    """지금 매수 추천 재계산 시작 (비동기, 약 30~90초 소요).

    진행 상태는 GET /today/refresh-status 로 폴링한다.
    """
    if _refresh_state["running"]:
        return {"status": "already_running",
                "started_at": _refresh_state["started_at"]}
    _refresh_state.update(running=True, error=None,
                          started_at=datetime.now().isoformat())
    background_tasks.add_task(_do_refresh_recommendations, _today_str())
    return {"status": "started", "started_at": _refresh_state["started_at"]}


@router.get("/today/refresh-status")
async def get_refresh_status():
    """온디맨드 추천 갱신 진행 상태 (프론트 버튼 폴링용)."""
    return dict(_refresh_state)


@router.get("/today/status")
async def get_today_status():
    """오늘 작업 실행 상태 — 프론트 '수집 중/실패 사유' 표시용."""
    try:
        today = _today_str()
        repo = _get_job_repo()
        runs = repo.get_runs(today)
        jobs = {
            run["job_name"]: {
                "status": run.get("status"),
                "detail": run.get("detail"),
                "finished_at": run.get("finished_at"),
            }
            for run in runs
        }
        return {"date": today, "jobs": jobs}
    except Exception as e:
        logger.error(f"오늘의 작업 상태 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=_GENERIC_ERROR)

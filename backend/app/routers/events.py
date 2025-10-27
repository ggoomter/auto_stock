"""
이벤트 관리 API 엔드포인트

자동 수집된 이벤트 조회 및 수동 업데이트 기능 제공
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from ..services.event_scheduler import (
    load_events_from_file,
    manual_update,
    save_events_to_file
)
from ..services.news_crawler import NewsCrawler

router = APIRouter(prefix="/events", tags=["Events"])
logger = logging.getLogger(__name__)


@router.get("/global", summary="글로벌 이벤트 조회")
async def get_global_events(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100
):
    """
    자동 수집된 글로벌 경제/정치 이벤트 조회

    Args:
        from_date: 시작일 (YYYY-MM-DD)
        to_date: 종료일 (YYYY-MM-DD)
        category: 카테고리 필터 (crisis, election, policy, etc.)
        limit: 최대 개수

    Returns:
        이벤트 리스트
    """
    try:
        events = load_events_from_file('global_events.json')

        # 날짜 필터
        if from_date:
            events = [e for e in events if e['date'] >= from_date]
        if to_date:
            events = [e for e in events if e['date'] <= to_date]

        # 카테고리 필터
        if category:
            events = [e for e in events if e['category'] == category]

        # 제한
        events = events[:limit]

        return {
            'success': True,
            'count': len(events),
            'events': events
        }

    except Exception as e:
        logger.error(f"이벤트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{symbol}", summary="종목별 이벤트 조회")
async def get_company_events(
    symbol: str,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 50
):
    """
    특정 종목 관련 이벤트 조회

    Args:
        symbol: 종목 심볼 (예: AAPL)
        from_date: 시작일
        to_date: 종료일
        limit: 최대 개수

    Returns:
        종목 이벤트 리스트
    """
    try:
        filename = f'{symbol.upper()}_events.json'
        events = load_events_from_file(filename)

        # 날짜 필터
        if from_date:
            events = [e for e in events if e['date'] >= from_date]
        if to_date:
            events = [e for e in events if e['date'] <= to_date]

        # 제한
        events = events[:limit]

        return {
            'success': True,
            'symbol': symbol.upper(),
            'count': len(events),
            'events': events
        }

    except Exception as e:
        logger.error(f"{symbol} 이벤트 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update/manual", summary="수동 업데이트 실행")
async def trigger_manual_update(background_tasks: BackgroundTasks):
    """
    이벤트 수동 업데이트

    백그라운드 작업으로 뉴스 크롤링을 즉시 실행합니다.
    스케줄러를 기다리지 않고 즉시 업데이트가 필요할 때 사용.

    Returns:
        작업 시작 메시지
    """
    try:
        background_tasks.add_task(manual_update)

        return {
            'success': True,
            'message': '백그라운드에서 이벤트 업데이트 시작',
            'note': '완료까지 1-2분 소요될 수 있습니다.'
        }

    except Exception as e:
        logger.error(f"수동 업데이트 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/crawl/test", summary="테스트 크롤링 (개발용)")
async def test_crawl(days_back: int = 1):
    """
    테스트용 크롤링 (저장하지 않음)

    Args:
        days_back: 몇 일 전까지 수집할지

    Returns:
        수집된 이벤트 (저장 안 함)
    """
    try:
        crawler = NewsCrawler()
        events = crawler.fetch_daily_events(days_back=days_back)

        return {
            'success': True,
            'count': len(events),
            'events': events[:10],  # 상위 10개만 반환
            'note': '테스트 모드: 데이터가 저장되지 않았습니다.'
        }

    except Exception as e:
        logger.error(f"테스트 크롤링 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", summary="이벤트 통계")
async def get_event_stats():
    """
    수집된 이벤트 통계 정보

    Returns:
        글로벌/종목별 이벤트 개수, 최신 업데이트 시각 등
    """
    try:
        global_events = load_events_from_file('global_events.json')

        # 종목별 이벤트 개수
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
        company_stats = {}

        for symbol in symbols:
            filename = f'{symbol}_events.json'
            events = load_events_from_file(filename)
            company_stats[symbol] = {
                'count': len(events),
                'latest_date': events[0]['date'] if events else None
            }

        # 카테고리별 분포
        category_dist = {}
        for event in global_events:
            cat = event['category']
            category_dist[cat] = category_dist.get(cat, 0) + 1

        return {
            'success': True,
            'global_events': {
                'total': len(global_events),
                'latest_date': global_events[0]['date'] if global_events else None,
                'category_distribution': category_dist
            },
            'company_events': company_stats
        }

    except Exception as e:
        logger.error(f"통계 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

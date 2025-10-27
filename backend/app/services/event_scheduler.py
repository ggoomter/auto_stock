"""
자동 이벤트 수집 스케줄러

매일 자정에 자동으로 뉴스를 크롤링하여 이벤트를 업데이트합니다.
APScheduler를 사용하여 백그라운드에서 실행됩니다.

사용법:
    from app.services.event_scheduler import start_scheduler
    start_scheduler()  # FastAPI 시작 시 호출
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import json
import os

from .news_crawler import NewsCrawler

logger = logging.getLogger(__name__)

# 스케줄러 인스턴스
scheduler = BackgroundScheduler()

# 이벤트 저장 경로
EVENTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'events')
os.makedirs(EVENTS_DIR, exist_ok=True)


def save_events_to_file(events: List[Dict], filename: str):
    """이벤트를 JSON 파일로 저장"""
    filepath = os.path.join(EVENTS_DIR, filename)

    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
        logger.info(f"이벤트 저장 완료: {filepath} ({len(events)}개)")
    except Exception as e:
        logger.error(f"이벤트 저장 실패: {e}")


def load_events_from_file(filename: str) -> List[Dict]:
    """JSON 파일에서 이벤트 로드"""
    filepath = os.path.join(EVENTS_DIR, filename)

    if not os.path.exists(filepath):
        return []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            events = json.load(f)
        logger.info(f"이벤트 로드 완료: {filepath} ({len(events)}개)")
        return events
    except Exception as e:
        logger.error(f"이벤트 로드 실패: {e}")
        return []


def daily_global_events_update():
    """
    매일 글로벌 이벤트 업데이트

    매일 자정(00:00)에 실행되어 전날 뉴스를 수집합니다.
    """
    logger.info("===== 일일 글로벌 이벤트 업데이트 시작 =====")

    try:
        crawler = NewsCrawler()

        # 어제 하루 이벤트 수집
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        events = crawler.fetch_daily_events(days_back=1)

        if events:
            # 기존 이벤트 로드
            all_events = load_events_from_file('global_events.json')

            # 중복 제거 (날짜 + 제목 기준)
            existing_keys = {(e['date'], e['title']) for e in all_events}
            new_events = [
                e for e in events
                if (e['date'], e['title']) not in existing_keys
            ]

            if new_events:
                all_events.extend(new_events)
                all_events.sort(key=lambda x: x['date'], reverse=True)

                # 저장
                save_events_to_file(all_events, 'global_events.json')
                logger.info(f"신규 이벤트 {len(new_events)}개 추가 (전체: {len(all_events)}개)")
            else:
                logger.info("신규 이벤트 없음")
        else:
            logger.warning("수집된 이벤트 없음")

    except Exception as e:
        logger.error(f"글로벌 이벤트 업데이트 실패: {e}")

    logger.info("===== 일일 글로벌 이벤트 업데이트 완료 =====\n")


def daily_company_events_update():
    """
    매일 주요 종목 이벤트 업데이트

    매일 자정 10분(00:10)에 실행됩니다.
    """
    logger.info("===== 일일 종목별 이벤트 업데이트 시작 =====")

    # 주요 종목 리스트
    symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
    companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'NVIDIA', 'Tesla', 'Meta']

    try:
        crawler = NewsCrawler()

        # 최근 3일 이벤트 수집 (놓친 것 포함)
        company_events = crawler.fetch_company_events_batch(
            symbols=symbols,
            company_names=companies,
            days_back=3
        )

        for symbol, events in company_events.items():
            if events:
                # 기존 이벤트 로드
                filename = f'{symbol}_events.json'
                all_events = load_events_from_file(filename)

                # 중복 제거
                existing_keys = {(e['date'], e['title']) for e in all_events}
                new_events = [
                    e for e in events
                    if (e['date'], e['title']) not in existing_keys
                ]

                if new_events:
                    all_events.extend(new_events)
                    all_events.sort(key=lambda x: x['date'], reverse=True)

                    # 최근 100개만 유지
                    all_events = all_events[:100]

                    save_events_to_file(all_events, filename)
                    logger.info(f"{symbol}: 신규 {len(new_events)}개 추가")

    except Exception as e:
        logger.error(f"종목별 이벤트 업데이트 실패: {e}")

    logger.info("===== 일일 종목별 이벤트 업데이트 완료 =====\n")


def weekly_cleanup():
    """
    주간 데이터 정리

    매주 일요일 02:00에 실행되어 오래된 데이터를 정리합니다.
    """
    logger.info("===== 주간 데이터 정리 시작 =====")

    try:
        # 글로벌 이벤트: 최근 3년만 유지
        three_years_ago = (datetime.now() - timedelta(days=365 * 3)).strftime('%Y-%m-%d')

        all_events = load_events_from_file('global_events.json')
        filtered_events = [e for e in all_events if e['date'] >= three_years_ago]

        if len(filtered_events) < len(all_events):
            save_events_to_file(filtered_events, 'global_events.json')
            logger.info(f"글로벌 이벤트 {len(all_events) - len(filtered_events)}개 삭제")

    except Exception as e:
        logger.error(f"주간 정리 실패: {e}")

    logger.info("===== 주간 데이터 정리 완료 =====\n")


def start_scheduler():
    """
    스케줄러 시작

    FastAPI 앱 시작 시 호출하여 백그라운드 작업을 등록합니다.
    """
    if scheduler.running:
        logger.warning("스케줄러가 이미 실행 중입니다.")
        return

    # 1. 매일 자정 00:00 - 글로벌 이벤트 수집
    scheduler.add_job(
        daily_global_events_update,
        trigger=CronTrigger(hour=0, minute=0),
        id='daily_global_events',
        name='일일 글로벌 이벤트 수집',
        replace_existing=True
    )

    # 2. 매일 자정 00:10 - 종목별 이벤트 수집
    scheduler.add_job(
        daily_company_events_update,
        trigger=CronTrigger(hour=0, minute=10),
        id='daily_company_events',
        name='일일 종목별 이벤트 수집',
        replace_existing=True
    )

    # 3. 매주 일요일 02:00 - 데이터 정리
    scheduler.add_job(
        weekly_cleanup,
        trigger=CronTrigger(day_of_week='sun', hour=2, minute=0),
        id='weekly_cleanup',
        name='주간 데이터 정리',
        replace_existing=True
    )

    # 스케줄러 시작
    scheduler.start()
    logger.info("✅ 이벤트 자동 수집 스케줄러 시작")
    logger.info("  - 매일 00:00: 글로벌 이벤트 수집")
    logger.info("  - 매일 00:10: 종목별 이벤트 수집")
    logger.info("  - 매주 일요일 02:00: 데이터 정리")

    # 시작 시 즉시 한 번 실행 (테스트용)
    # daily_global_events_update()


def stop_scheduler():
    """스케줄러 중지"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("스케줄러 중지됨")


def manual_update():
    """
    수동 업데이트 실행

    테스트 또는 즉시 업데이트가 필요할 때 호출
    """
    logger.info("===== 수동 업데이트 시작 =====")
    daily_global_events_update()
    daily_company_events_update()
    logger.info("===== 수동 업데이트 완료 =====")


# 개발 모드에서 직접 실행
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 수동 업데이트 테스트
    manual_update()

    # 또는 스케줄러 시작 (프로그램 종료 방지)
    # start_scheduler()
    # import time
    # while True:
    #     time.sleep(60)

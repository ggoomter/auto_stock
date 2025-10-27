"""
자동 뉴스 크롤링 및 이벤트 수집 시스템

News API를 사용하여 매일 금융/경제 뉴스를 수집하고
AI로 자동 분류 및 감성 분석을 수행합니다.

필수 환경 변수:
- NEWS_API_KEY: https://newsapi.org에서 발급 (무료 100 requests/day)
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class NewsCrawler:
    """뉴스 자동 수집 및 이벤트 생성"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWS_API_KEY')
        if not self.api_key:
            raise ValueError("NEWS_API_KEY 환경 변수가 설정되지 않았습니다.")

        self.base_url = "https://newsapi.org/v2/everything"

    def fetch_financial_news(
        self,
        from_date: str,
        to_date: str,
        keywords: List[str] = None,
        language: str = 'en'
    ) -> List[Dict]:
        """
        News API에서 금융 뉴스 가져오기

        Args:
            from_date: 시작일 (YYYY-MM-DD)
            to_date: 종료일 (YYYY-MM-DD)
            keywords: 검색 키워드 리스트
            language: 언어 코드 (en, ko)

        Returns:
            뉴스 기사 리스트
        """
        if keywords is None:
            keywords = [
                "stock market", "federal reserve", "interest rate",
                "inflation", "GDP", "unemployment", "earnings",
                "merger", "acquisition", "IPO", "bankruptcy"
            ]

        # 키워드를 OR로 연결
        query = " OR ".join(keywords)

        params = {
            'q': query,
            'from': from_date,
            'to': to_date,
            'language': language,
            'sortBy': 'relevancy',
            'apiKey': self.api_key,
            'pageSize': 100,  # 최대 100개
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'ok':
                logger.info(f"뉴스 {data['totalResults']}개 중 {len(data['articles'])}개 수집 성공")
                return data['articles']
            else:
                logger.error(f"News API 오류: {data.get('message')}")
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"뉴스 수집 실패: {e}")
            return []

    def fetch_company_news(
        self,
        symbol: str,
        company_name: str,
        from_date: str,
        to_date: str
    ) -> List[Dict]:
        """
        특정 종목 관련 뉴스 가져오기

        Args:
            symbol: 종목 심볼 (예: AAPL)
            company_name: 회사명 (예: Apple)
            from_date: 시작일
            to_date: 종료일

        Returns:
            뉴스 기사 리스트
        """
        query = f'"{company_name}" OR {symbol}'

        params = {
            'q': query,
            'from': from_date,
            'to': to_date,
            'language': 'en',
            'sortBy': 'relevancy',
            'apiKey': self.api_key,
            'pageSize': 50,
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data['status'] == 'ok':
                return data['articles']
            else:
                return []

        except requests.exceptions.RequestException as e:
            logger.error(f"{symbol} 뉴스 수집 실패: {e}")
            return []

    def classify_category(self, title: str, description: str = "") -> str:
        """
        뉴스 카테고리 분류

        Returns:
            'crisis' | 'election' | 'policy' | 'pandemic' | 'war' | 'tech'
        """
        text = f"{title} {description}".lower()

        # 카테고리별 키워드 매칭
        if any(word in text for word in [
            'election', 'vote', 'president', 'congress', 'senate', 'campaign'
        ]):
            return 'election'

        elif any(word in text for word in [
            'fed', 'federal reserve', 'interest rate', 'monetary policy',
            'central bank', 'powell', 'rate hike', 'rate cut', 'inflation'
        ]):
            return 'policy'

        elif any(word in text for word in [
            'war', 'conflict', 'military', 'invasion', 'attack', 'sanction'
        ]):
            return 'war'

        elif any(word in text for word in [
            'covid', 'pandemic', 'virus', 'outbreak', 'lockdown', 'vaccine'
        ]):
            return 'pandemic'

        elif any(word in text for word in [
            'crash', 'crisis', 'bankruptcy', 'collapse', 'default',
            'recession', 'bear market', 'plunge', 'tumble'
        ]):
            return 'crisis'

        else:
            return 'tech'  # 기본값

    def analyze_sentiment(self, title: str, description: str = "") -> str:
        """
        간단한 감성 분석 (키워드 기반)

        프로덕션에서는 FinBERT 같은 AI 모델 사용 권장

        Returns:
            'positive' | 'negative' | 'neutral'
        """
        text = f"{title} {description}".lower()

        positive_words = [
            'surge', 'soar', 'rally', 'gain', 'rise', 'jump', 'boost',
            'record', 'profit', 'growth', 'success', 'breakthrough',
            'strong', 'beat', 'exceed', 'upgrade', 'optimistic'
        ]

        negative_words = [
            'fall', 'drop', 'plunge', 'crash', 'tumble', 'decline',
            'loss', 'crisis', 'fear', 'concern', 'warning', 'risk',
            'weak', 'miss', 'disappoint', 'downgrade', 'pessimistic',
            'bankruptcy', 'layoff', 'cut'
        ]

        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count and positive_count >= 2:
            return 'positive'
        elif negative_count > positive_count and negative_count >= 2:
            return 'negative'
        else:
            return 'neutral'

    def convert_to_events(self, articles: List[Dict]) -> List[Dict]:
        """
        뉴스 기사를 이벤트 형식으로 변환

        Returns:
            GlobalEvent 형식의 이벤트 리스트
        """
        events = []

        for article in articles:
            # 중복 제거: 제목이 너무 짧거나 None인 경우 스킵
            if not article.get('title') or len(article['title']) < 10:
                continue

            # 날짜 파싱
            published_at = article.get('publishedAt', '')
            date = published_at.split('T')[0] if published_at else datetime.now().strftime('%Y-%m-%d')

            title = article['title']
            description = article.get('description', '') or article.get('content', '')

            # 카테고리 및 감성 분석
            category = self.classify_category(title, description)
            impact = self.analyze_sentiment(title, description)

            event = {
                'date': date,
                'title': title[:100],  # 제목 길이 제한
                'description': description[:200] if description else title,
                'category': category,
                'impact': impact,
                'source': article.get('source', {}).get('name', 'Unknown'),
                'url': article.get('url', ''),
            }

            events.append(event)

        # 날짜순 정렬
        events.sort(key=lambda x: x['date'], reverse=True)

        return events

    def fetch_daily_events(self, days_back: int = 1) -> List[Dict]:
        """
        최근 N일간의 이벤트 자동 수집

        Args:
            days_back: 몇 일 전까지 수집할지 (기본 1일)

        Returns:
            이벤트 리스트
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')

        logger.info(f"뉴스 수집 시작: {from_date} ~ {to_date}")

        # 글로벌 금융 뉴스
        articles = self.fetch_financial_news(from_date, to_date)

        # 이벤트로 변환
        events = self.convert_to_events(articles)

        logger.info(f"이벤트 {len(events)}개 생성 완료")

        return events

    def fetch_company_events_batch(
        self,
        symbols: List[str],
        company_names: List[str],
        days_back: int = 1
    ) -> Dict[str, List[Dict]]:
        """
        여러 종목의 이벤트를 일괄 수집

        Args:
            symbols: 종목 심볼 리스트
            company_names: 회사명 리스트
            days_back: 수집 기간

        Returns:
            {symbol: [events]} 딕셔너리
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        from_date = start_date.strftime('%Y-%m-%d')
        to_date = end_date.strftime('%Y-%m-%d')

        result = {}

        for symbol, company_name in zip(symbols, company_names):
            logger.info(f"{symbol} ({company_name}) 뉴스 수집 중...")

            articles = self.fetch_company_news(
                symbol=symbol,
                company_name=company_name,
                from_date=from_date,
                to_date=to_date
            )

            events = self.convert_to_events(articles)
            result[symbol] = events

        return result


# 사용 예시
if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.INFO)

    # API 키는 환경 변수에서 가져옴
    crawler = NewsCrawler()

    # 어제 하루 글로벌 이벤트 수집
    print("=== 글로벌 이벤트 수집 ===")
    global_events = crawler.fetch_daily_events(days_back=1)

    for event in global_events[:5]:  # 상위 5개만 출력
        print(f"\n날짜: {event['date']}")
        print(f"제목: {event['title']}")
        print(f"카테고리: {event['category']} | 영향: {event['impact']}")
        print(f"출처: {event['source']}")

    # 주요 종목 이벤트 수집
    print("\n\n=== 종목별 이벤트 수집 ===")
    symbols = ['AAPL', 'TSLA', 'NVDA']
    companies = ['Apple', 'Tesla', 'NVIDIA']

    company_events = crawler.fetch_company_events_batch(
        symbols=symbols,
        company_names=companies,
        days_back=3
    )

    for symbol, events in company_events.items():
        print(f"\n{symbol}: {len(events)}개 이벤트")
        if events:
            print(f"  최신: {events[0]['title']}")

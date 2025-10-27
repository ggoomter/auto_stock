# 실제 데이터 연동 가이드

현재 `frontend/src/data/globalEvents.ts`는 **샘플 데모 데이터**입니다.
실제 투자 서비스를 만들려면 아래 API들을 사용하세요.

## 1. 주가 데이터 (Stock Price Data)

### Alpha Vantage (무료 플랜 있음)
```bash
# 설치
npm install axios

# API 키 발급
https://www.alphavantage.co/support/#api-key
```

```typescript
// backend/app/services/stock_data.py
import requests

def get_stock_data(symbol: str, start_date: str, end_date: str):
    API_KEY = 'YOUR_ALPHA_VANTAGE_KEY'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={API_KEY}'

    response = requests.get(url)
    data = response.json()

    # OHLC 데이터 추출
    time_series = data.get('Time Series (Daily)', {})
    return time_series
```

### Yahoo Finance (무료, 비공식)
```bash
pip install yfinance
```

```python
import yfinance as yf

def get_stock_data(symbol: str, start_date: str, end_date: str):
    stock = yf.Ticker(symbol)
    df = stock.history(start=start_date, end=end_date)

    # DataFrame에 이미 Open, High, Low, Close, Volume 포함
    return df
```

## 2. 뉴스 및 이벤트 데이터

### News API (뉴스 데이터)
```bash
# API 키 발급
https://newsapi.org/

# 무료 플랜: 100 requests/day
```

```typescript
// frontend/src/services/news.ts
const NEWS_API_KEY = 'YOUR_NEWS_API_KEY';

export async function getFinancialNews(keyword: string, from: string, to: string) {
  const url = `https://newsapi.org/v2/everything?q=${keyword}&from=${from}&to=${to}&apiKey=${NEWS_API_KEY}`;

  const response = await fetch(url);
  const data = await response.json();

  return data.articles.map(article => ({
    date: article.publishedAt.split('T')[0],
    title: article.title,
    description: article.description,
    category: 'news',
    impact: 'neutral' // AI로 분석 필요
  }));
}
```

### Finnhub (금융 뉴스 + 이벤트)
```bash
# API 키 발급
https://finnhub.io/

# 무료 플랜: 60 API calls/minute
```

```python
import requests

def get_company_events(symbol: str, from_date: str, to_date: str):
    API_KEY = 'YOUR_FINNHUB_KEY'
    url = f'https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={API_KEY}'

    response = requests.get(url)
    news = response.json()

    return [{
        'date': item['datetime'],
        'title': item['headline'],
        'description': item['summary'],
        'category': 'news',
        'impact': 'neutral'
    } for item in news]
```

## 3. 경제 캘린더 (Economic Events)

### Trading Economics API
```bash
# API 키 발급 (유료)
https://tradingeconomics.com/api
```

```python
import tradingeconomics as te

te.login('YOUR_API_KEY')

# Fed 금리 결정, 고용지표 등
calendar = te.getCalendar(country='United States', category='Interest Rate')
```

### FRED API (연준 경제 데이터)
```bash
# API 키 발급 (무료)
https://fred.stlouisfed.org/docs/api/api_key.html
```

```python
from fredapi import Fred

fred = Fred(api_key='YOUR_FRED_API_KEY')

# 연방 기준 금리
interest_rate = fred.get_series('FEDFUNDS')

# 실업률
unemployment = fred.get_series('UNRATE')
```

## 4. 실시간 업데이트

### WebSocket 연결 (Finnhub)
```typescript
// frontend/src/services/realtime.ts
const socket = new WebSocket('wss://ws.finnhub.io?token=YOUR_API_KEY');

socket.addEventListener('open', () => {
  socket.send(JSON.stringify({'type':'subscribe', 'symbol': 'AAPL'}));
});

socket.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  console.log('실시간 주가:', data);
});
```

## 5. 백엔드 통합 예시

```python
# backend/app/services/data_provider.py
from typing import List, Dict
import yfinance as yf
import requests
from datetime import datetime

class DataProvider:
    def __init__(self):
        self.news_api_key = 'YOUR_NEWS_API_KEY'
        self.finnhub_key = 'YOUR_FINNHUB_KEY'

    def get_stock_ohlc(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """주가 OHLC 데이터"""
        stock = yf.Ticker(symbol)
        return stock.history(start=start, end=end)

    def get_global_events(self, from_date: str, to_date: str) -> List[Dict]:
        """글로벌 경제/정치 이벤트"""
        # News API 사용
        url = f'https://newsapi.org/v2/everything?q=economy OR politics&from={from_date}&to={to_date}&apiKey={self.news_api_key}'
        response = requests.get(url)
        articles = response.json().get('articles', [])

        events = []
        for article in articles:
            events.append({
                'date': article['publishedAt'][:10],
                'title': article['title'],
                'description': article['description'] or '',
                'category': self._classify_category(article['title']),
                'impact': self._analyze_sentiment(article['title'])
            })

        return events

    def get_company_events(self, symbol: str, from_date: str, to_date: str) -> List[Dict]:
        """종목별 이벤트"""
        url = f'https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={self.finnhub_key}'
        response = requests.get(url)
        news = response.json()

        return [{
            'date': datetime.fromtimestamp(item['datetime']).strftime('%Y-%m-%d'),
            'title': item['headline'],
            'description': item['summary'],
            'category': 'company',
            'impact': self._analyze_sentiment(item['headline'])
        } for item in news[:50]]  # 최근 50개만

    def _classify_category(self, text: str) -> str:
        """텍스트 기반 카테고리 분류"""
        text_lower = text.lower()
        if 'election' in text_lower or 'vote' in text_lower:
            return 'election'
        elif 'fed' in text_lower or 'rate' in text_lower or 'policy' in text_lower:
            return 'policy'
        elif 'war' in text_lower or 'conflict' in text_lower:
            return 'war'
        elif 'covid' in text_lower or 'pandemic' in text_lower:
            return 'pandemic'
        elif 'crisis' in text_lower or 'crash' in text_lower:
            return 'crisis'
        else:
            return 'tech'

    def _analyze_sentiment(self, text: str) -> str:
        """간단한 감성 분석 (실제로는 AI 모델 사용 권장)"""
        positive_words = ['surge', 'rise', 'gain', 'win', 'success', 'growth']
        negative_words = ['fall', 'drop', 'crash', 'loss', 'crisis', 'war']

        text_lower = text.lower()
        if any(word in text_lower for word in negative_words):
            return 'negative'
        elif any(word in text_lower for word in positive_words):
            return 'positive'
        else:
            return 'neutral'
```

## 6. API 키 관리 (보안)

```bash
# .env 파일 생성
NEWS_API_KEY=your_news_api_key_here
FINNHUB_API_KEY=your_finnhub_key_here
ALPHA_VANTAGE_KEY=your_alphavantage_key_here
FRED_API_KEY=your_fred_key_here
```

```python
# backend/app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    news_api_key: str
    finnhub_api_key: str
    alpha_vantage_key: str
    fred_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
```

## 7. 캐싱 (API 호출 최소화)

```python
from functools import lru_cache
from datetime import datetime, timedelta

# 메모리 캐시 (1시간 유효)
@lru_cache(maxsize=128)
def get_cached_events(date_key: str):
    # 실제 API 호출
    return data_provider.get_global_events(from_date, to_date)

# Redis 캐시 (프로덕션 환경)
import redis

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def get_events_with_cache(from_date: str, to_date: str):
    cache_key = f'events:{from_date}:{to_date}'

    # 캐시 확인
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # 캐시 미스 시 API 호출
    events = data_provider.get_global_events(from_date, to_date)

    # 캐시 저장 (1시간)
    redis_client.setex(cache_key, 3600, json.dumps(events))

    return events
```

## 8. 비용 최적화 팁

1. **무료 티어 활용**
   - Yahoo Finance: 무료, 제한 없음 (비공식)
   - Alpha Vantage: 무료 플랜 (500 requests/day)
   - News API: 무료 플랜 (100 requests/day)

2. **캐싱 전략**
   - 과거 데이터는 영구 캐시
   - 당일 데이터는 1시간 캐시
   - 실시간 데이터만 WebSocket 사용

3. **배치 처리**
   - 매일 새벽에 전날 데이터 수집
   - 사용자 요청 시 캐시된 데이터 제공

4. **데이터베이스 저장**
   - 한번 가져온 뉴스/이벤트는 DB에 저장
   - API는 새로운 데이터만 요청

## 9. 추천 조합 (무료)

```
주가 데이터: Yahoo Finance (yfinance)
뉴스 데이터: News API (무료 100/day)
경제 지표: FRED API (무료)
실시간 가격: Finnhub WebSocket (무료 60/min)
```

## 10. 프로덕션 추천 조합 (유료)

```
주가 데이터: IEX Cloud ($9/month)
뉴스 + 이벤트: Bloomberg API or Reuters API
경제 캘린더: Trading Economics API
실시간: 거래소 직접 연결 (비용 높음)
```

# 데이터 출처 및 관리 가이드

## 📊 현재 데이터 상태 (개발/데모 단계)

### 1. 글로벌 이벤트 데이터

**저장 위치:** `frontend/src/data/globalEvents.ts`

**데이터 출처:**
- **수동으로 작성한 샘플 데이터** (실제 API 연동 없음)
- 역사적으로 중요한 금융/정치 이벤트를 직접 선별하여 입력
- 2008년 리먼 브라더스 파산부터 2025년 트럼프 취임까지 주요 이벤트 88개

**포함된 이벤트:**
```typescript
export interface GlobalEvent {
  date: string;               // 날짜 (YYYY-MM-DD)
  title: string;              // 이벤트 제목
  description: string;        // 상세 설명
  category: 'crisis' | 'election' | 'policy' | 'pandemic' | 'war' | 'tech';
  impact: 'positive' | 'negative' | 'neutral';
  symbolImpacts?: Record<string, 'positive' | 'negative' | 'neutral'>; // 종목별 영향도
}
```

**카테고리별 예시:**
- `crisis`: 2008 리먼 파산, 2020 코로나 폭락, 2023 SVB 파산
- `election`: 2016 트럼프 당선, 2020 바이든 당선, 2024 트럼프 재선
- `policy`: Fed 금리 인상, QE 종료, CARES Act
- `pandemic`: 2020 WHO 팬데믹 선언
- `war`: 2022 러시아-우크라이나 전쟁
- `tech`: 2022 ChatGPT 출시, 2024 AI 반도체 호황

**종목별 영향도 (symbolImpacts):**
- 정치적 이벤트는 종목마다 다르게 영향 (예: 트럼프 재선 → AAPL은 negative, TSLA는 positive)
- 종목별 영향도가 설정된 경우 해당 값 우선 사용, 없으면 전체 impact 사용

---

### 2. 종목별 이벤트 데이터

**저장 위치:** `frontend/src/data/globalEvents.ts` (같은 파일 내 `companyEvents`)

**데이터 출처:**
- **수동으로 작성한 샘플 데이터**
- 각 종목의 중요한 역사적 이벤트 직접 선별

**포함된 종목:** AAPL, TSLA, NVDA, MSFT, GOOGL

**예시 (AAPL):**
- 2007-06-29: iPhone 출시
- 2010-04-03: iPad 출시
- 2011-10-05: 스티브 잡스 사망
- 2018-08-02: 시총 1조 달러 돌파
- 2023-06-05: Vision Pro 공개

---

### 3. 종목 심볼 데이터베이스

**저장 위치:** `frontend/src/data/stockSymbols.ts`

**데이터 출처:**
- **수동으로 작성한 주요 종목 리스트** (50개)
- 미국 주식 35개 + 한국 주식 10개

**포함된 정보:**
```typescript
export interface StockSymbol {
  symbol: string;      // 티커 심볼 (AAPL, 005930.KS)
  nameKo: string;      // 한글명 (애플, 삼성전자)
  nameEn: string;      // 영문명 (Apple Inc.)
  market: 'US' | 'KR'; // 시장 구분
  sector?: string;     // 섹터 (Technology, Healthcare)
}
```

**미국 주요 종목:**
- 빅테크: AAPL, MSFT, GOOGL, AMZN, NVDA, TSLA, META
- 반도체: AMD, INTC
- 금융: JPM, BAC, V, MA
- 소비재: WMT, DIS, NKE, MCD, KO, PEP
- 에너지: XOM, CVX
- 헬스케어: JNJ, PFE, MRNA

**한국 주요 종목:**
- 전자/IT: 삼성전자, SK하이닉스, 네이버, 카카오
- 화학/배터리: LG화학, 삼성SDI
- 자동차: 현대차, 기아
- 바이오: 셀트리온, 삼성바이오로직스

---

## 🚀 프로덕션 데이터 연동 방안

### 1. 주가 데이터 (현재 미연동)

**권장 방법:**
```python
# backend/app/services/stock_data.py
import yfinance as yf

def get_stock_data(symbol: str, start: str, end: str):
    """Yahoo Finance에서 실시간 주가 데이터 가져오기"""
    stock = yf.Ticker(symbol)
    df = stock.history(start=start, end=end)
    return df  # Open, High, Low, Close, Volume 포함
```

**대안:**
- Alpha Vantage (무료 500 requests/day)
- IEX Cloud (유료 $9/month)
- Polygon.io (유료)

**상세 가이드:** `REAL_DATA_INTEGRATION.md` 참고

---

### 2. 뉴스/이벤트 데이터 (프로덕션 필수)

#### 글로벌 경제 이벤트

**News API** (뉴스 기반 이벤트 추출)
```typescript
// frontend/src/services/news.ts
const NEWS_API_KEY = process.env.VITE_NEWS_API_KEY;

export async function getFinancialNews(from: string, to: string) {
  const url = `https://newsapi.org/v2/everything?q=economy OR politics&from=${from}&to=${to}&apiKey=${NEWS_API_KEY}`;

  const response = await fetch(url);
  const data = await response.json();

  return data.articles.map(article => ({
    date: article.publishedAt.split('T')[0],
    title: article.title,
    description: article.description,
    category: classifyCategory(article.title), // AI 분류 필요
    impact: analyzeSentiment(article.title),   // 감성 분석 필요
  }));
}
```

**무료 티어:** 100 requests/day
**유료 플랜:** $449/month (무제한)

---

**Finnhub API** (금융 뉴스 + 기업 이벤트)
```python
# backend/app/services/events.py
import requests

def get_company_events(symbol: str, from_date: str, to_date: str):
    """종목별 뉴스 이벤트 가져오기"""
    API_KEY = os.getenv('FINNHUB_API_KEY')
    url = f'https://finnhub.io/api/v1/company-news?symbol={symbol}&from={from_date}&to={to_date}&token={API_KEY}'

    response = requests.get(url)
    news = response.json()

    return [{
        'date': datetime.fromtimestamp(item['datetime']).strftime('%Y-%m-%d'),
        'title': item['headline'],
        'description': item['summary'],
        'category': 'company',
        'impact': analyze_sentiment(item['headline'])
    } for item in news]
```

**무료 티어:** 60 API calls/minute
**유료 플랜:** $59/month

---

**FRED API** (연준 경제 지표)
```python
from fredapi import Fred

fred = Fred(api_key=os.getenv('FRED_API_KEY'))

# 연방 기준 금리
interest_rate = fred.get_series('FEDFUNDS')

# 실업률
unemployment = fred.get_series('UNRATE')

# CPI (인플레이션)
cpi = fred.get_series('CPIAUCSL')
```

**무료:** 무제한 사용 (API 키 필요)
**신청:** https://fred.stlouisfed.org/docs/api/api_key.html

---

### 3. 감성 분석 및 카테고리 분류

현재는 **수동 분류**이지만, 프로덕션에서는 **AI 모델** 필요:

```python
# backend/app/services/sentiment.py
from transformers import pipeline

# FinBERT 감성 분석 모델
sentiment_analyzer = pipeline(
    "sentiment-analysis",
    model="ProsusAI/finbert"
)

def analyze_sentiment(text: str) -> str:
    """뉴스 헤드라인 감성 분석"""
    result = sentiment_analyzer(text)[0]

    if result['label'] == 'positive' and result['score'] > 0.7:
        return 'positive'
    elif result['label'] == 'negative' and result['score'] > 0.7:
        return 'negative'
    else:
        return 'neutral'

def classify_category(text: str) -> str:
    """이벤트 카테고리 분류"""
    text_lower = text.lower()

    if 'election' in text_lower or 'vote' in text_lower:
        return 'election'
    elif 'fed' in text_lower or 'rate' in text_lower:
        return 'policy'
    elif 'war' in text_lower or 'conflict' in text_lower:
        return 'war'
    elif 'covid' in text_lower or 'pandemic' in text_lower:
        return 'pandemic'
    elif 'crisis' in text_lower or 'crash' in text_lower:
        return 'crisis'
    else:
        return 'tech'
```

---

## 💾 데이터 캐싱 전략

### 1. 과거 데이터 (영구 캐시)
```python
# backend/app/services/cache.py
import redis
import json

redis_client = redis.Redis(host='localhost', port=6379)

def cache_historical_events(from_date: str, to_date: str, events: list):
    """과거 이벤트는 변하지 않으므로 영구 캐시"""
    cache_key = f'events:historical:{from_date}:{to_date}'
    redis_client.set(cache_key, json.dumps(events))
    # TTL 없음 (영구 저장)

def cache_recent_events(events: list):
    """최근 이벤트는 1시간 캐시"""
    cache_key = f'events:recent:{datetime.now().date()}'
    redis_client.setex(cache_key, 3600, json.dumps(events))
```

### 2. 실시간 데이터 (짧은 TTL)
- 당일 주가: 5분 캐시
- 당일 뉴스: 1시간 캐시
- 역사적 데이터: 영구 캐시

---

## 🔄 데이터 업데이트 전략

### 1. 배치 작업 (매일 새벽)
```python
# backend/app/tasks/daily_update.py
from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

@scheduler.scheduled_job('cron', hour=3, minute=0)
def update_daily_events():
    """매일 새벽 3시 전날 이벤트 수집"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    # 뉴스 수집
    news = get_financial_news(yesterday, yesterday)

    # DB 저장
    save_events_to_db(news)

    # 캐시 업데이트
    cache_historical_events(yesterday, yesterday, news)

scheduler.start()
```

### 2. 실시간 업데이트 (WebSocket)
```typescript
// frontend/src/services/realtime.ts
const socket = new WebSocket(`wss://ws.finnhub.io?token=${API_KEY}`);

socket.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'news') {
    // 실시간 뉴스 이벤트 추가
    updateEvents(data.data);
  }
});
```

---

## 📁 데이터 파일 구조

```
frontend/src/data/
├── globalEvents.ts        # 글로벌 이벤트 (현재: 샘플 데이터)
│   ├── globalEvents[]     # 2008-2025 주요 경제/정치 이벤트
│   └── companyEvents{}    # 종목별 주요 이벤트 (AAPL, TSLA, etc.)
│
├── stockSymbols.ts        # 종목 데이터베이스 (현재: 50개 수동 입력)
│   ├── stockSymbols[]     # 미국 35개 + 한국 10개
│   └── searchStocks()     # 한글/영문/심볼 검색 함수
│
└── (미래 추가 예정)
    ├── marketHolidays.ts  # 시장 휴장일
    ├── sectorETFs.ts      # 섹터 ETF 리스트
    └── economicCalendar.ts # 경제 지표 발표 일정
```

---

## ⚠️ 현재 제한사항

1. **샘플 데이터만 사용 중**
   - 글로벌 이벤트: 수동으로 88개 입력
   - 종목 이벤트: 5개 종목만 (AAPL, TSLA, NVDA, MSFT, GOOGL)
   - 종목 리스트: 50개만 (실제 수천 개 존재)

2. **실시간 업데이트 없음**
   - 새로운 이벤트 자동 추가 안 됨
   - 수동으로 `globalEvents.ts` 편집 필요

3. **감성 분석 없음**
   - 이벤트 영향도를 수동으로 판단하여 입력
   - 종목별 영향도도 수동 분류

4. **데이터 정확성 보장 안 됨**
   - 교육/데모 목적의 샘플 데이터
   - 실제 투자에 사용 금지

---

## ✅ 프로덕션 체크리스트

실제 서비스 출시 전 필수 작업:

- [ ] Yahoo Finance API 연동 (주가 데이터)
- [ ] News API 또는 Finnhub 연동 (이벤트 데이터)
- [ ] FRED API 연동 (경제 지표)
- [ ] FinBERT 감성 분석 모델 통합
- [ ] Redis 캐싱 시스템 구축
- [ ] 매일 배치 작업 설정
- [ ] PostgreSQL + TimescaleDB 도입 (시계열 데이터)
- [ ] 실시간 WebSocket 연결
- [ ] 데이터 품질 검증 파이프라인
- [ ] API 키 환경 변수 관리 (.env)

---

## 🇰🇷 한국 주식 데이터 (DART API) - ✅ **구현 완료**

### DART (전자공시) API 통합

**상태:** 완전 구현 및 테스트 완료 (2025-10-05)

**기능:**
- ✅ 기업코드 자동 매핑 (stock_code ↔ corp_code)
- ✅ 재무제표 자동 다운로드 (분기별)
- ✅ 무한 루프 방지 (max_attempts: 12)
- ✅ 지능형 캐싱 (7일 자동 갱신)

**구현 위치:** `backend/app/services/dart_api.py`

#### 1. 기업코드 자동 매핑

DART API는 주식 코드 대신 **8자리 기업 고유번호(corp_code)** 사용:

```python
from app.services.dart_api import DartAPI

dart = DartAPI()  # 자동으로 corpCode.xml 다운로드
corp_code = dart.get_corp_code('096530')  # 씨젠: "00788773"
corp_code = dart.get_corp_code('005930')  # 삼성전자: "00126380"
```

**매핑 방식:**
- `corpCode.xml` 자동 다운로드 (ZIP 압축)
- XML 파싱 → JSON 변환
- 로컬 캐싱: `backend/cache/dart/corp_code_mapping.json`
- 메모리 캐싱으로 빠른 재사용
- 7일마다 자동 갱신
- 총 3,901개 상장 기업 매핑

#### 2. 재무제표 조회

```python
# 최근 4개 분기 재무 데이터 조회
financials = dart.get_quarterly_financials('096530', num_quarters=4)

# 결과 예시 (씨젠)
{
    'quarters': ['2025Q2', '2025Q1', '2024Q4', '2024Q3'],
    'net_income': [...],
    'revenue': [114059888071, 115996860695, 414251733221, None],
    'operating_income': [...]
}
```

**조회 로직:**
- 현재 분기 자동 계산 (2025-10 = Q4)
- 현재 분기 스킵 (공시까지 45일 소요)
- 역순 조회 (최신부터)
- 최대 12개 분기까지 시도 (3년치)

#### 3. 무한 루프 방지

**문제:** 미래 분기 조회 → 데이터 없음 → 무한 반복

**해결:**
```python
max_attempts = 12  # 최대 3년치만 시도
attempts = 0

while quarters_fetched < num_quarters and attempts < max_attempts:
    attempts += 1
    # 조회 로직
```

**에러 로그 최적화:**
- 처음 3개만 로깅 (스팸 방지)
- 조회 결과 요약 로깅

#### 4. P/B 비율 계산 (한국 주식)

yfinance가 P/B를 제공하지 않는 경우 재무제표에서 계산:

```python
# backend/app/services/fundamental_analysis.py
# P/B = 현재 주가 ÷ BPS (주당순자산가치)
# BPS = Tangible Book Value ÷ Ordinary Shares Number

pb = info.get('priceToBook', None)
if pb is None:
    bs = ticker.quarterly_balance_sheet
    tbv = bs.loc['Tangible Book Value', latest]
    shares = bs.loc['Ordinary Shares Number', latest]
    bps = tbv / shares
    pb = current_price / bps
```

**예시 (씨젠):**
- Tangible Book Value: 954,281,739,080원
- Ordinary Shares: 46,112,381주
- BPS: 20,694.70원
- P/B: 25,200원 ÷ 20,694.70원 = **1.22**

#### 5. 설정 방법

**API 키 발급:**
1. https://opendart.fss.or.kr/ 회원가입
2. API 키 발급 (무료)
3. `backend/.env`에 추가:
```bash
DART_API_KEY=your_api_key_here
```

**Fallback:**
- DART_API_KEY 없으면 yfinance 사용
- P/B 계산 실패 시 조건 스킵

#### 6. 캐시 관리

**위치:** `backend/cache/dart/`
- `corp_code_mapping.json`: 기업코드 매핑 (3,901개)

**자동 갱신:**
- 7일마다 corpCode.xml 재다운로드
- 메모리 캐시로 세션 내 재사용

**gitignore 설정:**
```
# Cache
backend/cache/
```

---

## 📚 추가 참고 자료

- **API 연동 상세 가이드:** [REAL_DATA_INTEGRATION.md](./REAL_DATA_INTEGRATION.md)
- **한국 주식 특수 처리:** [CLAUDE.md](./CLAUDE.md) - 호가 단위, P/B 계산
- **시작 가이드:** [START_HERE.txt](./START_HERE.txt)
- **README:** [README.md](./README.md)

---

**⚠️ 중요:** 현재 앱은 **데모/교육 목적**이며, 실제 투자 결정에 사용해서는 안 됩니다. 프로덕션 환경에서는 반드시 실시간 데이터 API를 연동하고 데이터 품질을 검증해야 합니다.

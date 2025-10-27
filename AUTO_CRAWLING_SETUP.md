# 자동 이벤트 크롤링 설정 가이드

## 🎯 개요

뉴스를 **매일 자동으로 수집**하여 이벤트 데이터를 업데이트하는 시스템입니다.
더 이상 수동으로 이벤트를 입력할 필요가 없습니다!

### 주요 기능

✅ **매일 자정 자동 크롤링**
- 글로벌 경제/정치 뉴스 수집
- 주요 종목별 뉴스 수집
- AI 자동 분류 (카테고리, 감성 분석)

✅ **중복 제거**
- 날짜 + 제목 기준으로 자동 중복 제거
- 기존 데이터와 병합하여 저장

✅ **주간 데이터 정리**
- 매주 일요일 오래된 데이터 정리
- 최근 3년 데이터만 유지

---

## 📋 사전 준비

### 1. News API 키 발급 (무료)

**무료 플랜:** 100 requests/day (충분함)

1. https://newsapi.org/register 접속
2. 이메일 입력하여 계정 생성
3. API 키 복사 (예: `abc123def456...`)

### 2. 환경 변수 설정

**backend/.env 파일 생성:**
```bash
# News API 키
NEWS_API_KEY=your_api_key_here
```

또는 시스템 환경 변수로 설정:

**Windows:**
```cmd
set NEWS_API_KEY=your_api_key_here
```

**Linux/Mac:**
```bash
export NEWS_API_KEY=your_api_key_here
```

### 3. Python 패키지 설치

```bash
cd backend
pip install apscheduler requests python-dotenv
```

---

## 🚀 사용 방법

### 방법 1: FastAPI 앱과 함께 자동 시작 (권장)

**backend/app/main.py에 추가:**

```python
from fastapi import FastAPI
from .services.event_scheduler import start_scheduler, stop_scheduler
from .routers import events  # 이벤트 API 라우터

app = FastAPI()

# 이벤트 라우터 등록
app.include_router(events.router)

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 스케줄러 자동 시작"""
    start_scheduler()
    print("✅ 이벤트 자동 수집 스케줄러 시작됨")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 스케줄러 정리"""
    stop_scheduler()
```

**실행:**
```bash
cd backend
uvicorn app.main:app --reload
```

이제 서버가 실행되는 동안 자동으로:
- **매일 00:00** - 글로벌 이벤트 수집
- **매일 00:10** - 종목별 이벤트 수집
- **매주 일요일 02:00** - 데이터 정리

---

### 방법 2: 독립 실행 (서버 없이)

**별도 프로세스로 스케줄러만 실행:**

```python
# backend/run_scheduler.py
import logging
from app.services.event_scheduler import start_scheduler
import time

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    start_scheduler()
    print("스케줄러 실행 중... (Ctrl+C로 종료)")

    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("스케줄러 종료")
```

**실행:**
```bash
python backend/run_scheduler.py
```

---

### 방법 3: 수동 업데이트 (즉시 실행)

**Python 스크립트:**
```python
from app.services.event_scheduler import manual_update

manual_update()  # 지금 즉시 크롤링 실행
```

**API 호출:**
```bash
curl -X POST http://localhost:8000/events/update/manual
```

---

## 📊 API 엔드포인트

### 1. 글로벌 이벤트 조회
```http
GET /events/global?from_date=2024-01-01&to_date=2024-12-31&category=election&limit=50
```

**응답:**
```json
{
  "success": true,
  "count": 25,
  "events": [
    {
      "date": "2024-11-05",
      "title": "Trump wins presidential election",
      "description": "Donald Trump elected as 47th president...",
      "category": "election",
      "impact": "neutral",
      "source": "CNN",
      "url": "https://..."
    }
  ]
}
```

### 2. 종목별 이벤트 조회
```http
GET /events/company/AAPL?limit=20
```

### 3. 수동 업데이트 실행
```http
POST /events/update/manual
```

**응답:**
```json
{
  "success": true,
  "message": "백그라운드에서 이벤트 업데이트 시작",
  "note": "완료까지 1-2분 소요될 수 있습니다."
}
```

### 4. 테스트 크롤링 (저장 안 함)
```http
POST /events/crawl/test?days_back=1
```

### 5. 이벤트 통계
```http
GET /events/stats
```

**응답:**
```json
{
  "success": true,
  "global_events": {
    "total": 523,
    "latest_date": "2024-12-15",
    "category_distribution": {
      "policy": 145,
      "election": 32,
      "crisis": 87,
      "tech": 259
    }
  },
  "company_events": {
    "AAPL": { "count": 67, "latest_date": "2024-12-15" },
    "TSLA": { "count": 89, "latest_date": "2024-12-14" }
  }
}
```

---

## 📁 데이터 저장 구조

```
backend/data/events/
├── global_events.json          # 글로벌 경제/정치 이벤트
├── AAPL_events.json            # 애플 종목 이벤트
├── TSLA_events.json            # 테슬라 종목 이벤트
├── NVDA_events.json            # 엔비디아 종목 이벤트
├── MSFT_events.json            # 마이크로소프트
├── GOOGL_events.json           # 구글
├── AMZN_events.json            # 아마존
└── META_events.json            # 메타
```

**이벤트 JSON 형식:**
```json
[
  {
    "date": "2024-12-15",
    "title": "Fed holds interest rates steady",
    "description": "Federal Reserve maintains current interest rate...",
    "category": "policy",
    "impact": "neutral",
    "source": "Reuters",
    "url": "https://www.reuters.com/..."
  }
]
```

---

## 🤖 AI 자동 분류 시스템

### 카테고리 분류 (키워드 기반)

| 카테고리 | 키워드 예시 |
|---------|-----------|
| `election` | election, vote, president, congress |
| `policy` | fed, interest rate, monetary policy, central bank |
| `war` | war, conflict, military, invasion |
| `pandemic` | covid, pandemic, virus, outbreak |
| `crisis` | crash, crisis, bankruptcy, recession |
| `tech` | 기타 모든 뉴스 |

### 감성 분석 (키워드 기반)

| 감성 | 긍정 키워드 | 부정 키워드 |
|------|------------|------------|
| `positive` | surge, rally, gain, profit, growth | - |
| `negative` | - | fall, crash, loss, crisis, warning |
| `neutral` | 위 두 가지 모두 해당 안 됨 | - |

**⚠️ 주의:** 현재는 간단한 키워드 매칭 방식입니다.
프로덕션에서는 **FinBERT** 같은 AI 모델 사용을 권장합니다.

---

## 🔧 커스터마이징

### 1. 크롤링 주기 변경

**event_scheduler.py 수정:**
```python
# 매일 오전 9시로 변경
scheduler.add_job(
    daily_global_events_update,
    trigger=CronTrigger(hour=9, minute=0),  # 00 → 9
    ...
)

# 4시간마다 실행
scheduler.add_job(
    daily_global_events_update,
    trigger='interval',
    hours=4,
    ...
)
```

### 2. 수집 종목 추가/변경

**event_scheduler.py에서:**
```python
symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META']
companies = ['Apple', 'Microsoft', 'Google', 'Amazon', 'NVIDIA', 'Tesla', 'Meta']

# 종목 추가
symbols.append('NFLX')
companies.append('Netflix')
```

### 3. 검색 키워드 추가

**news_crawler.py에서:**
```python
keywords = [
    "stock market", "federal reserve", "interest rate",
    "inflation", "GDP", "unemployment", "earnings",
    # 커스텀 키워드 추가
    "bitcoin", "cryptocurrency", "climate change"
]
```

### 4. 데이터 보관 기간 변경

**event_scheduler.py에서:**
```python
# 3년 → 5년으로 변경
five_years_ago = (datetime.now() - timedelta(days=365 * 5)).strftime('%Y-%m-%d')
```

---

## 🐛 문제 해결

### 1. "NEWS_API_KEY 환경 변수가 설정되지 않았습니다"
```bash
# .env 파일 확인
cat backend/.env

# 또는 직접 설정
export NEWS_API_KEY=your_key_here
```

### 2. "수집된 이벤트 없음"
- News API 할당량 확인 (무료: 100/day)
- API 키가 유효한지 확인
- 인터넷 연결 확인

### 3. 중복 이벤트가 계속 생김
- 날짜 형식이 일치하는지 확인 (YYYY-MM-DD)
- 제목이 완전히 동일한지 확인

### 4. 스케줄러가 작동 안 함
```python
# 로깅 활성화
import logging
logging.basicConfig(level=logging.INFO)

# 작업 목록 확인
from app.services.event_scheduler import scheduler
print(scheduler.get_jobs())
```

---

## 📈 성능 최적화

### 1. API 호출 최소화
- 캐싱 사용 (Redis 권장)
- 중복 제거 로직 강화
- 배치 크기 조정 (pageSize)

### 2. 저장 공간 관리
- 오래된 데이터 정기 삭제
- 종목당 최대 100개 이벤트만 유지
- JSON 압축 (gzip)

### 3. AI 모델 통합 (선택)
```bash
pip install transformers torch

# FinBERT 감성 분석
from transformers import pipeline
sentiment = pipeline("sentiment-analysis", model="ProsusAI/finbert")
```

---

## ✅ 체크리스트

배포 전 확인사항:

- [ ] News API 키 발급 및 설정
- [ ] 환경 변수 설정 (.env 파일)
- [ ] APScheduler 패키지 설치
- [ ] FastAPI 앱에 스케줄러 통합
- [ ] 이벤트 API 라우터 등록
- [ ] 데이터 저장 디렉토리 생성
- [ ] 첫 수동 업데이트 실행 (테스트)
- [ ] 로그 확인 (스케줄러 작동 여부)
- [ ] API 엔드포인트 테스트
- [ ] 프론트엔드에서 이벤트 조회 연동

---

## 🚀 프로덕션 추천 사항

1. **Redis 캐싱**
   - 같은 날짜 뉴스는 캐시에서 반환
   - API 호출 횟수 절감

2. **PostgreSQL 저장**
   - JSON 파일 대신 DB 사용
   - 검색 성능 향상

3. **AI 모델 통합**
   - FinBERT로 정확한 감성 분석
   - GPT-4로 이벤트 요약 생성

4. **WebSocket 실시간 업데이트**
   - Finnhub WebSocket 연결
   - 실시간 뉴스 푸시

5. **모니터링**
   - Sentry로 에러 추적
   - Prometheus + Grafana로 메트릭 수집

---

**참고:**
- [NEWS_API 공식 문서](https://newsapi.org/docs)
- [APScheduler 문서](https://apscheduler.readthedocs.io/)
- [DATA_SOURCES.md](./DATA_SOURCES.md) - 전체 데이터 가이드

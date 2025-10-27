# 📡 실시간 데이터 모니터링 시스템

yfinance를 이용한 **10분 간격 실시간 가격 업데이트** 및 **WebSocket 스트리밍** 시스템입니다.

---

## 🚀 기능 개요

### 1. 실시간 데이터 수집
- **yfinance**에서 10분마다 최신 가격 자동 수집
- **1분봉 데이터** 제공 (최근 1일)
- 백그라운드에서 비동기 실행 (FastAPI + asyncio)

### 2. WebSocket 스트리밍
- **양방향 통신**: 클라이언트 ↔ 서버
- **실시간 푸시**: 가격 업데이트 즉시 전송
- **다중 구독**: 여러 종목 동시 모니터링

### 3. 실시간 신호 생성
- MACD 크로스 자동 감지
- RSI 과매수/과매도 체크
- 매수/매도 신호 즉시 알림

---

## 📋 아키텍처

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   브라우저   │◄────────┤  WebSocket   │◄────────┤  yfinance   │
│  (React UI)  │ 실시간   │   서버       │  10분   │   API       │
└─────────────┘         └──────────────┘         └─────────────┘
      │                        │
      │ 구독(subscribe)         │ 데이터 수집
      │                        │ (백그라운드)
      ▼                        ▼
 ┌─────────────┐         ┌──────────────┐
 │ 관심종목     │         │ 가격 캐시     │
 │ [AAPL,TSLA] │         │ {AAPL: data} │
 └─────────────┘         └──────────────┘
```

---

## 🛠️ 구현 상세

### 백엔드 (FastAPI)

#### 1. 실시간 데이터 수집기
**파일**: `backend/app/services/realtime_data.py`

```python
class RealtimeDataCollector:
    def __init__(self, update_interval=600):  # 600초 = 10분
        self.update_interval = update_interval
        self.subscribed_symbols = set()
        self.latest_data = {}

    async def fetch_realtime_data(self, symbol):
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d", interval="1m")
        return data

    async def start(self):
        while self.running:
            await self.update_all_symbols()
            await asyncio.sleep(self.update_interval)
```

#### 2. WebSocket 서버
**파일**: `backend/app/api/websocket.py`

**엔드포인트**: `ws://localhost:8000/api/v1/ws/realtime`

**클라이언트 → 서버 메시지**:
```json
{
  "action": "subscribe",
  "symbols": ["AAPL", "TSLA", "NVDA"]
}
```

**서버 → 클라이언트 메시지**:
```json
{
  "type": "price_update",
  "symbol": "AAPL",
  "timestamp": "2024-01-01T12:00:00",
  "data": {
    "open": 180.50,
    "high": 182.30,
    "low": 179.80,
    "close": 181.20,
    "volume": 1234567,
    "current_price": 181.25
  }
}
```

### 프론트엔드 (React + TypeScript)

#### 1. WebSocket Hook
**파일**: `frontend/src/hooks/useWebSocket.ts`

```typescript
export const useWebSocket = (url: string) => {
  const [isConnected, setIsConnected] = useState(false);
  const [latestPrices, setLatestPrices] = useState<Map<string, PriceUpdate>>(new Map());

  const subscribe = (symbols: string[]) => {
    ws.send(JSON.stringify({ action: 'subscribe', symbols }));
  };

  return { isConnected, latestPrices, subscribe };
};
```

#### 2. 실시간 모니터링 UI
**파일**: `frontend/src/pages/RealtimeMonitor.tsx`

**기능**:
- 🟢 연결 상태 표시
- 📊 실시간 가격 테이블
- 📈 변동률 색상 표시 (빨강/초록)
- 🕐 마지막 업데이트 시간
- ➕ 관심종목 추가/제거

---

## 🚀 사용 방법

### 1. 백엔드 시작

```bash
# 백엔드가 이미 실행 중이면 재시작
STOP.bat
START.bat

# 또는 수동 시작
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 프론트엔드 접속

```bash
# 브라우저에서 http://localhost:5173 접속
# "실시간 모니터링" 탭 클릭
```

### 3. 종목 구독

1. **종목 추가**: 검색창에서 종목 검색 (예: AAPL)
2. **자동 구독**: 추가한 종목은 자동으로 WebSocket 구독
3. **실시간 업데이트**: 10분마다 최신 가격이 자동으로 표시됨

---

## 📊 데이터 업데이트 주기

| 항목 | 주기 | 설명 |
|------|------|------|
| **yfinance 호출** | 10분 | 백엔드가 자동으로 데이터 수집 |
| **WebSocket 푸시** | 즉시 | 데이터 수집 후 즉시 전송 |
| **재연결** | 5초 | 연결 끊김 시 자동 재연결 |

---

## ⚙️ 설정 변경

### 업데이트 간격 변경

```python
# backend/app/services/realtime_data.py
collector = RealtimeDataCollector(update_interval=300)  # 5분
```

또는

```python
# backend/app/api/websocket.py
collector = get_realtime_collector(update_interval=300)  # 5분
```

### 주의사항
- **1분 이하**: yfinance API 제한으로 권장하지 않음
- **5분**: 적극적인 트레이딩 용
- **10분** (기본): 비용 vs 실시간성 균형
- **30분 이상**: 장기 투자용

---

## 🔧 트러블슈팅

### 1. WebSocket 연결 안 됨
```bash
# 백엔드 로그 확인
tail -f backend/logs/app.log

# WebSocket 엔드포인트 확인
curl http://localhost:8000/
# 출력: {"websocket": "/api/v1/ws/realtime"}
```

### 2. 데이터가 업데이트 안 됨
```bash
# 브라우저 콘솔에서
ws.send(JSON.stringify({action: 'get_latest', symbols: ['AAPL']}))

# 백엔드에서 수동 테스트
cd backend
python
>>> from app.services.realtime_data import get_realtime_collector
>>> collector = get_realtime_collector()
>>> collector.subscribe('AAPL')
>>> import asyncio
>>> asyncio.run(collector.update_all_symbols())
```

### 3. yfinance 오류
```python
# yfinance 버전 확인
pip show yfinance

# 최신 버전 설치
pip install --upgrade yfinance

# 직접 테스트
python
>>> import yfinance as yf
>>> ticker = yf.Ticker('AAPL')
>>> data = ticker.history(period="1d", interval="1m")
>>> print(data)
```

---

## 🎯 실전 사용 예시

### 예시 1: 단순 가격 모니터링
```
1. "실시간 모니터링" 탭 열기
2. AAPL, TSLA, NVDA 추가
3. 10분마다 자동 업데이트 확인
```

### 예시 2: 매매 신호 감지
```python
# backend/app/services/realtime_data.py
class RealtimeSignalGenerator:
    async def check_signals(self, symbol, data):
        # MACD 골든 크로스 감지
        if prev['MACD'] <= prev['MACD_signal'] and latest['MACD'] > latest['MACD_signal']:
            return {"type": "BUY", "reason": "MACD 골든 크로스"}
```

### 예시 3: 알림 (추후 구현)
```
- 텔레그램 봇으로 매수 신호 전송
- 이메일로 일일 리포트 발송
- Discord webhook으로 실시간 알림
```

---

## 📈 성능 최적화

### 1. 메모리 사용량
```python
# 최대 100개 종목만 허용
MAX_SYMBOLS = 100

if len(self.subscribed_symbols) >= MAX_SYMBOLS:
    raise Exception("최대 구독 종목 수 초과")
```

### 2. 네트워크 대역폭
```python
# 변경된 데이터만 전송
if latest_price != previous_price:
    await self._notify_subscribers(symbol, latest_price)
```

### 3. CPU 사용량
```python
# asyncio로 비동기 처리
tasks = [self.fetch_realtime_data(symbol) for symbol in symbols]
results = await asyncio.gather(*tasks)
```

---

## 🚨 주의사항

### 1. yfinance 제한
- **1분봉**: 최대 7일치만 제공
- **API 제한**: 너무 많은 요청 시 차단 가능
- **지연 시간**: 실제 시장과 15분 지연 (무료)

### 2. WebSocket 연결 수
- **브라우저 제한**: 탭당 1개 연결
- **서버 제한**: 기본 무제한 (추후 제한 가능)

### 3. 데이터 정확성
- **샘플 데이터**: 교육용, 실전 투자 X
- **실시간 ≠ 실제 시장**: 15분 지연
- **백테스트 결과**: 과거 성과 ≠ 미래 수익

---

## 🔮 향후 계획

### Phase 1 완료 ✅
- [x] 실시간 데이터 수집 (10분)
- [x] WebSocket 서버
- [x] 실시간 모니터링 UI

### Phase 2 예정
- [ ] 실시간 매매 신호 생성
- [ ] 텔레그램 봇 알림
- [ ] 이메일 알림
- [ ] Discord Webhook

### Phase 3 예정 (자동매매)
- [ ] 증권사 API 연동
- [ ] 자동 주문 실행
- [ ] 포지션 관리
- [ ] 리스크 관리 (킬 스위치)

---

## 📞 문의

- **버그 리포트**: GitHub Issues
- **기능 제안**: Discord 서버
- **이메일**: support@example.com

---

**다음 단계**: [자동매매 시스템 구축](AUTO_TRADING.md) (작성 예정)

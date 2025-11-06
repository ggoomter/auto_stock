# 🚀 자동매매 시스템 가이드

## 📋 목차
1. [개요](#개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [주요 기능](#주요-기능)
4. [시작하기](#시작하기)
5. [자동매매 전략 설정](#자동매매-전략-설정)
6. [리스크 관리](#리스크-관리)
7. [실시간 모니터링](#실시간-모니터링)
8. [API 레퍼런스](#api-레퍼런스)
9. [보안 및 주의사항](#보안-및-주의사항)

---

## 🎯 개요

이 자동매매 시스템은 **백테스트 검증된 전략**을 실시간 시장에서 자동으로 실행하는 고급 트레이딩 플랫폼입니다.

### 핵심 특징
- ✅ **실시간 데이터 기반** 자동 거래
- ✅ **7가지 대가 전략** (버핏, 린치, 그레이엄 등)
- ✅ **고급 위험 관리** (위험가치, 켈리 공식, 포트폴리오 최적화)
- ✅ **웹소켓 실시간 모니터링**
- ✅ **모의/실전 거래** 모드 지원

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────┐
│                   Frontend (React)                       │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  Dashboard  │  │  Strategy    │  │  Risk Panel  │   │
│  │  Component  │  │  Selector    │  │  Component   │   │
│  └─────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────┬───────────────────────────────┘
                          │ WebSocket
                          │ REST API
┌─────────────────────────▼───────────────────────────────┐
│                   Backend (FastAPI)                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │          Auto Trading Engine                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │  Strategy  │  │    Risk    │  │  Position  │ │   │
│  │  │  Executor  │  │  Manager   │  │  Manager   │ │   │
│  │  └────────────┘  └────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Real-time Data Collector                  │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐ │   │
│  │  │  yfinance  │  │   News     │  │   Market   │ │   │
│  │  │    API     │  │  Crawler   │  │  Indicators│ │   │
│  │  └────────────┘  └────────────┘  └────────────┘ │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
                          │
                          │ 주문 실행
                          ▼
┌──────────────────────────────────────────────────────────┐
│              Broker API (한국투자증권)                      │
└──────────────────────────────────────────────────────────┘
```

---

## 💡 주요 기능

### 1. 자동매매 엔진
- **실시간 신호 감지**: 10초 간격 시장 모니터링
- **자동 주문 실행**: 시장가/지정가 주문
- **포지션 관리**: 진입/청산 자동화
- **트레일링 스톱**: 수익 보호

### 2. 위험 관리
- **포트폴리오 위험가치**: 95% 신뢰수준 최대 예상 손실
- **켈리 공식**: 최적 포지션 크기 계산
- **상관관계 분석**: 종목 간 분산 최적화
- **일일 손실 한도**: 5% 자동 차단

### 3. 전략 시스템
- **7가지 마스터 전략**: 검증된 투자 대가 전략
- **커스텀 전략**: 사용자 정의 조건
- **멀티 전략 운용**: 가중치 기반 포트폴리오

---

## 🚀 시작하기

### 1. 환경 설정

```bash
# 1. 환경 변수 설정 (.env 파일)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
KIS_ACCOUNT_NO=your_account_number
KIS_REAL_TRADING=false  # true: 실전, false: 모의

# 2. 서버 시작
START.bat  # Windows
./start.sh  # Linux/Mac
```

### 2. 대시보드 접속

브라우저에서 `http://localhost:5173` 접속 후 **"자동매매 대시보드"** 탭 클릭

### 3. 초기 설정

```javascript
// 자동매매 설정 예시
{
  "mode": "paper",           // "paper" 또는 "live"
  "total_capital": 10000000,  // 총 자본금 (KRW)
  "max_positions": 5,         // 최대 보유 종목 수
  "max_position_size": 0.2,   // 종목당 최대 비중 (20%)
  "max_risk_per_trade": 0.02, // 거래당 최대 리스크 (2%)
  "max_daily_loss": 0.05,     // 일일 최대 손실 (5%)
  "enabled_strategies": ["buffett", "lynch"],
  "trading_hours": {
    "start": "09:00",
    "end": "15:30"
  }
}
```

---

## 📊 자동매매 전략 설정

### 마스터 전략 활용

```python
# 1. Warren Buffett (가치 투자)
- ROE > 15%
- 부채비율 < 50%
- P/E < 20
- 손절: -7%, 익절: +20%

# 2. Peter Lynch (성장주)
- PEG < 1.0
- 이익 성장률 > 20%
- 손절: -8%, 익절: +25%

# 3. Benjamin Graham (깊은 가치)
- P/B < 0.67
- 유동비율 > 2.0
- 손절: -5%, 익절: +15%
```

### 커스텀 전략 생성

```python
# 예시: MACD + RSI 전략
entry_condition = "MACD.cross_up == true AND RSI < 30"
exit_condition = "MACD.cross_down == true OR RSI > 70"

# API 호출
POST /api/v1/trading/strategy
{
  "name": "my_strategy",
  "entry": entry_condition,
  "exit": exit_condition,
  "stop_loss": 0.05,
  "take_profit": 0.15
}
```

---

## 🛡️ 리스크 관리

### 포지션 사이징

```python
# 켈리 공식 기반 최적 크기
position_size = capital * kelly_fraction * 0.25  # 보수적 켈리 25%

# 리스크 기반 제한
max_loss = capital * max_risk_per_trade
position_size = min(position_size, max_loss / stop_loss_distance)
```

### 포트폴리오 위험 지표

| 지표 | 설명 | 권장 수준 |
|------|------|----------|
| 위험가치 (95%) | 일일 최대 예상 손실 | < 3% |
| 위험조정수익률 | 위험 대비 수익 효율성 | > 1.0 |
| 최대낙폭 | 고점 대비 최대 하락률 | < 15% |
| 집중도지수 | 종목 편중 위험도 | < 0.3 |

### 동적 위험 조정

```python
# 변동성지수 기반 자동 조정
if 변동성지수 > 30:
    거래당_위험 *= 0.5  # 고변동성: 위험 50% 축소
elif 변동성지수 < 15:
    거래당_위험 *= 1.2  # 저변동성: 위험 20% 확대
```

---

## 📡 실시간 모니터링

### WebSocket 연결

```javascript
// WebSocket 연결
const ws = new WebSocket('ws://localhost:8000/ws/realtime');

// 종목 구독
ws.send(JSON.stringify({
  type: 'subscribe',
  symbols: ['AAPL', 'MSFT', '005930.KS']
}));

// 데이터 수신
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'position_update') {
    updatePositions(data.positions);
  } else if (data.type === 'alert') {
    showAlert(data.alert);
  }
};
```

### 대시보드 기능

1. **실시간 포지션 현황**
   - 종목별 손익
   - 진입/현재가 비교
   - 손절/익절 레벨

2. **리스크 모니터링**
   - 포트폴리오 VaR
   - 샤프 비율
   - 리스크 레벨 (Low/Medium/High/Extreme)

3. **알림 시스템**
   - 주문 체결
   - 손절/익절 도달
   - 리스크 경고

---

## 📚 API 레퍼런스

### REST API

#### 자동매매 시작
```http
POST /api/v1/trading/start
Content-Type: application/json

{
  "mode": "paper",
  "total_capital": 10000000,
  "enabled_strategies": ["buffett", "lynch"]
}
```

#### 자동매매 중지
```http
POST /api/v1/trading/stop
```

#### 상태 조회
```http
GET /api/v1/trading/status

Response:
{
  "is_running": true,
  "mode": "paper",
  "active_positions": 3,
  "daily_pnl": 150000
}
```

#### 성과 조회
```http
GET /api/v1/trading/performance

Response:
{
  "total_trades": 42,
  "win_rate": 0.64,
  "profit_factor": 2.3,
  "sharpe_ratio": 1.5,
  "max_drawdown": -0.08
}
```

### WebSocket API

#### 거래 제어
```javascript
// 자동매매 시작
ws.send(JSON.stringify({
  type: 'start_trading',
  config: {
    mode: 'paper',
    enabled_strategies: ['buffett']
  }
}));

// 포지션 청산
ws.send(JSON.stringify({
  type: 'close_position',
  symbol: 'AAPL',
  reason: '수동 청산'
}));
```

---

## 🔒 보안 및 주의사항

### 보안 설정

1. **API 키 관리**
   - `.env` 파일에 저장 (절대 git에 commit 금지)
   - 환경별 분리 (개발/운영)

2. **접근 제어**
   - IP 화이트리스트 설정
   - API 키 권한 최소화

3. **거래 제한**
   ```python
   # 안전 장치
   MAX_ORDER_SIZE = 1000000  # 최대 주문 금액
   MAX_DAILY_TRADES = 100     # 일일 최대 거래 수
   BLOCKED_HOURS = ["03:00", "09:00"]  # 거래 제한 시간
   ```

### ⚠️ 주의사항

1. **실전 거래 전 체크리스트**
   - [ ] 모의 거래로 최소 1개월 테스트
   - [ ] 백테스트 결과 검증 (최소 3년 데이터)
   - [ ] 리스크 파라미터 설정 확인
   - [ ] 비상 정지 버튼 동작 테스트
   - [ ] 증권사 API 한도 확인

2. **위험 관리**
   - 초기 자본의 10%로 시작
   - 일일 손실 한도 반드시 설정
   - 시스템 오류 시 수동 개입 준비
   - 정기적인 성과 리뷰

3. **법적 책임**
   - 본 시스템은 교육/연구 목적
   - 투자 손실에 대한 책임은 사용자 본인
   - 증권사 약관 및 규정 준수

---

## 🆘 문제 해결

### 자주 발생하는 문제

1. **WebSocket 연결 실패**
   ```bash
   # 포트 확인
   netstat -an | findstr 8000

   # 백엔드 재시작
   STOP.bat
   START.bat
   ```

2. **주문 실패**
   - API 키 유효성 확인
   - 계좌 잔고 확인
   - 거래 시간 확인

3. **데이터 수집 오류**
   - yfinance 버전 확인 (`pip install --upgrade yfinance`)
   - 네트워크 연결 상태 확인

### 로그 확인

```bash
# 백엔드 로그
tail -f backend/logs/trading.log

# 에러 추적
cat G:/ai_coding/auto_stock/error_traceback.txt
```

---

## 📈 성과 분석

### 백테스트 vs 실거래 비교

```python
# 슬리피지 및 수수료 고려
실제_수익률 = 백테스트_수익률 * 0.85  # 보수적 추정

# 성과 지표 모니터링
- 일일: 손익, 승률, 거래 횟수
- 주간: 샤프 비율, 최대 낙폭
- 월간: 총 수익률, 리스크 조정 수익률
```

### 전략 개선

1. **A/B 테스트**: 전략 변경 시 병렬 운영
2. **파라미터 최적화**: Grid Search, Bayesian Optimization
3. **기계학습 통합**: 신호 확률 예측

---

## 🎓 추가 학습 자료

- [백테스트 가이드](./BACKTEST_GUIDE.md)
- [마스터 전략 상세](./MASTER_STRATEGIES.md)
- [API 상세 문서](http://localhost:8000/docs)
- [리스크 관리 이론](./RISK_MANAGEMENT.md)

---

## 📞 지원

- **이슈 리포트**: GitHub Issues
- **커뮤니티**: Discord 채널
- **문서**: [공식 문서](./docs)

---

**⚡ Happy Trading! 성공적인 자동매매를 기원합니다! ⚡**
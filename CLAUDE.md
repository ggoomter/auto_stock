# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**⚠️ IMPORTANT: Always communicate in Korean (한글) with the user unless explicitly requested otherwise.**

## Project Overview

Financial Research Copilot - A financial analysis platform providing probabilistic predictions and strategy simulations with explainability. Built with FastAPI (backend) and React + TypeScript (frontend).

**✅ Python Version:** Python 3.10, 3.11, 3.12, and 3.13 are all supported. The project has been tested and verified working on Python 3.13.

## 🚨 **한국 주식 필수 개념: 호가 단위 (Tick Size)**

### **주식 전문가가 반드시 알아야 할 기초**

한국 주식시장에서는 **가격대별로 호가 단위가 정해져 있습니다**. 이는 주식 거래의 **기본 규칙**입니다.

| 가격대 | 호가 단위 | 예시 |
|--------|----------|------|
| 1,000원 미만 | 1원 | 999원, 998원 |
| 1,000원 ~ 5,000원 | 5원 | 1,000원, 1,005원, 4,995원 |
| 5,000원 ~ 10,000원 | 10원 | 5,000원, 5,010원, 9,990원 |
| **10,000원 ~ 50,000원** | **50원** | **27,000원, 27,050원** (❌ 27,041원 불가능) |
| 50,000원 ~ 100,000원 | 100원 | 50,000원, 50,100원 |
| 100,000원 ~ 500,000원 | 500원 | 100,000원, 100,500원 |
| 500,000원 이상 | 1,000원 | 500,000원, 501,000원 |

### **백테스트 시 반드시 적용해야 하는 규칙**

1. **매수 가격**: 호가 단위로 **올림** (보수적)
   - 예: 27,041원 → 27,050원

2. **매도 가격**: 호가 단위로 **내림** (보수적)
   - 예: 33,348원 → 33,300원

3. **주식 수량**: **정수**만 가능
   - ❌ 36.44주 → 불가능
   - ✅ 36주 → 정상

4. **진입 비용 계산**:
   ```python
   # 잘못된 방법
   entry_cost = 27,041 * 1.0015  # = 27,445.54원 (불가능!)

   # 올바른 방법
   actual_price = 27,050원 (호가 단위 올림)
   entry_cost = 27,050 * 1.0015 = 27,090.575원
   entry_cost = 27,100원 (호가 단위 올림)
   shares = 1,000,000 / 27,100 = 36.9주
   shares = 36주 (정수 변환)
   ```

### **구현 위치**
- **파일**: `backend/app/utils/tick_size.py`
- **함수**:
  - `get_korean_tick_size(price)`: 호가 단위 반환
  - `round_to_tick_up(price, is_korean)`: 올림
  - `round_to_tick_down(price, is_korean)`: 내림
- **적용 위치**: `backend/app/services/backtest.py` (진입/청산 시)

## 🚨 **한국 주식 재무 지표 계산: P/B (Price-to-Book)**

한국 주식은 yfinance가 P/B 비율을 직접 제공하지 않습니다. 따라서 재무제표 데이터로 직접 계산합니다.

**계산 공식:**
```
P/B = 현재 주가 ÷ BPS (주당순자산가치)
BPS = Tangible Book Value ÷ Ordinary Shares Number
```

**예시 (씨젠):**
```python
# yfinance 재무제표에서
Tangible Book Value = 954,281,739,080원  # 유형 순자산
Ordinary Shares Number = 46,112,381주    # 발행주식수
Current Price = 25,200원                 # 현재가

# 계산
BPS = 954,281,739,080 ÷ 46,112,381 = 20,694.70원
P/B = 25,200 ÷ 20,694.70 = 1.22
```

**구현:**
- `backend/app/services/fundamental_analysis.py`:
  - `get_buffett_metrics()`: P/B 자동 계산
  - `get_graham_metrics()`: P/B 자동 계산
- yfinance 제공 시: 그대로 사용
- 없으면: `Tangible Book Value` ÷ `Ordinary Shares Number`로 BPS 계산 → P/B 산출

**PEG와 동일한 방식:**
- PEG: yfinance 제공 → P/E ÷ 성장률 계산 → 기술적 분석만
- P/B: yfinance 제공 → 재무제표 계산 → 조건 스킵

## Quick Start Commands

### Windows (Recommended)
```bash
# Start everything (auto-installs dependencies first time)
START.bat

# Stop all services
STOP.bat

# Individual services
run_backend.bat   # Backend only (http://localhost:8000)
run_frontend.bat  # Frontend only (http://localhost:5173)
```

### Linux/Mac
```bash
# Backend
chmod +x run_backend.sh
./run_backend.sh

# Frontend (in new terminal)
chmod +x run_frontend.sh
./run_frontend.sh
```

### Manual Development Setup
```bash
# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend setup (new terminal)
cd frontend
npm install
npm run dev
```

### Testing
```bash
# Test API connection
python tests/test_api.py

# Test master strategies (Buffett, Lynch, etc.)
python tests/test_master_strategies.py

# Windows batch test
TEST_CONNECTION.bat
```

### Build & Production
```bash
# Frontend build
cd frontend
npm run build      # TypeScript compilation + Vite build
npm run preview    # Preview production build
```

## Architecture Overview

### Backend (FastAPI)
**Entry point:** `backend/app/main.py`

**Core components:**
- **Parser** (`services/parser.py`): Strategy condition parsing engine supporting AND/OR/parentheses, comparison operators, cross detection (MACD.cross_up), and event windows (WITHIN)
- **Backtest** (`services/backtest.py`): Trading simulation with stop-loss/take-profit, position sizing, slippage, and transaction costs
- **Indicators** (`services/indicators.py`): Technical indicators using pandas-ta (MACD, RSI, DMI, Bollinger Bands, OBV, Stochastic)
- **Monte Carlo** (`services/monte_carlo.py`): 1000-iteration bootstrap simulations for performance distribution (P5/P50/P95)
- **Master Strategies** (`services/master_strategies.py`): Pre-built strategies from legendary investors (Buffett, Lynch, Graham, Dalio, Livermore, Soros, Druckenmiller)
- **Fundamental Analysis** (`services/fundamental_analysis.py`): Financial metrics calculation (P/E, P/B, ROE, PEG, debt ratios)
- **Event Scheduler** (`services/event_scheduler.py`): Auto-scheduling for news crawling (FOMC, earnings, elections)
- **News Crawler** (`services/news_crawler.py`): Automated news fetching with Selenium (see AUTO_CRAWLING_SETUP.md)

**API Routes:**
- `/api/v1/analyze`: Custom strategy analysis
- `/api/v1/master-strategy`: Pre-built investment legend strategies
- `/api/v1/events/*`: Event data endpoints
- `/docs`: Interactive API documentation (Swagger UI)

### Frontend (React + TypeScript)
**Entry point:** `frontend/src/App.tsx`

**Key patterns:**
- **State management:** Zustand for global state, React Query for API state
- **API client:** Axios with typed interfaces (`services/api.ts`)
- **Component structure:**
  - `SimpleStrategyForm`: Custom strategy builder
  - `MasterStrategySelector`: Investment legend strategy picker
  - `ResultsDisplay`: Custom strategy results
  - `MasterStrategyResults`: Master strategy results with comparative analysis
  - `NewsFetchButton`: Manual news crawling trigger

**Data files:**
- `frontend/src/data/globalEvents.ts`: Sample economic/political events (2008-2025, 88 events) - manually curated for demo
- `frontend/src/data/stockSymbols.ts`: 50 stock symbols (35 US + 10 Korean) with search functionality

## Strategy Condition Syntax

The parser (`services/parser.py`) supports:

```
# Logical operators
AND, OR, ()

# Comparison operators
<, >, <=, >=, ==

# Cross detection
MACD.cross_up == true
MACD.cross_down == true

# Event windows
WITHIN(event="ELECTION", window_days=20)
```

**Examples:**
```
Entry: ( MACD.cross_up == true AND RSI < 30 ) AND ( +DI > -DI )
Exit: ( MACD.cross_down == true ) OR ( RSI > 70 )

Entry: MACD.cross_up == true AND WITHIN(event="ELECTION", window_days=20)
Exit: RSI > 75
```

## Data Sources

**Current status:** Sample/demo data only (see DATA_SOURCES.md)

- **Global events:** 88 manually-curated events in `globalEvents.ts`
- **Company events:** Sample events for AAPL, TSLA, NVDA, MSFT, GOOGL
- **Stock symbols:** 50 hand-picked symbols
- **Price data:** Currently using mock data; yfinance integration ready but not active

**Production TODO:** See DATA_SOURCES.md and REAL_DATA_INTEGRATION.md for API integration (Yahoo Finance, News API, Finnhub, FRED)

## Master Strategies

Seven pre-built strategies in `services/master_strategies.py`:

1. **Warren Buffett** (Value Investing): ROE > 15%, debt ratio < 0.5, P/E < 20, P/B < 3
2. **Peter Lynch** (Growth): PEG < 1.0, earnings growth > 20%
3. **Benjamin Graham** (Deep Value): P/B < 0.67, current ratio > 2.0
4. **Ray Dalio** (All Weather): 30% stocks, 40% bonds, 30% gold/commodities
5. **Jesse Livermore** (Trend Following): 52-week high breakout, pyramiding
6. **George Soros** (Macro): Economic indicators + market sentiment
7. **Stanley Druckenmiller** (Growth + Macro): High growth + macro trends

Each strategy has:
- Entry/exit conditions
- Risk parameters (stop-loss %, take-profit %)
- Required fundamental data
- Historical performance metrics

See MASTER_STRATEGIES.md for detailed documentation.

## Key Technical Details

### Backtest Engine
- Initial capital: $100,000
- Position sizing: Configurable (default 100%)
- Transaction costs: 10 bps
- Slippage: 5 bps
- Risk management: Stop-loss and take-profit built-in
- Metrics: CAGR, Sharpe ratio, Max Drawdown, Win Rate, Profit Factor

### Monte Carlo Simulation
- 1000 bootstrap iterations
- Resampling with replacement
- Output: P5/P50/P95 percentiles for CAGR and MaxDD
- Confidence intervals for robustness assessment

### Indicators (pandas-ta)
All technical indicators use pandas-ta library:
- MACD (12, 26, 9)
- RSI (14)
- DMI/ADX (14)
- Bollinger Bands (20, 2)
- OBV, Stochastic, SMA, EMA

## Important Files to Review

- `START_HERE.txt`: User-facing quick start guide
- `DATA_SOURCES.md`: Data architecture and future API integration
- `REAL_DATA_INTEGRATION.md`: Production data setup guide
- `AUTO_CRAWLING_SETUP.md`: News crawler setup (Selenium + ChromeDriver)
- `MASTER_STRATEGIES.md`: Investment legend strategy documentation
- `QUICK_START.md`: Development quickstart

## Development Notes

- **Git repository:** Initialized with comprehensive .gitignore for Python and Node.js
- **Test structure:** Tests organized in `tests/` directory
- **Cross-origin:** CORS is enabled for localhost:5173 → localhost:8000
- **Sample data:** All current data is mock/demo; suitable for education only
- **Legal disclaimer:** Not investment advice; past performance doesn't guarantee future results

## Common Workflows

### Adding a new technical indicator
1. Add calculation in `backend/app/services/indicators.py`
2. Update parser in `services/parser.py` for condition support
3. Add UI input in `frontend/src/components/SimpleStrategyForm.tsx`

### Adding a new master strategy
1. Define strategy class in `backend/app/services/master_strategies.py`
2. Register in `MASTER_STRATEGIES` dict
3. Add UI option in `frontend/src/components/MasterStrategySelector.tsx`
4. Document in `MASTER_STRATEGIES.md`

### Integrating real data APIs
Follow `REAL_DATA_INTEGRATION.md` for:
- yfinance for historical prices
- News API / Finnhub for events
- FRED API for economic indicators
- FinBERT for sentiment analysis

## ✅ Critical Features (절대 삭제/누락 금지!)

### 1. 조건별 체크 표시 (Condition Details)

**위치:**
- 백엔드: `backend/app/api/routes.py` 385-434줄
- 프론트엔드: `frontend/src/components/MasterStrategyResults.tsx` 216-262줄

**기능:** 마스터 전략 실행 시 각 조건의 통과/실패 여부 표시

**지원 전략:** Warren Buffett, Peter Lynch, Benjamin Graham, William O'Neil

**백엔드 로직:**
```python
if request.strategy_name in ["buffett", "lynch", "graham", "oneil"]:
    condition_details = analyzer.get_{strategy}_condition_details()
    condition_checks = [ConditionCheck(**cond) for cond in condition_details]
```

**프론트엔드 표시:**
- 초록색 박스: 조건 통과 ✓
- 빨간색 박스: 조건 실패 ✗
- 통과율 표시: "3 / 5개"

### 2. 한국 주식 가격 포맷 (호가 단위)

**위치:**
- 백엔드: `backend/app/services/indicators.py` `round_to_korean_tick()` 함수
- 백엔드: `backend/app/services/backtest.py` 주식 수 정수 처리
- 프론트엔드: `frontend/src/components/MasterStrategyResults.tsx` `formatPrice()` 함수

**기능:** 한국 주식(KRW)은 정수로 표시, 소수점 없음

**호가 단위 규칙:**
```python
if price < 1000: tick = 1원
elif price < 5000: tick = 5원
elif price < 10000: tick = 10원
elif price < 50000: tick = 50원
elif price < 100000: tick = 100원
elif price < 500000: tick = 500원
else: tick = 1000원
```

### 3. PEG Ratio 자동 계산

**위치:** `backend/app/services/fundamental_analysis.py` 298-331줄

**기능:** PEG Ratio를 3단계로 계산:
1. yfinance에서 제공하는 PEG 사용
2. 없으면 계산: `PEG = P/E ÷ 이익성장률(%)`
3. 계산 불가능하면 None + 이유 표시

**데이터 소스 우선순위:**
- 이익 성장률: DART API (한국 주식) → yfinance → 분기별 재무제표 직접 계산
- PEG: yfinance 제공 값 → P/E ÷ 성장률 계산 → None (계산 불가)

### 4. DART API 통합 (한국 주식)

**위치:**
- 설정: `backend/.env` 파일
- Config: `backend/app/core/config.py` DART_API_KEY
- 클라이언트: `backend/app/services/dart_api.py`
- 사용: `backend/app/services/fundamental_analysis.py`

**설정 방법:**
```bash
# 1. .env 파일 생성
copy backend\.env.example backend\.env

# 2. API 키 입력
DART_API_KEY=your_key_here

# 3. 백엔드 재시작
STOP.bat
START.bat
```

**자동 fallback:**
- DART API 키 있음 → DART 사용 (한국 주식)
- DART API 키 없음 → yfinance 사용 (경고 메시지)
- DART 실패 → yfinance로 자동 fallback

### 5. 대가 전략 알고리즘 (수정 완료 2025-10-05)

**위치:** `backend/app/services/master_strategies.py`

**수정 내역:**
- **Warren Buffett**: RSI 과매도 대기 삭제 → 펀더멘털 충족 시 즉시 매수
- **Peter Lynch**: 52주 고점 근처 매수 → PEG < 1.0 확인 시 즉시 매수
- **Benjamin Graham**: ffill() 버그 수정 → 펀더멘털 기반 청산
- **Ray Dalio**: 분기별 리밸런싱 → Buy & Hold로 단순화
- **Jesse Livermore**: 20일 신고가 돌파 → **52주(252일) 신고가 돌파**
- **William O'Neil**: MA21 아래면 청산 → MA21 하향 돌파 (크로스다운)

### 6. UI: 한 번에 백테스트 실행

**위치:**
- App: `frontend/src/App.tsx` handleSubmit, handleMasterSubmit
- 버튼: `frontend/src/components/MasterStrategySelector.tsx` 228줄
- 버튼: `frontend/src/components/SimpleStrategyForm.tsx` 277줄

**수정 내역:** "분석 시작" → "백테스트 실행" 2단계를 "🚀 백테스트 실행" 1단계로 통합

### 🔒 수정 시 주의사항

**절대 삭제하면 안 되는 코드:**
1. 조건 체크 로직 (routes.py 385-434줄)
2. 한국 주식 포맷 (backtest.py, MasterStrategyResults.tsx)
3. PEG 계산 (fundamental_analysis.py 298-331줄)
4. DART API fallback (fundamental_analysis.py 251-297줄)

**자주 발생하는 버그:**
- 조건 체크 누락: 백엔드에서 `condition_checks=None` 전송
- 한국 주식 소수점: formatPrice 함수 또는 백엔드 정수 변환 누락
- PEG 없음: 계산 로직 누락 또는 DART API 실패

**참고 문서:**
- `claudedocs/master_strategies_audit.md` - 대가 전략 검증 보고서
- `DART_SETUP.md` - DART API 설정 가이드
- `backend/ENV_SETUP.md` - 환경변수 설정 가이드

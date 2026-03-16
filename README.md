# Financial Research Copilot - 금융 리서치 코파일럿

> **투자 대가들의 전략을 백테스팅하고, 확률적 예측으로 투자 의사결정을 지원하는 금융 분석 플랫폼**

---

## 주요 화면

> **Note:** 로컬 개발 전용 프로젝트입니다. 아래는 주요 기능 스크린샷 예정 영역입니다.

### 전략 분석 인터페이스
```
┌─────────────────────────────────────────────────────────────────┐
│  Financial Research Copilot                                     │
├─────────────────────────────────────────────────────────────────┤
│  [종목 선택]  삼성전자 (005930.KS)  ▼                           │
│  [기간 설정]  2020-01-01 ~ 2024-12-31                          │
│                                                                 │
│  ┌─ 진입 조건 ──────────────────────────────────────────────┐  │
│  │ ( MACD.cross_up == true AND RSI < 30 ) AND ( +DI > -DI ) │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌─ 청산 조건 ──────────────────────────────────────────────┐  │
│  │ ( MACD.cross_down == true ) OR ( RSI > 70 )              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  [손절] -15%    [익절] +50%    [포지션 크기] 100%              │
│                                                                 │
│  [ 백테스트 실행 ]                                             │
└─────────────────────────────────────────────────────────────────┘
```

### 백테스트 결과
```
┌─────────────────────────────────────────────────────────────────┐
│  백테스트 결과 - 삼성전자                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  CAGR: 18.5%     Sharpe: 1.23     MaxDD: -22.3%                │
│  Win Rate: 62%   Profit Factor: 1.85   총 거래: 24건           │
│                                                                 │
│  ┌─ 몬테카를로 시뮬레이션 (1000회) ─────────────────────────┐  │
│  │  CAGR P5: 8.2%  │  P50: 17.8%  │  P95: 28.4%            │  │
│  │  MaxDD P5: -35%  │  P50: -20%   │  P95: -12%             │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  조건 체크:                                                     │
│  [✓] P/E < 20        [✓] ROE > 15%     [✗] P/B < 3            │
│  [✓] 부채비율 < 0.5   [✓] 이익 성장률 > 0%                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 핵심 기능

| 기능 | 설명 |
|------|------|
| **확률적 예측** | 과거 데이터 기반 조건부 확률 분석 (상승/하락 확률, 95% 신뢰구간) |
| **전략 백테스팅** | 사용자 정의 매매 규칙 검증 (CAGR, Sharpe, MaxDD, Hit Ratio) |
| **몬테카를로 시뮬레이션** | 1000회 부트스트랩으로 성과 분포 추정 (P5/P50/P95) |
| **투자 대가 전략** | Buffett, Lynch, Graham, Livermore 등 7가지 전설적 전략 |
| **한국 주식 지원** | DART API로 정확한 재무제표 + 호가 단위 자동 적용 |
| **기술지표 분석** | MACD, RSI, DMI, Bollinger Bands, OBV, Stochastic 등 |
| **이벤트 연동** | FOMC, 실적발표, 선거 등 타임스탬프 기반 윈도우 필터 |

---

## 기술 스택

### Backend

| 기술 | 용도 |
|------|------|
| **FastAPI** | 고성능 Python API 프레임워크 |
| **Pandas / NumPy** | 데이터 처리 및 수치 연산 |
| **Pandas-TA** | 기술지표 계산 라이브러리 |
| **yfinance** | 주가 데이터 수집 |
| **DART API** | 한국 주식 재무제표 (금융감독원) |
| **Pydantic** | 데이터 검증 및 타입 안전성 |

### Frontend

| 기술 | 용도 |
|------|------|
| **React 18** | 모던 UI 라이브러리 |
| **TypeScript** | 타입 안전성 |
| **TailwindCSS** | 유틸리티 기반 스타일링 |
| **Zustand** | 경량 상태 관리 |
| **React Query** | API 상태 관리 및 캐싱 |
| **Recharts** | 차트 시각화 |

---

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │   Strategy Form  │  │  Master Strategy │  │   Results    │  │
│  │   (조건 입력)    │  │   Selector       │  │   Display    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └──────┬───────┘  │
│           └─────────────────────┴────────────────────┘          │
│                                 │ Axios + React Query           │
└─────────────────────────────────┼───────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Routes                             │  │
│  │  /api/v1/analyze       - 커스텀 전략 분석                 │  │
│  │  /api/v1/master-strategy - 대가 전략 백테스트             │  │
│  │  /api/v1/events/*      - 이벤트 데이터                    │  │
│  └─────────────────────────────┬────────────────────────────┘  │
│                                │                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Parser    │  │  Backtest   │  │   Monte Carlo           │ │
│  │ (조건 파싱) │  │   Engine    │  │   Simulation            │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│         ▼                ▼                      ▼               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Technical Indicators (pandas-ta)             │  │
│  │  MACD, RSI, DMI, Bollinger Bands, OBV, Stochastic        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                │                                │
│  ┌─────────────────────────────┴────────────────────────────┐  │
│  │                 Fundamental Analysis                      │  │
│  │  P/E, P/B, ROE, PEG, Debt Ratio, Cash Flow               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                  │
           ┌──────────────────────┼──────────────────────┐
           ▼                      ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│     yfinance     │  │    DART API      │  │   News Crawler   │
│   (글로벌 주가)  │  │  (한국 재무제표) │  │   (Selenium)     │
└──────────────────┘  └──────────────────┘  └──────────────────┘
```

---

## 기술적 도전과 해결

### 1. 한국 주식 호가 단위 (Tick Size) 정확한 처리

**문제:** 한국 주식시장은 가격대별로 호가 단위가 다름. 백테스트에서 실제로 거래 불가능한 가격으로 계산하면 결과가 비현실적

**해결:**

```python
# backend/app/utils/tick_size.py
def get_korean_tick_size(price: float) -> int:
    """가격대별 호가 단위 반환"""
    if price < 1000:
        return 1
    elif price < 5000:
        return 5
    elif price < 10000:
        return 10
    elif price < 50000:
        return 50    # 27,041원 → 27,050원 (올림)
    elif price < 100000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000

def round_to_tick_up(price: float, is_korean: bool = False) -> float:
    """매수 시 호가 단위로 올림 (보수적)"""
    if not is_korean:
        return price
    tick = get_korean_tick_size(price)
    return math.ceil(price / tick) * tick

def round_to_tick_down(price: float, is_korean: bool = False) -> float:
    """매도 시 호가 단위로 내림 (보수적)"""
    if not is_korean:
        return price
    tick = get_korean_tick_size(price)
    return math.floor(price / tick) * tick
```

**적용:** 백테스트 엔진에서 진입/청산 시 자동 적용

---

### 2. PEG Ratio 자동 계산 (yfinance 미제공 시)

**문제:** yfinance가 한국 주식의 PEG ratio를 제공하지 않음. Peter Lynch 전략 등에서 PEG는 필수 지표

**해결:** 3단계 fallback 로직

```python
# backend/app/services/fundamental_analysis.py
def calculate_peg_ratio(ticker: str, info: dict) -> Optional[float]:
    """PEG Ratio 계산 (3단계 fallback)"""

    # 1단계: yfinance 제공 값 사용
    if "pegRatio" in info and info["pegRatio"]:
        return info["pegRatio"]

    # 2단계: P/E와 성장률로 직접 계산
    pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    earnings_growth = info.get("earningsGrowth")  # 예: 0.25 = 25%

    if pe_ratio and earnings_growth and earnings_growth > 0:
        growth_pct = earnings_growth * 100  # 0.25 → 25
        return pe_ratio / growth_pct

    # 3단계: DART API에서 성장률 가져오기 (한국 주식)
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        dart_growth = get_dart_earnings_growth(ticker)
        if dart_growth and pe_ratio:
            return pe_ratio / dart_growth

    return None  # 계산 불가
```

**결과:** 한국 주식에서도 정확한 PEG 기반 전략 적용 가능

---

### 3. 전략 조건 파싱 엔진 (AND/OR/괄호 지원)

**문제:** 사용자가 복잡한 매매 조건을 자연스럽게 입력하고, 이를 프로그래밍 로직으로 변환해야 함

**해결:** 재귀 하강 파서 (Recursive Descent Parser) 구현

```python
# backend/app/services/parser.py
class StrategyParser:
    """
    지원 문법:
    - 논리 연산: AND, OR, ()
    - 비교 연산: <, >, <=, >=, ==
    - 교차 감지: MACD.cross_up, RSI.cross_down
    - 이벤트: WITHIN(event="ELECTION", window_days=20)
    """

    def parse(self, condition: str, data: pd.DataFrame) -> pd.Series:
        tokens = self.tokenize(condition)
        return self._parse_expression(tokens, data)

    def _parse_expression(self, tokens: list, data: pd.DataFrame) -> pd.Series:
        """OR 연산 처리"""
        left = self._parse_term(tokens, data)
        while tokens and tokens[0].upper() == "OR":
            tokens.pop(0)  # consume OR
            right = self._parse_term(tokens, data)
            left = left | right
        return left

    def _parse_term(self, tokens: list, data: pd.DataFrame) -> pd.Series:
        """AND 연산 처리"""
        left = self._parse_factor(tokens, data)
        while tokens and tokens[0].upper() == "AND":
            tokens.pop(0)  # consume AND
            right = self._parse_factor(tokens, data)
            left = left & right
        return left
```

**사용 예시:**
```
진입: ( MACD.cross_up == true AND RSI < 30 ) AND ( +DI > -DI )
청산: ( MACD.cross_down == true ) OR ( RSI > 70 )
```

---

### 4. 몬테카를로 시뮬레이션으로 전략 견고성 검증

**문제:** 백테스트 결과가 과적합(overfitting)인지 판단하기 어려움

**해결:** 1000회 부트스트랩으로 성과 분포 추정

```python
# backend/app/services/monte_carlo.py
def run_monte_carlo(trades: List[Trade], n_simulations: int = 1000) -> MonteCarloResult:
    """
    부트스트랩 시뮬레이션으로 성과 분포 추정
    - 거래 기록을 무작위로 재추출하여 1000개의 가상 시나리오 생성
    - P5, P50, P95 백분위수로 최악/중간/최선 케이스 제공
    """
    cagrs = []
    max_drawdowns = []

    for _ in range(n_simulations):
        # 복원 추출 (with replacement)
        sampled_trades = np.random.choice(trades, size=len(trades), replace=True)
        metrics = calculate_metrics(sampled_trades)
        cagrs.append(metrics.cagr)
        max_drawdowns.append(metrics.max_drawdown)

    return MonteCarloResult(
        cagr_p5=np.percentile(cagrs, 5),
        cagr_p50=np.percentile(cagrs, 50),
        cagr_p95=np.percentile(cagrs, 95),
        maxdd_p5=np.percentile(max_drawdowns, 5),
        maxdd_p50=np.percentile(max_drawdowns, 50),
        maxdd_p95=np.percentile(max_drawdowns, 95),
    )
```

**결과:** CAGR 18%가 운인지 실력인지 신뢰구간으로 판단 가능

---

## 투자 대가 전략

7가지 전설적인 투자 전략을 시뮬레이션:

| 전략 | 투자자 | 핵심 원칙 | 손절/익절 |
|------|--------|----------|----------|
| **Value Investing** | Warren Buffett | ROE > 15%, P/E < 20, P/B < 3 | -25% / +50% |
| **Growth Investing** | Peter Lynch | PEG < 1.0, 이익 성장률 > 20% | -15% / +50% |
| **Deep Value** | Benjamin Graham | P/B < 0.67, 유동비율 > 2.0 | -20% / +30% |
| **All Weather** | Ray Dalio | 주식 30%, 채권 40%, 금 30% | N/A (장기) |
| **Trend Following** | Jesse Livermore | 52주 신고가 돌파, 피라미딩 | -8% / +50% |
| **CAN SLIM** | William O'Neil | C-A-N-S-L-I-M 7가지 조건 | -7% / +20% |
| **Macro Trading** | George Soros | 경제지표 + 시장 심리 | -10% / +30% |

---

## 실행 방법

### Windows (권장)

```bash
# 전체 시작 (자동 의존성 설치)
START.bat

# 종료
STOP.bat
```

### 수동 실행

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (새 터미널)
cd frontend
npm install
npm run dev
```

### 접속

- **프론트엔드:** http://localhost:5173
- **API 문서:** http://localhost:8000/docs

---

## 프로젝트 구조

```
auto_stock/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 엔트리포인트
│   │   ├── api/
│   │   │   └── routes.py              # API 엔드포인트
│   │   ├── services/
│   │   │   ├── parser.py              # 전략 조건 파싱
│   │   │   ├── backtest.py            # 백테스트 엔진
│   │   │   ├── indicators.py          # 기술지표 계산
│   │   │   ├── monte_carlo.py         # 몬테카를로 시뮬레이션
│   │   │   ├── master_strategies.py   # 대가 전략
│   │   │   ├── fundamental_analysis.py # 재무 분석
│   │   │   └── dart_api.py            # DART API 연동
│   │   ├── models/
│   │   │   └── schemas.py             # Pydantic 스키마
│   │   └── utils/
│   │       └── tick_size.py           # 호가 단위 처리
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                    # 메인 앱
│   │   ├── components/
│   │   │   ├── SimpleStrategyForm.tsx # 커스텀 전략 폼
│   │   │   ├── MasterStrategySelector.tsx # 대가 전략 선택
│   │   │   ├── ResultsDisplay.tsx     # 결과 표시
│   │   │   └── MasterStrategyResults.tsx # 조건 체크 UI
│   │   ├── services/
│   │   │   └── api.ts                 # Axios 클라이언트
│   │   └── data/
│   │       ├── globalEvents.ts        # 이벤트 데이터
│   │       └── stockSymbols.ts        # 종목 리스트
│   └── package.json
├── tests/
│   ├── test_api.py
│   └── test_master_strategies.py
├── START.bat                          # 원클릭 시작
├── STOP.bat                           # 원클릭 종료
└── README.md
```

---

## 향후 개선 계획

- [ ] 실시간 모니터링 및 알림
- [ ] 멀티 종목 포트폴리오 분석
- [ ] PostgreSQL + TimescaleDB 연동
- [ ] 사용자 인증 및 전략 저장
- [ ] 모바일 반응형 UI

---

## 법적 고지

**본 서비스는 교육 및 리서치 목적으로만 제공되며, 투자 조언이 아닙니다.**

- 과거 성과는 미래 수익을 보장하지 않습니다
- 모든 투자 결정은 본인의 책임입니다
- 실제 투자 전 전문가와 상담하세요

---

## 개발자

GitHub: [@ggoomter](https://github.com/ggoomter)

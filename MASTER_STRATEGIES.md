# 투자 대가 전략 백테스팅 시스템

실제 투자 대가들의 전략을 과거 데이터로 시뮬레이션하는 시스템입니다.

## 📚 구현된 전략

### 1. Warren Buffett - 가치 투자
**핵심 원칙:**
- ROE > 15% (자기자본이익률)
- 부채비율 < 0.5
- P/E < 20, P/B < 3 (저평가)
- 일관된 이익 성장
- 경쟁 우위(moat) 보유

**투자 방식:**
- 우량 기업을 저평가 시점에 매수
- 장기 보유 (수년~수십년)
- 손절: -25% (넓은 손절폭)
- 익절: +50% (높은 목표)

**필요 데이터:** P/E, P/B, ROE, 부채비율, 영업현금흐름

---

### 2. Peter Lynch - 성장주 투자
**핵심 원칙:**
- PEG ratio < 1.0 (저평가된 성장주)
- 이익 성장률 > 20%
- 중소형주 선호
- "이해하는 기업에 투자"

**투자 방식:**
- 저평가된 고성장 기업 발굴
- 중장기 보유 (1~5년)
- 손절: -15%
- 익절: +50%

**필요 데이터:** PEG, EPS 성장률, 매출 성장률

---

### 3. Benjamin Graham - 딥 밸류
**핵심 원칙:**
- P/B < 0.67 (청산가치 이하)
- 유동비율 > 2.0
- 부채/자산 < 0.5
- 배당 지급 이력

**투자 방식:**
- 청산가치 이하로 거래되는 초저평가 기업
- 중기 보유 (1~3년)
- 손절: -20%
- 익절: +30% (보수적)

**필요 데이터:** P/B, 유동비율, 부채비율, 배당

---

### 4. Ray Dalio - 올웨더 포트폴리오
**핵심 원칙:**
- 분산 투자: 주식 30%, 채권 40%, 금/원자재 30%
- 리스크 패리티
- 분기별 리밸런싱
- 모든 경제 환경에 대비

**투자 방식:**
- Buy & Hold + 분기별 리밸런싱
- 영구 보유
- 손절 없음 (장기 자산 배분)

**필요 데이터:** 다중 자산 가격 데이터

---

### 5. Jesse Livermore - 추세 추종
**핵심 원칙:**
- 52주 신고가 돌파 매수
- 추세선 이탈 손절
- 피라미딩 (분할 매수)
- "시장이 옳다"

**투자 방식:**
- 신고가 돌파와 추세 추종
- 단기~중기 (추세 지속)
- 손절: -8% (타이트)
- 익절: +50%

**필요 데이터:** 가격, 거래량

---

### 6. William O'Neil - CAN SLIM
**핵심 원칙:**
- C: 당기순이익 25%+ 성장
- A: 연간 수익 증가
- N: 신제품/신고가
- S: 소형주, 적은 유통주식
- L: 시장 선도주
- I: 기관 매수
- M: 시장 방향성

**투자 방식:**
- 고성장 모멘텀 주식 선별
- 단기~중기 (모멘텀 지속)
- 손절: -8% (7-8% 손절 원칙)
- 익절: +25%

**필요 데이터:** EPS 성장률, 거래량, ROE

---

## 🚀 사용 방법

### 1. 서버 실행
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 2. 사용 가능한 전략 확인
```bash
curl http://localhost:8000/master-strategies
```

### 3. 전략 백테스트 실행

**API 요청:**
```bash
curl -X POST http://localhost:8000/master-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "buffett",
    "symbols": ["AAPL"],
    "date_range": {
      "start": "2020-01-01",
      "end": "2024-12-31"
    },
    "simulate": {
      "bootstrap_runs": 1000,
      "transaction_cost_bps": 10,
      "slippage_bps": 5
    },
    "output_detail": "full"
  }'
```

**Python 테스트:**
```bash
python test_master_strategies.py
```

---

## 📊 API 엔드포인트

### GET `/master-strategies`
사용 가능한 전략 목록 조회

**응답 예시:**
```json
{
  "strategies": [
    {
      "name": "buffett",
      "description": "우량 기업을 저평가 시점에 매수하여 장기 보유",
      "info": {
        "name": "Warren Buffett - Value Investing",
        "key_principles": ["ROE > 15%", "부채비율 < 0.5", ...],
        "holding_period": "장기 (수년~수십년)",
        "risk_profile": "낮음 (안전마진 중시)"
      }
    }
  ]
}
```

### POST `/master-strategy`
특정 전략 백테스트 실행

**요청:**
```json
{
  "strategy_name": "buffett",
  "symbols": ["AAPL"],
  "date_range": {
    "start": "2020-01-01",
    "end": "2024-12-31"
  },
  "simulate": {
    "bootstrap_runs": 1000,
    "transaction_cost_bps": 10,
    "slippage_bps": 5
  },
  "output_detail": "full"
}
```

**응답:**
```json
{
  "strategy_info": {
    "name": "Warren Buffett - Value Investing",
    "description": "우량 기업을 저평가 시점에 매수하여 장기 보유",
    "key_principles": [...],
    "holding_period": "장기 (수년~수십년)",
    "risk_profile": "낮음 (안전마진 중시)"
  },
  "backtest": {
    "metrics": {
      "CAGR": 0.1234,
      "Sharpe": 1.23,
      "MaxDD": -0.15,
      "HitRatio": 0.65,
      "AvgWin": 0.08,
      "AvgLoss": -0.05
    },
    "cost_assumptions_bps": {
      "fee": 10,
      "slippage": 5
    }
  },
  "fundamental_screen": {
    "metrics": {
      "ROE": 28.5,
      "debt_to_equity": 0.32,
      "PE": 18.2,
      "PB": 2.1
    },
    "criteria": {
      "ROE_above_15": true,
      "low_debt": true,
      "reasonable_PE": true,
      "low_PB": true,
      "passed_count": 4,
      "total_count": 5,
      "pass_rate": 0.8
    }
  },
  "signal_examples": [
    {
      "date": "2020-03-15",
      "symbol": "AAPL",
      "reason": ["Warren Buffett - Value Investing"]
    }
  ]
}
```

---

## 🏗️ 시스템 아키텍처

```
backend/
├── app/
│   ├── services/
│   │   ├── fundamental_analysis.py  # 재무제표 분석 (yfinance)
│   │   ├── master_strategies.py     # 투자 대가 전략 구현
│   │   ├── backtest.py              # 백테스팅 엔진
│   │   └── indicators.py            # 기술적 지표
│   ├── models/
│   │   └── schemas.py               # API 스키마
│   └── api/
│       └── routes.py                # API 엔드포인트
```

### 주요 컴포넌트

**1. FundamentalAnalyzer** (`fundamental_analysis.py`)
- yfinance를 활용한 재무제표 분석
- 각 대가별 펀더멘털 지표 계산
- 투자 기준 체크 함수

**2. MasterStrategy** (`master_strategies.py`)
- 각 대가의 실제 전략 구현
- 매매 시그널 생성 로직
- 전략별 리스크 파라미터

**3. BacktestEngine** (`backtest.py`)
- 시그널 기반 백테스팅
- 성과 지표 계산 (CAGR, Sharpe, MDD 등)
- 거래 비용 반영

---

## 🧪 테스트 방법

### 전체 전략 테스트
```bash
python test_master_strategies.py
```

### 개별 전략 테스트
```python
import httpx

response = httpx.post(
    "http://localhost:8000/master-strategy",
    json={
        "strategy_name": "buffett",  # buffett, lynch, graham, dalio, livermore, oneil
        "symbols": ["AAPL"],
        "date_range": {
            "start": "2020-01-01",
            "end": "2024-12-31"
        }
    },
    timeout=60.0
)

print(response.json())
```

---

## 📈 데이터 소스

### yfinance (무료)
- **재무 지표:** P/E, P/B, ROE, 부채비율 등
- **재무제표:** 손익계산서, 대차대조표, 현금흐름표
- **가격 데이터:** OHLCV, 조정 가격
- **제한사항:** API rate limit, 일부 지표 누락 가능

### 향후 확장 가능성
- Alpha Vantage (무료 500 calls/day)
- Financial Modeling Prep (무료 250 calls/day)
- Yahoo Finance API (백업)

---

## ⚠️ 주의사항

### 1. 교육 목적
- 실제 투자 조언이 아님
- 과거 성과가 미래 수익을 보장하지 않음

### 2. 데이터 제약 (⭐ 중요)
- **yfinance는 최근 4분기 재무제표만 제공**
- **백테스트 가능 기간: 최근 1년만 정확**
- 그 이전 기간은 기술적 분석만 사용
- 실적 발표 지연 45일 반영 (Look-ahead bias 방지)
- 실시간 데이터 아님 (약 1일 지연)

### 3. Look-Ahead Bias 방지
- **각 매수 시점마다 그 당시 공개된 재무제표만 사용**
- 분기말 + 45일 후 실적 발표 가정
- 예: 2024년 6월 매수 → 2024년 Q1 (3/31) 재무제표 사용
- 미래 정보 사용하지 않음

### 4. 전략 간소화
- 실제 대가들의 전략을 단순화하여 구현
- 정성적 판단 (경영진 평가, 산업 분석 등)은 미포함
- 정량적 지표 위주로 구현

### 5. 백테스트 한계
- 생존자 편향 (현재 상장된 기업만)
- 과거 데이터 최적화 위험
- 슬리피지, 유동성 리스크 단순화

---

## 🔮 향후 개선사항

### 단기
- [ ] 다중 종목 포트폴리오 백테스팅
- [ ] 월간/분기별 리포트 생성
- [ ] 차트 시각화 추가

### 중기
- [ ] 더 많은 투자 대가 전략 추가 (George Soros, Stanley Druckenmiller 등)
- [ ] 섹터별, 국가별 분석
- [ ] 리스크 조정 수익률 계산 개선

### 장기
- [ ] 실시간 모니터링 시스템
- [ ] 자동 매매 인터페이스 (모의투자)
- [ ] 머신러닝 기반 전략 최적화

---

## 📞 문의

이슈나 개선사항은 GitHub Issues에 등록해주세요.

**면책조항:** 이 시스템은 교육 및 연구 목적으로만 사용하세요. 투자 결정은 본인 책임입니다.

# Jesse Livermore 전략 가이드

## 개요

Jesse Livermore의 트레이딩 방법론을 두 가지 버전으로 구현했습니다:

1. **순수 Livermore (Pure Livermore)**: 역사적으로 정확한 방법론
2. **Modern Livermore**: 현대적 개선 버전 (MA, Trailing Stop, 부분 익절)

---

## 1. 순수 Jesse Livermore 전략

### 핵심 원칙 (Reminiscences of a Stock Operator 기반)

1. **피봇 포인트 돌파 매수** (52주 신고가)
2. **추세가 끝날 때까지 전량 보유**
3. **"It never was my thinking that made the big money. It was my sitting."**
4. **이익을 손실로 바꾸지 마라**
5. **감정 배제, 시장이 말할 때까지 기다림**

### 전략 특징

- ❌ **MA20/MA50 같은 기술적 지표 사용 안 함** (당시 컴퓨터 없었음)
- ❌ **부분 익절 없음** (추세 끝까지 보유가 원칙)
- ✅ **가격 패턴과 거래량만으로 판단**
- ✅ **5일 연속 하락 + 거래량 증가 = 청산**

### 진입 조건

```
1. 52주(252일) 신고가 돌파
2. 거래량 급증 (평균 대비 1.5배 이상)
```

### 청산 조건

```
5일 연속 하락 + 거래량 증가 (명확한 추세 반전)
```

### 리스크 관리

```python
- 손절: -8% (Never let a profit turn into a loss)
- 익절: 무제한 (추세 끝까지 보유, 청산 신호로만 매도)
- 포지션: 100% 투자 (equal_weight)
```

---

## 2. Modern Livermore 전략

### 핵심 원칙

순수 Livermore 기반 + 현대적 개선:
1. 신고가 돌파 매수
2. 추세 추종
3. 이익을 손실로 바꾸지 마라

### 현대적 개선 사항

- ✅ **MA20 사용** (빠른 추세 이탈 감지)
- ✅ **Trailing Stop** (고점 대비 -10%)
- ✅ **부분 익절** (+20% = 50%, +40% = 25%)
- ✅ **3일 연속 하락 패턴 조기 감지**

### 진입 조건

```
1. 52주(252일) 신고가 돌파
2. MA20, MA50 위에 있음 (상승 추세 확인)
3. MA20이 상승 중
4. 거래량 증가 (평균 대비 1.3배 이상)
```

### 청산 조건

```
1. MA20 하향 돌파 (빠른 청산)
   OR
2. 3일 연속 하락 + 거래량 증가 (추세 반전 조기 감지)
```

### 리스크 관리

```python
- 손절: -8% (타이트한 손절)
- 익절: +30% (현실적 목표)
- 포지션: 100% 투자 (equal_weight)
- Trailing Stop: 고점 대비 -10% (백테스트 엔진에서 자동 적용)
- 부분 익절: +20% = 50%, +40% = 25% (백테스트 엔진에서 자동 적용)
```

---

## 전략 비교

| 항목 | Pure Livermore | Modern Livermore |
|------|----------------|------------------|
| **역사적 정확성** | ✅ 매우 높음 | ❌ 현대적 재해석 |
| **기술적 지표** | ❌ 없음 | ✅ MA20 사용 |
| **청산 신호** | 5일 연속 하락 | MA20 하향 돌파 OR 3일 하락 |
| **부분 익절** | ❌ 없음 | ✅ +20%, +40% |
| **Trailing Stop** | ❌ 없음 | ✅ 고점 -10% |
| **익절 목표** | 무제한 (추세 끝까지) | +30% |
| **적합한 시장** | 강한 트렌드 시장 | 변동성 높은 시장 |

---

## 사용 방법

### 1. 웹 UI에서 사용

1. **START.bat** 실행 (백엔드 + 프론트엔드 시작)
2. 브라우저에서 **http://localhost:5173** 접속
3. **"투자 대가 전략"** 탭 선택
4. 전략 선택:
   - **Jesse Livermore - Pure Trend Following** (순수 버전)
   - **Modern Livermore - Improved Trend Following** (현대적 버전)
5. 종목 입력 (예: 씨젠 = `096530.KQ`)
6. 백테스트 기간 설정
7. **"백테스트 실행"** 클릭

### 2. API로 사용

```bash
# 백엔드만 실행
cd backend
venv\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 순수 Livermore 테스트

```bash
curl -X POST http://localhost:8000/api/v1/master-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "livermore",
    "symbols": ["096530.KQ"],
    "date_range": {
      "start": "2024-01-01",
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

#### Modern Livermore 테스트

```bash
curl -X POST http://localhost:8000/api/v1/master-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "modern_livermore",
    "symbols": ["096530.KQ"],
    "date_range": {
      "start": "2024-01-01",
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

---

## 매수 금액 문제 해결

### 문제

- **기존**: 100만원 자본금으로 단 1-2주만 매수 (약 5만원, 5% 투자)
- **원인**: `vol_target_10` 포지션 사이징이 변동성 데이터 없을 때 50%만 투자

### 해결

두 전략 모두 **`equal_weight`** (100% 투자) 사용:

```python
# LivermoreStrategy, ModernLivermoreStrategy
def get_risk_params(self) -> RiskParams:
    return RiskParams(
        stop_pct=0.08,
        take_pct=...,
        position_sizing="equal_weight"  # 100% 투자
    )
```

### 결과

- **씨젠 (27,050원)**: 36주 매수 (973,800원, 97.38% 투자) ✅
- **호가 단위 적용**: 27,041원 → 27,050원 (50원 단위)
- **정수 주식 수**: 36.97주 → 36주

---

## 호가 단위 (Tick Size) 적용

한국 주식은 **가격대별 호가 단위**가 정해져 있습니다.

| 가격대 | 호가 단위 | 예시 |
|--------|----------|------|
| 10,000 ~ 50,000원 | **50원** | 27,000원, 27,050원 |
| 50,000 ~ 100,000원 | 100원 | 75,000원, 75,100원 |

### 백테스트에 자동 적용

```python
# backend/app/utils/tick_size.py
def round_to_tick_up(price: float, is_korean: bool = False) -> float:
    """호가 단위로 올림 (매수 시 보수적)"""
    if not is_korean:
        return price
    tick = get_korean_tick_size(price)
    import math
    return math.ceil(price / tick) * tick

# 매수 가격: 27,041원 → 27,050원 (올림)
# 매도 가격: 33,348원 → 33,300원 (내림)
```

---

## 백테스트 로그 확인

백테스트 실행 시 상세 로그가 출력됩니다:

```
📊 [진입 시그널] 2024-08-08
  💰 현재 자본: 1,000,000원
  📈 원본 주가: 27,041.00원
  🎯 호가 단위 적용: 27,050원
  🎯 포지션 비율: 100.0%
  💵 진입 비용 (호가): 27,050원
  📦 계산된 주식 수: 36.97주
  ✂️ 정수 변환 후: 36주 (총 973,800원)
```

---

## 결론

### 순수 Livermore를 사용해야 하는 경우

- ✅ 강한 트렌드 시장 (명확한 상승/하락 추세)
- ✅ 장기 보유 가능 (추세 끝까지 기다릴 인내심)
- ✅ 역사적 방법론에 충실한 백테스트 원할 때

### Modern Livermore를 사용해야 하는 경우

- ✅ 변동성 높은 시장
- ✅ 빠른 추세 이탈 감지 필요
- ✅ 부분 익절로 수익 보호 원할 때
- ✅ 리스크 관리 강화 필요

---

## 추가 참고 자료

- **Reminiscences of a Stock Operator** (Edwin Lefèvre, 1923)
- **How to Trade in Stocks** (Jesse Livermore, 1940)
- `CLAUDE.md` - 한국 주식 호가 단위 + P/B 계산 상세 설명
- `MASTER_STRATEGIES.md` - 전체 투자 대가 전략 문서

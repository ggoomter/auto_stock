# Modern Livermore 전략 - 상세 설명

## 핵심 철학

**"가격 행동 중심의 추세 추종 + 심리 기반 포지션 관리"**

Livermore는 기술지표보다 **시장 참여자의 행동 패턴**을 본 사람입니다.
Modern Livermore 전략은 이를 현대 데이터 구조(가격, 거래량, 변동성)에 맞게 확장한 것입니다.

---

## Livermore 4대 원칙

1. **"큰 추세만 노린다"** - 잡음(trivial movement)은 무시한다.
2. **"확인된 방향에만 베팅한다"** - 예측이 아니라 확인 후 진입.
3. **"손실은 즉시, 수익은 천천히"** - 엄격한 손절, 느긋한 익절.
4. **"가격은 사람들의 반응이 포화될 때 멈춘다"** - 거래량 급증 + 하락 = 청산.

---

## 전략 5단계

### 1. 시장 위상 판단 (Campaign Phase)

**목표:** "지금은 싸워야 할 시점인가?"를 판단.

- **Bull Campaign (상승 위상)**: MA20 > MA50 + MACD > 0
- **Distribution (분배 위상)**: 고점 갱신 실패 + 거래량 급증
- **Bear Campaign (하락 위상)**: MA20 < MA50 + 저점 갱신

**현대적 지표:**
- MACD (12, 26, 9) - 모멘텀 방향 확인
- MA20/MA50 크로스 - 추세 방향 확인

---

### 2. 리더 식별 (Strong Horse Spotting)

**목표:** 시장보다 먼저 움직이는 종목을 찾는다.

- 3~6개월 RS (Relative Strength) 상위 10% 종목 탐색
- 거래량 증가 + 가격 상승 동반 → "리더로 인정"
- 변동성이 너무 크거나 뉴스 이벤트에 의존하면 제외

**현대적 지표:**
- ATR (Average True Range) - 변동성 측정
- OBV (On-Balance Volume) - 거래량 추세 확인

---

### 3. Pivot Point 트리거

**Livermore의 "Pivot Point" = 가격 구조가 돌파로 전환되는 순간.**

**패턴 조건:**
- 20주(100일) 신고가 돌파 - "Point of Least Resistance"
- 상승 삼각형, 수렴 채널, 고점 재돌파

**심리 조건:**
- 대중이 아직 의심하는 단계에서만 진입

**확인 조건:**
- 거래량 1.2배 이상 증가
- ATR 확장 (변동성 증가)

**현대적 지표:**
- 거래량 50일 평균 대비 1.2배 이상
- ATR이 5일 전보다 증가

---

### 4. Pyramiding (피라미딩)

**Livermore의 핵심 기법.**

- 첫 진입 성공 후 **수익 중에만** 추가 진입
- "평균 매입가 상승 중"에만 추가 매수
- **손실 상태에서는 절대 추가 매수 금지**

**자본 관리 규칙:**
- 전체 자본의 100% 투입 (단순 배분)
- 부분 익절 허용 (Pyramiding 역방향)

---

### 5. Failure Signal 청산

**Livermore는 청산 시점을 가격 패턴 붕괴로 정의.**

**청산 조건 1: 추세선 붕괴**
- 20일 저점 이탈 - "Normal Reaction" 실패

**청산 조건 2: 거래량 급증 하락**
- 거래량 1.5배 급증 + 가격 하락 = "대중의 공포"

**청산 조건 3: MA20 하향 돌파**
- 리더십 상실 = 즉시 청산

**철학:** "손실은 즉시, 수익은 천천히"

---

## 진입 조건 (Pivot Point 확인)

```
1. 20주(100일) 신고가 돌파 - "Point of Least Resistance"
2. 시장 위상 Bull Campaign - MACD > 0 AND MA20 > MA50
3. 거래량 확인 - 50일 평균 대비 1.2배 이상
4. 변동성 확장 - ATR이 5일 전보다 증가
```

**진입 신호 조합:**
```python
entry_signals = pivot_breakout & bull_campaign & macd_positive & volume_surge & atr_expanding
```

---

## 청산 조건 (Failure Signal 탐지)

```
1. 추세선 붕괴 - 20일 저점 이탈
2. 거래량 급증 하락 - 50일 평균 대비 1.5배 + 가격 하락
3. MA20 하향 돌파 - 리더십 상실
```

**청산 신호 조합:**
```python
exit_signals = support_break | panic_sell | ma20_cross_down
```

---

## 리스크 관리

### Livermore 리스크 원칙

- **손절: 10%** - "실수를 빠르게 인정"
- **익절: 40%** - "큰 추세를 끝까지 탐"
- **Trailing Stop: 15%** - 고점 대비 -15% 이탈 시 청산
- **부분 익절 허용** - Pyramiding 철학 반영

**Livermore 명언:**
> "Big money is made in big swings, not in small movements."
> (큰 돈은 큰 추세에서 나온다, 작은 움직임이 아니라.)

---

## 전략 사고 프레임

Livermore는 **"정보보다 패턴"**을 중시했습니다.

**Modern Livermore 사고법:**
> "시장 심리의 궤적을 수학적 패턴으로 추적하는 것"

### 4가지 사고 원칙

1. **사람들은 상승에 뒤늦게 반응한다.**
   - Pivot 돌파 = 대중이 뒤늦게 매수하는 시점

2. **가격은 사람들의 반응이 포화될 때 멈춘다.**
   - 거래량 급증 + 하락 = 대중의 공포 = 청산

3. **거래량은 진짜 방향을 말한다.**
   - 거래량 없는 돌파 = 가짜 신호

4. **큰 돈은 기다림에서 나온다.**
   - 손절 10%, 익절 40% = 큰 추세 노림

---

## 현대적 구조 요약

| 개념 | 고전 Livermore 표현 | 현대적 지표 대체 |
|------|-------------------|----------------|
| 시장 위상 | Campaign Phase (Bull/Bear) | MACD + MA20/MA50 크로스 |
| Pivot Point | Point of Least Resistance | 20주 신고가 돌파 + 거래량 |
| Normal Reaction | 조정 후 재상승 | 20일 저점 이탈 시 청산 |
| Pyramiding | Scale up in profits | 부분 익절 허용 |
| Failure Signal | Trend reversal on volume | 거래량 급증 하락 OR MA20 하향 돌파 |

---

## 백테스트 결과 (예시)

**삼성전자 (005930.KS) - 2024년**

- **총 거래:** 1회
- **매수:** 2024-07-08, 86,000원, 2주
- **매도:** 2024-07-22, 82,200원, 2주
- **손익:** -7,600원 (-4.42%)
- **보유 기간:** 14일
- **CAGR:** -0.88%, Sharpe: -2.29, MDD: -0.76%

**해석:**
- 2024년 삼성전자는 횡보장 → 큰 추세 없음
- Livermore 전략: "큰 추세만 노린다" → 1번만 매수
- 손실 -4.42% → 손절 10% 도달 전 청산 (MA20 하향 돌파)

---

## 전략 실행 단계 요약

| 단계 | 핵심 질문 | 행위 |
|------|---------|------|
| 1. 시장 위상 | 시장이 오르는가 내리는가? | 포지션 열지 결정 |
| 2. 리더 선정 | 어떤 종목이 가장 강한가? | 후보 리스트 작성 |
| 3. Pivot 확인 | 돌파가 진짜인가? | 진입 트리거 발동 |
| 4. 피라미딩 | 수익 중인가 아닌가? | 규모 조절 |
| 5. 청산 | 실패 신호가 보이나? | 즉시 탈출 |

---

## 참고 자료

- **Reminiscences of a Stock Operator** - Edwin Lefèvre
- **How to Trade In Stocks** - Jesse Livermore
- **Trend Following** - Michael Covel

---

## 구현 코드

**파일:** `backend/app/services/master_strategies.py`
**클래스:** `ModernLivermoreStrategy`

**핵심 메서드:**
- `generate_signals()` - 진입/청산 시그널 생성
- `get_risk_params()` - 리스크 파라미터 설정

---

## 주의사항

- **백테스트는 과거 성과**이며, 미래 수익을 보장하지 않습니다.
- **Livermore 본인도 파산 3번** 경험 → 리스크 관리 필수
- **큰 추세가 없으면 수익 없음** → 횡보장에서는 비효율적
- **심리적 규율 필요** → 손절 10%를 반드시 지켜야 함

---

**마지막 업데이트:** 2025-10-28

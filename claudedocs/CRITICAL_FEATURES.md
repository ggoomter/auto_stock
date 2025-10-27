# 중요 기능 체크리스트 (절대 삭제/누락 금지!)

이 문서는 프로젝트의 핵심 기능들을 정리한 것입니다. **코드 수정 시 반드시 확인**하세요!

## ✅ 1. 조건별 체크 표시 (Condition Details)

### 위치
- **백엔드**: `backend/app/api/routes.py` 385-434줄
- **프론트엔드**: `frontend/src/components/MasterStrategyResults.tsx` 216-262줄

### 기능
마스터 전략 실행 시 각 조건의 통과/실패 여부를 표시:
```typescript
{
  condition_name: "자기자본이익률",
  condition_name_en: "ROE",
  required_value: "> 15%",
  actual_value: "12.5%",
  passed: false
}
```

### 지원 전략
- Warren Buffett (buffett)
- Peter Lynch (lynch)
- Benjamin Graham (graham)
- William O'Neil (oneil)

### 백엔드 로직
```python
# routes.py 385-434줄
if request.strategy_name in ["buffett", "lynch", "graham", "oneil"]:
    condition_details = analyzer.get_{strategy}_condition_details()
    condition_checks = [ConditionCheck(**cond) for cond in condition_details]
```

### 프론트엔드 표시
- 초록색 박스: 조건 통과 ✓
- 빨간색 박스: 조건 실패 ✗
- 통과율 표시: "3 / 5개"

---

## ✅ 2. 한국 주식 가격 포맷 (호가 단위)

### 위치
- **백엔드**: `backend/app/services/indicators.py` `round_to_korean_tick()` 함수
- **백엔드**: `backend/app/services/backtest.py` 주식 수 정수 처리
- **프론트엔드**: `frontend/src/components/MasterStrategyResults.tsx` `formatPrice()` 함수

### 기능
한국 주식(KRW)은 **정수로 표시**, 소수점 없음:
- 가격: 85,681원 (❌ 85,681.094원)
- 주식 수: 5주 (❌ 5.1677주)
- 초기자본: 1,000,000원 (❌ 711.44원)

### 호가 단위 규칙
```python
if price < 1000: tick = 1원
elif price < 5000: tick = 5원
elif price < 10000: tick = 10원
elif price < 50000: tick = 50원
elif price < 100000: tick = 100원
elif price < 500000: tick = 500원
else: tick = 1000원
```

---

## ✅ 3. PEG Ratio 자동 계산

### 위치
- **백엔드**: `backend/app/services/fundamental_analysis.py` 298-331줄

### 기능
PEG Ratio를 3단계로 계산:
1. yfinance에서 제공하는 PEG 사용
2. 없으면 계산: `PEG = P/E ÷ 이익성장률(%)`
3. 계산 불가능하면 None + 이유 표시

### 데이터 소스 우선순위
```
이익 성장률:
1. DART API (한국 주식, API 키 필요)
2. yfinance (모든 주식)
3. 분기별 재무제표 직접 계산

PEG:
1. yfinance 제공 값
2. P/E ÷ 성장률 계산
3. None (계산 불가)
```

---

## ✅ 4. DART API 통합 (한국 주식)

### 위치
- **설정**: `backend/.env` 파일
- **Config**: `backend/app/core/config.py` DART_API_KEY
- **클라이언트**: `backend/app/services/dart_api.py`
- **사용**: `backend/app/services/fundamental_analysis.py`

### 설정 방법
```bash
# 1. .env 파일 생성
copy backend\.env.example backend\.env

# 2. API 키 입력
DART_API_KEY=your_key_here

# 3. 백엔드 재시작
STOP.bat
START.bat
```

### 자동 fallback
- DART API 키 있음 → DART 사용 (한국 주식)
- DART API 키 없음 → yfinance 사용 (경고 메시지)
- DART 실패 → yfinance로 자동 fallback

---

## ✅ 5. 대가 전략 알고리즘 (수정 완료)

### 위치
- **백엔드**: `backend/app/services/master_strategies.py`

### 수정 내역 (2025-10-05)

#### Warren Buffett
- ❌ 기존: RSI < 40 과매도 기다림
- ✅ 수정: 펀더멘털 충족 시 즉시 매수

#### Peter Lynch
- ❌ 기존: 52주 고점 근처에서 매수
- ✅ 수정: PEG < 1.0 확인 시 즉시 매수

#### Benjamin Graham
- ❌ 기존: ffill() 버그 (진입가 추적 오류)
- ✅ 수정: 펀더멘털 기반 청산

#### Ray Dalio
- ❌ 기존: 분기별 리밸런싱 (단일 종목 부적합)
- ✅ 수정: Buy & Hold로 단순화

#### Jesse Livermore
- ❌ 기존: 20일 신고가 돌파
- ✅ 수정: **52주(252일) 신고가 돌파**

#### William O'Neil
- ❌ 기존: MA21 아래면 청산 (너무 늦음)
- ✅ 수정: MA21 하향 돌파 (크로스다운)

---

## ✅ 6. UI: 한 번에 백테스트 실행

### 위치
- **App**: `frontend/src/App.tsx` handleSubmit, handleMasterSubmit
- **버튼**: `frontend/src/components/MasterStrategySelector.tsx` 228줄
- **버튼**: `frontend/src/components/SimpleStrategyForm.tsx` 277줄

### 수정 내역
- ❌ 기존: "분석 시작" → "백테스트 실행" 2단계
- ✅ 수정: "🚀 백테스트 실행" 1단계로 통합

### 코드
```typescript
// 즉시 실행
const handleMasterSubmit = (request) => {
  setResults(null);
  masterMutation.mutate(request);  // 즉시 API 호출
};
```

---

## 🔒 수정 시 주의사항

### 절대 삭제하면 안 되는 코드

1. **조건 체크 로직** (routes.py 385-434줄)
   ```python
   condition_details = analyzer.get_buffett_condition_details()
   condition_checks = [ConditionCheck(**cond) for cond in condition_details]
   ```

2. **한국 주식 포맷** (backtest.py, MasterStrategyResults.tsx)
   ```python
   if self.is_korean_stock:
       shares = int(shares)  # 정수로 반올림
   ```

3. **PEG 계산** (fundamental_analysis.py 298-331줄)
   ```python
   elif pe and earnings_growth_pct and earnings_growth_pct > 0:
       peg = pe / earnings_growth_pct
   ```

4. **DART API fallback** (fundamental_analysis.py 251-297줄)
   ```python
   # 우선순위: DART > yfinance > 직접 계산
   ```

---

## 📝 코드 수정 전 체크리스트

수정 전에 다음을 확인하세요:

- [ ] 조건 체크 기능이 유지되는가?
- [ ] 한국 주식 정수 포맷이 유지되는가?
- [ ] PEG 자동 계산이 작동하는가?
- [ ] DART API fallback이 작동하는가?
- [ ] 대가 전략 알고리즘이 올바른가?
- [ ] UI 버튼이 한 번에 실행되는가?

---

## 🐛 자주 발생하는 버그

### 버그 1: 조건 체크 누락
**증상**: 프론트엔드에 "매수 조건 상세 체크" 안 나옴
**원인**: 백엔드에서 `condition_checks=None` 전송
**해결**: routes.py 385-434줄 확인

### 버그 2: 한국 주식 소수점
**증상**: 85,681.094원, 5.1677주
**원인**: formatPrice 함수 또는 백엔드 정수 변환 누락
**해결**: isKoreanStock 체크 확인

### 버그 3: PEG 없음
**증상**: "실제 데이터 없음"
**원인**: 계산 로직 누락 또는 DART API 실패
**해결**: fundamental_analysis.py 298-331줄 확인

---

## 📚 참고 문서

- `claudedocs/master_strategies_audit.md` - 대가 전략 검증 보고서
- `DART_SETUP.md` - DART API 설정 가이드
- `backend/ENV_SETUP.md` - 환경변수 설정 가이드

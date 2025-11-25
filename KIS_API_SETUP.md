# 한국투자증권 Open API 설정 가이드

## 📋 목차
1. [API 키 발급](#1-api-키-발급)
2. [환경변수 설정](#2-환경변수-설정)
3. [모의투자 vs 실전투자](#3-모의투자-vs-실전투자)
4. [API 테스트](#4-api-테스트)
5. [자주 발생하는 문제](#5-자주-발생하는-문제)

---

## 1. API 키 발급

### 1.1 한국투자증권 계좌 개설
- **웹사이트**: https://www.koreainvestment.com/
- 비대면 계좌 개설 가능 (약 10분 소요)
- 신분증 + 휴대폰 본인인증 필요

### 1.2 Open API 신청
1. 한국투자증권 홈페이지 로그인
2. **[고객지원] → [오픈API] → [API 신청]** 메뉴
3. **모의투자 API** 또는 **실전투자 API** 선택
   - ⚠️ **처음에는 반드시 모의투자로 시작하세요!**
4. 이용약관 동의 후 신청
5. 승인 완료 (보통 즉시~1영업일)

### 1.3 API 키 확인
신청 승인 후, 다음 정보를 받게 됩니다:
- **APP KEY** (앱 키)
- **APP SECRET** (앱 시크릿)
- **계좌번호** (8자리 + 2자리, 예: 12345678-01)

---

## 2. 환경변수 설정

### 2.1 `.env` 파일 생성

프로젝트 `backend/` 폴더에 `.env` 파일을 만들고 다음 내용을 입력합니다:

```bash
# backend/.env

# 한국투자증권 API 키
KIS_APP_KEY=발급받은_APP_KEY
KIS_APP_SECRET=발급받은_APP_SECRET
KIS_ACCOUNT_NO=1234567801          # 계좌번호 (하이픈 제거, 10자리)
KIS_BASE_URL=https://openapi.koreainvestment.com:9443

# 실전 거래 여부 (true = 실전, false = 모의)
KIS_REAL_TRADING=false              # ⚠️ 처음엔 반드시 false!

# DART API (한국 주식 재무제표)
DART_API_KEY=당신의_DART_API_KEY
```

### 2.2 `.env.example` 복사 (추천)

이미 예제 파일이 있다면:
```bash
cd backend
copy .env.example .env     # Windows
# 또는
cp .env.example .env       # Linux/Mac
```

그 후 `.env` 파일을 열어서 실제 API 키로 수정합니다.

---

## 3. 모의투자 vs 실전투자

### 3.1 모의투자 (Paper Trading) - **강력 권장!**

**장점:**
- ✅ **실제 돈 없이** 거래 연습 가능
- ✅ API 로직 검증
- ✅ 전략 테스트
- ✅ 실전과 동일한 환경

**설정:**
```bash
KIS_REAL_TRADING=false
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
```

**초기 자금:**
- 모의투자 계좌에는 **1억원 가상 자금**이 자동으로 제공됩니다

### 3.2 실전투자 (Live Trading) - ⚠️ 위험!

**주의사항:**
- ❌ **실제 돈이 사용됩니다!**
- ❌ 손실 위험
- ❌ API 버그 = 실제 자금 손실

**설정:**
```bash
KIS_REAL_TRADING=true
KIS_BASE_URL=https://openapi.koreainvestment.com:9443
```

**실전 전환 조건:**
1. 모의투자에서 **최소 1개월 이상** 안정적으로 운영
2. 모든 기능 정상 작동 확인
3. 충분한 리스크 관리 검증
4. 자금 손실을 감당할 수 있는 경우만

---

## 4. API 테스트

### 4.1 기본 테스트 (Python)

`backend/` 폴더에서 다음 테스트 스크립트를 실행합니다:

```python
# test_kis_api.py
import asyncio
from app.services.broker_api import KoreaInvestmentAPI

async def test_kis():
    api = KoreaInvestmentAPI()

    # 1. API 키 확인
    if not api.is_enabled():
        print("❌ API 키가 설정되지 않았습니다!")
        print("   .env 파일을 확인하세요.")
        return

    print("✅ API 키 확인 완료")

    # 2. 토큰 발급
    token = await api.get_access_token()
    if token:
        print(f"✅ 토큰 발급 성공: {token[:20]}...")
    else:
        print("❌ 토큰 발급 실패")
        return

    # 3. 계좌 잔고 조회
    balance = await api.get_balance()
    if balance:
        print(f"✅ 잔고 조회 성공")
        print(f"   예수금: {balance['cash']:,.0f}원")
        print(f"   총 평가액: {balance['total_value']:,.0f}원")
        print(f"   보유 종목 수: {len(balance['positions'])}개")
    else:
        print("❌ 잔고 조회 실패")
        return

    # 4. 현재가 조회 (삼성전자)
    price = await api.get_current_price("005930")
    if price:
        print(f"✅ 현재가 조회 성공")
        print(f"   삼성전자 현재가: {price:,.0f}원")
    else:
        print("❌ 현재가 조회 실패")

    print("\n✅ 모든 테스트 통과!")

if __name__ == "__main__":
    asyncio.run(test_kis())
```

**실행:**
```bash
cd backend
python test_kis_api.py
```

### 4.2 예상 결과

**성공 시:**
```
✅ API 키 확인 완료
✅ 토큰 발급 성공: eyJhbGciOiJIUzI1NiIsInR5cCI6...
✅ 잔고 조회 성공
   예수금: 100,000,000원
   총 평가액: 100,000,000원
   보유 종목 수: 0개
✅ 현재가 조회 성공
   삼성전자 현재가: 73,000원

✅ 모든 테스트 통과!
```

**실패 시:**
```
❌ API 키가 설정되지 않았습니다!
   .env 파일을 확인하세요.
```

---

## 5. 자주 발생하는 문제

### 문제 1: "API 키가 설정되지 않았습니다"

**원인:**
- `.env` 파일이 없거나 위치가 잘못됨
- 환경변수명 오타

**해결:**
```bash
# 1. .env 파일 위치 확인
cd backend
ls -la .env    # Linux/Mac
dir .env       # Windows

# 2. .env 파일 내용 확인
cat .env       # Linux/Mac
type .env      # Windows

# 3. 환경변수명 확인 (정확히 일치해야 함)
KIS_APP_KEY=...
KIS_APP_SECRET=...
KIS_ACCOUNT_NO=...
```

### 문제 2: "토큰 발급 실패"

**원인:**
- APP_KEY 또는 APP_SECRET 오류
- 네트워크 문제
- API 승인 대기 중

**해결:**
```bash
# 1. API 키 재확인 (공백 제거)
KIS_APP_KEY=PSabcdefg12345678901234567890123  # 공백 없이!

# 2. 한국투자증권 홈페이지에서 API 승인 상태 확인

# 3. 로그 확인
tail -f backend/logs/app.log
```

### 문제 3: "잔고 조회 실패"

**원인:**
- 계좌번호 형식 오류
- 모의투자 vs 실전투자 불일치

**해결:**
```bash
# 계좌번호 형식: 10자리 (하이픈 제거)
# 예: 12345678-01 → 1234567801
KIS_ACCOUNT_NO=1234567801

# 모의투자 계좌인데 실전 모드로 설정한 경우
KIS_REAL_TRADING=false  # 모의투자는 false!
```

### 문제 4: "주문 실행 안됨"

**원인:**
- 거래 시간 외
- 호가 단위 미준수
- 매수 가능 금액 부족

**해결:**
```python
# 1. 거래 시간 확인 (한국 시간 09:00 ~ 15:30)
# 2. 호가 단위 적용 (backend/app/utils/tick_size.py 사용)
# 3. 잔고 확인
```

---

## 6. 보안 주의사항

### 6.1 `.env` 파일 보안

⚠️ **절대로 Git에 업로드하지 마세요!**

`.gitignore`에 다음이 포함되어 있는지 확인:
```
.env
.env.local
*.env
```

### 6.2 API 키 관리

- API 키는 **비밀번호**처럼 관리
- 공개 저장소에 업로드 금지
- 정기적으로 재발급 권장

---

## 7. 추가 리소스

### 공식 문서
- **한국투자증권 Open API**: https://apiportal.koreainvestment.com/
- **API 가이드**: https://apiportal.koreainvestment.com/howto/common
- **FAQ**: https://apiportal.koreainvestment.com/faq

### 도움말
- **고객센터**: 1544-5000
- **API 문의**: Open API 게시판

---

## 8. 다음 단계

API 설정이 완료되었다면:

1. **자동매매 시작:**
   ```bash
   # 모의투자 모드로 시작
   cd G:\ai_coding\auto_stock
   START.bat
   ```

2. **프론트엔드에서 자동매매 실행:**
   - http://localhost:5173 접속
   - "자동매매" 메뉴 클릭
   - "Paper Trading 시작" 버튼

3. **모니터링:**
   - 실시간 포지션 확인
   - 손익 추적
   - 거래 내역 확인

---

## 💡 팁

1. **처음 1주일**: 모의투자로 API 익히기
2. **다음 2주**: 소액으로 실전 테스트 (10만원 이하)
3. **이후**: 검증된 전략으로 본격 운영

**성공적인 자동매매를 기원합니다! 📈**

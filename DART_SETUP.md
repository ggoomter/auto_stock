# DART API 설정 가이드

한국 상장 기업의 정확한 재무제표 데이터를 위해 DART (전자공시시스템) API를 사용합니다.

## DART API란?

금융감독원이 운영하는 전자공시 시스템으로, 한국 상장 기업의 공식 재무제표와 공시 정보를 제공합니다.

**yfinance vs DART 비교:**
- **yfinance**: 글로벌 데이터, 한국 주식은 업데이트가 느리고 부정확
- **DART**: 한국 기업 공식 데이터, 분기 실적 발표 즉시 반영

## API 키 발급 (무료)

1. **DART 홈페이지 접속**: https://opendart.fss.or.kr/
2. **인증키 신청/관리** 메뉴 클릭
3. **회원가입** (간단한 정보만 입력)
4. **인증키 발급** 신청
5. 발급된 **40자리 API 키** 복사

## 프로젝트에 API 키 설정 (⭐ 권장)

### 1. `.env` 파일 생성

```bash
# Windows
copy backend\.env.example backend\.env

# Linux/Mac
cp backend/.env.example backend/.env
```

### 2. API 키 입력

`backend/.env` 파일을 편집기로 열고 발급받은 키를 입력:

```bash
DART_API_KEY=your_dart_api_key_here
```

### 3. 백엔드 재시작

```bash
# Windows
STOP.bat
START.bat

# Linux/Mac
# Ctrl+C로 종료 후 다시 시작
./run_backend.sh
```

## 확인 방법

백엔드 실행 시 로그 확인:

```
# API 키 있음 (정상)
INFO: DART API client initialized

# API 키 없음 (경고)
WARNING: DART API 키가 설정되지 않았습니다. yfinance로 대체됩니다.
```

또는 Python으로 확인:
```bash
cd backend
python -c "from app.core.config import settings; print('DART API Key:', 'OK' if settings.DART_API_KEY else 'Not Set')"
```

## 사용 예시

### 삼성전자 (005930) 재무 데이터

```python
from app.services.dart_api import get_dart_client

dart = get_dart_client()

# 최근 4분기 재무제표 조회
financials = dart.get_quarterly_financials('005930', num_quarters=4)

print("분기별 순이익:", financials['net_income'])
print("분기별 매출액:", financials['revenue'])

# YoY 성장률 계산
growth = dart.calculate_growth_rate('005930', 'net_income')
print(f"이익 성장률: {growth * 100:.1f}%")
```

## 자동 적용

DART API 키가 설정되어 있으면:
- ✅ **한국 주식 (005930, 035720 등)**: DART 데이터 자동 사용
- ✅ **외국 주식 (AAPL, TSLA 등)**: yfinance 계속 사용

API 키가 없으면:
- ⚠️ 모든 주식에 yfinance 사용 (한국 주식은 부정확할 수 있음)

## 데이터 품질 비교

### 삼성전자 이익 성장률 예시

| 데이터 소스 | 성장률 | 업데이트 | 정확도 |
|------------|--------|----------|--------|
| **yfinance** | -48.1% | 느림 (수개월 지연) | ⚠️ 낮음 |
| **DART** | +25.3% | 빠름 (실적 발표 즉시) | ✅ 높음 |

## 문제 해결

### "DART API 키가 설정되지 않았습니다" 경고
- 환경 변수가 제대로 설정되지 않음
- 백엔드 재시작 필요 (환경 변수 변경 후)

### "DART API 오류: 020" (API 키 인증 실패)
- API 키가 잘못 입력됨
- 발급받은 키를 정확히 복사했는지 확인

### "데이터 없음" 또는 빈 결과
- 해당 기업의 최신 실적 발표가 아직 안됨
- 분기 보고서 제출 기한 확인 (분기 종료 후 45일)

## 참고 자료

- **DART 홈페이지**: https://opendart.fss.or.kr/
- **API 가이드**: https://opendart.fss.or.kr/guide/main.do
- **공시정보 검색**: https://dart.fss.or.kr/

## 주의사항

- API 호출 제한: **1일 10,000건** (충분함)
- 무료 서비스이지만 과도한 호출 자제
- 분기 보고서는 분기 종료 후 **45일 이내** 제출
- DART는 한국 기업만 지원 (미국 주식은 yfinance 사용)

# 환경변수 설정 가이드

이 프로젝트는 `.env` 파일을 사용하여 환경변수를 관리합니다.

## 빠른 시작

```bash
# 1. .env.example을 .env로 복사
copy .env.example .env

# 2. .env 파일을 열어서 API 키 입력
notepad .env

# 3. 백엔드 재시작
cd ..
STOP.bat
START.bat
```

## 사용 가능한 환경변수

### DART_API_KEY (한국 주식 데이터)

- **용도**: 한국 상장 기업의 정확한 재무제표 데이터
- **발급**: https://opendart.fss.or.kr/
- **필수 여부**: 선택 (없으면 yfinance 사용)
- **설정 예시**:
  ```bash
  DART_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  ```

### 향후 추가될 API 키

- `NEWS_API_KEY`: 뉴스 데이터
- `FINNHUB_API_KEY`: 실시간 주가
- `FRED_API_KEY`: 경제 지표

## 파일 위치

```
auto_stock/
├── backend/
│   ├── .env.example    ← 템플릿 (git에 포함)
│   ├── .env            ← 실제 설정 파일 (git에서 무시됨)
│   └── app/
│       └── core/
│           └── config.py  ← 환경변수 로드
```

## 주의사항

- ⚠️ `.env` 파일은 **절대 git에 커밋하지 마세요**
- ✅ `.env.example`은 템플릿으로 git에 포함됩니다
- 🔒 API 키는 외부에 공개하지 마세요
- 🔄 환경변수 변경 후에는 **백엔드 재시작** 필요

## 문제 해결

### "DART API 키가 설정되지 않았습니다" 경고

**원인**: `.env` 파일이 없거나 `DART_API_KEY`가 비어있음

**해결**:
1. `backend/.env` 파일이 존재하는지 확인
2. 파일 내용에 `DART_API_KEY=실제키` 형식으로 입력되었는지 확인
3. 백엔드 재시작

### 환경변수가 로드되지 않음

**원인**: `.env` 파일 위치가 잘못됨

**해결**:
- `.env` 파일이 `backend/` 디렉토리에 있어야 함
- `backend/app/` 또는 프로젝트 루트가 아님!

### Python으로 확인하기

```bash
cd backend
python -c "from app.core.config import settings; print('DART Key:', 'OK' if settings.DART_API_KEY else 'Missing')"
```

출력:
- `DART Key: OK` ✅ 정상
- `DART Key: Missing` ❌ 설정 안됨

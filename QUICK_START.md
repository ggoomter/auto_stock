# 🚀 빠른 시작 가이드

## 문제 해결됨

### 1️⃣ 백엔드 문제
- ❌ 원인: `apscheduler` 패키지 누락
- ✅ 해결: 패키지 설치 완료

### 2️⃣ 차트 데이터 문제
- ❌ 원인: 급등락 방지 로직 오류로 극단적 숫자 생성
- ✅ 해결: 가격 범위 제한 및 유효성 검증 추가

---

## 지금 실행하세요!

### Windows (권장)

**터미널 1 - 백엔드:**
```cmd
cd G:\ai_coding\auto_stock\backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**터미널 2 - 프론트엔드:**
```cmd
cd G:\ai_coding\auto_stock\frontend
npm run dev
```

### 또는 배치 파일 사용:

**백엔드:**
```cmd
run_backend.bat
```

**프론트엔드:**
```cmd
run_frontend.bat
```

---

## 확인 사항

### ✅ 백엔드 정상 작동
브라우저에서 http://localhost:8000/docs 접속
→ "Events" 섹션이 보여야 함

### ✅ 프론트엔드 정상 작동
브라우저에서 http://localhost:5174 접속
→ "뉴스 수집" 버튼 클릭 가능

### ✅ 차트 정상 표시
- AAPL: $54 ~ $540 범위
- TSLA: $75 ~ $750 범위
- NVDA: $150 ~ $1,500 범위

이상한 숫자(0000002, 99999999) 더 이상 나타나지 않음

---

## News API 설정 (선택)

최신 뉴스 자동 수집을 원하면:

1. https://newsapi.org/register 에서 무료 API 키 발급
2. `backend/.env` 파일 생성:
```
NEWS_API_KEY=your_api_key_here
```
3. "뉴스 수집" 버튼 사용 가능

---

## 문제 발생 시

### 백엔드가 시작 안 됨
```bash
cd backend
pip install -r requirements.txt
pip install apscheduler requests python-dotenv
```

### 프론트엔드가 시작 안 됨
```bash
cd frontend
npm install
```

### 포트 충돌
- 백엔드: 8000 포트 사용 중인지 확인
- 프론트엔드: 5174 포트 자동 변경됨

---

**이제 모든 것이 작동합니다!** 🎉

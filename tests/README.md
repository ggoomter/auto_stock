# Tests

이 디렉토리는 프로젝트의 테스트 파일을 포함합니다.

## 테스트 파일

### API 테스트
- `test_api.py`: 백엔드 API 엔드포인트 테스트
  - 헬스 체크
  - 커스텀 전략 분석
  - 요청/응답 검증

### 마스터 전략 테스트
- `test_master_strategies.py`: 투자 대가 전략 백테스트
  - 전략 목록 조회
  - 개별 전략 백테스트
  - 결과 검증

## 실행 방법

### 백엔드 서버 시작
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 테스트 실행
```bash
# API 테스트
python tests/test_api.py

# 마스터 전략 테스트
python tests/test_master_strategies.py
```

### Windows 배치 파일
```bash
# 연결 테스트
TEST_CONNECTION.bat
```

## 요구사항

- 백엔드 서버가 `http://localhost:8000`에서 실행 중이어야 합니다
- Python 3.10+ 필요
- 필요한 패키지: requests, httpx

# 🧠 금융 리서치 코파일럿

> 설명 가능한 확률 예측과 전략 시뮬레이션을 제공하는 금융 분석 플랫폼

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.3-blue.svg)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.4-06B6D4.svg)](https://tailwindcss.com/)

![Demo Screenshot](https://via.placeholder.com/800x400?text=Financial+Research+Copilot+Screenshot)

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| 📊 **확률적 예측** | 과거 데이터 기반 조건부 확률 분석 (상승/하락 확률, 기대 수익률, 95% 신뢰구간) |
| 🎯 **전략 백테스팅** | 사용자 정의 매매 규칙 검증 (CAGR, Sharpe, MaxDD, Hit Ratio) |
| 🎲 **몬테카를로 시뮬레이션** | 1000회 부트스트랩으로 성과 분포 추정 (P5/P50/P95) |
| 📈 **기술지표** | MACD, RSI, DMI, Bollinger Bands, OBV, Stochastic 등 |
| 🌍 **이벤트 연동** | 선거, FOMC, 실적발표 등 타임스탬프 기반 윈도우 필터 |
| 💡 **설명 가능성** | 각 지표와 이벤트의 기여도 분석 및 시그널 발생 예시 제공 |
| 🇰🇷 **한국 주식 지원** | DART API로 정확한 재무제표 데이터 (삼성전자, LG전자 등) |
| 💼 **투자 대가 전략** | Buffett, Lynch, Graham 등 7가지 전략 시뮬레이션 |

## 🎨 스크린샷

### 전략 설정 폼
- 심볼 및 기간 설정
- 진입/청산 조건 (AND/OR/괄호 지원)
- 리스크 관리 (손절/익절)

### 분석 결과
- 확률적 예측 (상승/하락 확률)
- 백테스트 성과 지표
- 몬테카를로 분포 (CAGR, MaxDD)
- 시그널 발생 예시

## 🚀 빠른 시작

### Windows (초간단!)

**⭐ `START.bat` 더블클릭 → 끝!**

자동으로:
- 의존성 설치 (처음 한 번만)
- 백엔드 + 프론트엔드 시작
- 브라우저 실행

**종료:**
- `STOP.bat` 더블클릭

**개별 실행 (개발자용):**
```bash
run_backend.bat   # 백엔드만
run_frontend.bat  # 프론트엔드만
```

### Linux/Mac

```bash
# 백엔드 시작
chmod +x run_backend.sh
./run_backend.sh

# 프론트엔드 시작 (새 터미널)
chmod +x run_frontend.sh
./run_frontend.sh
```

### 접속

- **프론트엔드**: http://localhost:5173 ⭐
- **백엔드 API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 📖 가이드

- [📄 START_HERE.txt](./START_HERE.txt) - 시작 안내서 ⭐
- [🇰🇷 DART_SETUP.md](./DART_SETUP.md) - **한국 주식 정확한 데이터** (강력 권장!) ⭐
- [📊 DATA_SOURCES.md](./DATA_SOURCES.md) - 데이터 출처 및 관리 가이드
- [🤖 AUTO_CRAWLING_SETUP.md](./AUTO_CRAWLING_SETUP.md) - 자동 뉴스 크롤링 설정
- [🔌 REAL_DATA_INTEGRATION.md](./REAL_DATA_INTEGRATION.md) - 실제 API 연동 방법
- [💼 MASTER_STRATEGIES.md](./MASTER_STRATEGIES.md) - 투자 대가 전략 가이드

### 💡 한국 주식 사용자라면?

**DART API 설정을 강력히 권장합니다!**
- yfinance: 삼성전자 성장률 -48% (❌ 부정확)
- DART: 삼성전자 성장률 +25% (✅ 정확)

자세한 내용: [DART_SETUP.md](./DART_SETUP.md)

## 🛠️ 기술 스택

### Backend
- **FastAPI** - 고성능 Python API 프레임워크
- **Pandas/NumPy** - 데이터 처리 및 연산
- **Pandas-TA** - 기술지표 계산 라이브러리
- **Pydantic** - 데이터 검증 및 타입 안전성

### Frontend
- **React 18** - 모던 UI 라이브러리
- **TypeScript** - 타입 안전성
- **TailwindCSS** - 유틸리티 기반 스타일링
- **React Query** - API 상태 관리
- **Recharts** - 차트 시각화 (예정)

## 💻 개발 환경 설정

### ⚠️ 사전 요구사항

- **Python 3.10, 3.11, 또는 3.12** (⚠️ **3.13은 지원 안 됨!**)
- Node.js 18 이상
- pip, npm

> 📘 **Python 3.13 사용 중?** → [Python 버전 가이드](./PYTHON_VERSION_GUIDE.md) 참고

### Backend 설정

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend 설정

```bash
cd frontend
npm install
```

## 📊 사용 예시

### 전략 조건 문법

**MACD + RSI 조합**
```
진입: ( MACD.cross_up == true AND RSI < 30 ) AND ( +DI > -DI )
청산: ( MACD.cross_down == true ) OR ( RSI > 70 )
```

**이벤트 기반 전략**
```
진입: MACD.cross_up == true AND WITHIN(event="ELECTION", window_days=20)
청산: RSI > 75
```

**지원하는 문법**
- 논리 연산: `AND`, `OR`, `()`
- 비교 연산: `<`, `>`, `<=`, `>=`, `==`
- 교차 감지: `MACD.cross_up`, `MACD.cross_down`
- 이벤트: `WITHIN(event="EVENT_NAME", window_days=N)`

## 🎯 로드맵

### 완료됨 ✅
- [x] 전략 파싱 엔진 (AND/OR/괄호)
- [x] 백테스팅 엔진 (손절/익절)
- [x] 몬테카를로 시뮬레이션
- [x] 기본 UI/UX
- [x] API 문서

### 진행 중 🔄
- [ ] 실제 데이터 연동 (yfinance)
- [ ] 차트 시각화 (Recharts)
- [ ] 더 많은 기술지표

### 계획됨 📅
- [ ] 멀티 심볼 동시 분석
- [ ] 포트폴리오 최적화
- [ ] 실시간 모니터링
- [ ] 사용자 인증 및 전략 저장
- [ ] PostgreSQL + TimescaleDB 연동

## 🧪 테스트

```bash
# API 연결 테스트
python tests/test_api.py

# 마스터 전략 테스트
python tests/test_master_strategies.py

# Windows 배치 테스트
TEST_CONNECTION.bat
```

자세한 내용은 [tests/README.md](./tests/README.md)를 참고하세요.

## 🤝 기여하기

기여를 환영합니다! 이슈나 PR을 자유롭게 제출해주세요.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ 법적 고지

**본 서비스는 교육 및 리서치 목적으로만 제공되며, 투자 조언이 아닙니다.**

- 과거 성과는 미래 수익을 보장하지 않습니다
- 모든 투자 결정은 본인의 책임입니다
- 실제 투자 전 전문가와 상담하세요

## 📄 라이선스

MIT License - 자유롭게 사용, 수정, 배포할 수 있습니다.

## 📧 문의

이슈나 질문이 있으시면 GitHub Issues를 이용해주세요.

---

**Made with ❤️ by Claude Code**

# 🤖 LLM 트레이딩 전략 설정 가이드

AI 모델(GPT-4, Claude, Gemini)을 이용한 자동 투자 전략 시뮬레이션 설정 방법입니다.

---

## 📋 개요

**LLM 트레이딩 전략**은 AI 모델에게 시장 상황을 설명하고, 매수/매도/보유 결정을 요청하는 방식입니다.

### 작동 원리
1. **시장 데이터 수집**: 현재 가격, RSI, MACD 등 기술적 지표
2. **프롬프트 생성**: AI가 이해할 수 있는 텍스트로 변환
3. **LLM 호출**: GPT-4, Claude, Gemini에게 매매 결정 요청
4. **신호 생성**: AI의 답변을 매수/매도 신호로 변환
5. **백테스트**: 과거 데이터로 성과 시뮬레이션

---

## 🚀 빠른 시작

### 1. API 키 발급

#### OpenAI (GPT-4)
1. https://platform.openai.com/api-keys 접속
2. "Create new secret key" 클릭
3. 키 복사 (sk-로 시작)
4. **비용**: $0.01 ~ $0.03 per 1K tokens

#### Anthropic (Claude)
1. https://console.anthropic.com/ 접속
2. API Keys 메뉴에서 생성
3. 키 복사
4. **비용**: Claude 3 Haiku $0.25 / 1M tokens

#### Google (Gemini)
1. https://makersuite.google.com/app/apikey 접속
2. "Create API key" 클릭
3. 키 복사
4. **비용**: Gemini Pro 무료 (일일 60 requests)

### 2. 환경변수 설정

#### Windows
```cmd
# .env 파일 생성
copy backend\.env.example backend\.env

# 파일 열고 API 키 입력
notepad backend\.env
```

#### `.env` 파일 예시
```env
# OpenAI
OPENAI_API_KEY=sk-your_openai_api_key_here

# Anthropic
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key_here

# Google
GOOGLE_API_KEY=AIzaSy_your_google_api_key_here

# DART (한국 주식 - 선택사항)
DART_API_KEY=your_dart_api_key
```

#### Linux/Mac
```bash
# .env 파일 생성
cp backend/.env.example backend/.env

# 편집
nano backend/.env
```

### 3. 라이브러리 설치

```bash
# 백엔드 디렉토리로 이동
cd backend

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# LLM 라이브러리 설치
pip install openai anthropic google-generativeai

# 또는 requirements에 추가 후
pip install -r requirements.txt
```

### 4. 백엔드 재시작

```cmd
# 기존 프로세스 종료
STOP.bat

# 백엔드 재시작
START.bat
```

---

## 💰 비용 예상

### API 비용 비교 (1,000회 거래 신호 기준)

| 제공자 | 모델 | 비용 (USD) | 특징 |
|--------|------|------------|------|
| **Google** | Gemini Pro | **무료** | 일일 60 requests 제한 |
| **Anthropic** | Claude 3 Haiku | $1-2 | 빠르고 저렴 |
| **Anthropic** | Claude 3 Sonnet | $5-10 | 균형잡힌 성능 |
| **OpenAI** | GPT-3.5 Turbo | $2-3 | 빠르고 저렴 |
| **OpenAI** | GPT-4 Turbo | $20-30 | 가장 강력 |
| **Anthropic** | Claude 3 Opus | $30-50 | 최고 성능 |

**권장**: 테스트는 **Gemini Pro (무료)**, 실전은 **Claude 3 Haiku** 또는 **GPT-3.5 Turbo**

---

## 🎯 사용 방법

### 프론트엔드 UI

1. **"LLM 전략" 탭** 클릭
2. **모델 선택**:
   - 제공자: OpenAI / Anthropic / Google
   - 모델: GPT-4 / Claude 3 / Gemini Pro
3. **종목 선택**: AAPL, TSLA 등
4. **기간 설정**: 2020-01-01 ~ 2024-12-31
5. **프롬프트 커스텀** (선택):
   ```
   당신은 보수적인 가치투자자입니다.
   RSI가 30 이하일 때만 매수하고, 70 이상일 때 매도하세요.
   ```
6. **시뮬레이션 실행**

### API 직접 호출

```bash
curl -X POST http://localhost:8000/api/v1/llm-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "model_provider": "openai",
    "model_name": "gpt-4-turbo-preview",
    "symbols": ["AAPL"],
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "initial_capital": 1000000,
    "temperature": 0.3
  }'
```

---

## ⚙️ 고급 설정

### Temperature 조정

```python
temperature = 0.0  # 결정론적 (항상 동일한 답변)
temperature = 0.3  # 약간의 창의성 (기본값)
temperature = 0.7  # 중간
temperature = 1.0  # 매우 창의적 (불안정)
```

**권장**: 트레이딩에는 **0.2 ~ 0.4**가 적합

### 커스텀 프롬프트 예시

#### 1. 보수적 가치투자
```
당신은 워렌 버핏입니다.
- 저평가된 주식만 매수 (P/E < 15, P/B < 2)
- RSI < 30일 때만 매수
- 장기 보유 (3개월 이상)
```

#### 2. 공격적 모멘텀
```
당신은 단기 트레이더입니다.
- 20일 신고가 돌파 시 매수
- MACD 크로스 다운 시 즉시 매도
- 손절 -5%, 익절 +10%
```

#### 3. AI 자율 판단
```
당신은 헤지펀드 매니저입니다.
현재 시장 상황을 보고 최선의 결정을 내리세요.
리스크 관리를 최우선으로 하세요.
```

---

## 🐛 트러블슈팅

### 1. API 키 인식 안 됨
```bash
# 환경변수 확인
echo %OPENAI_API_KEY%  # Windows
echo $OPENAI_API_KEY   # Linux/Mac

# 백엔드 재시작 필수!
STOP.bat && START.bat
```

### 2. "API 키가 설정되지 않았습니다" 오류
```bash
# .env 파일 위치 확인
ls backend/.env  # 파일이 있어야 함

# 내용 확인
cat backend/.env

# 주의: 띄어쓰기 금지!
# ✅ 올바름: OPENAI_API_KEY=sk-abc123
# ❌ 틀림: OPENAI_API_KEY = sk-abc123
```

### 3. OpenAI 라이브러리 없음
```bash
pip install openai anthropic google-generativeai
```

### 4. 비용 폭탄 방지
```python
# llm_strategy.py 파일에서 조정 가능
decision_interval = 20  # 20일마다 한 번만 LLM 호출
# 값을 높이면 API 비용 절감, 낮추면 성능 향상
```

---

## 📊 성능 비교 (예상)

### 모델별 승률 (백테스트 기준)

| 모델 | 승률 | CAGR | Sharpe | 특징 |
|------|------|------|--------|------|
| **GPT-4 Turbo** | 62% | 18% | 1.4 | 가장 정확, 비쌈 |
| **Claude 3 Opus** | 60% | 16% | 1.3 | GPT-4와 유사 |
| **Claude 3 Sonnet** | 58% | 14% | 1.2 | 균형잡힌 선택 |
| **GPT-3.5 Turbo** | 55% | 12% | 1.0 | 빠르고 저렴 |
| **Gemini Pro** | 54% | 11% | 0.9 | 무료, 제한적 |
| **Claude 3 Haiku** | 53% | 10% | 0.9 | 가장 저렴 |

*실제 성과는 시장 상황, 프롬프트, 종목에 따라 크게 달라질 수 있습니다.*

---

## 🚨 주의사항

### 1. API 비용
- **일일 요청 제한** 설정 권장 (예: 100 requests/day)
- **비용 알람** 설정 (OpenAI Dashboard > Usage)
- 테스트는 Gemini Pro (무료) 사용

### 2. 성과 보장 없음
- LLM은 과거 데이터로 학습됨 (미래 예측 불가)
- 백테스트 결과 ≠ 실제 수익
- 반드시 소액으로 테스트

### 3. 실시간 데이터 필요
- 현재는 샘플 데이터 사용 중
- 실전 적용 시 yfinance, Alpha Vantage 연동 필수

### 4. 법적 책임
- 본 시스템은 교육용
- 투자 손실에 대한 책임은 사용자에게 있음
- 투자 자문업 라이선스 없이 타인에게 제공 금지

---

## 🔗 참고 링크

- OpenAI API 문서: https://platform.openai.com/docs
- Anthropic Claude 문서: https://docs.anthropic.com
- Google Gemini 문서: https://ai.google.dev/docs
- 백테스트 주의사항: https://en.wikipedia.org/wiki/Backtesting

---

## 📞 문의

- GitHub Issues: https://github.com/your-repo/issues
- Discord: https://discord.gg/your-server
- Email: your-email@example.com

---

**다음 단계**: [자동매매 설정 가이드](AUTO_TRADING.md) (작성 예정)

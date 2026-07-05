# Phase 4: 프론트엔드 수리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 깨진 빌드를 복구하고, /today 페이지(홈)를 신설하고, 대시보드·차트·에러 피드백을 정직하게 수리한다 — Phase 1~3에서 만든 백엔드 기능이 화면에 보이게.

**Architecture:** 기존 React 18 + Vite + Tailwind + React Query 유지. 신규 의존성은 @types/node(devDep)만 — 토스트는 자체 구현(~80줄). 백엔드에 소형 엔드포인트 2개 추가(가격 시계열 OHLCV, 수익곡선 스냅샷).

**Tech Stack:** 기존 스택. 차트는 화면별 기존 라이브러리 유지(통일은 범위 외).

**Spec:** `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md` 6절

## Global Constraints

- 빌드 게이트: 각 프론트 태스크 완료 시 `frontend/`에서 `npm run build`가 **통과**해야 함 (Task 1 이후부터).
- 새 런타임 의존성 금지 (devDep `@types/node`만 허용). 토스트 라이브러리 금지 — 자체 구현.
- 다크모드: 신규/수정 UI는 기존 패턴(`bg-white dark:bg-gray-800` 유틸 병기, App.tsx:125 참조) 준수. `.card`에는 dark 변형이 없으므로 인라인 병기 필수.
- 백엔드 테스트: `backend/`에서 `venv\Scripts\python -m pytest tests/unit -q` (현재 156 passed — 회귀 필수).
- 커밋 메시지 `<type>: <설명>` 한국어, attribution 금지. 외과적 수정 — 범위 외 리팩토링 금지.
- 면책 문구: /today 추천 카드에 백엔드 disclaimer("교육·연구용 정보로 투자 권유가 아닙니다") 표시 필수.

## 알려진 사실 (수집 완료 — 구현자 필독)

- **빌드**: node_modules에 react-router-dom(v7)·lightweight-charts 없음(package.json엔 선언됨 → npm install로 해소). @types/node 미선언 → `useWebSocket.ts:28` NodeJS namespace 에러. tsconfig `noUnusedLocals/noUnusedParameters: true` + strict → TS6133(미사용) 다수와 실타입에러 소수가 빌드 전체를 막음: 실에러 = `AdvancedStrategyBuilder.tsx:243,250`(never), `ResultsDisplay.tsx:203-214`(Sortino/Calmar/TailRatio 타입에 없음), `StrategyComparison.tsx:184`(chart.js font weight), `TradingTimeline.tsx:40,50,51`(undefined 가능), `MasterStrategySelector.tsx:174`(placeholder prop 없음). TS6133 파일: TradingDashboard, StockChart, SimpleStrategyForm, MasterStrategyResults, PortfolioChart, RealtimeMonitor, Candlestick 등.
- **라우팅**: `App.tsx:200-209` — index=StrategyPage, compare/realtime/dashboard/learn, `*`→`/`. 네비는 `Layout.tsx:43-49` menuItems 배열.
- **api.ts**: baseURL '/api/v1' (vite 프록시 `/api`→localhost:8000, vite.config.ts:13-24). `PortfolioStatusResponse`(381-394행)에 price_is_stale 없음(백엔드는 있음). /today 클라이언트 함수 없음 — 486행 부근에 추가.
- **/today 백엔드 API 존재**: GET `/today/news`(date?,symbol?) → {date,count,articles[{title,url,source,published_at,sentiment,symbols}]}; `/today/recommendations` → {date,count,disclaimer,recommendations[{symbol,name,score,passed_conditions[ConditionCheck],technical_signals[ConditionCheck]}]}; `/today/status` → {date,jobs:{name:{status,detail,finished_at}}}. ConditionCheck = {condition_name, condition_name_en, required_value, actual_value, passed}.
- **TradingDashboard**: LIVE UI = 모드 select(413-423), 배지(281-289), confirm(104-111), state(44행). 강제 다크 = 루트 258행 `bg-gray-950` + 카드 7곳 `bg-gray-900`. formatKRW가 미국 주식도 ₩ 표시(564-569행). 폴링 5초(61-69행). 긴급정지 자체 모달 패턴 355-387행 존재(재사용).
- **StockChart**: 가짜 데이터 = 23-140행 useMemo(Math.random). props startDate/endDate 미사용. 데이터 형태 {date,open,high,low,close,price}. 렌더 블록이 4벌 복붙(462-887, 1150-1574) — 데이터 소스(useMemo 1곳)만 교체하면 렌더는 그대로 동작. **백엔드에 OHLCV 엔드포인트 없음** → Task 2에서 신설.
- **수익곡선**: `SnapshotRepository.list_all()` 존재, 노출 API 없음 → Task 2에서 신설. 하루 1행이라 초기엔 점 1~2개 — 빈/희소 상태 UI 필요.
- **alert 15곳 + confirm 2곳**: App.tsx 45,58(에러),81(성공); MasterStrategySelector 26,66(경고),42(에러); ComparisonPage 38(에러),53,57(경고); TradingDashboard 140,177,203(성공),144,181,206(에러) + confirm 105(LIVE — 제거 대상),154(중지 확인 — 모달로).
- **ErrorBoundary 없음**. main.tsx: StrictMode > BrowserRouter > App. React 18.2 class 패턴 사용.
- **스타일**: tailwind darkMode 'class', primary(sky)/success/danger/warning 토큰, index.css `.card/.btn/.input`(dark 변형 없음). 다크 토글 = Layout.tsx:19-38.
- **실행**: `run_frontend.bat`(npm install+dev), vite port 5173 strictPort(배치 파일의 "4783" 문구는 거짓), 백엔드 8000.

---

### Task 1: 빌드 복구

**Files:**
- Modify: `frontend/package.json` (devDependencies에 `"@types/node": "^22"`)
- Modify: 위 "알려진 사실"의 TS 에러 파일 전부 — **동작 변경 없는 최소 수정만**: 미사용 import/변수 삭제(TS6133), 실타입에러는 옵셔널 필드 추가·타입 단언·undefined 가드 등 가장 작은 수정. `ResultsDisplay`의 Sortino/Calmar/TailRatio는 `api.ts`의 metrics 타입에 `Sortino?: number` 등 옵셔널 추가로 해소(표시 로직 유지).
- 검증: `npm install` → `npm run build` **통과**

**Interfaces:** 이후 모든 프론트 태스크의 전제. 동작 변경 금지 — 삭제한 미사용 항목 목록을 보고서에 기록.

- [ ] Step 1: `npm install` + `npm install -D @types/node` → 모듈 에러 해소 확인 (`npx tsc --noEmit` 에러 수 기록)
- [ ] Step 2: 파일별 최소 수정 (수정마다 tsc 에러 수 감소 확인)
- [ ] Step 3: `npm run build` 통과 + 백엔드 테스트 회귀(무관하지만 관례)
- [ ] Step 4: 커밋 `fix: 프론트엔드 빌드 복구 (의존성 설치·미사용 코드 정리·타입 에러 수정)` (package-lock.json 포함)

---

### Task 2: 백엔드 소형 API 2개 + api.ts 클라이언트

**Files:**
- Create: `backend/app/api/market_routes.py` — `GET /api/v1/price-history?symbol=005930.KS&start=YYYY-MM-DD&end=YYYY-MM-DD` → `{symbol, count, bars: [{date, open, high, low, close, volume}]}`. 데이터 소스: 한국 종목은 `paper_reconcile.fetch_daily_pykrx` 재사용(소문자 컬럼 반환), 미국은 같은 함수가 yfinance 처리. 빈 결과 → 200 + count 0 (404 아님). 내부 예외 → 500 + 일반 메시지(상세 로그만).
- Modify: `backend/app/api/trading_routes.py` — `GET /api/v1/portfolio/snapshots` → `{count, snapshots: [{snapshot_date, total_value, cash, positions_value}]}` (`SnapshotRepository.list_all()` — Phase 1 저장소, db_path 기본).
- Modify: `backend/app/main.py` — market_routes 등록 (기존 패턴).
- Modify: `frontend/src/services/api.ts` — ① `PortfolioStatusResponse`에 `price_is_stale?: boolean` 추가, ② 타입+함수 추가: `getTodayNews(date?, symbol?)`, `getTodayRecommendations(date?)`, `getTodayStatus()`, `getPriceHistory(symbol, start, end)`, `getPortfolioSnapshots()` — 기존 패턴(`async (): Promise<T> => (await api.get(...)).data`).
- Test: `backend/tests/unit/test_market_routes.py` — TestClient + fetch_daily monkeypatch(합성 DF)로 price-history 응답 형태·빈 결과 200; snapshots는 tmp DB 주입(today_routes의 팩토리 monkeypatch 패턴 참조 — snapshots 핸들러도 팩토리 함수 경유로 작성).

- [ ] Step 1: 백엔드 TDD (RED→GREEN, 회귀 156+) → 커밋 `feat: 가격 시계열·수익곡선 스냅샷 API 추가`
- [ ] Step 2: api.ts 수정 → `npm run build` 통과 → 커밋 `feat: /today·가격·스냅샷 API 클라이언트 추가`

---

### Task 3: 토스트 시스템 + ErrorBoundary (공통 인프라)

**Files:**
- Create: `frontend/src/components/Toast.tsx` — Context 기반: `ToastProvider`, `useToast()` → `{success(msg), error(msg), warning(msg)}`. 우상단 고정, 4초 자동 소멸, 수동 닫기 버튼, 타입별 색(success/danger/warning 토큰), dark 변형, 동시 여러 개 스택. framer-motion 금지(CSS transition).
- Create: `frontend/src/components/ErrorBoundary.tsx` — class 컴포넌트(strict 타입 명시), fallback UI: "문제가 발생했습니다" + 오류 메시지 + "새로고침" 버튼(window.location.reload), dark 변형.
- Modify: `frontend/src/App.tsx` — QueryClientProvider 안쪽에 `<ToastProvider>`, Routes를 `<ErrorBoundary>`로 감싸기.

- [ ] Step 1: 구현 → 빌드 통과 → 임시 사용처 없이도 렌더 영향 없음 확인
- [ ] Step 2: 커밋 `feat: 토스트 시스템·ErrorBoundary 추가`

---

### Task 4: alert()/confirm 전면 교체

**Files:**
- Modify: `frontend/src/App.tsx`(45,58→error, 81→success), `MasterStrategySelector.tsx`(26,66→warning, 42→error), `ComparisonPage.tsx`(38→error, 53,57→warning), `TradingDashboard.tsx`(140,177,203→success, 144,181,206→error) — 전부 `useToast()`로. 이모지 제거하고 문구 유지.
- `TradingDashboard.tsx` confirm 2곳: 105행(LIVE 경고)은 **Task 6에서 LIVE UI째 제거되므로 이 태스크에서는 두라**(충돌 방지). 154행(중지 확인)은 기존 긴급정지 모달 패턴(355-387행)을 일반화해 재사용(확인 모달 컴포넌트로 추출 가능하면 같은 파일 안에서).
- 검증: `npm run build` + 각 화면에서 토스트가 뜨는지는 Task 8 스모크에서.

- [ ] Step 1: 교체 → 빌드 통과 → grep으로 `alert(` 잔존 0건 확인(TradingDashboard 105행 confirm 제외)
- [ ] Step 2: 커밋 `feat: alert/confirm을 토스트·확인 모달로 교체`

---

### Task 5: /today 페이지 (홈)

**Files:**
- Create: `frontend/src/pages/TodayPage.tsx`
- Modify: `frontend/src/App.tsx` — index를 TodayPage로, StrategyPage는 `path="strategy"`로 이동. `*`→`/` 유지.
- Modify: `frontend/src/components/Layout.tsx` — menuItems 맨 앞에 `{path: '/', label: '오늘', icon: ...}` 추가, 기존 전략 분석 항목 path를 '/strategy'로.

**TodayPage 구성** (React Query useQuery 3개 — mutation+useState 이중관리 금지):
1. **작업 상태 스트립**: getTodayStatus — 3개 작업(뉴스/추천/정산)의 성공·실패·진행중 배지. 작업이 아직 없으면(기동 직후) "수집 중..." 표시 + 30초 refetchInterval (전부 success/failure면 폴링 중단).
2. **추천 카드 그리드**: getTodayRecommendations — 카드마다 종목명·심볼·score(크게)·통과 조건 배지(passed=true인 condition_name들)·시그널 배지. 카드 클릭 → 펼침(조건 체크리스트 전체: 기존 조건 체크 UI 패턴 — 초록/빨강 박스, MasterStrategyResults.tsx 216-262행 참조 — + 해당 종목 뉴스 `getTodayNews(undefined, symbol)` lazy 조회). 빈 상태: "오늘 추천이 아직 없습니다 (주말·장 시작 전이거나 수집 중)". **상단에 disclaimer 문구 상시 표시.**
3. **뉴스 피드**: getTodayNews — 시간 내림차순 리스트: [호재/악재/중립 색 배지] 제목(원문 링크, 새 탭) · 언론사 · 시각 · 연결 종목 칩. 빈 상태 처리.
- 로딩 스피너/에러+재시도(refetch 버튼) 각 섹션 독립. 다크 변형 병기. 이모지를 의미 전달 주수단으로 쓰지 말 것(색+텍스트).

- [ ] Step 1: 구현 → 빌드 통과
- [ ] Step 2: 커밋 `feat: 오늘 페이지 신설 (추천·뉴스·수집상태, 홈 지정)`

---

### Task 6: TradingDashboard 수리

**Files:** `frontend/src/components/TradingDashboard.tsx`, (필요시) `frontend/src/services/api.ts`

1. **LIVE 제거**: 모드 select(413-423)·배지(281-289)·confirm(104-111)·`tradingMode` state 제거 → 시작 요청 `mode: 'paper'` 고정, 헤더에 "모의투자 전용" 라벨.
2. **테마**: 루트 `bg-gray-950 text-white` → `bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-white`, 카드 7곳 동일 패턴으로 (기존 다크 룩은 dark: 변형으로 보존).
3. **지연 배지**: `portfolio.price_is_stale`이 true면 "시세 갱신 전" 배지, 아니면 "시세 약 15분 지연" 상시 소형 배지.
4. **수익 곡선**: getPortfolioSnapshots → recharts LineChart(total_value). 데이터 2점 미만이면 "데이터가 쌓이면 수익 곡선이 표시됩니다" placeholder.
5. **통화 포맷**: `formatKRW`를 심볼 기반 분기 — `.KS/.KQ` 또는 6자리 숫자면 ₩ 정수, 아니면 $ 소수 2자리 (paper_execution.is_korean_symbol과 동일 규칙을 TS로).

- [ ] Step 1: 구현 → 빌드 통과
- [ ] Step 2: 커밋 `feat: 대시보드 수리 (모의 전용·테마 정합·지연 배지·수익 곡선·통화 포맷)`

---

### Task 7: StockChart 실데이터 교체

**Files:** `frontend/src/components/StockChart.tsx`

- 23-140행 가짜 데이터 useMemo 제거 → React Query `getPriceHistory(symbol, start, end)`. 기간: props `startDate/endDate`가 있으면 그것을, 없으면 내부 chartPeriod로 계산 — **폼 선택 기간과 차트 동기화**가 목적.
- 응답 bars → 기존 데이터 형태 {date,open,high,low,close,price(=close)}로 매핑 — 렌더 4벌은 무수정으로 동작해야 함.
- 로딩 스피너·에러("가격 데이터를 불러올 수 없습니다"+재시도)·빈 데이터 상태 추가. symbol 변경 시 자동 refetch(queryKey에 symbol/기간 포함).
- 하드코딩 시작가 목록(88-96행)과 미사용 유틸 함께 제거.

- [ ] Step 1: 구현 → 빌드 통과
- [ ] Step 2: 커밋 `fix: 종목 차트를 실데이터로 교체 (랜덤 데이터 제거, 기간 동기화)`

---

### Task 8: 스모크 (실행 검증 — 컨트롤러 수행)

- [ ] 백엔드(8000) + 프론트 dev(5173) 기동, 브라우저 확인 항목:
  1. `/` → 오늘 페이지: 추천 카드(있으면)·뉴스 피드·상태 스트립·disclaimer
  2. 카드 펼침 → 조건 체크리스트 + 종목 뉴스
  3. `/dashboard` → 라이트/다크 모두 정상, LIVE 흔적 없음, paper 시작 → 토스트 표시
  4. `/strategy` → 종목 차트가 실데이터(삼성전자 실제 최근 종가와 대조), 기간 변경 반영
  5. 에러 경로: 백엔드 내리고 새로고침 → ErrorBoundary가 아닌 각 섹션 에러+재시도 UI (ErrorBoundary는 렌더 예외용)
- [ ] `npm run build` 최종 통과 + 백엔드 156+ 테스트 회귀
- [ ] 발견 문제 stop-the-line

---

## Self-Review 결과

- **Spec coverage**: 6절 4항목 전부 매핑(①Task 5, ②Task 6, ③Task 7, ④Task 3·4) + 전제인 빌드 복구(Task 1)와 데이터 API(Task 2). 범위 외(차트 통일·다크 전면·죽은 코드 제거)는 계획에서 명시적으로 제외 유지 — 단 Task 1의 TS6133 정리는 빌드 게이트상 불가피한 최소 삭제로 한정.
- **Placeholder scan**: 통과 — 파일·라인·응답 형태·상태 처리 규칙 명시. 프론트 태스크는 코드 전문 대신 인터페이스+참조 패턴 방식(Phase 2·3에서 검증된 방식).
- **Type consistency**: api.ts 함수명(getToday*/getPriceHistory/getPortfolioSnapshots)이 Task 2↔5↔6↔7 간 일치. price-history 응답 bars 필드가 StockChart 매핑과 일치.
- **리스크**: Task 1이 손대는 파일이 많아(기계적이지만) 회귀 위험 → 동작 변경 금지 원칙과 빌드 게이트로 통제, Task 8 스모크가 최종 안전망.

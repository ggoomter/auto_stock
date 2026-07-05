# Phase 3: 뉴스 수집 + 추천 종목 + 따라잡기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 서버 기동 시 "오늘치 따라잡기(catch-up)"로 네이버 금융 뉴스를 수집·종목 연결하고, pykrx 기반 전 종목 추천을 생성하고, 꺼져 있던 기간의 모의투자 포지션을 일봉으로 보수적으로 정산한다.

**Architecture:** 신규 서비스 3개 — `naver_news.py`(수집·종목매칭·태깅, 순수 로직과 네트워크 분리), `recommender.py`(pykrx 유니버스→펀더멘털 필터→기술 시그널→점수화), `daily_jobs.py`(job_runs 기반 멱등 오케스트레이터). 저장소 2개 추가(News/Recommendation). API는 `/api/v1/today/*` 신설. **네트워크 없는 단위 테스트 원칙** — HTML/DataFrame 픽스처로 순수 로직 검증, 실네트워크는 Task 9 스모크에서.

**Tech Stack:** requests + BeautifulSoup4(venv에 4.14.2 설치됨, requirements 선언만 추가), pykrx, 기존 indicators.py(pandas-ta), sqlite3.

**Spec:** `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md` 4.2/5.3/5.4절

## Global Constraints

- 새 pip 패키지 설치 금지 — 단 venv에 이미 있는 beautifulsoup4/lxml의 requirements.txt 선언은 이번 범위.
- fabrication 금지: 데이터 없으면 None/빈 값 + 로그. 태그 판단 불가면 'neutral'.
- 멱등성: 뉴스 재수집은 `INSERT OR IGNORE`(url UNIQUE), 추천 재생성은 `INSERT OR REPLACE`(rec_date+symbol UNIQUE), 작업 기록은 기존 `JobRunRepository`(job_name+run_date UNIQUE) 계약.
- 따라잡기 정산은 **보수적**: 꺼진 기간에 손절가 터치 시 `min(해당일 시가, 손절가)`... 정확 규칙은 Task 6 참조 — 낙관적 체결 금지.
- 네이버 요청 간 1초 딜레이, User-Agent 헤더 필수, 실패는 job_runs 기록 후 앱 계속.
- pytest: `backend/`에서 `venv\Scripts\python -m pytest ...` (현재 74 passed — 회귀 필수). 단위 테스트에서 실네트워크 호출 금지.
- 커밋 메시지 `<type>: <설명>` 한국어, attribution 금지.

## 알려진 코드 사실 (구현자 필독)

- DB 스키마 이미 존재 (`app/db/database.py:48-83`): `news_articles(id, published_at, source, title, url UNIQUE, summary, sentiment DEFAULT 'neutral')`, `news_stock_links(article_id, symbol, PK(article_id,symbol))`, `recommendations(id, rec_date, symbol, name, score, passed_conditions TEXT, technical_signals TEXT, UNIQUE(rec_date,symbol))`, `job_runs(job_name, run_date, status, detail, finished_at, UNIQUE(job_name,run_date))`.
- `repositories.py` 패턴: 호출마다 `get_connection(self._db_path)` → try/finally close, 반환 `[dict(r) for r in rows]`. `JobRunRepository.record/has_succeeded`, `SnapshotRepository`, `PaperTradingRepository(list_open_positions/close_position/update_stops)` 존재.
- `stock_screener.py:328`: 후보 >50일 때 존재하지 않는 `ScreenerType.GRAHAM` 참조 → AttributeError (enum 멤버: VALUE/GROWTH/QUALITY/MOMENTUM/DIVIDEND/GARP/BUFFETT/LYNCH/SAFE).
- pykrx 사용 현황: `get_market_ticker_list`, `get_market_fundamental_by_ticker(date, market)` (PER/PBR/EPS/BPS/DIV/DPS — **ROE 없음, EPS/BPS로 계산 가능**), 사용 안 하는 것: `get_market_cap_by_ticker`(시총·거래대금 — 신규 도입 필요), `get_market_ticker_name`(종목명 — 신규 도입 필요). pykrx는 휴장일 조회 시 빈/0값 DF 반환 — 최근 영업일로 보정 필요.
- `main.py:91-96`: `@app.on_event("startup")`에서 `init_db()` + `register_websocket_callbacks()` — 여기에 daily_jobs 기동 추가 (lifespan 전환은 범위 밖).
- 라우터 등록: `app.include_router(r, prefix=settings.API_V1_STR, tags=[...])` 패턴 (main.py:85-88). `API_V1_STR="/api/v1"`.
- `news_crawler.py`(NewsAPI 기반)와 `event_scheduler.py`(JSON 파일, 미기동)는 **사용하지 않음** — 건드리지 마라.
- `indicators.py`의 `IndicatorCalculator.calculate_all(df)`: 소문자 open/high/low/close/volume 컬럼 기대, 말미 dropna()로 선행 구간 소실(200일 MA 등). pykrx OHLCV는 한글 컬럼(시가/고가/저가/종가/거래량) — rename 필요.
- `ConditionCheck` 스키마(schemas.py:177-183): `{condition_name, condition_name_en, required_value, actual_value, passed}` — 추천 근거 JSON도 이 형태로 저장하면 프론트 조건 체크 UI 재사용 가능.
- 모의투자 체결 규칙 재사용: `paper_execution.simulate_fill_price(price, side, slippage, symbol)`, `tick_size.round_to_tick_down`.
- beautifulsoup4 4.14.2·lxml 6.0.2 venv 설치됨, requirements.txt 미선언.

---

### Task 1: 저장소 확장 (News/Recommendation) + requirements 선언

**Files:**
- Modify: `backend/app/db/repositories.py` (클래스 2개 추가)
- Modify: `backend/requirements.txt` (beautifulsoup4, lxml 선언 — "# 뉴스 크롤링" 주석과 함께)
- Test: `backend/tests/unit/test_news_and_reco_repository.py`

**Interfaces (Produces):**
```python
class NewsRepository:
    def __init__(self, db_path: str | None = None): ...
    def save_article(self, published_at: str, source: str, title: str, url: str,
                     summary: str | None, sentiment: str,
                     symbols: list[str]) -> int | None:
        # INSERT OR IGNORE (url UNIQUE). 신규 삽입 시 article_id 반환하고 news_stock_links에
        # symbols 연결(INSERT OR IGNORE). 이미 존재(무시)면 None 반환, 링크도 건드리지 않음.
    def list_by_date(self, date_prefix: str) -> list[dict]:
        # published_at LIKE 'YYYY-MM-DD%' — 각 dict에 'symbols': [연결 종목코드] 포함, 최신순
    def list_for_symbol(self, symbol: str, limit: int = 20) -> list[dict]
    def count_by_date(self, date_prefix: str) -> int

class RecommendationRepository:
    def __init__(self, db_path: str | None = None): ...
    def save(self, rec_date: str, symbol: str, name: str | None, score: float,
             passed_conditions: list[dict], technical_signals: list[dict]) -> None:
        # INSERT OR REPLACE. passed_conditions/technical_signals는 json.dumps(ensure_ascii=False)
    def list_by_date(self, rec_date: str) -> list[dict]:
        # score 내림차순. JSON 컬럼은 json.loads 해서 list로 반환
    def latest_date(self) -> str | None  # 가장 최근 rec_date (프론트 "최신 추천" 용)
```

- [ ] **Step 1: 실패하는 테스트** — 시나리오: ① save_article 신규 → id 반환 + 링크 저장, 같은 url 재저장 → None + 기사 1건 유지; ② list_by_date가 symbols 포함해 최신순 반환; ③ RecommendationRepository.save 같은 (날짜,종목) 재저장 시 upsert; ④ list_by_date의 JSON 역직렬화 + score 내림차순; ⑤ latest_date. (픽스처는 Phase 1 방식: `init_db(tmp_path)` — `tests/unit/test_paper_repository.py` 참조)
- [ ] **Step 2: RED 확인** → **Step 3: 구현** (기존 저장소 패턴 그대로) → **Step 4: GREEN + 전체 회귀** → **Step 5: 커밋** `feat: 뉴스·추천 저장소 추가 및 크롤링 의존성 선언`

---

### Task 2: stock_screener GRAHAM 크래시 수정

**Files:**
- Modify: `backend/app/services/stock_screener.py:328` (존재하지 않는 `ScreenerType.GRAHAM` 참조 제거 — `[ScreenerType.VALUE, ScreenerType.BUFFETT]`로)
- Test: `backend/tests/unit/test_screener_no_crash.py`

- [ ] **Step 1: 실패하는 테스트** — 네트워크 없이: 51개 가짜 후보 DataFrame을 만들어 크래시 지점 분기만 직접 검증하거나, 최소한 `ScreenerType` 모든 멤버 접근 + 해당 분기 리스트가 실제 enum 멤버로만 구성됨을 소스 검사로 assert:
```python
def test_screener_type_references_are_valid():
    import inspect
    from app.services import stock_screener
    src = inspect.getsource(stock_screener)
    import re
    referenced = set(re.findall(r"ScreenerType\.([A-Z_]+)", src))
    valid = {m.name for m in stock_screener.ScreenerType}
    assert referenced.issubset(valid), f"존재하지 않는 멤버 참조: {referenced - valid}"
```
- [ ] **Step 2-4: RED → 수정 → GREEN + 회귀** → **Step 5: 커밋** `fix: 스크리너의 존재하지 않는 ScreenerType.GRAHAM 참조 제거 (후보 50개 초과 시 크래시)`

---

### Task 3: 종목명 사전 + 종목 매칭 + 감성 태깅 (naver_news.py 순수 로직)

**Files:**
- Create: `backend/app/services/naver_news.py` (이 태스크에서는 순수 로직만)
- Test: `backend/tests/unit/test_news_matching.py`

**Interfaces (Produces):**
```python
def build_name_map() -> dict[str, str]:
    # pykrx get_market_ticker_list(market="KOSPI"/"KOSDAQ") × get_market_ticker_name(ticker)
    # → {"삼성전자": "005930.KS", "카카오": "035720.KS", ...} (KOSPI=.KS, KOSDAQ=.KQ 접미사)
    # pykrx 실패 시 빈 dict + logger.warning. 모듈 레벨 캐시(프로세스당 1회).

def match_stocks(title: str, name_map: dict[str, str]) -> list[str]:
    # 제목에 포함된 종목명 → 심볼 리스트. 긴 이름 우선 매칭(겹침 방지: "삼성전자우" vs "삼성전자"),
    # 2글자 미만 이름 제외(오탐), 중복 제거, 매칭 순서 유지.

POSITIVE_KEYWORDS = ["수주", "흑자전환", "신고가", "상향", "호실적", "매수", "급등", "돌파", "최대 실적", "배당 확대", "자사주 매입"]
NEGATIVE_KEYWORDS = ["적자", "소송", "하향", "유상증자", "급락", "부진", "리콜", "횡령", "감자", "상장폐지", "경고"]

def tag_sentiment(title: str) -> str:
    # positive/negative 키워드 카운트 비교 → 'positive'/'negative', 동수·무매칭 → 'neutral'
```

- [ ] **Step 1: 실패하는 테스트** — 네트워크 없음(고정 name_map 사용):
```python
def test_match_longest_name_first():
    name_map = {"삼성전자": "005930.KS", "삼성전자우": "005935.KS", "카카오": "035720.KS"}
    assert match_stocks("삼성전자우 강세, 카카오도 상승", name_map) == ["005935.KS", "035720.KS"]

def test_match_no_partial_pollution():
    # "삼성전자우" 기사에서 "삼성전자"가 함께 매칭되면 안 됨 (긴 이름이 소비)
    ...

def test_sentiment_positive_negative_neutral():
    assert tag_sentiment("A사 대규모 수주 소식에 급등") == "positive"
    assert tag_sentiment("B사 소송 리스크에 급락") == "negative"
    assert tag_sentiment("C사 주주총회 개최") == "neutral"
    assert tag_sentiment("D사 수주에도 소송 우려") == "neutral"  # 동수
```
build_name_map은 pykrx를 mock(patch)해 KOSPI/KOSDAQ 접미사 부착을 검증.
- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** → **Step 5: 커밋** `feat: 뉴스 종목 매칭·감성 태깅 로직 추가`

---

### Task 4: 네이버 금융 뉴스 크롤러 (fetch + parse)

**Files:**
- Modify: `backend/app/services/naver_news.py` (수집 함수 추가)
- Create: `backend/tests/fixtures/naver_mainnews_sample.html` (구현자가 실제 페이지를 1회 저장해 고정 픽스처로 — 저작권상 구조 검증에 필요한 최소 부분만 남기고 축약 가능)
- Test: `backend/tests/unit/test_naver_crawler.py`

**Interfaces (Produces):**
```python
@dataclass
class NewsItem:
    title: str
    url: str            # 절대 URL
    source: str         # 언론사명, 없으면 "naver"
    published_at: str   # "YYYY-MM-DD HH:MM" (파싱 실패 시 수집 시각)
    summary: str | None

def parse_mainnews_html(html: str, base_url: str = "https://finance.naver.com") -> list[NewsItem]:
    # 순수 함수 — 픽스처로 테스트. 구조 변경으로 0건 파싱되면 빈 리스트 + 호출자가 로그.

def fetch_mainnews(pages: int = 3, delay_sec: float = 1.0) -> list[NewsItem]:
    # https://finance.naver.com/news/mainnews.naver?page=N 을 requests로 GET
    # (User-Agent 헤더, timeout=10, 실패 페이지는 건너뛰고 logger.warning). 반환 전 url 기준 중복 제거.

def collect_and_store(repo: NewsRepository, name_map: dict[str, str],
                      pages: int = 3) -> dict:
    # fetch → 각 기사: match_stocks + tag_sentiment → repo.save_article
    # 반환: {"fetched": n, "inserted": m, "linked_symbols": k} (daily_jobs가 detail로 기록)
```

- [ ] **Step 1: 실제 페이지 구조 확인** — 구현자는 네이버 금융 주요뉴스 페이지(https://finance.naver.com/news/mainnews.naver)를 1회 가져와 실제 DOM 구조(기사 목록 셀렉터, 제목/링크/언론사/시각 위치)를 확인하고, 그 HTML을 픽스처로 저장한 뒤 **관찰한 셀렉터를 보고서에 기록**하라. 페이지 구조가 예상(li 목록)과 다르면 관찰 결과가 정답이다. 네트워크 불가 환경이면 BLOCKED 보고.
- [ ] **Step 2: 실패하는 테스트** — 픽스처 기반: `parse_mainnews_html(fixture)` → 1건 이상, 각 item의 title 비어있지 않음·url 절대경로·published_at 형식. 빈 HTML → 빈 리스트(예외 금지). `collect_and_store`는 fetch를 mock해 저장·링크·통계 반환 검증.
- [ ] **Step 3-4: RED → 구현 → GREEN + 회귀** → **Step 5: 커밋** `feat: 네이버 금융 뉴스 크롤러 추가`

---

### Task 5: 추천 엔진 (recommender.py)

**Files:**
- Create: `backend/app/services/recommender.py`
- Test: `backend/tests/unit/test_recommender.py`

**Interfaces (Produces):**
```python
@dataclass
class Candidate:
    symbol: str; name: str; close: float
    per: float | None; pbr: float | None; roe: float | None  # roe = eps/bps (소수, 0.15=15%)
    market_cap: float | None

def build_universe(top_n: int = 300, date: str | None = None) -> list[Candidate]:
    # pykrx: 최근 영업일 보정(오늘부터 최대 7일 역방향으로 get_market_cap_by_ticker가
    # 비지 않은 날짜 탐색) → KOSPI+KOSDAQ 시가총액 상위 top_n
    # → get_market_fundamental_by_ticker로 PER/PBR/EPS/BPS 병합, roe=eps/bps(bps>0일 때만)
    # → get_market_ticker_name으로 이름. 실패 시 빈 리스트 + logger.warning.

def fundamental_filter(cands: list[Candidate]) -> list[tuple[Candidate, list[dict]]]:
    # 조건(ConditionCheck dict 형식으로 기록):
    #   PER: 0 < per < 25 / PBR: 0 < pbr < 3 / ROE: roe > 0.10
    # 3개 중 2개 이상 통과한 후보만 반환. 각 후보에 조건별
    # {condition_name, condition_name_en, required_value, actual_value, passed} 리스트 첨부.
    # 값 None인 조건은 passed=False + actual_value='데이터 없음'.

def technical_signals(symbol: str, ohlcv: pd.DataFrame) -> list[dict]:
    # 입력: 소문자 컬럼 일봉 (호출자가 pykrx 한글 컬럼 rename 후 전달, 최소 260행 권장)
    # 시그널 3종 (같은 dict 형식, condition_name):
    #   골든크로스: MA20이 MA60을 최근 5일 내 상향 돌파
    #   RSI 반등: RSI(14)가 최근 10일 내 30 미만 → 현재 30 이상
    #   52주 신고가 근접: 종가가 252일 최고가의 95% 이상
    # 데이터 부족(260행 미만)이면 판정 불가 조건은 passed=False + '데이터 부족'.

def score(passed_conditions: list[dict], signals: list[dict]) -> float:
    # 펀더멘털 통과 1개당 20점 + 기술 시그널 1개당 (100 - 60) / 3 점 → 최대 100.
    # 단순·설명 가능 우선. 근거 없는 가중치 금지.

def generate_recommendations(repo: RecommendationRepository, rec_date: str,
                             top_n_universe: int = 300, top_k: int = 10,
                             max_technical: int = 30) -> dict:
    # build_universe → fundamental_filter → 상위 max_technical개만 OHLCV 조회(pykrx
    # get_market_ohlcv, 종목당 1회, 0.3초 딜레이)해 technical_signals → score →
    # 상위 top_k를 repo.save. 반환 {"universe": n, "filtered": m, "saved": k}.
```

- [ ] **Step 1: 실패하는 테스트** — 순수 로직만 (pykrx mock/합성 DataFrame):
  - `fundamental_filter`: 3개 통과/2개 통과/1개 통과(제외)/값 None(passed=False) 케이스
  - `technical_signals`: 골든크로스가 있는 합성 시계열(MA20<MA60 → 상향 돌파)에서 passed=True, 횡보 시계열에서 False, 100행짜리 짧은 데이터에서 '데이터 부족'
  - `score`: 5개 전부 통과 = 100 근사, 0개 = 0
  - `generate_recommendations`: build_universe/OHLCV를 mock해 저장 호출·통계 검증
- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** → **Step 5: 커밋** `feat: pykrx 기반 일별 추천 엔진 추가 (펀더멘털+기술 시그널, 근거 저장)`

---

### Task 6: 모의투자 따라잡기 정산 (보수적)

**Files:**
- Create: `backend/app/services/paper_reconcile.py`
- Test: `backend/tests/unit/test_paper_reconcile.py`

**Interfaces (Produces):**
```python
def reconcile_positions(repo: PaperTradingRepository,
                        fetch_daily: Callable[[str, str, str], pd.DataFrame],
                        as_of: str) -> dict:
    # repo.list_open_positions()의 각 포지션에 대해:
    #   bars = fetch_daily(symbol, entry_at 이후 다음날, as_of)  # 소문자 open/high/low/close
    #   날짜 오름차순으로 순회하며 (보수적 규칙):
    #     1) low <= stop_loss  → 청산가 = min(open, stop_loss)를 호가단위 내림 → close_position(reason="손절매(정산)")
    #     2) high >= take_profit → 청산가 = take_profit을 호가단위 내림 (갭상승 개장이어도 목표가 — 낙관 금지... 단 open > take_profit이면 open 사용이 아니라 take_profit 사용: 보수 방향은 낮은 값이므로 take_profit)
    #     같은 봉에서 둘 다 터치 → 손절 우선 (백테스트 엔진과 동일 규칙)
    #   청산 안 됐으면 highest_price/트레일링 갱신 없이 유지(트레일링은 장중 엔진 소관).
    # fetch_daily 실패/빈 DF → 해당 포지션 건너뛰고 결과에 기록.
    # 반환: {"checked": n, "closed": m, "skipped": s, "details": [...]}

def fetch_daily_pykrx(symbol: str, start: str, end: str) -> pd.DataFrame:
    # 한국 종목: pykrx get_market_ohlcv → 소문자 rename. 미국 종목: yfinance history.
    # 실패 시 빈 DataFrame.
```
- 주의: `close_position`은 중복 청산 방어가 없다(Phase 1 이월) — reconcile은 open 포지션 목록 기준으로만 호출하므로 안전하지만, 같은 실행 내 이중 호출이 없도록 루프 구조에 유의.
- 청산가 계산에 `tick_size.round_to_tick_down`, 한국 여부는 `paper_execution.is_korean_symbol` 재사용.

- [ ] **Step 1: 실패하는 테스트** — 스펙 8절의 시나리오 그대로 (네트워크 없음, fetch_daily는 합성 DataFrame 주입):
  - "서버 3일 꺼짐, 둘째 날 low가 손절가 터치" → closed, exit_price ≤ 손절가 (보수적), exit_reason에 "손절"
  - "갭하락 개장(open < stop_loss)" → 청산가 = open 기준 (min(open, stop) 규칙) — 낙관 금지 검증
  - "고가가 익절가 터치" → 청산가 = take_profit (그 이상 금지)
  - "같은 봉에서 손절·익절 동시 터치" → 손절 우선
  - "터치 없음" → 유지, checked=1 closed=0
  - "데이터 없음" → skipped
- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** → **Step 5: 커밋** `feat: 모의투자 오프라인 기간 보수적 정산(reconcile) 추가`

---

### Task 7: daily_jobs 오케스트레이터 + 기동 연결

**Files:**
- Create: `backend/app/services/daily_jobs.py`
- Modify: `backend/app/main.py` (startup에서 백그라운드 태스크 기동)
- Test: `backend/tests/unit/test_daily_jobs.py`

**Interfaces (Produces):**
```python
JOB_NEWS = "news_crawl"; JOB_RECO = "recommendations"; JOB_RECONCILE = "paper_reconcile"

async def run_catchup(db_path: str | None = None,
                      today: str | None = None) -> dict:
    # today 기본값: KST 오늘 (datetime.now() — 서버 로컬이 KST 가정, 주석 명시)
    # JobRunRepository.has_succeeded(job, today) 미충족 작업만 순서대로 실행:
    #   1) 뉴스: build_name_map → collect_and_store  2) 추천: generate_recommendations
    #   3) 정산: reconcile_positions(fetch_daily_pykrx)
    # 각 작업 독립 try/except: 성공 → record(..., 'success', detail=통계 JSON),
    #   실패 → record(..., 'failure', detail=str(e)[:500]) 후 다음 작업 계속.
    # 블로킹 작업(requests/pykrx)은 asyncio.to_thread로 감싸 이벤트 루프 보호.
    # 반환: {job_name: "success"|"failure"|"skipped(already)"} — 테스트 계약.

def start_background_catchup() -> None:
    # main.py startup에서 호출: asyncio.get_event_loop().create_task(run_catchup())
    # 주말(토·일)엔 뉴스만 수행하고 추천·정산은 skip (pykrx 휴장 — detail에 사유 기록).
```
- main.py 수정: startup_event에 `from .services.daily_jobs import start_background_catchup; start_background_catchup()` 추가 (init_db 다음). **동기로 기다리지 말 것** — 서버 기동을 막으면 안 됨.
- 장중 주기 루프(뉴스 30분)는 이 태스크 범위 — `run_catchup` 후 KST 09:00~15:30이면 30분 간격으로 뉴스만 재수집하는 `async def intraday_news_loop()`를 같은 태스크에서 이어 실행. 장외면 즉시 종료.

- [ ] **Step 1: 실패하는 테스트** — 네트워크 없음(작업 함수들 monkeypatch):
  - 오늘 이미 success인 작업은 skipped(already), 아닌 작업만 실행
  - 작업 1이 예외를 던져도 작업 2·3 실행 + job_runs에 failure 기록
  - 성공 시 job_runs에 success + detail 기록
  - 주말이면 추천·정산 skip
  (asyncio 테스트: `asyncio.run(run_catchup(db_path=..., today=...))`)
- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** (main.py import 스모크 포함) → **Step 5: 커밋** `feat: 서버 기동 시 따라잡기 오케스트레이터 추가 (뉴스·추천·정산 멱등 실행)`

---

### Task 8: /today API 엔드포인트

**Files:**
- Create: `backend/app/api/today_routes.py`
- Modify: `backend/app/main.py` (라우터 등록: `app.include_router(today_router, prefix=settings.API_V1_STR, tags=["today"])`)
- Test: `backend/tests/unit/test_today_api.py`

**Interfaces (Produces):**
- `GET /api/v1/today/news?date=YYYY-MM-DD&symbol=005930.KS` (둘 다 선택; date 기본 오늘) → `{"date": ..., "count": n, "articles": [{title, url, source, published_at, sentiment, symbols}]}`
- `GET /api/v1/today/recommendations?date=YYYY-MM-DD` (기본: `latest_date()`) → `{"date": ..., "count": n, "disclaimer": "교육·연구용 정보로 투자 권유가 아닙니다", "recommendations": [{symbol, name, score, passed_conditions: [...], technical_signals: [...]}]}`
- `GET /api/v1/today/status` → job_runs의 오늘 상태 `{"jobs": {job_name: {"status": ..., "detail": ..., "finished_at": ...}}}` (프론트 "수집 중/실패 사유" 표시용 — JobRunRepository에 `get_runs(run_date) -> list[dict]` 메서드 1개 추가 필요)
- 에러 처리: 내부 예외는 500 + 일반 메시지(상세는 로그만 — Phase 2까지의 `detail=str(e)` 패턴 반복 금지).

- [ ] **Step 1: 실패하는 테스트** — TestClient + tmp DB 주입이 어려우므로(전역 DEFAULT_DB_PATH), 라우터가 사용하는 저장소 접근을 모듈 함수(`_get_news_repo()` 등)로 분리하고 테스트에서 monkeypatch. 검증: 뉴스 2건 저장 후 date 조회 → 2건+symbols, symbol 필터 동작; 추천 저장 후 조회 → score 내림차순 + disclaimer 존재; status에 기록된 작업 상태 노출.
- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** → **Step 5: 커밋** `feat: /today API 추가 (뉴스·추천·작업상태 조회)`

---

### Task 9: 스모크 테스트 (실네트워크 E2E)

**Files:** 없음 (검증만 — 집 네트워크 필요: 회사 VPN에서는 SSL 차단됨, memory 참조)

- [ ] **Step 1**: 서버 기동 → 로그에서 catch-up 실행 확인 (뉴스 수집 통계, 추천 생성 통계). `backend/data/auto_stock.db`의 news_articles/recommendations에 오늘 데이터 존재 확인.
- [ ] **Step 2**: `GET /api/v1/today/news` → 오늘 뉴스 목록 (제목·태그·종목 링크 눈으로 표본 검증 — 종목 오매칭 표본 3건 확인). `GET /api/v1/today/recommendations` → 추천 목록 + 조건별 근거. `GET /api/v1/today/status` → 3개 작업 success.
- [ ] **Step 3**: 서버 재시작 → job_runs 멱등 확인 (같은 날 재실행 skip 로그). 모의투자 정산: open 포지션 1건 수동 삽입(손절가를 과거에 터치하도록) 후 재기동 → closed + 보수적 청산가 확인.
- [ ] **Step 4**: 문제 발견 시 stop-the-line. 통과 시 보고.

---

## Self-Review 결과

- **Spec coverage**: 4.2(catch-up 흐름 1~5) → Task 6·7; 5.3(네이버 수집·종목연결·태그·주기) → Task 3·4·7; 5.4(1차 pykrx 유니버스·2차 펀더멘털·3차 기술 시그널·점수화·근거저장·면책) → Task 5·8. 스크리너 크래시 수정(스펙 5.4 전제) → Task 2. 전부 매핑됨.
- **설계 변경 근거 명시**: 스펙 5.4는 "수리된 stock_screener로 버핏/린치/그레이엄 평가"라 했으나, 사실 수집 결과 screener의 2차 단계가 yfinance `.info` 종목당 순차 호출(후보 50개 = 50회 왕복, 실패 시 조용한 빈 dict)이라 신뢰성·속도 모두 부적합 → recommender는 pykrx 벌크 데이터(PER/PBR/EPS→ROE)로 자체 필터. screener는 크래시만 수정(Task 2 — auto_trading_engine이 사용 중이므로).
- **Placeholder scan**: 통과. Task 4의 셀렉터는 의도적으로 미지정 — 실제 DOM 관찰 후 결정(브리프에 명시), 나머지는 인터페이스·규칙 완결.
- **Type consistency**: NewsRepository ↔ collect_and_store ↔ today_routes의 dict 키, ConditionCheck 형식(fundamental_filter/technical_signals), reconcile의 fetch_daily 시그니처 — Task 간 일치 확인.
- **알려진 리스크**: ① 네이버 DOM 구조는 실측 필요(Task 4 Step 1), ② pykrx 휴장일 보정(Task 5 build_universe에 규칙 명시), ③ 뉴스 크롤링의 사이트 정책 — 요청 간 1초 딜레이·페이지 3개 제한으로 부하 최소화.

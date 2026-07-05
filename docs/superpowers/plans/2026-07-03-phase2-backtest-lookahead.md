# Phase 2: 백테스트 look-ahead 수리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 펀더멘털 백테스트의 look-ahead bias(미래 재무로 과거 판정)를 제거하고, 데이터 조작(하드코딩·기본값 fabrication)을 삭제하고, 한국 매도 거래세를 반영하고, 깨진 몬테카를로·Chanos를 비활성화한다.

**Architecture:** 신규 모듈 `pit_fundamentals.py`(point-in-time 지표 수집기)가 한국(DART 분기보고서)·미국(yfinance 최근 4분기) 재무를 "그 날짜에 알 수 있었던 최신 분기" 기준으로 제공한다. `fundamental_analysis.py`의 `check_*_criteria_at_date` 4개가 이를 사용하도록 재작성한다. **데이터 없으면 매수 불가(False)** — 조용한 통과 금지. 검증 가능 구간은 API 응답 warnings로 노출.

**Tech Stack:** 기존 스택만 (DART API, yfinance, pandas). 새 의존성 없음.

**Spec:** `docs/superpowers/specs/2026-07-02-simulation-news-recommendation-design.md` 5.1절

## Global Constraints

- 새 런타임 외부 의존성 금지.
- **look-ahead 금지 원칙**: 날짜 D의 판정에는 `분기말 + 45일(EARNINGS_DELAY_DAYS) <= D`인 분기의 재무만 사용. 위반을 잡는 회귀 테스트 필수.
- **fabrication 금지 원칙**: 데이터가 없으면 None/False를 반환하고 이유를 로그·응답에 남긴다. 기본값 대체(성장률 0.10, current_ratio 1.5, ROE→성장률 proxy, 삼성 하드코딩) 전면 삭제.
- 한국 매도 거래세: `sell_tax_bps: int = 18` (schemas.py 설정, 한국 종목 매도 체결가에만 적용).
- pytest: `backend/`에서 `venv\Scripts\python -m pytest ...`. 네트워크 없는 단위 테스트 원칙 — DART/yfinance는 고정 픽스처로 mock.
- 커밋 메시지 `<type>: <설명>` 한국어, attribution 금지.
- 기존 현재-시점 스크리닝 API(`get_buffett_metrics` 등의 "지금" 용도)는 유지하되 fabrication만 제거 — 백테스트 경로(`*_at_date`)와 분리.

## 알려진 코드 사실 (구현자 필독)

- `fundamental_analysis.py:36-40` — DART 클라이언트는 `self._dart_client`로 초기화됨. `check_*_at_date` 안의 `self.dart_client` 참조(711, 753, 794행)는 존재하지 않는 속성 → 죽은 코드. `self.ticker`는 `yf.Ticker` 객체(str 아님).
- `check_buffett_criteria_at_date(672-738)`: 한국이면 현재 시점 fetcher 사용(682-702, as_of_date 무시), `applicable_quarter is None → return True`(704-708), fallback은 `ticker.info` 현재값(722-731).
- `check_lynch(740-784)`: 데이터 없으면 True(746-750, 784). `check_graham(786-821)`: 없으면 False. `check_oneil(823-835)`: 없으면 False, DART 경로 없음.
- 호출자: `master_strategies.py`의 generate_signals가 **모든 봉마다** `check_*_at_date(date)` 호출 (Buffett 106, Lynch 181, Graham 256, ONeil 644행). analyzer 인스턴스 캐시 덕에 네트워크는 1회지만 모든 날짜가 같은 "현재" 값으로 판정됨.
- `dart_api.py`: `get_financial_statement(corp_code, year, report_type)`(185행, reprt_code: 11013=1Q, 11012=반기, 11014=3Q, 11011=사업보고서)로 연도·분기별 원자료 조회 가능. `get_metrics_at_date`(376행)는 월→분기 하드코딩 매핑, 반환 키 대문자. 공시일(rcept_dt) 조회 코드 없음 — 45일 지연 근사 사용.
- `korean_stock_data.py`: 삼성 하드코딩 `_enhance_samsung_data`(239-272), 호출 지점은 358-359행 한 곳. Lynch 성장률 fabrication(446-455), Graham `current_ratio` 기본값 1.5(472행).
- `backtest.py`: 체결가 함수 `_execute_entry_price/_execute_exit_price`(475-483), 생성자에 `is_korean_stock` 플래그 존재(52-55). 부분 익절은 이미 `_execute_exit_price` 경유(407행) — 슬리피지 반영됨, 추가 수리 불필요.
- 몬테카를로: routes.py `/analyze`의 150-159행 한 곳에서만 호출. **프론트 `ResultsDisplay.tsx:12`는 monte_carlo를 구조분해만 하고 렌더링 0건** — 계산 제거해도 UI 무영향. `schemas.py:140-145` MonteCarloResult, AnalysisResponse.monte_carlo.
- Chanos: `master_strategies.py:1050-1062` MASTER_STRATEGIES dict 등록, `schemas.py:82` Literal에 "chanos", 프론트는 `GET /master-strategies` 목록을 그대로 렌더링(MasterStrategySelector.tsx:53-56, 99행) → 서버에서 빼면 UI에서 사라짐.
- 테스트: fundamental 관련 자동화 테스트 전무 — 이 계획에서 신설.

---

### Task 1: fabrication 제거 (korean_stock_data.py)

**Files:**
- Modify: `backend/app/services/korean_stock_data.py` (239-272행 `_enhance_samsung_data` 삭제, 358-359행 호출 삭제, 446-455행 Lynch 성장률 fabrication 제거, 472행 Graham current_ratio 기본값 제거)
- Test: `backend/tests/unit/test_no_fabrication.py`

**Interfaces:**
- Produces: `get_lynch_metrics(symbol)` — 성장률 데이터가 없으면 `earnings_growth: None, PEG: None` (0.10 기본값·ROE proxy 금지). `get_graham_metrics(symbol)` — current_ratio 없으면 `None` (1.5 금지). 반환 dict 키 이름은 유지.
- 소비자(`fundamental_analysis.py`의 현재-시점 경로, 조건 체크 UI)는 이미 None 처리 분기 보유 — 키 유지가 계약.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_no_fabrication.py`:

```python
"""데이터 조작(fabrication) 제거 검증 — 없는 데이터는 None이어야 한다"""
from unittest.mock import patch, MagicMock

from app.services.korean_stock_data import KoreanStockDataFetcher


def _fetcher_with_metrics(metrics):
    fetcher = KoreanStockDataFetcher()
    with patch.object(fetcher, "get_stock_data", return_value=metrics):
        yield_metrics_lynch = fetcher.get_lynch_metrics("005930.KS")
        yield_metrics_graham = fetcher.get_graham_metrics("005930.KS")
    return yield_metrics_lynch, yield_metrics_graham


def test_lynch_growth_is_none_without_data():
    lynch, _ = _fetcher_with_metrics({"PE": 10.0, "ROE": 8.4})
    assert lynch["earnings_growth"] is None  # ROE proxy·기본값 0.10 금지
    assert lynch["PEG"] is None


def test_graham_current_ratio_is_none_without_data():
    _, graham = _fetcher_with_metrics({"PB": 1.2, "PE": 10.0})
    assert graham["current_ratio"] is None  # 기본값 1.5 금지


def test_samsung_hardcode_removed():
    import inspect
    from app.services import korean_stock_data
    src = inspect.getsource(korean_stock_data)
    assert "_enhance_samsung_data" not in src
    assert "0.084" not in src  # 하드코딩 ROE 잔재 금지
```

주의: `_fetcher_with_metrics`의 mock 대상 메서드명(`get_stock_data`)은 실제 `get_lynch_metrics`/`get_graham_metrics`가 내부에서 지표 dict를 얻는 메서드를 확인 후 그 이름으로 조정하라 (435-474행 참조).

- [ ] **Step 2: 실패 확인** — `venv\Scripts\python -m pytest tests/unit/test_no_fabrication.py -v` → FAIL (기본값 반환 또는 `_enhance_samsung_data` 존재)
- [ ] **Step 3: 구현** — 삭제 위주: `_enhance_samsung_data` 메서드와 호출부 삭제, Lynch에서 `earnings_growth`는 실제 데이터가 있을 때만 계산(DART `calculate_growth_rate` 결과 또는 yfinance 값), 없으면 None; PEG는 PE와 earnings_growth 둘 다 있을 때만 계산; Graham current_ratio는 실측 없으면 None. 삭제로 참조가 끊기는 코드가 있으면 함께 정리하되 파일 밖으로 확산 금지.
- [ ] **Step 4: 통과 확인** — 전체 `tests/unit` 회귀 포함
- [ ] **Step 5: 커밋** — `fix: 재무 지표 fabrication 제거 (삼성 하드코딩·성장률 기본값·current_ratio 기본값)`

---

### Task 2: point-in-time 지표 수집기 (pit_fundamentals.py)

**Files:**
- Create: `backend/app/services/pit_fundamentals.py`
- Test: `backend/tests/unit/test_pit_fundamentals.py`

**Interfaces:**
- Produces:
```python
@dataclass
class QuarterMetrics:
    quarter_end: pd.Timestamp      # 분기말
    available_from: pd.Timestamp   # 분기말 + EARNINGS_DELAY_DAYS(45일) — 이 날짜부터 사용 가능
    eps: float | None              # 분기 EPS (연환산 아님)
    bps: float | None
    roe: float | None              # 연환산: 분기 순이익*4 / 자본
    debt_to_equity: float | None
    net_income: float | None       # 분기 순이익 (성장률 계산용)
    current_ratio: float | None

class PointInTimeFundamentals:
    def __init__(self, symbol: str, quarters: list[QuarterMetrics]):
        # quarters는 quarter_end 오름차순 정렬 저장
    def metrics_at(self, as_of: pd.Timestamp) -> QuarterMetrics | None:
        # available_from <= as_of 인 가장 최근 분기. 없으면 None (look-ahead 방지의 핵심)
    def yoy_net_income_growth_at(self, as_of: pd.Timestamp) -> float | None:
        # metrics_at 분기와 그 4분기 전(같은 분기말 월·일 기준 약 1년 전) 비교.
        # 둘 다 있고 전년 분기 net_income > 0 일 때만 (증가율); 아니면 None
    def coverage(self) -> tuple[pd.Timestamp, pd.Timestamp] | None:
        # (첫 분기 available_from, 마지막 분기 quarter_end + 1분기) — 검증 가능 구간 표시용
    def pe_at(self, as_of, price) -> float | None    # price / (eps*4), eps>0일 때만
    def pb_at(self, as_of, price) -> float | None    # price / bps, bps>0일 때만

def build_korean_pit(stock_code: str, start_year: int, end_year: int) -> PointInTimeFundamentals | None:
    # DartAPI.get_financial_statement(corp_code, year, reprt_code)를 연도×4분기 루프로 조회해
    # QuarterMetrics 목록 구성. corp_code 없거나 전 분기 실패면 None.
def build_us_pit(symbol: str) -> PointInTimeFundamentals | None:
    # yf.Ticker의 quarterly_financials/quarterly_balance_sheet에서 최근 4분기 구성 (그 이전은 커버 불가)
```
- 순수 로직(`metrics_at`, `yoy`, `pe_at`)과 데이터 빌더(`build_*`)를 분리 — 순수 로직은 픽스처로 완전 테스트, 빌더는 DART/yf 호출을 mock.
- Task 3이 이 클래스를 소비한다.

- [ ] **Step 1: 실패하는 테스트 작성** — `test_pit_fundamentals.py` (네트워크 없음, 합성 QuarterMetrics 픽스처):

```python
"""point-in-time 지표 수집기 테스트 — look-ahead 방지의 핵심 계약"""
import pandas as pd
import pytest


def _q(end, eps=100.0, bps=2000.0, roe=0.12, ni=1000.0):
    from app.services.pit_fundamentals import QuarterMetrics
    end = pd.Timestamp(end)
    return QuarterMetrics(
        quarter_end=end, available_from=end + pd.Timedelta(days=45),
        eps=eps, bps=bps, roe=roe, debt_to_equity=0.3,
        net_income=ni, current_ratio=2.0,
    )


@pytest.fixture
def pit():
    from app.services.pit_fundamentals import PointInTimeFundamentals
    quarters = [
        _q("2023-03-31", ni=800.0), _q("2023-06-30", ni=900.0),
        _q("2023-09-30", ni=950.0), _q("2023-12-31", ni=1000.0),
        _q("2024-03-31", ni=1200.0),
    ]
    return PointInTimeFundamentals("005930.KS", quarters)


def test_lookahead_guard_before_disclosure(pit):
    # 2024-03-31 분기는 5/15(45일 후)부터만 사용 가능 — 4/30 시점엔 직전 분기여야 함
    m = pit.metrics_at(pd.Timestamp("2024-04-30"))
    assert m.quarter_end == pd.Timestamp("2023-12-31")  # look-ahead면 2024-03-31이 나옴 → 실패


def test_no_data_before_first_disclosure(pit):
    assert pit.metrics_at(pd.Timestamp("2023-04-01")) is None  # 첫 공시(5/15) 전


def test_yoy_growth_uses_same_quarter_prev_year(pit):
    # 2024-06-01 시점: 최신=2024-03-31(ni 1200), 전년 동분기=2023-03-31(ni 800) → +50%
    g = pit.yoy_net_income_growth_at(pd.Timestamp("2024-06-01"))
    assert g == pytest.approx(0.5)


def test_yoy_none_when_prev_year_missing(pit):
    # 2023-08-01 시점: 최신=2023-03-31, 전년 분기 없음 → None (fabrication 금지)
    assert pit.yoy_net_income_growth_at(pd.Timestamp("2023-08-01")) is None


def test_pe_pb_at(pit):
    d = pd.Timestamp("2024-06-01")
    assert pit.pe_at(d, price=48000.0) == pytest.approx(48000.0 / (100.0 * 4))
    assert pit.pb_at(d, price=48000.0) == pytest.approx(48000.0 / 2000.0)
    assert pit.pe_at(pd.Timestamp("2023-04-01"), price=100.0) is None
```

- [ ] **Step 2: 실패 확인** → ModuleNotFoundError
- [ ] **Step 3: 구현** — 위 인터페이스대로. `build_korean_pit`: `DartAPI.get_financial_statement`의 계정과목에서 당기순이익·자본총계·부채총계·유동자산·유동부채를 추출(계정명은 `fnlttSinglAcntAll` 표준 계정 `account_nm` 기준 — "당기순이익", "자본총계", "부채총계", "유동자산", "유동부채"; 분기 손익은 누적치이므로 **직전 분기 누적을 빼서 분기 단독치 산출** — 사업보고서(11011)는 연간). 발행주식수는 `dart_api.get_metrics_at_date`가 쓰는 `stockTotqySttus.json` 로직 재사용. 실패한 분기는 건너뛰고 로그. `build_us_pit`: `ticker.quarterly_financials`("Net Income" 행)·`quarterly_balance_sheet`("Stockholders Equity", "Total Liabilities...", "Current Assets", "Current Liabilities")에서 구성, 주식수는 `info.get('sharesOutstanding')` 1회.
- [ ] **Step 4: 통과 확인** — 순수 로직 6개 테스트. 빌더는 이 태스크에서 단위 테스트 강제하지 않음(다음 태스크 mock + Task 7 스모크에서 검증).
- [ ] **Step 5: 커밋** — `feat: point-in-time 재무 지표 수집기 추가 (공시 지연 반영, look-ahead 차단)`

---

### Task 3: check_*_criteria_at_date 재작성 (look-ahead 제거)

**Files:**
- Modify: `backend/app/services/fundamental_analysis.py` (672-835행의 4개 함수 교체 + pit 인스턴스 캐시 추가; 죽은 `self.dart_client` 경로 삭제)
- Test: `backend/tests/unit/test_criteria_at_date.py`

**Interfaces:**
- Consumes: `PointInTimeFundamentals` (Task 2)
- Produces: 시그니처 유지 — `check_buffett_criteria_at_date(as_of_date) -> bool` 등 4개 (호출자 master_strategies.py 무변경). 추가로 `fundamental_coverage() -> tuple[str, str] | None` (Task 4가 응답 노출에 사용).
- 새 판정 규칙 (조건은 기존 전략 정의 유지, 데이터 출처만 교체):
  - 내부에서 `self._pit`(최초 1회 build: 한국 → `build_korean_pit(stock_code, 백테스트 시작연도-1, 현재연도)`, 미국 → `build_us_pit`) 캐시. build 실패/None → 모든 날짜 False + logger.warning 1회.
  - `m = self._pit.metrics_at(as_of_date)`; `m is None → False` (기존 "True 통과" 전면 폐지).
  - Buffett: `m.roe > 0.15 and m.debt_to_equity < 0.5 and 0 < pe_at < 25 and pb_at < 3` — pe/pb 계산에 쓸 가격은 `as_of_date`의 주가가 필요하므로 시그니처를 `check_*_criteria_at_date(as_of_date, price: float | None = None)`로 확장(기본 None이면 가격 조건 스킵이 아니라 **PE/PB 조건은 판정 불가 → False**). 호출자 수정: master_strategies.py의 4개 루프에서 `price_data.loc[date, 'close']`를 전달.
  - Lynch: `growth = yoy_net_income_growth_at`; `growth is None → False`; `peg = pe_at / (growth*100)`; `0 < peg < 1.0 and growth > 0.20`.
  - Graham: `pb_at < 0.67 and m.current_ratio > 2.0` (둘 중 하나라도 None → False).
  - O'Neil: `growth > 0.25` (None → False).
  - FCF 조건(기존 Buffett)은 point-in-time 산출 불가 → 조건에서 제외하고 함수 docstring과 Task 4의 응답 warning에 "FCF 조건은 시점별 데이터 부재로 미적용" 명시.
- 호출자 수정 파일: `backend/app/services/master_strategies.py` 106-107, 181-182, 256-257, 644-645행 (price 인자 추가만).

- [ ] **Step 1: 실패하는 테스트 작성** — `test_criteria_at_date.py`: `FundamentalAnalyzer` 인스턴스를 만들고 `_pit`에 Task 2 픽스처를 직접 주입해 네트워크 차단:

```python
"""look-ahead 가드 회귀 테스트 — 공시 전 날짜에 그 분기 재무로 매수 판정이 나오면 실패"""
import pandas as pd
import pytest

# _q, 픽스처는 test_pit_fundamentals.py의 것을 conftest.py로 옮겨 공유하라


def _analyzer_with_pit(pit):
    from app.services.fundamental_analysis import FundamentalAnalyzer
    analyzer = FundamentalAnalyzer.__new__(FundamentalAnalyzer)  # __init__(네트워크) 우회
    analyzer.symbol = "005930.KS"
    analyzer.is_korean = True
    analyzer._pit = pit
    return analyzer


def test_no_pass_before_first_disclosure(good_pit):
    a = _analyzer_with_pit(good_pit)
    assert a.check_buffett_criteria_at_date(pd.Timestamp("2023-04-01"), price=10000.0) is False


def test_pass_after_disclosure_when_criteria_met(good_pit):
    a = _analyzer_with_pit(good_pit)
    # good_pit: roe 0.20, d/e 0.3, eps 100(연환산 400), bps 2000 → price 6000: PE 15, PB 3 미만
    assert a.check_buffett_criteria_at_date(pd.Timestamp("2024-06-01"), price=6000.0) is True


def test_missing_price_fails_not_passes(good_pit):
    a = _analyzer_with_pit(good_pit)
    assert a.check_buffett_criteria_at_date(pd.Timestamp("2024-06-01"), price=None) is False


def test_lynch_requires_real_growth(good_pit):
    a = _analyzer_with_pit(good_pit)
    # 전년 동분기 없는 시점 → growth None → False (기존엔 True로 통과했음)
    assert a.check_lynch_criteria_at_date(pd.Timestamp("2023-08-01"), price=1000.0) is False
```

(good_pit 픽스처는 roe 0.20으로 구성. 필요한 추가 케이스 — graham current_ratio None → False, oneil growth 경계 — 를 포함해 총 8개 이상.)

- [ ] **Step 2: 실패 확인** (기존 구현은 데이터 없으면 True → test_no_pass_before_first_disclosure FAIL)
- [ ] **Step 3: 구현** — 4개 함수 교체 + 죽은 DART 경로(711-721, 753-762, 794-803행) 삭제 + master_strategies.py 호출부 price 전달. 한국 현재-시점 분기(682-702행의 fetcher 경로)도 삭제 — at_date 경로는 pit만 사용.
- [ ] **Step 4: 통과 확인** — 신규 + 전체 회귀
- [ ] **Step 5: 커밋** — `fix: 시점별 펀더멘털 판정을 point-in-time 데이터로 교체 (look-ahead 제거)`

---

### Task 4: 검증 가능 구간 응답 노출

**Files:**
- Modify: `backend/app/api/routes.py` (`/master-strategy` 핸들러 — generate_signals 이후 warnings 조립부)
- Modify: `backend/app/services/master_strategies.py` (전략이 사용한 analyzer의 coverage를 결과에 포함할 수 있도록 generate_signals 반환에 부가정보 또는 전략 인스턴스 속성 `last_fundamental_coverage` 저장 — 기존 반환 시그니처 `(entry_signals, exit_signals)` 유지 우선, 속성 방식 권장)
- Test: `backend/tests/unit/test_coverage_warning.py`

**Interfaces:**
- Produces: `/master-strategy` 응답의 기존 `warnings: List[str]`에 다음 형식 문자열 추가 — `"펀더멘털 검증 가능 구간: 2023-05-15 ~ 2026-07-03 (이전 구간은 매수 신호 없음)"` 또는 coverage None이면 `"펀더멘털 시점별 데이터 없음 — 이 백테스트는 매수 신호가 생성되지 않았습니다"`. Buffett/Lynch/Graham/O'Neil 4개 전략에만 해당.

- [ ] **Step 1: 실패하는 테스트** — 전략 인스턴스에 mock analyzer(coverage 반환)를 주입해 `last_fundamental_coverage` 속성이 설정되는지 + warnings 조립 헬퍼가 올바른 문자열을 만드는지 검증 (routes 핸들러 전체 호출은 스모크로 미룸; warnings 조립 로직을 `master_strategies.py`의 모듈 함수 `format_coverage_warning(coverage) -> str`로 분리해 그 함수를 단위 테스트)
- [ ] **Step 2: 실패 확인** → ImportError
- [ ] **Step 3: 구현** — `format_coverage_warning` + 전략 4개의 generate_signals에서 `self.last_fundamental_coverage = analyzer.fundamental_coverage()` 저장 + routes.py에서 해당 전략일 때 warnings.append.
- [ ] **Step 4: 통과 확인** — 신규 + 회귀
- [ ] **Step 5: 커밋** — `feat: 백테스트 응답에 펀더멘털 검증 가능 구간 표시`

---

### Task 5: 한국 매도 거래세

**Files:**
- Modify: `backend/app/models/schemas.py` (50-54행 SimulateParams에 `sell_tax_bps: int = Field(default=18, ge=0, le=100)` 추가 — schemas 위치는 실제 파일 경로 확인)
- Modify: `backend/app/services/backtest.py` (생성자에 `sell_tax_bps: int = 18` 추가, `_execute_exit_price`에서 한국 종목일 때만 `adjusted *= (1 - self.sell_tax)` 추가)
- Modify: `backend/app/api/routes.py` (`/master-strategy` 427행 부근과 `/analyze` 103-110행 부근의 BacktestEngine 생성에 `sell_tax_bps=request.simulate.sell_tax_bps` 전달. **주의: `/analyze` 경로는 현재 `is_korean_stock`도 전달하지 않음(기본 False) — routes.py 380-382행의 판별 로직을 `/analyze`에도 적용해 함께 전달하라. 이것은 이번 태스크 범위다.**)
- Test: `backend/tests/unit/test_sell_tax.py`

**Interfaces:**
- Produces: `BacktestEngine(..., sell_tax_bps: int = 18)`. `_execute_exit_price(price)` = `price * (1 - slippage) * (1 - cost) * (1 - sell_tax if is_korean_stock else 1)` 후 tick 내림. 매수는 무변경.

- [ ] **Step 1: 실패하는 테스트** — `test_sell_tax.py`:

```python
"""한국 매도 거래세 반영 테스트"""
import pandas as pd
import pytest


def _engine(is_korean, sell_tax_bps=18):
    from app.services.backtest import BacktestEngine
    idx = pd.date_range("2024-01-01", periods=10)
    data = pd.DataFrame({"open": 10000.0, "high": 10000.0, "low": 10000.0,
                         "close": 10000.0, "volume": 1000}, index=idx)
    sig = pd.Series(False, index=idx)
    return BacktestEngine(data, sig, sig.copy(),
                          {"stop_loss_pct": 0.1, "take_profit_pct": 0.2},
                          is_korean_stock=is_korean, sell_tax_bps=sell_tax_bps)


def test_korean_exit_price_includes_tax():
    kr = _engine(True)
    us = _engine(False)
    assert kr._execute_exit_price(10000.0) < us._execute_exit_price(10000.0)


def test_tax_amount_is_18bps():
    kr0 = _engine(True, sell_tax_bps=0)
    kr18 = _engine(True, sell_tax_bps=18)
    # 세금 0bp 대비 18bp만큼 낮아야 함 (tick 내림 전 기준 0.18%)
    assert kr18._execute_exit_price(100000.0) <= kr0._execute_exit_price(100000.0) * (1 - 0.0018) + 100
```

주의: BacktestEngine 생성자의 실제 positional/keyword 시그니처(27-37행)를 확인하고 테스트의 생성 인자를 맞춰라.

- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀**
- [ ] **Step 5: 커밋** — `feat: 한국 주식 매도 거래세(기본 18bp) 백테스트 반영`

---

### Task 6: 몬테카를로 비활성화 + Chanos 미등록

**Files:**
- Modify: `backend/app/api/routes.py` (150-159행 MonteCarloSimulator 호출 삭제, 202행 `monte_carlo=None` 전달)
- Modify: `backend/app/models/schemas.py` (AnalysisResponse.monte_carlo를 `Optional[MonteCarloResult] = None`으로; 82행 Literal에서 "chanos" 제거)
- Modify: `backend/app/services/master_strategies.py` (1050-1062행 dict에서 `"chanos"` 항목 제거 — 클래스 코드는 유지하고 dict 위에 `# TODO: 숏 엔진 구현 전까지 비활성화 (backtest.py에 숏 로직 없음 — 롱으로 체결되는 결함)` 주석)
- Modify: `frontend/src/components/ResultsDisplay.tsx` (12행 구조분해에서 monte_carlo 제거 — 미사용이므로 1줄)
- Test: `backend/tests/unit/test_disabled_features.py`

**Interfaces:**
- Produces: `/analyze` 응답 `monte_carlo: null`. `GET /master-strategies` 목록에 chanos 부재. `/master-strategy`에 strategy_name="chanos" 요청 시 422 (Literal 검증).

- [ ] **Step 1: 실패하는 테스트**:

```python
"""깨진 기능 비활성화 검증 — 허수 신뢰구간과 롱 체결 공매도 전략 차단"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_chanos_not_in_strategy_list():
    res = client.get("/api/v1/master-strategies")
    assert res.status_code == 200
    names = [s.get("name") or s.get("id") for s in res.json().get("strategies", res.json())]
    assert "chanos" not in str(names).lower()


def test_chanos_request_rejected():
    res = client.post("/api/v1/master-strategy", json={
        "strategy_name": "chanos", "symbol": "AAPL",
        "start_date": "2024-01-01", "end_date": "2024-06-01",
    })
    assert res.status_code == 422
```

주의: `/master-strategies` 응답의 실제 구조(routes.py 920-933행 `list_strategies()`)를 확인해 파싱을 맞춰라. `/analyze`의 monte_carlo=null 검증은 네트워크(yfinance) 필요라 단위 테스트 제외 — Task 7 스모크에서 확인.

- [ ] **Step 2-4: RED → 구현 → GREEN + 회귀** (프론트는 `cd frontend; npm run build`로 타입 확인)
- [ ] **Step 5: 커밋** — `fix: 몬테카를로 비활성화(시그널 정렬 결함) 및 Chanos 전략 미등록(숏 미지원)`

---

### Task 7: 스모크 테스트 (실데이터 E2E)

**Files:** 없음 (검증만; 네트워크 사용 — DART 키는 backend/.env에 존재)

- [ ] **Step 1**: 서버 기동 후 `POST /api/v1/master-strategy` `{"strategy_name":"buffett","symbol":"005930.KS","start_date":"2023-01-01","end_date":"2024-12-31"}` → 200, 응답 warnings에 "펀더멘털 검증 가능 구간" 문자열 존재, condition_checks 정상.
- [ ] **Step 2**: 같은 요청을 미국 주식 AAPL로 → 200, coverage가 최근 4분기 창으로 제한됨을 warnings에서 확인 (오래된 start_date 구간은 매수 신호 없어야 함 — trades의 첫 진입일이 coverage 시작 이후인지 확인).
- [ ] **Step 3**: `GET /api/v1/master-strategies`에 chanos 없음, `/analyze` 1회 호출로 `monte_carlo: null` 확인.
- [ ] **Step 4**: 문제 발견 시 stop-the-line — 해당 태스크로 복귀. 통과 시 결과를 보고서로 기록.

---

## Self-Review 결과

- **Spec coverage**: 스펙 5.1의 5개 항목(시점별 재무·버그 수정 / 무조건 통과 폐지·구간 표시 / 거래세·부분익절 / 하드코딩 제거 / MC·Chanos 숨김) 전부 태스크 매핑됨. 부분 익절 슬리피지는 사실 수집 결과 이미 반영돼 있어 태스크 불필요(근거: backtest.py 407행 `_execute_exit_price` 경유).
- **Placeholder scan**: 통과 — 각 태스크에 실제 테스트 코드와 구현 지시 포함. Task 2 빌더와 Task 4 warnings 조립은 구현자 확인 지점을 명시.
- **Type consistency**: `QuarterMetrics`/`metrics_at`/`pe_at` 시그니처가 Task 2↔3 간 일치. `check_*_at_date(as_of_date, price=None)` 확장은 Task 3에서 정의하고 호출자 수정 포함.
- **알려진 리스크**: DART `fnlttSinglAcntAll` 계정명이 기업/연도별로 상이할 수 있음(연결 vs 별도, IFRS 계정명 변형) — Task 2 구현자는 실제 응답 1건을 확인하고 계정명 매칭을 유연하게(포함 검색) 구현하라. Task 7 스모크가 최종 안전망.

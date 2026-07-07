"""일별 추천 엔진.

pykrx로 KOSPI/KOSDAQ 시가총액 상위 종목을 유니버스로 뽑고, 펀더멘털 필터
(PER/PBR/ROE 3개 중 2개 이상 통과)와 기술 시그널(골든크로스·RSI 반등·52주
신고가 근접)을 적용해 점수화한 뒤 상위 top_k를 저장소에 근거와 함께 남긴다.

설계 원칙:
- 단순·설명 가능 우선(근거 없는 가중치 금지).
- fabrication 금지: 값이 None/데이터 부족이면 passed=False + 사유 문자열.
- 조건/시그널 dict는 프론트 조건 체크 UI와 키가 일치(ConditionCheck).
- pykrx 실호출은 build_universe/_fetch_ohlcv에만 격리 — 순수 로직은 테스트 가능.
"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

import pandas as pd

# pykrx는 임포트 시점에 KRX 로그인(네트워크)을 시도한다 — 실패해도 앱은 떠야 함
# (stock=None이면 호출부 try/except의 AttributeError로 네이버 폴백 경로 동작)
try:
    from pykrx import stock
except Exception as _pykrx_exc:  # noqa: BLE001
    stock = None
    logging.getLogger(__name__).warning("pykrx 임포트 실패(네트워크/SSL 추정): %s", _pykrx_exc)

from app.services import naver_market

logger = logging.getLogger(__name__)

# 펀더멘털 임계값
_PER_MAX = 25.0
_PBR_MAX = 3.0
_ROE_MIN = 0.10

# 점수 배분: 펀더멘털 60점(3개), 기술 40점(3개)
_FUND_POINT = 20.0          # 펀더멘털 통과 1개당
_SIG_POINT = (100.0 - 60.0) / 3.0  # 기술 시그널 통과 1개당 (≈13.333)

# 기술 판정 최소 데이터 길이(252일 최고가 + 여유)
_MIN_ROWS = 260


@dataclass
class Candidate:
    symbol: str
    name: str
    close: float
    per: float | None
    pbr: float | None
    roe: float | None  # eps/bps (소수, 0.15 = 15%)
    market_cap: float | None


# ── 조건 dict 헬퍼 (ConditionCheck 키와 일치) ─────────────────────
def _cond(name: str, name_en: str, required: str,
          actual: str, passed: bool) -> dict:
    return {
        "condition_name": name,
        "condition_name_en": name_en,
        "required_value": required,
        "actual_value": actual,
        "passed": passed,
    }


# ── 유니버스 구성 (pykrx) ─────────────────────────────────────────
def _latest_business_date(date: str | None = None) -> str | None:
    """오늘(또는 지정일)부터 최대 7일 역방향으로 데이터가 존재하는 영업일을 찾는다.

    pykrx는 휴장일에 빈 DF 또는 0값 DF를 줄 수 있으므로 시가총액 합으로 판정한다.
    """
    base = datetime.strptime(date, "%Y%m%d") if date else datetime.now()
    for delta in range(7):
        d = (base - timedelta(days=delta)).strftime("%Y%m%d")
        try:
            df = stock.get_market_cap_by_ticker(d, market="KOSPI")
        except Exception as exc:  # 네트워크/pykrx 실패
            logger.warning("get_market_cap_by_ticker(%s) 실패: %s", d, exc)
            continue
        if not (df.empty or df["시가총액"].sum() == 0):
            return d
    return None


def _merge_fundamental(cap_df: pd.DataFrame, date_str: str,
                       market: str) -> pd.DataFrame:
    """시가총액 DF에 PER/PBR/EPS/BPS를 병합해 반환(인덱스=티커)."""
    fund = stock.get_market_fundamental_by_ticker(date_str, market=market)
    return cap_df.join(fund[["PER", "PBR", "EPS", "BPS"]], how="left")


def build_universe(
    top_n: int = 300, date: str | None = None, meta: dict | None = None
) -> list[Candidate]:
    """KOSPI+KOSDAQ 시가총액 상위 top_n 종목을 Candidate 리스트로 반환.

    경로 우선순위:
    1. KRX(pykrx) — 자격증명이 있으면 우선 사용(PER/PBR/ROE 전부 제공).
    2. KRX가 비면(2026 로그인 정책·네트워크 실패 등) 네이버 금융 시총 페이지 폴백.

    폴백(네이버) 특성:
    - 네이버 기본 시총 페이지에는 **PBR이 없어** Candidate.pbr=None이 된다.
      → fundamental_filter의 PBR 조건은 '데이터 없음'으로 passed=False가 되므로,
        2/3 통과 규칙상 폴백 종목은 PER·ROE 두 조건을 모두 통과해야 필터를 통과한다.
    - 폴백 데이터는 "현재 시점" 스냅샷이다 — rec_date가 과거인 재생성 시 부정확할 수 있다.

    symbol 형식: 두 경로 모두 접미사 포함("005930.KS"/"035720.KQ")으로 통일 — 앱 표준
    (paper_positions·news_stock_links와 일치). OHLCV 조회(_fetch_ohlcv)는 접미사를
    제거한 6자리 코드로 pykrx를 호출하므로 폴백 경로에서도 기술 시그널이 산출된다
    (pykrx 종목별 get_market_ohlcv는 로그인 불필요 — 실증 확인).

    meta(dict)가 주어지면 "universe_source" 키에 실제 사용 경로를 기록한다
    ("krx" | "naver_fallback" | "empty").
    """
    krx = _build_universe_krx(top_n, date)
    if krx:
        if meta is not None:
            meta["universe_source"] = "krx"
        return krx

    logger.info("build_universe: KRX 유니버스 비어있음 → 네이버 시총 폴백 시도")
    naver = _build_universe_naver(top_n, date)
    if meta is not None:
        meta["universe_source"] = "naver_fallback" if naver else "empty"
    return naver


# 시장별 yfinance 접미사 — 앱 표준 심볼 형식(paper_positions·news_stock_links와 일치)
_MARKET_SUFFIX = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}


def _build_universe_krx(top_n: int, date: str | None) -> list[Candidate]:
    """KRX(pykrx) 경로. 실패(영업일 미발견/예외/빈 결과) 시 빈 리스트 + warning.

    Candidate.symbol은 앱 표준인 접미사 포함 형식("005930.KS")으로 통일한다
    (네이버 폴백 경로와 recommendations.symbol 키 일관성).
    """
    date_str = _latest_business_date(date)
    if date_str is None:
        logger.warning("build_universe: 최근 영업일을 찾지 못해 KRX 유니버스 비어있음")
        return []

    try:
        frames = []
        for market in ("KOSPI", "KOSDAQ"):
            cap = stock.get_market_cap_by_ticker(date_str, market=market)
            if cap.empty or cap["시가총액"].sum() == 0:
                continue
            frame = _merge_fundamental(cap, date_str, market)
            # concat 후에도 시장 구분을 잃지 않도록 접미사 컬럼을 부착
            frame = frame.assign(_suffix=_MARKET_SUFFIX[market])
            frames.append(frame)
        if not frames:
            return []
        merged = pd.concat(frames)
    except Exception as exc:
        logger.warning("build_universe(KRX) 실패, 빈 유니버스 반환: %s", exc)
        return []

    merged = merged.sort_values("시가총액", ascending=False).head(top_n)

    candidates: list[Candidate] = []
    for ticker, row in merged.iterrows():
        eps = _to_float(row.get("EPS"))
        bps = _to_float(row.get("BPS"))
        # 자본잠식(BPS≤0)에서는 ROE 계산 금지 — 계약: bps>0일 때만
        roe = eps / bps if (eps is not None and bps is not None and bps > 0) else None
        candidates.append(
            Candidate(
                symbol=f"{ticker}{row.get('_suffix', '.KS')}",
                name=stock.get_market_ticker_name(ticker) or str(ticker),
                close=_to_float(row.get("종가")) or 0.0,
                per=_positive_or_none(_to_float(row.get("PER"))),
                pbr=_positive_or_none(_to_float(row.get("PBR"))),
                roe=roe,
                market_cap=_to_float(row.get("시가총액")),
            )
        )
    return candidates


def _build_universe_naver(top_n: int, date: str | None) -> list[Candidate]:
    """네이버 금융 시총 페이지 폴백 경로. 실패 시 빈 리스트.

    PBR은 페이지에 없어 None. 시총 내림차순 상위 top_n으로 절삭한다.
    rec_date가 오늘이 아니면(과거 재생성) 스냅샷 부정확 가능성을 warning.
    """
    try:
        rows = naver_market.fetch_market_sum()
    except Exception as exc:  # 방어적 — fetch 내부에서 이미 페이지별 예외 처리
        logger.warning("build_universe(네이버) 실패, 빈 유니버스 반환: %s", exc)
        return []
    if not rows:
        logger.warning("build_universe: 네이버 폴백도 0건 — 빈 유니버스 반환")
        return []

    today = datetime.now().strftime("%Y%m%d")
    if date is not None and _to_yyyymmdd(date) != today:
        logger.warning(
            "네이버 폴백은 현재 시점 스냅샷 — rec_date(%s)가 과거이면 부정확할 수 있음", date
        )

    rows.sort(key=lambda r: r.market_cap or 0.0, reverse=True)
    logger.info("build_universe: 네이버 폴백 %d종목 → 상위 %d 사용", len(rows), top_n)
    return [
        Candidate(
            symbol=r.symbol,
            name=r.name,
            close=r.close or 0.0,
            per=r.per,
            pbr=None,  # 네이버 기본 페이지 미제공
            roe=r.roe,
            market_cap=r.market_cap,
        )
        for r in rows[:top_n]
    ]


def _to_float(value) -> float | None:
    """숫자 변환, NaN/None은 None."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(f) else f


def _positive_or_none(value: float | None) -> float | None:
    """0 이하(pykrx는 적자·미산정 시 0)를 None으로 취급."""
    if value is None or value <= 0:
        return None
    return value


# ── 펀더멘털 필터 ─────────────────────────────────────────────────
def fundamental_filter(
    cands: list[Candidate],
) -> list[tuple[Candidate, list[dict]]]:
    """PER/PBR/ROE 3개 중 2개 이상 통과한 후보만 조건 근거와 함께 반환."""
    result: list[tuple[Candidate, list[dict]]] = []
    for cand in cands:
        conds = [
            _range_cond("PER 25 미만", "PER", "0 < PER < 25", cand.per,
                        lambda v: 0 < v < _PER_MAX),
            _range_cond("PBR 3 미만", "PBR", "0 < PBR < 3", cand.pbr,
                        lambda v: 0 < v < _PBR_MAX),
            _range_cond("ROE 10% 초과", "ROE", "ROE > 10%", cand.roe,
                        lambda v: v > _ROE_MIN, is_pct=True),
        ]
        if sum(1 for c in conds if c["passed"]) >= 2:
            result.append((cand, conds))
    return result


def _range_cond(name: str, name_en: str, required: str,
                value: float | None, ok, is_pct: bool = False) -> dict:
    """단일 펀더멘털 조건을 ConditionCheck dict로 판정."""
    if value is None:
        return _cond(name, name_en, required, "데이터 없음", False)
    actual = f"{value * 100:.1f}%" if is_pct else f"{value:.2f}"
    return _cond(name, name_en, required, actual, bool(ok(value)))


# ── 기술 시그널 ───────────────────────────────────────────────────
def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """단순(SMA) RSI. 하락분이 없으면 100."""
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    # loss==0 → rs=inf → rsi=100, gain==loss==0 → NaN → 100(변동 없음)
    return rsi.where(loss != 0, 100.0)


def technical_signals(symbol: str, ohlcv: pd.DataFrame) -> list[dict]:
    """소문자 컬럼 일봉에서 3종 시그널을 ConditionCheck dict 리스트로 반환.

    데이터 부족(260행 미만)이면 세 조건 모두 passed=False + '데이터 부족'.
    """
    if ohlcv is None or len(ohlcv) < _MIN_ROWS:
        return [
            _cond("골든크로스", "GoldenCross", "MA20이 MA60 상향 돌파(최근 5일)",
                  "데이터 부족", False),
            _cond("RSI 반등", "RSIRebound", "RSI(14) 30 미만→30 이상(최근 10일)",
                  "데이터 부족", False),
            _cond("52주 신고가 근접", "NearHigh", "종가 ≥ 252일 최고가의 95%",
                  "데이터 부족", False),
        ]

    close = ohlcv["close"].astype(float).reset_index(drop=True)
    high = ohlcv["high"].astype(float).reset_index(drop=True)

    # 1) 골든크로스: MA20이 MA60을 최근 5일 내 상향 돌파
    ma20 = close.rolling(20).mean()
    ma60 = close.rolling(60).mean()
    above = ma20 > ma60
    crossed = above & ~above.shift(1, fill_value=False)  # 직전 미돌파→돌파 전환
    gc_passed = bool(crossed.iloc[-5:].any())
    gc = _cond("골든크로스", "GoldenCross", "MA20이 MA60 상향 돌파(최근 5일)",
               "돌파" if gc_passed else "없음", gc_passed)

    # 2) RSI 반등: 최근 10일 내 30 미만이었고 현재 30 이상
    rsi = _rsi(close)
    recent = rsi.iloc[-10:]
    rsi_passed = bool((recent < 30).any() and rsi.iloc[-1] >= 30)
    rsi_now = rsi.iloc[-1]
    rsi_actual = "데이터 부족" if pd.isna(rsi_now) else f"현재 {rsi_now:.1f}"
    rsi_cond = _cond("RSI 반등", "RSIRebound",
                     "RSI(14) 30 미만→30 이상(최근 10일)", rsi_actual, rsi_passed)

    # 3) 52주 신고가 근접: 종가 ≥ 252일 최고가의 95%
    high_252 = high.iloc[-252:].max()
    cur = close.iloc[-1]
    near_passed = bool(high_252 > 0 and cur >= high_252 * 0.95)
    ratio = (cur / high_252 * 100) if high_252 > 0 else 0.0
    near = _cond("52주 신고가 근접", "NearHigh", "종가 ≥ 252일 최고가의 95%",
                 f"고점대비 {ratio:.1f}%", near_passed)

    return [gc, rsi_cond, near]


# ── 추세 건전성 게이트 ────────────────────────────────────────────
def trend_gate(ohlcv: pd.DataFrame | None) -> dict:
    """종가 ≥ 200일 이동평균 게이트 — 하락 추세 종목의 추천 진입 차단.

    실측 근거: 하락 추세 역행 매수(지표 역추세·물타기)는 전부 음의 기대값
    (claudedocs/strategy_verification_2026-07-06.md 3차 검증). 펀더멘털이
    좋아도 추세가 무너진 종목(예: 고점 대비 -50%대 하락 중)은 추천 부적격.
    """
    _REQUIRED = "일봉 종가 ≥ 200거래일(약 10개월) 이동평균"
    if ohlcv is None or len(ohlcv) < _MIN_ROWS:
        return _cond("장기 상승 추세(일봉 200일선)", "Trend", _REQUIRED,
                     "데이터 부족", False)
    close = ohlcv["close"].astype(float)
    ma200 = close.rolling(200).mean().iloc[-1]
    cur = close.iloc[-1]
    passed = bool(pd.notna(ma200) and ma200 > 0 and cur >= ma200)
    # 당일 등락 병기 — 장기 추세 판정과 별개로 오늘의 급등락을 숨기지 않는다
    daily_chg = (f" · 당일 {(cur / close.iloc[-2] - 1) * 100:+.1f}%"
                 if len(close) >= 2 and close.iloc[-2] > 0 else "")
    actual = (f"200일선 대비 {(cur / ma200 - 1) * 100:+.1f}%{daily_chg}"
              if pd.notna(ma200) and ma200 > 0 else "데이터 부족")
    return _cond("장기 상승 추세(일봉 200일선)", "Trend", _REQUIRED, actual, passed)


# ── 점수 ──────────────────────────────────────────────────────────
def score(passed_conditions: list[dict], signals: list[dict]) -> float:
    """펀더멘털 통과 1개당 20점(최대 60) + 기술 시그널 1개당 ≈13.3점(최대 40).

    Trend 게이트 조건은 제외 — 생존 종목 전원이 통과라 점수에 넣으면
    일괄 가산만 되고 변별력이 없다 (게이트는 필터, 점수는 순위).
    """
    fund_passed = min(sum(1 for c in passed_conditions if c.get("passed")), 3)
    sig_passed = min(
        sum(1 for s in signals
            if s.get("passed") and s.get("condition_name_en") != "Trend"),
        3,
    )
    total = fund_passed * _FUND_POINT + sig_passed * _SIG_POINT
    return round(total, 1)


# ── OHLCV 조회 (pykrx) ────────────────────────────────────────────
def _fetch_ohlcv(symbol: str, rec_date: str) -> pd.DataFrame:
    """종목의 최근 ~400영업일 일봉을 소문자 컬럼으로 반환. 실패 시 빈 DF.

    symbol은 접미사 포함("005930.KS")·bare("005930") 모두 허용 — pykrx의
    종목별 get_market_ohlcv는 로그인 없이 동작하나 6자리 코드만 받으므로
    접미사를 제거하고 호출한다(네이버 폴백 경로에서도 기술 시그널 산출 가능).
    """
    end = _to_yyyymmdd(rec_date)
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=400)).strftime("%Y%m%d")
    code = symbol.split(".")[0]  # "005930.KS" → "005930"
    try:
        df = stock.get_market_ohlcv(start, end, code)
    except Exception as exc:
        logger.warning("get_market_ohlcv(%s) 실패: %s", symbol, exc)
        return pd.DataFrame()
    return df.rename(
        columns={"시가": "open", "고가": "high", "저가": "low",
                 "종가": "close", "거래량": "volume"}
    )


def _to_yyyymmdd(rec_date: str) -> str:
    """'YYYY-MM-DD' 또는 'YYYYMMDD'를 'YYYYMMDD'로 정규화."""
    return rec_date.replace("-", "")


# ── 오케스트레이션 ────────────────────────────────────────────────
def generate_recommendations(
    repo,
    rec_date: str,
    top_n_universe: int = 300,
    top_k: int = 10,
    max_technical: int = 30,
) -> dict:
    """유니버스→펀더멘털 필터→상위 max_technical개 기술 판정→점수→상위 top_k 저장.

    반환: {"universe": n, "filtered": m, "saved": k, "universe_source": src}
    universe_source: "krx" | "naver_fallback" | "empty" (폴백 사용 여부 추적).
    """
    # rec_date 기준으로 유니버스 구성 — 휴장일 역보정도 이 날짜를 기준으로 동작
    meta: dict = {}
    universe = build_universe(
        top_n=top_n_universe, date=_to_yyyymmdd(rec_date), meta=meta
    )
    filtered = fundamental_filter(universe)

    # 기술 판정 대상 선정: 펀더멘털 통과 수 → 시가총액 순으로 상위 max_technical개
    ranked = sorted(
        filtered,
        key=lambda fc: (
            sum(1 for c in fc[1] if c["passed"]),
            fc[0].market_cap or 0.0,
        ),
        reverse=True,
    )

    scored: list[tuple[Candidate, list[dict], list[dict], float]] = []
    trend_rejected = 0
    for cand, conds in ranked[:max_technical]:
        ohlcv = _fetch_ohlcv(cand.symbol, rec_date)
        gate = trend_gate(ohlcv)
        if not gate["passed"]:
            # 하락 추세(종가 < 200일선) → 점수와 무관하게 추천 제외
            trend_rejected += 1
            time.sleep(0.3)
            continue
        signals = technical_signals(cand.symbol, ohlcv) + [gate]
        scored.append((cand, conds, signals, score(conds, signals)))
        time.sleep(0.3)  # pykrx 요청 간 예의상 딜레이

    scored.sort(key=lambda x: x[3], reverse=True)
    # 재생성 시 옛 추천이 섞이지 않도록 해당일 기존 행 제거 후 저장
    if hasattr(repo, "delete_by_date"):
        repo.delete_by_date(rec_date)
    for cand, conds, signals, sc in scored[:top_k]:
        repo.save(rec_date, cand.symbol, cand.name, sc, conds, signals)

    return {
        "universe": len(universe),
        "filtered": len(filtered),
        "trend_rejected": trend_rejected,
        "saved": min(top_k, len(scored)),
        "universe_source": meta.get("universe_source", "krx"),
    }

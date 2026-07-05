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
from pykrx import stock

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


def build_universe(top_n: int = 300, date: str | None = None) -> list[Candidate]:
    """KOSPI+KOSDAQ 시가총액 상위 top_n 종목을 Candidate 리스트로 반환.

    실패(영업일 미발견/예외) 시 빈 리스트 + warning.
    """
    date_str = _latest_business_date(date)
    if date_str is None:
        logger.warning("build_universe: 최근 영업일을 찾지 못해 빈 유니버스 반환")
        return []

    try:
        frames = []
        for market in ("KOSPI", "KOSDAQ"):
            cap = stock.get_market_cap_by_ticker(date_str, market=market)
            if cap.empty or cap["시가총액"].sum() == 0:
                continue
            frames.append(_merge_fundamental(cap, date_str, market))
        if not frames:
            return []
        merged = pd.concat(frames)
    except Exception as exc:
        logger.warning("build_universe 실패, 빈 유니버스 반환: %s", exc)
        return []

    merged = merged.sort_values("시가총액", ascending=False).head(top_n)

    candidates: list[Candidate] = []
    for ticker, row in merged.iterrows():
        eps = _to_float(row.get("EPS"))
        bps = _to_float(row.get("BPS"))
        roe = eps / bps if (eps is not None and bps not in (None, 0)) else None
        candidates.append(
            Candidate(
                symbol=str(ticker),
                name=stock.get_market_ticker_name(ticker) or str(ticker),
                close=_to_float(row.get("종가")) or 0.0,
                per=_positive_or_none(_to_float(row.get("PER"))),
                pbr=_positive_or_none(_to_float(row.get("PBR"))),
                roe=roe,
                market_cap=_to_float(row.get("시가총액")),
            )
        )
    return candidates


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


# ── 점수 ──────────────────────────────────────────────────────────
def score(passed_conditions: list[dict], signals: list[dict]) -> float:
    """펀더멘털 통과 1개당 20점(최대 60) + 기술 시그널 1개당 ≈13.3점(최대 40)."""
    fund_passed = min(sum(1 for c in passed_conditions if c.get("passed")), 3)
    sig_passed = min(sum(1 for s in signals if s.get("passed")), 3)
    total = fund_passed * _FUND_POINT + sig_passed * _SIG_POINT
    return round(total, 1)


# ── OHLCV 조회 (pykrx) ────────────────────────────────────────────
def _fetch_ohlcv(symbol: str, rec_date: str) -> pd.DataFrame:
    """종목의 최근 ~400영업일 일봉을 소문자 컬럼으로 반환. 실패 시 빈 DF."""
    end = _to_yyyymmdd(rec_date)
    start = (datetime.strptime(end, "%Y%m%d") - timedelta(days=400)).strftime("%Y%m%d")
    try:
        df = stock.get_market_ohlcv(start, end, symbol)
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

    반환: {"universe": n, "filtered": m, "saved": k}
    """
    universe = build_universe(top_n=top_n_universe, date=None)
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
    for cand, conds in ranked[:max_technical]:
        ohlcv = _fetch_ohlcv(cand.symbol, rec_date)
        signals = technical_signals(cand.symbol, ohlcv)
        scored.append((cand, conds, signals, score(conds, signals)))
        time.sleep(0.3)  # pykrx 요청 간 예의상 딜레이

    scored.sort(key=lambda x: x[3], reverse=True)
    for cand, conds, signals, sc in scored[:top_k]:
        repo.save(rec_date, cand.symbol, cand.name, sc, conds, signals)

    return {
        "universe": len(universe),
        "filtered": len(filtered),
        "saved": min(top_k, len(scored)),
    }

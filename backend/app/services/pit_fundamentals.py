"""
point-in-time 재무 지표 수집기 (look-ahead 차단)

핵심 계약:
- 각 분기 데이터는 분기말 + EARNINGS_DELAY_DAYS(45일) 이후부터만 사용 가능(available_from).
- metrics_at(as_of): available_from <= as_of 인 "가장 최근" 분기만 반환. 없으면 None.
  → 백테스트 특정 시점에 미래(미공시) 재무를 보는 look-ahead를 원천 차단.

순수 로직(metrics_at/yoy/pe/pb)과 데이터 빌더(build_korean_pit/build_us_pit)를 분리.
순수 로직은 합성 픽스처로 완전 테스트, 빌더는 DART/yfinance 호출을 mock 하거나 스모크로 검증.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import pandas as pd

from ..core.logging_config import logger
# 실적 발표 지연 상수는 fundamental_analysis에 이미 존재 — 재사용(중복 상수 금지)
from .fundamental_analysis import FundamentalAnalyzer

EARNINGS_DELAY_DAYS = FundamentalAnalyzer.EARNINGS_DELAY_DAYS

# 전년 동분기 매칭 허용 오차(분기말 일자가 회사/연도별로 며칠 다를 수 있음)
_YOY_TOLERANCE_DAYS = 20


@dataclass
class QuarterMetrics:
    """단일 분기의 point-in-time 재무 지표 스냅샷"""
    quarter_end: pd.Timestamp       # 분기말
    available_from: pd.Timestamp    # 분기말 + EARNINGS_DELAY_DAYS(45일) — 이 날짜부터 사용 가능
    eps: Optional[float]            # 분기 EPS (연환산 아님)
    bps: Optional[float]
    roe: Optional[float]            # 연환산: 분기 순이익*4 / 자본
    debt_to_equity: Optional[float]
    net_income: Optional[float]     # 분기 순이익 (성장률 계산용)
    current_ratio: Optional[float]


class PointInTimeFundamentals:
    """분기 스냅샷 목록을 시점 조회 가능한 형태로 보관"""

    def __init__(self, symbol: str, quarters: List[QuarterMetrics]):
        self.symbol = symbol
        # quarter_end 오름차순 정렬 저장
        self.quarters: List[QuarterMetrics] = sorted(
            quarters, key=lambda q: q.quarter_end
        )

    def metrics_at(self, as_of: pd.Timestamp) -> Optional[QuarterMetrics]:
        """available_from <= as_of 인 가장 최근 분기. 없으면 None (look-ahead 방지의 핵심)."""
        as_of = pd.Timestamp(as_of)
        if as_of.tzinfo is not None:
            as_of = as_of.tz_localize(None)  # 내부 quarter_end는 tz-naive — 비교 오류 방어
        latest: Optional[QuarterMetrics] = None
        for q in self.quarters:  # 오름차순 → 마지막으로 조건 만족한 것이 최신
            if q.available_from <= as_of:
                latest = q
            else:
                break
        return latest

    def _prev_year_quarter(self, m: QuarterMetrics) -> Optional[QuarterMetrics]:
        """m 분기의 전년 동분기(약 1년 전, 같은 분기말 월·일 기준)를 오차 범위 내에서 탐색"""
        target = m.quarter_end - pd.DateOffset(years=1)
        best: Optional[QuarterMetrics] = None
        best_diff = pd.Timedelta(days=_YOY_TOLERANCE_DAYS)
        for q in self.quarters:
            diff = abs(q.quarter_end - target)
            if diff <= best_diff:
                best_diff = diff
                best = q
        return best

    def yoy_net_income_growth_at(self, as_of: pd.Timestamp) -> Optional[float]:
        """
        metrics_at 분기와 그 전년 동분기 순이익 비교(증가율).
        둘 다 존재하고 전년 분기 net_income > 0 일 때만 반환; 아니면 None(fabrication 금지).
        """
        m = self.metrics_at(as_of)
        if m is None or m.net_income is None:
            return None
        prev = self._prev_year_quarter(m)
        if prev is None or prev is m or prev.net_income is None:
            return None
        if prev.net_income <= 0:
            return None
        return (m.net_income - prev.net_income) / prev.net_income

    def coverage(self) -> Optional[Tuple[pd.Timestamp, pd.Timestamp]]:
        """(첫 분기 available_from, 마지막 분기말 + 1분기) — 검증 가능 구간 표시용. 비면 None."""
        if not self.quarters:
            return None
        start = self.quarters[0].available_from
        end = self.quarters[-1].quarter_end + pd.DateOffset(months=3)
        return (start, end)

    def pe_at(self, as_of: pd.Timestamp, price: float) -> Optional[float]:
        """price / (분기 EPS * 4), EPS > 0 일 때만."""
        m = self.metrics_at(as_of)
        if m is None or m.eps is None or m.eps <= 0:
            return None
        return price / (m.eps * 4)

    def pb_at(self, as_of: pd.Timestamp, price: float) -> Optional[float]:
        """price / BPS, BPS > 0 일 때만."""
        m = self.metrics_at(as_of)
        if m is None or m.bps is None or m.bps <= 0:
            return None
        return price / m.bps


# ---------------------------------------------------------------------------
# 데이터 빌더 (네트워크) — 순수 로직과 분리. 단위 테스트는 mock/스모크에서 수행.
# ---------------------------------------------------------------------------

# 분기 → DART 보고서 코드
_REPRT_CODE = {1: "11013", 2: "11012", 3: "11014", 4: "11011"}
# 분기 → 분기말 (월, 일)
_QUARTER_END_MD = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


# 계정명 정확 일치용 알려진 변형 (공백 제거 기준) — 실응답 관찰(삼성전자 2023) 기반
_ACCOUNT_NAME_VARIANTS = {
    "당기순이익": ("당기순이익", "당기순이익(손실)", "연결당기순이익", "연결당기순이익(손실)"),
    "자본총계": ("자본총계",),
    "부채총계": ("부채총계",),
    "유동자산": ("유동자산",),
    "유동부채": ("유동부채",),
}


def _find_amount(
    df: pd.DataFrame,
    keyword: str,
    sj_div: Optional[tuple] = None,
    column: str = "thstrm_amount",
) -> Optional[float]:
    """
    DART fnlttSinglAcntAll 응답에서 account_nm 매칭으로 지정 컬럼 금액 추출.
    sj_div 지정 시 해당 재무제표 구분만 대상(BS=재무상태표, IS/CIS=손익).

    매칭 순서 (오매칭 방지 — 비유동자산/귀속내역 행 오염 차단):
    1) 공백 제거 후 알려진 변형과 정확 일치 우선 (예: "당기순이익(손실)")
    2) fallback: 포함 검색하되 "비"로 시작하는 계정(비유동자산/비유동부채 등) 제외

    실응답 확인(삼성전자 005930, 2023): 손익 계정의
    - thstrm_amount = 분기 단독(3개월)치 (사업보고서만 연간 12개월)
    - thstrm_add_amount = 당기누적치 (사업보고서는 빈 값)
    """
    if df is None or df.empty or "account_nm" not in df.columns:
        return None
    sub = df
    if sj_div is not None and "sj_div" in df.columns:
        sub = df[df["sj_div"].isin(sj_div)]

    names = sub["account_nm"].astype(str).str.replace(" ", "")

    # 1) 정확 일치 우선 (알려진 변형 포함)
    variants = _ACCOUNT_NAME_VARIANTS.get(keyword, (keyword,))
    rows = sub[names.isin(variants)]

    # 2) fallback: 포함 검색 — 단, "비"로 시작하는 계정(비유동~) 제외
    if rows.empty:
        rows = sub[names.str.contains(keyword, na=False) & ~names.str.startswith("비")]
    if rows.empty:
        return None

    raw = str(rows.iloc[0].get(column, "")).replace(",", "").strip()
    if raw in ("", "-", "nan", "None"):
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _fetch_shares(client, corp_code: str, year: int, reprt_code: str) -> Optional[float]:
    """발행주식수 조회 (stockTotqySttus.json) — dart_api.get_metrics_at_date 로직 재사용."""
    import requests
    try:
        url = "https://opendart.fss.or.kr/api/stockTotqySttus.json"
        params = {
            "crtfc_key": client.api_key,
            "corp_code": corp_code,
            "bsns_year": str(year),
            "reprt_code": reprt_code,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if data.get("status") == "000" and data.get("list"):
            # 보통주 합계(일반적으로 첫 행) — istc_totqy(발행주식 총수)
            raw = str(data["list"][0].get("istc_totqy", "")).replace(",", "").strip()
            shares = float(raw)
            return shares if shares > 0 else None
    except Exception as e:  # noqa: BLE001 - 발행주식수 실패는 해당 분기 스킵으로 흡수
        logger.warning(f"발행주식수 조회 실패 ({corp_code}, {year}, {reprt_code}): {e}")
    return None


def build_korean_pit(
    stock_code: str, start_year: int, end_year: int
) -> Optional[PointInTimeFundamentals]:
    """
    DART 재무제표를 연도×4분기 루프로 조회해 QuarterMetrics 목록 구성.

    당기순이익 분기 단독치 산출 (실응답 확인, 삼성전자 2023 기준):
    - 분기/반기/3분기 보고서(11013/11012/11014): thstrm_amount 가 이미 '분기 단독(3개월)'치 → 그대로 사용.
    - 사업보고서(11011): thstrm_amount 는 '연간(12개월)'치 → Q4 단독 = 연간 - 3분기누적(9개월).
      3분기누적(9개월)은 3분기보고서의 thstrm_add_amount 에서 획득.
    재무상태표 항목(자본/부채/유동자산/유동부채)은 시점 잔액이므로 thstrm_amount 그대로 사용.

    corp_code 없거나 전 분기 실패면 None.
    """
    from .dart_api import get_dart_client

    client = get_dart_client()
    corp_code = client.get_corp_code(stock_code)
    if not corp_code:
        logger.warning(f"build_korean_pit: {stock_code} 기업코드 없음")
        return None

    quarters: List[QuarterMetrics] = []
    for year in range(start_year, end_year + 1):
        cum9: Optional[float] = None  # 3분기 누적(9개월) 순이익 — Q4 단독치 산출용
        for q in (1, 2, 3, 4):
            reprt_code = _REPRT_CODE[q]
            try:
                df = client.get_financial_statement(corp_code, year, reprt_code)
            except Exception as e:  # noqa: BLE001 - 실패 분기는 건너뛰고 로그
                logger.warning(f"build_korean_pit: {stock_code} {year}Q{q} 조회 실패: {e}")
                continue
            if df is None or df.empty:
                continue

            # 당기순이익 분기 단독치
            quarter_ni: Optional[float] = None
            if q < 4:
                # 분기/반기/3분기: thstrm_amount = 분기 단독(3개월)치
                quarter_ni = _find_amount(df, "당기순이익", sj_div=("IS", "CIS"))
                if q == 3:
                    # 3분기 누적(9개월) 저장 → 사업보고서에서 Q4 단독 산출
                    cum9 = _find_amount(df, "당기순이익", sj_div=("IS", "CIS"),
                                        column="thstrm_add_amount")
            else:
                # 사업보고서: thstrm_amount = 연간(12개월). Q4 단독 = 연간 - 9개월누적
                annual = _find_amount(df, "당기순이익", sj_div=("IS", "CIS"))
                if annual is not None and cum9 is not None:
                    quarter_ni = annual - cum9
                # TODO(Task 7 스모크 실측 후 판단): 3분기보고서의 thstrm_add_amount(9개월 누적)
                # 부재 시 Q4 net_income이 None으로 유실됨. fallback으로 같은 해 Q1+Q2+Q3
                # 단독치 합산(모두 존재할 때만)으로 9개월 누적을 재구성하는 방안 검토.

            equity = _find_amount(df, "자본총계", sj_div=("BS",))
            debt = _find_amount(df, "부채총계", sj_div=("BS",))
            current_assets = _find_amount(df, "유동자산", sj_div=("BS",))
            current_liab = _find_amount(df, "유동부채", sj_div=("BS",))
            shares = _fetch_shares(client, corp_code, year, reprt_code)

            eps = (quarter_ni / shares) if (quarter_ni is not None and shares) else None
            bps = (equity / shares) if (equity is not None and shares) else None
            roe = (quarter_ni * 4 / equity) if (quarter_ni is not None and equity and equity > 0) else None
            dte = (debt / equity) if (debt is not None and equity and equity > 0) else None
            current_ratio = (
                current_assets / current_liab
                if (current_assets is not None and current_liab and current_liab > 0)
                else None
            )

            month, day = _QUARTER_END_MD[q]
            quarter_end = pd.Timestamp(year=year, month=month, day=day)
            quarters.append(
                QuarterMetrics(
                    quarter_end=quarter_end,
                    available_from=quarter_end + pd.Timedelta(days=EARNINGS_DELAY_DAYS),
                    eps=eps, bps=bps, roe=roe, debt_to_equity=dte,
                    net_income=quarter_ni, current_ratio=current_ratio,
                )
            )

    if not quarters:
        logger.warning(f"build_korean_pit: {stock_code} 유효 분기 없음")
        return None
    return PointInTimeFundamentals(stock_code, quarters)


def build_us_pit(symbol: str) -> Optional[PointInTimeFundamentals]:
    """
    yfinance quarterly_financials/quarterly_balance_sheet 에서 최근 4분기 구성.
    (그 이전 기간은 데이터가 없어 커버 불가 — coverage()로 검증 구간이 좁게 노출됨)
    """
    import yfinance as yf

    try:
        ticker = yf.Ticker(symbol)
        fin = ticker.quarterly_financials
        bs = ticker.quarterly_balance_sheet
        shares = ticker.info.get("sharesOutstanding")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"build_us_pit: {symbol} yfinance 조회 실패: {e}")
        return None

    if fin is None or fin.empty:
        logger.warning(f"build_us_pit: {symbol} 분기 손익 데이터 없음")
        return None

    def _row(frame: pd.DataFrame, *names: str):
        if frame is None or frame.empty:
            return None
        for name in names:
            if name in frame.index:
                return frame.loc[name]
        return None

    ni_row = _row(fin, "Net Income", "Net Income Common Stockholders")
    eq_row = _row(bs, "Stockholders Equity", "Total Stockholder Equity")
    liab_row = _row(bs, "Total Liabilities Net Minority Interest", "Total Liab")
    ca_row = _row(bs, "Current Assets", "Total Current Assets")
    cl_row = _row(bs, "Current Liabilities", "Total Current Liabilities")

    if ni_row is None:
        logger.warning(f"build_us_pit: {symbol} Net Income 행 없음")
        return None

    def _val(row, col):
        if row is None or col not in row.index:
            return None
        v = row[col]
        return float(v) if pd.notna(v) else None

    quarters: List[QuarterMetrics] = []
    for col in ni_row.index:  # 각 컬럼 = 분기말 날짜
        quarter_end = pd.Timestamp(col)
        ni = _val(ni_row, col)
        equity = _val(eq_row, col)
        debt = _val(liab_row, col)
        ca = _val(ca_row, col)
        cl = _val(cl_row, col)

        eps = (ni / shares) if (ni is not None and shares) else None
        bps = (equity / shares) if (equity is not None and shares) else None
        roe = (ni * 4 / equity) if (ni is not None and equity and equity > 0) else None
        dte = (debt / equity) if (debt is not None and equity and equity > 0) else None
        current_ratio = (ca / cl) if (ca is not None and cl and cl > 0) else None

        quarters.append(
            QuarterMetrics(
                quarter_end=quarter_end,
                available_from=quarter_end + pd.Timedelta(days=EARNINGS_DELAY_DAYS),
                eps=eps, bps=bps, roe=roe, debt_to_equity=dte,
                net_income=ni, current_ratio=current_ratio,
            )
        )

    if not quarters:
        return None
    return PointInTimeFundamentals(symbol, quarters)

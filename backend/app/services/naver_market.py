"""네이버 금융 시가총액 페이지 크롤러 (KRX 로그인 대체 폴백).

2026년 KRX 정책 변경으로 pykrx 벌크 조회(get_market_cap/fundamental/ticker_list)가
로그인 필수가 되어, 자격증명이 없을 때 유니버스/종목명 사전을 구성하지 못한다.
이 모듈은 네이버 금융 시가총액 페이지를 크롤링해 시총 상위 종목의 기본 지표를
제공하는 **폴백** 경로다. KRX 경로가 성공하면 이 모듈은 호출되지 않는다.

관찰한 실제 DOM 구조 (finance.naver.com/sise/sise_market_sum.naver, EUC-KR, 2026-07-05):
  table.type_2 > tbody > tr (데이터 행은 td 13개)
    td[0]  N(순위)         td.no
    td[1]  종목명           a.tltle[href=/item/main.naver?code=XXXXXX]
    td[2]  현재가           "309,500"
    td[3]  전일비           td[4] 등락률   td[5] 액면가
    td[6]  시가총액(억원)    "18,094,232"  ← 억원 단위 → 원으로 ×1e8 변환
    td[7]  상장주식수  td[8] 외국인비율  td[9] 거래량
    td[10] PER            "25.02" | "N/A"
    td[11] ROE(%)         "10.85" | "N/A"  ← % → 소수(/100) 변환
    td[12] 토론 링크
  * 행 사이에 spacer 행(td colspan=13)이 있어 td 13개 미만 행은 건너뛴다.
  * PBR/BPS는 이 기본 페이지에 없음 → 폴백 Candidate.pbr은 None(호출자 처리).
  * 'N/A'/'-' 등 값 없음은 None(fabrication 금지).

설계:
- parse_market_sum_html: 순수 함수(픽스처 테스트 대상). 인코딩 무관.
- fetch_market_sum: HTTP I/O 격리. 모듈 레벨 캐시 없음(호출자가 캐시).
"""
import logging
import re
import time
from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_BASE_URL = "https://finance.naver.com/sise/sise_market_sum.naver"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

# sosok(시장구분) → yfinance 접미사: 0=KOSPI(.KS), 1=KOSDAQ(.KQ)
_SOSOK_SUFFIX = {0: ".KS", 1: ".KQ"}

# 데이터 행 최소 td 개수(spacer 행 배제용)
_MIN_TD = 13

# 종목 상세 링크에서 종목코드 추출: .../main.naver?code=005930
_CODE_RE = re.compile(r"code=(\d{6})")


@dataclass
class MarketRow:
    """시가총액 페이지 1행(순수 값). 값 없음은 None(추측 금지)."""
    symbol: str        # "005930.KS" / "035720.KQ"
    name: str
    close: float | None
    market_cap: float | None   # 원 단위 (페이지의 억원 × 1e8)
    per: float | None
    roe: float | None          # 소수 (페이지의 % ÷ 100)


def _num(text: str | None) -> float | None:
    """'309,500' → 309500.0, 'N/A'/'-'/'' → None. 콤마·공백 제거 후 float."""
    if text is None:
        return None
    cleaned = text.strip().replace(",", "")
    if cleaned in ("", "-", "N/A"):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_market_sum_html(html: str, market_suffix: str) -> list[MarketRow]:
    """시가총액 페이지 HTML을 MarketRow 리스트로 파싱하는 순수 함수.

    - 종목코드는 각 행 종목명 링크의 href(code=XXXXXX)에서 추출한다.
    - 시가총액은 억원 → 원(×1e8), ROE는 % → 소수(÷100) 변환한다.
    - 'N/A'/'-' 값은 None(fabrication 금지).
    - 구조 변경 등으로 행/코드를 못 찾으면 해당 행을 건너뛴다(예외 없이 빈 리스트 가능).
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    table = soup.select_one("table.type_2")
    if table is None:
        return []

    rows: list[MarketRow] = []
    for tr in table.select("tbody tr"):
        tds = tr.find_all("td", recursive=False)
        if len(tds) < _MIN_TD:  # spacer/구분 행 건너뜀
            continue

        link = tds[1].select_one("a[href]")
        if link is None:
            continue
        match = _CODE_RE.search(link.get("href", ""))
        if match is None:
            continue
        code = match.group(1)
        name = link.get_text(strip=True)
        if not name:
            continue

        cap_eok = _num(tds[6].get_text(strip=True))
        roe_pct = _num(tds[11].get_text(strip=True))
        rows.append(
            MarketRow(
                symbol=f"{code}{market_suffix}",
                name=name,
                close=_num(tds[2].get_text(strip=True)),
                # 억원 → 원
                market_cap=(cap_eok * 1e8) if cap_eok is not None else None,
                per=_num(tds[10].get_text(strip=True)),
                # % → 소수
                roe=(roe_pct / 100.0) if roe_pct is not None else None,
            )
        )
    return rows


def fetch_market_sum(
    markets: tuple = (0, 1),
    max_pages_per_market: int = 8,
    delay_sec: float = 1.0,
) -> list[MarketRow]:
    """네이버 시가총액 페이지를 시장·페이지별로 GET·파싱해 MarketRow 리스트 반환.

    - 페이지당 50종목 — 기본 8페이지 × 2시장 = 시총 상위 800종목 커버.
    - User-Agent 헤더, timeout=10. 네이버 금융은 EUC-KR 인코딩.
    - 페이지 실패는 건너뛰고 logger.warning. 요청 간 delay_sec 만큼 sleep(과호출 방지).
    - 모듈 레벨 캐시 없음 — 호출자(recommender/naver_news)가 필요 시 캐시한다.
    """
    headers = {"User-Agent": _USER_AGENT}
    result: list[MarketRow] = []

    for sosok in markets:
        suffix = _SOSOK_SUFFIX.get(sosok, ".KS")
        for page in range(1, max_pages_per_market + 1):
            try:
                resp = requests.get(
                    _BASE_URL,
                    params={"sosok": sosok, "page": page},
                    headers=headers,
                    timeout=10,
                )
                resp.raise_for_status()
                resp.encoding = "euc-kr"  # 네이버 금융 고정 인코딩(실관찰)
                page_rows = parse_market_sum_html(resp.text, suffix)
                if not page_rows:
                    logger.warning(
                        "네이버 시총 sosok=%d page=%d 파싱 0건 (구조 변경/마지막 페이지 의심)",
                        sosok, page,
                    )
                result.extend(page_rows)
            except Exception as exc:  # 네트워크/HTTP 실패 — 해당 페이지만 건너뜀
                logger.warning(
                    "네이버 시총 sosok=%d page=%d 수집 실패: %s", sosok, page, exc
                )
            finally:
                if delay_sec > 0:
                    time.sleep(delay_sec)

    return result

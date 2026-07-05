"""네이버 뉴스 서비스.

모듈 구성:
- Task 3: 순수 로직 — 종목명 사전(build_name_map), 종목 매칭(match_stocks),
  감성 태깅(tag_sentiment) 및 키워드 상수.
- Task 4: 네이버 금융 주요뉴스 크롤링 — fetch_mainnews(HTTP), parse_mainnews_html(파싱),
  collect_and_store(수집→매칭/감성→저장).

종목명 사전은 pykrx로 KOSPI/KOSDAQ 전 종목을 조회하며, 조회 비용이 크므로
프로세스당 1회만 빌드하여 모듈 전역에 캐시한다(build_name_map).
"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from pykrx import stock

from app.services import naver_market

logger = logging.getLogger(__name__)

# ── 감성 키워드 상수 (추후 확장 가능) ──────────────────────────
POSITIVE_KEYWORDS = [
    "수주", "흑자전환", "신고가", "상향", "호실적", "매수",
    "급등", "돌파", "최대 실적", "배당 확대", "자사주 매입",
]
NEGATIVE_KEYWORDS = [
    "적자", "소송", "하향", "유상증자", "급락", "부진",
    "리콜", "횡령", "감자", "상장폐지", "경고",
]

# ── 종목명 → 심볼 사전 모듈 캐시 (프로세스당 1회) ──────────────
_NAME_MAP_CACHE: dict[str, str] | None = None

# 시장별 yfinance 접미사
_MARKET_SUFFIX = {"KOSPI": ".KS", "KOSDAQ": ".KQ"}


def build_name_map(force_refresh: bool = False) -> dict[str, str]:
    """pykrx로 KOSPI/KOSDAQ 전 종목의 {종목명: 심볼} 사전을 빌드한다.

    - KOSPI 종목은 ``.KS``, KOSDAQ 종목은 ``.KQ`` 접미사를 붙인다.
    - 조회 비용이 크므로 모듈 전역에 캐시하며, 프로세스당 1회만 실제 호출한다.
    - pykrx 실패/빈 결과(2026 로그인 정책 등) 시 네이버 금융 시총 페이지로 폴백한다.
    - 폴백까지 실패하면 빈 dict를 반환하고 warning(캐시하지 않음).

    Args:
        force_refresh: True면 캐시를 무시하고 다시 빌드한다(테스트/갱신용).
    """
    global _NAME_MAP_CACHE
    if _NAME_MAP_CACHE is not None and not force_refresh:
        return _NAME_MAP_CACHE

    name_map: dict[str, str] = {}
    try:
        for market, suffix in _MARKET_SUFFIX.items():
            for ticker in stock.get_market_ticker_list(market=market):
                name = stock.get_market_ticker_name(ticker)
                if name:
                    name_map[name] = f"{ticker}{suffix}"
    except Exception as exc:  # pykrx/네트워크 실패 — 네이버 폴백으로 넘어감
        logger.warning("build_name_map(pykrx) 실패: %s", exc)
        name_map = {}

    # pykrx 실패/빈 결과 시 네이버 시총 페이지로 폴백 (KRX 로그인 대체)
    if not name_map:
        logger.info("build_name_map: pykrx 비어있음 → 네이버 시총 폴백으로 사전 구성")
        try:
            for row in naver_market.fetch_market_sum():
                if row.name:
                    name_map[row.name] = row.symbol
        except Exception as exc:  # 방어적 — fetch 내부에서 이미 페이지별 예외 처리
            logger.warning("build_name_map(네이버 폴백) 실패: %s", exc)
            name_map = {}

    if not name_map:  # 폴백까지 실패 — 캐시하지 않음
        logger.warning("build_name_map 실패, 빈 사전 반환")
        return {}

    _NAME_MAP_CACHE = name_map
    return name_map


def match_stocks(title: str, name_map: dict[str, str]) -> list[str]:
    """제목에 등장한 종목명을 심볼 리스트로 반환한다.

    규칙:
    - 긴 이름 우선 매칭: "삼성전자우"가 매칭되면 그 구간에서 "삼성전자" 재매칭 금지.
    - 2글자 미만(1글자) 종목명은 오탐 방지를 위해 제외.
    - 반환 순서는 제목 내 등장 위치 순서, 중복 심볼은 제거.
    """
    # 긴 이름부터 소비하여 부분 매칭 오염 방지
    names = sorted(
        (n for n in name_map if len(n) >= 2),
        key=len,
        reverse=True,
    )

    # 이미 소비된 문자 구간 추적(True=소비됨)
    consumed = [False] * len(title)
    hits: list[tuple[int, str]] = []  # (등장 위치, 심볼)

    for name in names:
        start = 0
        while True:
            idx = title.find(name, start)
            if idx == -1:
                break
            end = idx + len(name)
            if not any(consumed[idx:end]):
                for i in range(idx, end):
                    consumed[i] = True
                hits.append((idx, name_map[name]))
            start = idx + 1

    # 등장 위치 순 정렬 후 심볼 중복 제거(순서 유지)
    hits.sort(key=lambda h: h[0])
    result: list[str] = []
    seen: set[str] = set()
    for _, symbol in hits:
        if symbol not in seen:
            seen.add(symbol)
            result.append(symbol)
    return result


def tag_sentiment(title: str) -> str:
    """제목의 긍정/부정 키워드 카운트를 비교해 감성을 반환한다.

    긍정 우세 → 'positive', 부정 우세 → 'negative',
    동수이거나 무매칭 → 'neutral'.
    """
    pos = sum(title.count(kw) for kw in POSITIVE_KEYWORDS)
    neg = sum(title.count(kw) for kw in NEGATIVE_KEYWORDS)
    if pos > neg:
        return "positive"
    if neg > pos:
        return "negative"
    return "neutral"


# ════════════════════════════════════════════════════════════════
# Task 4: 네이버 금융 주요뉴스 크롤러
#
# 관찰한 실제 DOM 구조 (finance.naver.com/news/mainnews.naver, EUC-KR):
#   ul.newsList > li.block1
#     dd.articleSubject > a[href]   → 제목 + 상세 링크(상대경로)
#     dd.articleSummary             → 요약 텍스트(뒤에 아래 span들이 붙어 있음)
#       span.press                  → 언론사명
#       span.bar                    → "|" 구분자
#       span.wdate                  → "YYYY-MM-DD HH:MM:SS"
# ════════════════════════════════════════════════════════════════

_NAVER_BASE = "https://finance.naver.com"
_MAINNEWS_URL = _NAVER_BASE + "/news/mainnews.naver"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
_PUBLISHED_FMT = "%Y-%m-%d %H:%M"  # 저장소 정렬 정합성: 분까지만 통일


@dataclass
class NewsItem:
    """주요뉴스 1건 (파싱 결과의 순수 값)."""
    title: str
    url: str            # 절대 URL
    source: str         # 언론사명, 없으면 "naver"
    published_at: str   # "YYYY-MM-DD HH:MM" (파싱 실패 시 수집 시각)
    summary: str | None


def _normalize_published_at(raw: str | None) -> str:
    """네이버 wdate("YYYY-MM-DD HH:MM:SS")를 "YYYY-MM-DD HH:MM"으로 정규화한다.

    파싱 실패(형식 불일치·값 없음) 시 현재 수집 시각으로 폴백한다.
    """
    if raw:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y.%m.%d %H:%M"):
            try:
                return datetime.strptime(raw.strip(), fmt).strftime(_PUBLISHED_FMT)
            except ValueError:
                continue
    return datetime.now().strftime(_PUBLISHED_FMT)


def parse_mainnews_html(html: str, base_url: str = _NAVER_BASE) -> list[NewsItem]:
    """주요뉴스 목록 HTML을 NewsItem 리스트로 파싱하는 순수 함수.

    - 구조 변경 등으로 목록을 못 찾으면 예외 없이 빈 리스트를 반환한다(호출자가 로그).
    - 제목/링크가 없는 항목은 건너뛴다.
    """
    if not html:
        return []

    soup = BeautifulSoup(html, "lxml")
    items: list[NewsItem] = []

    for li in soup.select("ul.newsList li.block1"):
        subject = li.select_one("dd.articleSubject a")
        if subject is None:
            continue
        title = subject.get_text(strip=True)
        href = subject.get("href")
        if not title or not href:
            continue
        url = urljoin(base_url, href)

        press_el = li.select_one("span.press")
        source = press_el.get_text(strip=True) if press_el else ""
        source = source or "naver"

        wdate_el = li.select_one("span.wdate")
        published_at = _normalize_published_at(
            wdate_el.get_text(strip=True) if wdate_el else None
        )

        summary_el = li.select_one("dd.articleSummary")
        summary: str | None = None
        if summary_el is not None:
            # 요약 dd 안의 press/bar/wdate span을 제거한 뒤 본문 텍스트만 추출
            clone = BeautifulSoup(str(summary_el), "lxml")
            for span in clone.select("span"):
                span.decompose()
            text = clone.get_text(strip=True)
            summary = text or None

        items.append(NewsItem(
            title=title, url=url, source=source,
            published_at=published_at, summary=summary,
        ))

    return items


def fetch_mainnews(pages: int = 3, delay_sec: float = 1.0) -> list[NewsItem]:
    """주요뉴스 여러 페이지를 GET하여 파싱한다(url 기준 중복 제거).

    - User-Agent 헤더, timeout=10. 네이버 금융은 EUC-KR이므로 apparent/헤더 인코딩을 따른다.
    - 페이지 실패는 건너뛰고 logger.warning. 요청 간 delay_sec 만큼 sleep(과호출 방지).
    """
    headers = {"User-Agent": _USER_AGENT}
    seen: set[str] = set()
    result: list[NewsItem] = []

    for page in range(1, pages + 1):
        try:
            resp = requests.get(
                _MAINNEWS_URL, params={"page": page},
                headers=headers, timeout=10,
            )
            resp.raise_for_status()
            # 네이버 금융은 EUC-KR — requests가 못 잡으면 apparent_encoding으로 보정
            if not resp.encoding or resp.encoding.lower() in ("iso-8859-1",):
                resp.encoding = resp.apparent_encoding
            page_items = parse_mainnews_html(resp.text)
            if not page_items:
                logger.warning("주요뉴스 page=%d 파싱 0건 (구조 변경 의심)", page)
            for item in page_items:
                if item.url not in seen:
                    seen.add(item.url)
                    result.append(item)
        except Exception as exc:  # 네트워크/HTTP 실패 — 해당 페이지만 건너뜀
            logger.warning("주요뉴스 page=%d 수집 실패: %s", page, exc)
        finally:
            if page < pages and delay_sec > 0:
                time.sleep(delay_sec)

    return result


def collect_and_store(repo, name_map: dict[str, str], pages: int = 3) -> dict:
    """주요뉴스를 수집→종목 매칭+감성 태깅→저장소에 적재하고 통계를 반환한다.

    반환: {"fetched": 수집 건수, "inserted": 신규 저장 건수,
           "linked_symbols": 신규 저장분에 연결된 종목 링크 총합}
    - 중복 url은 repo.save_article가 None을 반환하므로 inserted에서 제외된다.
    """
    items = fetch_mainnews(pages=pages)
    inserted = 0
    linked_symbols = 0

    for item in items:
        symbols = match_stocks(item.title, name_map)
        sentiment = tag_sentiment(item.title)
        article_id = repo.save_article(
            published_at=item.published_at,
            source=item.source,
            title=item.title,
            url=item.url,
            summary=item.summary,
            sentiment=sentiment,
            symbols=symbols,
        )
        if article_id is not None:
            inserted += 1
            linked_symbols += len(symbols)

    return {
        "fetched": len(items),
        "inserted": inserted,
        "linked_symbols": linked_symbols,
    }

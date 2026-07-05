"""네이버 뉴스 서비스.

모듈 구성:
- Task 3 (본 파일): 순수 로직 — 종목명 사전(build_name_map), 종목 매칭(match_stocks),
  감성 태깅(tag_sentiment) 및 키워드 상수.
- Task 4 (추후 추가): 네이버 뉴스 크롤링(fetch/parse) — 같은 파일에 append 예정.

종목명 사전은 pykrx로 KOSPI/KOSDAQ 전 종목을 조회하며, 조회 비용이 크므로
프로세스당 1회만 빌드하여 모듈 전역에 캐시한다(build_name_map).
"""
import logging

from pykrx import stock

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
    - pykrx 호출 실패 시 빈 dict를 반환하고 warning 로그를 남긴다(캐시하지 않음).

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
    except Exception as exc:  # pykrx/네트워크 실패 — 빈 dict로 안전 폴백
        logger.warning("build_name_map 실패, 빈 사전 반환: %s", exc)
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

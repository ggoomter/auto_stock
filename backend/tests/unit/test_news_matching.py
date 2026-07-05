"""naver_news.py 순수 로직 테스트: 종목명 사전 · 종목 매칭 · 감성 태깅"""
from unittest.mock import patch

from app.services.naver_news import (
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    build_name_map,
    match_stocks,
    tag_sentiment,
)


# ── match_stocks: 긴 이름 우선 매칭 ─────────────────────────────
def test_match_longest_name_first():
    name_map = {
        "삼성전자": "005930.KS",
        "삼성전자우": "005935.KS",
        "카카오": "035720.KS",
    }
    assert match_stocks("삼성전자우 강세, 카카오도 상승", name_map) == [
        "005935.KS",
        "035720.KS",
    ]


def test_match_no_partial_pollution():
    # "삼성전자우" 기사에서 "삼성전자"가 함께 매칭되면 안 됨 (긴 이름이 구간 소비)
    name_map = {"삼성전자": "005930.KS", "삼성전자우": "005935.KS"}
    assert match_stocks("삼성전자우 신고가 경신", name_map) == ["005935.KS"]


def test_match_order_and_dedup():
    # 반환 순서는 제목 내 등장 순서, 중복 종목은 한 번만
    name_map = {"카카오": "035720.KS", "네이버": "035420.KS"}
    assert match_stocks("네이버·카카오 동반 상승, 카카오 재차 강세", name_map) == [
        "035420.KS",
        "035720.KS",
    ]


def test_match_excludes_short_names():
    # 2글자 미만(1글자) 이름은 오탐 방지를 위해 제외
    name_map = {"A": "000001.KS", "카카오": "035720.KS"}
    assert match_stocks("A 그룹과 카카오 협업", name_map) == ["035720.KS"]


def test_match_no_hit_returns_empty():
    name_map = {"삼성전자": "005930.KS"}
    assert match_stocks("코스피 강보합 마감", name_map) == []


# ── tag_sentiment: 카운트 비교 ──────────────────────────────────
def test_sentiment_positive_negative_neutral():
    assert tag_sentiment("A사 대규모 수주 소식에 급등") == "positive"
    assert tag_sentiment("B사 소송 리스크에 급락") == "negative"
    assert tag_sentiment("C사 주주총회 개최") == "neutral"
    assert tag_sentiment("D사 수주에도 소송 우려") == "neutral"  # 동수


# ── build_name_map: pykrx mock, KOSPI=.KS / KOSDAQ=.KQ 접미사 ──
def test_build_name_map_appends_suffix():
    def fake_ticker_list(market):
        return {"KOSPI": ["005930"], "KOSDAQ": ["035720"]}[market]

    def fake_ticker_name(ticker):
        return {"005930": "삼성전자", "035720": "카카오게임즈"}[ticker]

    with patch("app.services.naver_news.stock") as mock_stock:
        mock_stock.get_market_ticker_list.side_effect = fake_ticker_list
        mock_stock.get_market_ticker_name.side_effect = fake_ticker_name
        result = build_name_map(force_refresh=True)

    assert result["삼성전자"] == "005930.KS"
    assert result["카카오게임즈"] == "035720.KQ"


def test_build_name_map_pykrx_failure_returns_empty():
    with patch("app.services.naver_news.stock") as mock_stock:
        mock_stock.get_market_ticker_list.side_effect = RuntimeError("network down")
        result = build_name_map(force_refresh=True)

    assert result == {}


def test_keyword_constants_nonempty():
    assert len(POSITIVE_KEYWORDS) > 0
    assert len(NEGATIVE_KEYWORDS) > 0

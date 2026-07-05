"""KRX 실패 → 네이버 폴백 배선 테스트 (recommender.build_universe · naver_news.build_name_map).

네트워크 금지: naver_market.fetch_market_sum을 mock하여 폴백 경로만 검증한다.
"""
from unittest.mock import patch

from app.services import naver_news, recommender
from app.services.naver_market import MarketRow


def _fake_rows():
    return [
        MarketRow(symbol="005930.KS", name="삼성전자", close=309500.0,
                  market_cap=1.8e15, per=25.0, roe=0.108),
        MarketRow(symbol="035720.KQ", name="카카오", close=41000.0,
                  market_cap=1.7e14, per=None, roe=None),
    ]


# ── recommender.build_universe 폴백 ──────────────────────────────
def test_build_universe_falls_back_to_naver_when_krx_empty():
    meta: dict = {}
    with patch("app.services.recommender._build_universe_krx", return_value=[]), \
         patch("app.services.recommender.naver_market.fetch_market_sum",
               return_value=_fake_rows()) as mock_fetch:
        cands = recommender.build_universe(top_n=10, date="20260706", meta=meta)

    mock_fetch.assert_called_once()
    assert meta["universe_source"] == "naver_fallback"
    assert len(cands) == 2
    # 시총 내림차순 정렬
    assert cands[0].symbol == "005930.KS"
    # PBR은 네이버 미제공 → None
    assert all(c.pbr is None for c in cands)
    assert cands[0].roe == 0.108


def test_build_universe_krx_used_when_available_no_naver_call():
    krx = [recommender.Candidate(symbol="000660", name="SK하이닉스",
                                 close=200000.0, per=10.0, pbr=1.5, roe=0.2,
                                 market_cap=1.4e14)]
    meta: dict = {}
    with patch("app.services.recommender._build_universe_krx", return_value=krx), \
         patch("app.services.recommender.naver_market.fetch_market_sum") as mock_fetch:
        cands = recommender.build_universe(top_n=10, date="20260706", meta=meta)

    mock_fetch.assert_not_called()
    assert meta["universe_source"] == "krx"
    assert cands == krx


def test_build_universe_naver_top_n_by_market_cap():
    rows = [
        MarketRow(symbol="A.KS", name="A", close=1.0, market_cap=1e12,
                  per=5.0, roe=0.1),
        MarketRow(symbol="B.KS", name="B", close=1.0, market_cap=3e12,
                  per=5.0, roe=0.1),
        MarketRow(symbol="C.KS", name="C", close=1.0, market_cap=2e12,
                  per=5.0, roe=0.1),
    ]
    with patch("app.services.recommender._build_universe_krx", return_value=[]), \
         patch("app.services.recommender.naver_market.fetch_market_sum",
               return_value=rows):
        cands = recommender.build_universe(top_n=2, date="20260706")
    # 시총순 B(3e12) > C(2e12), top_n=2 절삭 → A 제외
    assert [c.symbol for c in cands] == ["B.KS", "C.KS"]


# ── naver_news.build_name_map 폴백 ───────────────────────────────
def test_build_name_map_falls_back_to_naver():
    with patch("app.services.naver_news.stock.get_market_ticker_list",
               side_effect=Exception("KRX 로그인 필요")), \
         patch("app.services.naver_news.naver_market.fetch_market_sum",
               return_value=_fake_rows()) as mock_fetch:
        name_map = naver_news.build_name_map(force_refresh=True)

    mock_fetch.assert_called_once()
    assert name_map["삼성전자"] == "005930.KS"
    assert name_map["카카오"] == "035720.KQ"


def test_build_name_map_empty_when_both_fail_not_cached():
    naver_news._NAME_MAP_CACHE = None
    with patch("app.services.naver_news.stock.get_market_ticker_list",
               side_effect=Exception("KRX 실패")), \
         patch("app.services.naver_news.naver_market.fetch_market_sum",
               return_value=[]):
        name_map = naver_news.build_name_map(force_refresh=True)
    assert name_map == {}
    assert naver_news._NAME_MAP_CACHE is None  # 빈 결과는 캐시 안 함

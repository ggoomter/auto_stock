"""KRX 실패 → 네이버 폴백 배선 테스트 (recommender.build_universe · naver_news.build_name_map).

네트워크 금지: naver_market.fetch_market_sum/pykrx를 mock하여 폴백 경로만 검증한다.
심볼 형식 통일(접미사 포함)과 _fetch_ohlcv의 6자리 코드 변환도 여기서 검증.
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from app.services import naver_news, recommender
from app.services.naver_market import MarketRow


def _patch_stock(module_path: str, **fns):
    """pykrx stock을 Mock 묶음으로 통째 교체.

    stock 속성 단위 패치는 pykrx 임포트가 실패한 환경(stock=None — 임포트가
    KRX 로그인 네트워크를 타므로 간헐 실패)에서 AttributeError로 깨진다.
    객체 자체를 교체하면 네트워크 상태와 무관하게 결정론적으로 동작한다.
    """
    return patch(module_path, SimpleNamespace(**fns), create=True)


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
    with _patch_stock("app.services.naver_news.stock",
                      get_market_ticker_list=Mock(side_effect=Exception("KRX 로그인 필요"))), \
         patch("app.services.naver_news.naver_market.fetch_market_sum",
               return_value=_fake_rows()) as mock_fetch:
        name_map = naver_news.build_name_map(force_refresh=True)

    mock_fetch.assert_called_once()
    assert name_map["삼성전자"] == "005930.KS"
    assert name_map["카카오"] == "035720.KQ"


def test_build_name_map_empty_when_both_fail_not_cached():
    naver_news._NAME_MAP_CACHE = None
    with _patch_stock("app.services.naver_news.stock",
                      get_market_ticker_list=Mock(side_effect=Exception("KRX 실패"))), \
         patch("app.services.naver_news.naver_market.fetch_market_sum",
               return_value=[]):
        name_map = naver_news.build_name_map(force_refresh=True)
    assert name_map == {}
    assert naver_news._NAME_MAP_CACHE is None  # 빈 결과는 캐시 안 함


# ── 심볼 형식 통일 · _fetch_ohlcv 코드 변환 ──────────────────────
def test_fetch_ohlcv_strips_suffix_before_pykrx():
    """pykrx get_market_ohlcv는 6자리 코드만 받으므로 접미사를 제거해 호출해야 한다."""
    ohlcv = pd.DataFrame(
        {"시가": [1.0], "고가": [1.0], "저가": [1.0], "종가": [1.0], "거래량": [1]}
    )
    mock_ohlcv = Mock(return_value=ohlcv)
    with _patch_stock("app.services.recommender.stock", get_market_ohlcv=mock_ohlcv):
        df = recommender._fetch_ohlcv("005930.KS", "2026-07-06")

    # 세 번째 위치 인자(티커)가 접미사 제거된 6자리 코드여야 함
    assert mock_ohlcv.call_args.args[2] == "005930"
    assert list(df.columns) == ["open", "high", "low", "close", "volume"]


def test_fetch_ohlcv_bare_code_passthrough():
    ohlcv = pd.DataFrame(
        {"시가": [1.0], "고가": [1.0], "저가": [1.0], "종가": [1.0], "거래량": [1]}
    )
    mock_ohlcv = Mock(return_value=ohlcv)
    with _patch_stock("app.services.recommender.stock", get_market_ohlcv=mock_ohlcv):
        recommender._fetch_ohlcv("005930", "2026-07-06")
    assert mock_ohlcv.call_args.args[2] == "005930"


def test_build_universe_krx_symbols_have_market_suffix():
    """KRX 경로 Candidate.symbol도 앱 표준(접미사 포함)으로 통일돼야 한다."""
    kospi_cap = pd.DataFrame({"시가총액": [1e12], "종가": [50000]}, index=["005930"])
    kosdaq_cap = pd.DataFrame({"시가총액": [5e11], "종가": [40000]}, index=["035720"])
    fund_df = pd.DataFrame(
        {"PER": [10.0], "PBR": [1.5], "EPS": [5000.0], "BPS": [30000.0]},
        index=["005930", "035720"],
    )

    def fake_cap(date_str, market="KOSPI"):
        return kospi_cap if market == "KOSPI" else kosdaq_cap

    with _patch_stock("app.services.recommender.stock",
                      get_market_cap_by_ticker=Mock(side_effect=fake_cap),
                      get_market_fundamental_by_ticker=Mock(return_value=fund_df),
                      get_market_ticker_name=Mock(return_value="테스트")):
        cands = recommender.build_universe(top_n=10, date="20260706")

    symbols = {c.symbol for c in cands}
    assert symbols == {"005930.KS", "035720.KQ"}

"""네이버 금융 시가총액 크롤러 테스트: parse_market_sum_html (순수 파싱).

- 고정 픽스처(naver_market_sum_sample.html)로 파싱 검증(네트워크 금지).
- 컬럼 순서/단위 변환(억원→원, %→소수)/N-A 처리(None)를 검증한다.
"""
from pathlib import Path

from app.services.naver_market import MarketRow, parse_market_sum_html

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "naver_market_sum_sample.html"
)


def _load() -> str:
    return FIXTURE.read_text(encoding="utf-8")


def _rows(suffix=".KS"):
    return parse_market_sum_html(_load(), suffix)


def test_parse_returns_marketrows():
    rows = _rows()
    # 픽스처는 데이터 3행(삼성전자, 삼성전자우, KODEX 200) — spacer/header 제외
    assert len(rows) == 3
    assert all(isinstance(r, MarketRow) for r in rows)


def test_symbol_from_href_with_suffix():
    rows = _rows(".KS")
    assert rows[0].symbol == "005930.KS"
    assert rows[1].symbol == "005935.KS"
    # 코스닥 접미사도 인자대로 적용
    kq = _rows(".KQ")
    assert kq[0].symbol == "005930.KQ"


def test_name_and_close_parsed():
    rows = _rows()
    assert rows[0].name == "삼성전자"
    assert rows[0].close == 309500.0
    assert rows[2].name == "KODEX 200"


def test_market_cap_eok_to_won():
    rows = _rows()
    # 시가총액 18,094,232 억원 → 원 단위 (×1e8)
    assert rows[0].market_cap == 18094232 * 1e8


def test_per_roe_parsed_and_scaled():
    rows = _rows()
    assert rows[0].per == 25.02
    # ROE 10.85(%) → 소수 0.1085
    assert abs(rows[0].roe - 0.1085) < 1e-9


def test_na_values_become_none():
    rows = _rows()
    # 삼성전자우: PER 있음, ROE N/A → None
    assert rows[1].per == 16.81
    assert rows[1].roe is None
    # KODEX 200: PER·ROE 모두 N/A → None
    assert rows[2].per is None
    assert rows[2].roe is None


def test_empty_html_returns_empty():
    assert parse_market_sum_html("", ".KS") == []
    assert parse_market_sum_html("<html><body>x</body></html>", ".KS") == []

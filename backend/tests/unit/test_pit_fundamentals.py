"""point-in-time 지표 수집기 테스트 — look-ahead 방지의 핵심 계약"""
import pandas as pd
import pytest


def test_lookahead_guard_before_disclosure(good_pit):
    # 2024-03-31 분기는 5/15(45일 후)부터만 사용 가능 — 4/30 시점엔 직전 분기여야 함
    m = good_pit.metrics_at(pd.Timestamp("2024-04-30"))
    assert m.quarter_end == pd.Timestamp("2023-12-31")  # look-ahead면 2024-03-31이 나옴 → 실패


def test_no_data_before_first_disclosure(good_pit):
    assert good_pit.metrics_at(pd.Timestamp("2023-04-01")) is None  # 첫 공시(5/15) 전


def test_yoy_growth_uses_same_quarter_prev_year(good_pit):
    # 2024-06-01 시점: 최신=2024-03-31(ni 1200), 전년 동분기=2023-03-31(ni 800) → +50%
    g = good_pit.yoy_net_income_growth_at(pd.Timestamp("2024-06-01"))
    assert g == pytest.approx(0.5)


def test_yoy_none_when_prev_year_missing(good_pit):
    # 2023-08-01 시점: 최신=2023-03-31, 전년 분기 없음 → None (fabrication 금지)
    assert good_pit.yoy_net_income_growth_at(pd.Timestamp("2023-08-01")) is None


def test_pe_pb_at(good_pit):
    d = pd.Timestamp("2024-06-01")
    assert good_pit.pe_at(d, price=48000.0) == pytest.approx(48000.0 / (100.0 * 4))
    assert good_pit.pb_at(d, price=48000.0) == pytest.approx(48000.0 / 2000.0)
    assert good_pit.pe_at(pd.Timestamp("2023-04-01"), price=100.0) is None


def test_coverage_span(good_pit):
    # coverage: (첫 분기 available_from, 마지막 분기말 + 1분기)
    cov = good_pit.coverage()
    assert cov is not None
    start, end = cov
    assert start == pd.Timestamp("2023-03-31") + pd.Timedelta(days=45)
    assert end == pd.Timestamp("2024-03-31") + pd.DateOffset(months=3)

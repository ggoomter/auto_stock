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


def test_find_amount_not_polluted_by_nonflow_accounts():
    # 유동성 배열법(비유동 항목 먼저 나열) 기업에서 "유동자산" 검색이
    # "비유동자산" 행에 오매칭되지 않아야 함 (current_ratio 오염 방지)
    from app.services.pit_fundamentals import _find_amount
    df = pd.DataFrame([
        {"sj_div": "BS", "account_nm": "비유동자산", "thstrm_amount": "999000"},
        {"sj_div": "BS", "account_nm": "비유동부채", "thstrm_amount": "888000"},
        {"sj_div": "BS", "account_nm": "유동자산", "thstrm_amount": "111000"},
        {"sj_div": "BS", "account_nm": "유동부채", "thstrm_amount": "222000"},
        # 당기순이익: 귀속 내역 행이 총액보다 먼저 나열된 경우도 방어
        {"sj_div": "IS", "account_nm": "지배기업 소유주지분에 귀속되는 당기순이익", "thstrm_amount": "777"},
        {"sj_div": "IS", "account_nm": "당기순이익(손실)", "thstrm_amount": "555"},
    ])
    assert _find_amount(df, "유동자산", sj_div=("BS",)) == 111000.0
    assert _find_amount(df, "유동부채", sj_div=("BS",)) == 222000.0
    assert _find_amount(df, "당기순이익", sj_div=("IS", "CIS")) == 555.0


def test_metrics_at_accepts_tz_aware(good_pit):
    # tz-aware Timestamp가 들어와도 비교 오류 없이 동작해야 함
    m = good_pit.metrics_at(pd.Timestamp("2024-04-30", tz="Asia/Seoul"))
    assert m is not None
    assert m.quarter_end == pd.Timestamp("2023-12-31")


def test_coverage_span(good_pit):
    # coverage: (첫 분기 available_from, 마지막 분기말 + 1분기)
    cov = good_pit.coverage()
    assert cov is not None
    start, end = cov
    assert start == pd.Timestamp("2023-03-31") + pd.Timedelta(days=45)
    assert end == pd.Timestamp("2024-03-31") + pd.DateOffset(months=3)

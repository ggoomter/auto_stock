"""look-ahead 가드 회귀 테스트 — 공시 전 날짜에 그 분기 재무로 매수 판정이 나오면 실패

핵심 계약(Task 3):
- check_*_criteria_at_date(as_of_date, price)는 point-in-time 데이터(_pit)만 사용.
- 데이터 없음(pit None / metrics_at None / 필요한 지표 None) → 무조건 False.
- 기존의 "데이터 없으면 True 통과" 로직 전면 폐지.

네트워크 차단: FundamentalAnalyzer.__new__로 __init__(yfinance/DART 접속) 우회하고
_pit에 합성 픽스처를 직접 주입한다.
"""
import pandas as pd
import pytest

from app.services.pit_fundamentals import PointInTimeFundamentals, QuarterMetrics


def _analyzer_with_pit(pit):
    """__init__(네트워크) 우회하고 _pit 주입한 analyzer 생성"""
    from app.services.fundamental_analysis import FundamentalAnalyzer
    analyzer = FundamentalAnalyzer.__new__(FundamentalAnalyzer)
    analyzer.symbol = "005930.KS"
    analyzer.is_korean = True
    analyzer.stock_code = "005930"
    analyzer._pit = pit
    return analyzer


def _pit_from(quarters):
    return PointInTimeFundamentals("005930.KS", quarters)


def _quarter(end, eps=100.0, bps=2000.0, roe=0.20, dte=0.3, ni=1000.0,
             current_ratio=2.0):
    end = pd.Timestamp(end)
    return QuarterMetrics(
        quarter_end=end,
        available_from=end + pd.Timedelta(days=45),
        eps=eps, bps=bps, roe=roe, debt_to_equity=dte,
        net_income=ni, current_ratio=current_ratio,
    )


# ========== Buffett ==========

def test_no_pass_before_first_disclosure(good_pit):
    """첫 공시(2023-05-15) 전에는 metrics_at None → False (기존엔 True 통과 버그)"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2023-04-01"), price=10000.0) is False


def test_pass_after_disclosure_when_criteria_met(good_pit):
    """공시 후 + 모든 조건 충족 시 True.

    good_pit: roe 0.20, d/e 0.3, eps 100(연환산 400), bps 2000.
    price 5000 → PE 12.5(<25), PB 2.5(<3) 통과.
    """
    a = _analyzer_with_pit(good_pit)
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is True


def test_missing_price_fails_not_passes(good_pit):
    """price None → PE/PB 판정 불가 → False (스킵하고 통과시키면 안 됨)"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=None) is False


def test_buffett_high_pe_fails(good_pit):
    """PE가 25 이상이면 False (price 매우 높음)"""
    a = _analyzer_with_pit(good_pit)
    # price 12000 → PE 30(>25) → False
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=12000.0) is False


def test_buffett_low_roe_fails():
    """roe <= 0.15 이면 False"""
    pit = _pit_from([
        _quarter("2023-12-31", roe=0.10, ni=1000.0),
        _quarter("2024-03-31", roe=0.10, ni=1200.0),
    ])
    a = _analyzer_with_pit(pit)
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is False


def test_buffett_pit_none_always_false():
    """pit build 실패(None) → 항상 False"""
    a = _analyzer_with_pit(None)
    # _pit None + build 시도해도(주입 없음) 네트워크 없이 False 여야 하므로
    # _pit_build_failed 플래그로 강제 실패 처리
    a._pit_build_failed = True
    assert a.check_buffett_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is False


# ========== Lynch ==========

def test_lynch_requires_real_growth(good_pit):
    """전년 동분기 없는 시점 → growth None → False (기존엔 True 통과)"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_lynch_criteria_at_date(
        pd.Timestamp("2023-08-01"), price=1000.0) is False


def test_lynch_pass_when_growth_and_peg(good_pit):
    """growth +50%(>20%), PEG<1.0 이면 True.

    2024-06-01: growth 0.5(2024Q1 ni1200 vs 2023Q1 ni800).
    price 6000 → PE 15, PEG = 15/(0.5*100) = 0.3 (<1.0) → True.
    """
    a = _analyzer_with_pit(good_pit)
    assert a.check_lynch_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=6000.0) is True


def test_lynch_missing_price_fails(good_pit):
    """price None → PEG 계산 불가 → False"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_lynch_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=None) is False


def test_lynch_high_peg_fails(good_pit):
    """PEG >= 1.0 이면 False (price 높아 PE 큼)"""
    a = _analyzer_with_pit(good_pit)
    # price 24000 → PE 60, PEG = 60/50 = 1.2 (>1.0) → False
    assert a.check_lynch_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=24000.0) is False


# ========== Graham ==========

def test_graham_pass_when_deep_value():
    """PB<0.67 + current_ratio>2.0 → True"""
    pit = _pit_from([
        _quarter("2023-12-31", bps=20000.0, current_ratio=2.5, ni=1000.0),
        _quarter("2024-03-31", bps=20000.0, current_ratio=2.5, ni=1200.0),
    ])
    a = _analyzer_with_pit(pit)
    # price 10000, bps 20000 → PB 0.5(<0.67), current_ratio 2.5(>2.0) → True
    assert a.check_graham_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=10000.0) is True


def test_graham_current_ratio_none_fails():
    """current_ratio None → False (둘 중 하나라도 None → False)"""
    pit = _pit_from([
        _quarter("2023-12-31", bps=20000.0, current_ratio=None, ni=1000.0),
        _quarter("2024-03-31", bps=20000.0, current_ratio=None, ni=1200.0),
    ])
    a = _analyzer_with_pit(pit)
    assert a.check_graham_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=10000.0) is False


def test_graham_high_pb_fails():
    """PB >= 0.67 이면 False"""
    pit = _pit_from([
        _quarter("2023-12-31", bps=2000.0, current_ratio=2.5, ni=1000.0),
        _quarter("2024-03-31", bps=2000.0, current_ratio=2.5, ni=1200.0),
    ])
    a = _analyzer_with_pit(pit)
    # price 5000, bps 2000 → PB 2.5(>0.67) → False
    assert a.check_graham_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is False


# ========== O'Neil ==========

def test_oneil_pass_when_high_growth(good_pit):
    """growth 0.5(>0.25) → True"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_oneil_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is True


def test_oneil_growth_none_fails(good_pit):
    """전년 동분기 없음 → growth None → False"""
    a = _analyzer_with_pit(good_pit)
    assert a.check_oneil_criteria_at_date(
        pd.Timestamp("2023-08-01"), price=1000.0) is False


def test_oneil_growth_boundary_fails():
    """growth 0.25 경계 — 초과가 아니면(>0.25) False.

    2024Q1 ni1250 vs 2023Q1 ni1000 → growth 0.25 정확 → False.
    """
    pit = _pit_from([
        _quarter("2023-03-31", ni=1000.0),
        _quarter("2023-06-30", ni=1000.0),
        _quarter("2023-09-30", ni=1000.0),
        _quarter("2023-12-31", ni=1000.0),
        _quarter("2024-03-31", ni=1250.0),
    ])
    a = _analyzer_with_pit(pit)
    assert a.check_oneil_criteria_at_date(
        pd.Timestamp("2024-06-01"), price=5000.0) is False


# ========== fundamental_coverage ==========

def test_fundamental_coverage_returns_iso_dates(good_pit):
    """pit coverage를 ISO 날짜 문자열 튜플로 반환"""
    a = _analyzer_with_pit(good_pit)
    cov = a.fundamental_coverage()
    assert cov is not None
    start, end = cov
    assert start == "2023-05-15"  # 2023-03-31 + 45일
    assert isinstance(start, str) and isinstance(end, str)


def test_fundamental_coverage_none_when_no_pit():
    """pit 없으면 None"""
    a = _analyzer_with_pit(None)
    assert a.fundamental_coverage() is None

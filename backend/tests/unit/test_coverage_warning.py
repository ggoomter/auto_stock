"""Task 4: 펀더멘털 검증 가능 구간 응답 노출 테스트

계약:
- format_coverage_warning(coverage): coverage 튜플/None → 사용자 경고 문자열.
- Buffett/Lynch/Graham/O'Neil 전략의 generate_signals가 끝나면
  self.last_fundamental_coverage 에 analyzer.fundamental_coverage() 결과를 저장.
- 전역 싱글톤이므로 generate_signals 시작 시 None으로 리셋(이전 요청 잔존 방지).

네트워크 차단: master_strategies.FundamentalAnalyzer 를 가짜로 monkeypatch.
"""
import pandas as pd
import pytest

from app.services import master_strategies
from app.services.master_strategies import (
    format_coverage_warning,
    BuffettStrategy,
    LynchStrategy,
    GrahamStrategy,
    ONeilStrategy,
)


# ========== format_coverage_warning ==========

def test_format_coverage_warning_with_coverage():
    """coverage 튜플 → 구간 표시 문자열"""
    msg = format_coverage_warning(("2023-05-15", "2026-07-03"))
    assert msg == "펀더멘털 검증 가능 구간: 2023-05-15 ~ 2026-07-03 (이전 구간은 매수 신호 없음)"


def test_format_coverage_warning_none():
    """coverage None → 데이터 없음 문자열"""
    msg = format_coverage_warning(None)
    assert msg == "펀더멘털 시점별 데이터 없음 — 이 백테스트는 매수 신호가 생성되지 않았습니다"


# ========== 전략의 last_fundamental_coverage 저장/리셋 ==========

class _FakeAnalyzer:
    """네트워크 없이 check_*는 모두 False, coverage는 지정값 반환"""

    coverage_value = ("2023-05-15", "2026-07-03")

    def __init__(self, symbol):
        self.symbol = symbol

    def _false(self, *args, **kwargs):
        return False

    check_buffett_criteria_at_date = _false
    check_lynch_criteria_at_date = _false
    check_graham_criteria_at_date = _false
    check_oneil_criteria_at_date = _false

    def fundamental_coverage(self):
        return type(self).coverage_value


def _price_data(rows=5):
    idx = pd.date_range("2024-01-01", periods=rows, freq="D")
    return pd.DataFrame(
        {"close": [10000.0 + i * 10 for i in range(rows)],
         "volume": [1000.0] * rows},
        index=idx,
    )


@pytest.mark.parametrize("strategy_cls", [
    BuffettStrategy, LynchStrategy, GrahamStrategy, ONeilStrategy,
])
def test_strategy_sets_last_fundamental_coverage(monkeypatch, strategy_cls):
    """generate_signals 후 last_fundamental_coverage 에 coverage 저장"""
    monkeypatch.setattr(master_strategies, "FundamentalAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(_FakeAnalyzer, "coverage_value", ("2023-05-15", "2026-07-03"))

    strategy = strategy_cls()
    entry, exit_ = strategy.generate_signals("005930.KS", _price_data())

    # 반환 시그니처 유지
    assert isinstance(entry, pd.Series) and isinstance(exit_, pd.Series)
    assert strategy.last_fundamental_coverage == ("2023-05-15", "2026-07-03")


@pytest.mark.parametrize("strategy_cls", [
    BuffettStrategy, LynchStrategy, GrahamStrategy, ONeilStrategy,
])
def test_strategy_resets_coverage_between_runs(monkeypatch, strategy_cls):
    """이전 요청 coverage가 새 요청(coverage None)에 새면 안 됨"""
    monkeypatch.setattr(master_strategies, "FundamentalAnalyzer", _FakeAnalyzer)
    monkeypatch.setattr(_FakeAnalyzer, "coverage_value", None)

    strategy = strategy_cls()
    strategy.last_fundamental_coverage = ("2020-01-01", "2020-12-31")  # 이전 잔존값

    strategy.generate_signals("005930.KS", _price_data())

    assert strategy.last_fundamental_coverage is None

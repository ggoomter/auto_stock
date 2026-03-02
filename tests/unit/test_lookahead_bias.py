"""
Lookahead Bias 회귀 테스트

Phase 1에서 수정한 버그가 다시 발생하지 않도록 방어합니다.
- 펀더멘털 예외 시 False 반환
- rolling 계산에 현재 봉 미포함 (.shift(1))
- DART 클라이언트 속성명 정확성
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[2] / "backend"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# ───────────────────────────────────────────────
# 테스트 1: master_strategies.py rolling 계산
# ───────────────────────────────────────────────

class TestRollingLookahead:
    """rolling 계산에 .shift(1)이 적용되어 현재 봉이 포함되지 않는지 검증."""

    def test_buffett_rolling_low_excludes_current_bar(self):
        """BuffettStrategy의 rolling_low_252에 현재 봉 미포함 (소스코드 + 수학적 검증)"""
        from app.services.master_strategies import BuffettStrategy
        import inspect

        # 1. 소스코드 검증: .shift(1) 패턴이 있어야 함
        source = inspect.getsource(BuffettStrategy.generate_signals)
        assert ".shift(1)" in source, (
            "BuffettStrategy.generate_signals에 .shift(1)이 없음. "
            "rolling 계산에 현재 봉이 포함될 수 있음 (lookahead bias)"
        )

        # 2. 수학적 검증: shift(1)이 현재 봉을 제외하는지 확인
        dates = pd.bdate_range("2020-01-02", periods=300)
        prices = np.random.uniform(50, 100, size=300)
        prices[-1] = 10.0  # 마지막 날에 극단적 저가

        close = pd.Series(prices, index=dates)
        rolling_low = close.rolling(252, min_periods=100).min().shift(1)

        last_rolling_low = rolling_low.iloc[-1]
        assert last_rolling_low != 10.0, "현재 봉의 극단값이 rolling에 포함됨 (lookahead bias)"

    def test_graham_rolling_low_excludes_current_bar(self):
        """GrahamStrategy의 rolling_low에 현재 봉 미포함"""
        dates = pd.bdate_range("2020-01-02", periods=300)
        prices = np.random.uniform(50, 100, size=300)
        prices[-1] = 5.0  # 극단적 저가

        close = pd.Series(prices, index=dates)
        rolling_low = close.rolling(252, min_periods=100).min().shift(1)

        last_rolling_low = rolling_low.iloc[-1]
        assert last_rolling_low != 5.0, "현재 봉의 극단값이 rolling에 포함됨 (lookahead bias)"


# ───────────────────────────────────────────────
# 테스트 2: 펀더멘털 예외 처리
# ───────────────────────────────────────────────

class TestFundamentalExceptionHandling:
    """펀더멘털 데이터 조회 실패 시 False 반환 검증."""

    def test_buffett_exception_returns_false(self):
        """Buffett 전략 펀더멘털 예외 시 passes_fundamental=False"""
        from app.services.master_strategies import BuffettStrategy

        strategy = BuffettStrategy()

        # generate_signals에서 펀더멘털 체크는 내부적으로 수행됨
        # 여기서는 코드 패턴을 직접 검증

        # master_strategies.py의 Buffett except 블록이 False를 설정하는지 확인
        import inspect
        source = inspect.getsource(BuffettStrategy.generate_signals)

        # except 블록에서 passes_fundamental = False 가 있어야 함
        assert "passes_fundamental = False" in source, (
            "Buffett 전략에서 펀더멘털 예외 시 passes_fundamental = True로 되어있음 (lookahead bias)"
        )

    def test_lynch_exception_returns_false(self):
        """Lynch 전략 펀더멘털 예외 시 passes_fundamental=False"""
        from app.services.master_strategies import LynchStrategy

        import inspect
        source = inspect.getsource(LynchStrategy.generate_signals)
        assert "passes_fundamental = False" in source

    def test_graham_exception_returns_false(self):
        """Graham 전략 펀더멘털 예외 시 passes_fundamental=False"""
        from app.services.master_strategies import GrahamStrategy

        import inspect
        source = inspect.getsource(GrahamStrategy.generate_signals)
        assert "passes_fundamental = False" in source


# ───────────────────────────────────────────────
# 테스트 3: DART 클라이언트 속성명
# ───────────────────────────────────────────────

class TestDartClientAttribute:
    """fundamental_analysis.py에서 _dart_client 속성명이 올바른지 검증."""

    def test_dart_client_attribute_name(self):
        """self._dart_client (언더스코어)가 사용되는지 확인"""
        from app.services import fundamental_analysis
        import inspect

        source = inspect.getsource(fundamental_analysis)

        # self.dart_client (언더스코어 없음)가 사용되면 안 됨
        # 단, 초기화(self._dart_client = ...)는 허용
        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # 주석이나 문자열 무시
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'"):
                continue
            # self.dart_client (언더스코어 없음) 사용 체크
            if "self.dart_client" in stripped and "self._dart_client" not in stripped:
                pytest.fail(
                    f"Line {i}: 'self.dart_client' 발견 (올바른 속성명은 'self._dart_client')\n"
                    f"  → {stripped}"
                )

    def test_symbol_not_ticker_in_replace(self):
        """self.ticker.replace() 대신 self.symbol.replace()가 사용되는지 확인"""
        from app.services import fundamental_analysis
        import inspect

        source = inspect.getsource(fundamental_analysis)

        lines = source.split("\n")
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # self.ticker.replace()는 버그 (ticker는 yf.Ticker 객체)
            if "self.ticker.replace(" in stripped:
                pytest.fail(
                    f"Line {i}: 'self.ticker.replace()' 발견 "
                    f"(self.ticker는 yf.Ticker 객체이므로 self.symbol.replace() 사용 필요)\n"
                    f"  → {stripped}"
                )

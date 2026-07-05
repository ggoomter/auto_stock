"""stock_screener가 존재하지 않는 ScreenerType 멤버를 참조하지 않는지 검증.

배경: `screen_by_market`에서 후보가 50개를 초과하면 정렬 분기를 타는데,
과거 코드가 enum에 없는 `ScreenerType.GRAHAM`을 참조해 후보 50개 초과 시
AttributeError로 크래시했다. 이 경로는 auto_trading_engine._auto_stock_discovery가
실사용 중이므로 회귀 방지가 필요하다.
"""

import inspect
import re
from unittest.mock import MagicMock, patch

import pandas as pd

from app.services import stock_screener
from app.services.stock_screener import ScreenerType, StockScreener


def test_screener_type_references_are_valid():
    """소스에서 참조하는 모든 ScreenerType 멤버가 실제 enum에 존재해야 한다."""
    src = inspect.getsource(stock_screener)
    referenced = set(re.findall(r"ScreenerType\.([A-Z_]+)", src))
    valid = {m.name for m in ScreenerType}
    assert referenced.issubset(valid), (
        f"존재하지 않는 멤버 참조: {referenced - valid}"
    )


def test_screen_by_market_no_crash_over_50_candidates():
    """후보 51개(50개 초과) 상황에서 정렬 분기를 타도 크래시하지 않아야 한다."""
    # 51개 가짜 종목 펀더멘털 DataFrame (index = 종목코드)
    tickers = [f"{i:06d}" for i in range(51)]
    # PER은 VALUE 기준(max_pe=15)을 모두 통과하되 정렬 가능하도록 구분값 부여
    df = pd.DataFrame(
        {
            "PER": [5.0 + i * 0.1 for i in range(51)],
            "PBR": [0.5 for _ in range(51)],
            "DIV": [3.0 for _ in range(51)],
        },
        index=tickers,
    )

    screener = StockScreener()

    mock_fetcher = MagicMock()
    mock_fetcher.get_market_fundamentals.return_value = df

    with patch.object(
        stock_screener, "get_korean_stock_fetcher", return_value=mock_fetcher
    ), patch.object(
        StockScreener, "screen_stocks", return_value=[]
    ) as mock_screen:
        # VALUE 경로: 50개 초과 시 PER 정렬 분기를 탄다
        result = screener.screen_market(
            market="KOSPI", screener_type=ScreenerType.VALUE
        )

    assert result == []
    # screen_stocks에 정확히 50개만 넘어가야 한다 (상위 절삭)
    passed_candidates = mock_screen.call_args[0][0]
    assert len(passed_candidates) == 50

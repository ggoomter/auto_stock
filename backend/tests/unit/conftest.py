"""unit 테스트 공용 픽스처 — point-in-time 재무 지표 (Task 2, Task 3 공용)"""
import pandas as pd
import pytest


def _q(end, eps=100.0, bps=2000.0, roe=0.12, ni=1000.0):
    """합성 QuarterMetrics 생성 헬퍼 (available_from = 분기말 + 45일)"""
    from app.services.pit_fundamentals import QuarterMetrics
    end = pd.Timestamp(end)
    return QuarterMetrics(
        quarter_end=end,
        available_from=end + pd.Timedelta(days=45),
        eps=eps, bps=bps, roe=roe, debt_to_equity=0.3,
        net_income=ni, current_ratio=2.0,
    )


@pytest.fixture
def good_pit():
    """정상 5분기(2023Q1~2024Q1) point-in-time 픽스처"""
    from app.services.pit_fundamentals import PointInTimeFundamentals
    quarters = [
        _q("2023-03-31", ni=800.0), _q("2023-06-30", ni=900.0),
        _q("2023-09-30", ni=950.0), _q("2023-12-31", ni=1000.0),
        _q("2024-03-31", ni=1200.0),
    ]
    return PointInTimeFundamentals("005930.KS", quarters)

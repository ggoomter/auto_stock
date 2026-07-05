"""
가격 시계열(OHLCV) API 라우트 (읽기 전용)

데이터 소스는 paper_reconcile.fetch_daily_pykrx를 재사용한다
(한국=pykrx / 미국=yfinance, 실패 시 빈 DataFrame, 소문자 컬럼).
테스트에서 이 모듈의 fetch_daily_pykrx를 monkeypatch 해 합성 DF를 주입한다.
"""
import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..core.logging_config import logger
from ..services.paper_reconcile import fetch_daily_pykrx

router = APIRouter()

# 일반 사용자에게 노출하는 안전한 500 메시지 (내부 예외 문자열 은닉)
_GENERIC_ERROR = "일시적인 오류가 발생했습니다"


def _bar_date(idx) -> str:
    """DataFrame index(날짜) → 'YYYY-MM-DD' 문자열."""
    if isinstance(idx, str):
        return idx[:10]
    return pd.Timestamp(idx).strftime("%Y-%m-%d")


@router.get("/price-history")
async def get_price_history(
    symbol: str = Query(...),
    start: str = Query(...),
    end: str = Query(...),
):
    """일봉 OHLCV 시계열 조회.

    빈 결과는 404가 아니라 200 + count 0으로 반환한다(정상적으로 데이터가
    아직 없을 수 있음). 내부 예외는 로그만 남기고 일반 메시지로 500.
    """
    try:
        df = fetch_daily_pykrx(symbol, start, end)
        bars = []
        if df is not None and len(df) > 0:
            has_volume = "volume" in df.columns
            for idx, row in df.sort_index().iterrows():
                bars.append({
                    "date": _bar_date(idx),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": int(row["volume"]) if has_volume else 0,
                })
        return {"symbol": symbol, "count": len(bars), "bars": bars}
    except Exception as e:
        logger.error(
            f"가격 시계열 조회 실패 (symbol={symbol}, start={start}, end={end}): {e}"
        )
        raise HTTPException(status_code=500, detail=_GENERIC_ERROR)

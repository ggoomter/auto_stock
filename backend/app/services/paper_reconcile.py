"""모의투자 오프라인 기간 보수적 정산(reconcile).

서버가 꺼져 있던 기간의 일봉을 사후에 훑어, 그동안 손절/익절 조건이
터치됐다면 보수적 규칙으로 청산 처리한다. 장중 엔진을 대체하는 것이 아니라,
'놓친 청산'만 뒤늦게 결정론적으로 메꾸는 용도.

보수 원칙(낙관 금지):
  - 손절 터치(low <= stop): 청산가 = min(그 봉 open, stop) 호가단위 내림
    → 갭하락 개장이면 개장가(더 불리)로 체결.
  - 익절 터치(high >= take): 청산가 = take 호가단위 내림
    → 갭상승 개장이어도 목표가(더 낮은 값) 사용.
  - 같은 봉 동시 터치 → 손절 우선 (백테스트 엔진 backtest.py와 동일 규칙).
"""
from datetime import datetime, timedelta
from typing import Callable, Optional

import pandas as pd

from ..utils.tick_size import round_to_tick_down
from .paper_execution import is_korean_symbol


def reconcile_positions(repo,
                        fetch_daily: Callable[[str, str, str], pd.DataFrame],
                        as_of: str) -> dict:
    """open 포지션 각각을 오프라인 기간 일봉으로 정산.

    Args:
        repo: PaperTradingRepository (list_open_positions / close_position 사용)
        fetch_daily: (symbol, start, end) → 소문자 open/high/low/close DataFrame
                     (주입 가능 — 테스트에서 합성 DF 주입, 실패/빈 시 빈 DF)
        as_of: 정산 종료일 'YYYY-MM-DD'

    Returns:
        {"checked": n, "closed": m, "skipped": s, "details": [...]}
    """
    checked = closed = skipped = 0
    details: list[dict] = []

    for pos in repo.list_open_positions():
        checked += 1
        symbol = pos["symbol"]
        # 진입 당일은 엔진이 이미 처리(또는 진입가 자체가 그날 체결) → 다음 날부터
        start = _next_day(pos["entry_at"])

        try:
            bars = fetch_daily(symbol, start, as_of)
        except Exception as exc:  # 조회 실패 → 건너뛰고 기록 (침묵 실패 금지)
            skipped += 1
            details.append({"id": pos["id"], "symbol": symbol,
                            "status": "skipped", "reason": f"조회 실패: {exc}"})
            continue

        if bars is None or len(bars) == 0:
            skipped += 1
            details.append({"id": pos["id"], "symbol": symbol,
                            "status": "skipped", "reason": "데이터 없음"})
            continue

        hit = _scan_bars(pos, bars)
        if hit is None:
            details.append({"id": pos["id"], "symbol": symbol, "status": "held"})
            continue

        exit_price, exit_reason, exit_at = hit
        repo.close_position(pos["id"], exit_price, exit_reason, exit_at)
        closed += 1
        details.append({"id": pos["id"], "symbol": symbol, "status": "closed",
                        "exit_price": exit_price, "exit_reason": exit_reason,
                        "exit_at": exit_at})

    return {"checked": checked, "closed": closed,
            "skipped": skipped, "details": details}


def _scan_bars(pos: dict, bars: pd.DataFrame) -> Optional[tuple]:
    """날짜 오름차순으로 첫 손절/익절 터치를 찾는다. 없으면 None.

    반환: (exit_price, exit_reason, exit_at)
    """
    korean = is_korean_symbol(pos["symbol"])
    stop_loss = pos.get("stop_loss")
    take_profit = pos.get("take_profit")

    for idx, row in bars.sort_index().iterrows():
        open_price = float(row["open"])
        high = float(row["high"])
        low = float(row["low"])
        exit_at = _exit_at(idx)

        # 1) 손절 우선: min(open, stop) — 갭하락이면 개장가(더 불리)
        if stop_loss is not None and low <= stop_loss:
            exit_price = round_to_tick_down(min(open_price, stop_loss), korean)
            return exit_price, "손절매(정산)", exit_at

        # 2) 익절: take_profit 그대로 — 갭상승이어도 목표가(더 낮은 값)
        if take_profit is not None and high >= take_profit:
            exit_price = round_to_tick_down(take_profit, korean)
            return exit_price, "익절매(정산)", exit_at

    return None


def _next_day(entry_at: str) -> str:
    """entry_at 'YYYY-MM-DDTHH:MM:SS'의 다음 날짜 'YYYY-MM-DD'."""
    day = datetime.strptime(entry_at[:10], "%Y-%m-%d") + timedelta(days=1)
    return day.strftime("%Y-%m-%d")


def _exit_at(idx) -> str:
    """봉 날짜(index) → 'YYYY-MM-DDT15:30:00' (장 마감 시각)."""
    if isinstance(idx, str):
        date_str = idx[:10]
    else:
        date_str = pd.Timestamp(idx).strftime("%Y-%m-%d")
    return date_str + "T15:30:00"


def fetch_daily_pykrx(symbol: str, start: str, end: str) -> pd.DataFrame:
    """오프라인 기간 일봉 조회. 한국=pykrx, 미국=yfinance. 실패 시 빈 DataFrame.

    Args:
        symbol: 종목 코드 (한국: '005930.KS'/'005930', 미국: 'AAPL')
        start, end: 'YYYY-MM-DD' 또는 'YYYYMMDD'
    """
    if is_korean_symbol(symbol):
        return _fetch_korean(symbol, start, end)
    return _fetch_us(symbol, start, end)


def _fetch_korean(symbol: str, start: str, end: str) -> pd.DataFrame:
    code = symbol.replace(".KS", "").replace(".KQ", "")
    s = start.replace("-", "")
    e = end.replace("-", "")
    try:
        from pykrx import stock
        df = stock.get_market_ohlcv(s, e, code)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.rename(columns={"시가": "open", "고가": "high", "저가": "low",
                              "종가": "close", "거래량": "volume"})


def _fetch_us(symbol: str, start: str, end: str) -> pd.DataFrame:
    try:
        import yfinance as yf
        df = yf.Ticker(symbol).history(start=start, end=end)
    except Exception:
        return pd.DataFrame()
    if df is None or df.empty:
        return pd.DataFrame()
    return df.rename(columns={c: str(c).lower() for c in df.columns})

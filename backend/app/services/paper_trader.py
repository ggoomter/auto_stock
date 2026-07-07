"""페이퍼 트레이딩 자동화 — 전진 검증(forward validation)의 실행부

백테스트(과거 시험)와 달리 아직 오지 않은 데이터로 시스템을 검증한다.
매수·매도 규칙은 화면의 추천/매도 진단과 동일:

- run_paper_entry: 직전 거래일 추천(신고가 근접 주도주)을 오늘 시가에 가상 매수.
  백테스트와 같은 '신호 익일 시가 진입' 원칙. 체결은 보수적(슬리피지 가산 + 호가 올림),
  배분은 균등 1/N, 초기 손절 -8%.
- run_stop_update: 보유 종목의 매도 기준선(샹들리에 22일고점-2.5×ATR, 200일선) 중
  큰 값으로 stop_loss를 끌어올린다(인상만 — 인하 금지). 실제 청산 체결은
  paper_reconcile의 보수 규칙(갭하락 시 시가 등)이 매일 수행한다.

v1 미지원(의도적 축소): 부분 익절(+20%/+40%) — 수량 분할 청산은 포지션 모델
확장이 필요해 docs/TODO.md에 이월.
"""
from __future__ import annotations

import math
from typing import Callable

import pandas as pd

from ..core.logging_config import logger
from ..utils.tick_size import round_to_tick_down
from .paper_execution import calculate_equal_weight_shares, is_korean_symbol, simulate_fill_price

# 진입 슬리피지 10bp — 백테스트(슬리피지 5bp + 수수료 10bp)의 보수적 근사
PAPER_SLIPPAGE = 0.001
# 초기 손절 -8% (livermore 검증 파라미터, sell_advisor와 동일)
INITIAL_STOP_PCT = 0.08
# 스탑 갱신 계산 파라미터 (sell_advisor와 동일해야 화면 진단과 일치)
CHANDELIER_WINDOW = 22
CHANDELIER_ATR_MULT = 2.5
MA_LONG = 200
_MIN_ROWS_FOR_STOPS = 220


def available_cash(repo, initial_capital: float) -> float:
    """가용 현금 = 초기자본 + 실현손익 - 보유 포지션 투자금 (별도 현금 원장 없이 유도)"""
    invested = sum(p["entry_price"] * p["quantity"] for p in repo.list_open_positions())
    return initial_capital + repo.total_realized_pnl() - invested


def run_paper_entry(repo, reco_repo, fetch_daily: Callable[[str, str, str], pd.DataFrame],
                    as_of: str, initial_capital: float, max_positions: int) -> dict:
    """직전 거래일 추천을 오늘(as_of) 시가에 가상 매수.

    반환: {"rec_date", "candidates", "opened", "skipped_held",
           "skipped_cash", "skipped_data", "skipped_slots"}
    """
    stats = {"rec_date": None, "candidates": 0, "opened": 0, "skipped_held": 0,
             "skipped_cash": 0, "skipped_data": 0, "skipped_slots": 0}

    rec_date = reco_repo.latest_date_before(as_of)
    if rec_date is None:
        return stats  # 아직 추천 이력 없음
    stats["rec_date"] = rec_date

    open_positions = repo.list_open_positions()
    open_symbols = {p["symbol"] for p in open_positions}
    slots = max_positions - len(open_positions)
    cash = available_cash(repo, initial_capital)
    equity = initial_capital + repo.total_realized_pnl()

    for rec in reco_repo.list_by_date(rec_date):  # score 내림차순
        stats["candidates"] += 1
        symbol = rec.get("symbol")
        if not symbol:
            continue
        if symbol in open_symbols:
            stats["skipped_held"] += 1
            continue
        if slots <= 0:
            stats["skipped_slots"] += 1
            continue

        # as_of 당일 봉의 시가 조회 (없으면 데이터 스킵 — 휴장/미개장/조회실패)
        try:
            bars = fetch_daily(symbol, as_of, as_of)
        except Exception as exc:  # noqa: BLE001 - 종목별 실패 격리
            logger.warning("페이퍼 진입 시가 조회 실패 %s: %s", symbol, exc)
            bars = None
        if bars is None or len(bars) == 0:
            stats["skipped_data"] += 1
            continue
        open_price = float(bars.sort_index().iloc[-1]["open"])
        if not math.isfinite(open_price) or open_price <= 0:
            stats["skipped_data"] += 1
            continue

        fill = simulate_fill_price(open_price, "buy", PAPER_SLIPPAGE, symbol)
        shares = calculate_equal_weight_shares(equity, max_positions, fill)
        if shares * fill > cash:  # 현금 부족 시 가능한 만큼으로 축소
            shares = int(cash // fill)
        if shares <= 0:
            stats["skipped_cash"] += 1
            continue

        stop = round_to_tick_down(fill * (1 - INITIAL_STOP_PCT), is_korean_symbol(symbol))
        repo.open_position(
            symbol=symbol, quantity=shares, entry_price=fill,
            strategy="reco_nearhigh_v1", stop_loss=stop, take_profit=None,
            entry_at=f"{as_of}T09:00:00",
        )
        cash -= shares * fill
        slots -= 1
        open_symbols.add(symbol)
        stats["opened"] += 1
        logger.info(f"페이퍼 진입 {symbol} {shares}주 @ {fill:,.0f} (손절 {stop:,.0f})")

    return stats


def compute_dynamic_stop(bars: pd.DataFrame) -> float | None:
    """샹들리에(22일 최고 종가 - 2.5×ATR22)와 200일선 중 큰 값. 데이터 부족 시 None."""
    if bars is None or len(bars) < _MIN_ROWS_FOR_STOPS:
        return None
    close = bars["close"].astype(float)
    high = bars["high"].astype(float) if "high" in bars.columns else close
    low = bars["low"].astype(float) if "low" in bars.columns else close

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(CHANDELIER_WINDOW).mean().iloc[-1])
    hh = float(close.rolling(CHANDELIER_WINDOW).max().iloc[-1])
    chandelier = hh - CHANDELIER_ATR_MULT * atr
    ma200 = float(close.rolling(MA_LONG).mean().iloc[-1])

    candidates = [v for v in (chandelier, ma200) if math.isfinite(v) and v > 0]
    return max(candidates) if candidates else None


def run_stop_update(repo, fetch_daily: Callable[[str, str, str], pd.DataFrame],
                    as_of: str) -> dict:
    """보유 포지션의 stop_loss를 매도 기준선으로 끌어올림 (인상만, 인하 금지).

    반환: {"checked", "raised", "skipped"}
    """
    stats = {"checked": 0, "raised": 0, "skipped": 0}
    start = (pd.Timestamp(as_of) - pd.Timedelta(days=450)).strftime("%Y-%m-%d")

    for pos in repo.list_open_positions():
        stats["checked"] += 1
        try:
            bars = fetch_daily(pos["symbol"], start, as_of)
            new_stop = compute_dynamic_stop(bars)
        except Exception as exc:  # noqa: BLE001 - 종목별 실패 격리
            logger.warning("페이퍼 스탑 갱신 실패 %s: %s", pos["symbol"], exc)
            new_stop = None
        if new_stop is None:
            stats["skipped"] += 1
            continue

        new_stop = round_to_tick_down(new_stop, is_korean_symbol(pos["symbol"]))
        current = pos.get("stop_loss") or 0.0
        if new_stop > current:
            repo.update_stops(pos["id"], new_stop,
                              pos.get("highest_price") or pos["entry_price"])
            stats["raised"] += 1

    return stats

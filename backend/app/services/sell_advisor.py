"""매도 판단 로직 (sell advisor)

"언제까지 들고 있다가 언제 파는가"의 답 — 날짜가 아니라 조건으로 판단한다.
검증된 규칙만 사용 (claudedocs/strategy_verification_2026-07-06.md):

1) 손절 (StopLoss): 현재가 <= 매수가 × (1 - 8%) → 전량 매도. 원금 방어가 최우선.
2) 추세 종료 (Chandelier): 종가 < 22일 최고 종가 - 2.5×ATR22 → 전량 매도.
   4차 검증 채택 — 고정 %보다 변동성 적응 청산이 CAGR·MDD·Sharpe 모두 개선.
3) 장기 추세 상실 (TrendBreak): 종가 < 200일 이동평균 → 전량 매도.
   매수 게이트(상승 추세)와 대칭 — 살 자격이 없어진 종목은 들 자격도 없다.
4) 부분 익절 (PartialProfit): +20% 도달 시 절반, +40% 도달 시 추가 1/4 제안.
   백테스트 엔진의 partial_rules와 동일.
5) 위 신호가 없으면 보유(hold) — 추세가 살아있는 한 파는 날짜는 정하지 않는다.
   (리버모어: "돈은 생각이 아니라 앉아 기다림이 벌었다")
"""
from __future__ import annotations

from typing import Optional

import pandas as pd

from ..core.logging_config import logger

# 검증된 파라미터 (livermore / livermore_atr / backtest 엔진과 동일)
STOP_LOSS_PCT = 0.08
CHANDELIER_WINDOW = 22
CHANDELIER_ATR_MULT = 2.5
MA_LONG = 200
PARTIAL_RULES = [(0.20, 0.50), (0.40, 0.25)]  # (수익률 임계, 매도 비중)
_MIN_ROWS = 220  # MA200 + ATR 계산 여유


def _cond(name: str, name_en: str, required: str, actual: str, passed: bool) -> dict:
    return {
        "condition_name": name,
        "condition_name_en": name_en,
        "required_value": required,
        "actual_value": actual,
        "passed": passed,  # True = 해당 매도/익절 신호 발생
    }


def evaluate_sell(entry_price: float, ohlcv: pd.DataFrame,
                  entry_date: Optional[str] = None) -> dict:
    """보유 종목의 매도 여부 판단.

    반환 dict:
    - action: "sell" | "partial_sell" | "hold" | "insufficient_data"
    - current_price, pnl_pct, holding_days(entry_date 제공 시)
    - checks: 조건별 판정 목록 (passed=True → 신호 발생)
    - levels: 매도 기준선 {stop_loss, chandelier, ma200} — hold일 때 감시 대상
    - summary: 한글 판단 요약
    """
    if entry_price is None or entry_price <= 0:
        raise ValueError("매수가(entry_price)는 0보다 커야 합니다.")

    clean = ohlcv.dropna(subset=[c for c in ("close",) if c in ohlcv.columns])
    if clean is None or len(clean) < _MIN_ROWS:
        return {
            "action": "insufficient_data",
            "summary": f"일봉 데이터가 {len(clean) if clean is not None else 0}개뿐입니다 "
                       f"(최소 {_MIN_ROWS}개 필요) — 200일선·ATR 기반 판단이 불가합니다.",
            "checks": [], "levels": {}, "current_price": None, "pnl_pct": None,
        }

    cols = {c.lower(): c for c in clean.columns}
    close = clean[cols["close"]].astype(float)
    high = clean[cols.get("high", cols["close"])].astype(float)
    low = clean[cols.get("low", cols["close"])].astype(float)

    current = float(close.iloc[-1])
    pnl_pct = current / entry_price - 1

    # 기준선 계산
    stop_level = entry_price * (1 - STOP_LOSS_PCT)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs(),
    ], axis=1).max(axis=1)
    atr = float(tr.rolling(CHANDELIER_WINDOW).mean().iloc[-1])
    hh = float(close.rolling(CHANDELIER_WINDOW).max().iloc[-1])
    chandelier_level = hh - CHANDELIER_ATR_MULT * atr
    ma200 = float(close.rolling(MA_LONG).mean().iloc[-1])

    checks = []

    # 1) 손절
    stop_hit = current <= stop_level
    checks.append(_cond(
        "손절선 (-8%)", "StopLoss",
        f"현재가 > {stop_level:,.0f} (매수가 -8%)",
        f"현재가 {current:,.0f} ({pnl_pct:+.1%})", stop_hit))

    # 2) 샹들리에 (추세 종료)
    chand_hit = current < chandelier_level
    checks.append(_cond(
        "추세 종료 (샹들리에)", "Chandelier",
        f"현재가 ≥ {chandelier_level:,.0f} (22일 고점 {hh:,.0f} - 2.5×ATR {atr:,.0f})",
        f"현재가 {current:,.0f}", chand_hit))

    # 3) 200일선 이탈
    trend_break = current < ma200
    checks.append(_cond(
        "장기 추세 (200일선)", "TrendBreak",
        f"현재가 ≥ 200일선 {ma200:,.0f}",
        f"현재가 {current:,.0f} (200일선 대비 {(current / ma200 - 1) * 100:+.1f}%)",
        trend_break))

    # 4) 부분 익절
    partial_msgs = []
    partial_hit = False
    for threshold, fraction in PARTIAL_RULES:
        hit = pnl_pct >= threshold
        partial_hit = partial_hit or hit
        if hit:
            partial_msgs.append(f"+{threshold:.0%} 도달 → 보유량의 {fraction:.0%} 익절")
    checks.append(_cond(
        "부분 익절 구간", "PartialProfit",
        "+20% 도달 시 절반, +40% 도달 시 추가 1/4",
        f"현재 수익률 {pnl_pct:+.1%}", partial_hit))

    holding_days = None
    if entry_date:
        try:
            holding_days = int((close.index[-1] - pd.Timestamp(entry_date)).days)
        except Exception:  # noqa: BLE001 - 날짜 형식 오류는 표시 생략
            holding_days = None

    levels = {
        "stop_loss": round(stop_level, 2),
        "chandelier": round(chandelier_level, 2),
        "ma200": round(ma200, 2),
    }

    # 판정: 전량 매도 신호가 하나라도 발생하면 sell (안전 우선)
    if stop_hit or chand_hit or trend_break:
        reasons = [c["condition_name"] for c in checks[:3] if c["passed"]]
        summary = (f"매도 신호 발생: {', '.join(reasons)}. "
                   f"검증된 규칙상 추세가 끝났거나 원금 방어선에 도달했습니다 — 전량 매도를 권고합니다.")
        action = "sell"
    elif partial_hit:
        summary = (f"추세는 살아있습니다 — 전량 매도는 이르지만 이익 보호를 위해 "
                   f"{' / '.join(partial_msgs)}를 권고합니다. 남은 물량은 추세 종료 신호까지 보유하세요.")
        action = "partial_sell"
    else:
        summary = ("보유 유지 — 매도할 날짜를 정하지 마세요. 아래 세 기준선 중 하나라도 "
                   "깨지는 날 파는 것입니다: "
                   f"① 손절선 {stop_level:,.0f} ② 추세 종료선 {chandelier_level:,.0f} "
                   f"③ 200일선 {ma200:,.0f}.")
        action = "hold"

    return {
        "action": action,
        "current_price": current,
        "pnl_pct": round(pnl_pct, 4),
        "holding_days": holding_days,
        "checks": checks,
        "levels": levels,
        "summary": summary,
        "as_of": str(close.index[-1].date()),
    }


def check_sell(symbol: str, entry_price: float,
               entry_date: Optional[str] = None) -> dict:
    """심볼로 시세를 조회해 매도 판단 (API 진입점)."""
    from datetime import datetime, timedelta
    from .indicators import load_sample_data

    end = datetime.now()
    start = end - timedelta(days=450)
    ohlcv = load_sample_data(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    verdict = evaluate_sell(entry_price, ohlcv, entry_date=entry_date)
    verdict["symbol"] = symbol
    return verdict

"""위기 매수 프로토콜 (crisis buying protocol)

시장 지수가 52주 고점 대비 트랜치 임계값까지 폭락하면 예비 현금의 일부를
시장 바스켓에 분할 투입하라는 신호를 발동한다. 손절 없음 · 장기 보유 전제.

실측 근거 (claudedocs/strategy_verification_2026-07-06.md):
- KR 균등가중 바스켓, 고점 -30% 매수: 2020-03 → 1년 +94.7%, 2022-06 → 2년 +25.2%
- US 균등가중 바스켓, 고점 -20% 매수: 5회 중 4회가 2년 후 +55~119%
- 빈도는 10년에 2~4회. 매수 후 추가 -17~-30% 하락을 견디는 설계가 필수
  (그래서 트랜치 분할 + 무손절 + 시장 단위).

1단계 구현 범위: 감지 → 이벤트 영속화(중복 발동 차단) → 알림.
페이퍼 계좌 자동 분할 매수는 2단계 (docs/TODO.md 참고).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Dict, List, Optional, Set

import pandas as pd

from ..core.logging_config import logger
from ..db.repositories import CrisisRepository

# 감시 대상 시장 지수 (yfinance 심볼)
MARKET_INDICES: Dict[str, str] = {
    "KR": "^KS11",   # KOSPI
    "US": "^GSPC",   # S&P 500
}

# (낙폭 임계값, 예비대 투입 비율) — 합계 1.0
# 1단계는 얕은 조정에도 걸리므로 작게, 깊은 폭락일수록 크게 투입한다.
TRANCHES: List[tuple] = [
    (-0.20, 0.30),  # 1단계: 고점 대비 -20% → 예비대의 30%
    (-0.30, 0.35),  # 2단계: -30% → 35%
    (-0.40, 0.35),  # 3단계: -40% → 35%
]

# 고점 대비 -2% 이내로 회복하면 위기 종료로 판정하고 재장전
_REARM_THRESHOLD = -0.02

# 낙폭 계산에 사용할 조회 구간 (52주 고점 기준 + 여유)
LOOKBACK_DAYS = 400


@dataclass
class CrisisAction:
    type: str                       # "deploy" | "rearm"
    stage: Optional[int]            # deploy: 1~3, rearm: None
    drawdown: float
    reserve_fraction: float = 0.0   # deploy 시 예비대 투입 비율


def compute_drawdown(index_series: pd.Series) -> float:
    """구간 내 최고점 대비 마지막 값의 낙폭 (0 이하 값)"""
    clean = index_series.dropna()
    if clean.empty:
        raise ValueError("지수 시계열이 비어있습니다.")
    return float(clean.iloc[-1] / clean.max() - 1)


def evaluate(drawdown: float, active_stages: Set[int]) -> List[CrisisAction]:
    """현재 낙폭과 활성 트랜치 상태로 발동할 액션 목록 결정 (순수 함수)"""
    if drawdown >= _REARM_THRESHOLD:
        if active_stages:
            return [CrisisAction(type="rearm", stage=None, drawdown=drawdown)]
        return []

    actions: List[CrisisAction] = []
    for i, (threshold, fraction) in enumerate(TRANCHES, start=1):
        if drawdown <= threshold and i not in active_stages:
            actions.append(CrisisAction(
                type="deploy", stage=i, drawdown=drawdown,
                reserve_fraction=fraction,
            ))
    return actions


def _deploy_message(market: str, action: CrisisAction, today: str) -> str:
    return (
        f"🚨 [위기 매수 프로토콜] {market} 시장 {action.stage}단계 발동 ({today})\n"
        f"고점 대비 낙폭: {action.drawdown:.1%}\n"
        f"지시: 예비 현금의 {action.reserve_fraction:.0%}를 시장 바스켓(지수 ETF)에 매수\n"
        f"원칙: 손절 없음 · 분할 진입 · 신고점 회복까지 보유 (추가 하락 감내 전제)"
    )


def _rearm_message(market: str, drawdown: float, today: str) -> str:
    return (
        f"✅ [위기 매수 프로토콜] {market} 시장 회복 — 재장전 ({today})\n"
        f"현재 낙폭 {drawdown:.1%} (고점 근처). 위기 보유분 정리·예비대 환원을 검토하세요."
    )


def run_check(
    repo: CrisisRepository,
    market: str,
    index_series: pd.Series,
    notify: Optional[Callable[[str], None]] = None,
    today: str = "",
) -> dict:
    """낙폭 평가 → 이벤트 기록 → 알림. 알림 실패는 상태 기록을 막지 않는다.

    반환: {"market", "drawdown", "deployed_stages", "rearmed"}
    """
    drawdown = compute_drawdown(index_series)
    actions = evaluate(drawdown, repo.active_stages(market))

    deployed: List[int] = []
    rearmed = False
    for action in actions:
        repo.record_event(market, action.type, action.stage, today, drawdown)
        if action.type == "deploy":
            deployed.append(action.stage)
            message = _deploy_message(market, action, today)
        else:
            rearmed = True
            message = _rearm_message(market, drawdown, today)
        logger.info("위기 프로토콜 [%s] %s", market, message.replace("\n", " / "))
        if notify is not None:
            try:
                notify(message)
            except Exception as exc:  # 알림 실패 격리
                logger.error("위기 프로토콜 알림 실패 [%s]: %s", market, exc)

    return {
        "market": market,
        "drawdown": round(drawdown, 4),
        "deployed_stages": deployed,
        "rearmed": rearmed,
    }


def fetch_index_series(symbol: str, lookback_days: int = LOOKBACK_DAYS) -> pd.Series:
    """지수 종가 시계열 조회 (yfinance 경유, 52주 고점 계산용 구간)"""
    from .indicators import load_sample_data
    end = datetime.now()
    start = end - timedelta(days=lookback_days)
    df = load_sample_data(symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    return df["close"]


def _telegram_notify(message: str) -> None:
    """텔레그램 알림 (미설정 시 무동작). 동기 컨텍스트(to_thread)에서 호출됨."""
    from .telegram_bot import get_telegram_notifier
    notifier = get_telegram_notifier()
    if notifier.is_enabled():
        asyncio.run(notifier.send_message(message))


def check_markets(db_path: Optional[str] = None, today: str = "") -> dict:
    """전 시장 위기 체크 (daily_jobs 진입점). 시장별 실패 격리."""
    repo = CrisisRepository(db_path)
    results: dict = {}
    for market, symbol in MARKET_INDICES.items():
        try:
            series = fetch_index_series(symbol)
            results[market] = run_check(
                repo, market, series, notify=_telegram_notify, today=today)
        except Exception as exc:  # 한 시장 실패가 다른 시장 체크를 막지 않게
            logger.error("위기 프로토콜 체크 실패 [%s/%s]: %s", market, symbol, exc)
            results[market] = {"error": str(exc)[:200]}
    return results

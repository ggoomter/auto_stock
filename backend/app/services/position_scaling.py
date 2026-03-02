"""
분할 매수/매도 전략 모듈

"안 잃는" 투자를 위한 핵심 기능:
1. DCA (Dollar Cost Averaging): 평균 단가 낮추기
2. 피라미딩 (Pyramiding): 승리 중인 포지션 추가 매수
3. 단계별 청산: 이익 실현 + 손실 최소화
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from datetime import datetime
from enum import Enum
import pandas as pd
import numpy as np

from ..core.logging_config import logger


class ScalingType(Enum):
    """포지션 스케일링 유형"""
    DCA = "dca"                    # Dollar Cost Averaging
    PYRAMID = "pyramid"            # Pyramiding (추세 추종)
    GRID = "grid"                  # Grid Trading (일정 간격)
    VALUE_AVERAGE = "value_avg"   # Value Averaging


class ExitStrategy(Enum):
    """청산 전략"""
    FIXED_LEVELS = "fixed_levels"  # 고정 레벨 (25%, 50%, 75%, 100%)
    TRAILING = "trailing"          # 트레일링 (최고가 대비 하락 시)
    TIME_BASED = "time_based"      # 시간 기반 (보유 기간)
    RISK_BASED = "risk_based"      # 리스크 기반 (변동성 증가 시)


@dataclass
class ScalingConfig:
    """분할 매수/매도 설정"""
    # 진입 설정
    scaling_type: ScalingType = ScalingType.DCA
    num_entries: int = 3                      # 분할 매수 횟수 (3-5회 권장)
    entry_interval_pct: float = 2.0           # 추가 매수 간격 (% 하락 시)
    max_total_position: float = 1.0           # 최대 포지션 크기 (초기 계획의 100%)

    # DCA 설정
    dca_fixed_amount: Optional[float] = None  # 고정 금액 (None이면 균등 분할)
    dca_time_interval_hours: int = 24         # 시간 간격 (24시간 = 매일)

    # 피라미딩 설정
    pyramid_profit_threshold: float = 5.0     # 추가 매수 조건 (5% 이상 수익)
    pyramid_size_reduction: float = 0.5       # 추가 매수 크기 감소 (50%)
    pyramid_max_adds: int = 2                 # 최대 추가 횟수

    # 청산 설정
    exit_strategy: ExitStrategy = ExitStrategy.FIXED_LEVELS
    exit_levels: List[Tuple[float, float]] = None  # [(profit%, sell%), ...]
    trailing_stop_pct: float = 5.0            # 트레일링 스톱 (5%)

    # 리스크 관리
    stop_loss_pct: float = 10.0               # 전체 손절 (10%)
    max_holding_days: int = 90                # 최대 보유 기간 (90일)

    def __post_init__(self):
        if self.exit_levels is None:
            # 기본 청산 레벨: 10% 도달 시 25% 매도, 20% 시 25% 매도, 30% 시 50% 매도
            self.exit_levels = [
                (10.0, 0.25),  # 10% 수익 → 25% 매도
                (20.0, 0.25),  # 20% 수익 → 추가 25% 매도 (총 50%)
                (30.0, 0.50),  # 30% 수익 → 나머지 전부 매도
            ]


@dataclass
class PositionEntry:
    """개별 진입 기록"""
    entry_id: str
    timestamp: datetime
    price: float
    shares: int
    cost: float
    reason: str  # "initial", "dca_add", "pyramid_add", "grid_add"


@dataclass
class PositionExit:
    """개별 청산 기록"""
    exit_id: str
    timestamp: datetime
    price: float
    shares: int
    proceeds: float
    pnl: float
    pnl_pct: float
    reason: str  # "partial_profit", "trailing_stop", "stop_loss", "final_exit"


@dataclass
class ScaledPosition:
    """스케일링 포지션 관리"""
    symbol: str
    strategy_name: str
    config: ScalingConfig

    # 진입 기록
    entries: List[PositionEntry] = field(default_factory=list)
    total_shares: int = 0
    total_cost: float = 0.0
    avg_entry_price: float = 0.0

    # 청산 기록
    exits: List[PositionExit] = field(default_factory=list)
    remaining_shares: int = 0
    realized_pnl: float = 0.0

    # 상태
    initial_plan_shares: int = 0              # 초기 계획 수량
    highest_price: float = 0.0                # 최고가
    lowest_price: float = float('inf')        # 최저가
    last_add_timestamp: Optional[datetime] = None
    last_add_price: Optional[float] = None
    num_adds: int = 0                         # 추가 매수 횟수
    is_closed: bool = False

    def update_metrics(self):
        """메트릭 업데이트"""
        if self.total_shares > 0:
            self.avg_entry_price = self.total_cost / self.total_shares

        # 남은 수량 계산
        total_sold = sum(exit.shares for exit in self.exits)
        self.remaining_shares = self.total_shares - total_sold

        # 실현 손익
        self.realized_pnl = sum(exit.pnl for exit in self.exits)

    def get_unrealized_pnl(self, current_price: float) -> Tuple[float, float]:
        """미실현 손익 계산"""
        if self.remaining_shares == 0:
            return 0.0, 0.0

        unrealized_pnl = (current_price - self.avg_entry_price) * self.remaining_shares
        unrealized_pnl_pct = ((current_price / self.avg_entry_price) - 1) * 100

        return unrealized_pnl, unrealized_pnl_pct

    def get_total_pnl(self, current_price: float) -> Tuple[float, float]:
        """총 손익 (실현 + 미실현)"""
        unrealized_pnl, _ = self.get_unrealized_pnl(current_price)
        total_pnl = self.realized_pnl + unrealized_pnl

        if self.total_cost > 0:
            total_pnl_pct = (total_pnl / self.total_cost) * 100
        else:
            total_pnl_pct = 0.0

        return total_pnl, total_pnl_pct


class PositionScalingManager:
    """분할 매수/매도 관리자"""

    def __init__(self):
        self.positions: Dict[str, ScaledPosition] = {}  # {symbol: ScaledPosition}
        logger.info("분할 매수/매도 관리자 초기화")

    def create_position(
        self,
        symbol: str,
        strategy_name: str,
        initial_shares: int,
        config: ScalingConfig = None
    ) -> ScaledPosition:
        """
        새 포지션 생성

        Args:
            symbol: 종목 코드
            strategy_name: 전략 이름
            initial_shares: 초기 계획 수량
            config: 스케일링 설정
        """
        if config is None:
            config = ScalingConfig()

        position = ScaledPosition(
            symbol=symbol,
            strategy_name=strategy_name,
            config=config,
            entries=[],
            exits=[],
            initial_plan_shares=initial_shares
        )

        self.positions[symbol] = position
        logger.info(f"포지션 생성: {symbol} (초기 계획: {initial_shares}주)")

        return position

    def add_entry(
        self,
        symbol: str,
        price: float,
        shares: int,
        reason: str = "initial"
    ) -> Optional[PositionEntry]:
        """
        진입 추가

        Args:
            symbol: 종목 코드
            price: 진입 가격
            shares: 진입 수량
            reason: 진입 사유
        """
        if symbol not in self.positions:
            logger.warning(f"포지션이 없습니다: {symbol}")
            return None

        position = self.positions[symbol]

        # 최대 포지션 크기 체크
        total_after_add = position.total_shares + shares
        max_allowed = int(position.initial_plan_shares * position.config.max_total_position)

        if total_after_add > max_allowed:
            logger.warning(
                f"최대 포지션 초과: {symbol} "
                f"(현재: {position.total_shares}, 추가: {shares}, 최대: {max_allowed})"
            )
            shares = max(0, max_allowed - position.total_shares)
            if shares == 0:
                return None

        # 진입 기록 생성
        entry = PositionEntry(
            entry_id=f"{symbol}_{len(position.entries)}",
            timestamp=datetime.now(),
            price=price,
            shares=shares,
            cost=price * shares,
            reason=reason
        )

        position.entries.append(entry)
        position.total_shares += shares
        position.total_cost += entry.cost
        position.last_add_timestamp = entry.timestamp
        position.last_add_price = price
        position.num_adds += 1

        # 최저가 업데이트
        if price < position.lowest_price:
            position.lowest_price = price

        position.update_metrics()

        logger.info(
            f"진입 추가: {symbol} {shares}주 @ {price:,.0f} "
            f"(사유: {reason}, 평균가: {position.avg_entry_price:,.0f})"
        )

        return entry

    def add_exit(
        self,
        symbol: str,
        price: float,
        shares: int,
        reason: str = "partial_profit"
    ) -> Optional[PositionExit]:
        """
        청산 추가

        Args:
            symbol: 종목 코드
            price: 청산 가격
            shares: 청산 수량
            reason: 청산 사유
        """
        if symbol not in self.positions:
            logger.warning(f"포지션이 없습니다: {symbol}")
            return None

        position = self.positions[symbol]

        # 보유 수량 체크
        if shares > position.remaining_shares:
            logger.warning(
                f"청산 수량 초과: {symbol} "
                f"(요청: {shares}, 보유: {position.remaining_shares})"
            )
            shares = position.remaining_shares

        # 손익 계산
        avg_cost = position.avg_entry_price
        pnl = (price - avg_cost) * shares
        pnl_pct = ((price / avg_cost) - 1) * 100 if avg_cost > 0 else 0

        # 청산 기록 생성
        exit_record = PositionExit(
            exit_id=f"{symbol}_{len(position.exits)}",
            timestamp=datetime.now(),
            price=price,
            shares=shares,
            proceeds=price * shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            reason=reason
        )

        position.exits.append(exit_record)
        position.update_metrics()

        # 전량 청산 체크
        if position.remaining_shares == 0:
            position.is_closed = True

        logger.info(
            f"청산 추가: {symbol} {shares}주 @ {price:,.0f} "
            f"(사유: {reason}, 손익: {pnl:+,.0f} ({pnl_pct:+.2f}%))"
        )

        return exit_record

    def check_dca_signal(
        self,
        symbol: str,
        current_price: float
    ) -> Tuple[bool, int, str]:
        """
        DCA 추가 매수 신호 확인

        Returns:
            (should_add, shares, reason)
        """
        if symbol not in self.positions:
            return False, 0, ""

        position = self.positions[symbol]
        config = position.config

        # DCA가 아니면 스킵
        if config.scaling_type != ScalingType.DCA:
            return False, 0, ""

        # 이미 최대 횟수 도달
        if position.num_adds >= config.num_entries:
            return False, 0, "max_entries_reached"

        # 가격 하락 체크
        if position.last_add_price is None:
            return False, 0, "no_previous_entry"

        price_drop_pct = ((current_price / position.last_add_price) - 1) * 100

        # 설정된 간격만큼 하락했는지 확인
        if price_drop_pct >= -config.entry_interval_pct:
            return False, 0, "price_not_dropped_enough"

        # 시간 간격 체크 (선택적)
        if config.dca_time_interval_hours > 0 and position.last_add_timestamp:
            hours_since_last = (datetime.now() - position.last_add_timestamp).total_seconds() / 3600
            if hours_since_last < config.dca_time_interval_hours:
                return False, 0, "time_interval_not_met"

        # 추가 매수 수량 계산
        if config.dca_fixed_amount:
            # 고정 금액
            shares = int(config.dca_fixed_amount / current_price)
        else:
            # 균등 분할
            shares = position.initial_plan_shares // config.num_entries

        reason = f"dca_add_{position.num_adds + 1}"

        return True, shares, reason

    def check_pyramid_signal(
        self,
        symbol: str,
        current_price: float
    ) -> Tuple[bool, int, str]:
        """
        피라미딩 추가 매수 신호 확인

        Returns:
            (should_add, shares, reason)
        """
        if symbol not in self.positions:
            return False, 0, ""

        position = self.positions[symbol]
        config = position.config

        # 피라미딩이 아니면 스킵
        if config.scaling_type != ScalingType.PYRAMID:
            return False, 0, ""

        # 이미 최대 횟수 도달
        if position.num_adds > config.pyramid_max_adds:
            return False, 0, "max_adds_reached"

        # 미실현 손익 확인
        _, unrealized_pnl_pct = position.get_unrealized_pnl(current_price)

        # 수익이 임계값 이상인지 확인
        if unrealized_pnl_pct < config.pyramid_profit_threshold:
            return False, 0, "profit_threshold_not_met"

        # 추가 매수 수량 계산 (이전보다 작게)
        base_shares = position.initial_plan_shares // config.num_entries
        reduction_factor = config.pyramid_size_reduction ** position.num_adds
        shares = int(base_shares * reduction_factor)

        reason = f"pyramid_add_{position.num_adds + 1}"

        return True, shares, reason

    def check_exit_signals(
        self,
        symbol: str,
        current_price: float
    ) -> List[Tuple[int, str]]:
        """
        청산 신호 확인

        Returns:
            [(shares_to_sell, reason), ...]
        """
        if symbol not in self.positions:
            return []

        position = self.positions[symbol]
        config = position.config
        signals = []

        # 최고가 업데이트
        if current_price > position.highest_price:
            position.highest_price = current_price

        # 1. 손절 확인 (최우선)
        _, total_pnl_pct = position.get_total_pnl(current_price)
        if total_pnl_pct <= -config.stop_loss_pct:
            signals.append((position.remaining_shares, "stop_loss"))
            return signals  # 즉시 전량 청산

        # 2. 청산 전략별 확인
        if config.exit_strategy == ExitStrategy.FIXED_LEVELS:
            # 고정 레벨 청산
            for profit_pct, sell_pct in config.exit_levels:
                _, unrealized_pnl_pct = position.get_unrealized_pnl(current_price)

                if unrealized_pnl_pct >= profit_pct:
                    # 이미 이 레벨에서 매도했는지 확인
                    already_sold_at_level = any(
                        exit.reason == f"partial_profit_{profit_pct}%"
                        for exit in position.exits
                    )

                    if not already_sold_at_level:
                        shares_to_sell = int(position.remaining_shares * sell_pct)
                        if shares_to_sell > 0:
                            reason = f"partial_profit_{profit_pct}%"
                            signals.append((shares_to_sell, reason))

        elif config.exit_strategy == ExitStrategy.TRAILING:
            # 트레일링 스톱
            if position.highest_price > 0:
                drawdown_pct = ((current_price / position.highest_price) - 1) * 100

                if drawdown_pct <= -config.trailing_stop_pct:
                    signals.append((position.remaining_shares, "trailing_stop"))
                    return signals

        # 3. 최대 보유 기간 확인
        if position.entries:
            first_entry = position.entries[0]
            holding_days = (datetime.now() - first_entry.timestamp).days

            if holding_days >= config.max_holding_days:
                signals.append((position.remaining_shares, "max_holding_days"))

        return signals

    def get_position_summary(self, symbol: str, current_price: float) -> Dict:
        """포지션 요약 정보"""
        if symbol not in self.positions:
            return {}

        position = self.positions[symbol]
        unrealized_pnl, unrealized_pnl_pct = position.get_unrealized_pnl(current_price)
        total_pnl, total_pnl_pct = position.get_total_pnl(current_price)

        return {
            "symbol": symbol,
            "strategy": position.strategy_name,
            "total_entries": len(position.entries),
            "total_exits": len(position.exits),
            "avg_entry_price": position.avg_entry_price,
            "current_price": current_price,
            "remaining_shares": position.remaining_shares,
            "total_cost": position.total_cost,
            "realized_pnl": position.realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_pct": unrealized_pnl_pct,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "highest_price": position.highest_price,
            "lowest_price": position.lowest_price if position.lowest_price != float('inf') else 0,
            "is_closed": position.is_closed,
            "num_adds": position.num_adds
        }

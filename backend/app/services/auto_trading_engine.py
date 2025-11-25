"""
자동매매 엔진
실시간 데이터 기반 자동 거래 실행
"""
import asyncio
import json
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import pandas as pd
import numpy as np

from ..core.logging_config import logger
from .backtest import BacktestEngine
from .parser import StrategyParser
from .indicators import IndicatorCalculator
from .master_strategies import MASTER_STRATEGIES
from .advanced_risk_manager import AdvancedRiskManager, RiskLevel
from .broker_api import KoreaInvestmentAPI
from .realtime_data import RealtimeDataCollector
from .position_manager import PositionManager
from .position_scaling import (
    PositionScalingManager,
    ScalingConfig,
    ScalingType,
    ExitStrategy
)
from .stock_screener import StockScreener, ScreenerType


class TradingMode(Enum):
    """거래 모드"""
    PAPER = "paper"        # 모의 거래
    LIVE = "live"          # 실전 거래
    BACKTEST = "backtest"  # 백테스트


class OrderType(Enum):
    """주문 유형"""
    MARKET = "market"      # 시장가
    LIMIT = "limit"        # 지정가
    STOP = "stop"          # 스톱
    STOP_LIMIT = "stop_limit"  # 스톱 리밋


class OrderStatus(Enum):
    """주문 상태"""
    PENDING = "pending"    # 대기중
    FILLED = "filled"      # 체결
    PARTIAL = "partial"    # 부분체결
    CANCELLED = "cancelled"  # 취소
    REJECTED = "rejected"  # 거부


@dataclass
class TradingSignal:
    """거래 신호"""
    timestamp: datetime
    symbol: str
    action: str  # 'buy', 'sell', 'hold'
    strategy_name: str
    confidence: float  # 0~1
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: int
    reason: str


@dataclass
class Order:
    """주문 정보"""
    order_id: str
    symbol: str
    side: str  # 'buy', 'sell'
    order_type: OrderType
    quantity: int
    price: float
    status: OrderStatus
    filled_quantity: int
    filled_price: float
    timestamp: datetime
    strategy: str


@dataclass
class AutoTradingConfig:
    """자동매매 설정"""
    mode: TradingMode = TradingMode.PAPER
    max_positions: int = 5
    max_position_size: float = 0.2  # 20% per position
    total_capital: float = 10_000_000  # KRW

    # 리스크 관리
    max_daily_loss: float = 0.05  # 5% 일일 최대 손실
    max_risk_per_trade: float = 0.02  # 2% per trade
    use_trailing_stop: bool = True
    trailing_stop_percent: float = 0.05

    # 실행 설정
    order_type: OrderType = OrderType.MARKET
    slippage_tolerance: float = 0.01  # 1% 슬리피지

    # 전략 설정
    enabled_strategies: List[str] = None
    strategy_weights: Dict[str, float] = None

    # 시간 설정
    trading_hours: Dict[str, str] = None  # {"start": "09:00", "end": "15:30"}

    # 분할 매수/매도 설정 (신규!)
    use_position_scaling: bool = True              # 분할 매수/매도 활성화
    scaling_type: ScalingType = ScalingType.DCA    # DCA, PYRAMID, GRID
    num_entries: int = 3                           # 분할 매수 횟수
    entry_interval_pct: float = 2.0                # 추가 매수 간격 (%)
    exit_strategy: ExitStrategy = ExitStrategy.FIXED_LEVELS

    # 종목 발굴 설정 (신규!)
    use_stock_screener: bool = True                # 자동 종목 발굴
    screener_type: ScreenerType = ScreenerType.BUFFETT  # 스크리너 유형
    screener_update_hours: int = 24                # 스크리닝 주기 (시간)

    def __post_init__(self):
        if self.enabled_strategies is None:
            self.enabled_strategies = ["buffett", "lynch", "custom"]
        if self.strategy_weights is None:
            self.strategy_weights = {"buffett": 0.4, "lynch": 0.3, "custom": 0.3}
        if self.trading_hours is None:
            self.trading_hours = {"start": "09:00", "end": "15:30"}


class AutoTradingEngine:
    """자동매매 엔진"""

    def __init__(self, config: AutoTradingConfig = None):
        self.config = config or AutoTradingConfig()
        self.is_running = False

        # 컴포넌트 초기화
        self.risk_manager = AdvancedRiskManager(
            total_capital=self.config.total_capital,
            max_risk_per_trade=self.config.max_risk_per_trade
        )

        self.data_collector = RealtimeDataCollector()
        self.position_manager = PositionManager()
        self.broker_api = KoreaInvestmentAPI() if self.config.mode == TradingMode.LIVE else None

        # 분할 매수/매도 관리자 (신규!)
        self.scaling_manager = PositionScalingManager()

        # 종목 스크리너 (신규!)
        self.stock_screener = StockScreener()
        self.last_screening_time: Optional[datetime] = None

        # 전략 파서
        self.strategy_parsers: Dict[str, StrategyParser] = {}
        self.master_strategies = MASTER_STRATEGIES

        # 상태 관리
        self.active_positions: Dict[str, Dict] = {}
        self.pending_orders: List[Order] = []
        self.trade_history: List[Dict] = []
        self.daily_pnl = 0.0

        # 신호 큐
        self.signal_queue: asyncio.Queue = asyncio.Queue()

        # WebSocket 클라이언트 (대시보드 연동)
        self.ws_clients: Set = set()

        # 시작 시간 및 관심 종목
        self.start_time: Optional[datetime] = None
        self.watchlist: List[str] = []

        logger.info(f"자동매매 엔진 초기화 (모드: {self.config.mode.value})")
        logger.info(f"분할 매수/매도: {'활성화' if self.config.use_position_scaling else '비활성화'}")
        logger.info(f"자동 종목 발굴: {'활성화' if self.config.use_stock_screener else '비활성화'}")

    async def start(self, symbols: List[str] = None):
        """자동매매 시작"""
        if self.is_running:
            logger.warning("자동매매가 이미 실행 중입니다")
            return

        self.is_running = True
        self.start_time = datetime.now()

        # 거래 종목 설정
        if symbols:
            self.watchlist = symbols

        logger.info(f"자동매매 엔진 시작 (종목: {self.watchlist if symbols else '기본'})")

        # 비동기 태스크 실행
        tasks = [
            asyncio.create_task(self._monitor_market()),
            asyncio.create_task(self._process_signals()),
            asyncio.create_task(self._manage_positions()),
            asyncio.create_task(self._risk_monitor())
        ]

        # 자동 종목 발굴 태스크 추가 (선택적)
        if self.config.use_stock_screener:
            tasks.append(asyncio.create_task(self._auto_stock_discovery()))

        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"자동매매 엔진 오류: {e}")
        finally:
            self.is_running = False

    async def stop(self, close_positions: bool = False):
        """자동매매 중지"""
        logger.info(f"자동매매 엔진 중지 요청 (포지션 청산: {close_positions})")
        self.is_running = False

        # 포지션 청산 (옵션)
        if close_positions:
            await self._close_all_positions("자동매매 중지 - 사용자 요청")

    async def _monitor_market(self):
        """시장 모니터링 및 신호 생성"""
        while self.is_running:
            try:
                # 거래 시간 확인
                if not self._is_trading_hours():
                    await asyncio.sleep(60)  # 1분 대기
                    continue

                # 관심 종목 리스트
                symbols = self._get_watchlist()

                for symbol in symbols:
                    # 실시간 데이터 수집
                    data = await self.data_collector.fetch_realtime_data(symbol)
                    if data is None:
                        continue

                    # 각 전략별 신호 확인
                    for strategy_name in self.config.enabled_strategies:
                        signal = await self._check_strategy_signal(
                            strategy_name, symbol, data
                        )

                        if signal:
                            await self.signal_queue.put(signal)
                            logger.info(f"신호 생성: {symbol} - {signal.action} ({strategy_name})")

                # 주기적 실행 (10초)
                await asyncio.sleep(10)

            except Exception as e:
                logger.error(f"시장 모니터링 오류: {e}")
                await asyncio.sleep(10)

    async def _check_strategy_signal(self,
                                    strategy_name: str,
                                    symbol: str,
                                    data: pd.DataFrame) -> Optional[TradingSignal]:
        """전략 신호 확인"""
        try:
            # 이미 포지션이 있는지 확인
            if symbol in self.active_positions:
                # 청산 신호 확인
                return await self._check_exit_signal(strategy_name, symbol, data)

            # 진입 신호 확인
            return await self._check_entry_signal(strategy_name, symbol, data)

        except Exception as e:
            logger.error(f"신호 확인 오류 ({symbol}, {strategy_name}): {e}")
            return None

    async def _check_entry_signal(self,
                                 strategy_name: str,
                                 symbol: str,
                                 data: pd.DataFrame) -> Optional[TradingSignal]:
        """진입 신호 확인"""
        if len(data) < 200:  # 최소 데이터 필요
            return None

        current_price = data['close'].iloc[-1]

        # 마스터 전략
        if strategy_name in self.master_strategies:
            strategy = self.master_strategies[strategy_name]

            # 백테스트 엔진으로 조건 확인
            backtest = BacktestEngine(
                symbols=[symbol],
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d'),
                initial_capital=self.config.total_capital
            )

            # 조건 충족 확인
            is_signal = backtest._evaluate_condition(
                strategy.entry_condition, data.iloc[-1], data
            )

            if is_signal:
                # 포지션 크기 계산
                sizing_result = self.risk_manager.calculate_position_size(
                    symbol=symbol,
                    entry_price=current_price,
                    stop_loss=current_price * (1 - strategy.stop_loss_pct / 100),
                    strategy_win_rate=0.5,  # 기본값
                    avg_win_loss_ratio=2.0,  # 기본값
                    current_positions=list(self.active_positions.values())
                )

                return TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="buy",
                    strategy_name=strategy_name,
                    confidence=0.8,  # 신뢰도 계산 필요
                    entry_price=current_price,
                    stop_loss=sizing_result.stop_loss_price,
                    take_profit=sizing_result.take_profit_price,
                    position_size=sizing_result.recommended_shares,
                    reason=f"{strategy_name} 진입 조건 충족"
                )

        # 커스텀 전략
        elif strategy_name == "custom" and strategy_name in self.strategy_parsers:
            parser = self.strategy_parsers[strategy_name]
            # 커스텀 로직...

        return None

    async def _check_exit_signal(self,
                                strategy_name: str,
                                symbol: str,
                                data: pd.DataFrame) -> Optional[TradingSignal]:
        """청산 신호 확인"""
        if symbol not in self.active_positions:
            return None

        position = self.active_positions[symbol]
        current_price = data['close'].iloc[-1]

        # 손절/익절 확인
        if current_price <= position['stop_loss']:
            return TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action="sell",
                strategy_name=strategy_name,
                confidence=1.0,
                entry_price=current_price,
                stop_loss=0,
                take_profit=0,
                position_size=position['shares'],
                reason="손절매"
            )

        if current_price >= position['take_profit']:
            return TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action="sell",
                strategy_name=strategy_name,
                confidence=1.0,
                entry_price=current_price,
                stop_loss=0,
                take_profit=0,
                position_size=position['shares'],
                reason="익절매"
            )

        # 전략별 청산 조건
        if strategy_name in self.master_strategies:
            strategy = self.master_strategies[strategy_name]

            backtest = BacktestEngine(
                symbols=[symbol],
                start_date=(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
                end_date=datetime.now().strftime('%Y-%m-%d')
            )

            is_exit = backtest._evaluate_condition(
                strategy.exit_condition, data.iloc[-1], data
            )

            if is_exit:
                return TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="sell",
                    strategy_name=strategy_name,
                    confidence=0.8,
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    position_size=position['shares'],
                    reason=f"{strategy_name} 청산 조건 충족"
                )

        # 트레일링 스톱
        if self.config.use_trailing_stop:
            trailing_stop = position['highest_price'] * (1 - self.config.trailing_stop_percent)
            if current_price <= trailing_stop:
                return TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="sell",
                    strategy_name=strategy_name,
                    confidence=0.9,
                    entry_price=current_price,
                    stop_loss=0,
                    take_profit=0,
                    position_size=position['shares'],
                    reason="트레일링 스톱"
                )

        return None

    async def _process_signals(self):
        """신호 처리 및 주문 실행"""
        while self.is_running:
            try:
                # 신호 대기 (타임아웃 1초)
                signal = await asyncio.wait_for(
                    self.signal_queue.get(), timeout=1.0
                )

                # 리스크 확인
                if not self._check_risk_limits():
                    logger.warning(f"리스크 한도 초과로 신호 무시: {signal.symbol}")
                    continue

                # 주문 실행
                order = await self._execute_order(signal)

                if order:
                    logger.info(f"주문 실행: {order.symbol} {order.side} {order.quantity}주")

                    # WebSocket으로 알림
                    await self._broadcast_to_clients({
                        "type": "order_executed",
                        "order": asdict(order)
                    })

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"신호 처리 오류: {e}")

    async def _execute_order(self, signal: TradingSignal) -> Optional[Order]:
        """주문 실행"""
        try:
            order_id = f"{signal.symbol}_{datetime.now().timestamp()}"

            order = Order(
                order_id=order_id,
                symbol=signal.symbol,
                side="buy" if signal.action == "buy" else "sell",
                order_type=self.config.order_type,
                quantity=signal.position_size,
                price=signal.entry_price,
                status=OrderStatus.PENDING,
                filled_quantity=0,
                filled_price=0,
                timestamp=datetime.now(),
                strategy=signal.strategy_name
            )

            # 실전 거래
            if self.config.mode == TradingMode.LIVE and self.broker_api.is_enabled():
                if signal.action == "buy":
                    result = await self.broker_api.buy_stock(
                        signal.symbol,
                        signal.position_size,
                        signal.entry_price
                    )
                else:
                    result = await self.broker_api.sell_stock(
                        signal.symbol,
                        signal.position_size,
                        signal.entry_price
                    )

                if result['success']:
                    order.status = OrderStatus.FILLED
                    order.filled_quantity = signal.position_size
                    order.filled_price = result['executed_price']
                else:
                    order.status = OrderStatus.REJECTED
                    logger.error(f"주문 거부: {result['message']}")

            # 모의 거래
            else:
                # 슬리피지 시뮬레이션
                slippage = np.random.uniform(-self.config.slippage_tolerance,
                                            self.config.slippage_tolerance)
                order.status = OrderStatus.FILLED
                order.filled_quantity = signal.position_size
                order.filled_price = signal.entry_price * (1 + slippage)

            # 포지션 업데이트
            if order.status == OrderStatus.FILLED:
                if signal.action == "buy":
                    self.active_positions[signal.symbol] = {
                        "symbol": signal.symbol,
                        "shares": order.filled_quantity,
                        "entry_price": order.filled_price,
                        "stop_loss": signal.stop_loss,
                        "take_profit": signal.take_profit,
                        "highest_price": order.filled_price,
                        "strategy": signal.strategy_name,
                        "entry_time": datetime.now()
                    }
                else:
                    if signal.symbol in self.active_positions:
                        position = self.active_positions[signal.symbol]
                        pnl = (order.filled_price - position['entry_price']) * order.filled_quantity
                        self.daily_pnl += pnl

                        # 거래 기록
                        self.trade_history.append({
                            "symbol": signal.symbol,
                            "entry_price": position['entry_price'],
                            "exit_price": order.filled_price,
                            "shares": order.filled_quantity,
                            "pnl": pnl,
                            "strategy": signal.strategy_name,
                            "entry_time": position['entry_time'],
                            "exit_time": datetime.now(),
                            "reason": signal.reason
                        })

                        del self.active_positions[signal.symbol]

            self.pending_orders.append(order)
            return order

        except Exception as e:
            logger.error(f"주문 실행 오류: {e}")
            return None

    async def _manage_positions(self):
        """포지션 관리 (트레일링 스톱 등)"""
        while self.is_running:
            try:
                for symbol, position in self.active_positions.items():
                    # 현재가 업데이트
                    data = await self.data_collector.fetch_realtime_data(symbol)
                    if data is not None:
                        current_price = data['close'].iloc[-1]

                        # 최고가 업데이트
                        if current_price > position['highest_price']:
                            position['highest_price'] = current_price

                            # 트레일링 스톱 업데이트
                            if self.config.use_trailing_stop:
                                new_stop = current_price * (1 - self.config.trailing_stop_percent)
                                position['stop_loss'] = max(position['stop_loss'], new_stop)

                        # 포지션 정보 브로드캐스트
                        position_info = position.copy()
                        position_info['current_price'] = current_price
                        position_info['pnl'] = (current_price - position['entry_price']) * position['shares']
                        position_info['pnl_percent'] = ((current_price / position['entry_price']) - 1) * 100

                        await self._broadcast_to_clients({
                            "type": "position_update",
                            "positions": [position_info]
                        })

                await asyncio.sleep(30)  # 30초마다 업데이트

            except Exception as e:
                logger.error(f"포지션 관리 오류: {e}")
                await asyncio.sleep(30)

    async def _risk_monitor(self):
        """리스크 모니터링"""
        while self.is_running:
            try:
                # 일일 손실 확인
                if abs(self.daily_pnl) > self.config.total_capital * self.config.max_daily_loss:
                    logger.warning(f"일일 최대 손실 도달: {self.daily_pnl:,.0f}")
                    await self.stop()
                    break

                # 포트폴리오 리스크 계산
                if self.active_positions:
                    price_history = {}
                    for symbol in self.active_positions:
                        data = await self.data_collector.fetch_realtime_data(symbol)
                        if data is not None:
                            price_history[symbol] = data

                    risk_metrics = self.risk_manager.calculate_portfolio_risk(
                        list(self.active_positions.values()),
                        price_history
                    )

                    # 리스크 레벨 확인
                    if risk_metrics.overall_risk_level == RiskLevel.EXTREME:
                        logger.warning("익스트림 리스크 레벨 감지")
                        # 일부 포지션 축소 고려
                        await self._reduce_exposure()

                    # 리스크 지표 브로드캐스트
                    await self._broadcast_to_clients({
                        "type": "risk_update",
                        "riskMetrics": {
                            "portfolioRisk": risk_metrics.concentration_risk,
                            "var95": risk_metrics.var_95,
                            "sharpeRatio": risk_metrics.sharpe_ratio,
                            "maxDrawdown": risk_metrics.max_drawdown,
                            "riskLevel": risk_metrics.overall_risk_level.value
                        }
                    })

                await asyncio.sleep(60)  # 1분마다 체크

            except Exception as e:
                logger.error(f"리스크 모니터링 오류: {e}")
                await asyncio.sleep(60)

    async def _reduce_exposure(self):
        """포지션 축소"""
        # 손실이 큰 포지션부터 청산
        positions_with_pnl = []

        for symbol, position in self.active_positions.items():
            data = await self.data_collector.fetch_realtime_data(symbol)
            if data is not None:
                current_price = data['close'].iloc[-1]
                pnl = (current_price - position['entry_price']) * position['shares']
                positions_with_pnl.append((symbol, pnl))

        # 손실 순으로 정렬
        positions_with_pnl.sort(key=lambda x: x[1])

        # 하위 20% 청산
        to_close = int(len(positions_with_pnl) * 0.2) or 1
        for symbol, _ in positions_with_pnl[:to_close]:
            signal = TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action="sell",
                strategy_name="risk_management",
                confidence=1.0,
                entry_price=0,
                stop_loss=0,
                take_profit=0,
                position_size=self.active_positions[symbol]['shares'],
                reason="리스크 축소"
            )
            await self.signal_queue.put(signal)

    async def _close_all_positions(self, reason: str):
        """모든 포지션 청산"""
        for symbol, position in self.active_positions.items():
            signal = TradingSignal(
                timestamp=datetime.now(),
                symbol=symbol,
                action="sell",
                strategy_name="system",
                confidence=1.0,
                entry_price=0,
                stop_loss=0,
                take_profit=0,
                position_size=position['shares'],
                reason=reason
            )
            await self.signal_queue.put(signal)

    def _is_trading_hours(self) -> bool:
        """거래 시간 확인"""
        now = datetime.now()
        current_time = now.strftime("%H:%M")

        # 주말 제외
        if now.weekday() >= 5:  # 토요일(5), 일요일(6)
            return False

        # 거래 시간 확인
        start_time = self.config.trading_hours["start"]
        end_time = self.config.trading_hours["end"]

        return start_time <= current_time <= end_time

    def _get_watchlist(self) -> List[str]:
        """관심 종목 리스트"""
        # 사용자가 지정한 watchlist가 있으면 사용, 없으면 기본값
        return self.watchlist if self.watchlist else ["AAPL", "MSFT", "GOOGL", "005930.KS", "035720.KS"]

    def _check_risk_limits(self) -> bool:
        """리스크 한도 확인"""
        # 최대 포지션 수 확인
        if len(self.active_positions) >= self.config.max_positions:
            return False

        # 일일 손실 한도 확인
        if abs(self.daily_pnl) > self.config.total_capital * self.config.max_daily_loss:
            return False

        return True

    async def _broadcast_to_clients(self, message: Dict):
        """WebSocket 클라이언트에 메시지 전송"""
        if self.ws_clients:
            message_str = json.dumps(message, default=str)
            disconnected = set()

            for client in self.ws_clients:
                try:
                    await client.send(message_str)
                except:
                    disconnected.add(client)

            # 연결 끊긴 클라이언트 제거
            self.ws_clients -= disconnected

    def add_websocket_client(self, websocket):
        """WebSocket 클라이언트 추가"""
        self.ws_clients.add(websocket)

    def remove_websocket_client(self, websocket):
        """WebSocket 클라이언트 제거"""
        self.ws_clients.discard(websocket)

    def get_status(self) -> Dict:
        """현재 상태 반환"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0

        # 일일 손익률 계산
        daily_pnl_pct = (self.daily_pnl / self.config.total_capital) * 100 if self.config.total_capital > 0 else 0

        # 오늘 거래 수 계산
        today = datetime.now().date()
        total_trades_today = sum(1 for trade in self.trade_history if trade.get('exit_time', datetime.min).date() == today)

        # 리스크 레벨 계산 (간단 버전)
        risk_level = "low"
        if abs(daily_pnl_pct) > 3:
            risk_level = "high"
        elif abs(daily_pnl_pct) > 2:
            risk_level = "medium"

        return {
            "is_running": self.is_running,
            "mode": self.config.mode.value,
            "uptime_seconds": uptime,
            "active_positions": len(self.active_positions),
            "total_trades_today": total_trades_today,
            "daily_pnl": self.daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "enabled_strategies": self.config.enabled_strategies,
            "risk_level": risk_level
        }

    def get_portfolio_summary(self) -> Dict:
        """포트폴리오 요약"""
        # 포지션 가치 계산 (현재가 필요 - 임시로 entry_price 사용)
        total_positions_value = sum(
            pos.get('entry_price', 0) * pos.get('shares', 0)
            for pos in self.active_positions.values()
        )

        # 현금 잔고 (초기 자본 - 투자금)
        cash = self.config.total_capital - total_positions_value

        # 총 자산
        total_value = cash + total_positions_value

        # 총 손익
        total_pnl = total_value - self.config.total_capital
        total_pnl_pct = (total_pnl / self.config.total_capital) * 100 if self.config.total_capital > 0 else 0

        # 포지션 상세 정보
        positions = []
        for symbol, pos in self.active_positions.items():
            # 현재가 (임시로 entry_price 사용)
            current_price = pos.get('entry_price', 0)
            entry_price = pos.get('entry_price', 0)
            quantity = pos.get('shares', 0)

            pnl = (current_price - entry_price) * quantity
            pnl_pct = ((current_price / entry_price) - 1) * 100 if entry_price > 0 else 0

            positions.append({
                "symbol": symbol,
                "quantity": quantity,
                "entry_price": entry_price,
                "entry_date": pos.get('entry_time', datetime.now()).strftime('%Y-%m-%d'),
                "current_price": current_price,
                "pnl": pnl,
                "pnl_pct": pnl_pct,
                "stop_loss": pos.get('stop_loss'),
                "take_profit": pos.get('take_profit'),
                "strategy": pos.get('strategy', 'unknown')
            })

        # 리스크 지표 (간단 버전)
        risk_metrics = {
            "concentration_risk": len(self.active_positions) / self.config.max_positions if self.config.max_positions > 0 else 0,
            "daily_var": abs(self.daily_pnl) / self.config.total_capital if self.config.total_capital > 0 else 0,
            "max_position_size": max([pos.get('shares', 0) * pos.get('entry_price', 0) for pos in self.active_positions.values()]) if self.active_positions else 0
        }

        return {
            "total_value": total_value,
            "cash": cash,
            "positions_value": total_positions_value,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": positions,
            "risk_metrics": risk_metrics
        }

    async def emergency_stop(self, reason: str = "emergency") -> Dict:
        """긴급 정지"""
        logger.warning(f"🚨 긴급 정지 실행: {reason}")

        # 모든 포지션 즉시 청산
        closed_positions = 0
        for symbol in list(self.active_positions.keys()):
            try:
                position = self.active_positions[symbol]

                # 긴급 청산 신호 생성
                signal = TradingSignal(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    action="sell",
                    strategy_name="emergency_stop",
                    confidence=1.0,
                    entry_price=0,
                    stop_loss=0,
                    take_profit=0,
                    position_size=position['shares'],
                    reason=f"긴급 정지: {reason}"
                )

                # 시장가로 즉시 청산
                order = await self._execute_order(signal)
                if order and order.status == OrderStatus.FILLED:
                    closed_positions += 1

            except Exception as e:
                logger.error(f"긴급 청산 실패 ({symbol}): {e}")

        # 엔진 중지
        self.is_running = False

        # 최종 포트폴리오 상태
        final_portfolio = self.get_portfolio_summary()

        logger.warning(f"🛑 긴급 정지 완료 (청산: {closed_positions}개 포지션)")

        return {
            "closed_positions": closed_positions,
            "final_portfolio": final_portfolio,
            "reason": reason
        }

    def get_performance_metrics(self) -> Dict:
        """성과 지표 계산"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_rate": 0,
                "avg_profit": 0,
                "avg_loss": 0,
                "profit_factor": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0
            }

        trades = pd.DataFrame(self.trade_history)

        # 승률
        winning_trades = trades[trades['pnl'] > 0]
        win_rate = len(winning_trades) / len(trades)

        # 평균 수익/손실
        avg_profit = winning_trades['pnl'].mean() if len(winning_trades) > 0 else 0
        losing_trades = trades[trades['pnl'] < 0]
        avg_loss = losing_trades['pnl'].mean() if len(losing_trades) > 0 else 0

        # Profit Factor
        total_profit = winning_trades['pnl'].sum() if len(winning_trades) > 0 else 0
        total_loss = abs(losing_trades['pnl'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_profit / total_loss if total_loss > 0 else 0

        # 샤프 비율 (간단 계산)
        returns = trades['pnl'] / self.config.total_capital
        sharpe = np.sqrt(252) * returns.mean() / returns.std() if returns.std() > 0 else 0

        # 최대 낙폭
        cumulative_pnl = trades['pnl'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = (cumulative_pnl - running_max) / self.config.total_capital
        max_drawdown = drawdown.min()

        return {
            "total_trades": len(trades),
            "win_rate": win_rate,
            "avg_profit": avg_profit,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_drawdown,
            "total_pnl": trades['pnl'].sum()
        }

    async def _auto_stock_discovery(self):
        """자동 종목 발굴 (백그라운드)"""
        while self.is_running:
            try:
                # 스크리닝 주기 확인
                should_screen = False
                if self.last_screening_time is None:
                    should_screen = True
                else:
                    hours_since_last = (datetime.now() - self.last_screening_time).total_seconds() / 3600
                    if hours_since_last >= self.config.screener_update_hours:
                        should_screen = True

                if should_screen:
                    logger.info("🔍 자동 종목 발굴 시작")

                    # 스크리닝할 종목 풀 (예: S&P 500, KOSPI 200 등)
                    # 여기서는 간단하게 watchlist를 사용
                    symbols_to_screen = self.watchlist if self.watchlist else [
                        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
                        "NVDA", "META", "BRK-B", "JPM", "V",
                        "005930.KS", "000660.KS", "035720.KS"  # 삼성전자, SK하이닉스, 카카오
                    ]

                    # 스크리닝 실행
                    best_stocks = self.stock_screener.screen_stocks(
                        symbols=symbols_to_screen,
                        screener_type=self.config.screener_type,
                        top_n=5
                    )

                    if best_stocks:
                        logger.info(f"✅ {len(best_stocks)}개 우량 종목 발견:")
                        for i, stock in enumerate(best_stocks, 1):
                            logger.info(
                                f"  {i}. {stock.symbol} ({stock.name}) - "
                                f"점수: {stock.score:.1f}, "
                                f"PER: {stock.pe_ratio:.1f if stock.pe_ratio else 'N/A'}, "
                                f"ROE: {stock.roe:.1f if stock.roe else 'N/A'}%"
                            )

                        # watchlist에 자동 추가 (중복 제거)
                        for stock in best_stocks:
                            if stock.symbol not in self.watchlist:
                                self.watchlist.append(stock.symbol)
                                logger.info(f"  → {stock.symbol} watchlist에 추가")

                    self.last_screening_time = datetime.now()

                # 다음 스크리닝까지 대기 (1시간)
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"자동 종목 발굴 오류: {e}")
                await asyncio.sleep(3600)
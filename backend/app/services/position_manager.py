"""
포지션 관리 시스템
자동 매수/매도, 리스크 관리, 손절/익절
"""
from typing import Dict, List, Optional
from datetime import datetime
from ..core.logging_config import logger
from .broker_api import get_broker_api
from .telegram_bot import get_telegram_notifier
import asyncio


class Position:
    """개별 포지션"""

    def __init__(
        self,
        symbol: str,
        quantity: int,
        entry_price: float,
        entry_date: str,
        strategy: str = "unknown"
    ):
        self.symbol = symbol
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.strategy = strategy
        self.stop_loss: Optional[float] = None
        self.take_profit: Optional[float] = None

    def set_stop_loss(self, percent: float):
        """손절가 설정"""
        self.stop_loss = self.entry_price * (1 - percent)

    def set_take_profit(self, percent: float):
        """익절가 설정"""
        self.take_profit = self.entry_price * (1 + percent)

    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """
        청산 조건 체크

        Returns:
            "stop_loss" | "take_profit" | None
        """
        if self.stop_loss and current_price <= self.stop_loss:
            return "stop_loss"
        if self.take_profit and current_price >= self.take_profit:
            return "take_profit"
        return None

    def get_pnl(self, current_price: float) -> Dict:
        """손익 계산"""
        pnl = (current_price - self.entry_price) * self.quantity
        pnl_pct = ((current_price / self.entry_price) - 1) * 100

        return {
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "entry_price": self.entry_price,
            "current_price": current_price,
            "quantity": self.quantity
        }

    def to_dict(self) -> Dict:
        """딕셔너리로 변환"""
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "entry_price": self.entry_price,
            "entry_date": self.entry_date,
            "strategy": self.strategy,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit
        }


class PositionManager:
    """포지션 관리자"""

    def __init__(
        self,
        initial_capital: float = 10000000,  # 1천만원
        max_position_size: float = 0.2,  # 종목당 최대 20%
        max_positions: int = 5,
        default_stop_loss: float = 0.05,  # 5% 손절
        default_take_profit: float = 0.15,  # 15% 익절
        broker: str = "kis"
    ):
        self.initial_capital = initial_capital
        self.max_position_size = max_position_size
        self.max_positions = max_positions
        self.default_stop_loss = default_stop_loss
        self.default_take_profit = default_take_profit

        self.positions: Dict[str, Position] = {}
        self.cash = initial_capital
        self.broker_api = get_broker_api(broker)
        self.telegram = get_telegram_notifier()

        # 거래 내역
        self.trade_history: List[Dict] = []

    def get_portfolio_value(self, prices: Dict[str, float]) -> float:
        """총 포트폴리오 가치"""
        positions_value = sum(
            pos.quantity * prices.get(pos.symbol, pos.entry_price)
            for pos in self.positions.values()
        )
        return self.cash + positions_value

    def get_portfolio_summary(self, prices: Dict[str, float]) -> Dict:
        """포트폴리오 요약"""
        total_value = self.get_portfolio_value(prices)
        total_pnl = total_value - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital) * 100

        positions_data = []
        for pos in self.positions.values():
            current_price = prices.get(pos.symbol, pos.entry_price)
            pnl_data = pos.get_pnl(current_price)
            positions_data.append({
                **pos.to_dict(),
                "current_price": current_price,
                **pnl_data
            })

        return {
            "total_value": total_value,
            "cash": self.cash,
            "positions_value": total_value - self.cash,
            "total_pnl": total_pnl,
            "total_pnl_pct": total_pnl_pct,
            "positions": positions_data,
            "num_positions": len(self.positions)
        }

    async def open_position(
        self,
        symbol: str,
        price: float,
        strategy: str = "auto",
        quantity: Optional[int] = None
    ) -> Optional[Position]:
        """
        포지션 진입

        Args:
            symbol: 종목 코드
            price: 진입 가격
            strategy: 전략 이름
            quantity: 매수 수량 (None이면 자동 계산)

        Returns:
            Position 객체 또는 None
        """
        # 1. 이미 포지션이 있는지 확인
        if symbol in self.positions:
            logger.warning(f"{symbol}: 이미 포지션이 있습니다.")
            return None

        # 2. 최대 포지션 수 체크
        if len(self.positions) >= self.max_positions:
            logger.warning(f"최대 포지션 수({self.max_positions})에 도달했습니다.")
            return None

        # 3. 매수 수량 계산
        if quantity is None:
            max_investment = self.cash * self.max_position_size
            quantity = int(max_investment / price)

        total_cost = price * quantity

        # 4. 현금 충분한지 확인
        if total_cost > self.cash:
            logger.warning(f"{symbol}: 현금 부족 (필요: {total_cost:,.0f}, 보유: {self.cash:,.0f})")
            return None

        # 5. 실제 주문 (증권사 API)
        order_result = None
        if self.broker_api and self.broker_api.is_enabled():
            order_result = await self.broker_api.place_order(
                symbol=symbol,
                order_type="buy",
                quantity=quantity,
                price=price
            )

            if not order_result:
                logger.error(f"{symbol}: 주문 실패")
                await self.telegram.send_error_alert(
                    f"매수 주문 실패: {symbol}",
                    f"가격: {price}, 수량: {quantity}"
                )
                return None

        # 6. 포지션 생성
        position = Position(
            symbol=symbol,
            quantity=quantity,
            entry_price=price,
            entry_date=datetime.now().isoformat(),
            strategy=strategy
        )

        # 7. 손절/익절 설정
        position.set_stop_loss(self.default_stop_loss)
        position.set_take_profit(self.default_take_profit)

        # 8. 현금 차감
        self.cash -= total_cost

        # 9. 포지션 저장
        self.positions[symbol] = position

        logger.info(f"✅ 포지션 진입: {symbol} {quantity}주 @ {price:,.0f}")

        # 10. 텔레그램 알림
        await self.telegram.send_buy_signal({
            "symbol": symbol,
            "price": price,
            "reason": f"{strategy} 전략",
            "quantity": quantity,
            "total_cost": total_cost,
            "timestamp": datetime.now().isoformat()
        })

        return position

    async def close_position(
        self,
        symbol: str,
        price: float,
        reason: str = "manual"
    ) -> Optional[Dict]:
        """
        포지션 청산

        Args:
            symbol: 종목 코드
            price: 청산 가격
            reason: 청산 이유

        Returns:
            거래 결과 또는 None
        """
        # 1. 포지션 확인
        if symbol not in self.positions:
            logger.warning(f"{symbol}: 포지션이 없습니다.")
            return None

        position = self.positions[symbol]

        # 2. 실제 주문 (증권사 API)
        if self.broker_api and self.broker_api.is_enabled():
            order_result = await self.broker_api.place_order(
                symbol=symbol,
                order_type="sell",
                quantity=position.quantity,
                price=price
            )

            if not order_result:
                logger.error(f"{symbol}: 매도 주문 실패")
                return None

        # 3. 손익 계산
        pnl_data = position.get_pnl(price)
        proceeds = price * position.quantity

        # 4. 현금 증가
        self.cash += proceeds

        # 5. 포지션 제거
        del self.positions[symbol]

        # 6. 거래 내역 저장
        trade = {
            "symbol": symbol,
            "strategy": position.strategy,
            "entry_date": position.entry_date,
            "exit_date": datetime.now().isoformat(),
            "entry_price": position.entry_price,
            "exit_price": price,
            "quantity": position.quantity,
            "pnl": pnl_data['pnl'],
            "pnl_pct": pnl_data['pnl_pct'],
            "exit_reason": reason
        }
        self.trade_history.append(trade)

        logger.info(f"✅ 포지션 청산: {symbol} {pnl_data['pnl']:+,.0f}원 ({pnl_data['pnl_pct']:+.2f}%)")

        # 7. 텔레그램 알림
        await self.telegram.send_sell_signal({
            "symbol": symbol,
            "price": price,
            "reason": reason,
            "pnl": pnl_data['pnl'],
            "pnl_pct": pnl_data['pnl_pct'],
            "timestamp": datetime.now().isoformat()
        })

        return trade

    async def check_all_positions(self, prices: Dict[str, float]):
        """
        모든 포지션 체크 (손절/익절)

        Args:
            prices: {symbol: current_price}
        """
        for symbol, position in list(self.positions.items()):
            current_price = prices.get(symbol)
            if not current_price:
                continue

            exit_reason = position.check_exit_conditions(current_price)
            if exit_reason:
                await self.close_position(symbol, current_price, exit_reason)

    def get_trade_statistics(self) -> Dict:
        """거래 통계"""
        if not self.trade_history:
            return {
                "total_trades": 0,
                "win_trades": 0,
                "lose_trades": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "total_pnl": 0
            }

        win_trades = [t for t in self.trade_history if t['pnl'] > 0]
        lose_trades = [t for t in self.trade_history if t['pnl'] <= 0]

        return {
            "total_trades": len(self.trade_history),
            "win_trades": len(win_trades),
            "lose_trades": len(lose_trades),
            "win_rate": len(win_trades) / len(self.trade_history) * 100,
            "avg_pnl": sum(t['pnl'] for t in self.trade_history) / len(self.trade_history),
            "total_pnl": sum(t['pnl'] for t in self.trade_history),
            "best_trade": max(self.trade_history, key=lambda t: t['pnl']),
            "worst_trade": min(self.trade_history, key=lambda t: t['pnl'])
        }


# 싱글톤
_position_manager = None


def get_position_manager() -> PositionManager:
    """포지션 관리자 싱글톤"""
    global _position_manager
    if _position_manager is None:
        _position_manager = PositionManager()
    return _position_manager

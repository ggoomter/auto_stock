"""
텔레그램 봇: 매매 신호 알림
"""
import os
from typing import Optional, Dict, List
from ..core.logging_config import logger

# 텔레그램 봇 라이브러리 (선택적 import)
try:
    import telegram
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot 라이브러리가 설치되지 않았습니다. pip install python-telegram-bot")


class TelegramNotifier:
    """텔레그램 알림 서비스"""

    def __init__(self):
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = os.getenv("TELEGRAM_CHAT_ID")
        self.bot: Optional[Bot] = None

        if self.bot_token and TELEGRAM_AVAILABLE:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("텔레그램 봇 초기화 완료")
            except Exception as e:
                logger.error(f"텔레그램 봇 초기화 실패: {e}")
        else:
            logger.warning("TELEGRAM_BOT_TOKEN이 설정되지 않았거나 라이브러리가 없습니다.")

    def is_enabled(self) -> bool:
        """텔레그램 알림이 활성화되어 있는지 확인"""
        return self.bot is not None and self.chat_id is not None

    async def send_message(self, message: str, parse_mode: str = "Markdown") -> bool:
        """
        메시지 전송

        Args:
            message: 전송할 메시지
            parse_mode: Markdown 또는 HTML

        Returns:
            성공 여부
        """
        if not self.is_enabled():
            logger.warning("텔레그램 봇이 비활성화되어 있습니다.")
            return False

        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode=parse_mode
            )
            logger.info(f"텔레그램 메시지 전송 완료: {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"텔레그램 메시지 전송 실패: {e}")
            return False

    async def send_buy_signal(self, signal: Dict) -> bool:
        """
        매수 신호 알림

        Args:
            signal: {
                "symbol": "AAPL",
                "price": 180.50,
                "reason": "MACD 골든 크로스",
                "indicators": {...}
            }
        """
        message = f"""
🟢 **매수 신호**

📊 종목: `{signal['symbol']}`
💰 가격: `${signal['price']:.2f}`
📝 이유: {signal['reason']}

**기술적 지표:**
"""
        if 'indicators' in signal:
            for key, value in signal['indicators'].items():
                if isinstance(value, float):
                    message += f"• {key}: `{value:.2f}`\n"
                else:
                    message += f"• {key}: `{value}`\n"

        message += f"\n⏰ {signal.get('timestamp', 'N/A')}"
        return await self.send_message(message)

    async def send_sell_signal(self, signal: Dict) -> bool:
        """
        매도 신호 알림

        Args:
            signal: {
                "symbol": "AAPL",
                "price": 185.30,
                "reason": "MACD 데드 크로스",
                "pnl": 500.0,
                "pnl_pct": 2.65
            }
        """
        pnl = signal.get('pnl', 0)
        pnl_pct = signal.get('pnl_pct', 0)
        emoji = "🟢" if pnl >= 0 else "🔴"

        message = f"""
🔴 **매도 신호**

📊 종목: `{signal['symbol']}`
💰 가격: `${signal['price']:.2f}`
📝 이유: {signal['reason']}

**수익/손실:**
{emoji} 손익: `${pnl:+,.2f}` (`{pnl_pct:+.2f}%`)

⏰ {signal.get('timestamp', 'N/A')}
"""
        return await self.send_message(message)

    async def send_portfolio_update(self, portfolio: Dict) -> bool:
        """
        포트폴리오 업데이트

        Args:
            portfolio: {
                "total_value": 105000,
                "cash": 50000,
                "positions": [...]
                "total_pnl": 5000,
                "total_pnl_pct": 5.0
            }
        """
        total_value = portfolio['total_value']
        cash = portfolio['cash']
        positions = portfolio.get('positions', [])
        total_pnl = portfolio.get('total_pnl', 0)
        total_pnl_pct = portfolio.get('total_pnl_pct', 0)

        emoji = "📈" if total_pnl >= 0 else "📉"

        message = f"""
{emoji} **포트폴리오 업데이트**

💼 총 자산: `${total_value:,.2f}`
💵 현금: `${cash:,.2f}`
📊 포지션: `{len(positions)}개`

**총 손익:**
{emoji} `${total_pnl:+,.2f}` (`{total_pnl_pct:+.2f}%`)

**보유 종목:**
"""
        for pos in positions[:5]:  # 최대 5개만 표시
            message += f"• {pos['symbol']}: {pos['shares']}주 @ ${pos['avg_price']:.2f}\n"

        return await self.send_message(message)

    async def send_error_alert(self, error: str, context: Optional[str] = None) -> bool:
        """오류 알림"""
        message = f"""
⚠️ **시스템 오류**

{error}
"""
        if context:
            message += f"\n**상세:**\n{context}"

        return await self.send_message(message)

    async def send_daily_report(self, report: Dict) -> bool:
        """
        일일 리포트

        Args:
            report: {
                "date": "2024-01-01",
                "total_trades": 5,
                "win_trades": 3,
                "daily_pnl": 1250.0,
                "daily_pnl_pct": 1.25
            }
        """
        daily_pnl = report['daily_pnl']
        emoji = "🎉" if daily_pnl >= 0 else "😢"

        message = f"""
📊 **일일 트레이딩 리포트**

📅 날짜: {report['date']}

**거래 통계:**
• 총 거래: `{report['total_trades']}회`
• 승리: `{report['win_trades']}회`
• 승률: `{(report['win_trades']/report['total_trades']*100):.1f}%`

**손익:**
{emoji} `${daily_pnl:+,.2f}` (`{report['daily_pnl_pct']:+.2f}%`)
"""
        return await self.send_message(message)


# 싱글톤 인스턴스
_notifier = None


def get_telegram_notifier() -> TelegramNotifier:
    """텔레그램 알림 서비스 싱글톤"""
    global _notifier
    if _notifier is None:
        _notifier = TelegramNotifier()
    return _notifier

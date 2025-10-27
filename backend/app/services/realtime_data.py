"""
실시간 데이터 수집 및 스트리밍
10분마다 yfinance에서 최신 데이터 가져오기
"""
import asyncio
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from ..core.logging_config import logger
import json
from collections import defaultdict


class RealtimeDataCollector:
    """실시간 데이터 수집기 (10분 간격)"""

    def __init__(self, update_interval: int = 600):  # 600초 = 10분
        self.update_interval = update_interval  # 초 단위
        self.subscribed_symbols: Set[str] = set()
        self.latest_data: Dict[str, pd.DataFrame] = {}
        self.last_update: Dict[str, datetime] = {}
        self.running = False
        self.callbacks: List[callable] = []  # WebSocket 전송용

    def subscribe(self, symbol: str):
        """종목 구독 추가"""
        self.subscribed_symbols.add(symbol)
        logger.info(f"종목 구독: {symbol} (총 {len(self.subscribed_symbols)}개)")

    def unsubscribe(self, symbol: str):
        """종목 구독 해제"""
        if symbol in self.subscribed_symbols:
            self.subscribed_symbols.remove(symbol)
            logger.info(f"종목 구독 해제: {symbol}")

    def register_callback(self, callback: callable):
        """데이터 업데이트 시 호출될 콜백 등록"""
        self.callbacks.append(callback)

    async def fetch_realtime_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        yfinance에서 최신 데이터 가져오기

        Args:
            symbol: 종목 코드

        Returns:
            최근 1일 데이터 (1분봉)
        """
        try:
            ticker = yf.Ticker(symbol)

            # 최근 1일 데이터 (1분봉)
            # yfinance는 1분봉을 최대 7일까지만 제공
            data = ticker.history(period="1d", interval="1m")

            if data.empty:
                logger.warning(f"{symbol}: 데이터 없음")
                return None

            # 컬럼명 소문자로 변환
            data.columns = [col.lower() for col in data.columns]

            # 현재 가격 정보 추가
            try:
                info = ticker.info
                current_price = info.get('currentPrice') or info.get('regularMarketPrice')
                if current_price:
                    data['current_price'] = current_price
            except:
                pass

            return data

        except Exception as e:
            logger.error(f"{symbol} 데이터 수집 오류: {e}")
            return None

    async def update_all_symbols(self):
        """모든 구독 종목 데이터 업데이트"""
        if not self.subscribed_symbols:
            return

        logger.info(f"데이터 업데이트 시작: {len(self.subscribed_symbols)}개 종목")

        for symbol in self.subscribed_symbols:
            data = await self.fetch_realtime_data(symbol)
            if data is not None:
                self.latest_data[symbol] = data
                self.last_update[symbol] = datetime.now()

                # 콜백 호출 (WebSocket으로 전송)
                await self._notify_subscribers(symbol, data)

        logger.info(f"데이터 업데이트 완료: {len(self.latest_data)}개 종목")

    async def _notify_subscribers(self, symbol: str, data: pd.DataFrame):
        """구독자에게 데이터 전송"""
        if data.empty:
            return

        # 최신 데이터만 전송
        latest = data.iloc[-1]
        message = {
            "type": "price_update",
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "open": float(latest['open']),
                "high": float(latest['high']),
                "low": float(latest['low']),
                "close": float(latest['close']),
                "volume": int(latest['volume']),
                "current_price": float(latest.get('current_price', latest['close']))
            }
        }

        # 모든 콜백 호출
        for callback in self.callbacks:
            try:
                await callback(message)
            except Exception as e:
                logger.error(f"콜백 오류: {e}")

    async def start(self):
        """백그라운드에서 주기적으로 데이터 수집"""
        self.running = True
        logger.info(f"실시간 데이터 수집 시작 (간격: {self.update_interval}초)")

        while self.running:
            try:
                await self.update_all_symbols()
            except Exception as e:
                logger.error(f"데이터 수집 오류: {e}")

            # 다음 업데이트까지 대기
            await asyncio.sleep(self.update_interval)

    def stop(self):
        """데이터 수집 중지"""
        self.running = False
        logger.info("실시간 데이터 수집 중지")

    def get_latest_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """특정 종목의 최신 데이터 반환"""
        return self.latest_data.get(symbol)

    def get_latest_price(self, symbol: str) -> Optional[Dict]:
        """특정 종목의 최신 가격 반환"""
        data = self.latest_data.get(symbol)
        if data is None or data.empty:
            return None

        latest = data.iloc[-1]
        return {
            "symbol": symbol,
            "timestamp": data.index[-1].isoformat(),
            "open": float(latest['open']),
            "high": float(latest['high']),
            "low": float(latest['low']),
            "close": float(latest['close']),
            "volume": int(latest['volume']),
            "current_price": float(latest.get('current_price', latest['close'])),
            "last_update": self.last_update.get(symbol).isoformat() if symbol in self.last_update else None
        }

    def get_all_latest_prices(self) -> List[Dict]:
        """모든 구독 종목의 최신 가격 반환"""
        return [
            self.get_latest_price(symbol)
            for symbol in self.subscribed_symbols
            if self.get_latest_price(symbol) is not None
        ]


# 싱글톤 인스턴스
_realtime_collector = None


def get_realtime_collector(update_interval: int = 600) -> RealtimeDataCollector:
    """실시간 데이터 수집기 싱글톤"""
    global _realtime_collector
    if _realtime_collector is None:
        _realtime_collector = RealtimeDataCollector(update_interval)
    return _realtime_collector


# =============================================================================
# 실시간 신호 생성기
# =============================================================================

class RealtimeSignalGenerator:
    """실시간으로 매매 신호 생성"""

    def __init__(self, strategy_name: str = "macd_rsi", strategy_params: Dict = None):
        self.strategy_name = strategy_name
        self.strategy_params = strategy_params or {}
        self.active_signals: Dict[str, Dict] = {}  # symbol -> signal info
        self.position_tracker: Dict[str, bool] = {}  # symbol -> in_position

    async def check_signals(self, symbol: str, data: pd.DataFrame) -> Optional[Dict]:
        """
        매매 신호 체크

        Args:
            symbol: 종목 코드
            data: 최신 데이터

        Returns:
            {"type": "BUY"|"SELL", "reason": "...", "price": float}
        """
        if data.empty or len(data) < 50:
            return None

        # 기술적 지표 계산
        from .indicators import IndicatorCalculator
        calculator = IndicatorCalculator(data)
        data_with_indicators = calculator.calculate_all()

        latest = data_with_indicators.iloc[-1]
        prev = data_with_indicators.iloc[-2] if len(data_with_indicators) > 1 else None

        # 간단한 MACD 크로스 전략 예시
        if prev is not None:
            # MACD 골든 크로스 (매수)
            if prev['MACD'] <= prev['MACD_signal'] and latest['MACD'] > latest['MACD_signal']:
                if latest['RSI'] < 70:  # 과매수 아닐 때
                    return {
                        "type": "BUY",
                        "symbol": symbol,
                        "reason": "MACD 골든 크로스 + RSI < 70",
                        "price": float(latest['close']),
                        "timestamp": datetime.now().isoformat(),
                        "indicators": {
                            "MACD": float(latest['MACD']),
                            "MACD_signal": float(latest['MACD_signal']),
                            "RSI": float(latest['RSI'])
                        }
                    }

            # MACD 데드 크로스 (매도)
            if prev['MACD'] >= prev['MACD_signal'] and latest['MACD'] < latest['MACD_signal']:
                if latest['RSI'] > 30:  # 과매도 아닐 때
                    return {
                        "type": "SELL",
                        "symbol": symbol,
                        "reason": "MACD 데드 크로스 + RSI > 30",
                        "price": float(latest['close']),
                        "timestamp": datetime.now().isoformat(),
                        "indicators": {
                            "MACD": float(latest['MACD']),
                            "MACD_signal": float(latest['MACD_signal']),
                            "RSI": float(latest['RSI'])
                        }
                    }

        return None


# 싱글톤
_signal_generator = None


def get_signal_generator(strategy_name: str = "macd_rsi", strategy_params: Dict = None) -> RealtimeSignalGenerator:
    """실시간 신호 생성기 싱글톤"""
    global _signal_generator
    if _signal_generator is None:
        _signal_generator = RealtimeSignalGenerator(strategy_name, strategy_params or {})
    return _signal_generator

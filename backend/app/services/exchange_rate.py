"""
환율 서비스: 실시간 USD-KRW 환율 조회 및 캐싱
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional


class ExchangeRateService:
    """실시간 환율 조회 서비스"""

    def __init__(self):
        self._cached_rate: Optional[float] = None
        self._cached_time: Optional[datetime] = None
        self.CACHE_MINUTES = 10  # 10분 캐시

    def get_usd_krw_rate(self) -> float:
        """
        실시간 USD-KRW 환율 조회 (캐싱 포함)

        Returns:
            USD 1달러 = KRW ?원
        """
        now = datetime.now()

        # 캐시 유효성 확인
        if self._cached_rate and self._cached_time:
            if now - self._cached_time < timedelta(minutes=self.CACHE_MINUTES):
                return self._cached_rate

        # yfinance로 실시간 환율 조회
        try:
            # KRW=X: USD/KRW 환율 심볼
            ticker = yf.Ticker("KRW=X")
            data = ticker.history(period="1d")

            if not data.empty:
                # 최신 종가 사용 (yfinance가 대문자 'Close' 반환)
                # indicators.py와 달리 환율 데이터는 컬럼명이 대문자로 반환됨
                if 'Close' in data.columns:
                    rate = float(data['Close'].iloc[-1])
                elif 'close' in data.columns:
                    rate = float(data['close'].iloc[-1])
                else:
                    raise KeyError(f"'Close' or 'close' column not found. Columns: {data.columns.tolist()}")
                self._cached_rate = rate
                self._cached_time = now
                print(f"환율 업데이트: $1 = KRW {rate:,.2f}")
                return rate
        except Exception as e:
            print(f"환율 조회 실패: {e}")

        # 실패시 기본 환율 (최근 평균)
        default_rate = 1320.0
        if not self._cached_rate:
            self._cached_rate = default_rate
            self._cached_time = now
            print(f"기본 환율 사용: $1 = KRW {default_rate:,.0f}")

        return self._cached_rate

    def usd_to_krw(self, usd_amount: float) -> float:
        """달러를 원화로 변환"""
        rate = self.get_usd_krw_rate()
        return usd_amount * rate

    def krw_to_usd(self, krw_amount: float) -> float:
        """원화를 달러로 변환"""
        rate = self.get_usd_krw_rate()
        return krw_amount / rate


# 전역 인스턴스
_global_exchange_service = ExchangeRateService()


def get_exchange_service() -> ExchangeRateService:
    """전역 환율 서비스 인스턴스 반환"""
    return _global_exchange_service


def get_current_usd_krw_rate() -> float:
    """현재 USD-KRW 환율 조회"""
    return _global_exchange_service.get_usd_krw_rate()

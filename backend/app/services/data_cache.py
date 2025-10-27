"""
실시간 주가 데이터 캐싱 레이어

yfinance API 호출을 최소화하면서도 최신 데이터 보장:
- 일중 데이터: 5분 캐시 (실시간성)
- 과거 데이터: 1시간 캐시 (변하지 않음)
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
import pandas as pd
import hashlib


class DataCache:
    """주가 데이터 캐시 관리"""

    def __init__(self):
        # 캐시 저장소: {cache_key: (data, cached_time)}
        self._cache: Dict[str, Tuple[pd.DataFrame, datetime]] = {}

        # 캐시 유효 시간 설정
        self.INTRADAY_CACHE_MINUTES = 5  # 당일 데이터: 5분
        self.HISTORICAL_CACHE_MINUTES = 60  # 과거 데이터: 1시간

    def _get_cache_key(self, symbol: str, start_date: str, end_date: str) -> str:
        """캐시 키 생성"""
        key_str = f"{symbol}_{start_date}_{end_date}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_intraday_query(self, end_date: str) -> bool:
        """당일 데이터 조회인지 확인"""
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            today = datetime.now()

            # 종료일이 오늘이면 실시간 데이터 조회
            return end_dt.date() >= today.date()
        except:
            return False

    def get(
        self,
        symbol: str,
        start_date: str,
        end_date: str
    ) -> Optional[pd.DataFrame]:
        """캐시에서 데이터 조회"""
        cache_key = self._get_cache_key(symbol, start_date, end_date)

        if cache_key not in self._cache:
            return None

        data, cached_time = self._cache[cache_key]

        # 캐시 유효성 확인
        is_intraday = self._is_intraday_query(end_date)
        cache_duration = (
            self.INTRADAY_CACHE_MINUTES if is_intraday
            else self.HISTORICAL_CACHE_MINUTES
        )

        expiry_time = cached_time + timedelta(minutes=cache_duration)

        if datetime.now() > expiry_time:
            # 캐시 만료
            del self._cache[cache_key]
            return None

        return data.copy()

    def set(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        data: pd.DataFrame
    ):
        """데이터를 캐시에 저장"""
        cache_key = self._get_cache_key(symbol, start_date, end_date)
        self._cache[cache_key] = (data.copy(), datetime.now())

    def clear(self):
        """캐시 전체 삭제"""
        self._cache.clear()

    def clear_symbol(self, symbol: str):
        """특정 심볼의 캐시만 삭제"""
        keys_to_delete = [
            key for key in self._cache.keys()
            if key.startswith(symbol)
        ]
        for key in keys_to_delete:
            del self._cache[key]

    def get_cache_stats(self) -> Dict:
        """캐시 통계"""
        return {
            "total_entries": len(self._cache),
            "cached_symbols": list(set(
                key.split('_')[0] for key in self._cache.keys()
            )),
            "cache_size_mb": sum(
                data.memory_usage(deep=True).sum()
                for data, _ in self._cache.values()
            ) / (1024 * 1024)
        }


# 전역 캐시 인스턴스
_global_cache = DataCache()


def get_cache() -> DataCache:
    """전역 캐시 인스턴스 반환"""
    return _global_cache

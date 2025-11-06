"""
백테스트 결과 캐싱 시스템

동일한 파라미터로 요청 시 API/LLM 호출 없이 즉시 결과 반환
"""
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from ..core.logging_config import logger


class BacktestCache:
    """백테스트 결과 캐싱 클래스"""

    def __init__(self, cache_dir: str = "cache/backtest_results"):
        """
        Args:
            cache_dir: 캐시 파일 저장 디렉토리
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"백테스트 캐시 디렉토리 초기화: {self.cache_dir}")

    def _generate_cache_key(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        strategy_name: str,
        initial_capital: float,
        **kwargs
    ) -> str:
        """
        캐시 키 생성 (해시값)

        Args:
            symbols: 종목 리스트
            start_date: 시작일
            end_date: 종료일
            strategy_name: 전략명
            initial_capital: 초기 자본
            **kwargs: 추가 파라미터

        Returns:
            SHA256 해시 문자열
        """
        # 캐시 키 생성용 데이터
        cache_data = {
            "symbols": sorted(symbols),  # 정렬하여 순서 무관하게
            "start_date": start_date,
            "end_date": end_date,
            "strategy_name": strategy_name,
            "initial_capital": initial_capital,
            **kwargs
        }

        # JSON 직렬화 후 SHA256 해시
        cache_str = json.dumps(cache_data, sort_keys=True)
        cache_hash = hashlib.sha256(cache_str.encode()).hexdigest()

        logger.debug(f"캐시 키 생성: {cache_hash[:16]}... (전략: {strategy_name}, 종목: {symbols})")
        return cache_hash

    def get(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        strategy_name: str,
        initial_capital: float,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        캐시된 결과 조회

        Returns:
            캐시된 결과 (없으면 None)
        """
        cache_key = self._generate_cache_key(
            symbols, start_date, end_date, strategy_name, initial_capital, **kwargs
        )
        cache_file = self.cache_dir / f"{cache_key}.json"

        if not cache_file.exists():
            logger.debug(f"캐시 미스: {cache_key[:16]}...")
            return None

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # 메타데이터 확인
            cached_at = cached_data.get('cached_at')
            logger.info(
                f"✅ 캐시 히트: {strategy_name} / {symbols} "
                f"(캐시 생성: {cached_at})"
            )

            return cached_data.get('result')

        except Exception as e:
            logger.error(f"캐시 읽기 실패: {e}")
            return None

    def set(
        self,
        symbols: list,
        start_date: str,
        end_date: str,
        strategy_name: str,
        initial_capital: float,
        result: Dict[str, Any],
        **kwargs
    ):
        """
        백테스트 결과 캐싱

        Args:
            symbols: 종목 리스트
            start_date: 시작일
            end_date: 종료일
            strategy_name: 전략명
            initial_capital: 초기 자본
            result: 백테스트 결과
            **kwargs: 추가 파라미터
        """
        cache_key = self._generate_cache_key(
            symbols, start_date, end_date, strategy_name, initial_capital, **kwargs
        )
        cache_file = self.cache_dir / f"{cache_key}.json"

        # 캐시 데이터 구조
        cache_data = {
            "cached_at": datetime.now().isoformat(),
            "params": {
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "strategy_name": strategy_name,
                "initial_capital": initial_capital,
                **kwargs
            },
            "result": result
        }

        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            logger.info(
                f"💾 캐시 저장: {strategy_name} / {symbols} "
                f"(파일: {cache_key[:16]}...json)"
            )

        except Exception as e:
            logger.error(f"캐시 저장 실패: {e}")

    def clear_cache(self, older_than_days: Optional[int] = None):
        """
        캐시 삭제

        Args:
            older_than_days: N일 이상 오래된 캐시만 삭제 (None이면 전체 삭제)
        """
        deleted_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                if older_than_days is not None:
                    # 파일 수정 시간 확인
                    file_mtime = cache_file.stat().st_mtime
                    file_age_days = (datetime.now().timestamp() - file_mtime) / 86400

                    if file_age_days < older_than_days:
                        continue

                cache_file.unlink()
                deleted_count += 1

            except Exception as e:
                logger.error(f"캐시 파일 삭제 실패: {cache_file.name} - {e}")

        logger.info(f"캐시 삭제 완료: {deleted_count}개 파일")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        캐시 통계 조회

        Returns:
            캐시 파일 개수, 총 크기 등
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)

        return {
            "total_files": len(cache_files),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "cache_dir": str(self.cache_dir)
        }


# 전역 캐시 인스턴스
_cache_instance: Optional[BacktestCache] = None


def get_cache() -> BacktestCache:
    """전역 캐시 인스턴스 반환 (싱글톤)"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = BacktestCache()
    return _cache_instance

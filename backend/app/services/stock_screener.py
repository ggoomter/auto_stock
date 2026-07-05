"""
종목 발굴 시스템 (펀더멘털 스크리너)

좋은 기업을 찾기 위한 다양한 스크리닝 전략:
1. 가치주 (Value): 저PER, 저PBR, 고배당
2. 성장주 (Growth): 매출/이익 성장률, 낮은 PEG
3. 퀄리티 (Quality): 높은 ROE, 낮은 부채비율
4. 모멘텀 (Momentum): 상승 추세, 거래량 증가
5. 콤보 (Combo): 복합 전략 (GARP, 워렌 버핏 스타일)
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

from ..core.logging_config import logger
from .korean_stock_data import get_korean_stock_fetcher



class ScreenerType(Enum):
    """스크리너 유형"""
    VALUE = "value"                # 가치주
    GROWTH = "growth"              # 성장주
    QUALITY = "quality"            # 퀄리티
    MOMENTUM = "momentum"          # 모멘텀
    DIVIDEND = "dividend"          # 배당주
    GARP = "garp"                  # Growth At Reasonable Price
    BUFFETT = "buffett"            # 워렌 버핏 스타일
    LYNCH = "lynch"                # 피터 린치 스타일
    SAFE = "safe"                  # 안전주 (낮은 변동성 + 우량)


@dataclass
class ScreenerCriteria:
    """스크리너 조건"""
    # 밸류에이션
    max_pe: Optional[float] = None           # PER 상한
    min_pe: Optional[float] = None           # PER 하한
    max_pb: Optional[float] = None           # PBR 상한
    max_ps: Optional[float] = None           # PSR 상한
    max_peg: Optional[float] = None          # PEG 상한

    # 수익성
    min_roe: Optional[float] = None          # ROE 하한 (%)
    min_roa: Optional[float] = None          # ROA 하한 (%)
    min_profit_margin: Optional[float] = None # 순이익률 하한 (%)

    # 성장성
    min_revenue_growth: Optional[float] = None     # 매출 성장률 하한 (%)
    min_earnings_growth: Optional[float] = None    # 이익 성장률 하한 (%)

    # 재무 안정성
    max_debt_to_equity: Optional[float] = None     # 부채비율 상한 (%)
    min_current_ratio: Optional[float] = None      # 유동비율 하한

    # 배당
    min_dividend_yield: Optional[float] = None     # 배당수익률 하한 (%)
    min_payout_ratio: Optional[float] = None       # 배당성향 하한 (%)
    max_payout_ratio: Optional[float] = None       # 배당성향 상한 (%)

    # 모멘텀
    min_price_change_52w: Optional[float] = None   # 52주 가격 변동률 하한 (%)
    min_volume_avg: Optional[float] = None         # 평균 거래량 하한

    # 시가총액
    min_market_cap: Optional[float] = None         # 시가총액 하한 ($)
    max_market_cap: Optional[float] = None         # 시가총액 상한 ($)


@dataclass
class StockScore:
    """종목 점수"""
    symbol: str
    name: str
    score: float           # 종합 점수 (0-100)
    rank: int              # 순위

    # 개별 점수
    value_score: float     # 가치 점수
    growth_score: float    # 성장 점수
    quality_score: float   # 퀄리티 점수
    momentum_score: float  # 모멘텀 점수

    # 핵심 지표
    current_price: float
    pe_ratio: Optional[float]
    pb_ratio: Optional[float]
    roe: Optional[float]
    debt_to_equity: Optional[float]
    market_cap: Optional[float]

    # 상세 정보
    details: Dict


# 사전 정의된 스크리너 조건
PRESET_SCREENERS = {
    ScreenerType.VALUE: ScreenerCriteria(
        max_pe=15.0,
        max_pb=2.0,
        min_roe=10.0,
        max_debt_to_equity=70.0,
        min_market_cap=1_000_000_000  # $1B
    ),
    ScreenerType.GROWTH: ScreenerCriteria(
        min_revenue_growth=20.0,
        min_earnings_growth=20.0,
        max_peg=1.5,
        min_roe=15.0,
        min_market_cap=500_000_000  # $500M
    ),
    ScreenerType.QUALITY: ScreenerCriteria(
        min_roe=20.0,
        min_roa=10.0,
        max_debt_to_equity=50.0,
        min_current_ratio=1.5,
        min_profit_margin=15.0
    ),
    ScreenerType.DIVIDEND: ScreenerCriteria(
        min_dividend_yield=3.0,
        min_payout_ratio=30.0,
        max_payout_ratio=70.0,
        min_roe=10.0,
        max_debt_to_equity=60.0
    ),
    ScreenerType.GARP: ScreenerCriteria(
        max_peg=1.0,
        min_revenue_growth=15.0,
        max_pe=25.0,
        min_roe=15.0,
        max_debt_to_equity=60.0
    ),
    ScreenerType.BUFFETT: ScreenerCriteria(
        min_roe=15.0,
        max_debt_to_equity=50.0,
        max_pe=20.0,
        max_pb=3.0,
        min_profit_margin=10.0,
        min_market_cap=10_000_000_000  # $10B (우량 대형주)
    ),
    ScreenerType.LYNCH: ScreenerCriteria(
        max_peg=1.0,
        min_earnings_growth=20.0,
        max_pe=30.0,
        min_roe=15.0
    ),
    ScreenerType.SAFE: ScreenerCriteria(
        min_roe=12.0,
        max_debt_to_equity=40.0,
        min_current_ratio=2.0,
        max_pe=18.0,
        max_pb=2.5,
        min_market_cap=5_000_000_000  # $5B
    ),
    ScreenerType.MOMENTUM: ScreenerCriteria(
        min_price_change_52w=20.0,
        min_volume_avg=1_000_000,
        min_market_cap=1_000_000_000
    )
}


class StockScreener:
    """종목 스크리너"""

    def __init__(self):
        self.cache: Dict[str, Dict] = {}  # 종목 데이터 캐시
        self.cache_expiry: Dict[str, datetime] = {}
        self.cache_duration_hours = 24
        logger.info("종목 스크리너 초기화")

    def screen_stocks(
        self,
        symbols: List[str],
        screener_type: ScreenerType = ScreenerType.BUFFETT,
        custom_criteria: Optional[ScreenerCriteria] = None,
        top_n: int = 10
    ) -> List[StockScore]:
        """
        종목 스크리닝

        Args:
            symbols: 스크리닝할 종목 리스트
            screener_type: 스크리너 유형
            custom_criteria: 커스텀 조건 (None이면 사전 정의 사용)
            top_n: 상위 N개 종목만 반환

        Returns:
            StockScore 리스트 (점수 순 정렬)
        """
        logger.info(f"종목 스크리닝 시작: {len(symbols)}개 종목, 유형: {screener_type.value}")

        # 조건 설정
        criteria = custom_criteria or PRESET_SCREENERS.get(screener_type, ScreenerCriteria())

        # 데이터 수집 (Batch Optimization)
        fetcher = get_korean_stock_fetcher()
        stocks_data = fetcher.get_multiple_stocks_data(symbols)

        # 각 종목 분석
        results = []
        for symbol, data in stocks_data.items():
            try:
                if not data:
                    continue

                # 데이터 매핑 (Fetcher -> Screener format)
                mapped_data = self._map_fetcher_data(symbol, data)

                # 조건 확인
                if not self._meets_criteria(mapped_data, criteria):
                    continue

                # 점수 계산
                score = self._calculate_score(mapped_data, screener_type)
                results.append(score)

            except Exception as e:
                logger.warning(f"종목 분석 실패 ({symbol}): {e}")
                continue

        # 점수 순 정렬
        results.sort(key=lambda x: x.score, reverse=True)

        # 순위 부여
        for rank, stock in enumerate(results[:top_n], start=1):
            stock.rank = rank

        logger.info(f"스크리닝 완료: {len(results)}개 종목 발견")

        return results[:top_n]

    def _map_fetcher_data(self, symbol: str, data: Dict) -> Dict:
        """Fetcher 데이터를 Screener 내부 포맷으로 변환"""
        metrics = data.get('metrics', {})
        
        # ROE 단위 보정 (0.15 -> 15.0)
        roe = metrics.get("ROE")
        if roe and roe < 1.0: roe *= 100
        
        # 순이익률 단위 보정
        margin = metrics.get("net_margin")
        if margin and margin < 1.0: margin *= 100
        
        # 부채비율 단위 보정 (0.5 -> 50.0)
        debt = metrics.get("debt_to_equity")
        if debt and debt < 10.0: debt *= 100 # 보통 100% 이상도 나오므로 10 미만이면 소수점으로 간주

        return {
            "symbol": symbol,
            "name": data.get("name", symbol),
            "current_price": data.get("current_price", 0),
            "market_cap": data.get("market_cap"),
            "pe_ratio": metrics.get("PE"),
            "pb_ratio": metrics.get("PB"),
            "roe": roe,
            "debt_to_equity": debt,
            "current_ratio": metrics.get("current_ratio"),
            "profit_margin": margin,
            "dividend_yield": metrics.get("dividend_yield"), 
            "revenue_growth": None, # Fetcher에서 제공하지 않을 수 있음
            "earnings_growth": None,
            "peg_ratio": None,
            "52w_high": None, 
            "price_change_52w": None,
            "info": data
        }

    def screen_market(
        self,
        market: str = "ALL",
        screener_type: ScreenerType = ScreenerType.BUFFETT,
        top_n: int = 10
    ) -> List[StockScore]:
        """
        전체 시장 스크리닝 (Bulk Data 사용으로 고속 처리)
        
        Args:
            market: "KOSPI", "KOSDAQ", "ALL"
            screener_type: 스크리너 유형
            top_n: 상위 N개 종목
            
        Returns:
            StockScore 리스트
        """
        logger.info(f"전체 시장 스크리닝 시작 ({market}, {screener_type.value})")
        
        fetcher = get_korean_stock_fetcher()
        
        # 1. 전체 펀더멘털 데이터 가져오기 (고속)
        df = fetcher.get_market_fundamentals(market=market)
        if df.empty:
            logger.warning("시장 데이터를 가져올 수 없습니다.")
            return []
            
        # 2. 1차 필터링 (Vectorized)
        criteria = PRESET_SCREENERS.get(screener_type, ScreenerCriteria())
        
        # PER 필터
        if criteria.max_pe:
            df = df[df['PER'] <= criteria.max_pe]
        if criteria.min_pe:
            df = df[df['PER'] >= criteria.min_pe]
            
        # PBR 필터
        if criteria.max_pb:
            df = df[df['PBR'] <= criteria.max_pb]
            
        # 배당수익률 필터
        if criteria.min_dividend_yield:
            df = df[df['DIV'] >= criteria.min_dividend_yield]
            
        # ROE 필터 (PyKrx 데이터에는 ROE가 없을 수 있음, 있으면 필터링)
        if 'ROE' in df.columns and criteria.min_roe:
            df = df[df['ROE'] >= criteria.min_roe / 100.0] # PyKrx ROE 단위 확인 필요
            
        candidates = df.index.tolist()
        logger.info(f"1차 필터링 결과: {len(candidates)}개 종목")
        
        # 3. 후보군에 대해 상세 분석 (기존 로직 재사용)
        # 너무 많으면 상위 50개만 분석 (시가총액 순 등 정렬이 필요하지만 여기선 단순 절삭)
        if len(candidates) > 50:
            # PBR이나 PER 순으로 정렬해서 자르기
            if screener_type in [ScreenerType.VALUE, ScreenerType.BUFFETT]:
                # 저평가 순
                candidates = df.sort_values(by='PER').head(50).index.tolist()
            else:
                candidates = candidates[:50]
                
        # 종목 코드에 .KS, .KQ 붙이기
        final_candidates = []
        for ticker in candidates:
            if market == "KOSPI":
                final_candidates.append(f"{ticker}.KS")
            elif market == "KOSDAQ":
                final_candidates.append(f"{ticker}.KQ")
            else:
                # market 정보가 df에 있으면 사용
                if 'market' in df.columns:
                    m = df.loc[ticker, 'market']
                    suffix = ".KS" if m == "KOSPI" else ".KQ"
                    final_candidates.append(f"{ticker}{suffix}")
                else:
                    # 모르면 둘 다 시도하거나 생략
                    final_candidates.append(f"{ticker}.KS")

        return self.screen_stocks(final_candidates, screener_type, top_n=top_n)


    def _get_stock_data(self, symbol: str) -> Optional[Dict]:
        """Deprecated: Use fetcher.get_stock_data instead"""
        fetcher = get_korean_stock_fetcher()
        data = fetcher.get_stock_data(symbol)
        if data:
            return self._map_fetcher_data(symbol, data)
        return None

    def _calculate_52w_return(self, history: pd.DataFrame) -> Optional[float]:
        """52주 수익률 계산"""
        if history.empty or len(history) < 2:
            return None

        start_price = history['Close'].iloc[0]
        end_price = history['Close'].iloc[-1]

        if start_price > 0:
            return ((end_price / start_price) - 1) * 100
        return None

    def _meets_criteria(self, data: Dict, criteria: ScreenerCriteria) -> bool:
        """조건 충족 여부 확인"""
        # PER
        if criteria.max_pe and data.get("pe_ratio"):
            if data["pe_ratio"] > criteria.max_pe:
                return False
        if criteria.min_pe and data.get("pe_ratio"):
            if data["pe_ratio"] < criteria.min_pe:
                return False

        # PBR
        if criteria.max_pb and data.get("pb_ratio"):
            if data["pb_ratio"] > criteria.max_pb:
                return False

        # PEG
        if criteria.max_peg and data.get("peg_ratio"):
            if data["peg_ratio"] > criteria.max_peg:
                return False

        # ROE
        if criteria.min_roe and data.get("roe"):
            if data["roe"] < criteria.min_roe:
                return False

        # ROA
        if criteria.min_roa and data.get("roa"):
            if data["roa"] < criteria.min_roa:
                return False

        # 순이익률
        if criteria.min_profit_margin and data.get("profit_margin"):
            if data["profit_margin"] < criteria.min_profit_margin:
                return False

        # 매출 성장률
        if criteria.min_revenue_growth and data.get("revenue_growth"):
            if data["revenue_growth"] < criteria.min_revenue_growth:
                return False

        # 이익 성장률
        if criteria.min_earnings_growth and data.get("earnings_growth"):
            if data["earnings_growth"] < criteria.min_earnings_growth:
                return False

        # 부채비율
        if criteria.max_debt_to_equity and data.get("debt_to_equity"):
            if data["debt_to_equity"] > criteria.max_debt_to_equity:
                return False

        # 유동비율
        if criteria.min_current_ratio and data.get("current_ratio"):
            if data["current_ratio"] < criteria.min_current_ratio:
                return False

        # 배당수익률
        if criteria.min_dividend_yield and data.get("dividend_yield"):
            if data["dividend_yield"] < criteria.min_dividend_yield:
                return False

        # 시가총액
        if criteria.min_market_cap and data.get("market_cap"):
            if data["market_cap"] < criteria.min_market_cap:
                return False
        if criteria.max_market_cap and data.get("market_cap"):
            if data["market_cap"] > criteria.max_market_cap:
                return False

        return True

    def _calculate_score(self, data: Dict, screener_type: ScreenerType) -> StockScore:
        """종목 점수 계산 (0-100)"""
        # 개별 점수 계산
        value_score = self._value_score(data)
        growth_score = self._growth_score(data)
        quality_score = self._quality_score(data)
        momentum_score = self._momentum_score(data)

        # 스크리너 유형별 가중치
        weights = self._get_score_weights(screener_type)

        # 종합 점수
        total_score = (
            value_score * weights["value"] +
            growth_score * weights["growth"] +
            quality_score * weights["quality"] +
            momentum_score * weights["momentum"]
        )

        return StockScore(
            symbol=data["symbol"],
            name=data["name"],
            score=total_score,
            rank=0,  # 나중에 설정
            value_score=value_score,
            growth_score=growth_score,
            quality_score=quality_score,
            momentum_score=momentum_score,
            current_price=data["current_price"],
            pe_ratio=data.get("pe_ratio"),
            pb_ratio=data.get("pb_ratio"),
            roe=data.get("roe"),
            debt_to_equity=data.get("debt_to_equity"),
            market_cap=data.get("market_cap"),
            details=data
        )

    def _get_score_weights(self, screener_type: ScreenerType) -> Dict[str, float]:
        """스크리너 유형별 점수 가중치"""
        weights_map = {
            ScreenerType.VALUE: {"value": 0.5, "growth": 0.1, "quality": 0.3, "momentum": 0.1},
            ScreenerType.GROWTH: {"value": 0.1, "growth": 0.5, "quality": 0.2, "momentum": 0.2},
            ScreenerType.QUALITY: {"value": 0.2, "growth": 0.2, "quality": 0.5, "momentum": 0.1},
            ScreenerType.DIVIDEND: {"value": 0.4, "growth": 0.1, "quality": 0.4, "momentum": 0.1},
            ScreenerType.GARP: {"value": 0.3, "growth": 0.4, "quality": 0.2, "momentum": 0.1},
            ScreenerType.BUFFETT: {"value": 0.3, "growth": 0.2, "quality": 0.4, "momentum": 0.1},
            ScreenerType.LYNCH: {"value": 0.2, "growth": 0.5, "quality": 0.2, "momentum": 0.1},
            ScreenerType.SAFE: {"value": 0.3, "growth": 0.1, "quality": 0.5, "momentum": 0.1},
            ScreenerType.MOMENTUM: {"value": 0.1, "growth": 0.2, "quality": 0.2, "momentum": 0.5}
        }
        return weights_map.get(screener_type, {"value": 0.25, "growth": 0.25, "quality": 0.25, "momentum": 0.25})

    def _value_score(self, data: Dict) -> float:
        """가치 점수 (0-100)"""
        score = 0.0
        count = 0

        # PER (낮을수록 좋음)
        pe = data.get("pe_ratio")
        if pe and pe > 0:
            if pe < 10:
                score += 100
            elif pe < 15:
                score += 80
            elif pe < 20:
                score += 60
            elif pe < 25:
                score += 40
            else:
                score += 20
            count += 1

        # PBR (낮을수록 좋음)
        pb = data.get("pb_ratio")
        if pb and pb > 0:
            if pb < 1:
                score += 100
            elif pb < 2:
                score += 80
            elif pb < 3:
                score += 60
            else:
                score += 40
            count += 1

        # 배당수익률 (높을수록 좋음)
        div_yield = data.get("dividend_yield")
        if div_yield and div_yield > 0:
            if div_yield > 5:
                score += 100
            elif div_yield > 3:
                score += 80
            elif div_yield > 2:
                score += 60
            else:
                score += 40
            count += 1

        return score / count if count > 0 else 50.0

    def _growth_score(self, data: Dict) -> float:
        """성장 점수 (0-100)"""
        score = 0.0
        count = 0

        # 매출 성장률
        rev_growth = data.get("revenue_growth")
        if rev_growth is not None:
            if rev_growth > 30:
                score += 100
            elif rev_growth > 20:
                score += 80
            elif rev_growth > 10:
                score += 60
            elif rev_growth > 0:
                score += 40
            else:
                score += 20
            count += 1

        # 이익 성장률
        earn_growth = data.get("earnings_growth")
        if earn_growth is not None:
            if earn_growth > 30:
                score += 100
            elif earn_growth > 20:
                score += 80
            elif earn_growth > 10:
                score += 60
            elif earn_growth > 0:
                score += 40
            else:
                score += 20
            count += 1

        # PEG (낮을수록 좋음)
        peg = data.get("peg_ratio")
        if peg and peg > 0:
            if peg < 0.5:
                score += 100
            elif peg < 1.0:
                score += 80
            elif peg < 1.5:
                score += 60
            else:
                score += 40
            count += 1

        return score / count if count > 0 else 50.0

    def _quality_score(self, data: Dict) -> float:
        """퀄리티 점수 (0-100)"""
        score = 0.0
        count = 0

        # ROE
        roe = data.get("roe")
        if roe is not None:
            if roe > 25:
                score += 100
            elif roe > 20:
                score += 80
            elif roe > 15:
                score += 60
            elif roe > 10:
                score += 40
            else:
                score += 20
            count += 1

        # 부채비율 (낮을수록 좋음)
        debt = data.get("debt_to_equity")
        if debt is not None:
            if debt < 30:
                score += 100
            elif debt < 50:
                score += 80
            elif debt < 70:
                score += 60
            elif debt < 100:
                score += 40
            else:
                score += 20
            count += 1

        # 순이익률
        margin = data.get("profit_margin")
        if margin is not None:
            if margin > 20:
                score += 100
            elif margin > 15:
                score += 80
            elif margin > 10:
                score += 60
            elif margin > 5:
                score += 40
            else:
                score += 20
            count += 1

        # 유동비율
        current_ratio = data.get("current_ratio")
        if current_ratio is not None:
            if current_ratio > 2:
                score += 100
            elif current_ratio > 1.5:
                score += 80
            elif current_ratio > 1:
                score += 60
            else:
                score += 40
            count += 1

        return score / count if count > 0 else 50.0

    def _momentum_score(self, data: Dict) -> float:
        """모멘텀 점수 (0-100)"""
        score = 0.0
        count = 0

        # 52주 수익률
        price_change = data.get("price_change_52w")
        if price_change is not None:
            if price_change > 50:
                score += 100
            elif price_change > 30:
                score += 80
            elif price_change > 10:
                score += 60
            elif price_change > 0:
                score += 40
            else:
                score += 20
            count += 1

        # 현재가 vs 52주 고가
        current = data.get("current_price")
        high_52w = data.get("52w_high")
        if current and high_52w and high_52w > 0:
            pct_from_high = (current / high_52w - 1) * 100
            if pct_from_high > -5:
                score += 100
            elif pct_from_high > -10:
                score += 80
            elif pct_from_high > -20:
                score += 60
            else:
                score += 40
            count += 1

        return score / count if count > 0 else 50.0

    def get_best_stocks_by_category(
        self,
        symbols: List[str],
        top_n: int = 5
    ) -> Dict[str, List[StockScore]]:
        """
        카테고리별 최고 종목 찾기

        Returns:
            {
                "value": [...],
                "growth": [...],
                "quality": [...],
                "safe": [...]
            }
        """
        logger.info(f"카테고리별 종목 분석 시작 ({len(symbols)}개)")

        results = {}

        categories = [
            ScreenerType.VALUE,
            ScreenerType.GROWTH,
            ScreenerType.QUALITY,
            ScreenerType.SAFE
        ]

        for category in categories:
            try:
                stocks = self.screen_stocks(symbols, category, top_n=top_n)
                results[category.value] = stocks
                logger.info(f"{category.value}: {len(stocks)}개 발견")
            except Exception as e:
                logger.error(f"{category.value} 분석 실패: {e}")
                results[category.value] = []

        return results

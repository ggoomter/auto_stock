"""
고급 리스크 관리 시스템
포트폴리오 수준의 리스크 관리 및 자금 관리
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from ..core.logging_config import logger


class RiskLevel(Enum):
    """리스크 레벨 정의"""
    LOW = "low"           # 안정적
    MEDIUM = "medium"     # 보통
    HIGH = "high"         # 공격적
    EXTREME = "extreme"   # 초고위험


@dataclass
class PortfolioRiskMetrics:
    """포트폴리오 위험 지표"""
    위험가치_95: float           # 95% 신뢰수준의 최대 예상 손실
    조건부_위험가치_95: float    # 극단적 손실 상황의 평균 손실
    위험조정수익률: float        # 위험 대비 수익률 (샤프 지수)
    최대낙폭: float             # 최고점 대비 최대 하락률
    시장민감도: float           # 시장 변동에 대한 민감도 (베타)
    상관관계_매트릭스: pd.DataFrame  # 종목 간 상관관계
    집중도_위험: float          # 특정 종목 편중 위험
    유동성_점수: float          # 거래 활성도 점수
    전체_위험_수준: RiskLevel   # 종합 위험 등급


@dataclass
class PositionSizingResult:
    """포지션 크기 결정 결과"""
    종목코드: str
    추천_주식수: int
    포지션_금액: float
    포지션_비율: float         # 전체 자본 대비 비율
    손절가: float
    목표가: float
    위험_금액: float           # 예상 최대 손실액
    위험_비율: float           # 전체 자본 대비 위험도


class AdvancedRiskManager:
    """고급 리스크 관리자"""

    def __init__(self,
                 total_capital: float = 10_000_000,
                 max_risk_per_trade: float = 0.02,     # 거래당 최대 2% 리스크
                 max_portfolio_risk: float = 0.06,     # 포트폴리오 최대 6% 리스크
                 max_position_size: float = 0.15):     # 종목당 최대 15%
        """
        Args:
            total_capital: 총 자본금 (KRW)
            max_risk_per_trade: 거래당 최대 리스크 비율
            max_portfolio_risk: 포트폴리오 전체 최대 리스크
            max_position_size: 단일 종목 최대 비중
        """
        self.total_capital = total_capital
        self.max_risk_per_trade = max_risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.max_position_size = max_position_size

        # 켈리 공식 파라미터
        self.kelly_fraction = 0.25  # 켈리 비율의 25%만 사용 (보수적)

        # 동적 리스크 조정
        self.dynamic_adjustment = True
        self.market_volatility_threshold = 0.3  # VIX 30 이상시 리스크 축소

    def calculate_portfolio_risk(self,
                                positions: List[Dict],
                                price_history: Dict[str, pd.DataFrame],
                                market_data: Optional[pd.DataFrame] = None) -> PortfolioRiskMetrics:
        """
        포트폴리오 전체 리스크 계산

        Args:
            positions: 현재 포지션 리스트
            price_history: 종목별 가격 이력
            market_data: 시장 지표 (KOSPI, VIX 등)

        Returns:
            포트폴리오 리스크 지표
        """
        if not positions:
            return self._empty_risk_metrics()

        # 포트폴리오 수익률 계산
        portfolio_returns = self._calculate_portfolio_returns(positions, price_history)

        # VaR 계산 (95% 신뢰수준)
        var_95 = np.percentile(portfolio_returns, 5)

        # CVaR (Expected Shortfall) 계산
        cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()

        # 샤프 비율
        sharpe = self._calculate_sharpe_ratio(portfolio_returns)

        # 최대 낙폭
        max_dd = self._calculate_max_drawdown(portfolio_returns)

        # 베타 계산
        beta = self._calculate_portfolio_beta(portfolio_returns, market_data)

        # 상관관계 매트릭스
        correlation = self._calculate_correlation_matrix(positions, price_history)

        # 집중도 리스크 (HHI)
        concentration = self._calculate_concentration_risk(positions)

        # 유동성 점수
        liquidity = self._calculate_liquidity_score(positions, price_history)

        # 전체 리스크 레벨 판단
        risk_level = self._determine_risk_level(var_95, sharpe, concentration)

        return PortfolioRiskMetrics(
            위험가치_95=var_95,
            조건부_위험가치_95=cvar_95,
            위험조정수익률=sharpe,
            최대낙폭=max_dd,
            시장민감도=beta,
            상관관계_매트릭스=correlation,
            집중도_위험=concentration,
            유동성_점수=liquidity,
            전체_위험_수준=risk_level
        )

    def calculate_position_size(self,
                               symbol: str,
                               entry_price: float,
                               stop_loss: float,
                               strategy_win_rate: float = 0.5,
                               avg_win_loss_ratio: float = 2.0,
                               current_positions: List[Dict] = None) -> PositionSizingResult:
        """
        켈리 공식과 리스크 관리를 결합한 최적 포지션 크기 계산

        Args:
            symbol: 종목 코드
            entry_price: 진입 가격
            stop_loss: 손절 가격
            strategy_win_rate: 전략 승률
            avg_win_loss_ratio: 평균 손익비
            current_positions: 현재 보유 포지션

        Returns:
            포지션 사이징 결과
        """
        # 켈리 비율 계산
        kelly = self._calculate_kelly_criterion(strategy_win_rate, avg_win_loss_ratio)

        # 리스크 기반 포지션 크기
        risk_per_share = abs(entry_price - stop_loss)
        max_risk_amount = self.total_capital * self.max_risk_per_trade
        risk_based_shares = int(max_risk_amount / risk_per_share)

        # 켈리 기준 포지션 크기
        kelly_position_size = self.total_capital * kelly * self.kelly_fraction
        kelly_based_shares = int(kelly_position_size / entry_price)

        # 최대 포지션 제한
        max_position_amount = self.total_capital * self.max_position_size
        max_shares = int(max_position_amount / entry_price)

        # 현재 포트폴리오 리스크 확인
        if current_positions:
            current_risk = self._calculate_current_portfolio_risk(current_positions)
            if current_risk > self.max_portfolio_risk * 0.8:  # 80% 도달시 축소
                max_shares = int(max_shares * 0.5)

        # 최종 주식 수 결정 (가장 보수적인 값)
        final_shares = min(risk_based_shares, kelly_based_shares, max_shares)

        # 목표가 계산 (리스크 리워드 비율 기반)
        take_profit = entry_price + (risk_per_share * avg_win_loss_ratio)

        return PositionSizingResult(
            종목코드=symbol,
            추천_주식수=final_shares,
            포지션_금액=final_shares * entry_price,
            포지션_비율=(final_shares * entry_price) / self.total_capital,
            손절가=stop_loss,
            목표가=take_profit,
            위험_금액=final_shares * risk_per_share,
            위험_비율=(final_shares * risk_per_share) / self.total_capital
        )

    def adjust_for_market_conditions(self,
                                    base_risk: float,
                                    vix_level: float = 20,
                                    market_trend: str = "neutral") -> float:
        """
        시장 상황에 따른 동적 리스크 조정

        Args:
            base_risk: 기본 리스크 수준
            vix_level: 변동성 지수
            market_trend: 시장 트렌드 (bullish/neutral/bearish)

        Returns:
            조정된 리스크 수준
        """
        adjusted_risk = base_risk

        # VIX 수준에 따른 조정
        if vix_level > 30:
            adjusted_risk *= 0.5  # 고변동성시 리스크 50% 축소
        elif vix_level > 25:
            adjusted_risk *= 0.7
        elif vix_level < 15:
            adjusted_risk *= 1.2  # 저변동성시 리스크 20% 확대

        # 시장 트렌드에 따른 조정
        if market_trend == "bearish":
            adjusted_risk *= 0.7
        elif market_trend == "bullish":
            adjusted_risk *= 1.1

        # 최대/최소 제한
        adjusted_risk = max(self.max_risk_per_trade * 0.3,
                           min(adjusted_risk, self.max_risk_per_trade * 1.5))

        return adjusted_risk

    def calculate_correlation_hedge(self,
                                   target_symbol: str,
                                   portfolio: List[str],
                                   correlation_matrix: pd.DataFrame) -> Dict:
        """
        상관관계 기반 헤지 전략 계산

        Args:
            target_symbol: 목표 종목
            portfolio: 포트폴리오 종목 리스트
            correlation_matrix: 상관관계 매트릭스

        Returns:
            헤지 추천 정보
        """
        hedge_recommendations = {
            'target': target_symbol,
            'hedge_candidates': [],
            'diversification_score': 0
        }

        if target_symbol not in correlation_matrix.columns:
            return hedge_recommendations

        # 음의 상관관계 종목 찾기
        target_corr = correlation_matrix[target_symbol]
        negative_corr = target_corr[target_corr < -0.3].sort_values()

        for symbol, corr in negative_corr.items():
            if symbol != target_symbol:
                hedge_recommendations['hedge_candidates'].append({
                    'symbol': symbol,
                    'correlation': corr,
                    'hedge_ratio': abs(corr)  # 헤지 비율
                })

        # 분산 점수 계산 (낮을수록 좋음)
        avg_correlation = correlation_matrix.loc[portfolio, portfolio].mean().mean()
        hedge_recommendations['diversification_score'] = 1 - abs(avg_correlation)

        return hedge_recommendations

    def _calculate_kelly_criterion(self, win_rate: float, win_loss_ratio: float) -> float:
        """켈리 공식 계산"""
        if win_loss_ratio <= 0:
            return 0

        p = win_rate  # 승률
        q = 1 - p     # 패률
        b = win_loss_ratio  # 배당률

        kelly = (p * b - q) / b
        return max(0, min(kelly, 0.25))  # 0~25% 제한

    def _calculate_portfolio_returns(self, positions: List[Dict],
                                    price_history: Dict[str, pd.DataFrame]) -> np.array:
        """포트폴리오 수익률 계산"""
        portfolio_value = []

        for date_idx in range(len(next(iter(price_history.values())))):
            daily_value = 0
            for position in positions:
                symbol = position['symbol']
                shares = position['shares']
                if symbol in price_history:
                    price = price_history[symbol].iloc[date_idx]['close']
                    daily_value += price * shares
            portfolio_value.append(daily_value)

        portfolio_value = np.array(portfolio_value)
        returns = np.diff(portfolio_value) / portfolio_value[:-1]
        return returns

    def _calculate_sharpe_ratio(self, returns: np.array, risk_free_rate: float = 0.02) -> float:
        """샤프 비율 계산"""
        excess_returns = returns - risk_free_rate / 252  # 일간 무위험 수익률
        if returns.std() == 0:
            return 0
        return np.sqrt(252) * excess_returns.mean() / returns.std()

    def _calculate_max_drawdown(self, returns: np.array) -> float:
        """최대 낙폭 계산"""
        cumulative = (1 + returns).cumprod()
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        return drawdown.min()

    def _calculate_portfolio_beta(self, portfolio_returns: np.array,
                                 market_data: Optional[pd.DataFrame]) -> float:
        """포트폴리오 베타 계산"""
        if market_data is None or len(market_data) == 0:
            return 1.0

        market_returns = market_data['close'].pct_change().dropna().values

        if len(market_returns) != len(portfolio_returns):
            return 1.0

        covariance = np.cov(portfolio_returns, market_returns)[0, 1]
        market_variance = np.var(market_returns)

        if market_variance == 0:
            return 1.0

        return covariance / market_variance

    def _calculate_correlation_matrix(self, positions: List[Dict],
                                     price_history: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """종목 간 상관관계 계산"""
        symbols = [p['symbol'] for p in positions]
        returns_dict = {}

        for symbol in symbols:
            if symbol in price_history:
                returns_dict[symbol] = price_history[symbol]['close'].pct_change().dropna()

        if not returns_dict:
            return pd.DataFrame()

        returns_df = pd.DataFrame(returns_dict)
        return returns_df.corr()

    def _calculate_concentration_risk(self, positions: List[Dict]) -> float:
        """HHI (Herfindahl-Hirschman Index) 기반 집중도 리스크"""
        total_value = sum(p['shares'] * p.get('current_price', p['entry_price'])
                         for p in positions)

        if total_value == 0:
            return 1.0

        hhi = 0
        for position in positions:
            position_value = position['shares'] * position.get('current_price', position['entry_price'])
            weight = position_value / total_value
            hhi += weight ** 2

        return hhi

    def _calculate_liquidity_score(self, positions: List[Dict],
                                  price_history: Dict[str, pd.DataFrame]) -> float:
        """유동성 점수 계산 (0~1, 높을수록 좋음)"""
        liquidity_scores = []

        for position in positions:
            symbol = position['symbol']
            if symbol in price_history and 'volume' in price_history[symbol].columns:
                avg_volume = price_history[symbol]['volume'].mean()
                position_size = position['shares']

                # 일평균 거래량 대비 포지션 크기
                if avg_volume > 0:
                    liquidity_ratio = position_size / avg_volume
                    # 일평균 거래량의 1% 이하면 유동성 좋음 (1.0)
                    score = max(0, 1 - liquidity_ratio * 100)
                    liquidity_scores.append(score)

        return np.mean(liquidity_scores) if liquidity_scores else 0.5

    def _determine_risk_level(self, var_95: float, sharpe: float, concentration: float) -> RiskLevel:
        """전체 리스크 수준 판단"""
        risk_score = 0

        # VaR 기준 (일간 -5% 이상 손실 가능성)
        if var_95 < -0.05:
            risk_score += 3
        elif var_95 < -0.03:
            risk_score += 2
        elif var_95 < -0.01:
            risk_score += 1

        # 샤프 비율 기준
        if sharpe < 0:
            risk_score += 3
        elif sharpe < 0.5:
            risk_score += 2
        elif sharpe < 1.0:
            risk_score += 1

        # 집중도 기준 (HHI)
        if concentration > 0.5:
            risk_score += 3
        elif concentration > 0.3:
            risk_score += 2
        elif concentration > 0.15:
            risk_score += 1

        # 리스크 레벨 결정
        if risk_score >= 7:
            return RiskLevel.EXTREME
        elif risk_score >= 5:
            return RiskLevel.HIGH
        elif risk_score >= 3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_current_portfolio_risk(self, positions: List[Dict]) -> float:
        """현재 포트폴리오의 리스크 비율"""
        total_risk = 0
        for position in positions:
            if 'stop_loss' in position and 'entry_price' in position:
                risk_per_share = abs(position['entry_price'] - position['stop_loss'])
                position_risk = risk_per_share * position['shares']
                total_risk += position_risk

        return total_risk / self.total_capital if self.total_capital > 0 else 0

    def _empty_risk_metrics(self) -> PortfolioRiskMetrics:
        """빈 위험 지표 반환"""
        return PortfolioRiskMetrics(
            위험가치_95=0,
            조건부_위험가치_95=0,
            위험조정수익률=0,
            최대낙폭=0,
            시장민감도=1.0,
            상관관계_매트릭스=pd.DataFrame(),
            집중도_위험=0,
            유동성_점수=0,
            전체_위험_수준=RiskLevel.LOW
        )
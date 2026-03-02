"""
몬테카를로 시뮬레이션: 부트스트랩 기반 성과 분포 추정
"""
import numpy as np
import pandas as pd
from typing import Dict, List
from .backtest import BacktestEngine
from ..models.schemas import RiskParams, MonteCarloResult


class MonteCarloSimulator:
    """몬테카를로 시뮬레이션"""

    def __init__(
        self,
        data: pd.DataFrame,
        entry_signals: pd.Series,
        exit_signals: pd.Series,
        risk_params: RiskParams,
        n_runs: int = 1000,
        transaction_cost_bps: int = 10,
        slippage_bps: int = 5,
        initial_capital: float = 100000
    ):
        self.data = data
        self.entry_signals = entry_signals
        self.exit_signals = exit_signals
        self.risk_params = risk_params
        self.n_runs = n_runs
        self.transaction_cost_bps = transaction_cost_bps
        self.slippage_bps = slippage_bps
        self.initial_capital = initial_capital

        self.results: List[Dict] = []

    def run(self) -> MonteCarloResult:
        """
        몬테카를로 시뮬레이션 실행

        Returns:
            MonteCarloResult with percentile distributions
        """
        cagr_distribution = []
        sharpe_distribution = []
        maxdd_distribution = []

        for i in range(self.n_runs):
            # 부트스트랩: 데이터 블록 리샘플링
            resampled_data = self._block_bootstrap(self.data)

            # 시그널도 동일하게 리샘플링
            resampled_entry = self.entry_signals.reindex(resampled_data.index, fill_value=False)
            resampled_exit = self.exit_signals.reindex(resampled_data.index, fill_value=False)

            # 백테스트 실행
            try:
                engine = BacktestEngine(
                    resampled_data,
                    resampled_entry,
                    resampled_exit,
                    self.risk_params,
                    self.transaction_cost_bps,
                    self.slippage_bps,
                    self.initial_capital
                )
                metrics, _, _ = engine.run()

                cagr_distribution.append(metrics.CAGR)
                sharpe_distribution.append(metrics.Sharpe)
                maxdd_distribution.append(metrics.MaxDD)

            except Exception as e:
                # 샘플링 실패 시 스킵
                continue

        # 분포 통계
        cagr_array = np.array(cagr_distribution)
        maxdd_array = np.array(maxdd_distribution)

        result = MonteCarloResult(
            runs=len(cagr_distribution),
            p5_cagr=float(np.percentile(cagr_array, 5)),
            p50_cagr=float(np.percentile(cagr_array, 50)),
            p95_cagr=float(np.percentile(cagr_array, 95)),
            maxdd_distribution={
                'p5': float(np.percentile(maxdd_array, 5)),
                'p50': float(np.percentile(maxdd_array, 50)),
                'p95': float(np.percentile(maxdd_array, 95))
            }
        )

        return result

    def _block_bootstrap(
        self,
        data: pd.DataFrame,
        expected_block_size: int = 20
    ) -> pd.DataFrame:
        """
        Stationary Bootstrap (기하분포 블록 크기)

        고정 블록 크기 대신 확률적 블록 경계를 사용하여
        시계열의 자기상관 구조를 더 잘 보존합니다.

        Args:
            data: 원본 데이터
            expected_block_size: 기대 블록 크기 (기하분포 평균)

        Returns:
            리샘플링된 데이터
        """
        n = len(data)
        if n < 2:
            return data.copy()

        p = 1.0 / expected_block_size  # 새 블록 시작 확률

        indices = []
        i = np.random.randint(0, n)
        for _ in range(n):
            indices.append(i)
            if np.random.random() < p:
                i = np.random.randint(0, n)  # 새 랜덤 위치
            else:
                i = (i + 1) % n  # 현재 블록 계속

        resampled_data = data.iloc[indices].copy()
        resampled_data.index = pd.date_range(
            start=data.index[0],
            periods=len(resampled_data),
            freq='B'  # 'B'=영업일 (주말 제외, 더 현실적)
        )

        return resampled_data

    def get_distribution_summary(self) -> pd.DataFrame:
        """분포 요약 통계"""
        if not self.results:
            return pd.DataFrame()

        summary = pd.DataFrame(self.results)
        return summary.describe()


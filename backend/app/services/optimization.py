"""
전략 파라미터 최적화 및 전진 분석(Walk-Forward Analysis) 서비스.
"""
from typing import Any, Dict, List, Optional, Tuple
import itertools
import pandas as pd
import numpy as np
from concurrent.futures import ProcessPoolExecutor

from ..core.logging_config import logger
from ..models.schemas import RiskParams
from .backtest import BacktestEngine

class StrategyOptimizer:
    """
    전략 파라미터 최적화 엔진.
    그리드 서치 및 전진 분석(Walk-Forward)을 지원합니다.
    """
    
    def __init__(self, data: pd.DataFrame, base_strategy_func: callable):
        self.data = data
        self.base_strategy_func = base_strategy_func

    def grid_search(
        self,
        param_grid: Dict[str, List[Any]],
        risk_params: RiskParams,
        target_metric: str = "Sharpe"
    ) -> Tuple[Dict[str, Any], float]:
        """
        주어진 파라미터 그리드에서 최적의 조합을 찾습니다.
        """
        keys = list(param_grid.keys())
        values = list(param_grid.values())
        combinations = list(itertools.product(*values))
        
        best_score = -float('inf')
        best_params = {}
        
        logger.info(f"그리드 서치 시작: 총 {len(combinations)}개 조합")
        
        for combo in combinations:
            params = dict(zip(keys, combo))
            
            # 전략 실행 (시그널 생성)
            entry_signals, exit_signals = self.base_strategy_func(self.data, **params)
            
            # 백테스트 실행
            engine = BacktestEngine(self.data, entry_signals, exit_signals, risk_params)
            metrics, _, _ = engine.run()
            
            score = getattr(metrics, target_metric, 0.0)
            
            if score > best_score:
                best_score = score
                best_params = params
                
        logger.info(f"최적 파라미터 발견: {best_params} (Score: {best_score:.2f})")
        return best_params, best_score

    def walk_forward_analysis(
        self,
        param_grid: Dict[str, List[Any]],
        risk_params: RiskParams,
        train_window_days: int = 365,
        test_window_days: int = 90,
        target_metric: str = "Sharpe"
    ) -> Dict[str, Any]:
        """
        전진 분석(Walk-Forward Analysis)을 수행하여 전략의 강건성을 검증합니다.
        """
        dates = self.data.index
        start_idx = 0
        
        results = []
        
        while True:
            train_end_idx = start_idx + train_window_days
            test_end_idx = train_end_idx + test_window_days
            
            if test_end_idx > len(dates):
                break
                
            train_data = self.data.iloc[start_idx:train_end_idx]
            test_data = self.data.iloc[train_end_idx:test_end_idx]
            
            # 1. In-Sample 최적화
            optimizer = StrategyOptimizer(train_data, self.base_strategy_func)
            best_params, train_score = optimizer.grid_search(param_grid, risk_params, target_metric)
            
            # 2. Out-of-Sample 테스트
            entry_signals, exit_signals = self.base_strategy_func(test_data, **best_params)
            engine = BacktestEngine(test_data, entry_signals, exit_signals, risk_params)
            metrics, _, _ = engine.run()
            test_score = getattr(metrics, target_metric, 0.0)
            
            results.append({
                "period_start": test_data.index[0],
                "period_end": test_data.index[-1],
                "best_params": best_params,
                "train_score": train_score,
                "test_score": test_score,
                "metrics": metrics
            })
            
            # 윈도우 이동
            start_idx += test_window_days
            
        return {
            "walk_forward_results": results,
            "average_test_score": np.mean([r["test_score"] for r in results]) if results else 0.0
        }

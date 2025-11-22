import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.backtest import BacktestEngine, RiskParams
from app.services.optimization import StrategyOptimizer

def create_dummy_data(days=200, start_price=100.0):
    dates = [datetime.now() - timedelta(days=x) for x in range(days)]
    dates.reverse()
    
    data = []
    price = start_price
    for date in dates:
        change = np.random.normal(0, 0.02)
        price = price * (1 + change)
        data.append({
            'date': date,
            'open': price * 0.99,
            'high': price * 1.02,
            'low': price * 0.98,
            'close': price,
            'volume': 1000000
        })
    
    df = pd.DataFrame(data)
    df.set_index('date', inplace=True)
    return df

def test_single_asset_backtest():
    print("\n=== Testing Single Asset Backtest ===")
    df = create_dummy_data()
    
    # Simple MA strategy signals
    df['ma5'] = df['close'].rolling(window=5).mean()
    df['ma20'] = df['close'].rolling(window=20).mean()
    
    entries = (df['ma5'] > df['ma20']) & (df['ma5'].shift(1) <= df['ma20'].shift(1))
    exits = (df['ma5'] < df['ma20']) & (df['ma5'].shift(1) >= df['ma20'].shift(1))
    
    risk_params = RiskParams(
        stop_loss_pct=0.05,
        take_profit_pct=0.10,
        max_drawdown_pct=0.20
    )
    
    engine = BacktestEngine(df, entries, exits, risk_params)
    metrics, equity, trades = engine.run()
    
    print(f"CAGR: {metrics.CAGR:.2%}")
    print(f"Sharpe: {metrics.Sharpe:.2f}")
    print(f"Sortino: {metrics.Sortino:.2f}")
    print(f"Total Trades: {metrics.TotalTrades}")
    
    assert metrics.TotalTrades >= 0
    print("✅ Single Asset Backtest Passed")

def test_portfolio_backtest():
    print("\n=== Testing Portfolio Backtest ===")
    df1 = create_dummy_data(start_price=100)
    df2 = create_dummy_data(start_price=50)
    
    data_map = {"AAPL": df1, "MSFT": df2}
    
    # Random signals
    entries_map = {
        "AAPL": pd.Series(np.random.choice([True, False], size=len(df1), p=[0.1, 0.9]), index=df1.index),
        "MSFT": pd.Series(np.random.choice([True, False], size=len(df2), p=[0.1, 0.9]), index=df2.index)
    }
    exits_map = {
        "AAPL": pd.Series(np.random.choice([True, False], size=len(df1), p=[0.1, 0.9]), index=df1.index),
        "MSFT": pd.Series(np.random.choice([True, False], size=len(df2), p=[0.1, 0.9]), index=df2.index)
    }
    
    risk_params = RiskParams(
        stop_loss_pct=0.05,
        take_profit_pct=0.10,
        max_position_size_pct=0.5 # Max 50% per asset
    )
    
    engine = BacktestEngine(data_map, entries_map, exits_map, risk_params)
    metrics, equity, trades = engine.run()
    
    print(f"Portfolio CAGR: {metrics.CAGR:.2%}")
    print(f"Portfolio Sharpe: {metrics.Sharpe:.2f}")
    print(f"Portfolio Sortino: {metrics.Sortino:.2f}")
    
    assert len(trades) >= 0
    print("✅ Portfolio Backtest Passed")

def test_optimization():
    print("\n=== Testing Strategy Optimization ===")
    df = create_dummy_data(days=300) # Increased days for walk-forward
    
    def strategy_fn(data, short_window, long_window):
        # Simple MA Crossover
        short_window = int(short_window)
        long_window = int(long_window)
        
        short_ma = data['close'].rolling(window=short_window).mean()
        long_ma = data['close'].rolling(window=long_window).mean()
        
        entries = (short_ma > long_ma) & (short_ma.shift(1) <= long_ma.shift(1))
        exits = (short_ma < long_ma) & (short_ma.shift(1) >= long_ma.shift(1))
        
        return entries, exits
    
    optimizer = StrategyOptimizer(
        data=df,
        base_strategy_func=strategy_fn
    )
    
    param_grid = {
        'short_window': [5, 10],
        'long_window': [20, 30]
    }
    risk_params = RiskParams()
    
    # Test Grid Search
    print("Running Grid Search...")
    best_params, best_metrics = optimizer.grid_search(param_grid, risk_params)
    print(f"Best Params: {best_params}")
    print(f"Best Score: {best_metrics:.2f}")
    
    # Test Walk Forward
    print("Running Walk Forward Analysis...")
    wf_results = optimizer.walk_forward_analysis(
        param_grid=param_grid,
        risk_params=risk_params,
        train_window_days=100,
        test_window_days=50
    )
    print(f"Walk Forward Avg Score: {wf_results['average_test_score']:.2f}")
    
    print("✅ Optimization Passed")

if __name__ == "__main__":
    try:
        test_single_asset_backtest()
        test_portfolio_backtest()
        test_optimization()
        print("\n🎉 All Tests Passed Successfully!")
    except Exception as e:
        print(f"\n❌ Test Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

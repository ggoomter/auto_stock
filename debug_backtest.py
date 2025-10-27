"""
Debug script to identify the 'initial_capital' undefined error
"""
import sys
import traceback
sys.path.insert(0, 'G:\\ai_coding\\auto_stock\\backend')

try:
    # Import required modules
    from app.services.indicators import load_sample_data, IndicatorCalculator
    from app.services.master_strategies import get_strategy
    from app.models.schemas import RiskParams

    # Load data
    print("1. Loading data for 005930...")
    data = load_sample_data("005930", "2024-01-01", "2025-10-04")
    print(f"   Loaded {len(data)} rows")

    # Calculate indicators
    print("2. Calculating indicators...")
    data = IndicatorCalculator.calculate_all(data)
    print(f"   Calculated, {len(data)} rows remain")

    # Get strategy
    print("3. Getting Livermore strategy...")
    strategy = get_strategy("livermore")
    print(f"   Strategy: {strategy.__class__.__name__}")

    # Generate signals
    print("4. Generating signals...")
    entry_signals, exit_signals = strategy.generate_signals("005930", data)
    print(f"   Entry signals: {entry_signals.sum()}, Exit signals: {exit_signals.sum()}")

    # Create risk params
    print("5. Getting risk params from strategy...")
    risk_params = strategy.get_risk_params()

    # Import BacktestEngine
    print("6. Importing BacktestEngine...")
    from app.services.backtest import BacktestEngine

    # Create backtest engine with custom initial capital
    print("7. Creating BacktestEngine with 1M won converted to USD...")
    initial_capital_usd = 710.0  # Example conversion
    engine = BacktestEngine(
        data=data,
        entry_signals=entry_signals,
        exit_signals=exit_signals,
        risk_params=risk_params,
        transaction_cost_bps=10,
        slippage_bps=5,
        initial_capital=initial_capital_usd
    )
    print(f"   Engine created with initial_capital={engine.initial_capital}")

    # Run backtest
    print("8. Running backtest...")
    metrics, equity_curve = engine.run()
    print(f"   Backtest complete! Trades: {len(engine.trades)}")
    print(f"   Metrics: CAGR={metrics.CAGR}, Sharpe={metrics.Sharpe}")

    print("\n[OK] All steps completed successfully!")

except Exception as e:
    print(f"\n[ERROR] at step: {e}")
    print("\nFull traceback:")
    traceback.print_exc()

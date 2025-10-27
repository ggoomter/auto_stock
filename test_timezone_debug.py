import sys
sys.path.insert(0, 'G:/ai_coding/auto_stock/backend')

from app.services.indicators import load_sample_data, IndicatorCalculator
from app.services.master_strategies import get_strategy

symbol = "AAPL"
start_date = "2020-01-01"
end_date = "2023-12-31"

print(f"Loading data for {symbol}...")
df = load_sample_data(symbol, start_date, end_date)
print(f"Data loaded: {len(df)} rows")
print(f"Columns: {df.columns.tolist()}")
print(f"Index type: {type(df.index[0])}")
print(f"Index has tz: {hasattr(df.index[0], 'tz')}")
if hasattr(df.index[0], 'tz'):
    print(f"Index tz: {df.index[0].tz}")

print("\nCalculating indicators...")
df = IndicatorCalculator.calculate_all(df)
print(f"Indicators calculated: {len(df)} rows")

print("\nGetting Buffett strategy...")
strategy = get_strategy("buffett")
print(f"Strategy: {strategy.name}")

print("\nGenerating signals...")
try:
    entry_signals, exit_signals = strategy.generate_signals(symbol, df)
    print(f"SUCCESS! Entry signals: {entry_signals.sum()}, Exit signals: {exit_signals.sum()}")

    print("\nRunning backtest...")
    from app.services.backtest import BacktestEngine
    risk_params = strategy.get_risk_params()
    engine = BacktestEngine(
        data=df,
        entry_signals=entry_signals,
        exit_signals=exit_signals,
        risk_params=risk_params,
        initial_capital=100000
    )
    metrics, equity_curve = engine.run()
    print(f"Backtest SUCCESS!")
    print(f"CAGR: {metrics.CAGR}, Sharpe: {metrics.Sharpe}, MaxDD: {metrics.MaxDD}")

except Exception as e:
    import traceback
    print(f"ERROR: {e}")
    print(f"Traceback:\n{traceback.format_exc()}")

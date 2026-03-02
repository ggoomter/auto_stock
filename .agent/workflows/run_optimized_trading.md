---
description: How to run the optimized auto trading system
---
# Optimized Auto Trading Workflow

This workflow describes how to run the auto trading system with the newly optimized data fetching and profitable strategies.

## Prerequisites
- Python 3.8+
- Dependencies installed (`pip install -r requirements.txt`)
- `pykrx` and `yfinance` installed

## Steps

1. **Verify Configuration**
   - Ensure `AutoTradingConfig` in `auto_trading_engine.py` has the desired strategies enabled (default: `buffett`, `modern_livermore`, `super_momentum`).
   - Check `trading_hours` if running in live mode.

2. **Run Auto Trading**
   You can run the auto trading engine using a script like this:

   ```python
   import asyncio
   from app.services.auto_trading_engine import AutoTradingEngine, AutoTradingConfig, TradingMode

   async def main():
       # Configure for Paper Trading (Simulation)
       config = AutoTradingConfig(
           mode=TradingMode.PAPER,
           total_capital=10_000_000,
           use_stock_screener=True,  # Enable auto stock discovery
           screener_type="momentum"  # Use momentum screener for high profit potential
       )
       
       engine = AutoTradingEngine(config)
       
       # Start trading (optionally provide initial watchlist)
       await engine.start(["005930.KS", "000660.KS"])

   if __name__ == "__main__":
       asyncio.run(main())
   ```

3. **Monitor Performance**
   - The engine logs activities to the console and log files.
   - Watch for "Signal Generated" and "Order Executed" logs.
   - Check `risk_metrics` in the logs to ensure risk is managed.

## Key Optimizations
- **Batch Data Fetching**: The system now fetches fundamental data for all stocks in batches, reducing API calls and speeding up screening.
- **Super Momentum Strategy**: A new aggressive strategy targeting high-growth stocks with strong trends.
- **Modern Livermore Strategy**: Improved trend following logic based on price action.

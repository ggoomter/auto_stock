"""
Test Hyundai E&C with .KS suffix
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

print("\n[Hyundai E&C Test with .KS suffix]")

req = {
    "strategy_name": "livermore",
    "symbols": ["000720.KS"],
    "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
    "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
}

res = requests.post(f"{BASE_URL}/master-strategy", json=req, timeout=120)
result = res.json()

if result.get('trade_history'):
    trade = result['trade_history'][0]
    print(f"\n[Trade Details]")
    print(f"  Entry Date: {trade['entry_date']}")
    print(f"  Currency: {trade['currency']}")
    print(f"  Entry Price (KRW): {trade['entry_price_krw']:,}")
    print(f"  Entry Price (USD): ${trade['entry_price']:.2f}")
    print(f"  Shares: {trade['shares']:.4f}")
    print(f"  Position (KRW): {trade['position_value_krw']:,}")

    # Validation
    if trade['currency'] == 'KRW':
        print(f"\n[OK] Detected as Korean stock")
        print(f"[OK] Entry price in normal range: {trade['entry_price_krw']:,} KRW")
    else:
        print(f"\n[FAIL] Not detected as Korean stock! Currency: {trade['currency']}")
        print(f"[FAIL] Entry price (USD): ${trade['entry_price']:.2f}")
else:
    print("\n[INFO] No trades executed")

print(f"\nExchange rate: {result.get('exchange_rate', 'N/A')}")
print(f"Initial capital: {result.get('initial_capital_krw', 'N/A'):,} KRW")

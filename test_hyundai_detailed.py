"""
Hyundai E&C detailed error test
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

print("\n[Hyundai E&C Detailed Error Test]\n")

req = {
    "strategy_name": "livermore",
    "symbols": ["000720.KS"],
    "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
    "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
}

try:
    res = requests.post(f"{BASE_URL}/master-strategy", json=req, timeout=120)

    print(f"Status code: {res.status_code}\n")

    if res.status_code == 500:
        print("[ERROR] Server returned 500")
        print("\nResponse text:")
        print(res.text)
    else:
        result = res.json()

        if result.get('trade_history'):
            trade = result['trade_history'][0]
            print(f"[Trade 1]")
            print(f"  Currency: {trade['currency']}")
            print(f"  Entry price (KRW): {trade.get('entry_price_krw', 'N/A'):,}")
            print(f"  Entry price (USD): ${trade['entry_price']:.2f}")
            print(f"  Shares: {trade['shares']:.4f}")
        else:
            print("[INFO] No trades")

except Exception as e:
    print(f"[EXCEPTION] {type(e).__name__}: {e}")

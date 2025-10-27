"""
Currency handling validation test
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

print("\n[CURRENCY VALIDATION TEST]\n")

# Test 1: Samsung Electronics (Korean stock)
print("=" * 80)
print("[TEST 1] Korean Stock - Samsung Electronics")
print("=" * 80)

req = {
    "strategy_name": "livermore",
    "symbols": ["005930"],
    "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
    "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
}

res = requests.post(f"{BASE_URL}/master-strategy", json=req, timeout=120)
result = res.json()

if result['trade_history']:
    trade = result['trade_history'][0]
    print(f"[OK] Currency: {trade['currency']}")
    print(f"[OK] Entry price: {trade['entry_price_krw']:,} KRW (${trade['entry_price']:.2f})")
    print(f"[OK] Shares: {trade['shares']:.4f}")
    print(f"[OK] Position: {trade['position_value_krw']:,} KRW")

    # Validation
    assert trade['currency'] == 'KRW', "Currency must be KRW"
    assert 50000 <= trade['entry_price_krw'] <= 150000, "Samsung price range error"
    print("\n[PASS] Test 1 passed\n")

# Test 2: LG Electronics (previous bug check)
print("=" * 80)
print("[TEST 2] LG Electronics - Previous Bug Check")
print("=" * 80)

req['symbols'] = ["066570"]
res = requests.post(f"{BASE_URL}/master-strategy", json=req, timeout=120)
result = res.json()

if result['trade_history']:
    trade = result['trade_history'][0]
    print(f"[OK] Currency: {trade['currency']}")
    print(f"[OK] Entry price: {trade['entry_price_krw']:,} KRW (${trade['entry_price']:.2f})")

    # Previous bug: showed $95989 instead of normal range
    assert 60000 <= trade['entry_price_krw'] <= 110000, "LG price range error - BUG DETECTED!"
    assert trade['entry_price'] < 100, "USD conversion error - BUG DETECTED!"
    print("\n[PASS] Test 2 passed - No bug recurrence\n")

print("=" * 80)
print("[OK] All tests passed! Currency handling is correct.")
print("=" * 80)

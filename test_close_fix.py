import requests
import json

url = "http://localhost:8000/api/v1/master-strategy"
payload = {
    "strategy_name": "buffett",
    "symbols": ["AAPL"],
    "date_range": {
        "start": "2020-01-01",
        "end": "2023-12-31"
    }
}

try:
    response = requests.post(url, json=payload, timeout=30)

    if response.status_code == 200:
        result = response.json()
        print("SUCCESS - Close error is FIXED!")
        print(f"CAGR: {result['metrics']['CAGR']}")
        print(f"Sharpe: {result['metrics']['Sharpe']}")
        print(f"MaxDD: {result['metrics']['MaxDD']}")
    else:
        print(f"ERROR - Status: {response.status_code}")
        print(f"Response: {response.text}")

except Exception as e:
    print(f"Request failed: {e}")

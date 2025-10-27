import sys
sys.path.insert(0, 'G:/ai_coding/auto_stock/backend')

from app.services.data_cache import get_cache

# 캐시 초기화
cache = get_cache()
cache.clear()
print("Cache cleared!")

# 테스트
import requests
url = "http://localhost:8000/api/v1/master-strategy"
payload = {
    "strategy_name": "buffett",
    "symbols": ["AAPL"],
    "date_range": {
        "start": "2020-01-01",
        "end": "2023-12-31"
    }
}

response = requests.post(url, json=payload, timeout=30)

if response.status_code == 200:
    result = response.json()
    print("SUCCESS - Timezone error is FIXED!")
    print(f"CAGR: {result['backtest']['metrics']['CAGR']}")
    print(f"Sharpe: {result['backtest']['metrics']['Sharpe']}")
    print(f"MaxDD: {result['backtest']['metrics']['MaxDD']}")
else:
    print(f"ERROR - Status: {response.status_code}")
    print(f"Response: {response.text}")

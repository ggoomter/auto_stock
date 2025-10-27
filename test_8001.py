"""
포트 8001로 한국 주식 테스트
"""

import requests
import json

# API 엔드포인트 - 포트 8001
url = "http://localhost:8001/api/v1/master-strategy"

# 요청 데이터
request_data = {
    "strategy_name": "buffett",
    "symbols": ["000720.KS"],  # 현대건설
    "date_range": {
        "start": "2024-01-01",
        "end": "2024-12-31"
    },
    "simulate": {
        "bootstrap_runs": 1000,
        "transaction_cost_bps": 10,
        "slippage_bps": 5
    },
    "output_detail": "full"
}

print("[포트 8001 테스트]")
print(f"URL: {url}")
print(f"Request: {json.dumps(request_data, indent=2)}")
print("-" * 50)

try:
    # API 호출
    response = requests.post(url, json=request_data)

    print(f"Status code: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print("[SUCCESS] Analysis completed!")
        print(f"Symbol: {result.get('symbol')}")
        print(f"Final capital: ₩{result.get('final_capital_krw', 0):,.0f}")
        print(f"Total return: {result.get('total_return', 0):.2%}")
    else:
        print(f"[ERROR] Server returned {response.status_code}")
        print(f"Response text: {response.text}")

except requests.exceptions.ConnectionError:
    print("[ERROR] Cannot connect to server at port 8001")
except Exception as e:
    print(f"[ERROR] Unexpected error: {e}")
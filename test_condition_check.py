"""조건 체크 기능 테스트"""
import requests
import json
import sys
import io

# UTF-8 출력 설정
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

url = "http://localhost:8000/api/v1/master-strategy"

payload = {
    "strategy_name": "buffett",
    "symbols": ["AAPL"],
    "date_range": {
        "start": "2023-01-01",
        "end": "2024-01-01"
    }
}

print("=== 버핏 전략 조건 체크 테스트 ===")
print(f"요청: {json.dumps(payload, indent=2, ensure_ascii=False)}\n")

try:
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        result = response.json()

        # 조건 체크 확인
        if "condition_checks" in result and result["condition_checks"]:
            print("✅ condition_checks 존재!")
            print(f"조건 개수: {len(result['condition_checks'])}\n")

            for i, check in enumerate(result["condition_checks"], 1):
                status = "✓ 통과" if check["passed"] else "✗ 실패"
                print(f"{i}. {check['condition_name']} ({check['condition_name_en']})")
                print(f"   필요값: {check['required_value']}")
                print(f"   실제값: {check['actual_value']}")
                print(f"   결과: {status}\n")
        else:
            print("❌ condition_checks 없음!")
            print("응답 키:", list(result.keys()))

    else:
        print(f"❌ 에러 {response.status_code}: {response.text}")

except Exception as e:
    print(f"❌ 요청 실패: {e}")

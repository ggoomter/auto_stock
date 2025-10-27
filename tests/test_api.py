#!/usr/bin/env python3
"""
API 테스트 스크립트
백엔드 서버가 실행 중일 때 사용하세요: uvicorn app.main:app --reload
"""
import requests
import json
from datetime import date

API_URL = "http://localhost:8000/api/v1"


def test_health():
    """헬스 체크 테스트"""
    print("🔍 Testing health endpoint...")
    response = requests.get(f"{API_URL}/health")
    print(f"   Status: {response.status_code}")
    print(f"   Response: {response.json()}")
    print()


def test_analyze():
    """분석 엔드포인트 테스트"""
    print("🔍 Testing analyze endpoint...")

    request_data = {
        "symbols": ["AAPL"],
        "date_range": {
            "start": "2023-01-01",
            "end": "2024-12-31"
        },
        "horizon": {
            "lookahead_days": 5,
            "rebalance_days": 1
        },
        "strategy": {
            "entry": "MACD.cross_up == true AND RSI < 30",
            "exit": "MACD.cross_down == true OR RSI > 70",
            "risk": {
                "stop_pct": 0.07,
                "take_pct": 0.15,
                "position_sizing": "vol_target_10"
            }
        },
        "simulate": {
            "bootstrap_runs": 100,  # 빠른 테스트를 위해 100회로 설정
            "transaction_cost_bps": 10,
            "slippage_bps": 5
        },
        "features": ["MACD", "RSI", "DMI", "BBANDS", "OBV"],
        "events": ["ELECTION", "FOMC"],
        "explain": True,
        "output_detail": "brief"
    }

    print(f"   Request: {json.dumps(request_data, indent=2)}")
    print()

    response = requests.post(
        f"{API_URL}/analyze",
        json=request_data,
        headers={"Content-Type": "application/json"}
    )

    print(f"   Status: {response.status_code}")

    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Success!")
        print()
        print("   📊 Results Summary:")
        print(f"      Summary: {result['summary']}")
        print(f"      Signals: {result['sample_info']['n_signals']}")
        print()
        print("   🎯 Prediction:")
        print(f"      Up Prob: {result['prediction']['up_prob']:.2%}")
        print(f"      Down Prob: {result['prediction']['down_prob']:.2%}")
        print(f"      Expected Return: {result['prediction']['expected_return_pct']:.2f}%")
        print()
        print("   📈 Backtest Metrics:")
        print(f"      CAGR: {result['backtest']['metrics']['CAGR']:.2%}")
        print(f"      Sharpe: {result['backtest']['metrics']['Sharpe']:.2f}")
        print(f"      Max DD: {result['backtest']['metrics']['MaxDD']:.2%}")
        print(f"      Hit Ratio: {result['backtest']['metrics']['HitRatio']:.2%}")
        print()
        print("   🎲 Monte Carlo:")
        print(f"      Runs: {result['monte_carlo']['runs']}")
        print(f"      P5 CAGR: {result['monte_carlo']['p5_cagr']:.2%}")
        print(f"      P50 CAGR: {result['monte_carlo']['p50_cagr']:.2%}")
        print(f"      P95 CAGR: {result['monte_carlo']['p95_cagr']:.2%}")
        print()
        print(f"   ⚠️ Limitations: {', '.join(result['limitations'])}")
        print()
        print(f"   Full response saved to 'test_response.json'")

        # 전체 응답 저장
        with open('test_response.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

    else:
        print(f"   ❌ Error!")
        print(f"   Response: {response.text}")

    print()


def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("  API Test Script")
    print("=" * 60)
    print()

    try:
        # 헬스 체크
        test_health()

        # 분석 테스트
        test_analyze()

        print("✅ All tests completed!")

    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to backend server")
        print("   Please start the backend first:")
        print("   uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    main()

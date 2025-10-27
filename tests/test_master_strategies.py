"""
투자 대가 전략 테스트 스크립트
각 전략을 과거 데이터로 백테스트
"""
import httpx
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_list_strategies():
    """사용 가능한 전략 목록 조회"""
    print("=" * 80)
    print("📋 사용 가능한 투자 대가 전략 목록")
    print("=" * 80)

    response = httpx.get(f"{BASE_URL}/master-strategies")
    if response.status_code == 200:
        data = response.json()
        for strategy in data["strategies"]:
            print(f"\n🎯 {strategy['name']}")
            print(f"   설명: {strategy['description']}")
            info = strategy['info']
            print(f"   보유 기간: {info['holding_period']}")
            print(f"   리스크: {info['risk_profile']}")
            print(f"   핵심 원칙:")
            for principle in info['key_principles']:
                print(f"      - {principle}")
    else:
        print(f"❌ 실패: {response.status_code}")


def test_strategy(strategy_name: str, symbol: str = "AAPL"):
    """특정 전략 백테스트"""
    print("\n" + "=" * 80)
    print(f"🧪 {strategy_name.upper()} 전략 백테스트 - {symbol}")
    print("=" * 80)

    request_data = {
        "strategy_name": strategy_name,
        "symbols": [symbol],
        "date_range": {
            "start": "2024-01-01",  # 최근 1년만 (펀더멘털 데이터 제약)
            "end": "2024-12-31"
        },
        "simulate": {
            "bootstrap_runs": 1000,
            "transaction_cost_bps": 10,
            "slippage_bps": 5
        },
        "output_detail": "full"
    }

    response = httpx.post(
        f"{BASE_URL}/master-strategy",
        json=request_data,
        timeout=60.0
    )

    if response.status_code == 200:
        data = response.json()

        # 전략 정보
        info = data['strategy_info']
        print(f"\n📖 전략: {info['name']}")
        print(f"   {info['description']}")

        # 백테스트 결과
        metrics = data['backtest']['metrics']
        print(f"\n📊 백테스트 결과:")
        print(f"   CAGR: {metrics['CAGR']:.2%}")
        print(f"   Sharpe Ratio: {metrics['Sharpe']:.2f}")
        print(f"   Max Drawdown: {metrics['MaxDD']:.2%}")
        print(f"   Hit Ratio: {metrics['HitRatio']:.2%}")
        if metrics.get('AvgWin'):
            print(f"   평균 수익: {metrics['AvgWin']:.2%}")
        if metrics.get('AvgLoss'):
            print(f"   평균 손실: {metrics['AvgLoss']:.2%}")

        # 펀더멘털 분석 (있는 경우)
        if data.get('fundamental_screen'):
            print(f"\n💰 펀더멘털 분석:")
            fund = data['fundamental_screen']
            if 'error' in fund:
                print(f"   ⚠️ 데이터 없음: {fund['error']}")
            else:
                if 'metrics' in fund:
                    print(f"   재무 지표:")
                    for key, value in fund['metrics'].items():
                        if value is not None:
                            print(f"      {key}: {value}")
                if 'criteria' in fund:
                    criteria = fund['criteria']
                    print(f"   투자 기준 통과율: {criteria['pass_rate']:.1%} ({criteria['passed_count']}/{criteria['total_count']})")

        # 시그널 예시
        if data.get('signal_examples'):
            print(f"\n🔔 매수 시그널 예시:")
            for example in data['signal_examples'][:3]:
                print(f"   {example['date']}: {example['symbol']}")

    else:
        print(f"❌ 실패: {response.status_code}")
        print(response.text)


def run_all_tests():
    """모든 전략 테스트"""
    print("\n🚀 투자 대가 전략 백테스트 시작\n")

    # 전략 목록 조회
    test_list_strategies()

    # 각 전략 테스트
    strategies = ["buffett", "lynch", "graham", "dalio", "livermore", "oneil"]

    print("\n" + "=" * 80)
    print("📈 AAPL 종목으로 전략별 백테스트 실행")
    print("=" * 80)

    results = []
    for strategy in strategies:
        try:
            test_strategy(strategy, "AAPL")
            results.append((strategy, "✅ 성공"))
        except Exception as e:
            print(f"❌ {strategy} 실패: {e}")
            results.append((strategy, f"❌ 실패: {str(e)[:50]}"))

    # 요약
    print("\n" + "=" * 80)
    print("📋 테스트 결과 요약")
    print("=" * 80)
    for strategy, status in results:
        print(f"{strategy:15s}: {status}")


if __name__ == "__main__":
    try:
        # 서버 헬스 체크
        response = httpx.get(f"{BASE_URL}/health", timeout=5.0)
        if response.status_code == 200:
            print("✅ 서버 연결 성공")
            run_all_tests()
        else:
            print(f"❌ 서버 응답 오류: {response.status_code}")
    except httpx.ConnectError:
        print("❌ 서버에 연결할 수 없습니다.")
        print("   백엔드 서버를 먼저 실행하세요: cd backend && uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

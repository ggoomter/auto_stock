"""
자동매매 API 테스트
"""
import requests
import time
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"


def test_trading_start():
    """자동매매 시작 테스트"""
    print("\n=== 자동매매 시작 테스트 ===")

    payload = {
        "mode": "paper",  # 모의 거래
        "total_capital": 10000000,
        "max_positions": 5,
        "max_position_size": 0.2,
        "max_risk_per_trade": 0.02,
        "max_daily_loss": 0.05,
        "enabled_strategies": ["buffett", "lynch"],
        "trading_symbols": ["AAPL", "TSLA", "005930.KS"],
        "use_trailing_stop": True,
        "trailing_stop_percent": 0.05,
        "order_type": "market"
    }

    try:
        response = requests.post(f"{BASE_URL}/trading/start", json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 자동매매 시작 성공")
            print(f"   - 모드: {data.get('mode')}")
            print(f"   - 초기 자본: {data.get('config', {}).get('total_capital'):,.0f} KRW")
            print(f"   - 활성화 전략: {data.get('config', {}).get('enabled_strategies')}")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_trading_status():
    """자동매매 상태 조회 테스트"""
    print("\n=== 자동매매 상태 조회 테스트 ===")

    try:
        response = requests.get(f"{BASE_URL}/trading/status", timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 상태 조회 성공")
            print(f"   - 실행 중: {data.get('is_running')}")
            print(f"   - 모드: {data.get('mode')}")
            print(f"   - 활성 포지션: {data.get('active_positions')}개")
            print(f"   - 일일 손익: {data.get('daily_pnl', 0):,.0f} KRW ({data.get('daily_pnl_pct', 0):.2f}%)")
            print(f"   - 리스크 레벨: {data.get('risk_level')}")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_portfolio_status():
    """포트폴리오 상태 조회 테스트"""
    print("\n=== 포트폴리오 상태 조회 테스트 ===")

    try:
        response = requests.get(f"{BASE_URL}/portfolio/status", timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 포트폴리오 조회 성공")
            print(f"   - 총 자산: {data.get('total_value', 0):,.0f} KRW")
            print(f"   - 현금: {data.get('cash', 0):,.0f} KRW")
            print(f"   - 포지션 가치: {data.get('positions_value', 0):,.0f} KRW")
            print(f"   - 총 손익: {data.get('total_pnl', 0):,.0f} KRW ({data.get('total_pnl_pct', 0):.2f}%)")
            print(f"   - 포지션 수: {len(data.get('positions', []))}개")

            # 포지션 상세
            for pos in data.get('positions', []):
                print(f"     * {pos['symbol']}: {pos['quantity']}주 @ {pos['entry_price']:,.0f} KRW")

            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_trading_stop():
    """자동매매 중지 테스트"""
    print("\n=== 자동매매 중지 테스트 ===")

    payload = {
        "close_all_positions": False,  # 포지션 유지
        "reason": "test_stop"
    }

    try:
        response = requests.post(f"{BASE_URL}/trading/stop", json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 자동매매 중지 성공")
            print(f"   - 상태: {data.get('status')}")
            print(f"   - 포지션 청산: {data.get('positions_closed')}")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_emergency_stop():
    """긴급 정지 테스트"""
    print("\n=== 긴급 정지 테스트 ===")

    payload = {
        "reason": "test_emergency"
    }

    try:
        response = requests.post(f"{BASE_URL}/trading/emergency-stop", json=payload, timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 긴급 정지 성공")
            print(f"   - 상태: {data.get('status')}")
            print(f"   - 청산 포지션: {data.get('closed_positions')}개")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def test_trading_health():
    """시스템 헬스 체크 테스트"""
    print("\n=== 시스템 헬스 체크 테스트 ===")

    try:
        response = requests.get(f"{BASE_URL}/trading/health", timeout=5)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"✅ 헬스 체크 성공")
            print(f"   - 전체 상태: {data.get('overall_status')}")
            print(f"   - CPU: {data.get('system', {}).get('cpu_percent', 0):.1f}%")
            print(f"   - 메모리: {data.get('system', {}).get('memory_percent', 0):.1f}%")
            print(f"   - 자동매매 상태: {data.get('trading', {}).get('engine_status')}")
            return True
        else:
            print(f"❌ 실패: {response.text}")
            return False

    except Exception as e:
        print(f"❌ 오류: {e}")
        return False


def run_all_tests():
    """모든 테스트 실행"""
    print("\n" + "=" * 60)
    print("자동매매 API 테스트 시작")
    print(f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    # 1. 헬스 체크 (서버 실행 여부 확인)
    results.append(("헬스 체크", test_trading_health()))

    # 2. 상태 조회 (자동매매 시작 전)
    results.append(("상태 조회 (시작 전)", test_trading_status()))

    # 3. 자동매매 시작
    results.append(("자동매매 시작", test_trading_start()))

    # 4. 상태 조회 (자동매매 시작 후)
    time.sleep(1)  # 1초 대기
    results.append(("상태 조회 (시작 후)", test_trading_status()))

    # 5. 포트폴리오 조회
    results.append(("포트폴리오 조회", test_portfolio_status()))

    # 6. 자동매매 중지
    results.append(("자동매매 중지", test_trading_stop()))

    # 7. 상태 조회 (중지 후)
    time.sleep(1)
    results.append(("상태 조회 (중지 후)", test_trading_status()))

    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)

    success_count = sum(1 for _, result in results if result)
    total_count = len(results)

    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")

    print("\n" + "-" * 60)
    print(f"총 {total_count}개 테스트 중 {success_count}개 성공 ({success_count/total_count*100:.1f}%)")
    print("=" * 60)


if __name__ == "__main__":
    print("⚠️  주의: 백엔드 서버가 실행 중이어야 합니다 (http://localhost:8000)")
    print("   START.bat을 실행한 후 이 스크립트를 실행하세요.\n")

    input("계속하려면 Enter를 누르세요...")

    run_all_tests()

    print("\n\n💡 Swagger UI에서 직접 테스트: http://localhost:8000/docs")

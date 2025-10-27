"""
통화 처리 검증 테스트 - 재발 방지
"""
import requests

BASE_URL = "http://localhost:8000/api/v1"

def test_korean_stock():
    """한국 주식: 원화 가격이 정상 범위인지 확인"""
    print("=" * 80)
    print("[TEST 1] Korean Stock (Samsung Electronics)")
    print("=" * 80)

    request_data = {
        "strategy_name": "livermore",
        "symbols": ["005930"],
        "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
        "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
    }

    response = requests.post(f"{BASE_URL}/master-strategy", json=request_data, timeout=120)

    if response.status_code == 200:
        result = response.json()

        # 검증 1: currency 필드
        if result['trade_history']:
            first_trade = result['trade_history'][0]
            assert first_trade['currency'] == 'KRW', f"[FAIL] Currency error: {first_trade['currency']}"
            print(f"[OK] Currency field: {first_trade['currency']}")

            # 검증 2: 가격 범위 (삼성전자는 50,000~150,000원 사이)
            entry_krw = first_trade['entry_price_krw']
            assert 50000 <= entry_krw <= 150000, f"[FAIL] Price range error: {entry_krw:,} KRW"
            print(f"[OK] Entry price: {entry_krw:,} KRW (normal range)")

            # 검증 3: USD 환산이 합리적인지 (원화 / 1400 정도)
            entry_usd = first_trade['entry_price']
            expected_usd = entry_krw / 1400
            assert abs(entry_usd - expected_usd) < 10, f"[FAIL] Exchange rate error: ${entry_usd}"
            print(f"[OK] USD conversion: ${entry_usd:.2f} (normal)")

            print(f"\n거래 예시:")
            print(f"  매수가: {entry_krw:,}원 (${entry_usd:.2f})")
            print(f"  수량: {first_trade['shares']:.4f}")
            print(f"  매수금액: {first_trade['position_value_krw']:,}원")
    else:
        print(f"❌ API 오류: {response.status_code}")
        return False

    return True


def test_us_stock():
    """미국 주식: 달러 가격이 정상 범위인지 확인"""
    print("\n" + "=" * 80)
    print("✅ TEST 2: 미국 주식 (애플)")
    print("=" * 80)

    request_data = {
        "strategy_name": "livermore",
        "symbols": ["AAPL"],
        "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
        "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
    }

    response = requests.post(f"{BASE_URL}/master-strategy", json=request_data, timeout=120)

    if response.status_code == 200:
        result = response.json()

        if result['trade_history']:
            first_trade = result['trade_history'][0]

            # 검증 1: currency 필드
            assert first_trade['currency'] == 'USD', f"❌ 통화 오류: {first_trade['currency']}"
            print(f"✅ 통화 필드: {first_trade['currency']}")

            # 검증 2: 가격 범위 (애플은 $100~$250 사이)
            entry_usd = first_trade['entry_price']
            assert 100 <= entry_usd <= 300, f"❌ 가격 범위 오류: ${entry_usd}"
            print(f"✅ 매수가: ${entry_usd:.2f} (정상 범위)")

            # 검증 3: KRW 환산이 합리적인지 (달러 * 1400 정도)
            entry_krw = first_trade['entry_price_krw']
            expected_krw = entry_usd * 1400
            assert abs(entry_krw - expected_krw) < 50000, f"❌ 환율 오류: {entry_krw:,}원"
            print(f"✅ 원화 환산: {entry_krw:,}원 (정상)")

            print(f"\n거래 예시:")
            print(f"  매수가: ${entry_usd:.2f} ({entry_krw:,}원)")
            print(f"  수량: {first_trade['shares']:.4f}")
            print(f"  매수금액: ${first_trade['position_value']:,.2f}")
    else:
        print(f"❌ API 오류: {response.status_code}")
        return False

    return True


def test_lg_electronics():
    """LG전자 특별 테스트 - 이전 버그 재발 확인"""
    print("\n" + "=" * 80)
    print("✅ TEST 3: LG전자 (이전 버그 재발 확인)")
    print("=" * 80)

    request_data = {
        "strategy_name": "livermore",
        "symbols": ["066570"],
        "date_range": {"start": "2024-01-01", "end": "2025-10-04"},
        "simulate": {"bootstrap_runs": 1000, "transaction_cost_bps": 10, "slippage_bps": 5}
    }

    response = requests.post(f"{BASE_URL}/master-strategy", json=request_data, timeout=120)

    if response.status_code == 200:
        result = response.json()

        if result['trade_history']:
            first_trade = result['trade_history'][0]
            entry_krw = first_trade['entry_price_krw']

            # 이전 버그: $95989 같은 이상한 값
            # 정상 범위: 60,000~110,000원
            assert 60000 <= entry_krw <= 110000, f"❌ LG전자 가격 오류: {entry_krw:,}원 (버그 재발!)"
            print(f"✅ LG전자 매수가: {entry_krw:,}원 (정상)")

            # USD가 10만 달러 같은 이상한 값이 아닌지 확인
            entry_usd = first_trade['entry_price']
            assert entry_usd < 100, f"❌ LG전자 USD 오류: ${entry_usd} (버그 재발!)"
            print(f"✅ USD 환산: ${entry_usd:.2f} (정상)")

            print(f"\n✅ 이전 버그 재발 없음!")
    else:
        print(f"❌ API 오류: {response.status_code}")
        return False

    return True


if __name__ == "__main__":
    print("\n[CURRENCY VALIDATION TEST START]\n")

    test1 = test_korean_stock()
    test2 = test_us_stock()
    test3 = test_lg_electronics()

    print("\n" + "=" * 80)
    if test1 and test2 and test3:
        print("[OK] All tests passed! Currency handling is correct.")
    else:
        print("[FAIL] Some tests failed")
    print("=" * 80)

"""
원화 표시 테스트: 삼성전자 (한국 주식) + AAPL (미국 주식)
"""
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000/api/v1"

def test_korean_stock():
    """삼성전자 테스트"""
    print("=" * 100)
    print("삼성전자 (005930) - Jesse Livermore 전략 테스트")
    print("=" * 100)

    request_data = {
        "strategy_name": "livermore",
        "symbols": ["005930"],
        "date_range": {
            "start": "2024-01-01",
            "end": "2025-10-04"
        },
        "simulate": {
            "bootstrap_runs": 1000,
            "transaction_cost_bps": 10,
            "slippage_bps": 5
        }
    }

    response = requests.post(f"{BASE_URL}/master-strategy", json=request_data, timeout=120)

    if response.status_code == 200:
        result = response.json()

        print(f"\n환율: $1 = {result['exchange_rate']:,.2f}")
        print(f"\n초기 자본:")
        print(f"  USD: ${result['initial_capital']:,.2f}")
        print(f"  KRW: {result['initial_capital_krw']:,.0f}")

        print(f"\n최종 자본:")
        print(f"  USD: ${result['final_capital']:,.2f}")
        print(f"  KRW: {result['final_capital_krw']:,.0f}")

        print(f"\n수익:")
        profit_usd = result['final_capital'] - result['initial_capital']
        profit_krw = result['final_capital_krw'] - result['initial_capital_krw']
        profit_pct = (profit_usd / result['initial_capital']) * 100
        print(f"  USD: ${profit_usd:,.2f}")
        print(f"  KRW: {profit_krw:,.0f}")
        print(f"  수익률: {profit_pct:.2f}%")

        if result['trade_history']:
            print(f"\n거래 내역 (최근 3개):")
            for i, trade in enumerate(result['trade_history'][:3], 1):
                print(f"\n  [{i}] {trade['entry_date']} ~ {trade['exit_date']}")
                print(f"      매수가: ${trade['entry_price']:,.2f} ({trade['entry_price_krw']:,.0f})")
                print(f"      매도가: ${trade['exit_price']:,.2f} ({trade['exit_price_krw']:,.0f})")
                print(f"      매수금액: ${trade['position_value']:,.2f} ({trade['position_value_krw']:,.0f})")
                print(f"      손익: ${trade['pnl']:,.2f} ({trade['pnl_krw']:,.0f}) [{trade['pnl_pct']:.2f}%]")
                print(f"      보유기간: {trade['holding_days']}일")
                print(f"      기준통화: {trade['currency']}")
    else:
        print(f"에러: {response.status_code}")
        print(response.text)


def test_us_stock():
    """AAPL 테스트"""
    print("\n\n" + "=" * 100)
    print("애플 (AAPL) - Jesse Livermore 전략 테스트")
    print("=" * 100)

    request_data = {
        "strategy_name": "livermore",
        "symbols": ["AAPL"],
        "date_range": {
            "start": "2024-01-01",
            "end": "2025-10-04"
        },
        "simulate": {
            "bootstrap_runs": 1000,
            "transaction_cost_bps": 10,
            "slippage_bps": 5
        }
    }

    response = requests.post(f"{BASE_URL}/master-strategy", json=request_data, timeout=120)

    if response.status_code == 200:
        result = response.json()

        print(f"\n환율: $1 = {result['exchange_rate']:,.2f}")
        print(f"\n초기 자본:")
        print(f"  USD: ${result['initial_capital']:,.2f}")
        print(f"  KRW: {result['initial_capital_krw']:,.0f}")

        print(f"\n최종 자본:")
        print(f"  USD: ${result['final_capital']:,.2f}")
        print(f"  KRW: {result['final_capital_krw']:,.0f}")

        print(f"\n수익:")
        profit_usd = result['final_capital'] - result['initial_capital']
        profit_krw = result['final_capital_krw'] - result['initial_capital_krw']
        profit_pct = (profit_usd / result['initial_capital']) * 100
        print(f"  USD: ${profit_usd:,.2f}")
        print(f"  KRW: {profit_krw:,.0f}")
        print(f"  수익률: {profit_pct:.2f}%")

        if result['trade_history']:
            print(f"\n거래 내역 (최근 3개):")
            for i, trade in enumerate(result['trade_history'][:3], 1):
                print(f"\n  [{i}] {trade['entry_date']} ~ {trade['exit_date']}")
                print(f"      매수가: ${trade['entry_price']:,.2f} ({trade['entry_price_krw']:,.0f})")
                print(f"      매도가: ${trade['exit_price']:,.2f} ({trade['exit_price_krw']:,.0f})")
                print(f"      매수금액: ${trade['position_value']:,.2f} ({trade['position_value_krw']:,.0f})")
                print(f"      손익: ${trade['pnl']:,.2f} ({trade['pnl_krw']:,.0f}) [{trade['pnl_pct']:.2f}%]")
                print(f"      보유기간: {trade['holding_days']}일")
                print(f"      기준통화: {trade['currency']}")
    else:
        print(f"에러: {response.status_code}")
        print(response.text)


if __name__ == "__main__":
    test_korean_stock()
    test_us_stock()
    print("\n" + "=" * 100)
    print("테스트 완료!")
    print("=" * 100)

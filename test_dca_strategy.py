"""
DCA (Dollar Cost Averaging) 전략 테스트

씨젠 (096530.KQ)으로 DCA 전략 백테스트
"""
import requests
import json

url = "http://localhost:8000/api/v1/master-strategy"

payload = {
    "strategy_name": "dca",
    "symbols": ["096530.KQ"],  # 씨젠
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

print("=" * 80)
print("DCA (Dollar Cost Averaging) 전략 테스트")
print("=" * 80)
print(f"종목: 씨젠 (096530.KQ)")
print(f"기간: 2024-01-01 ~ 2024-12-31")
print(f"전략: 매월 첫 거래일 + 상승 추세 확인 (MA20 > MA50)")
print("=" * 80)

try:
    response = requests.post(url, json=payload)
    response.raise_for_status()

    result = response.json()

    print("\n✅ DCA 전략 백테스트 성공!")
    print("\n[전략 정보]")
    info = result.get("strategy_info", {})
    print(f"  이름: {info.get('name')}")
    print(f"  설명: {info.get('description')}")
    print(f"  보유 기간: {info.get('holding_period')}")
    print(f"  리스크 프로파일: {info.get('risk_profile')}")

    print("\n[핵심 원칙]")
    for principle in info.get('key_principles', []):
        print(f"  - {principle}")

    print("\n[백테스트 결과]")
    metrics = result.get("backtest", {}).get("metrics", {})
    print(f"  CAGR: {metrics.get('CAGR', 0):.2%}")
    print(f"  Sharpe Ratio: {metrics.get('Sharpe', 0):.2f}")
    print(f"  Max Drawdown: {metrics.get('MaxDD', 0):.2%}")
    print(f"  Hit Ratio: {metrics.get('HitRatio', 0):.2%}")
    print(f"  총 거래 수: {metrics.get('TotalTrades', 0)}")
    print(f"  수익 거래: {metrics.get('WinTrades', 0)}")
    print(f"  손실 거래: {metrics.get('LossTrades', 0)}")

    print("\n[수익률]")
    print(f"  초기 자본 (KRW): {result.get('initial_capital_krw', 0):,.0f}원")
    print(f"  최종 자본 (KRW): {result.get('final_capital_krw', 0):,.0f}원")
    profit_krw = result.get('final_capital_krw', 0) - result.get('initial_capital_krw', 0)
    profit_pct = (profit_krw / result.get('initial_capital_krw', 1)) * 100
    print(f"  손익 (KRW): {profit_krw:,.0f}원 ({profit_pct:+.2f}%)")

    print("\n[거래 내역]")
    trades = result.get("trade_history", [])
    if trades:
        print(f"  총 {len(trades)}건의 거래")
        for i, trade in enumerate(trades[:5], 1):  # 최대 5개만 표시
            print(f"\n  [{i}] {trade['entry_date']} ~ {trade['exit_date']}")
            print(f"      진입: {trade['entry_price_krw']:,.0f}원 x {trade['shares']:.2f}주")
            print(f"      청산: {trade['exit_price_krw']:,.0f}원")
            print(f"      손익: {trade['pnl_krw']:,.0f}원 ({trade['pnl_pct']:+.2f}%)")
            print(f"      보유일: {trade['holding_days']}일")
            print(f"      청산 사유: {trade['exit_reason']}")

        if len(trades) > 5:
            print(f"\n  ... 외 {len(trades) - 5}건의 거래")
    else:
        print("  거래 내역 없음 (진입 조건 미충족)")

    print("\n" + "=" * 80)
    print("✅ 테스트 완료")
    print("=" * 80)

except requests.exceptions.ConnectionError:
    print("\n❌ 오류: 백엔드 서버에 연결할 수 없습니다.")
    print("   START.bat를 실행하여 백엔드를 먼저 시작하세요.")
except Exception as e:
    print(f"\n❌ 오류 발생: {e}")
    if hasattr(e, 'response') and e.response:
        print(f"   응답: {e.response.text}")

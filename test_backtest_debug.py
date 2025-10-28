"""백테스트 계산 버그 디버깅 스크립트"""
import sys
sys.path.append('backend')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.services.backtest import BacktestEngine
from app.models.schemas import RiskParams

# 1. 간단한 샘플 데이터 생성
dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
np.random.seed(42)

# 상승 추세 데이터 (10% 상승)
prices = np.linspace(100, 110, 100) + np.random.randn(100) * 2
data = pd.DataFrame({
    'open': prices * 0.99,
    'high': prices * 1.02,
    'low': prices * 0.98,
    'close': prices,
    'volume': np.random.randint(1000000, 5000000, 100)
}, index=dates)

# 2. 간단한 시그널: 처음 10일, 30일, 50일, 70일에 매수, 각 10일 후 매도
entry_signals = pd.Series(False, index=dates)
exit_signals = pd.Series(False, index=dates)

entry_signals.iloc[[10, 30, 50, 70]] = True
exit_signals.iloc[[20, 40, 60, 80]] = True

# 3. 백테스트 실행 (757 USD 시작)
initial_capital = 757.58
risk_params = RiskParams(
    stop_pct=0.08,
    take_pct=10.0,
    position_sizing="equal_weight"
)

engine = BacktestEngine(
    data=data,
    entry_signals=entry_signals,
    exit_signals=exit_signals,
    risk_params=risk_params,
    transaction_cost_bps=10,
    slippage_bps=5,
    initial_capital=initial_capital,
    is_korean_stock=False
)

print("="*80)
print("백테스트 시작")
print(f"초기 자본: ${initial_capital:.2f}")
print("="*80)

metrics, equity_curve, risk_summary = engine.run()

print("\n" + "="*80)
print("백테스트 결과")
print("="*80)
print(f"CAGR: {metrics.CAGR*100:.2f}%")
print(f"Sharpe: {metrics.Sharpe:.2f}")
print(f"Max DD: {metrics.MaxDD*100:.2f}%")
print(f"Hit Ratio: {metrics.HitRatio*100:.2f}%")
print(f"총 거래: {metrics.TotalTrades}개")
print(f"승: {metrics.WinTrades}개, 패: {metrics.LossTrades}개")

print("\n" + "="*80)
print("거래 내역")
print("="*80)
trade_df = engine.get_trade_details()
if not trade_df.empty:
    for idx, trade in trade_df.iterrows():
        print(f"\n거래 #{idx+1}")
        print(f"  진입: {trade['entry_date'].strftime('%Y-%m-%d')} @ ${trade['entry_price']:.2f}")
        print(f"  청산: {trade['exit_date'].strftime('%Y-%m-%d')} @ ${trade['exit_price']:.2f}")
        print(f"  주식수: {trade['shares']}")
        print(f"  손익: ${trade['pnl']:+.2f} ({trade['pnl_pct']*100:+.2f}%)")
        print(f"  거래 후 잔고: ${trade['balance_after']:.2f}")

    print("\n" + "="*80)
    print("최종 검증")
    print("="*80)
    print(f"초기 자본: ${initial_capital:.2f}")
    total_pnl = trade_df['pnl'].sum()
    print(f"개별 PnL 합계: ${total_pnl:+.2f}")
    expected_final = initial_capital + total_pnl
    print(f"예상 최종 자본: ${expected_final:.2f}")
    actual_final = trade_df.iloc[-1]['balance_after']
    print(f"실제 최종 자본: ${actual_final:.2f}")
    print(f"차이: ${actual_final - expected_final:+.2f}")

    if abs(actual_final - expected_final) > 1.0:
        print("\n⚠️  경고: 예상 최종 자본과 실제 최종 자본이 다릅니다!")
        print("버그 가능성이 높습니다.")
    else:
        print("\n✅ 계산이 정확합니다.")
else:
    print("거래 내역 없음")

print("\n" + "="*80)
print("Equity Curve (처음 10개)")
print("="*80)
print(equity_curve.head(10))
print(f"\n최종 Equity: ${equity_curve.iloc[-1]:.2f}")

"""
Jesse Livermore 전략 디버깅
LG전자 035720.KS 2024년 거래 내역 분석
"""
import yfinance as yf
import pandas as pd
import sys
sys.path.append('backend')

from app.services.indicators import load_sample_data, IndicatorCalculator
from app.services.master_strategies import LivermoreStrategy

# LG전자 데이터 로드
symbol = '035720.KS'
start_date = '2024-01-01'
end_date = '2024-12-31'

print(f"=== {symbol} 데이터 로드 ===")
data = load_sample_data(symbol, start_date, end_date)
data = IndicatorCalculator.calculate_all(data)

print(f"데이터 기간: {data.index[0]} ~ {data.index[-1]}")
print(f"데이터 건수: {len(data)}")

# Livermore 전략 시그널 생성
strategy = LivermoreStrategy()
entry_signals, exit_signals = strategy.generate_signals(symbol, data)

print(f"\n=== 시그널 통계 ===")
print(f"진입 시그널: {entry_signals.sum()}회")
print(f"청산 시그널: {exit_signals.sum()}회")

# 진입 시그널 상세
print(f"\n=== 진입 시그널 상세 ===")
entry_dates = data[entry_signals].index
for i, date in enumerate(entry_dates[:10]):  # 최대 10개
    row = data.loc[date]
    close = row['close']

    # 20일 신고가
    rolling_high_20 = data['close'].rolling(20).max().loc[date]

    # MA50
    ma50 = data['close'].rolling(50).mean().loc[date]

    # 거래량
    vol_ma20 = data['volume'].rolling(20).mean().loc[date] if 'volume' in data.columns else None
    volume = row.get('volume', None)

    print(f"\n{i+1}. {date.date()}")
    print(f"   종가: {close:,.0f}원")
    print(f"   20일 고점: {rolling_high_20:,.0f}원 (돌파: {close > rolling_high_20})")
    print(f"   MA50: {ma50:,.0f}원 (위치: {'위' if close > ma50 else '아래'})")
    if volume and vol_ma20:
        print(f"   거래량: {volume:,.0f} (평균: {vol_ma20:,.0f}, 비율: {volume/vol_ma20:.2f}x)")

# 청산 시그널 상세
print(f"\n=== 청산 시그널 분석 ===")
exit_dates = data[exit_signals].index
print(f"총 {len(exit_dates)}개 청산 시그널")

# MA50 이탈 vs 10% 손절
close = data['close']
ma50 = close.rolling(50).mean()
recent_high = close.rolling(20).max()

trend_broken = close < ma50
pullback = close < recent_high * 0.90

print(f"\nMA50 이탈 청산: {trend_broken.sum()}회")
print(f"10% 손절 청산: {pullback.sum()}회")
print(f"둘 다 만족: {(trend_broken & pullback).sum()}회")

# 문제점 분석
print(f"\n=== 문제점 분석 ===")
print(f"1. 20일 신고가 돌파 (현재): {(close > close.rolling(20).max().shift(1)).sum()}회")
print(f"   → 52주 신고가 돌파 (리버모어): {(close > close.rolling(252).max().shift(1)).sum()}회")
print(f"\n2. 청산 조건이 너무 빡빡함:")
print(f"   - MA50 아래: {trend_broken.sum()}회 ({trend_broken.sum()/len(data)*100:.1f}%)")
print(f"   - 10% 손절: {pullback.sum()}회 ({pullback.sum()/len(data)*100:.1f}%)")
print(f"   - 청산 시그널 (OR): {exit_signals.sum()}회 ({exit_signals.sum()/len(data)*100:.1f}%)")

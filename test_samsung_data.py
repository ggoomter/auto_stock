# -*- coding: utf-8 -*-
"""삼성전자 펀더멘털 데이터 테스트"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import yfinance as yf

ticker = yf.Ticker('005930.KS')
info = ticker.info

print("=" * 60)
print("삼성전자 (005930.KS) yfinance 데이터")
print("=" * 60)

# 주요 지표
metrics = {
    'P/E (trailingPE)': info.get('trailingPE'),
    'P/E (forwardPE)': info.get('forwardPE'),
    'P/B (priceToBook)': info.get('priceToBook'),
    'ROE (returnOnEquity)': info.get('returnOnEquity'),
    'Debt to Equity (debtToEquity)': info.get('debtToEquity'),
    'Free Cash Flow (freeCashflow)': info.get('freeCashflow'),
    'Current Price': info.get('currentPrice'),
    'Market Cap': info.get('marketCap'),
}

for key, value in metrics.items():
    if value is not None:
        print(f"{key:30s}: {value}")
    else:
        print(f"{key:30s}: ❌ 데이터 없음")

print("\n" + "=" * 60)
print("재무제표 (Financials)")
print("=" * 60)

# 재무제표 확인
try:
    financials = ticker.financials
    balance_sheet = ticker.balance_sheet
    cashflow = ticker.cashflow

    print(f"\nFinancials shape: {financials.shape if financials is not None else 'None'}")
    print(f"Balance Sheet shape: {balance_sheet.shape if balance_sheet is not None else 'None'}")
    print(f"Cash Flow shape: {cashflow.shape if cashflow is not None else 'None'}")

    if cashflow is not None and not cashflow.empty:
        print("\nCash Flow 데이터 (최근):")
        print(cashflow.head())

        # Free Cash Flow 계산
        if 'Free Cash Flow' in cashflow.index:
            fcf = cashflow.loc['Free Cash Flow'].iloc[0]
            print(f"\nFree Cash Flow (최근): {fcf:,.0f}")
        elif 'Operating Cash Flow' in cashflow.index and 'Capital Expenditure' in cashflow.index:
            ocf = cashflow.loc['Operating Cash Flow'].iloc[0]
            capex = cashflow.loc['Capital Expenditure'].iloc[0]
            fcf = ocf + capex  # capex는 보통 음수
            print(f"\nFree Cash Flow (계산): OCF {ocf:,.0f} + CapEx {capex:,.0f} = {fcf:,.0f}")

except Exception as e:
    print(f"재무제표 로드 오류: {e}")

print("\n" + "=" * 60)
print("모든 info 키 (일부)")
print("=" * 60)
print("Available keys:", list(info.keys())[:20])

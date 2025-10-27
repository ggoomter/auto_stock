"""
Symbol detection logic test
"""

def test_symbol_detection(symbol):
    symbol_base = symbol.replace('.KS', '').replace('.KQ', '')
    is_korean_stock = (symbol_base.isdigit() and len(symbol_base) == 6) or symbol.endswith(('.KS', '.KQ'))
    print(f"Symbol: {symbol:15} | Base: {symbol_base:10} | Korean: {is_korean_stock}")

print("Symbol Detection Test:")
print("-" * 60)
test_symbol_detection("005930")        # True - 6 digits
test_symbol_detection("005930.KS")     # True - endswith .KS
test_symbol_detection("000720.KS")     # True - endswith .KS
test_symbol_detection("066570.KQ")     # True - endswith .KQ
test_symbol_detection("AAPL")          # False
test_symbol_detection("NVDA")          # False
test_symbol_detection("TSLA")          # False

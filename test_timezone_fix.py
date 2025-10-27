"""
Timezone 수정 테스트 스크립트
백엔드를 직접 import해서 테스트
"""
import sys
sys.path.insert(0, 'G:/ai_coding/auto_stock/backend')

from app.services.indicators import load_sample_data, IndicatorCalculator
from app.services.master_strategies import get_strategy

# 1. 데이터 로드
print("="*80)
print("1. 데이터 로드 중...")
try:
    df = load_sample_data("AAPL", "2020-01-01", "2023-12-31")
    print(f"[OK] Data loaded: {len(df)} rows")
    print(f"   Index timezone: {df.index.tz}")
    print(f"   Index type: {type(df.index[0])}")
except Exception as e:
    print(f"[ERROR] Data load failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. 지표 계산
print("\n" + "="*80)
print("2. 지표 계산 중...")
try:
    df = IndicatorCalculator.calculate_all(df)
    print(f"[OK] Indicators calculated: {len(df)} rows")
    print(f"   Index timezone: {df.index.tz}")
except Exception as e:
    print(f"[ERROR] Indicator calculation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. 전략 시그널 생성
print("\n" + "="*80)
print("3. Buffett 전략 시그널 생성 중...")
try:
    strategy = get_strategy("buffett")
    entry_signals, exit_signals = strategy.generate_signals("AAPL", df)
    print(f"[OK] Signal generation completed!")
    print(f"   Entry signals: {entry_signals.sum()}")
    print(f"   Exit signals: {exit_signals.sum()}")
    print(f"\n[SUCCESS] TIMEZONE ERROR FIXED!")
except Exception as e:
    print(f"[ERROR] Signal generation failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

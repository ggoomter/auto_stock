"""한국 매도 거래세 반영 테스트"""
import pandas as pd
import pytest


def _engine(is_korean, sell_tax_bps=18):
    from app.services.backtest import BacktestEngine
    idx = pd.date_range("2024-01-01", periods=10)
    data = pd.DataFrame({"open": 10000.0, "high": 10000.0, "low": 10000.0,
                         "close": 10000.0, "volume": 1000}, index=idx)
    sig = pd.Series(False, index=idx)
    return BacktestEngine(data, sig, sig.copy(),
                          {"stop_loss_pct": 0.1, "take_profit_pct": 0.2},
                          is_korean_stock=is_korean, sell_tax_bps=sell_tax_bps)


def test_korean_exit_price_includes_tax():
    kr = _engine(True)
    us = _engine(False)
    assert kr._execute_exit_price(10000.0) < us._execute_exit_price(10000.0)


def test_tax_amount_is_18bps():
    kr0 = _engine(True, sell_tax_bps=0)
    kr18 = _engine(True, sell_tax_bps=18)
    # 세금 0bp 대비 18bp만큼 낮아야 함 (tick 내림 전 기준 0.18%)
    assert kr18._execute_exit_price(100000.0) <= kr0._execute_exit_price(100000.0) * (1 - 0.0018) + 100


def test_us_exit_price_unaffected_by_tax():
    # 미국 주식은 sell_tax 미적용 → sell_tax_bps 값과 무관하게 동일
    us0 = _engine(False, sell_tax_bps=0)
    us50 = _engine(False, sell_tax_bps=50)
    assert us0._execute_exit_price(100000.0) == us50._execute_exit_price(100000.0)


def test_entry_price_unaffected_by_tax():
    # 매수는 무변경 → 한국 주식이라도 sell_tax가 매수가에 영향 없음
    kr0 = _engine(True, sell_tax_bps=0)
    kr18 = _engine(True, sell_tax_bps=18)
    assert kr0._execute_entry_price(100000.0) == kr18._execute_entry_price(100000.0)

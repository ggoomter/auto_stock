"""
모의투자 가상 체결 규칙.
실제 호가/체결을 모사할 수 없으므로 보수적 결정론으로 대체한다:
매수는 불리하게(슬리피지 가산 후 호가단위 올림), 매도도 불리하게(차감 후 내림).
"""
from ..utils.tick_size import round_to_tick_up, round_to_tick_down


def is_korean_symbol(symbol: str) -> bool:
    """한국 종목 여부: .KS/.KQ 접미사 또는 6자리 숫자 코드"""
    if symbol.endswith(".KS") or symbol.endswith(".KQ"):
        return True
    return symbol.isdigit() and len(symbol) == 6


def simulate_fill_price(price: float, side: str, slippage: float,
                        symbol: str) -> float:
    """보수적 가상 체결가 계산. side는 'buy' 또는 'sell'."""
    korean = is_korean_symbol(symbol)
    if side == "buy":
        return round_to_tick_up(price * (1 + slippage), korean)
    if side == "sell":
        return round_to_tick_down(price * (1 - slippage), korean)
    raise ValueError(f"지원하지 않는 side: {side}")

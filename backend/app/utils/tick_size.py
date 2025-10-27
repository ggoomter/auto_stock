"""
한국 주식 호가 단위 (Tick Size) 처리

한국 주식시장에서는 가격대별로 호가 단위가 정해져 있음
"""


def get_korean_tick_size(price: float) -> int:
    """
    한국 주식 호가 단위 반환

    Args:
        price: 주가

    Returns:
        호가 단위 (원)
    """
    if price < 1000:
        return 1
    elif price < 5000:
        return 5
    elif price < 10000:
        return 10
    elif price < 50000:
        return 50
    elif price < 100000:
        return 100
    elif price < 500000:
        return 500
    else:
        return 1000


def round_to_tick(price: float, is_korean: bool = False) -> float:
    """
    호가 단위로 반올림

    Args:
        price: 원본 가격
        is_korean: 한국 주식 여부

    Returns:
        호가 단위로 반올림된 가격
    """
    if not is_korean:
        return price

    tick = get_korean_tick_size(price)
    return round(price / tick) * tick


def round_to_tick_down(price: float, is_korean: bool = False) -> float:
    """
    호가 단위로 내림 (매수 시 보수적)

    Args:
        price: 원본 가격
        is_korean: 한국 주식 여부

    Returns:
        호가 단위로 내림된 가격
    """
    if not is_korean:
        return price

    tick = get_korean_tick_size(price)
    return (int(price / tick)) * tick


def round_to_tick_up(price: float, is_korean: bool = False) -> float:
    """
    호가 단위로 올림 (매도 시 보수적)

    Args:
        price: 원본 가격
        is_korean: 한국 주식 여부

    Returns:
        호가 단위로 올림된 가격
    """
    if not is_korean:
        return price

    tick = get_korean_tick_size(price)
    import math
    return math.ceil(price / tick) * tick

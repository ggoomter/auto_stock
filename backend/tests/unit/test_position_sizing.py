"""1/N 균등 배분 사이징 테스트"""


def test_equal_weight_basic():
    from app.services.paper_execution import calculate_equal_weight_shares
    # 1,000만원 / 5포지션 = 200만원 / 71,000원 = 28.16주 → 28주
    assert calculate_equal_weight_shares(10_000_000, 5, 71000.0) == 28


def test_equal_weight_never_negative_or_fractional():
    from app.services.paper_execution import calculate_equal_weight_shares
    assert calculate_equal_weight_shares(100_000, 5, 71000.0) == 0  # 예산 부족
    assert calculate_equal_weight_shares(10_000_000, 5, 0) == 0     # 가격 오류 방어

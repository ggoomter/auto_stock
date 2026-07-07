"""추천 엔진(recommender) 단위 테스트.

순수 로직만 검증한다 — pykrx 실호출 금지, 전부 합성 DataFrame/mock.
- fundamental_filter: 3개/2개 통과, 1개(제외), 값 None(passed=False)
- technical_signals: 골든크로스 True, 횡보 False, 짧은 데이터 '데이터 부족'
- score: 5개 전부 통과 ≈ 100, 0개 = 0
- generate_recommendations: build_universe/OHLCV mock으로 저장·통계 검증
"""
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd


def _patch_stock(module_path: str, **fns):
    """pykrx stock을 Mock 묶음으로 통째 교체 — stock=None(임포트 실패) 환경에서도 결정론적"""
    return patch(module_path, SimpleNamespace(**fns), create=True)

from app.services.recommender import (
    Candidate,
    build_universe,
    fundamental_filter,
    generate_recommendations,
    score,
    technical_signals,
)


# ── 합성 시계열 헬퍼 ──────────────────────────────────────────────
def _make_ohlcv(closes: list[float], highs: list[float] | None = None) -> pd.DataFrame:
    """소문자 컬럼 일봉 DataFrame 생성(호출자 rename 후 형태)."""
    if highs is None:
        highs = closes
    n = len(closes)
    return pd.DataFrame(
        {
            "open": closes,
            "high": highs,
            "low": closes,
            "close": closes,
            "volume": [1000] * n,
        }
    )


def _golden_cross_series() -> pd.DataFrame:
    # 276일 평탄(100) 후 마지막 4일 급등(130) → MA20이 MA60을 최근 5일 내 상향 돌파
    closes = [100.0] * 276 + [130.0] * 4
    return _make_ohlcv(closes)


def _flat_series() -> pd.DataFrame:
    # 완전 횡보 → 골든크로스 없음
    return _make_ohlcv([100.0] * 280)


def _rsi_rebound_series() -> pd.DataFrame:
    # 250일 평탄 → 8일 급락(RSI<30) → 2일 반등(RSI≥30)
    closes = [100.0] * 250
    closes += [100.0 - 6 * (i + 1) for i in range(8)]  # 94,88,...,52
    closes += [70.0, 85.0]  # 반등
    return _make_ohlcv(closes)


# ── fundamental_filter ───────────────────────────────────────────
def _cand(per=None, pbr=None, roe=None) -> Candidate:
    return Candidate(
        symbol="005930", name="테스트", close=50000.0,
        per=per, pbr=pbr, roe=roe, market_cap=1e12,
    )


def test_fundamental_filter_all_three_pass():
    cand = _cand(per=10.0, pbr=1.5, roe=0.20)
    result = fundamental_filter([cand])
    assert len(result) == 1
    _, conds = result[0]
    assert len(conds) == 3
    assert all(c["passed"] for c in conds)


def test_fundamental_filter_two_pass_included():
    # PER 통과, PBR 통과, ROE 실패(0.05<0.10) → 2개 통과 → 포함
    cand = _cand(per=10.0, pbr=1.5, roe=0.05)
    result = fundamental_filter([cand])
    assert len(result) == 1
    _, conds = result[0]
    passed = [c for c in conds if c["passed"]]
    assert len(passed) == 2


def test_fundamental_filter_one_pass_excluded():
    # PER 통과, PBR 실패(5>3), ROE 실패 → 1개 통과 → 제외
    cand = _cand(per=10.0, pbr=5.0, roe=0.05)
    result = fundamental_filter([cand])
    assert result == []


def test_fundamental_filter_none_marked_failed():
    # per=None → passed=False + '데이터 없음', pbr/roe 통과 → 2개 통과로 포함
    cand = _cand(per=None, pbr=1.5, roe=0.20)
    result = fundamental_filter([cand])
    assert len(result) == 1
    _, conds = result[0]
    per_cond = next(c for c in conds if c["condition_name_en"] == "PER")
    assert per_cond["passed"] is False
    assert per_cond["actual_value"] == "데이터 없음"


# ── technical_signals ────────────────────────────────────────────
def test_technical_golden_cross_true():
    signals = technical_signals("005930", _golden_cross_series())
    gc = next(s for s in signals if s["condition_name_en"] == "GoldenCross")
    assert gc["passed"] is True


def test_technical_flat_no_golden_cross():
    signals = technical_signals("005930", _flat_series())
    gc = next(s for s in signals if s["condition_name_en"] == "GoldenCross")
    assert gc["passed"] is False


def test_technical_rsi_rebound_true():
    signals = technical_signals("005930", _rsi_rebound_series())
    rsi = next(s for s in signals if s["condition_name_en"] == "RSIRebound")
    assert rsi["passed"] is True


def test_technical_short_data_insufficient():
    signals = technical_signals("005930", _make_ohlcv([100.0] * 100))
    assert len(signals) == 3
    assert all(s["passed"] is False for s in signals)
    assert all(s["actual_value"] == "데이터 부족" for s in signals)


# ── score ────────────────────────────────────────────────────────
def test_score_all_pass_is_100():
    conds = [{"passed": True}] * 3
    sigs = [{"passed": True}] * 3
    assert score(conds, sigs) == 100.0


def test_score_none_pass_is_zero():
    conds = [{"passed": False}] * 3
    sigs = [{"passed": False}] * 3
    assert score(conds, sigs) == 0.0


# ── generate_recommendations ─────────────────────────────────────
class _FakeRepo:
    def __init__(self):
        self.saved = []

    def save(self, rec_date, symbol, name, score, passed_conditions,
             technical_signals):
        self.saved.append(
            {"rec_date": rec_date, "symbol": symbol, "name": name,
             "score": score, "passed_conditions": passed_conditions,
             "technical_signals": technical_signals}
        )


def test_generate_recommendations_flow():
    universe = [
        Candidate(symbol="000001", name="A", close=50000.0,
                  per=10.0, pbr=1.5, roe=0.20, market_cap=3e12),
        Candidate(symbol="000002", name="B", close=40000.0,
                  per=12.0, pbr=2.0, roe=0.15, market_cap=2e12),
        Candidate(symbol="000003", name="C", close=30000.0,
                  per=50.0, pbr=9.0, roe=0.01, market_cap=1e12),  # 0~1개 통과 → 제외
    ]
    repo = _FakeRepo()

    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_golden_cross_series()), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05", top_k=10, max_technical=30)

    assert stats["universe"] == 3
    assert stats["filtered"] == 2  # C 제외
    assert stats["saved"] == 2
    assert len(repo.saved) == 2
    # 저장된 근거 형식 확인
    first = repo.saved[0]
    assert isinstance(first["passed_conditions"], list)
    assert isinstance(first["technical_signals"], list)
    assert 0 <= first["score"] <= 100


def test_generate_passes_rec_date_to_build_universe():
    # rec_date가 유니버스 구성(휴장일 역보정 기준일)에 반영되어야 함
    repo = _FakeRepo()
    with patch("app.services.recommender.build_universe",
               return_value=[]) as mock_bu, \
         patch("app.services.recommender.time.sleep"):
        generate_recommendations(repo, "2026-07-05")
    assert mock_bu.call_args.kwargs["date"] == "20260705"


def test_build_universe_negative_bps_roe_none():
    # 자본잠식(BPS<0)이면 roe 계산 금지 → None (pykrx는 mock)
    cap_df = pd.DataFrame(
        {"시가총액": [1e12], "종가": [50000]}, index=["005930"],
    )
    fund_df = pd.DataFrame(
        {"PER": [10.0], "PBR": [1.5], "EPS": [5000.0], "BPS": [-100.0]},
        index=["005930"],
    )
    empty_df = pd.DataFrame({"시가총액": [], "종가": []})

    def fake_cap(date_str, market="KOSPI"):
        return cap_df if market == "KOSPI" else empty_df

    with _patch_stock("app.services.recommender.stock",
                      get_market_cap_by_ticker=Mock(side_effect=fake_cap),
                      get_market_fundamental_by_ticker=Mock(return_value=fund_df),
                      get_market_ticker_name=Mock(return_value="테스트")):
        cands = build_universe(top_n=10, date="20260703")

    assert len(cands) == 1
    assert cands[0].roe is None


def test_generate_recommendations_respects_top_k():
    universe = [
        Candidate(symbol=f"00000{i}", name=f"S{i}", close=50000.0,
                  per=10.0, pbr=1.5, roe=0.20, market_cap=(10 - i) * 1e12)
        for i in range(5)
    ]
    repo = _FakeRepo()

    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_flat_series()), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05", top_k=2, max_technical=30)

    assert stats["filtered"] == 5
    assert stats["saved"] == 2
    assert len(repo.saved) == 2


# ── 추세 건전성 게이트 (하락 추세 종목 추천 차단) ──────────────────
def _downtrend_series() -> pd.DataFrame:
    # 280일 연속 하락 (200 → 60): 종가가 200일 이동평균 아래 → 게이트 미달
    closes = [200.0 - i * 0.5 for i in range(280)]
    return _make_ohlcv(closes)


def test_generate_rejects_downtrend_below_ma200():
    """펀더멘털이 좋아도 종가 < MA200(하락 추세)이면 추천에서 제외.

    근거: 하락 추세 역행 매수 전략 전부 음의 기대값 (strategy_verification 3차).
    """
    universe = [Candidate(symbol="000001", name="A", close=60.0,
                          per=10.0, pbr=1.5, roe=0.20, market_cap=3e12)]
    repo = _FakeRepo()
    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_downtrend_series()), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05")

    assert stats["saved"] == 0
    assert stats["trend_rejected"] == 1
    assert repo.saved == []


def test_uptrend_includes_trend_condition_in_signals():
    """상승 추세 통과 종목은 시그널 목록에 '상승 추세' 조건이 포함되어 저장."""
    universe = [Candidate(symbol="000001", name="A", close=130.0,
                          per=10.0, pbr=1.5, roe=0.20, market_cap=3e12)]
    repo = _FakeRepo()
    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_golden_cross_series()), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05")

    assert stats["saved"] == 1
    trend = [s for s in repo.saved[0]["technical_signals"]
             if s["condition_name_en"] == "Trend"]
    assert len(trend) == 1 and trend[0]["passed"] is True


def test_score_ignores_trend_gate_condition():
    """Trend 게이트는 생존자 전원이 통과라 점수에 포함하면 안 됨 (등수 왜곡 방지)"""
    trend_only = [{"condition_name": "상승 추세", "condition_name_en": "Trend",
                   "required_value": "", "actual_value": "", "passed": True}]
    assert score([], trend_only) == 0.0


def test_regeneration_clears_stale_rows(tmp_path):
    """같은 날짜로 재생성하면 이전 추천이 삭제되고 새 결과만 남는다."""
    from app.db.database import init_db
    from app.db.repositories import RecommendationRepository
    db = str(tmp_path / "t.db")
    init_db(db)
    repo = RecommendationRepository(db)
    repo.save("2026-07-05", "999999", "옛종목", 90.0, [], [])

    universe = [Candidate(symbol="000001", name="A", close=130.0,
                          per=10.0, pbr=1.5, roe=0.20, market_cap=3e12)]
    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_golden_cross_series()), \
         patch("app.services.recommender.time.sleep"):
        generate_recommendations(repo, "2026-07-05")

    rows = repo.list_by_date("2026-07-05")
    assert [r["symbol"] for r in rows] == ["000001"]  # 옛종목(999999) 제거됨


# ── "지금 매수" 등재 3박자: 자격(추세) + 오늘 신호 + 급락일 아님 ──
def _qualified_but_no_signal_series() -> pd.DataFrame:
    """200일선 위(자격)이지만 신호는 없는 시계열:
    100 횡보 → 130까지 상승(골든크로스는 40일+ 전) → 118로 완만한 이탈
    (고점의 90.8% → 신고가 근접 미달, RSI 과매도 없음, 최근 크로스 없음)"""
    closes = [100.0] * 200
    closes += [100.0 + 0.75 * (i + 1) for i in range(40)]   # → 130
    closes += [130.0 - 0.3 * (i + 1) for i in range(40)]    # → 118
    return _make_ohlcv(closes)


def test_fundamentals_only_without_signal_excluded():
    """펀더멘털만 좋고 기술 신호가 0개면 '지금 매수' 목록에서 제외 (자격≠타이밍)."""
    universe = [Candidate(symbol="000001", name="A", close=118.0,
                          per=10.0, pbr=1.5, roe=0.20, market_cap=3e12)]
    repo = _FakeRepo()
    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv",
               return_value=_qualified_but_no_signal_series()), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05")

    assert stats["saved"] == 0
    assert stats["no_signal"] == 1


def test_crash_day_excluded_from_buy_now():
    """신호가 있어도 당일 -4% 초과 급락이면 제외 (급락 중 추격 매수 차단)."""
    df = _golden_cross_series()
    # 마지막 날 -9% 급락으로 교체 (골든크로스는 직전 5일 내 발생 상태 유지)
    crash = df["close"].iloc[-2] * 0.91
    df.iloc[-1, df.columns.get_loc("close")] = crash
    df.iloc[-1, df.columns.get_loc("low")] = crash * 0.99
    df.iloc[-1, df.columns.get_loc("high")] = df["close"].iloc[-2]

    universe = [Candidate(symbol="000001", name="A", close=float(crash),
                          per=10.0, pbr=1.5, roe=0.20, market_cap=3e12)]
    repo = _FakeRepo()
    with patch("app.services.recommender.build_universe", return_value=universe), \
         patch("app.services.recommender._fetch_ohlcv", return_value=df), \
         patch("app.services.recommender.time.sleep"):
        stats = generate_recommendations(repo, "2026-07-05")

    assert stats["saved"] == 0
    assert stats["crash_day"] == 1

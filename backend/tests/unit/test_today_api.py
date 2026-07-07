"""/today API 테스트

전역 DEFAULT_DB_PATH 회피: 라우터의 저장소 팩토리(_get_news_repo 등)를
monkeypatch로 tmp DB 저장소를 반환하도록 교체한다.
TestClient는 모듈 레벨 생성 시 startup을 실행하지 않으므로 실네트워크 걱정 없음.
"""
import pytest
from fastapi.testclient import TestClient

from app.db.database import init_db
from app.db.repositories import (
    NewsRepository,
    RecommendationRepository,
    JobRunRepository,
)
from app.api import today_routes
from app.main import app

client = TestClient(app)


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "today.db")
    init_db(path)
    return path


@pytest.fixture
def wire_repos(db_path, monkeypatch):
    """팩토리들을 tmp DB 저장소로 교체."""
    monkeypatch.setattr(today_routes, "_get_news_repo",
                        lambda: NewsRepository(db_path))
    monkeypatch.setattr(today_routes, "_get_reco_repo",
                        lambda: RecommendationRepository(db_path))
    monkeypatch.setattr(today_routes, "_get_job_repo",
                        lambda: JobRunRepository(db_path))
    return db_path


# ── 뉴스: date 필터 ──
def test_news_by_date_returns_two_with_symbols(wire_repos):
    repo = NewsRepository(wire_repos)
    repo.save_article(published_at="2026-07-05T08:00:00", source="A",
                      title="이른 기사", url="https://x/e", summary=None,
                      sentiment="neutral", symbols=["005930.KS"])
    repo.save_article(published_at="2026-07-05T18:00:00", source="B",
                      title="늦은 기사", url="https://x/l", summary=None,
                      sentiment="positive", symbols=["000660.KS"])
    repo.save_article(published_at="2026-07-04T12:00:00", source="C",
                      title="어제 기사", url="https://x/y", summary=None,
                      sentiment="neutral", symbols=[])

    resp = client.get("/api/v1/today/news?date=2026-07-05")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-07-05"
    assert body["count"] == 2
    assert body["articles"][0]["title"] == "늦은 기사"  # 최신순
    assert body["articles"][0]["symbols"] == ["000660.KS"]
    assert body["articles"][0]["sentiment"] == "positive"


# ── 뉴스: symbol 필터 (date 무시) ──
def test_news_by_symbol_ignores_date(wire_repos):
    repo = NewsRepository(wire_repos)
    repo.save_article(published_at="2026-07-05T08:00:00", source="A",
                      title="삼성 기사", url="https://x/s", summary=None,
                      sentiment="neutral", symbols=["005930.KS"])
    repo.save_article(published_at="2026-07-05T09:00:00", source="A",
                      title="하이닉스 기사", url="https://x/h", summary=None,
                      sentiment="neutral", symbols=["000660.KS"])

    resp = client.get("/api/v1/today/news?date=2020-01-01&symbol=005930.KS")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] is None  # symbol 지정 시 date 무시
    assert body["count"] == 1
    assert body["articles"][0]["title"] == "삼성 기사"


def test_news_default_date_is_empty_when_no_data(wire_repos):
    resp = client.get("/api/v1/today/news")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 0
    assert body["date"] is not None  # 기본 오늘 날짜


# ── 추천: 정렬 + disclaimer ──
def test_recommendations_sorted_with_disclaimer(wire_repos):
    repo = RecommendationRepository(wire_repos)
    repo.save(rec_date="2026-07-05", symbol="000660.KS", name="SK하이닉스",
              score=70.0, passed_conditions=[{"name": "PEG", "passed": True}],
              technical_signals=[{"name": "OBV", "value": "rising"}])
    repo.save(rec_date="2026-07-05", symbol="005930.KS", name="삼성전자",
              score=95.0, passed_conditions=[{"name": "ROE", "passed": True}],
              technical_signals=[{"name": "MACD", "value": "cross_up"}])

    resp = client.get("/api/v1/today/recommendations?date=2026-07-05")
    assert resp.status_code == 200
    body = resp.json()
    assert body["disclaimer"] == "교육·연구용 정보로 투자 권유가 아닙니다"
    assert body["count"] == 2
    symbols = [r["symbol"] for r in body["recommendations"]]
    assert symbols == ["005930.KS", "000660.KS"]  # score 내림차순
    assert body["recommendations"][0]["passed_conditions"][0]["name"] == "ROE"


def test_recommendations_default_uses_latest_date(wire_repos):
    repo = RecommendationRepository(wire_repos)
    repo.save(rec_date="2026-07-03", symbol="005930.KS", name="삼성전자",
              score=80.0, passed_conditions=[], technical_signals=[])
    repo.save(rec_date="2026-07-05", symbol="000660.KS", name="SK하이닉스",
              score=85.0, passed_conditions=[], technical_signals=[])

    resp = client.get("/api/v1/today/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == "2026-07-05"
    assert body["count"] == 1


def test_recommendations_empty_when_no_data(wire_repos):
    resp = client.get("/api/v1/today/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] is None
    assert body["count"] == 0
    assert body["recommendations"] == []
    assert body["disclaimer"] == "교육·연구용 정보로 투자 권유가 아닙니다"


# ── status: 기록된 작업 상태 노출 ──
def test_status_exposes_recorded_jobs(wire_repos):
    from datetime import date
    repo = JobRunRepository(wire_repos)
    today = date.today().isoformat()
    repo.record("news_crawl", today, "success", detail="12건 수집",
                finished_at="2026-07-05T07:00:00")
    repo.record("recommend", today, "failed", detail="데이터 부족",
                finished_at="2026-07-05T07:05:00")

    resp = client.get("/api/v1/today/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == today
    assert body["jobs"]["news_crawl"]["status"] == "success"
    assert body["jobs"]["news_crawl"]["detail"] == "12건 수집"
    assert body["jobs"]["recommend"]["status"] == "failed"
    assert body["jobs"]["recommend"]["detail"] == "데이터 부족"


# ── 500 은닉: 내부 예외 문자열 노출 금지 ──
def test_news_error_hides_internal_detail(wire_repos, monkeypatch):
    def boom():
        raise RuntimeError("secret db path /var/secret leaked")
    monkeypatch.setattr(today_routes, "_get_news_repo", boom)

    resp = client.get("/api/v1/today/news?date=2026-07-05")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "일시적인 오류가 발생했습니다"
    assert "secret" not in resp.json()["detail"]


def test_status_error_hides_internal_detail(wire_repos, monkeypatch):
    def boom():
        raise RuntimeError("internal stack trace")
    monkeypatch.setattr(today_routes, "_get_job_repo", boom)

    resp = client.get("/api/v1/today/status")
    assert resp.status_code == 500
    assert resp.json()["detail"] == "일시적인 오류가 발생했습니다"


# ── 추천: 분석 시점(analyzed_at) — 추천 작업의 성공 완료 시각 ──
def test_recommendations_include_analyzed_at(wire_repos):
    RecommendationRepository(wire_repos).save(
        rec_date="2026-07-05", symbol="005930.KS", name="삼성전자",
        score=95.0, passed_conditions=[], technical_signals=[])
    JobRunRepository(wire_repos).record(
        "recommendations", "2026-07-05", "success",
        detail='{"universe": 300, "filtered": 20, "saved": 10}',
        finished_at="2026-07-05T09:12:34")

    resp = client.get("/api/v1/today/recommendations?date=2026-07-05")
    assert resp.status_code == 200
    assert resp.json()["analyzed_at"] == "2026-07-05T09:12:34"


def test_recommendations_analyzed_at_null_without_job_record(wire_repos):
    """작업 기록이 없으면(수동 저장 등) analyzed_at은 None — 시각 조작 금지"""
    RecommendationRepository(wire_repos).save(
        rec_date="2026-07-05", symbol="005930.KS", name="삼성전자",
        score=95.0, passed_conditions=[], technical_signals=[])

    resp = client.get("/api/v1/today/recommendations?date=2026-07-05")
    assert resp.status_code == 200
    assert resp.json()["analyzed_at"] is None


# ── 온디맨드 추천 갱신 ("지금 매수 추천" 버튼) ──
def test_refresh_recommendations_runs_pipeline_and_records_job(wire_repos, monkeypatch):
    from app.services import recommender as reco_mod

    calls = {"n": 0}

    def fake_generate(repo, rec_date, **kwargs):
        calls["n"] += 1
        return {"universe": 10, "filtered": 3, "trend_rejected": 1, "saved": 2}

    monkeypatch.setattr(reco_mod, "generate_recommendations", fake_generate)
    # 상태 초기화 (다른 테스트 잔존 방지)
    today_routes._refresh_state.update(running=False, error=None, started_at=None)
    # 이 엔드포인트는 settings.DB_PATH를 직접 쓰므로 tmp DB로 교체
    monkeypatch.setattr(today_routes.settings, "DB_PATH", wire_repos, raising=False)

    resp = client.post("/api/v1/today/refresh-recommendations")
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"
    # TestClient는 응답 후 BackgroundTasks를 동기 완료시킴
    assert calls["n"] == 1
    assert today_routes._refresh_state["running"] is False
    assert JobRunRepository(wire_repos).has_succeeded(
        "recommendations", today_routes._today_str()) is True


def test_refresh_rejects_concurrent_run(wire_repos):
    today_routes._refresh_state.update(running=True, error=None,
                                       started_at="2026-07-07T09:00:00")
    try:
        resp = client.post("/api/v1/today/refresh-recommendations")
        assert resp.json()["status"] == "already_running"
    finally:
        today_routes._refresh_state.update(running=False)


def test_refresh_status_endpoint(wire_repos):
    today_routes._refresh_state.update(running=False, error=None, started_at=None)
    resp = client.get("/api/v1/today/refresh-status")
    assert resp.status_code == 200
    assert resp.json()["running"] is False


# ── 매도 진단 API ──
def test_sell_check_endpoint(monkeypatch):
    import numpy as np
    import pandas as pd
    from app.services import indicators

    closes = np.array([100.0 + i * 0.2 for i in range(300)])
    fake_df = pd.DataFrame({
        "open": closes, "high": closes * 1.01, "low": closes * 0.99,
        "close": closes, "volume": [1_000_000] * 300,
    }, index=pd.date_range("2025-01-02", periods=300, freq="B"))
    monkeypatch.setattr(indicators, "load_sample_data", lambda *a, **k: fake_df)

    resp = client.post("/api/v1/today/sell-check",
                       json={"symbol": "005930.KS", "entry_price": float(closes[-20])})
    assert resp.status_code == 200
    body = resp.json()
    assert body["action"] == "hold"
    assert body["levels"]["ma200"] > 0
    assert len(body["checks"]) == 4


def test_sell_check_rejects_invalid_price():
    resp = client.post("/api/v1/today/sell-check",
                       json={"symbol": "005930.KS", "entry_price": 0})
    assert resp.status_code == 422  # pydantic gt=0 검증


def test_recommendations_zero_today_does_not_fall_back_to_yesterday(wire_repos):
    """오늘 작업이 성공했고 결과가 0개면 어제 목록으로 폴백하지 않는다 (낡은 추천 오도 방지)."""
    RecommendationRepository(wire_repos).save(
        rec_date="2026-07-05", symbol="000660.KS", name="어제종목",
        score=90.0, passed_conditions=[], technical_signals=[])
    JobRunRepository(wire_repos).record(
        "recommendations", today_routes._today_str(), "success",
        detail='{"saved": 0}', finished_at="2026-07-07T09:00:00")

    resp = client.get("/api/v1/today/recommendations")
    assert resp.status_code == 200
    body = resp.json()
    assert body["date"] == today_routes._today_str()
    assert body["count"] == 0  # 어제 종목이 보이면 안 됨

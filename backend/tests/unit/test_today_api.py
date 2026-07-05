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

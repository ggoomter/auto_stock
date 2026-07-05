"""뉴스·추천 저장소 테스트"""
import pytest

from app.db.database import init_db


@pytest.fixture
def news_repo(tmp_path):
    from app.db.repositories import NewsRepository
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return NewsRepository(db_path)


@pytest.fixture
def reco_repo(tmp_path):
    from app.db.repositories import RecommendationRepository
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return RecommendationRepository(db_path)


# ── 시나리오 ①: save_article 신규 → id 반환 + 링크 저장, 같은 url 재저장 → None + 1건 유지
def test_save_article_new_returns_id_and_links(news_repo):
    article_id = news_repo.save_article(
        published_at="2026-07-05T09:00:00", source="연합뉴스",
        title="삼성전자 실적 발표", url="https://news.example/a1",
        summary="반도체 회복", sentiment="positive",
        symbols=["005930.KS", "000660.KS"],
    )
    assert isinstance(article_id, int)

    articles = news_repo.list_by_date("2026-07-05")
    assert len(articles) == 1
    assert set(articles[0]["symbols"]) == {"005930.KS", "000660.KS"}


def test_save_article_duplicate_url_returns_none_and_keeps_one(news_repo):
    first = news_repo.save_article(
        published_at="2026-07-05T09:00:00", source="연합뉴스",
        title="삼성전자 실적 발표", url="https://news.example/dup",
        summary="반도체 회복", sentiment="positive",
        symbols=["005930.KS"],
    )
    assert isinstance(first, int)

    second = news_repo.save_article(
        published_at="2026-07-05T10:00:00", source="연합뉴스",
        title="삼성전자 실적 발표(중복)", url="https://news.example/dup",
        summary="중복", sentiment="neutral",
        symbols=["000660.KS"],
    )
    assert second is None

    articles = news_repo.list_by_date("2026-07-05")
    assert len(articles) == 1
    # 링크도 건드리지 않음 — 최초 심볼만 유지
    assert articles[0]["symbols"] == ["005930.KS"]


# ── 시나리오 ②: list_by_date가 symbols 포함해 최신순 반환
def test_list_by_date_includes_symbols_and_orders_desc(news_repo):
    news_repo.save_article(
        published_at="2026-07-05T08:00:00", source="A", title="이른 기사",
        url="https://news.example/early", summary=None, sentiment="neutral",
        symbols=["005930.KS"],
    )
    news_repo.save_article(
        published_at="2026-07-05T18:00:00", source="B", title="늦은 기사",
        url="https://news.example/late", summary=None, sentiment="neutral",
        symbols=["000660.KS"],
    )
    # 다른 날짜는 제외되어야 함
    news_repo.save_article(
        published_at="2026-07-04T12:00:00", source="C", title="어제 기사",
        url="https://news.example/yesterday", summary=None, sentiment="neutral",
        symbols=[],
    )

    articles = news_repo.list_by_date("2026-07-05")
    assert len(articles) == 2
    assert articles[0]["title"] == "늦은 기사"  # 최신순
    assert articles[1]["title"] == "이른 기사"
    assert "symbols" in articles[0]


def test_list_for_symbol_and_count_by_date(news_repo):
    news_repo.save_article(
        published_at="2026-07-05T08:00:00", source="A", title="삼성 기사1",
        url="https://news.example/s1", summary=None, sentiment="neutral",
        symbols=["005930.KS"],
    )
    news_repo.save_article(
        published_at="2026-07-05T09:00:00", source="A", title="하이닉스 기사",
        url="https://news.example/h1", summary=None, sentiment="neutral",
        symbols=["000660.KS"],
    )
    samsung = news_repo.list_for_symbol("005930.KS")
    assert len(samsung) == 1
    assert samsung[0]["title"] == "삼성 기사1"
    assert news_repo.count_by_date("2026-07-05") == 2


# ── 시나리오 ③: RecommendationRepository.save 같은 (날짜,종목) 재저장 시 upsert
def test_recommendation_save_upserts_same_date_symbol(reco_repo):
    reco_repo.save(
        rec_date="2026-07-05", symbol="005930.KS", name="삼성전자", score=80.0,
        passed_conditions=[{"name": "ROE", "passed": True}],
        technical_signals=[{"name": "MACD", "value": "up"}],
    )
    reco_repo.save(
        rec_date="2026-07-05", symbol="005930.KS", name="삼성전자", score=92.5,
        passed_conditions=[{"name": "ROE", "passed": True}],
        technical_signals=[{"name": "RSI", "value": "oversold"}],
    )
    recs = reco_repo.list_by_date("2026-07-05")
    assert len(recs) == 1
    assert recs[0]["score"] == 92.5


# ── 시나리오 ④: list_by_date의 JSON 역직렬화 + score 내림차순
def test_recommendation_list_by_date_deserializes_and_orders_by_score(reco_repo):
    reco_repo.save(
        rec_date="2026-07-05", symbol="000660.KS", name="SK하이닉스", score=70.0,
        passed_conditions=[{"name": "PEG", "passed": True}],
        technical_signals=[{"name": "OBV", "value": "rising"}],
    )
    reco_repo.save(
        rec_date="2026-07-05", symbol="005930.KS", name="삼성전자", score=95.0,
        passed_conditions=[{"name": "ROE", "passed": True}],
        technical_signals=[{"name": "MACD", "value": "cross_up"}],
    )
    recs = reco_repo.list_by_date("2026-07-05")
    assert [r["symbol"] for r in recs] == ["005930.KS", "000660.KS"]  # 내림차순
    # JSON 역직렬화 확인 — list[dict]로 복원
    assert isinstance(recs[0]["passed_conditions"], list)
    assert recs[0]["passed_conditions"][0]["name"] == "ROE"
    assert isinstance(recs[0]["technical_signals"], list)


# ── 시나리오 ⑤: latest_date
def test_recommendation_latest_date(reco_repo):
    assert reco_repo.latest_date() is None
    reco_repo.save(
        rec_date="2026-07-03", symbol="005930.KS", name="삼성전자", score=80.0,
        passed_conditions=[], technical_signals=[],
    )
    reco_repo.save(
        rec_date="2026-07-05", symbol="000660.KS", name="SK하이닉스", score=85.0,
        passed_conditions=[], technical_signals=[],
    )
    assert reco_repo.latest_date() == "2026-07-05"

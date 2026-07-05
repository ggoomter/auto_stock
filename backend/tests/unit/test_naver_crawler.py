"""네이버 금융 주요뉴스 크롤러 테스트: parse_mainnews_html · collect_and_store.

- parse_mainnews_html: 고정 픽스처(naver_mainnews_sample.html)로 순수 파싱 검증(네트워크 금지).
- collect_and_store: fetch_mainnews를 patch하여 저장·링크·통계만 검증(네트워크 금지).
"""
import re
from pathlib import Path
from unittest.mock import patch

from app.services.naver_news import (
    NewsItem,
    collect_and_store,
    parse_mainnews_html,
)

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "naver_mainnews_sample.html"
)


def _load_fixture() -> str:
    return FIXTURE.read_text(encoding="utf-8")


# ── parse_mainnews_html: 구조 파싱 ────────────────────────────────
def test_parse_returns_items():
    items = parse_mainnews_html(_load_fixture())
    # 픽스처는 기사 5건(실제 4 + 엣지 1)
    assert len(items) == 5
    assert all(isinstance(it, NewsItem) for it in items)


def test_parse_titles_nonempty():
    items = parse_mainnews_html(_load_fixture())
    assert all(it.title.strip() for it in items)
    assert items[0].title == "美서 중소·중견기업 자금줄 역할…유럽 로드쇼엔 투자자들 북적"


def test_parse_urls_are_absolute():
    items = parse_mainnews_html(_load_fixture())
    for it in items:
        assert it.url.startswith("https://finance.naver.com/news/news_read.naver")
        assert "article_id=" in it.url


def test_parse_published_at_format():
    items = parse_mainnews_html(_load_fixture())
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$")
    for it in items:
        assert pattern.match(it.published_at), it.published_at
    # 초 단위는 절삭되어 분까지만
    assert items[0].published_at == "2026-07-05 19:10"


def test_parse_source_and_summary():
    items = parse_mainnews_html(_load_fixture())
    assert items[0].source == "서울경제"
    assert items[0].summary and "미들마켓론" in items[0].summary
    # summary 안에는 언론사/날짜 텍스트가 섞이지 않아야 함
    assert "서울경제" not in items[0].summary
    assert "2026-07-05" not in items[0].summary


def test_parse_edge_missing_press_and_date():
    items = parse_mainnews_html(_load_fixture())
    edge = items[-1]
    assert edge.title == "테스트 종목 신고가 돌파 소식"
    # 언론사 없음 → "naver" 폴백
    assert edge.source == "naver"
    # wdate 없음 → 수집 시각(YYYY-MM-DD HH:MM) 폴백
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$", edge.published_at)


def test_parse_empty_html_returns_empty_list():
    assert parse_mainnews_html("") == []
    assert parse_mainnews_html("<html><body>no news</body></html>") == []


# ── collect_and_store: fetch mock ────────────────────────────────
class _FakeRepo:
    """save_article를 흉내내는 인메모리 저장소 — url 중복 시 None."""

    def __init__(self, dup_urls=None):
        self.saved = []
        self._dup = set(dup_urls or [])
        self._next_id = 1

    def save_article(self, published_at, source, title, url, summary,
                     sentiment, symbols):
        if url in self._dup:
            return None
        self._dup.add(url)
        article_id = self._next_id
        self._next_id += 1
        self.saved.append(
            dict(id=article_id, published_at=published_at, source=source,
                 title=title, url=url, summary=summary, sentiment=sentiment,
                 symbols=symbols)
        )
        return article_id


def _items():
    return [
        NewsItem(title="삼성전자 신고가 돌파", url="https://finance.naver.com/a1",
                 source="서울경제", published_at="2026-07-05 19:10",
                 summary="요약1"),
        NewsItem(title="카카오 급락 소송 우려", url="https://finance.naver.com/a2",
                 source="한국경제", published_at="2026-07-05 18:46",
                 summary="요약2"),
    ]


def test_collect_and_store_stats_and_links():
    repo = _FakeRepo()
    name_map = {"삼성전자": "005930.KS", "카카오": "035720.KS"}
    with patch("app.services.naver_news.fetch_mainnews", return_value=_items()):
        result = collect_and_store(repo, name_map, pages=2)

    assert result == {"fetched": 2, "inserted": 2, "linked_symbols": 2}
    # 감성/종목 매칭이 저장 시 반영됐는지
    assert repo.saved[0]["symbols"] == ["005930.KS"]
    assert repo.saved[0]["sentiment"] == "positive"
    assert repo.saved[1]["symbols"] == ["035720.KS"]
    assert repo.saved[1]["sentiment"] == "negative"


def test_collect_and_store_skips_duplicates():
    repo = _FakeRepo(dup_urls={"https://finance.naver.com/a1"})
    name_map = {"삼성전자": "005930.KS", "카카오": "035720.KS"}
    with patch("app.services.naver_news.fetch_mainnews", return_value=_items()):
        result = collect_and_store(repo, name_map, pages=2)

    # a1은 중복이라 inserted 제외, linked_symbols도 신규 저장분만 카운트
    assert result["fetched"] == 2
    assert result["inserted"] == 1
    assert result["linked_symbols"] == 1

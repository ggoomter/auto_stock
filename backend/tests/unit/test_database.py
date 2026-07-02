"""DB 스키마 초기화 테스트"""
import sqlite3


def test_init_db_creates_all_tables(tmp_path):
    from app.db.database import init_db, get_connection

    db_path = str(tmp_path / "test.db")
    init_db(db_path)

    conn = get_connection(db_path)
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()

    table_names = {row["name"] for row in rows}
    expected = {
        "paper_positions", "paper_trades", "portfolio_snapshots",
        "news_articles", "news_stock_links", "recommendations", "job_runs",
    }
    assert expected.issubset(table_names)


def test_init_db_is_idempotent(tmp_path):
    from app.db.database import init_db

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    init_db(db_path)  # 두 번 호출해도 예외 없어야 함


def test_get_connection_uses_row_factory(tmp_path):
    from app.db.database import init_db, get_connection

    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO job_runs (job_name, run_date, status, finished_at) "
        "VALUES ('t', '2026-07-02', 'success', '2026-07-02T10:00:00')"
    )
    row = conn.execute("SELECT job_name FROM job_runs").fetchone()
    conn.close()
    assert row["job_name"] == "t"  # dict 스타일 접근 = Row factory 확인

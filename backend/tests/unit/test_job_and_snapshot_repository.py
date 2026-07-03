"""작업 기록·스냅샷 저장소 테스트"""
import pytest

from app.db.database import init_db


@pytest.fixture
def db_path(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def test_job_run_record_and_check(db_path):
    from app.db.repositories import JobRunRepository
    repo = JobRunRepository(db_path)

    assert repo.has_succeeded("news_crawl", "2026-07-02") is False

    repo.record("news_crawl", "2026-07-02", "failure",
                detail="timeout", finished_at="2026-07-02T09:00:00")
    assert repo.has_succeeded("news_crawl", "2026-07-02") is False

    # 실패 후 재시도 성공 → REPLACE 되어야 함
    repo.record("news_crawl", "2026-07-02", "success",
                finished_at="2026-07-02T09:05:00")
    assert repo.has_succeeded("news_crawl", "2026-07-02") is True


def test_snapshot_save_is_upsert(db_path):
    from app.db.repositories import SnapshotRepository
    repo = SnapshotRepository(db_path)

    repo.save("2026-07-02", total_value=10_000_000, cash=5_000_000,
              positions_value=5_000_000)
    repo.save("2026-07-02", total_value=10_100_000, cash=5_000_000,
              positions_value=5_100_000)  # 같은 날 재저장

    snapshots = repo.list_all()
    assert len(snapshots) == 1
    assert snapshots[0]["total_value"] == 10_100_000

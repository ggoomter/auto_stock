"""
저장소 계층: 호출마다 커넥션을 열고 닫는다 (스레드 안전, 단순함 우선).
"""
import json

from .database import get_connection


class PaperTradingRepository:
    """모의투자 포지션·체결 영속화"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def open_position(self, symbol: str, quantity: int, entry_price: float,
                      strategy: str, stop_loss: float, take_profit: float,
                      entry_at: str) -> int:
        conn = get_connection(self._db_path)
        try:
            cur = conn.execute(
                "INSERT INTO paper_positions "
                "(symbol, quantity, entry_price, entry_at, strategy, "
                " stop_loss, take_profit, highest_price, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')",
                (symbol, quantity, entry_price, entry_at, strategy,
                 stop_loss, take_profit, entry_price),
            )
            position_id = cur.lastrowid
            conn.execute(
                "INSERT INTO paper_trades "
                "(position_id, symbol, side, quantity, price, executed_at, strategy, reason) "
                "VALUES (?, ?, 'buy', ?, ?, ?, ?, '진입')",
                (position_id, symbol, quantity, entry_price, entry_at, strategy),
            )
            conn.commit()
            return position_id
        finally:
            conn.close()

    def close_position(self, position_id: int, exit_price: float,
                       exit_reason: str, exit_at: str) -> None:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT symbol, quantity, strategy FROM paper_positions WHERE id = ?",
                (position_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"포지션 없음: id={position_id}")
            conn.execute(
                "UPDATE paper_positions "
                "SET status='closed', exit_price=?, exit_at=?, exit_reason=? "
                "WHERE id = ?",
                (exit_price, exit_at, exit_reason, position_id),
            )
            conn.execute(
                "INSERT INTO paper_trades "
                "(position_id, symbol, side, quantity, price, executed_at, strategy, reason) "
                "VALUES (?, ?, 'sell', ?, ?, ?, ?, ?)",
                (position_id, row["symbol"], row["quantity"], exit_price,
                 exit_at, row["strategy"], exit_reason),
            )
            conn.commit()
        finally:
            conn.close()

    def list_open_positions(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, symbol, quantity, entry_price, entry_at, strategy, "
                "       stop_loss, take_profit, highest_price "
                "FROM paper_positions WHERE status = 'open' ORDER BY id",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def update_stops(self, position_id: int, stop_loss: float,
                     highest_price: float) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "UPDATE paper_positions SET stop_loss=?, highest_price=? WHERE id=?",
                (stop_loss, highest_price, position_id),
            )
            conn.commit()
        finally:
            conn.close()

    def total_realized_pnl(self) -> float:
        """청산 완료(closed) 포지션의 누적 실현손익 — 재시작해도 유지되는 진실의 원천"""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT COALESCE(SUM((exit_price - entry_price) * quantity), 0) AS pnl "
                "FROM paper_positions WHERE status='closed'",
            ).fetchone()
            return float(row["pnl"]) if row is not None else 0.0
        finally:
            conn.close()

    def list_trades(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, position_id, symbol, side, quantity, price, "
                "       executed_at, strategy, reason "
                "FROM paper_trades ORDER BY id",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class JobRunRepository:
    """일별 작업 실행 기록 — '오늘 이미 돌았나' 판단 근거"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def record(self, job_name: str, run_date: str, status: str,
               detail: str | None = None, finished_at: str = "") -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO job_runs "
                "(job_name, run_date, status, detail, finished_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (job_name, run_date, status, detail, finished_at),
            )
            conn.commit()
        finally:
            conn.close()

    def has_succeeded(self, job_name: str, run_date: str) -> bool:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT 1 FROM job_runs "
                "WHERE job_name=? AND run_date=? AND status='success'",
                (job_name, run_date),
            ).fetchone()
            return row is not None
        finally:
            conn.close()

    def get_runs(self, run_date: str) -> list[dict]:
        """해당 날짜에 기록된 작업 실행 목록 — 프론트 '수집 중/실패 사유' 표시용.
        각 dict 키: job_name, status, detail, finished_at."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT job_name, status, detail, finished_at "
                "FROM job_runs WHERE run_date=? ORDER BY job_name",
                (run_date,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class SnapshotRepository:
    """일별 가상 잔고 스냅샷 — 모의투자 수익 곡선의 원천"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def save(self, snapshot_date: str, total_value: float, cash: float,
             positions_value: float) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO portfolio_snapshots "
                "(snapshot_date, total_value, cash, positions_value) "
                "VALUES (?, ?, ?, ?)",
                (snapshot_date, total_value, cash, positions_value),
            )
            conn.commit()
        finally:
            conn.close()

    def list_all(self) -> list[dict]:
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT snapshot_date, total_value, cash, positions_value "
                "FROM portfolio_snapshots ORDER BY snapshot_date",
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()


class NewsRepository:
    """뉴스 기사·종목 연결 영속화 (url UNIQUE로 중복 방지)"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def save_article(self, published_at: str, source: str, title: str, url: str,
                     summary: str | None, sentiment: str,
                     symbols: list[str]) -> int | None:
        """신규 삽입 시 article_id 반환 + 종목 링크 저장. 이미 존재(무시)면 None."""
        conn = get_connection(self._db_path)
        try:
            cur = conn.execute(
                "INSERT OR IGNORE INTO news_articles "
                "(published_at, source, title, url, summary, sentiment) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (published_at, source, title, url, summary, sentiment),
            )
            # rowcount==0 이면 url 중복으로 무시됨 → 링크도 건드리지 않고 None 반환
            if cur.rowcount == 0:
                conn.rollback()
                return None
            article_id = cur.lastrowid
            for symbol in symbols:
                conn.execute(
                    "INSERT OR IGNORE INTO news_stock_links (article_id, symbol) "
                    "VALUES (?, ?)",
                    (article_id, symbol),
                )
            conn.commit()
            return article_id
        finally:
            conn.close()

    def _attach_symbols(self, conn, rows: list) -> list[dict]:
        """각 기사 dict에 연결된 종목코드 리스트를 붙인다."""
        result = []
        for r in rows:
            article = dict(r)
            links = conn.execute(
                "SELECT symbol FROM news_stock_links WHERE article_id = ? "
                "ORDER BY symbol",
                (article["id"],),
            ).fetchall()
            article["symbols"] = [lr["symbol"] for lr in links]
            result.append(article)
        return result

    def list_by_date(self, date_prefix: str) -> list[dict]:
        """published_at LIKE 'YYYY-MM-DD%' — symbols 포함, 최신순."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, published_at, source, title, url, summary, sentiment "
                "FROM news_articles WHERE published_at LIKE ? "
                "ORDER BY published_at DESC, id DESC",
                (date_prefix + "%",),
            ).fetchall()
            return self._attach_symbols(conn, rows)
        finally:
            conn.close()

    def list_for_symbol(self, symbol: str, limit: int = 20) -> list[dict]:
        """특정 종목에 연결된 기사 — symbols 포함, 최신순."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT a.id, a.published_at, a.source, a.title, a.url, "
                "       a.summary, a.sentiment "
                "FROM news_articles a "
                "JOIN news_stock_links l ON l.article_id = a.id "
                "WHERE l.symbol = ? "
                "ORDER BY a.published_at DESC, a.id DESC LIMIT ?",
                (symbol, limit),
            ).fetchall()
            return self._attach_symbols(conn, rows)
        finally:
            conn.close()

    def count_by_date(self, date_prefix: str) -> int:
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM news_articles "
                "WHERE published_at LIKE ?",
                (date_prefix + "%",),
            ).fetchone()
            return int(row["cnt"]) if row is not None else 0
        finally:
            conn.close()


class RecommendationRepository:
    """일별 추천 종목 영속화 ((rec_date, symbol) UNIQUE로 upsert)"""

    def __init__(self, db_path: str | None = None):
        self._db_path = db_path

    def save(self, rec_date: str, symbol: str, name: str | None, score: float,
             passed_conditions: list[dict], technical_signals: list[dict]) -> None:
        conn = get_connection(self._db_path)
        try:
            conn.execute(
                "INSERT OR REPLACE INTO recommendations "
                "(rec_date, symbol, name, score, passed_conditions, technical_signals) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (rec_date, symbol, name, score,
                 json.dumps(passed_conditions, ensure_ascii=False),
                 json.dumps(technical_signals, ensure_ascii=False)),
            )
            conn.commit()
        finally:
            conn.close()

    def list_by_date(self, rec_date: str) -> list[dict]:
        """score 내림차순. JSON 컬럼은 json.loads 해서 list로 반환."""
        conn = get_connection(self._db_path)
        try:
            rows = conn.execute(
                "SELECT id, rec_date, symbol, name, score, "
                "       passed_conditions, technical_signals "
                "FROM recommendations WHERE rec_date = ? "
                "ORDER BY score DESC, symbol",
                (rec_date,),
            ).fetchall()
            result = []
            for r in rows:
                rec = dict(r)
                rec["passed_conditions"] = json.loads(rec["passed_conditions"]) \
                    if rec["passed_conditions"] else []
                rec["technical_signals"] = json.loads(rec["technical_signals"]) \
                    if rec["technical_signals"] else []
                result.append(rec)
            return result
        finally:
            conn.close()

    def latest_date(self) -> str | None:
        """가장 최근 rec_date. 데이터 없으면 None."""
        conn = get_connection(self._db_path)
        try:
            row = conn.execute(
                "SELECT MAX(rec_date) AS d FROM recommendations",
            ).fetchone()
            return row["d"] if row is not None and row["d"] is not None else None
        finally:
            conn.close()

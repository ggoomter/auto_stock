"""
저장소 계층: 호출마다 커넥션을 열고 닫는다 (스레드 안전, 단순함 우선).
"""
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

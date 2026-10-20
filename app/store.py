import json
import sqlite3
import threading
import time
from typing import Any, Optional


class Store:
    """SQLite store for traces (observability) and escalation tickets."""

    def __init__(self, path: str):
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS traces(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user_id TEXT, message TEXT,
                    intent TEXT, action TEXT, confidence REAL, reason TEXT, retrieved TEXT,
                    cited TEXT, latency_ms REAL, model TEXT);
                CREATE TABLE IF NOT EXISTS tickets(
                    id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, user_id TEXT, message TEXT,
                    reason TEXT, intent TEXT, status TEXT DEFAULT 'open');
                """
            )

    def add_trace(self, **f: Any) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO traces(ts,user_id,message,intent,action,confidence,reason,retrieved,cited,latency_ms,model)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    time.time(), f["user_id"], f["message"], f["intent"], f["action"], f["confidence"],
                    f.get("reason"), json.dumps(f.get("retrieved", [])), json.dumps(f.get("cited", [])),
                    f["latency_ms"], f.get("model", ""),
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def add_ticket(self, user_id: str, message: str, reason: str, intent: str) -> int:
        with self._lock:
            cur = self._conn.execute(
                "INSERT INTO tickets(ts,user_id,message,reason,intent) VALUES(?,?,?,?,?)",
                (time.time(), user_id, message, reason, intent),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    @staticmethod
    def _parse_trace(row: sqlite3.Row) -> dict:
        d = dict(row)
        for key in ("retrieved", "cited"):
            if isinstance(d.get(key), str):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d

    def list_traces(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM traces ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [self._parse_trace(r) for r in rows]

    def get_trace(self, trace_id: int) -> Optional[dict]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
        return self._parse_trace(row) if row else None

    def list_tickets(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM tickets ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._lock:
            r = self._conn.execute(
                "SELECT COUNT(*) n, SUM(action='AUTO_ANSWER') auto, SUM(action='ESCALATE') esc,"
                " AVG(latency_ms) avg_ms FROM traces"
            ).fetchone()
            reasons = self._conn.execute(
                "SELECT reason, COUNT(*) c FROM traces WHERE action='ESCALATE' GROUP BY reason ORDER BY c DESC LIMIT 8"
            ).fetchall()
        n = r["n"] or 0
        return {
            "total": n,
            "auto_answered": r["auto"] or 0,
            "escalated": r["esc"] or 0,
            "auto_rate": round((r["auto"] or 0) / n, 3) if n else 0.0,
            "avg_latency_ms": round(r["avg_ms"] or 0, 1),
            "top_escalation_reasons": [{"reason": x["reason"], "count": x["c"]} for x in reasons],
        }

from __future__ import annotations

import contextlib
import json
import pathlib
import sqlite3
from typing import Any, Iterator


class BugDB(contextlib.AbstractContextManager["BugDB"]):
    def __init__(self, path: pathlib.Path) -> None:
        self._path = path
        self._conn: sqlite3.Connection | None = None

    def __enter__(self) -> "BugDB":
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._path)
        self._conn.row_factory = sqlite3.Row
        self._init()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._conn is not None:
            self._conn.commit()
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise RuntimeError("DB not opened")
        return self._conn

    def _init(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
              id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL,
              seed_id TEXT,
              mutation_trace TEXT,
              ref_text TEXT NOT NULL,
              hyp_text TEXT NOT NULL,
              audio_path_wav TEXT,
              audio_path_mp3 TEXT,
              duration_sec REAL,
              lang_guess TEXT,
              cer REAL,
              wer REAL,
              len_ratio REAL,
              critical_error_score REAL,
              score_total REAL,
              tags TEXT,
              signature TEXT,
              cluster_id TEXT,
              llm_summary TEXT,
              status TEXT NOT NULL
            )
            """
        )
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_score ON cases(score_total)")

    def upsert_case(self, row: dict[str, Any]) -> None:
        cols = list(row.keys())
        placeholders = ", ".join("?" for _ in cols)
        assignments = ", ".join(f"{c}=excluded.{c}" for c in cols if c != "id")
        sql = f"INSERT INTO cases ({', '.join(cols)}) VALUES ({placeholders}) ON CONFLICT(id) DO UPDATE SET {assignments}"
        values = [row[c] for c in cols]
        self.conn.execute(sql, values)

    def iter_cases(self, *, status: str | None = None) -> Iterator[dict[str, Any]]:
        if status is None:
            cur = self.conn.execute("SELECT * FROM cases ORDER BY score_total DESC")
        else:
            cur = self.conn.execute(
                "SELECT * FROM cases WHERE status=? ORDER BY score_total DESC",
                (status,),
            )
        for r in cur:
            d = dict(r)
            for k in ("tags", "signature"):
                if d.get(k):
                    d[k] = json.loads(d[k])
            yield d

    def list_cases_minimal(self, *, status: str) -> list[dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, ref_text, hyp_text, tags, signature, cluster_id, score_total FROM cases WHERE status=?",
            (status,),
        )
        rows: list[dict[str, Any]] = []
        for r in cur:
            d = dict(r)
            for k in ("tags", "signature"):
                if d.get(k):
                    d[k] = json.loads(d[k])
            rows.append(d)
        return rows

    def count_by_status(self) -> dict[str, int]:
        cur = self.conn.execute("SELECT status, COUNT(*) AS c FROM cases GROUP BY status")
        return {r["status"]: int(r["c"]) for r in cur}

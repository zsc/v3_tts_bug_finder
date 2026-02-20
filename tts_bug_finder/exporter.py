from __future__ import annotations

import json
import pathlib

from .db import BugDB


def export_cases(*, db_path: pathlib.Path, out_path: pathlib.Path, fmt: str, status: str) -> None:
    if fmt != "jsonl":
        raise ValueError(f"Unsupported export format: {fmt}")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with BugDB(db_path) as db:
        rows = db.iter_cases(status=status)

        with out_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {out_path}")


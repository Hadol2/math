"""SQLite DB 헬퍼 — 기출문제 저장/조회."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional

DB_PATH = Path(__file__).parent.parent / "data" / "problems.db"

UNITS = ["수학I", "수학II", "미적분", "확률과통계", "기하"]
DIFFICULTIES = ["상", "중", "하"]
EXAM_TYPES = ["수능", "6월", "9월"]

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS problems (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    year        INTEGER NOT NULL,
    exam_type   TEXT    NOT NULL CHECK(exam_type IN ('수능','6월','9월')),
    number      INTEGER NOT NULL,
    score       INTEGER NOT NULL DEFAULT 3,

    image_path  TEXT    NOT NULL,

    text        TEXT,
    latex       TEXT,
    choices     TEXT,
    answer      TEXT,
    has_figure  INTEGER NOT NULL DEFAULT 0,

    unit        TEXT,
    difficulty  TEXT    CHECK(difficulty IN ('상','중','하')),
    notes       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_year       ON problems(year);
CREATE INDEX IF NOT EXISTS idx_exam_type  ON problems(exam_type);
CREATE INDEX IF NOT EXISTS idx_unit       ON problems(unit);
CREATE INDEX IF NOT EXISTS idx_difficulty ON problems(difficulty);
"""


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as con:
        con.executescript(_SCHEMA)


# ── CRUD ──────────────────────────────────────────────────────────────

def insert_problem(data: dict[str, Any]) -> int:
    sql = """
        INSERT INTO problems
            (year, exam_type, number, score, image_path,
             text, latex, choices, answer, has_figure,
             unit, difficulty, notes)
        VALUES
            (:year, :exam_type, :number, :score, :image_path,
             :text, :latex, :choices, :answer, :has_figure,
             :unit, :difficulty, :notes)
    """
    row = {
        "year":       data["year"],
        "exam_type":  data["exam_type"],
        "number":     data["number"],
        "score":      data.get("score", 3),
        "image_path": data["image_path"],
        "text":       data.get("text"),
        "latex":      data.get("latex"),
        "choices":    json.dumps(data["choices"], ensure_ascii=False) if data.get("choices") else None,
        "answer":     data.get("answer"),
        "has_figure": int(bool(data.get("has_figure", False))),
        "unit":       data.get("unit"),
        "difficulty": data.get("difficulty"),
        "notes":      data.get("notes"),
    }
    with _conn() as con:
        cur = con.execute(sql, row)
        return cur.lastrowid


def get_problem(problem_id: int) -> Optional[dict]:
    with _conn() as con:
        row = con.execute("SELECT * FROM problems WHERE id=?", (problem_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_problem(problem_id: int, data: dict[str, Any]) -> bool:
    fields = {k: v for k, v in data.items() if k in (
        "year", "exam_type", "number", "score",
        "text", "latex", "choices", "answer", "has_figure",
        "unit", "difficulty", "notes",
    )}
    if "choices" in fields and isinstance(fields["choices"], list):
        fields["choices"] = json.dumps(fields["choices"], ensure_ascii=False)
    if "has_figure" in fields:
        fields["has_figure"] = int(bool(fields["has_figure"]))
    if not fields:
        return False
    set_clause = ", ".join(f"{k}=:{k}" for k in fields)
    fields["_id"] = problem_id
    with _conn() as con:
        cur = con.execute(f"UPDATE problems SET {set_clause} WHERE id=:_id", fields)
    return cur.rowcount > 0


def delete_problem(problem_id: int) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM problems WHERE id=?", (problem_id,))
    return cur.rowcount > 0


def list_problems(
    year: Optional[int] = None,
    exam_type: Optional[str] = None,
    unit: Optional[str] = None,
    difficulty: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[list[dict], int]:
    where, params = [], []
    if year:
        where.append("year=?"); params.append(year)
    if exam_type:
        where.append("exam_type=?"); params.append(exam_type)
    if unit:
        where.append("unit=?"); params.append(unit)
    if difficulty:
        where.append("difficulty=?"); params.append(difficulty)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    with _conn() as con:
        total = con.execute(f"SELECT COUNT(*) FROM problems {where_sql}", params).fetchone()[0]
        rows  = con.execute(
            f"SELECT * FROM problems {where_sql} ORDER BY year DESC, exam_type, number LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
    return [_row_to_dict(r) for r in rows], total


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    if d.get("choices"):
        try:
            d["choices"] = json.loads(d["choices"])
        except Exception:
            pass
    d["has_figure"] = bool(d.get("has_figure", 0))
    return d

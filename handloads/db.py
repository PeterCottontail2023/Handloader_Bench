"""Data access layer for the handloading records database.

SQLite file lives alongside this script as handloads.db (created on first
run) -- except when frozen (PyInstaller), where that would put it inside the
onefile build's temporary extraction directory, wiped after every run. See
_user_data_dir() below.
No external dependencies -- just the Python standard library.
"""
from __future__ import annotations

import csv
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any, Iterable


def _app_dir() -> Path:
    """Where this module's bundled read-only assets (schema.sql) live."""
    if getattr(sys, "frozen", False):
        # PyInstaller onefile: datas were extracted under _MEIPASS, mirroring
        # the ("handloads/schema.sql", "handloads") entry in the .spec file.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)) / "handloads"
    return Path(__file__).resolve().parent


def _user_data_dir() -> Path:
    """Where the actual database lives -- must survive between runs, so it
    can never be the frozen build's extraction dir (see _app_dir)."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA") or Path.home())
        data_dir = base / "HandloaderBench"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
DB_PATH = _user_data_dir() / "handloads.db"
SCHEMA_PATH = APP_DIR / "schema.sql"

# Single source of truth for each table's extra (non-id/timestamp) columns and
# their SQL types. init_db() uses this both to know what add_load/add_firearm
# may write, and to ALTER TABLE in any missing ones into an existing database
# -- so adding a field later (like "comments") doesn't require deleting and
# re-importing real data.
LOAD_COLUMN_TYPES: dict[str, str] = {
    "firearm_id": "INTEGER",
    "date_loaded": "TEXT",
    "date_tested": "TEXT",
    "caliber": "TEXT",
    "status": "TEXT",
    "case_mfr": "TEXT",
    "case_lot": "TEXT",
    "times_fired": "INTEGER",
    "primer_mfr": "TEXT",
    "primer_type": "TEXT",
    "powder_mfr": "TEXT",
    "powder_type": "TEXT",
    "charge_weight_gr": "REAL",
    "bullet_mfr": "TEXT",
    "bullet_weight_gr": "REAL",
    "bullet_type": "TEXT",
    "bullet_diameter_in": "REAL",
    "bullet_length_in": "REAL",
    "ballistic_coefficient": "REAL",
    "bc_drag_model": "TEXT",
    "coal_in": "REAL",
    "seating_depth_note": "TEXT",
    "crimp": "TEXT",
    "num_rounds": "INTEGER",
    "avg_velocity_fps": "REAL",
    "sd_fps": "REAL",
    "es_fps": "REAL",
    "group_size_in": "REAL",
    "group_distance_yd": "REAL",
    "pressure_psi": "REAL",
    "load_density_pct": "REAL",
    "pressure_signs": "TEXT",
    "temperature_f": "REAL",
    "weather_notes": "TEXT",
    "notes": "TEXT",
    "comments": "TEXT",
}
LOAD_COLUMNS = list(LOAD_COLUMN_TYPES)

FIREARM_COLUMN_TYPES: dict[str, str] = {
    "name": "TEXT",
    "make": "TEXT",
    "model": "TEXT",
    "caliber": "TEXT",
    "barrel_length_in": "REAL",
    "twist_rate": "TEXT",
    "action_type": "TEXT",
    "notes": "TEXT",
}
FIREARM_COLUMNS = list(FIREARM_COLUMN_TYPES)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate_columns(conn: sqlite3.Connection, table: str, column_types: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    for col, sqltype in column_types.items():
        if col not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {sqltype}")


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        _migrate_columns(conn, "loads", LOAD_COLUMN_TYPES)
        _migrate_columns(conn, "firearms", FIREARM_COLUMN_TYPES)


# ---------------------------------------------------------------- firearms --

def list_firearms() -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute("SELECT * FROM firearms ORDER BY name").fetchall()


def get_firearm(firearm_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM firearms WHERE id = ?", (firearm_id,)
        ).fetchone()


def add_firearm(values: dict[str, Any]) -> int:
    cols = [c for c in FIREARM_COLUMNS if c in values]
    placeholders = ", ".join("?" for _ in cols)
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO firearms ({', '.join(cols)}) VALUES ({placeholders})",
            [values[c] for c in cols],
        )
        return cur.lastrowid


def update_firearm(firearm_id: int, values: dict[str, Any]) -> None:
    cols = [c for c in FIREARM_COLUMNS if c in values]
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    with connect() as conn:
        conn.execute(
            f"UPDATE firearms SET {set_clause} WHERE id = ?",
            [values[c] for c in cols] + [firearm_id],
        )


def delete_firearm(firearm_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM firearms WHERE id = ?", (firearm_id,))


# ------------------------------------------------------------------ loads --

def list_loads(search: str | None = None) -> list[sqlite3.Row]:
    query = """
        SELECT loads.*, firearms.name AS firearm_name
        FROM loads
        LEFT JOIN firearms ON firearms.id = loads.firearm_id
    """
    params: list[Any] = []
    if search:
        query += """
            WHERE firearms.name LIKE ? OR loads.caliber LIKE ?
               OR loads.bullet_mfr LIKE ? OR loads.bullet_type LIKE ?
               OR loads.powder_mfr LIKE ? OR loads.powder_type LIKE ?
               OR loads.notes LIKE ?
        """
        like = f"%{search}%"
        params = [like] * 7
    query += " ORDER BY COALESCE(loads.date_tested, loads.date_loaded) DESC, loads.id DESC"
    with connect() as conn:
        return conn.execute(query, params).fetchall()


def get_load(load_id: int) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute("SELECT * FROM loads WHERE id = ?", (load_id,)).fetchone()


def add_load(values: dict[str, Any]) -> int:
    cols = [c for c in LOAD_COLUMNS if c in values]
    placeholders = ", ".join("?" for _ in cols)
    with connect() as conn:
        cur = conn.execute(
            f"INSERT INTO loads ({', '.join(cols)}) VALUES ({placeholders})",
            [values[c] for c in cols],
        )
        return cur.lastrowid


def update_load(load_id: int, values: dict[str, Any]) -> None:
    cols = [c for c in LOAD_COLUMNS if c in values]
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    with connect() as conn:
        conn.execute(
            f"UPDATE loads SET {set_clause}, updated_at = datetime('now') WHERE id = ?",
            [values[c] for c in cols] + [load_id],
        )


def delete_load(load_id: int) -> None:
    with connect() as conn:
        conn.execute("DELETE FROM loads WHERE id = ?", (load_id,))


# ------------------------------------------------------------ shot strings --

def list_shot_strings(load_id: int) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM shot_strings WHERE load_id = ? ORDER BY shot_number",
            (load_id,),
        ).fetchall()


def set_shot_strings(load_id: int, velocities: Iterable[float]) -> None:
    """Replace all shot strings for a load and recompute avg/SD/ES onto the load row."""
    velocities = list(velocities)
    with connect() as conn:
        conn.execute("DELETE FROM shot_strings WHERE load_id = ?", (load_id,))
        conn.executemany(
            "INSERT INTO shot_strings (load_id, shot_number, velocity_fps) VALUES (?, ?, ?)",
            [(load_id, i + 1, v) for i, v in enumerate(velocities)],
        )
        if velocities:
            avg = sum(velocities) / len(velocities)
            variance = sum((v - avg) ** 2 for v in velocities) / len(velocities)
            sd = variance ** 0.5
            es = max(velocities) - min(velocities)
            conn.execute(
                "UPDATE loads SET avg_velocity_fps = ?, sd_fps = ?, es_fps = ?, "
                "num_rounds = ?, updated_at = datetime('now') WHERE id = ?",
                (avg, sd, es, len(velocities), load_id),
            )


# ------------------------------------------------------------------- export --

def export_csv(path: Path) -> int:
    rows = list_loads()
    if not rows:
        path.write_text("")
        return 0
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(dict(row))
    return len(rows)

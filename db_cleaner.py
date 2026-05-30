"""
db_cleaner.py — auto-cleans a SQLite database after upload.

Operations (in order):
  1. Remove fully empty rows (every column is NULL or empty string)
  2. Strip leading/trailing whitespace from text columns
  3. Standardise column names (lowercase, underscores — no spaces or special chars)

Public function:
  - clean(db_path) → dict
"""

import re
import sqlite3


def clean(db_path: str) -> dict:
    """
    Clean a SQLite database in-place and return a summary of changes.

    Args:
        db_path: Path to the SQLite .db file to clean.

    Returns:
        A dict with:
        {
            "empty_rows_removed": int,
            "cells_stripped":     int,
            "columns_renamed":    list[str],   # "table.old → new"
        }

    Raises:
        sqlite3.DatabaseError: if the file is not a valid SQLite database.
    """
    report = {"empty_rows_removed": 0, "cells_stripped": 0, "columns_renamed": []}

    print(f"[db_cleaner] Cleaning '{db_path}' ...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}');")
        col_rows = cursor.fetchall()
        columns = [row[1] for row in col_rows]

        _remove_empty_rows(cursor, table, columns, report)
        _strip_whitespace(cursor, table, col_rows, report)
        _rename_columns(cursor, table, columns, report)

    conn.commit()
    conn.close()

    print(
        f"[db_cleaner] Done — {report['empty_rows_removed']} empty rows removed, "
        f"{report['cells_stripped']} cells stripped, "
        f"{len(report['columns_renamed'])} columns renamed."
    )
    return report


def _standardise(name: str) -> str:
    """Convert a column name to lowercase snake_case."""
    name = name.strip().lower()
    name = re.sub(r"[\s\-]+", "_", name)
    name = re.sub(r"[^\w]", "", name)
    return name or "col"


def _remove_empty_rows(cursor, table: str, columns: list, report: dict) -> None:
    """Delete rows where every column is NULL or an empty/whitespace-only string."""
    if not columns:
        return
    conditions = " AND ".join(
        f'("{col}" IS NULL OR TRIM(CAST("{col}" AS TEXT)) = "")'
        for col in columns
    )
    cursor.execute(f'DELETE FROM "{table}" WHERE {conditions};')
    removed = cursor.rowcount
    report["empty_rows_removed"] += removed
    if removed:
        print(f"[db_cleaner]   {table}: removed {removed} empty row(s).")


def _strip_whitespace(cursor, table: str, col_rows: list, report: dict) -> None:
    """Trim leading/trailing whitespace from text-like columns."""
    for row in col_rows:
        col_name = row[1]
        col_type = (row[2] or "").upper()
        is_text = any(
            t in col_type for t in ("TEXT", "CHAR", "CLOB", "VARCHAR")
        ) or col_type == ""
        if not is_text:
            continue
        cursor.execute(
            f'UPDATE "{table}" '
            f'SET "{col_name}" = TRIM("{col_name}") '
            f'WHERE "{col_name}" IS NOT NULL AND "{col_name}" != TRIM("{col_name}");'
        )
        stripped = cursor.rowcount
        report["cells_stripped"] += stripped
        if stripped:
            print(f"[db_cleaner]   {table}.{col_name}: stripped {stripped} cell(s).")


def _rename_columns(cursor, table: str, columns: list, report: dict) -> None:
    """Rename columns that don't conform to lowercase snake_case."""
    new_names = [_standardise(col) for col in columns]

    # Resolve collisions: if two columns map to the same new name, append a counter
    seen: dict[str, int] = {}
    resolved = []
    for name in new_names:
        if name in seen:
            seen[name] += 1
            resolved.append(f"{name}_{seen[name]}")
        else:
            seen[name] = 0
            resolved.append(name)

    for old, new in zip(columns, resolved):
        if old == new:
            continue
        try:
            cursor.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old}" TO "{new}";')
            entry = f"{table}.{old} → {new}"
            report["columns_renamed"].append(entry)
            print(f"[db_cleaner]   Renamed column: {entry}")
        except sqlite3.OperationalError as e:
            print(f"[db_cleaner]   Could not rename {table}.{old}: {e}")

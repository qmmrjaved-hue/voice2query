"""
correlation_detector.py — detects potential JOIN keys between tables in a SQLite database.

Two-pass strategy:
  1. Name match  — column names shared by two or more tables (strong signal).
  2. Value overlap — columns with different names whose distinct value sets
     share at least one common non-trivial value (weak signal).

Public function:
  - detect(db_path) → list[dict]
"""

import sqlite3
from itertools import combinations


def detect(db_path: str) -> list:
    """
    Scan all table pairs in the database for potential JOIN keys.

    Args:
        db_path: Path to the SQLite .db file.

    Returns:
        A list of hint dicts, each containing:
        {
            "table_a":  str,
            "column_a": str,
            "table_b":  str,
            "column_b": str,
            "reason":   str,   # "shared column name" or "overlapping values: ..."
            "strength": str,   # "strong" or "weak"
        }
        Sorted strong-first, then alphabetically.
        Empty list if the database has fewer than two tables or no correlations found.

    Raises:
        sqlite3.DatabaseError: if the file is not a valid SQLite database.
    """
    print(f"[correlation_detector] Scanning '{db_path}' for JOIN key hints ...")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]

    if len(tables) < 2:
        conn.close()
        print("[correlation_detector] Fewer than 2 tables — nothing to correlate.")
        return []

    # Build per-table column map: {table: {col_name: col_type}}
    schema: dict[str, dict[str, str]] = {}
    for table in tables:
        cursor.execute(f"PRAGMA table_info('{table}');")
        schema[table] = {row[1]: (row[2] or "").upper() for row in cursor.fetchall()}

    hints = []
    seen: set[tuple] = set()

    for (ta, tb) in combinations(tables, 2):
        cols_a = schema[ta]
        cols_b = schema[tb]

        # Pass 1 — shared column names
        for col in sorted(set(cols_a) & set(cols_b)):
            key = (ta, col, tb, col)
            if key not in seen:
                seen.add(key)
                hints.append({
                    "table_a": ta, "column_a": col,
                    "table_b": tb, "column_b": col,
                    "reason": "shared column name",
                    "strength": "strong",
                })

        # Pass 2 — value overlap for differently-named column pairs
        for col_a in sorted(cols_a):
            for col_b in sorted(cols_b):
                if col_a == col_b:
                    continue
                key = (ta, col_a, tb, col_b)
                rev_key = (tb, col_b, ta, col_a)
                if key in seen or rev_key in seen:
                    continue
                overlap = _value_overlap(cursor, ta, col_a, tb, col_b)
                if overlap:
                    seen.add(key)
                    sample = ", ".join(str(v) for v in overlap[:3])
                    hints.append({
                        "table_a": ta, "column_a": col_a,
                        "table_b": tb, "column_b": col_b,
                        "reason": f"overlapping values: {sample}",
                        "strength": "weak",
                    })

    conn.close()

    hints.sort(key=lambda h: (0 if h["strength"] == "strong" else 1, h["table_a"], h["table_b"]))
    print(f"[correlation_detector] Found {len(hints)} hint(s).")
    return hints


def _value_overlap(cursor, ta: str, col_a: str, tb: str, col_b: str) -> list:
    """Return up to 3 shared non-null values between two columns (cross-table)."""
    try:
        cursor.execute(
            f'SELECT DISTINCT "{col_a}" FROM "{ta}" '
            f'WHERE "{col_a}" IS NOT NULL LIMIT 200;'
        )
        vals_a = {row[0] for row in cursor.fetchall()}

        cursor.execute(
            f'SELECT DISTINCT "{col_b}" FROM "{tb}" '
            f'WHERE "{col_b}" IS NOT NULL LIMIT 200;'
        )
        vals_b = {row[0] for row in cursor.fetchall()}

        overlap = sorted(vals_a & vals_b)
        return overlap[:3]
    except sqlite3.OperationalError:
        return []

"""
file_converter.py — converts uploaded files to a SQLite .db file.

Supported formats:
  .db             → passed through unchanged
  .csv            → pandas read_csv → SQLite (one table)
  .json           → pandas read_json → SQLite (one table)
  .xlsx / .xls    → pandas/openpyxl read_excel → SQLite (one table per sheet)

Public function:
  - convert_to_db(file_bytes, original_filename, output_path) → str
"""

import io
import os
import re
import sqlite3
import tempfile

import pandas as pd


def convert_to_db(file_bytes: bytes, original_filename: str, output_path: str = None) -> str:
    """
    Convert an uploaded file to a SQLite .db file.

    Args:
        file_bytes:         Raw bytes of the uploaded file.
        original_filename:  Original file name (used to detect the format).
        output_path:        Destination path for the .db file.
                            If None, a temporary file is created automatically.

    Returns:
        Absolute path to the resulting SQLite .db file.

    Raises:
        ValueError: if the file extension is not supported.
        RuntimeError: if conversion fails (malformed file, missing dependency, etc.).
    """
    ext = os.path.splitext(original_filename)[1].lower()

    if output_path is None:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        output_path = tmp.name
        tmp.close()

    print(f"[file_converter] Converting '{original_filename}' (ext='{ext}') ...")

    if ext == ".db":
        with open(output_path, "wb") as f:
            f.write(file_bytes)
        print(f"[file_converter] Passed through .db → '{output_path}'")
        return output_path

    try:
        if ext == ".csv":
            df_map = _read_csv(file_bytes, original_filename)
        elif ext in (".xlsx", ".xls"):
            df_map = _read_excel(file_bytes)
        elif ext == ".json":
            df_map = _read_json(file_bytes, original_filename)
        else:
            raise ValueError(
                f"[file_converter] Unsupported format '{ext}'. "
                "Accepted: .db, .csv, .json, .xlsx, .xls"
            )
    except ValueError:
        raise
    except Exception as e:
        raise RuntimeError(
            f"[file_converter] Failed to read '{original_filename}': {e}"
        ) from e

    _write_sqlite(df_map, output_path)
    print(f"[file_converter] Wrote {len(df_map)} table(s) to '{output_path}'")
    return output_path


# ------------------------------------------------------------------ #
# Internal readers                                                     #
# ------------------------------------------------------------------ #

def _safe_table_name(name: str) -> str:
    """Convert a file/sheet name to a valid SQLite table identifier."""
    name = os.path.splitext(os.path.basename(name))[0]
    name = name.strip().lower()
    name = re.sub(r"[\s\-]+", "_", name)
    name = re.sub(r"[^\w]", "", name)
    return name or "data"


def _read_csv(file_bytes: bytes, filename: str) -> dict:
    df = pd.read_csv(io.BytesIO(file_bytes))
    return {_safe_table_name(filename): df}


def _read_excel(file_bytes: bytes) -> dict:
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes), engine="openpyxl")
    except ImportError as e:
        raise RuntimeError(
            "[file_converter] openpyxl is required for Excel files. "
            "Run: venv\\Scripts\\pip install openpyxl"
        ) from e
    return {sheet: xl.parse(sheet) for sheet in xl.sheet_names}


def _read_json(file_bytes: bytes, filename: str) -> dict:
    df = pd.read_json(io.BytesIO(file_bytes))
    return {_safe_table_name(filename): df}


def _write_sqlite(df_map: dict, db_path: str) -> None:
    """Write a dict of {table_name: DataFrame} into a SQLite file."""
    conn = sqlite3.connect(db_path)
    for table_name, df in df_map.items():
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        print(f"[file_converter]   Table '{table_name}': {len(df)} row(s), {len(df.columns)} column(s).")
    conn.close()

"""
schema_loader.py — reads the full schema and sample values from any SQLite .db file.

Provides two public functions:
  - get_schema(db_path)      → dict with table names, columns, and DDL
  - format_schema_for_prompt(db_path) → str ready to inject into an LLM prompt
"""

import sqlite3


def get_schema(db_path: str) -> dict:
    """
    Extract the full schema from a SQLite database file.

    Args:
        db_path: Absolute or relative path to the .db file.

    Returns:
        A dict with the following structure:
        {
            "tables": {
                "<table_name>": {
                    "columns": [
                        {"name": str, "type": str, "notnull": bool, "pk": bool}
                    ],
                    "ddl": str   # original CREATE TABLE statement
                }
            }
        }

    Raises:
        FileNotFoundError: if db_path does not exist.
        sqlite3.DatabaseError: if the file is not a valid SQLite database.
    """
    schema = {"tables": {}}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Retrieve all user-created table names
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table in table_names:
            # PRAGMA table_info returns: cid, name, type, notnull, dflt_value, pk
            cursor.execute(f"PRAGMA table_info('{table}');")
            columns = [
                {
                    "name": row[1],
                    "type": row[2] if row[2] else "TEXT",
                    "notnull": bool(row[3]),
                    "pk": bool(row[5]),
                }
                for row in cursor.fetchall()
            ]

            # Retrieve the original DDL for this table
            cursor.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?;",
                (table,),
            )
            ddl_row = cursor.fetchone()
            ddl = ddl_row[0] if ddl_row else ""

            schema["tables"][table] = {"columns": columns, "ddl": ddl}

        conn.close()
        print(f"[schema_loader] Loaded schema: {list(schema['tables'].keys())}")

    except sqlite3.DatabaseError as e:
        raise sqlite3.DatabaseError(
            f"[schema_loader] Failed to read '{db_path}': {e}"
        ) from e

    return schema


def get_vocabulary(db_path: str) -> list[str]:
    """
    Collect all table names, column names, and distinct non-numeric cell values
    from the database — used by error_correction.py for fuzzy matching.

    Args:
        db_path: Path to the .db file.

    Returns:
        A flat list of unique strings representing the database vocabulary.
    """
    vocabulary = set()

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        table_names = [row[0] for row in cursor.fetchall()]

        for table in table_names:
            vocabulary.add(table)

            cursor.execute(f"PRAGMA table_info('{table}');")
            columns = [row[1] for row in cursor.fetchall()]
            vocabulary.update(columns)

            # Sample distinct text values from every text-like column
            for col in columns:
                try:
                    cursor.execute(
                        f"SELECT DISTINCT \"{col}\" FROM \"{table}\" "
                        f"WHERE typeof(\"{col}\") = 'text' LIMIT 100;"
                    )
                    for (val,) in cursor.fetchall():
                        if val:
                            vocabulary.add(str(val))
                except sqlite3.OperationalError:
                    pass  # skip columns that can't be queried this way

        conn.close()

    except sqlite3.DatabaseError as e:
        raise sqlite3.DatabaseError(
            f"[schema_loader] Failed to build vocabulary from '{db_path}': {e}"
        ) from e

    return sorted(vocabulary)


def format_schema_for_prompt(db_path: str) -> str:
    """
    Build a human-readable schema string suitable for injection into an LLM prompt.

    Args:
        db_path: Path to the .db file.

    Returns:
        A multi-line string listing each table with its DDL, e.g.:

        Database schema:

        Table: students
        CREATE TABLE "students" (...)

        Table: professor
        CREATE TABLE 'professor' (...)
    """
    schema = get_schema(db_path)
    lines = ["Database schema:\n"]

    for table_name, info in schema["tables"].items():
        lines.append(f"Table: {table_name}")
        lines.append(info["ddl"])
        lines.append("")  # blank line between tables

    return "\n".join(lines).strip()

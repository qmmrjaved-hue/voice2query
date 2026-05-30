"""
text_to_sql.py — converts a natural language question to a SQL query via Gemini.

Injects the live database schema and few-shot examples into the system prompt
so the model always generates SQL that matches the connected database.

Public function:
  - generate_sql(question, db_path) → str
"""

import os
import re
import time
from google import genai
from google.genai import errors as genai_errors
from schema_loader import format_schema_for_prompt

_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_FEW_SHOT_EXAMPLES = """
Examples (input → SQL only, no explanation):

Q: List all students
A: SELECT * FROM students;

Q: Show students in class TPR1
A: SELECT s.idStudent, s.name, s.firstname, s.age
   FROM students s
   JOIN class c ON s.idClass = c.idClass
   WHERE c.classroom = 'TPR1';

Q: Who teaches Algorithm?
A: SELECT p.name, p.firstname
   FROM professor p
   JOIN teaching t ON p.idProf = t.idProf
   WHERE t.field = 'Algorithm';

Q: Which professors teach in class TPR1?
A: SELECT DISTINCT p.name, p.firstname
   FROM professor p
   JOIN teaching t ON p.idProf = t.idProf
   JOIN class c ON t.idClass = c.idClass
   WHERE c.classroom = 'TPR1';

Q: Show students younger than 22
A: SELECT * FROM students WHERE age < 22;

Q: How many students are in each class?
A: SELECT c.classroom, COUNT(s.idStudent) AS student_count
   FROM class c
   JOIN students s ON c.idClass = s.idClass
   GROUP BY c.idClass, c.classroom;

Q: What subjects are taught in TPR2?
A: SELECT t.field
   FROM teaching t
   JOIN class c ON t.idClass = c.idClass
   WHERE c.classroom = 'TPR2';

Q: List professors and their subjects
A: SELECT p.name, p.firstname, t.field
   FROM professor p
   JOIN teaching t ON p.idProf = t.idProf;

Q: Which class has the oldest students?
A: SELECT c.classroom, MAX(s.age) AS max_age
   FROM students s
   JOIN class c ON s.idClass = c.idClass
   GROUP BY c.idClass, c.classroom
   ORDER BY max_age DESC
   LIMIT 1;

Q: Show all teaching assignments
A: SELECT p.name, p.firstname, t.field, c.classroom
   FROM teaching t
   JOIN professor p ON t.idProf = p.idProf
   JOIN class c ON t.idClass = c.idClass;
"""


def _build_system_prompt(db_path: str) -> str:
    """
    Build the LLM system prompt by combining the live schema with few-shot examples.

    Args:
        db_path: Path to the SQLite database.

    Returns:
        A complete system prompt string.
    """
    schema_block = format_schema_for_prompt(db_path)

    return (
        "You are an expert SQL assistant. "
        "Convert the user's natural language question into a valid SQLite query.\n\n"
        "Rules:\n"
        "- Return ONLY the SQL query, nothing else.\n"
        "- No markdown fences, no explanation, no comments.\n"
        "- Use only the tables and columns defined in the schema below.\n"
        "- Always use explicit JOINs; never use implicit comma joins.\n"
        "- End every query with a semicolon.\n\n"
        f"{schema_block}\n\n"
        f"{_FEW_SHOT_EXAMPLES}"
    )


def _strip_fences(text: str) -> str:
    """Remove markdown code fences if the model includes them despite instructions."""
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    return text.strip()


def generate_sql(question: str, db_path: str) -> str:
    """
    Call the Gemini API to convert a natural language question into a SQL query.

    Args:
        question: The user's question in plain English or Italian.
        db_path:  Path to the SQLite database (used to inject the live schema).

    Returns:
        A SQL query string ready to be executed.

    Raises:
        EnvironmentError: if GEMINI_API_KEY is not set in the environment.
        RuntimeError: if the Gemini API call fails or returns an empty response.
    """
    try:
        import streamlit as st
        api_key = st.secrets.get("GEMINI_API_KEY")
    except:
        api_key = None

    if not api_key:
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "[text_to_sql] GEMINI_API_KEY is not set. "
            "Add it to your .env file and restart."
        )

    system_prompt = _build_system_prompt(db_path)
    full_prompt = f"{system_prompt}\n\nQ: {question}\nA:"

    print(f"[text_to_sql] Question: {question!r}")

    client = genai.Client(api_key=api_key)
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        print(f"[text_to_sql] Calling Gemini API (attempt {attempt}/{max_retries}) ...")
        try:
            response = client.models.generate_content(
                model=_GEMINI_MODEL,
                contents=full_prompt,
            )
            raw = response.text.strip()
            print(f"[text_to_sql] API call succeeded on attempt {attempt}.")
            break
        except genai_errors.ClientError as e:
            if e.code == 429 and attempt < max_retries:
                wait = 35
                match = re.search(r"retry in ([\d.]+)s", str(e))
                if match:
                    wait = int(float(match.group(1))) + 5
                print(f"[text_to_sql] Rate limited (429). Waiting {wait}s before attempt {attempt + 1}/{max_retries} ...")
                time.sleep(wait)
            else:
                raise RuntimeError(f"[text_to_sql] Gemini API call failed: {e}") from e
        except Exception as e:
            raise RuntimeError(f"[text_to_sql] Gemini API call failed: {e}") from e

    if not raw:
        raise RuntimeError("[text_to_sql] Gemini returned an empty response.")

    sql = _strip_fences(raw)
    print(f"[text_to_sql] Generated SQL: {sql}")
    return sql

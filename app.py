"""
app.py — Voice2Query Streamlit dashboard.
Three-page application: landing → upload → query.

Entry point: streamlit run app.py
"""

import io
import os
import sqlite3
import tempfile
import wave
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import db_cleaner
import correlation_detector
import file_converter
import pipeline

# ── Page config — must be the first Streamlit call ────────────────────────────
_initial_sidebar = (
    "expanded" if st.session_state.get("page", "landing") == "query" else "collapsed"
)
st.set_page_config(
    page_title="Voice2Query",
    page_icon=None,
    layout="wide",
    initial_sidebar_state=_initial_sidebar,
)

# ── API key ───────────────────────────────────────────────────────────────────
try:
    import streamlit as st
    api_key = st.secrets.get("GEMINI_API_KEY")
except:
    api_key = None

if not api_key:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    os.environ["GEMINI_API_KEY"] = api_key

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  #MainMenu {visibility: hidden;}
  footer {visibility: hidden;}
  header {visibility: hidden;}
  .block-container {padding-top: 1.5rem;}

  html, body, [class*="css"] {
    font-family: Arial, sans-serif;
  }

  .stButton > button {
    background-color: #1A202C;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 0.5rem 1.5rem;
    font-size: 15px;
    font-weight: bold;
    cursor: pointer;
  }
  .stButton > button:hover {
    background-color: #2D3748;
  }

  .vq-card {
    background: white;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.07);
    margin-bottom: 12px;
  }

  .vq-section-header {
    font-size: 15px;
    font-weight: bold;
    color: #1A202C;
    border-bottom: 2px solid #2E75B6;
    padding-bottom: 4px;
    margin-bottom: 12px;
  }

  .vq-code {
    background: #1E1E1E;
    color: #D4D4D4;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    padding: 12px 16px;
    border-radius: 6px;
    white-space: pre-wrap;
    margin-bottom: 10px;
  }

  .vq-transcript {
    background: #F7FAFC;
    color: #2D3748;
    font-family: 'Courier New', monospace;
    font-size: 13px;
    padding: 12px 16px;
    border-radius: 6px;
    border: 1px solid #E2E8F0;
    margin-bottom: 10px;
  }

  .status-done   { color: #276749; font-weight: bold; }
  .status-active { color: #2E75B6; font-weight: bold; }
  .status-wait   { color: #A0AEC0; }

  .logo-bar {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 32px;
    padding: 16px 0 8px 0;
    flex-wrap: wrap;
  }
  .logo-bar img {
    height: 64px;
    width: auto;
    max-width: 140px;
    object-fit: contain;
    background: white;
    padding: 4px;
    border-radius: 4px;
  }

  .vq-error {
    background: #FFF5F5;
    border: 1px solid #FC8181;
    border-radius: 6px;
    padding: 12px 16px;
    color: #742A2A;
    margin-bottom: 10px;
  }

  .vq-success {
    background: #F0FFF4;
    border: 1px solid #48BB78;
    border-radius: 6px;
    padding: 12px 16px;
    color: #1C4532;
    margin-bottom: 10px;
  }

  .landing-header {
    background: #1A202C;
    padding: 28px 32px 20px 32px;
    border-radius: 10px;
    margin-bottom: 20px;
    text-align: center;
  }
  .landing-header h1 {
    color: white;
    font-size: 42px;
    font-weight: 900;
    margin: 0 0 4px 0;
    letter-spacing: -1px;
  }
  .landing-header p {
    color: #90CDF4;
    font-size: 15px;
    margin: 0;
  }

  .info-card {
    flex: 1;
    background: white;
    border: 1px solid #E2E8F0;
    border-top: 3px solid #2E75B6;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .info-card .ic-number {
    font-size: 28px;
    font-weight: 900;
    color: #2E75B6;
  }
  .info-card .ic-label {
    font-size: 12px;
    color: #718096;
    margin-top: 2px;
  }

  .steps-list {
    counter-reset: steps;
    list-style: none;
    padding: 0;
  }
  .steps-list li {
    counter-increment: steps;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 10px 0;
    border-bottom: 1px solid #F0F0F0;
    font-size: 14px;
    color: #2D3748;
  }
  .steps-list li::before {
    content: counter(steps);
    background: #2E75B6;
    color: white;
    font-weight: bold;
    font-size: 12px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    margin-top: 1px;
  }

  .vq-footer {
    text-align: center;
    color: #A0AEC0;
    font-size: 11px;
    margin-top: 32px;
    padding-top: 12px;
    border-top: 1px solid #E2E8F0;
  }

  .stage-row {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 13px;
    color: #2D3748;
  }
  .stage-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .dot-done   { background: #276749; }
  .dot-active { background: #2E75B6; }
  .dot-wait   { background: #CBD5E0; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
_DEFAULTS = {
    "page": "landing",
    "db_path": None,
    "db_name": None,
    "audio_path": None,
    "history": [],
    "db_tables": None,
    "correlations": None,
    "processed_file_names": None,
    "result": None,
    "_active_audio": None,
    "_active_audio_ext": ".wav",
    "_query_counter": 0,
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_table_info(db_path: str) -> list:
    """Return [{name, rows}, ...] for each table in the database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        info = []
        for (name,) in cursor.fetchall():
            cursor.execute(f'SELECT COUNT(*) FROM "{name}";')
            info.append({"name": name, "rows": cursor.fetchone()[0]})
        conn.close()
        return info
    except Exception:
        return []


def audio_duration_sec(audio_bytes: bytes) -> float | None:
    """Return WAV duration in seconds, or None if unreadable."""
    try:
        with wave.open(io.BytesIO(audio_bytes)) as wf:
            return round(wf.getnframes() / wf.getframerate(), 1)
    except Exception:
        return None


def _stage_html(result: dict) -> str:
    """Build pipeline stage-progress HTML from a completed pipeline result."""
    failed_stage = result["stage"] if result.get("error") else None
    stages = [
        ("audio",            "Audio received"),
        ("transcribe",       "Whisper transcription"),
        ("error_correction", "Error correction"),
        ("text_to_sql",      "SQL generation"),
        ("query_executor",   "Query execution"),
    ]
    html = ""
    hit_failure = False
    for key, label in stages:
        if hit_failure:
            cls = "dot-wait"
        elif key == failed_stage:
            cls = "dot-active"
            hit_failure = True
        else:
            cls = "dot-done"
        html += (
            f'<div class="stage-row">'
            f'<div class="stage-dot {cls}"></div>'
            f"<span>{label}</span>"
            f"</div>"
        )
    return html


def _footer():
    st.markdown(
        '<div class="vq-footer">'
        "©Qamar Javed . Voice2Query · Data Science · DIETI · "
        "University of Naples Federico II · 2025/2026"
        "</div>",
        unsafe_allow_html=True,
    )


# ── Landing page ──────────────────────────────────────────────────────────────

def landing_page():
    st.markdown(
        """
        <div class="logo-bar">
          <img src="https://www.dieti.unina.it/images/logo/DIETI.png" alt="DIETI">
          <img src="https://www.dieti.unina.it/images/logo/logo_ecc.png" alt="">
          <img src="https://www.dieti.unina.it/images/logo/DIETI-DIP-ECCELLENZA-22-27_58.png" alt="">
          <img src="https://www.dieti.unina.it/images/logo/logo-spsb_80.png" alt="">
          <img src="https://napoli.esn.it/satellitenew/sites/esnnapoli.it/files/FedericoII.jpg"
               alt="Federico II">
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="landing-header">
          <h1>Voice2Query</h1>
          <p>Speech-to-SQL Pipeline — Data Science Project</p>
          <p style="color:#E2E8F0; font-size:13px; margin-top:8px;">
            Università degli Studi di Napoli Federico II
            &nbsp;·&nbsp; DIETI Department &nbsp;·&nbsp; 2025–2026
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Info cards
    c1, c2, c3 = st.columns(3)
    for col, number, label in [
        (c1, "6",  "Pipeline Stages"),
        (c2, "3",  "File Formats Supported"),
        (c3, "AI", "Gemini 2.5 Flash Powered"),
    ]:
        with col:
            st.markdown(
                f'<div class="info-card">'
                f'<div class="ic-number">{number}</div>'
                f'<div class="ic-label">{label}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )

    # How it works + Tech stack
    col_left, col_right = st.columns([0.6, 0.4])

    with col_left:
        st.markdown('<div class="vq-section-header">How it works</div>', unsafe_allow_html=True)
        st.markdown(
            """
            <ol class="steps-list">
              <li>Upload your database file (DB, Excel, or CSV)</li>
              <li>The system reads and cleans the schema automatically</li>
              <li>Record your question or upload an audio file</li>
              <li>Whisper transcribes your speech to text</li>
              <li>Gemini AI generates the correct SQL query</li>
              <li>Results appear as a table and chart</li>
            </ol>
            """,
            unsafe_allow_html=True,
        )

    with col_right:
        st.markdown('<div class="vq-section-header">Technology Stack</div>', unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame(
                {
                    "Component": [
                        "Speech Recognition",
                        "AI Translation",
                        "Database",
                        "Dashboard",
                        "Data Processing",
                        "Error Correction",
                    ],
                    "Technology": [
                        "OpenAI Whisper (local)",
                        "Google Gemini 2.5 Flash",
                        "SQLite (generic)",
                        "Streamlit",
                        "pandas + plotly",
                        "DBATI-inspired module",
                    ],
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    # Supervisor & student
    st.markdown("<br>", unsafe_allow_html=True)
    col_sup, col_stu = st.columns(2)
    with col_sup:
        st.markdown(
            """
            <div class="vq-card">
              <div class="vq-section-header">Supervisor</div>
              <strong>Prof. Vincenzo Moscato</strong><br>
              DIETI — University of Naples Federico II
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col_stu:
        st.markdown(
            """
            <div class="vq-card">
              <div class="vq-section-header">Student</div>
              <strong>Qamar Javed</strong><br>
              Matricola: D03000268<br>
              Master's in Data Science — A.Y. 2025/2026
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Launch button — centred
    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        if st.button("Launch Application", use_container_width=True):
            st.session_state.page = "upload"
            st.rerun()

    _footer()


# ── Upload helpers ────────────────────────────────────────────────────────────

def _build_combined_db(uploaded_files: list) -> str:
    """
    Convert every uploaded file and merge all tables into one temp SQLite db.
    Returns the path to that combined db file.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    combined_path = tmp.name

    conn = sqlite3.connect(combined_path)

    for uf in uploaded_files:
        tmp_conv = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        tmp_conv.close()
        try:
            file_converter.convert_to_db(uf.read(), uf.name, tmp_conv.name)
        except Exception as e:
            st.markdown(
                f'<div class="vq-error">Could not convert "{uf.name}": {e}</div>',
                unsafe_allow_html=True,
            )
            os.unlink(tmp_conv.name)
            continue

        src = sqlite3.connect(tmp_conv.name)
        src_cursor = src.cursor()
        src_cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
        )
        for (tbl,) in src_cursor.fetchall():
            df = pd.read_sql_query(f'SELECT * FROM "{tbl}"', src)
            df.to_sql(tbl, conn, if_exists="replace", index=False)
        src.close()
        os.unlink(tmp_conv.name)

    conn.close()
    return combined_path


# ── Upload page ───────────────────────────────────────────────────────────────

def upload_page():
    col_back, col_title, _ = st.columns([1, 8, 1])
    with col_back:
        if st.button("Back"):
            st.session_state.page = "landing"
            st.rerun()
    with col_title:
        st.markdown(
            '<h2 style="margin:0; padding:0;">Voice2Query — Upload Data</h2>',
            unsafe_allow_html=True,
        )

    st.divider()

    col_db, col_audio = st.columns(2)

    # Left — database upload
    with col_db:
        st.markdown('<div class="vq-section-header">Database File</div>', unsafe_allow_html=True)

        db_files = st.file_uploader(
            "Upload database file(s)",
            type=["db", "xlsx", "xls", "csv","json"],
            accept_multiple_files=True,
            help="Upload one or more files. Multiple files are merged into one database.",
            key="db_uploader",
        )

        if db_files:
            current_names = tuple(sorted(f.name for f in db_files))

            if current_names != st.session_state.processed_file_names:
                with st.spinner("Converting and combining files..."):
                    combined_path = _build_combined_db(db_files)

                try:
                    db_cleaner.clean(combined_path)
                except Exception:
                    pass

                st.session_state.db_path = combined_path
                st.session_state.db_name = ", ".join(f.name for f in db_files)
                st.session_state.db_tables = get_table_info(combined_path)
                st.session_state.correlations = correlation_detector.detect(combined_path)
                st.session_state.processed_file_names = current_names
                st.session_state.result = None
                st.session_state._active_audio = None

        if st.session_state.db_path:
            tables = st.session_state.db_tables or []
            rows_html = "".join(
                f"<li>{t['name']} — {t['rows']} row(s)</li>" for t in tables
            )
            st.markdown(
                f'<div class="vq-success">'
                f"Database ready — {len(tables)} table(s) detected:"
                f'<ul style="margin:6px 0 0 16px; padding:0;">{rows_html}</ul>'
                f"</div>",
                unsafe_allow_html=True,
            )

            hints = st.session_state.correlations or []
            if hints:
                hint_rows = "".join(
                    f"<li>"
                    f"{'<b>' if h['strength'] == 'strong' else ''}"
                    f"{h['table_a']}.{h['column_a']} &harr; {h['table_b']}.{h['column_b']}"
                    f"{'</b>' if h['strength'] == 'strong' else ''}"
                    f" &mdash; {h['reason']}"
                    f"</li>"
                    for h in hints
                )
                st.markdown(
                    f'<div class="vq-card" style="margin-top:8px;">'
                    f'<div class="vq-section-header">Detected Relationships</div>'
                    f'<ul style="margin:0; padding-left:18px; font-size:13px;">{hint_rows}</ul>'
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Right — audio upload (optional)
    with col_audio:
        st.markdown(
            '<div class="vq-section-header">Audio Query (optional)</div>',
            unsafe_allow_html=True,
        )

        audio_file = st.file_uploader(
            "Upload audio query",
            type=["wav", "mp3"],
            help="You can also record directly on the next page",
            key="audio_uploader_upload",
        )

        if audio_file is not None:
            audio_bytes = audio_file.read()
            ext = os.path.splitext(audio_file.name)[1].lower()
            tmp_a = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
            tmp_a.write(audio_bytes)
            tmp_a.close()
            st.session_state.audio_path = tmp_a.name
            st.session_state._active_audio = audio_bytes
            st.session_state._active_audio_ext = ext

            dur = audio_duration_sec(audio_bytes) if ext == ".wav" else None
            dur_str = f" — {dur} seconds" if dur else ""
            st.markdown(
                f'<div class="vq-success">Audio file ready{dur_str}</div>',
                unsafe_allow_html=True,
            )

    # Proceed button — centred, disabled until DB loaded
    st.markdown("<br>", unsafe_allow_html=True)
    _, btn_col, _ = st.columns([2, 1, 2])
    with btn_col:
        if st.button(
            "Proceed to Query",
            disabled=st.session_state.db_path is None,
            use_container_width=True,
        ):
            st.session_state.page = "query"
            st.rerun()

    _footer()


# ── Query page ────────────────────────────────────────────────────────────────

def query_page():
    # Sidebar
    with st.sidebar:
        st.markdown("**Voice2Query**")
        st.caption("Data Science · UNINA")
        st.divider()

        st.markdown(
            '<div class="vq-section-header">Connected Database</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.db_name:
            st.write(st.session_state.db_name)
        for t in (st.session_state.db_tables or []):
            st.write(f"{t['name']}: {t['rows']} rows")

        if st.button("Change Database"):
            st.session_state.page = "upload"
            st.rerun()

        st.divider()

        st.markdown(
            '<div class="vq-section-header">Query History</div>',
            unsafe_allow_html=True,
        )
        history = list(reversed(st.session_state.history[-5:]))
        if not history:
            st.caption("No queries yet.")
        for entry in history:
            label = entry["question"][:47] + ("..." if len(entry["question"]) > 47 else "")
            with st.expander(label):
                st.code(entry["sql"], language="sql")
                st.caption(entry["timestamp"])

    # Main area
    st.markdown('<h2 style="margin-bottom:16px;">Query</h2>', unsafe_allow_html=True)

    st.markdown('<div class="vq-section-header">Voice Input</div>', unsafe_allow_html=True)

    record_tab, upload_tab = st.tabs(["Record", "Upload File"])

    _qc = st.session_state._query_counter

    with record_tab:
        recorded = st.audio_input(
            label="Record your question",
            key=f"audio_input_{_qc}",
        )
        if recorded is not None:
            audio_bytes = recorded.read()
            if audio_bytes:
                st.session_state._active_audio = audio_bytes
                st.session_state._active_audio_ext = ".wav"

    with upload_tab:
        uploaded_audio = st.file_uploader(
            "Upload audio file",
            type=["wav", "mp3"],
            key=f"query_audio_upload_{_qc}",
        )
        if uploaded_audio is not None:
            audio_bytes = uploaded_audio.read()
            if audio_bytes:
                st.session_state._active_audio = audio_bytes
                st.session_state._active_audio_ext = (
                    os.path.splitext(uploaded_audio.name)[1].lower()
                )

    if st.button("Run Query", disabled=not bool(st.session_state._active_audio)):
        ext = st.session_state._active_audio_ext or ".wav"
        tmp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp_audio.write(st.session_state._active_audio)
        tmp_audio.close()

        with st.spinner("Running pipeline..."):
            try:
                result = pipeline.run(
                    db_path=st.session_state.db_path,
                    audio_path=tmp_audio.name,
                )
            except Exception as e:
                result = {
                    "audio_path": tmp_audio.name,
                    "transcript": None,
                    "corrected": None,
                    "sql": None,
                    "results": None,
                    "error": str(e),
                    "stage": "unknown",
                }

        st.session_state.result = result
        st.session_state._active_audio = None
        st.session_state._query_counter += 1

        if result.get("sql") and not result.get("error"):
            st.session_state.history.append(
                {
                    "question": result.get("corrected") or "",
                    "sql": result["sql"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
            )

        st.rerun()

    # Results section
    result = st.session_state.result
    if result is None:
        _footer()
        return

    st.divider()

    # Stage progress
    st.markdown(_stage_html(result), unsafe_allow_html=True)

    # Error
    if result.get("error"):
        st.markdown(
            f'<div class="vq-error">'
            f'<strong>Pipeline failed at stage: {result["stage"]}</strong><br>'
            f'{result["error"]}'
            f"</div>",
            unsafe_allow_html=True,
        )

    # Transcript
    if result.get("transcript") or result.get("corrected"):
        st.markdown(
            '<div class="vq-section-header" style="margin-top:16px;">Transcript</div>',
            unsafe_allow_html=True,
        )
        raw = result.get("transcript") or ""
        corrected = result.get("corrected") or ""
        col_raw, col_fix = st.columns(2)
        with col_raw:
            st.markdown("**Whisper Output**")
            st.markdown(f'<div class="vq-transcript">{raw}</div>', unsafe_allow_html=True)
        with col_fix:
            st.markdown("**Corrected**")
            highlight = "border-color: #48BB78;" if raw != corrected else ""
            st.markdown(
                f'<div class="vq-transcript" style="{highlight}">{corrected}</div>',
                unsafe_allow_html=True,
            )

    # Generated SQL
    if result.get("sql"):
        st.markdown(
            '<div class="vq-section-header" style="margin-top:16px;">Generated SQL</div>',
            unsafe_allow_html=True,
        )
        st.markdown("**SQL Query**")
        st.markdown(
            f'<div class="vq-code">{result["sql"]}</div>',
            unsafe_allow_html=True,
        )

    # Results table + chart
    df = result.get("results")
    if df is not None:
        st.markdown(
            '<div class="vq-section-header" style="margin-top:16px;">Results</div>',
            unsafe_allow_html=True,
        )
        if df.empty:
            st.write("The query returned no rows.")
        else:
            m1, m2, m3 = st.columns([1, 1, 2])
            with m1:
                st.metric("Rows", len(df))
            with m2:
                st.metric("Columns", len(df.columns))
            with m3:
                st.download_button(
                    label="Download CSV",
                    data=df.to_csv(index=False).encode("utf-8"),
                    file_name="query_results.csv",
                    mime="text/csv",
                )
            st.dataframe(df, hide_index=True, use_container_width=True)

            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            text_cols = df.select_dtypes(exclude="number").columns.tolist()
            if numeric_cols and text_cols:
                fig = px.bar(
                    df,
                    x=text_cols[0],
                    y=numeric_cols[0],
                    title=result.get("corrected") or "Query Results",
                    text_auto=True,
                    color_discrete_sequence=["#1F4E79"],
                )
                fig.update_layout(
                    plot_bgcolor="white",
                    paper_bgcolor="white",
                    xaxis=dict(title=text_cols[0], showgrid=False),
                    yaxis=dict(title=numeric_cols[0], showgrid=False),
                    font=dict(family="Arial, sans-serif"),
                )
                st.plotly_chart(fig, use_container_width=True)

    _footer()


# ── Router ────────────────────────────────────────────────────────────────────
_PAGE = st.session_state.page
if _PAGE == "landing":
    landing_page()
elif _PAGE == "upload":
    upload_page()
elif _PAGE == "query":
    query_page()

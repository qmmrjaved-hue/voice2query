# Voice2Query

> 🎙️ → 🗣️ → 🧠 → `SQL` → 📊
>
> AI-powered **Speech-to-SQL** pipeline that lets you query a relational database by speaking to it.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Whisper](https://img.shields.io/badge/ASR-OpenAI%20Whisper-412991?logo=openai&logoColor=white)](https://github.com/openai/whisper)
[![Gemini](https://img.shields.io/badge/LLM-Gemini%202.5%20Flash-4285F4?logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Live Demo](https://img.shields.io/badge/🚀%20Live%20Demo-Streamlit%20Cloud-FF4B4B?logo=streamlit&logoColor=white)](https://voice2query-qmrjvd.streamlit.app/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)

> 🌐 **Try it live:** [voice2query-qmrjvd.streamlit.app](https://voice2query-qmrjvd.streamlit.app/) — no install required.

Voice2Query records a spoken question, transcribes it locally with Whisper, repairs schema-specific mishearings, generates a valid SQL query with Google Gemini, executes it against any SQLite database, and shows the results — table + auto-chart — in an interactive Streamlit dashboard.

---

## 📋 Table of Contents

- [About](#-about)
- [Live Demo](#-live-demo)
- [Features](#-features)
- [Architecture](#-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database](#-database)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Example Voice Queries](#-example-voice-queries)
- [Pipeline Stages](#-pipeline-stages)
- [Future Roadmap](#-future-roadmap)
- [Troubleshooting](#-troubleshooting)
- [Author](#-author)
- [Acknowledgments](#-acknowledgments)
- [License](#-license)

---

## 📖 About

Voice2Query was built to make relational databases accessible to non-technical users. Instead of writing SQL, you speak — in English or Italian — and the system handles the rest:

1. **You speak**: "Show me students younger than 22."
2. **Whisper transcribes** your voice locally (no API key, no cloud).
3. **Error correction** repairs any schema-specific misrecognitions (e.g. `DPR1` → `TPR1`).
4. **Gemini generates the SQL** using the database schema injected into its prompt.
5. **SQLite executes** the query.
6. **Streamlit displays** the transcript, the SQL, the result table, and an auto-chart.

The pipeline is **fully generic** — drop in any `.db` file and it works without code changes. An optional pre-pipeline layer also accepts `.xlsx`, `.csv`, and `.json` and converts them on the fly.

---

## 🚀 Live Demo

**The app is deployed on Streamlit Community Cloud — try it without installing anything:**

### 👉 **[https://voice2query-qmrjvd.streamlit.app/](https://voice2query-qmrjvd.streamlit.app/)**

What you can do on the live demo:
- 🎤 Record a voice query directly in the browser (allow microphone access when prompted)
- 📁 Upload an audio file (`.wav`, `.mp3`) if you don't have a mic
- 🗄️ Use the bundled `school.db` or upload your own SQLite database
- 📊 See the transcript, generated SQL, results table, and auto-chart in real time

> 💡 **Tip:** The live app uses Whisper running on Streamlit's free tier, so the first transcription may take a few extra seconds while the model loads. Subsequent queries are much faster.

> ⚠️ **Note:** The live demo shares a single Gemini API key across all visitors, so heavy concurrent traffic may hit the 15 RPM rate limit. If a query stalls, wait 30 seconds and retry — that's the rate limiter, not a bug.

---

## ✨ Features

### ✅ Implemented
- 🎤 **Voice input** via microphone or audio file upload (WAV, 16 kHz mono)
- 🌍 **Multilingual ASR** — English and Italian (via OpenAI Whisper, runs locally)
- 🛠️ **Schema-aware error correction** — DBATI-inspired, repairs ASR mishearings of table/column names
- 🧠 **LLM-powered SQL generation** — Google Gemini 2.5 Flash with full schema prompt injection
- 🔁 **Retry logic** — exponential backoff on Gemini's 429 rate-limit responses
- 📊 **Interactive dashboard** — transcript display, generated SQL preview, result table, auto-bar chart, query history
- 🗄️ **Generic database support** — swap in any SQLite `.db` file, no code changes required
- 🪵 **Stage-by-stage logging** — see exactly what each pipeline stage is doing

### 🛠️ Planned (Pre-Pipeline Ingestion Layer)
- 📦 `file_converter.py` — accepts `.xlsx`, `.csv`, `.json`, `.db` and converts to SQLite automatically
- 🧹 `db_cleaner.py` — strips whitespace, removes empty rows, normalises column names
- 🔗 `correlation_detector.py` — multi-file upload + JOIN-key suggestions across uploaded tables

---

## 🏗️ Architecture

The system is split into two groups: an **optional pre-pipeline ingestion layer** (multi-file upload → convert → clean → detect correlations) and the **main 6-stage pipeline** (voice → ASR → error correction → text-to-SQL → execution → dashboard).

```
┌─────────────────────────────────────────────────────────────┐
│  PRE-PIPELINE — DATA INGESTION (optional, multi-file)       │
│                                                             │
│  User uploads files (.xlsx, .csv, .db, .json, mixed)        │
│              ↓                                              │
│  file_converter.py     — converts each to a SQLite table    │
│              ↓                                              │
│  db_cleaner.py         — cleans each table                  │
│              ↓                                              │
│  correlation_detector  — finds matching columns across      │
│                          tables, suggests JOIN keys         │
│              ↓                                              │
│       All merged into one in-memory SQLite database         │
└─────────────────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│  MAIN PIPELINE — VOICE TO RESULT                            │
│                                                             │
│  🎤  Voice input        (audio_input.py)                    │
│              ↓                                              │
│  🗣️  ASR — Whisper      (transcribe.py)                     │
│              ↓                                              │
│  🛠️  Error correction   (error_correction.py)               │
│              ↓                                              │
│  🧠  Text-to-SQL        (text_to_sql.py + Gemini API)       │
│              ↓                                              │
│  ⚙️  SQL execution      (query_executor.py)                 │
│              ↓                                              │
│  📊  Dashboard          (app.py — Streamlit)                │
└─────────────────────────────────────────────────────────────┘
```


---

## 🧰 Tech Stack

| Component             | Technology                  | Why                                                |
|-----------------------|-----------------------------|----------------------------------------------------|
| Web app framework     | **Streamlit**               | Rapid UI, browser-based, single-file deployment    |
| Speech recognition    | OpenAI Whisper (base)       | Free, local, multilingual, no API key              |
| LLM / text-to-SQL     | Google Gemini 2.5 Flash     | Free tier (15 RPM, 1500 RPD), current active model |
| Database              | SQLite + `sqlite3`          | Lightweight, built into Python                     |
| Audio capture         | `sounddevice` + `scipy`     | Cross-platform microphone access                   |
| Audio decoding        | `ffmpeg` (system)           | Required by Whisper on Windows                     |
| Data handling         | `pandas`                    | DataFrame I/O, integrates with Streamlit           |
| Charts                | `plotly`                    | Interactive visualisations                         |
| File conversion       | `pandas` + `openpyxl`       | For `.xlsx` / `.csv` / `.json` → SQLite            |
| Error correction      | `difflib` (stdlib)          | Fuzzy string matching                              |
| Env management        | `python-dotenv`             | Keep `GEMINI_API_KEY` out of source code           |

---

## 📁 Project Structure

```
voice2query/
│
├── README.md                    ← you are here
├── CLAUDE.md                    ← project context / dev notes
├── requirements.txt             ← Python dependencies
├── .env                         ← GEMINI_API_KEY (never committed)
├── .gitignore
│
├── school.db                    ← primary SQLite database
│
├── audio_input.py               ← microphone recording (sounddevice)
├── transcribe.py                ← Whisper ASR: audio → text
├── error_correction.py          ← schema-aware transcript repair
├── schema_loader.py             ← reads schema from any .db dynamically
├── text_to_sql.py               ← Gemini API: text + schema → SQL
├── query_executor.py            ← executes SQL on SQLite → DataFrame
├── pipeline.py                  ← orchestrates all stages end-to-end
│
├── app.py                       ← Streamlit dashboard (main entry)
│
├── file_converter.py            ← (planned) .xlsx/.csv/.json → SQLite
├── db_cleaner.py                ← (planned) auto-clean database
├── correlation_detector.py      ← (planned) cross-file JOIN suggestions
│
└── assets/
    └── flowchart.png            ← architecture diagram
```

---

## 🗄️ Database

The primary database is `school.db` — a small School Management database with four interrelated tables.

| Table       | Rows | Description                                       |
|-------------|------|---------------------------------------------------|
| `class`     | 2    | Classrooms (TPR1, TPR2)                           |
| `students`  | 6    | Students enrolled across the two classes          |
| `professor` | 4    | Teaching staff                                    |
| `teaching`  | 2    | Links professors → classes → subjects             |

**Schema:**

```sql
CREATE TABLE class (
    idClass   INTEGER PRIMARY KEY,
    classroom VARCHAR(11)
);

CREATE TABLE students (
    idStudent INTEGER PRIMARY KEY,
    idClass   INTEGER REFERENCES class(idClass),
    name      VARCHAR(20),   -- surname
    firstname VARCHAR(20),
    age       INTEGER
);

CREATE TABLE professor (
    idProf    INTEGER PRIMARY KEY,
    name      VARCHAR(20),
    firstname VARCHAR(20)
);

CREATE TABLE teaching (
    idProf  INTEGER REFERENCES professor(idProf),
    idClass INTEGER REFERENCES class(idClass),
    field   VARCHAR(20)   -- e.g. 'Algorithm', 'Database'
);
```

> 💡 The schema is loaded **dynamically at runtime** by `schema_loader.py`. You can drop in any other SQLite database and the pipeline will work without modification.

---

## 📦 Prerequisites

- **Python 3.11** (other 3.10+ versions should work)
- **Windows / macOS / Linux** (developed and tested on Windows 10/11)
- **ffmpeg** installed and on `PATH` (required by Whisper for audio decoding)
- A **Google Gemini API key** — free, get one at [aistudio.google.com](https://aistudio.google.com/)
- A working **microphone** (or you can upload audio files instead)

### Install ffmpeg (Windows)

```cmd
winget install Gyan.FFmpeg
```

Then close and reopen your terminal so `PATH` updates. Verify with:

```cmd
ffmpeg -version
```

### Install ffmpeg (macOS / Linux)

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt install ffmpeg
```

---

## ⚙️ Installation

### 1. Clone the repository

```cmd
git clone https://github.com/<your-username>/voice2query.git
cd voice2query
```

### 2. Create and activate a virtual environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```cmd
pip install -r requirements.txt
```

`requirements.txt`:
```
openai-whisper
google-genai
streamlit
pandas
plotly
sounddevice
scipy
python-dotenv
openpyxl
```

> ⚠️ Use `google-genai`, **not** the deprecated `google-generativeai` package.

---

## 🔐 Configuration

Create a `.env` file in the project root:

```
GEMINI_API_KEY=your_api_key_here
```

> 🚨 **Never commit `.env` to git.** Make sure it's listed in `.gitignore`.

The application loads the key automatically via `python-dotenv`:

```python
from dotenv import load_dotenv
import os
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
```

---

## ▶️ Usage

You have two ways to use Voice2Query:

### Option A — Use the live demo (zero setup)

Just open **[voice2query-qmrjvd.streamlit.app](https://voice2query-qmrjvd.streamlit.app/)** in any modern browser. Skip steps 1–3 below and go straight to "How to use the dashboard."

### Option B — Run locally

Follow [Installation](#-installation) and [Configuration](#-configuration), then launch the dashboard:

```cmd
streamlit run app.py
```

This opens the app in your browser at `http://localhost:8501`.

### How to use the dashboard

1. **Upload** a `.db` file (or use the bundled `school.db`).
2. **Record** your voice query by clicking the microphone button — or **upload** an audio file.
3. Watch the pipeline run:
   - Raw transcript appears
   - Corrected transcript appears (if any words were repaired)
   - Generated SQL is shown
   - Result table renders
   - Auto-bar chart appears if results contain numeric columns
4. Your query is added to the **history sidebar** so you can revisit it.

### Run without audio (text shortcut for testing)

You can call `pipeline.py` directly with a text string instead of an audio file — useful when developing without burning API calls on Whisper:

```python
from pipeline import run_pipeline
result = run_pipeline(text="List all students in class TPR1")
print(result)
```

---

## 🎯 Example Voice Queries

| Spoken query                                  | SQL operation              | Expected result |
|-----------------------------------------------|----------------------------|-----------------|
| "List all students"                           | `SELECT *`                 | 6 rows          |
| "Show students in class TPR1"                 | `JOIN` + `WHERE`           | 4 rows          |
| "Show students in class TPR2"                 | `JOIN` + `WHERE`           | 2 rows          |
| "Show me students younger than 22"            | `WHERE age < 22`           | 3 rows          |
| "Who teaches Algorithm?"                      | `JOIN` + `WHERE`           | 1 row           |
| "Which professors teach in class TPR1?"       | 3-table `JOIN`             | 2 rows          |
| "How many students in each class?"            | `GROUP BY` + `COUNT`       | 2 rows          |
| "What subjects are taught in TPR2?"           | `JOIN` + `WHERE`           | varies          |
| "List professors and their subjects"          | `JOIN`                     | 2 rows          |
| "Which class has the oldest students?"        | `JOIN` + `GROUP BY` + `MAX`| 1 row           |
| "Show all teaching assignments"               | 3-table `JOIN`             | 2 rows          |

---

## 🔄 Pipeline Stages

### Stage 1 — Voice Input (`audio_input.py`)
Captures audio from the system microphone via `sounddevice`. Saves a WAV file at 16 kHz mono — the format Whisper expects.

### Stage 2 — ASR (`transcribe.py`)
Loads the Whisper `base` model (140 MB, downloaded on first use) and transcribes the WAV to text. Runs entirely locally. Lazy-loaded so the model only loads if audio input is actually used.

### Stage 3 — Error Correction (`error_correction.py`)
Builds a vocabulary from the database schema (table names, column names, known values like `TPR1`, `Algorithm`). Scans each transcript word with `difflib.get_close_matches()` and replaces near-matches. High-priority terms are pinned so they always win.

**Real example from a test run:**
```
[transcribe]       Result: 'List all the students in class DPR1.'
[error_correction] 'DPR1.' → 'TPR1' (pinned)
[error_correction] Result: 'List all the students in class TPR1'
```

### Stage 4 — Text-to-SQL (`text_to_sql.py`)
Builds a prompt containing the full database schema + few-shot examples + the corrected transcript. Sends to Gemini 2.5 Flash. Returns only the SQL query — no markdown fences, no explanation. On 429 rate-limit, waits 30 s and retries up to 3×.

### Stage 5 — SQL Execution (`query_executor.py`)
Runs the generated SQL via `sqlite3`. Returns results as a `pandas.DataFrame`. Wraps everything in `try/except` so malformed SQL produces a readable error message instead of a crash.

### Stage 6 — Dashboard (`app.py`)
Streamlit UI at `localhost:8501`. Renders the transcript (raw + corrected), the SQL, the result table, an auto-bar chart for numeric columns, and a sidebar with query history.

---

## 🛣️ Future Roadmap

The pre-pipeline ingestion layer is designed and ready to implement.

### 🚧 Feature 1 — Automatic Database Cleaner (`db_cleaner.py`) — ~1 hour
Runs automatically after any database is uploaded. Removes fully empty rows, strips whitespace from text columns, standardises column names (lowercase, underscores). Reports results as a green success message in the dashboard.

### 🚧 Feature 2 — Universal File Converter (`file_converter.py`) — ~2 hours
Auto-detects uploaded file extension. Converts:
- `.xlsx` / `.xls` → via `openpyxl`
- `.csv` → via `pandas`
- `.json` → via `pandas`
- `.db` → passes through unchanged

Each spreadsheet sheet becomes its own SQLite table. Built because online Excel-to-SQLite converters produce malformed files the pipeline can't read.

### 🚧 Feature 3 — Multi-File Upload with Cross-File Correlation — ~3 hours
The dashboard accepts multiple files simultaneously. Each becomes a separate table in one combined in-memory SQLite database. `correlation_detector.py` scans for matching column names and overlapping values, suggesting JOIN keys to the user before querying. The LLM sees the full combined schema and can generate cross-table queries.

**Recommended build order:** Feature 1 → Feature 2 → Feature 3
**Full chain:** upload → convert → clean → detect correlations → query → results

---

## 🔧 Troubleshooting

### `ffmpeg not found` error
Whisper needs `ffmpeg` on `PATH`. See [Prerequisites](#-prerequisites) above. Reopen your terminal after installing.

### `429 RESOURCE_EXHAUSTED` from Gemini
You've hit the free-tier rate limit:
- **15 requests / minute**
- **1,500 requests / day**

This is not a code bug — wait 30 seconds and retry. The retry logic in `text_to_sql.py` does this automatically up to 3 times. Space out test calls during development.

### `Model 'gemini-2.0-flash' is not supported`
Google retired `gemini-2.0-flash` in March 2026. We're on **`gemini-2.5-flash`** now. If you see this error, check `text_to_sql.py` is using the current model name.

### `python` opens the Microsoft Store (Windows)
The Microsoft Store Python alias is intercepting your command. Fix:
1. Open *Settings → Apps → Advanced app settings → App execution aliases*
2. Disable both `python.exe` and `python3.exe`
3. Make sure your real Python install directory is on `PATH`

### Microphone not detected
Make sure your browser has permission to access the microphone (Streamlit runs in the browser). On macOS, also grant Terminal access to the mic under *System Settings → Privacy & Security → Microphone*.

---

## 👤 Author

**Qamar Javed**
Matricola: **D03000268**
Master's in Data Science — A.Y. 2025/2026
Università degli Studi di Napoli Federico II (UNINA)

---

## 🙏 Acknowledgments

This project was developed as the final assignment for **Fundamentals of Programming** under the supervision of:

**Prof. Vincenzo Moscato**
Università degli Studi di Napoli Federico II

Thanks also to the open-source projects that made this possible:
- [OpenAI Whisper](https://github.com/openai/whisper) for local speech recognition
- [Google Gemini](https://ai.google.dev/) for free-tier LLM access
- [Streamlit](https://streamlit.io/) for the dashboard framework

Research inspiration:
- Shao et al. (2023) — *Database-aware ASR error correction for speech-to-SQL parsing* (DBATI)
- Song et al. (2022) — *VoiceQuerySystem* (cascaded pipeline reference)
- Kumar et al. (2013) — original speech-to-SQL baseline

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ in Naples**
Università degli Studi di Napoli Federico II · A.Y. 2025/2026

🌐 Live at **[voice2query-qmrjvd.streamlit.app](https://voice2query-qmrjvd.streamlit.app/)**

</div>

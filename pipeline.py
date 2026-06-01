"""
pipeline.py — orchestrates all Voice2Query stages end-to-end.

Stages:
  1. Audio input   — record from microphone OR use an existing audio file
  2. Transcribe    — Whisper ASR: audio → raw text
  3. Error correct — schema-aware fuzzy repair of the transcript
  4. Text-to-SQL   — Gemini API: corrected text → SQL query
  5. Execute SQL   — run query against SQLite, return DataFrame

Public function:
  - run(db_path, audio_path=None, duration=5, model_size="base", language=None,
        correction_cutoff=0.8) → dict
"""

import os
import traceback
import text_to_sql
import query_executor

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# audio_input, transcribe, and error_correction are imported lazily inside run()
# so that loading pipeline.py does not trigger the Whisper/sounddevice imports
# when those stages are not needed (e.g. text-mode testing).


def run(
    db_path: str,
    audio_path: str = None,
    text: str = None,
    duration: int = 5,
    model_size: str = "base",
    language: str = None,
    correction_cutoff: float = 0.8,
) -> dict:
    """
    Execute the full Voice2Query pipeline and return all intermediate results.

    Three input modes (in priority order):
      1. text       — skip stages 1-3, use the string directly as the question.
      2. audio_path — skip recording, transcribe an existing file.
      3. (neither)  — record from the microphone for `duration` seconds.

    Args:
        db_path:            Path to the SQLite .db file.
        text:               Plain-text question to send directly to the LLM,
                            bypassing audio input, transcription, and error
                            correction. Useful for testing.
        audio_path:         Path to an existing audio file to transcribe.
        duration:           Recording length in seconds (microphone mode only).
                            Defaults to 5.
        model_size:         Whisper model size — "tiny", "base", "small",
                            "medium", or "large". Defaults to "base".
        language:           ISO-639-1 language code passed to Whisper (e.g.
                            "en", "it"). None means auto-detect.
        correction_cutoff:  Similarity threshold for error correction (0–1).
                            Defaults to 0.8.

    Returns:
        A dict with the following keys:
        {
            "audio_path":   str   — path to the audio file (None in text mode),
            "transcript":   str   — raw Whisper output (None in text mode),
            "corrected":    str   — question sent to the LLM,
            "sql":          str   — generated SQL query,
            "results":      pd.DataFrame — query results (empty DF on no rows),
            "error":        str | None   — error message if any stage failed,
            "stage":        str | None   — name of the failed stage,
        }
    """
    state = {
        "audio_path": audio_path,
        "transcript": None,
        "corrected": None,
        "sql": None,
        "results": None,
        "error": None,
        "stage": None,
    }

    # ------------------------------------------------------------------ #
    # Text shortcut — skip stages 1-3                                     #
    # ------------------------------------------------------------------ #
    if text is not None:
        print(f"\n[pipeline] Text mode — skipping audio/ASR stages.")
        print(f"[pipeline] Question: {text!r}")
        state["transcript"] = text
        state["corrected"] = text

    else:
        import transcribe as transcribe_module
        import error_correction

        # ------------------------------------------------------------------ #
        # Stage 1 — Audio input                                               #
        # ------------------------------------------------------------------ #
        if audio_path is None:
            import audio_input
            try:
                print("\n[pipeline] Stage 1/5 — Recording audio ...")
                state["audio_path"] = audio_input.record(
                    duration=duration,
                    output_path=os.path.join(_PROJECT_DIR, "recording.wav"),
                )
            except Exception as e:
                return _fail(state, "audio_input", e)
        else:
            print(f"\n[pipeline] Stage 1/5 — Using existing audio file: '{audio_path}'")

        # ------------------------------------------------------------------ #
        # Stage 2 — Transcription                                             #
        # ------------------------------------------------------------------ #
        try:
            print("\n[pipeline] Stage 2/5 — Transcribing audio ...")
            state["transcript"] = transcribe_module.transcribe(
                audio_path=state["audio_path"],
                model_size=model_size,
                language=language,
            )
        except Exception as e:
            return _fail(state, "transcribe", e)

        # ------------------------------------------------------------------ #
        # Stage 3 — Error correction                                          #
        # ------------------------------------------------------------------ #
        try:
            print("\n[pipeline] Stage 3/5 — Correcting transcript ...")
            state["corrected"] = error_correction.correct(
                transcript=state["transcript"],
                db_path=db_path,
                cutoff=correction_cutoff,
            )
        except Exception as e:
            return _fail(state, "error_correction", e)

    # ------------------------------------------------------------------ #
    # Stage 4 — Text-to-SQL                                               #
    # ------------------------------------------------------------------ #
    try:
        print("\n[pipeline] Stage 4/5 — Generating SQL ...")
        state["sql"] = text_to_sql.generate_sql(
            question=state["corrected"],
            db_path=db_path,
        )
    except Exception as e:
        return _fail(state, "text_to_sql", e)

    # ------------------------------------------------------------------ #
    # Stage 5 — SQL execution                                             #
    # ------------------------------------------------------------------ #
    try:
        print("\n[pipeline] Stage 5/5 — Executing SQL ...")
        state["results"] = query_executor.execute(
            sql=state["sql"],
            db_path=db_path,
        )
    except Exception as e:
        return _fail(state, "query_executor", e)

    print("\n[pipeline] Pipeline complete.")
    return state


def _fail(state: dict, stage: str, exc: Exception) -> dict:
    """
    Record the failed stage and exception message into state and return it.

    Args:
        state: Current pipeline state dict.
        stage: Name of the stage that raised the exception.
        exc:   The exception that was caught.

    Returns:
        The updated state dict with 'error' and 'stage' populated.
    """
    state["stage"] = stage
    state["error"] = f"{type(exc).__name__}: {exc}"
    print(f"\n[pipeline] ERROR in stage '{stage}': {exc}")
    print(traceback.format_exc())
    return state

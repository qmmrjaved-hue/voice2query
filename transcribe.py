"""
transcribe.py — transcribes an audio file to text using OpenAI Whisper (local).

Public function:
  - transcribe(audio_path, model_size="base", language=None) → str
"""

import os
import shutil
import whisper


def _ensure_ffmpeg() -> None:
    """
    Make sure ffmpeg is reachable before Whisper tries to spawn it.

    Strategy (in order):
    1. Already on PATH — nothing to do.
    2. Search the WinGet packages folder for ffmpeg.exe and add its
       directory to the running process's PATH.  Winget installs update
       the Windows registry but processes launched beforehand inherit a
       stale PATH snapshot; this patch lets them find newly-installed
       binaries without a restart.
    """
    if shutil.which("ffmpeg"):
        return

    local_app_data = os.environ.get("LOCALAPPDATA", "")
    winget_pkgs = os.path.join(local_app_data, "Microsoft", "WinGet", "Packages")

    if os.path.isdir(winget_pkgs):
        for root, _dirs, files in os.walk(winget_pkgs):
            if "ffmpeg.exe" in files:
                os.environ["PATH"] = root + os.pathsep + os.environ.get("PATH", "")
                print(f"[transcribe] Added ffmpeg to PATH from: {root}")
                return


def transcribe(audio_path: str, model_size: str = "base", language: str = None) -> str:
    """
    Transcribe an audio file to a text string using a local Whisper model.

    Args:
        audio_path:  Path to the audio file (WAV, MP3, M4A, FLAC, etc.).
        model_size:  Whisper model variant — "tiny", "base", "small", "medium",
                     or "large". Larger models are more accurate but slower.
                     Defaults to "base".
        language:    Optional ISO-639-1 language code to force (e.g. "en", "it").
                     When None, Whisper auto-detects the language.

    Returns:
        The transcribed text as a stripped string.

    Raises:
        FileNotFoundError: if audio_path does not exist.
        RuntimeError: if Whisper fails to load the model or transcribe the file.
    """
    try:
        print(f"[transcribe] Loading Whisper model '{model_size}' ...")
        model = whisper.load_model(model_size)
    except Exception as e:
        raise RuntimeError(f"[transcribe] Failed to load Whisper model '{model_size}': {e}") from e

    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"[transcribe] Audio file not found: '{audio_path}'")

    _ensure_ffmpeg()

    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "[transcribe] ffmpeg is not installed or not on PATH. "
            "Install it with: winget install Gyan.FFmpeg  "
            "then restart your terminal and Streamlit."
        )

    try:
        print(f"[transcribe] Transcribing '{audio_path}' ...")
        options = {}
        if language:
            options["language"] = language

        result = model.transcribe(audio_path, fp16=False, **options)
        text = result["text"].strip()
        print(f"[transcribe] Result: {text!r}")
        return text

    except Exception as e:
        raise RuntimeError(f"[transcribe] Transcription failed for '{audio_path}': {e}") from e

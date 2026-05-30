"""
audio_input.py — records audio from the microphone and saves it as a WAV file.

Public function:
  - record(duration, output_path="recording.wav", sample_rate=16000) → str
"""

import os
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write as write_wav


def record(
    duration: int = 5,
    output_path: str = "recording.wav",
    sample_rate: int = 16000,
) -> str:
    """
    Record audio from the default microphone and save it as a mono WAV file.

    Args:
        duration:     Recording length in seconds. Defaults to 5.
        output_path:  Where to save the WAV file. Defaults to 'recording.wav'
                      in the current working directory.
        sample_rate:  Samples per second. Whisper expects 16000 Hz. Defaults to 16000.

    Returns:
        The path to the saved WAV file (same as output_path).

    Raises:
        RuntimeError: if no input device is found or recording fails.
        OSError: if the output file cannot be written.
    """
    try:
        print(f"[audio_input] Recording for {duration}s at {sample_rate} Hz ...")
        audio = sd.rec(
            frames=int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()  # block until recording is complete
        print("[audio_input] Recording finished.")
    except sd.PortAudioError as e:
        raise RuntimeError(f"[audio_input] Microphone error: {e}") from e

    # Flatten to 1-D so scipy writes a proper mono WAV
    audio_mono = audio.flatten()

    try:
        write_wav(output_path, sample_rate, audio_mono)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"[audio_input] Saved to '{output_path}' ({size_kb:.1f} KB)")
    except OSError as e:
        raise OSError(f"[audio_input] Could not write file '{output_path}': {e}") from e

    return output_path

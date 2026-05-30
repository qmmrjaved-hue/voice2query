"""
error_correction.py — schema-aware transcript repair (simplified DBATI approach).

Scans each word in the transcribed text against the database vocabulary
(table names, column names, known values) and replaces near-misses using
difflib fuzzy matching.

Pinned values (e.g. classroom codes like TPR1, TPR2) are matched with a
more permissive cutoff and are protected against space-split ASR errors
such as "TPR 1" → "TPR1".

Public function:
  - correct(transcript, db_path, cutoff=0.8) → str
"""

import difflib
from schema_loader import get_vocabulary

# Values that must be preserved exactly and matched more aggressively.
# Whisper sometimes mis-hears or space-splits these short alphanumeric codes.
_PINNED_VALUES = ["TPR1", "TPR2"]
_PINNED_CUTOFF = 0.6  # more permissive than the general cutoff


def _merge_space_variants(words: list, targets: list) -> list:
    """
    Merge adjacent word pairs that concatenate to a known target value.

    Handles ASR splits like ['TPR', '1'] → ['TPR1'] caused by Whisper
    inserting a space inside a short alphanumeric code.

    Args:
        words:   Token list from transcript.split().
        targets: List of canonical values to check against (e.g. _PINNED_VALUES).

    Returns:
        New token list with merged tokens where applicable.
    """
    targets_lower = {t.lower(): t for t in targets}
    result = []
    i = 0
    while i < len(words):
        if i + 1 < len(words):
            bigram = words[i].strip(".,!?;:'\"") + words[i + 1].strip(".,!?;:'\"")
            if bigram.lower() in targets_lower:
                canonical = targets_lower[bigram.lower()]
                print(f"[error_correction] '{words[i]} {words[i + 1]}' → '{canonical}' (space merge)")
                result.append(canonical)
                i += 2
                continue
        result.append(words[i])
        i += 1
    return result


def correct(transcript: str, db_path: str, cutoff: float = 0.8) -> str:
    """
    Repair ASR errors in a transcript by replacing words that closely match
    known database terms (table names, column names, cell values).

    Two-pass strategy:
      1. Bigram merge — collapses space-split pinned codes ("TPR 1" → "TPR1").
      2. Word-by-word fuzzy match — pinned values are tried first at a lower
         cutoff; the general vocabulary is tried next at the caller's cutoff.

    The correction is intentionally conservative: a word is only replaced when
    a single unambiguous match is found above the applicable cutoff threshold.

    Args:
        transcript: Raw text returned by Whisper.
        db_path:    Path to the SQLite database used to build the vocabulary.
        cutoff:     Minimum similarity ratio (0–1) for general vocabulary matches.
                    Higher values mean stricter matching. Defaults to 0.8.

    Returns:
        The corrected transcript as a single string.

    Raises:
        sqlite3.DatabaseError: if the vocabulary cannot be loaded from db_path.
    """
    print("[error_correction] Building vocabulary from schema ...")
    vocabulary = get_vocabulary(db_path)

    # Ensure pinned values are present in the vocabulary
    vocab_lower = {v.lower() for v in vocabulary}
    for pv in _PINNED_VALUES:
        if pv.lower() not in vocab_lower:
            vocabulary.append(pv)

    # Pass 1 — merge space-split pinned codes ("TPR 1" → "TPR1")
    words = _merge_space_variants(transcript.split(), _PINNED_VALUES)

    # Pass 2 — word-by-word fuzzy correction
    corrected_words = []
    pinned_lower = [v.lower() for v in _PINNED_VALUES]

    for word in words:
        cleaned = word.strip(".,!?;:'\"").lower()

        # Try pinned values first with a more permissive cutoff
        pinned_match = difflib.get_close_matches(
            cleaned, pinned_lower, n=1, cutoff=_PINNED_CUTOFF
        )
        if pinned_match and pinned_match[0] != cleaned:
            canonical = next(v for v in _PINNED_VALUES if v.lower() == pinned_match[0])
            print(f"[error_correction] '{word}' → '{canonical}' (pinned)")
            corrected_words.append(canonical)
            continue

        # General vocabulary match at the caller's cutoff
        matches = difflib.get_close_matches(
            cleaned,
            [v.lower() for v in vocabulary],
            n=1,
            cutoff=cutoff,
        )
        if matches and matches[0] != cleaned:
            match_lower = matches[0]
            original_case = next(
                (v for v in vocabulary if v.lower() == match_lower), match_lower
            )
            print(f"[error_correction] '{word}' → '{original_case}'")
            corrected_words.append(original_case)
        else:
            corrected_words.append(word)

    corrected = " ".join(corrected_words)
    print(f"[error_correction] Result: {corrected!r}")
    return corrected

import os
from pathlib import Path
import hashlib
import textwrap
import nltk
import pytest

# ──────────────────────────────────────────────────────────────────────────────
# Configuration (portable)
# ──────────────────────────────────────────────────────────────────────────────
# Choose which corpus file to test:
#   STOPWORDS_VERSION=english  → test the original file
#   STOPWORDS_VERSION=modified → test the english_modified file
VARIANT = os.getenv("STOPWORDS_VERSION", "modified").lower()  # "english" | "modified"

# Try to get NLTK data root from env; otherwise search common locations.
NLTK_DATA_ROOT = os.getenv("NLTK_DATA")
if not NLTK_DATA_ROOT:
    candidates = [
        str(Path.cwd() / "../nltk_data/packages"),   # repos side-by-side
        str(Path.home() / "nltk_data/packages"),     # user install
        "/usr/share/nltk_data/packages",             # Linux system
        "/usr/local/share/nltk_data/packages",       # macOS/Linux alt
        "C:/nltk_data/packages",                     # Windows common
    ]
    for p in candidates:
        if Path(p).exists():
            NLTK_DATA_ROOT = p
            break
    else:
        NLTK_DATA_ROOT = None

# Make sure NLTK can see the path (if found)
if NLTK_DATA_ROOT and NLTK_DATA_ROOT not in nltk.data.path:
    nltk.data.path.insert(0, NLTK_DATA_ROOT)

STOPWORDS_DIR   = Path(NLTK_DATA_ROOT) / "corpora" / "stopwords" if NLTK_DATA_ROOT else None
ENGLISH_FILE    = STOPWORDS_DIR / "english" if STOPWORDS_DIR else None
ENGLISH_MODFILE = STOPWORDS_DIR / "english_modified" if STOPWORDS_DIR else None

# Expected additions (representative set)
EXPECTED = [
    # smart-quote + straight-quote pairs
    "i'm", "i’m", "you’re", "you're", "it’s", "it's", "don’t", "don't",
    "can’t", "can't", "won’t", "won't", "shouldn’t", "shouldn't",
    "wasn’t", "wasn't", "weren’t", "weren't",
    # colloquialisms / slang
    "ain’t", "ain't", "gonna", "wanna", "gotta", "lemme", "gimme",
    "coulda", "shoulda", "woulda",
]
SPOT_CHECK = ["ain’t", "ain't", "i’m", "i'm", "gonna", "shoulda"]


def _md5(path: Path) -> str:
    if not path or not path.exists():
        return "N/A"
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


@pytest.fixture(autouse=True)
def ensure_paths_and_variant():
    """Skip cleanly if paths are missing; banner explains how to set NLTK_DATA."""
    if not NLTK_DATA_ROOT or not STOPWORDS_DIR or not STOPWORDS_DIR.exists():
        pytest.skip(
            "NLTK_DATA path not found. Set NLTK_DATA to your '.../nltk_data/packages' folder.\n"
            "Example:\n"
            "  Bash:       export NLTK_DATA=/path/to/nltk_data/packages\n"
            "  PowerShell: $env:NLTK_DATA='C:\\path\\to\\nltk_data\\packages'\n"
        )
    if VARIANT not in {"english", "modified"}:
        pytest.skip("Set STOPWORDS_VERSION to 'english' or 'modified'.")


@pytest.fixture(autouse=True)
def swap_stopwords_file():
    """
    For STOPWORDS_VERSION=modified, copy english_modified -> english for the test,
    then restore the original contents afterward. This makes the test explicit and
    reproducible without editing the corpus between runs.
    """
    src = ENGLISH_MODFILE if VARIANT == "modified" else ENGLISH_FILE
    if not src or not src.exists():
        pytest.skip(f"Variant file not found: {src}")

    backup_text = ENGLISH_FILE.read_text(encoding="utf-8") if ENGLISH_FILE.exists() else None

    if VARIANT == "modified":
        ENGLISH_FILE.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    try:
        yield
    finally:
        if backup_text is not None:
            ENGLISH_FILE.write_text(backup_text, encoding="utf-8")


def test_stopwords_contractions_and_slang():
    from nltk.corpus import stopwords

    # Banner (helps graders see exactly what ran)
    print("\n" + "=" * 72)
    print(f" ACCEPTANCE TEST — STOPWORDS ({VARIANT.upper()})")
    print("=" * 72)
    print(f"NLTK_DATA root : {NLTK_DATA_ROOT}")
    print(f"Active file    : {ENGLISH_FILE}")
    print(f"MD5 fingerprint: {_md5(ENGLISH_FILE)}")

    sw = set(stopwords.words("english"))
    missing = [w for w in EXPECTED if w not in sw]
    present = {w: (w in sw) for w in SPOT_CHECK}

    print(f"Loaded words   : {len(sw)}")
    print("Spot checks    :", ", ".join(f"{w}={'✓' if ok else '✗'}" for w, ok in present.items()))

    if missing:
        sample = ", ".join(missing[:10]) + (" …" if len(missing) > 10 else "")
        msg = textwrap.dedent(f"""
            ------------------------------------------------------------------------
            RESULT: ❌ FAIL — Missing expected stopwords ({len(missing)} total)
            First few missing: {sample}

            How to reproduce locally:

              # Original corpus (expected FAIL)
              STOPWORDS_VERSION=english \\
              NLTK_DATA={NLTK_DATA_ROOT or '<set-your-path>'} \\
              pytest -q -s nltk/test/unit/test_stopwords_contractions.py

              # Modified corpus (expected PASS)
              STOPWORDS_VERSION=modified \\
              NLTK_DATA={NLTK_DATA_ROOT or '<set-your-path>'} \\
              pytest -q -s nltk/test/unit/test_stopwords_contractions.py
            ------------------------------------------------------------------------
        """).strip()
        pytest.fail(msg)
    else:
        print(textwrap.dedent("""
            ------------------------------------------------------------------------
            RESULT: ✅ PASS — All expected contractions & slang are present.
            Confirms the enhancement requested in Issue #3047.
            ------------------------------------------------------------------------
        """).rstrip())

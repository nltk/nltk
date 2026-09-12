# Natural Language Toolkit: Terminal-output safety helpers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Neutralise terminal control sequences before untrusted text is written to a
terminal.

A value that an attacker can influence -- a package ``id``/``name``/``filename``
from a (possibly MITM'd) download index, a tweet body from the network, corpus
content read from disk -- can carry ANSI/OSC escape sequences. When such a
string is printed to a terminal, those sequences are *executed* by the terminal:
they can clear the screen, move the cursor, rewrite already-printed lines to spoof
output, set the window title, or (on some terminals) drive clipboard/hyperlink
actions (CWE-150, "Improper Neutralization of Escape, Meta, or Control
Sequences").

:func:`sanitize_terminal` turns every dangerous control byte into a visible
``\\xNN`` / ``\\uNNNN`` escape (the same neutralisation Python's ``repr`` gives,
which is why the ``%r`` print sites are already safe), while leaving ordinary
text -- including tabs, newlines and non-ASCII/emoji -- untouched. Route every
untrusted-string terminal write through it.
"""

__all__ = ["sanitize_terminal", "safe_print", "sanitize_csv_field"]

# Bytes a terminal interprets as commands: the C0 controls (U+0000-U+001F) minus
# TAB and LF, the DEL (U+007F), and the C1 controls (U+0080-U+009F, which include
# the 8-bit CSI U+009B and OSC U+009D introducers). ESC (U+001B) is in the C0
# range, so ANSI/OSC sequences are neutralised at their introducer.
_ALLOWED_CONTROLS = frozenset("\t\n")

# Unicode explicit directional formatting characters (UAX #9). The override pair
# (LRO/RLO) forces a deceptive visual order regardless of the text, and any of
# them left unbalanced reorders the text that follows -- the "Trojan Source"
# spoof (CVE-2021-42574 / CWE-1007). Legitimate bidi text (Arabic/Hebrew) is
# reordered implicitly by the bidi algorithm and uses these only balanced and
# never uses the overrides, so overrides are neutralised always and the rest only
# when the string's directional nesting does not balance; balanced
# embeddings/isolates and the (harmless) direction marks pass through unchanged.
_BIDI_OVERRIDES = frozenset("\u202d\u202e")  # LRO, RLO
_BIDI_EMB_OPEN = frozenset("\u202a\u202b\u202d\u202e")  # LRE, RLE, LRO, RLO
_BIDI_ISO_OPEN = frozenset("\u2066\u2067\u2068")  # LRI, RLI, FSI
_BIDI_EMB_CLOSE = "\u202c"  # PDF
_BIDI_ISO_CLOSE = "\u2069"  # PDI
_BIDI_MARKS = frozenset("\u200e\u200f\u061c")  # LRM, RLM, ALM
_BIDI_ALL = (
    _BIDI_EMB_OPEN | _BIDI_ISO_OPEN | {_BIDI_EMB_CLOSE, _BIDI_ISO_CLOSE} | _BIDI_MARKS
)


def _bidi_is_balanced(text):
    """True if every embedding/override/isolate opener has a matching closer."""
    emb = iso = 0
    for char in text:
        if char in _BIDI_EMB_OPEN:
            emb += 1
        elif char == _BIDI_EMB_CLOSE:
            emb -= 1
            if emb < 0:
                return False
        elif char in _BIDI_ISO_OPEN:
            iso += 1
        elif char == _BIDI_ISO_CLOSE:
            iso -= 1
            if iso < 0:
                return False
    return emb == 0 and iso == 0


def sanitize_terminal(text):
    """Return *text* with terminal control characters replaced by visible escapes.

    Tabs and newlines are preserved; every other C0 control, DEL and C1 control
    is rendered as its ``\\xNN`` escape so it can never reach the terminal as a
    live control sequence. Bidirectional override characters, and any unbalanced
    directional formatting, are rendered as ``\\uNNNN`` to defeat Trojan-Source
    visual reordering while balanced Arabic/Hebrew bidi passes through unchanged.
    Ordinary printable text (including non-ASCII) is unchanged. Accepts any
    object; it is coerced with ``str`` first.
    """
    text = str(text)
    bidi_ok = _bidi_is_balanced(text)
    result = []
    for char in text:
        codepoint = ord(char)
        if char in _ALLOWED_CONTROLS:
            result.append(char)
        elif codepoint < 0x20 or codepoint == 0x7F or 0x80 <= codepoint <= 0x9F:
            result.append(f"\\x{codepoint:02x}")
        elif char in _BIDI_OVERRIDES or (char in _BIDI_ALL and not bidi_ok):
            result.append(f"\\u{codepoint:04x}")
        else:
            result.append(char)
    return "".join(result)


def safe_print(*values, sep=" ", **kwargs):
    """``print`` wrapper that sanitises each value with :func:`sanitize_terminal`.

    A drop-in for ``print`` when the arguments may contain untrusted text.
    """
    print(*(sanitize_terminal(v) for v in values), sep=sep, **kwargs)


# A leading one of these makes a spreadsheet evaluate a CSV cell as a formula, so
# crafted cell text can run a formula when the file is opened (CWE-1236). Leading
# whitespace is stripped before the test because a spreadsheet ignores it too.
_CSV_FORMULA_LEADS = ("=", "+", "-", "@")


def _looks_numeric(text):
    try:
        float(text)
        return True
    except ValueError:
        return False


def sanitize_csv_field(value):
    """Return *value* neutralised for writing as a CSV/TSV cell.

    Closes two hazards a later reader/opener would otherwise execute: control
    sequences that drive the terminal when the file is displayed (CWE-150, via
    :func:`sanitize_terminal`), and a leading ``= + - @`` that a spreadsheet runs
    as a formula (CWE-1236). A genuine number keeps its sign; any other value
    with a formula lead is prefixed with an apostrophe so the spreadsheet treats
    it as text. A non-string value (``None``, an int, a bool) is returned
    unchanged: the csv writer renders it safely (``None`` as an empty cell) and
    only a string can carry a control sequence or a formula lead.
    """
    if not isinstance(value, str):
        return value
    text = sanitize_terminal(value)
    lead = text.lstrip(" \t")
    if lead[:1] in _CSV_FORMULA_LEADS and not _looks_numeric(lead):
        text = "'" + text
    return text

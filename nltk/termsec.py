# Natural Language Toolkit: Terminal-output safety helpers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Neutralise terminal control sequences before untrusted text is written to a
terminal.

A value that an attacker can influence - a package ``id``/``name``/``filename``
from a (possibly MITM'd) download index, a tweet body from the network, corpus
content read from disk - can carry ANSI/OSC escape sequences. When such a
string is printed to a terminal, those sequences are *executed* by the terminal:
they can clear the screen, move the cursor, rewrite already-printed lines to spoof
output, set the window title, or (on some terminals) drive clipboard/hyperlink
actions (CWE-150, "Improper Neutralization of Escape, Meta, or Control
Sequences").

:func:`sanitize_terminal` turns every dangerous control byte into a visible
``\\xNN`` / ``\\uNNNN`` escape (the same neutralisation Python's ``repr`` gives,
which is why the ``%r`` print sites are already safe), while leaving ordinary
text - including tabs, newlines and non-ASCII/emoji - untouched. Route every
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
# them left unbalanced reorders the text that follows - the "Trojan Source"
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


# Format/structural characters with no legitimate role in a printed value that can
# hide, reorder, or inject line structure at a terminal (Trojan-Source family,
# invisible smuggling, line-break injection). Neutralised ALWAYS, like the bidi
# overrides - independent of bidi balance. The joiners U+200C/U+200D (ZWNJ/ZWJ)
# are deliberately NOT here: they are required for legitimate scripts and emoji.
_DANGEROUS_FORMAT = frozenset(
    chr(cp)
    for cp in (
        0x00AD,  # SOFT HYPHEN: invisible except at a rendered line break
        0x115F,
        0x1160,
        0x3164,
        0xFFA0,  # HANGUL FILLER family: zero-width, no role in a plain value
        0x180E,  # MONGOLIAN VOWEL SEPARATOR: zero-width (default-ignorable)
        0x2028,
        0x2029,  # LINE / PARAGRAPH SEPARATOR: injects a visual line break
        0x200B,
        0x2060,
        0xFEFF,  # ZERO WIDTH SPACE / WORD JOINER / ZWNBSP: invisible
        0x2061,
        0x2062,
        0x2063,
        0x2064,  # invisible math operators (function/times/separator/plus)
        0xFFF9,
        0xFFFA,
        0xFFFB,  # INTERLINEAR ANNOTATION anchor/separator/terminator
        *range(0x206A, 0x2070),  # deprecated format chars (symmetric swap, digit shape)
    )
)


def _is_dangerous(char, codepoint):
    return (
        char in _BIDI_OVERRIDES
        or char in _DANGEROUS_FORMAT
        or 0xE0000 <= codepoint <= 0xE01EF  # Tags block + variation-selector supplement
        or 0x1D173 <= codepoint <= 0x1D17A  # musical-symbol format controls (invisible)
        or 0xD800 <= codepoint <= 0xDFFF  # lone surrogate: crashes a terminal write
        or 0xFDD0 <= codepoint <= 0xFDEF  # noncharacters, never valid in interchange
        or (codepoint & 0xFFFE) == 0xFFFE  # plane noncharacters U+FFFE/U+FFFF/...
    )


def _escape(codepoint):
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    if codepoint <= 0xFFFF:
        return f"\\u{codepoint:04x}"
    return f"\\U{codepoint:08x}"


def _bidi_is_balanced(text):
    """True only if embeddings/overrides and isolates are STRICTLY nested (LIFO).

    Two independent counters would accept a *crossed* sequence like
    ``LRE LRI PDF PDI`` as balanced (each net-zero), letting a crafted reorder pass
    unsanitised. A single stack requires each PDF/PDI to close the most-recent
    opener of its own kind, so any crossing is rejected (and then neutralised).
    """
    stack = []
    for char in text:
        if char in _BIDI_EMB_OPEN:
            stack.append(_BIDI_EMB_CLOSE)
        elif char in _BIDI_ISO_OPEN:
            stack.append(_BIDI_ISO_CLOSE)
        elif char in (_BIDI_EMB_CLOSE, _BIDI_ISO_CLOSE):
            if not stack or stack[-1] != char:
                return False
            stack.pop()
    return not stack


def sanitize_terminal(text, *, single_line=False):
    """Return *text* with terminal control characters replaced by visible escapes.

    Tabs and newlines are preserved; every other C0 control, DEL and C1 control
    (the 8-bit ANSI/OSC/CSI/DCS introducers) is rendered as a visible ``\\xNN``
    escape so it can never reach the terminal as a live control sequence - this
    covers the whole ESC/CSI/OSC family (cursor moves, screen clears, OSC-8
    hyperlinks, OSC-52 clipboard writes, and terminal query/answerback sequences
    that would otherwise inject a reply into stdin). Bidi overrides and any
    unbalanced OR crossed directional nesting are escaped to defeat Trojan-Source
    reordering (CVE-2021-42574); balanced Arabic/Hebrew bidi passes through. Line
    and paragraph separators, deprecated/interlinear format controls, the invisible
    zero-width smuggling characters (soft hyphen, invisible math operators), the
    Unicode Tags block, lone surrogates (which would otherwise crash the write) and
    Unicode noncharacters are escaped too. Ordinary printable text (including
    non-ASCII and the ZWNJ/ZWJ joiners needed by real scripts) is unchanged.
    Accepts any object; it is coerced with ``str``.

    Set *single_line* for a value that must occupy one line (a filename, an id, a
    VCS ref): TAB and newline are then escaped too, so an embedded newline cannot
    forge a line and a tab cannot jump a column (the neutralisation GNU ls and git
    apply to such values). The default keeps TAB/newline for multi-line output.
    """
    text = str(text)
    allowed = frozenset() if single_line else _ALLOWED_CONTROLS
    bidi_ok = _bidi_is_balanced(text)
    result = []
    for char in text:
        codepoint = ord(char)
        if char in allowed:
            result.append(char)
        elif codepoint < 0x20 or codepoint == 0x7F or 0x80 <= codepoint <= 0x9F:
            result.append(_escape(codepoint))
        elif _is_dangerous(char, codepoint):
            result.append(_escape(codepoint))
        elif char in _BIDI_ALL and not bidi_ok:
            result.append(_escape(codepoint))
        else:
            result.append(char)
    return "".join(result)


def safe_print(*values, sep=" ", end="\n", **kwargs):
    """``print`` wrapper that sanitises each value with :func:`sanitize_terminal`.

    A drop-in for ``print`` when the arguments may contain untrusted text. The
    ``sep`` and ``end`` strings are sanitised too, so a caller-supplied separator
    cannot smuggle a control sequence; a ``sep``/``end`` of ``None`` keeps print's
    own default.
    """
    sep = sanitize_terminal(sep) if isinstance(sep, str) else sep
    end = sanitize_terminal(end) if isinstance(end, str) else end
    print(*(sanitize_terminal(v) for v in values), sep=sep, end=end, **kwargs)


# A leading one of these makes a spreadsheet evaluate a CSV cell as a formula, so
# crafted cell text can run a formula when the file is opened (CWE-1236). Leading
# whitespace is stripped before the test because a spreadsheet ignores it too.
_CSV_FORMULA_LEADS = ("=", "+", "-", "@")


def _looks_numeric(text):
    # float() also accepts inf/nan and digit-group underscores (1_0), which a
    # spreadsheet would NOT treat as a plain number, so the leading + / - is not a
    # genuine number sign there; reject them so the formula lead is still defused.
    lowered = text.lower()
    if "inf" in lowered or "nan" in lowered or "_" in text:
        return False
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
    # Strip every leading whitespace (space, tab, and any Unicode space such as a
    # no-break space) a spreadsheet skips before finding the formula lead.
    lead = text.lstrip()
    if lead[:1] in _CSV_FORMULA_LEADS and not _looks_numeric(lead):
        text = "'" + text
    return text

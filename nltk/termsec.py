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

# sanitize_csv_field is provided dynamically by __getattr__ below (it lives in
# nltk.csvsec); keeping it in __all__ preserves the historical star-import.
__all__ = ["sanitize_terminal", "safe_print", "sanitize_csv_field"]  # noqa: F822

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
# Other default-ignorables deliberately kept: variation selectors U+FE00-FE0F
# (emoji/CJK sequences), Mongolian FVS U+180B-180D/180F (legitimate Mongolian),
# and CGJ U+034F (Hebrew mark ordering, collation).
_DANGEROUS_FORMAT = frozenset(
    chr(cp)
    for cp in (
        0x00AD,  # SOFT HYPHEN: invisible except at a rendered line break
        0x115F,
        0x1160,
        0x3164,
        0xFFA0,  # HANGUL FILLER family: zero-width, no role in a plain value
        0x17B4,
        0x17B5,  # KHMER VOWEL INHERENT AQ/AA: deprecated, invisible
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
        0x2065,  # reserved default-ignorable between the operators and isolates
        0xFFF9,
        0xFFFA,
        0xFFFB,  # INTERLINEAR ANNOTATION anchor/separator/terminator
        *range(0xFFF0, 0xFFF9),  # reserved default-ignorables below the interlinear
        *range(0x1BCA0, 0x1BCA4),  # SHORTHAND FORMAT controls: invisible
        *range(0x206A, 0x2070),  # deprecated format chars (symmetric swap, digit shape)
    )
)


def _is_dangerous(char, codepoint):
    return (
        char in _BIDI_OVERRIDES
        or char in _DANGEROUS_FORMAT
        or 0xE0000 <= codepoint <= 0xE0FFF  # plane-14 DI: tags, VS supplement, reserved
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


# CPython refuses int-to-str conversion beyond sys.get_int_max_str_digits()
# digits (the CVE-2020-10735 mitigation), but big-integer applications disable
# that cap globally, and int-to-str is superlinear, so a crafted huge integer
# could then burn CPU at the write. The chokepoint keeps its own backstop: no
# printed value or CSV cell legitimately holds a >100,000-digit integer.
_INT_RENDER_BIT_LIMIT = 333_000  # about 100,000 decimal digits


def _refuse_int_bomb(value):
    """Refuse an integer too large to render.

    Only the real ``int`` tree can make the sanitiser itself perform the
    superlinear int-to-str conversion, so that is exactly what is checked:
    ``isinstance`` is the C-level type test, and the size is read with the
    UNBOUND builtin ``int.bit_length``, so a subclass overriding
    ``bit_length`` (or anything else) cannot underreport it: the payload is
    real even when the object lies. The guard looks up NOTHING on the object
    itself, so no attacker-defined attribute can steer or exploit it. A
    foreign big-integer type (a gmpy2 ``mpz``) is deliberately not probed:
    its text comes from its own ``__str__``, the same pre-existing exposure
    as any other object argument, and the sanitiser's own work stays linear
    in whatever text that produces.
    """
    if isinstance(value, int):
        bits = int.bit_length(value)
        if bits > _INT_RENDER_BIT_LIMIT:
            raise ValueError(
                f"integer of {bits} bits refused: too large to render "
                "as terminal or CSV output"
            )


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
    Accepts any object; it is coerced with ``str``, except an integer beyond
    the ~100,000-digit render backstop, which raises ``ValueError`` even when
    the interpreter's own int-to-str digit limit has been disabled.

    Set *single_line* for a value that must occupy one line (a filename, an id, a
    VCS ref): TAB and newline are then escaped too, so an embedded newline cannot
    forge a line and a tab cannot jump a column (the neutralisation GNU ls and git
    apply to such values). The default keeps TAB/newline for multi-line output.
    """
    _refuse_int_bomb(text)
    text = str(text)
    if type(text) is not str:
        # A subclass __str__ may return the subclass itself, whose __iter__,
        # __hash__ and __eq__ the scan below would consult. The unbound C slot
        # copies the REAL buffer into an exact str the subclass cannot lie to.
        text = str.__str__(text)
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


def safe_print(*values, sep=" ", end="\n", single_line=False, **kwargs):
    """``print`` wrapper that sanitises each value with :func:`sanitize_terminal`.

    A drop-in for ``print`` when the arguments may contain untrusted text. The
    ``sep`` and ``end`` strings are sanitised too, so a caller-supplied separator
    cannot smuggle a control sequence; a ``sep``/``end`` of ``None`` keeps print's
    own default. Set *single_line* to escape TAB and newline inside each VALUE
    as well (a filename, an id cannot then forge an extra line); ``sep`` and
    ``end`` keep default-mode sanitisation, so the trailing newline stays real.
    """
    sep = sanitize_terminal(sep) if isinstance(sep, str) else sep
    end = sanitize_terminal(end) if isinstance(end, str) else end
    print(
        *(sanitize_terminal(v, single_line=single_line) for v in values),
        sep=sep,
        end=end,
        **kwargs,
    )


def __getattr__(name):
    # CSV/TSV cell sanitisation lives in nltk.csvsec (whose SafeCsvWriter is
    # the intended API); this lazy re-export keeps the historical import
    # `from nltk.termsec import sanitize_csv_field` working without a cycle.
    if name == "sanitize_csv_field":
        from nltk.csvsec import sanitize_csv_field

        return sanitize_csv_field
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

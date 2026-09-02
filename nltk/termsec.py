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

__all__ = ["sanitize_terminal", "safe_print"]

# Bytes a terminal interprets as commands: the C0 controls (U+0000-U+001F) minus
# TAB and LF, the DEL (U+007F), and the C1 controls (U+0080-U+009F, which include
# the 8-bit CSI U+009B and OSC U+009D introducers). ESC (U+001B) is in the C0
# range, so ANSI/OSC sequences are neutralised at their introducer.
_ALLOWED_CONTROLS = frozenset("\t\n")


def sanitize_terminal(text):
    """Return *text* with terminal control characters replaced by visible escapes.

    Tabs and newlines are preserved; every other C0 control, DEL and C1 control
    is rendered as its ``\\xNN`` escape so it can never reach the terminal as a
    live control sequence. Ordinary printable text (including non-ASCII) is
    unchanged. Accepts any object; it is coerced with ``str`` first.
    """
    result = []
    for char in str(text):
        codepoint = ord(char)
        if char in _ALLOWED_CONTROLS:
            result.append(char)
        elif codepoint < 0x20 or codepoint == 0x7F or 0x80 <= codepoint <= 0x9F:
            result.append(f"\\x{codepoint:02x}")
        else:
            result.append(char)
    return "".join(result)


def safe_print(*values, sep=" ", **kwargs):
    """``print`` wrapper that sanitises each value with :func:`sanitize_terminal`.

    A drop-in for ``print`` when the arguments may contain untrusted text.
    """
    print(*(sanitize_terminal(v) for v in values), sep=sep, **kwargs)

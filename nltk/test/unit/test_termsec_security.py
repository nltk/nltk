# Natural Language Toolkit: terminal-control-sequence (CWE-150) attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack matrix for nltk.termsec.sanitize_terminal, the chokepoint every
untrusted-text terminal write routes through (the downloader's server-supplied
package index, TweetViewer's network tweet text). A neutralised string must
contain no live control byte a terminal could execute, while benign text is
unchanged."""

import pytest

from nltk.termsec import safe_print, sanitize_terminal

# Every byte a terminal may act on: C0 controls except TAB/LF, DEL, and C1.
_DANGEROUS = (
    [chr(c) for c in range(0x00, 0x20) if chr(c) not in "\t\n"]
    + [chr(0x7F)]
    + [chr(c) for c in range(0x80, 0xA0)]
)


@pytest.mark.parametrize(
    "payload",
    [
        "\x1b[2J\x1b[H",  # clear screen + home
        "\x1b[31mred\x1b[0m",  # SGR colour
        "\x1b]0;pwned-title\x07",  # OSC window-title set + BEL
        "\x1b]8;;http://evil\x07link\x1b]8;;\x07",  # OSC 8 hyperlink
        "safe\x08\x08\x08\x08evil",  # backspaces overwrite
        "line1\rSPOOFED",  # carriage-return line rewrite
        "\x9bpwn",  # 8-bit CSI (C1)
        "\x9d0;title\x07",  # 8-bit OSC (C1)
        "a\x7fb",  # DEL
        "pkg\x1b[2K\rlegit-looking",  # realistic package-name injection
    ],
)
def test_control_sequences_are_neutralised(payload):
    out = sanitize_terminal(payload)
    # No ESC, no C1, no bare C0/DEL control survives (TAB/LF excepted).
    for ch in out:
        assert ch in "\t\n" or not (
            ord(ch) < 0x20 or ord(ch) == 0x7F or 0x80 <= ord(ch) <= 0x9F
        ), f"control byte {ch!r} survived in {out!r}"
    assert "\x1b" not in out


@pytest.mark.parametrize("ctrl", _DANGEROUS)
def test_every_dangerous_control_byte_is_escaped(ctrl):
    out = sanitize_terminal(f"x{ctrl}y")
    assert ctrl not in out
    assert out == f"x\\x{ord(ctrl):02x}y"


def test_benign_text_passes_through_unchanged():
    for benign in [
        "Perfectly normal package name",
        "with\ttabs\tand\nnewlines",
        "unicode: café 模型 naïve 😀",
        "punctuation !@#$%^&*()_+-=[]{};:'\",.<>/?",
        "",
    ]:
        assert sanitize_terminal(benign) == benign


def test_accepts_non_string_input():
    assert sanitize_terminal(1234) == "1234"
    assert sanitize_terminal(None) == "None"


def test_safe_print_sanitises(capsys):
    safe_print("evil\x1b[2Jtitle")
    out = capsys.readouterr().out
    assert "\x1b" not in out and "evil" in out


def test_downloader_show_and_tweetviewer_route_through_termsec():
    # Source-pin: the fixed sinks call sanitize_terminal.
    import inspect

    import nltk.downloader as dl

    dsrc = inspect.getsource(dl)
    assert "sanitize_terminal(s)" in dsrc  # the show() chokepoint
    assert "sanitize_terminal(info.id)" in dsrc  # list()
    assert "sanitize_terminal(child_id)" in dsrc  # _update_index()

# Natural Language Toolkit: terminal-control-sequence (CWE-150) attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack matrix for nltk.termsec.sanitize_terminal, the sanitiser untrusted text
(a server-supplied package id from the download index, a network tweet body,
corpus content read from disk) is routed through before a terminal write. A
neutralised string must contain no live control byte a terminal could execute,
while benign text is unchanged. This exercises the sanitiser directly."""

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


def test_safe_print_sanitises_sep_and_end(capsys):
    # a caller-supplied separator or terminator must not smuggle a live sequence
    safe_print("a", "b", sep="\x1b[31m", end="\x1b]0;pwn\x07\n")
    out = capsys.readouterr().out
    assert "\x1b" not in out
    assert "a" in out and "b" in out


def test_safe_print_sep_none_keeps_default(capsys):
    safe_print("a", "b", sep=None)
    assert capsys.readouterr().out == "a b\n"


def test_safe_print_does_not_crash_on_lone_surrogate(capsys):
    # a lone surrogate would raise UnicodeEncodeError on a naive print
    safe_print("pkg" + chr(0xD800) + "evil")
    out = capsys.readouterr().out
    assert chr(0xD800) not in out
    assert "\\ud800" in out


class TestSingleLineMode:
    """single_line=True is for a value that must occupy one line (a filename, id,
    VCS ref): TAB and newline are escaped too, matching ls/git. The default must
    stay unchanged (TAB/newline kept) so nothing is relaxed."""

    def test_default_keeps_tab_and_newline(self):
        assert sanitize_terminal("a\tb\nc") == "a\tb\nc"

    def test_single_line_escapes_tab_and_newline(self):
        assert sanitize_terminal("a\tb\nc", single_line=True) == "a\\x09b\\x0ac"

    def test_single_line_defuses_newline_injection(self):
        # a crafted filename must not forge a second line
        out = sanitize_terminal(
            "safe.txt\nInstalling malware... done", single_line=True
        )
        assert "\n" not in out and "safe.txt" in out

    def test_single_line_still_escapes_controls_and_keeps_text(self):
        out = sanitize_terminal("café\n\x1b[2J😀", single_line=True)
        assert out == "café\\x0a\\x1b[2J😀"
        assert "\x1b" not in out

    @pytest.mark.parametrize(
        "payload", ["\r", "\t", "\n", "\x1b[2J", "\x9b31m", chr(0x202E) + "evil"]
    )
    def test_single_line_output_has_no_raw_control(self, payload):
        # single_line allows NO control, so its output is a strict superset of the
        # default neutralisation: not one C0/DEL/C1 byte survives.
        strict = sanitize_terminal("x" + payload + "y", single_line=True)
        assert not any(
            ord(ch) < 0x20 or ord(ch) == 0x7F or 0x80 <= ord(ch) <= 0x9F
            for ch in strict
        )
        assert "\x1b" not in strict

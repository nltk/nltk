# Natural Language Toolkit: terminal-injection sink tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests that the print() sinks which emit untrusted string data now
route through ``nltk.termsec.safe_print``, so a crafted corpus token carrying an
ANSI escape / C1 control / bidi override can never reach the terminal live
(CWE-150 / 1007 / 1236). Verified through the real public output methods, not a
mock: a raw ESC byte must be rendered as a visible ``\\x1b`` escape."""


class TestPrintSinksNeutralizeInjection:
    def test_freqdist_tabulate(self, capsys):
        from nltk.probability import FreqDist

        FreqDist(["\x1b[31mevil", "safe"]).tabulate()
        out = capsys.readouterr().out
        assert "\x1b" not in out  # raw ESC never emitted
        assert "\\x1b" in out  # rendered visibly instead

    def test_conditional_freqdist_tabulate(self, capsys):
        from nltk.probability import ConditionalFreqDist

        cfd = ConditionalFreqDist()
        cfd["\x1b[31mcond"]["\x1b[32msample"] += 1
        cfd.tabulate()
        out = capsys.readouterr().out
        assert "\x1b" not in out

    def test_bidi_override_is_neutralized(self):
        from nltk.termsec import sanitize_terminal

        # Trojan-Source RLO override must not pass through unbalanced.
        assert "‮" not in sanitize_terminal("a‮evil")

    def test_safe_print_is_identity_for_clean_text(self, capsys):
        from nltk.termsec import safe_print

        safe_print("ordinary café text 3.14")
        assert capsys.readouterr().out == "ordinary café text 3.14\n"

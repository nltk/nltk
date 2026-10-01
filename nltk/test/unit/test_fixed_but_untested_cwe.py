# Natural Language Toolkit: regression tests for fixed-but-unprobed weaknesses
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Adversarial tests for hardening that was applied but never had a test driving
the exploit: the WordNet-browser shutdown CSRF token + loopback bind
(CWE-352 / CWE-306) and the ShiftReduceParser reduce-loop time bound
(CWE-835 / CWE-674). Each drives the real code path."""

import pytest


class TestWordnetShutdownCsrf:
    def _handler(self):
        from nltk.app import wordnet_app as wa

        h = object.__new__(wa.MyServerHandler)
        return h, wa

    def test_shutdown_without_token_is_refused(self):
        h, wa = self._handler()
        h.path = "/SHUTDOWN THE SERVER"
        assert h._shutdown_authorized() is False

    def test_shutdown_with_wrong_token_is_refused(self):
        h, wa = self._handler()
        h.path = "/SHUTDOWN THE SERVER?token=guessed-value"
        assert h._shutdown_authorized() is False

    def test_shutdown_with_the_process_token_is_authorized(self):
        h, wa = self._handler()
        h.path = "/SHUTDOWN THE SERVER?token=" + wa._shutdown_token
        assert h._shutdown_authorized() is True

    def test_token_is_a_high_entropy_per_process_secret(self):
        from nltk.app import wordnet_app as wa

        assert len(wa._shutdown_token) >= 32  # secrets.token_urlsafe(32)

    def test_server_binds_loopback_only(self):
        # CWE-306: the server must bind 127.0.0.1 so a remote host cannot reach
        # the unauthenticated pages / shutdown route.
        import inspect

        from nltk.app import wordnet_app as wa

        src = inspect.getsource(wa)
        assert 'HTTPServer(("127.0.0.1"' in src
        assert 'HTTPServer(("0.0.0.0"' not in src and 'HTTPServer(("", ' not in src


class TestShiftReduceTimeBound:
    def test_reduce_loop_deadline_fires(self, monkeypatch):
        from nltk import CFG
        from nltk.parse.shiftreduce import ShiftReduceParser

        # A reducer that always "makes progress" is the pathological case the
        # bound exists for (a cyclic unit grammar can produce one); the
        # wall-clock deadline must break the otherwise-infinite reduce loop.
        grammar = CFG.fromstring("S -> 'x'")
        parser = ShiftReduceParser(grammar, max_time=0.3)
        monkeypatch.setattr(parser, "_reduce", lambda *a, **k: True)
        with pytest.raises(TimeoutError):
            list(parser.parse(["x"]))

    def test_normal_grammar_still_parses(self):
        from nltk import CFG
        from nltk.parse.shiftreduce import ShiftReduceParser

        grammar = CFG.fromstring(
            """
            S -> NP VP
            NP -> 'the' 'dog'
            VP -> 'barks'
            """
        )
        parser = ShiftReduceParser(grammar, max_time=5.0)
        trees = list(parser.parse(["the", "dog", "barks"]))
        assert trees and str(trees[0].label()) == "S"

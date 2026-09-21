"""Regression tests for nltk.help tag-pattern handling.

``_format_tagset`` compiles a caller-supplied tag pattern through ``nltk.redos``,
which refuses a source larger than ``MAX_PATTERN_LENGTH`` as a compile-time DoS
guard. An oversized pattern must degrade with a clear message rather than
surfacing the raw refusal as an uncaught exception; ordinary patterns are
unaffected.
"""

import pytest

import nltk.help as help_module
import nltk.redos as redos


def _tagset_available():
    from nltk.data import find

    try:
        find("help/tagsets_json/PY3_json/")
        return True
    except LookupError:
        return False


@pytest.mark.skipif(not _tagset_available(), reason="upenn_tagset data unavailable")
def test_ordinary_tagpattern_prints_matches(capsys):
    help_module._format_tagset("upenn_tagset", "NN")
    out = capsys.readouterr().out
    assert "NN" in out
    assert "Invalid or oversized" not in out


@pytest.mark.skipif(not _tagset_available(), reason="upenn_tagset data unavailable")
def test_oversized_tagpattern_degrades_gracefully(capsys):
    oversized = "N" * (redos.MAX_PATTERN_LENGTH + 10)
    # Must not raise: the redos refusal is caught and reported.
    help_module._format_tagset("upenn_tagset", oversized)
    out = capsys.readouterr().out
    assert "Invalid or oversized tag pattern" in out

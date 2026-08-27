# Natural Language Toolkit: the sandbox must not break ordinary NLTK use
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""With ENFORCE on and the real data roots, ordinary NLTK must still work.

Most security tests narrow ``nltk.data.path`` to a single throwaway root so an
attack target can be staged outside it. That is deliberate, but it also means
those tests say nothing about whether a NORMAL installation still functions:
under a narrowed path a corpus is simply absent, which is a very different
thing from the sandbox refusing it.

This file pins both halves of that distinction:

* with the real roots in place and ``ENFORCE`` on, the standard entry points
  load real data and produce real output;
* when a corpus genuinely is not on the path, the failure is ``LookupError``
  ("not found"), never ``PermissionError`` ("refused"). If the sandbox ever
  starts refusing legitimate in-root data, that difference is what catches it.
"""

import os
import tempfile

import pytest

import nltk
import nltk.data
from nltk import pathsec


@pytest.fixture
def enforced_real_roots(monkeypatch):
    """ENFORCE on, with the machine's real data roots left in place."""
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    return nltk.data.path


def _run_or_skip(call):
    """Run the real call; skip only if the DATA is genuinely absent.

    The check is the call itself rather than a guessed nltk.data.find() name:
    several corpora resolve through a zip or a lazy loader, so find("corpora/x")
    can raise for a corpus that loads perfectly well, which produced skips for
    data that was actually present.
    """
    try:
        return call()
    except LookupError:
        pytest.skip("data unavailable on this machine")


@pytest.mark.parametrize(
    "call, check",
    [
        (
            lambda: __import__("nltk").tokenize.word_tokenize("The dog barks."),
            lambda r: "dog" in r,
        ),
        (lambda: nltk.pos_tag(["The", "dog"]), lambda r: len(r) == 2),
        (
            lambda: __import__(
                "nltk.corpus", fromlist=["wordnet"]
            ).wordnet.synsets("dog")[0].name(),
            lambda r: r.startswith("dog."),
        ),
        (
            lambda: __import__(
                "nltk.corpus", fromlist=["stopwords"]
            ).stopwords.words("english"),
            lambda r: "the" in r,
        ),
        (
            lambda: __import__(
                "nltk.corpus", fromlist=["brown"]
            ).brown.tagged_words()[:1],
            lambda r: len(r) == 1,
        ),
        (
            lambda: __import__(
                "nltk.corpus", fromlist=["treebank"]
            ).treebank.parsed_sents()[0].label(),
            lambda r: r == "S",
        ),
        (
            lambda: __import__(
                "nltk.tag", fromlist=["PerceptronTagger"]
            ).PerceptronTagger().tag(["dog"]),
            lambda r: r[0][0] == "dog",
        ),
    ],
    ids=[
        "word_tokenize",
        "pos_tag",
        "wordnet",
        "stopwords",
        "brown",
        "treebank",
        "perceptron_tagger",
    ],
)
def test_real_data_still_loads_under_enforce(enforced_real_roots, call, check):
    """The sandbox must never refuse data that legitimately lives in a root."""
    assert pathsec.ENFORCE is True
    assert check(_run_or_skip(call)), "loaded, but not the result the caller expects"


def test_missing_data_is_lookuperror_not_permissionerror(monkeypatch):
    """Absence and refusal must stay distinguishable.

    A narrowed data path means the corpus is not there to find, which is a
    LookupError. A PermissionError here would mean the sandbox had started
    rejecting a legitimate read, which is the failure this whole guard set is
    supposed to avoid.
    """
    empty_root = tempfile.mkdtemp(prefix="nltk_empty_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [empty_root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    nltk.data.clear_cache()

    with pytest.raises(LookupError) as caught:
        nltk.data.find("corpora/definitely_not_a_real_corpus")
    assert not isinstance(caught.value, PermissionError)


def test_enforce_is_actually_on_by_default():
    """A guard set that ships with ENFORCE off would test nothing in production."""
    assert pathsec.ENFORCE is True

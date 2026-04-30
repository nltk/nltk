# Natural Language Toolkit: Interactive Transcription -- Morphological Acceptors
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Pluggable morphological acceptors for interactive transcription.

A *morphological acceptor* answers two questions about candidate
expansions of a known lexeme:

1. Does this candidate string represent a morphotactically valid word
   in the language?  (:meth:`MorphologicalAcceptor.accepts`)
2. What words are licensed by the grammar that contain this lexeme?
   (:meth:`MorphologicalAcceptor.expand`)

Lane and Bird (2022) use a hand-built FOMA/HFST analyser for Bininj
Kunwok (Lane and Bird, 2019).  In NLTK we provide an abstract base
class plus a :class:`WordlistAcceptor` reference implementation that
treats a flat wordlist as the language.  Field linguists with an
existing FST can subclass :class:`MorphologicalAcceptor` to plug their
analyser in --- the rest of the pipeline (constraints,
:class:`InteractiveTranscriber`) does not change.

References
----------
Lane, W. and Bird, S. (2019). Towards a robust morphological analyzer
for Kunwinjku. In *Proceedings of ALTA*, 1-9.

Lane, W. and Bird, S. (2022). A Finite State Approach to Interactive
Transcription. In *Proceedings of the First Workshop on NLP
Applications to Field Linguistics*, 1-10.
"""

from abc import ABC, abstractmethod


class MorphologicalAcceptor(ABC):
    """
    Abstract base class for a morphological acceptor.

    The acceptor is plugged into :class:`~nltk.transcribe.completion.InteractiveTranscriber`
    and used by GEN to filter candidate expansions of an anchor lexeme
    to those that are morphotactically valid.

    Subclasses must implement :meth:`accepts` and :meth:`expand`.
    """

    @abstractmethod
    def accepts(self, word: str) -> bool:
        """Return ``True`` iff ``word`` is a morphotactically valid word."""

    @abstractmethod
    def expand(self, lexeme: str):
        """
        Yield words licensed by the grammar that contain ``lexeme`` as a substring.

        For a wordlist acceptor this is a simple containment scan; for
        a finite-state morphological analyser it would be a regular
        composition with ``?* lexeme ?*``.
        """


class WordlistAcceptor(MorphologicalAcceptor):
    """
    A reference :class:`MorphologicalAcceptor` backed by a flat list of words.

    This is appropriate for early-stage fieldwork where a small lexicon
    of attested forms exists but no full FST analyser has yet been
    built.  As the lexicon grows, the same code paths continue to
    work; replacing this with an HFST/FOMA-backed acceptor is a
    drop-in change.

    Parameters
    ----------
    words : Iterable[str]
        The words licensed by the grammar.

    Examples
    --------
    >>> from nltk.transcribe.acceptor import WordlistAcceptor
    >>> a = WordlistAcceptor(["kabirridurrkmirri", "kabirri", "manme"])
    >>> a.accepts("kabirri")
    True
    >>> sorted(a.expand("kabirri"))
    ['kabirri', 'kabirridurrkmirri']
    """

    def __init__(self, words):
        self._words = frozenset(words)

    def accepts(self, word: str) -> bool:
        return word in self._words

    def expand(self, lexeme: str):
        if not lexeme:
            return list(self._words)
        return [w for w in self._words if lexeme in w]

    def __len__(self):
        return len(self._words)

    def __iter__(self):
        return iter(self._words)

    def __contains__(self, word):
        return word in self._words

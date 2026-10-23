# Natural Language Toolkit: Interactive Transcription -- OT Constraints
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Optimality-theoretic constraints for interactive transcription.

The OT framework (Prince and Smolensky, 2004) treats a candidate set
through a ranked sequence of constraints.  A high-ranked constraint
filters first; a candidate that violates it loses to any candidate that
does not.  Where *all* candidates would be eliminated by a constraint,
that constraint is skipped (Karttunen 1998's *lenient composition*),
and the survivors fall through to the next constraint.

This module provides a small, dependency-free implementation of that
semantics that operates on Python objects instead of FSTs.  It is
intended to be combined with the candidate generator in
:mod:`nltk.transcribe.completion` to reproduce the algorithm of Lane
and Bird (2022), but the constraints are general and may be reused for
any OT-style ranking task.

References
----------
Karttunen, L. (1998). The proper treatment of optimality in
computational phonology. In *Finite State Methods in Natural Language
Processing*.

Lane, W. and Bird, S. (2022). A Finite State Approach to Interactive
Transcription. In *Proceedings of the First Workshop on NLP
Applications to Field Linguistics*, 1-10.

Prince, A. and Smolensky, P. (2004). *Optimality Theory: Constraint
interaction in generative grammar*. John Wiley & Sons.
"""

from abc import ABC, abstractmethod


class Constraint(ABC):
    """
    Abstract base class for an OT constraint.

    A constraint maps a candidate to a non-negative integer count of
    *violations*.  ``0`` means the candidate fully satisfies the
    constraint; higher numbers indicate worse violations.  In the
    classic OT tableau, each violation is rendered as one ``*``.

    Subclasses must implement :meth:`violations`.  The ``name``
    attribute is used by :class:`~nltk.transcribe.tableau.Tableau` and
    in repr output.
    """

    name: str = "Constraint"

    @abstractmethod
    def violations(self, candidate) -> int:
        """Return the number of times *candidate* violates this constraint."""

    def __call__(self, candidate) -> int:
        return self.violations(candidate)

    def __repr__(self):
        return f"<{type(self).__name__}: {self.name}>"


class AnchoredConstraint(Constraint):
    """
    Candidate must contain at least one of the *known lexemes* as a
    contiguous substring.

    This corresponds to the ``AnchoredWords`` constraint of Lane and
    Bird (2022, Fig. 5, line 35): ``[?+ LEXEMES] | [LEXEMES ?+] | [?+
    LEXEMES ?+]``.  The intuition is that we should not hallucinate
    completions that are unmoored from anything the transcriber has
    already heard.

    Parameters
    ----------
    lexemes : Iterable[str]
        The known lexemes the transcriber has confirmed in this
        utterance, in any order.
    name : str, optional
        Display name for the constraint.  Defaults to ``"Anchored"``.

    Examples
    --------
    >>> from nltk.transcribe.constraints import AnchoredConstraint
    >>> c = AnchoredConstraint(["kabirri", "manme"])
    >>> c.violations("kabirridurrkmirri")
    0
    >>> c.violations("bedberre")
    1
    """

    def __init__(self, lexemes, name="Anchored"):
        self.lexemes = tuple(lexemes)
        self.name = name

    def violations(self, candidate) -> int:
        word = _candidate_word(candidate)
        for lexeme in self.lexemes:
            if lexeme and lexeme in word:
                return 0
        return 1


class LexicalConstraint(Constraint):
    """
    Candidate's surface word must appear in a given lexicon.

    Lane and Bird (2022) use two such constraints --- ``Topical`` (words
    drawn from related transcribed audio in the same domain) and
    ``Attested`` (words drawn from a wider corpus).  Both are instances
    of this class with different lexica and different rank.

    Parameters
    ----------
    lexicon : Iterable[str] or set
        The set of acceptable surface forms.
    name : str
        Display name for the constraint.  By convention,
        ``"Attested"`` for a corpus-wide list, ``"Topical"`` for a
        domain-specific list.
    """

    def __init__(self, lexicon, name):
        self.lexicon = frozenset(lexicon)
        self.name = name

    def violations(self, candidate) -> int:
        word = _candidate_word(candidate)
        return 0 if word in self.lexicon else 1


class EditConstraint(Constraint):
    """
    Candidate must have *at most* ``max_edits`` edit-distance violations
    against the underlying phone string.

    Lane and Bird (2022) split this into two constraints --- ``edit1``
    and ``edit2`` --- ranked at the bottom of the hierarchy as a
    tie-breaker between candidates that are otherwise equally well
    supported by anchored, attested and topical constraints.  Each
    candidate carries a count of how many edits were required to
    license it (``"^"`` markers in their formulation).

    Parameters
    ----------
    max_edits : int
        Inclusive upper bound on edits.  A candidate with more edits
        than this is in violation.
    name : str, optional
        Display name.  Defaults to ``"Edit<=max_edits>"``.
    """

    def __init__(self, max_edits, name=None):
        self.max_edits = int(max_edits)
        self.name = name or f"Edit<={self.max_edits}"

    def violations(self, candidate) -> int:
        edits = _candidate_edits(candidate)
        return 0 if edits <= self.max_edits else (edits - self.max_edits)


def lenient_compose(candidates, *constraints):
    """
    Apply Karttunen-style lenient composition over ``candidates``.

    For each constraint in ``constraints``, partition the surviving
    candidates into those that satisfy the constraint (zero violations)
    and those that do not.  If the satisfying set is non-empty, it
    becomes the new survivor set; otherwise *all* candidates fall
    through unchanged.  This is the OT operationalisation that Lane and
    Bird (2022, Sec. 4.2) use to evaluate candidates from highest to
    lowest ranked constraint.

    Parameters
    ----------
    candidates : Iterable
        The output of GEN.  May be strings or any object accepted by
        the supplied constraints.
    *constraints : Constraint
        Ranked from highest priority to lowest.  Earlier constraints
        outrank later ones.

    Returns
    -------
    list
        The optimal candidate set.

    Examples
    --------
    >>> from nltk.transcribe.constraints import (
    ...     AnchoredConstraint, LexicalConstraint, lenient_compose)
    >>> cands = ["kabirridurrkmirri", "kabirriXX", "bedberre"]
    >>> anchored = AnchoredConstraint(["kabirri"])
    >>> attested = LexicalConstraint({"kabirridurrkmirri"}, "Attested")
    >>> lenient_compose(cands, anchored, attested)
    ['kabirridurrkmirri']
    """
    survivors = list(candidates)
    for constraint in constraints:
        passing = [c for c in survivors if constraint(c) == 0]
        if passing:
            survivors = passing
        # else: lenient -- everyone falls through unchanged
    return survivors


def _candidate_word(candidate):
    """Return the surface word of a candidate, whether it is a string or a Candidate."""
    if isinstance(candidate, str):
        return candidate
    return getattr(candidate, "word", str(candidate))


def _candidate_edits(candidate):
    """Return the edit count of a candidate, defaulting to 0 for plain strings."""
    return getattr(candidate, "edits", 0)

# Natural Language Toolkit: Interactive Transcription -- Alignment
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Phone-to-orthography mapping and edit-distance bounded alignment.

The interactive transcription model of Lane and Bird (2022) takes as
input a noisy phone string from a phone recogniser (e.g. Allosaurus,
Li et al. 2020) and an ordered list of *known lexemes* identified by a
human transcriber.  Before constraints can be evaluated, candidates
must be aligned: each known lexeme has to be located in the phone
stream within a small edit budget.

This module provides two pieces:

1. :class:`PhoneOrthMapping` -- a one-to-many mapping from phones to
   orthographic alternatives, used to convert noisy phone output into
   the orthography in which the lexicon and the morphological
   acceptor speak.  This corresponds to the ``PHONES2ORTH`` FST in
   Lane and Bird (2022, Fig. 5).

2. :func:`anchor_positions` -- find every substring of an orthographic
   string that aligns to a target lexeme within a given edit budget.
   This is the explicit, dependency-free analogue of composing
   ``LexemePattern`` with ``Edit1`` and ``Edit2`` in Lane and Bird
   (2022, Fig. 5, lines 17-19).

References
----------
Lane, W. and Bird, S. (2022). A Finite State Approach to Interactive
Transcription. In *Proceedings of the First Workshop on NLP
Applications to Field Linguistics*, 1-10.
"""

from dataclasses import dataclass


class PhoneOrthMapping:
    """
    A one-to-many mapping from phone symbols to orthographic strings.

    Phone recognisers emit IPA-like symbols; the orthography of a
    language may use multigraphs (``ng``, ``rr``, ``kk``).  A single
    phone may correspond to several orthographic forms, and the
    mapping is therefore represented as ``phone -> list[str]``.

    The :meth:`expand` method rewrites a phone string into the
    *orthography lattice* over which alignment will be performed.  For
    simplicity in this Python implementation, ``expand`` returns the
    Cartesian product of choices as a generator -- callers should
    apply edit-distance early (via :func:`anchor_positions`) rather
    than enumerating the full set.

    Parameters
    ----------
    mapping : dict[str, list[str]]
        Mapping from phone symbol to a list of orthographic
        realisations.  An empty list means *delete*.

    Examples
    --------
    >>> from nltk.transcribe.align import PhoneOrthMapping
    >>> m = PhoneOrthMapping({"k": ["k", "kk"], "N": ["ng"], "i": ["i"]})
    >>> sorted(m.realisations("k"))
    ['k', 'kk']
    >>> m.realisations("z")        # unknown phone -- pass through
    ['z']
    """

    def __init__(self, mapping):
        self._mapping = {p: list(orths) for p, orths in mapping.items()}

    def realisations(self, phone):
        """Return the orthographic alternatives for a single phone."""
        return list(self._mapping.get(phone, [phone]))

    def expand(self, phone_string):
        """
        Yield orthographic strings corresponding to ``phone_string``.

        Each phone is expanded independently.  Use sparingly: the
        number of strings is the product of branching factors.
        """
        return _cartesian_expand(phone_string, self._mapping)

    def to_canonical(self, phone_string):
        """
        Return a *canonical* (first-listed) orthographic realisation
        of ``phone_string``.  Useful as a deterministic starting point
        for alignment when full lattice exploration is too expensive.
        """
        out = []
        for ph in phone_string:
            out.append(self.realisations(ph)[0])
        return "".join(out)


def _cartesian_expand(phone_string, mapping):
    if not phone_string:
        yield ""
        return
    head, *tail = phone_string
    options = mapping.get(head, [head])
    for opt in options:
        for rest in _cartesian_expand(tail, mapping):
            yield opt + rest


@dataclass(frozen=True)
class Anchor:
    """
    A single placement of a known lexeme inside an orthographic string.

    Attributes
    ----------
    lexeme : str
        The known lexeme being aligned.
    start : int
        Character index in the orthographic string where the lexeme
        match begins (inclusive).
    end : int
        Character index where the match ends (exclusive).
    edits : int
        Edit distance between ``orth[start:end]`` and ``lexeme``.
    """

    lexeme: str
    start: int
    end: int
    edits: int


def anchor_positions(orth, lexeme, max_edits=None):
    """
    Find every substring of ``orth`` that matches ``lexeme`` within
    ``max_edits`` Levenshtein operations.

    This is the dependency-free analogue of composing ``LexemePattern``
    with ``Edit1``/``Edit2`` in Lane and Bird (2022, Fig. 5, lines
    17-19) for a single lexeme.  The default edit budget follows their
    heuristic: 1 edit for short lexemes (length <= 3), 2 otherwise.

    Parameters
    ----------
    orth : str
        Orthographic string in which to align.
    lexeme : str
        Lexeme to locate.
    max_edits : int, optional
        Maximum number of edits permitted in a successful match.  If
        ``None``, defaults to ``1`` for ``len(lexeme) <= 3`` and ``2``
        otherwise.

    Returns
    -------
    list[Anchor]
        All matches sorted by ``(edits, start)``.

    Examples
    --------
    >>> from nltk.transcribe.align import anchor_positions
    >>> matches = anchor_positions("kabirridurrkmirri", "kabirri")
    >>> [(a.start, a.end, a.edits) for a in matches][0]
    (0, 7, 0)

    A near-miss with one substitution is still reported when the
    budget allows it:

    >>> [(a.start, a.end, a.edits) for a in
    ...  anchor_positions("kbirridurrkmirri", "kabirri", max_edits=1)][0]
    (0, 6, 1)
    """
    if max_edits is None:
        max_edits = 1 if len(lexeme) <= 3 else 2

    matches = []
    L = len(lexeme)
    N = len(orth)
    # Sliding window: try every substring of length L-max_edits .. L+max_edits
    for window in range(max(1, L - max_edits), L + max_edits + 1):
        for start in range(0, N - window + 1):
            end = start + window
            d = _bounded_levenshtein(orth[start:end], lexeme, max_edits)
            if d <= max_edits:
                matches.append(Anchor(lexeme, start, end, d))
    matches.sort(key=lambda a: (a.edits, a.start, a.end))
    return _dedupe_anchors(matches)


def _dedupe_anchors(anchors):
    """Drop dominated anchors -- if two anchors have the same span, keep the lower-edit one."""
    seen = {}
    for a in anchors:
        key = (a.start, a.end, a.lexeme)
        if key not in seen or a.edits < seen[key].edits:
            seen[key] = a
    return sorted(seen.values(), key=lambda a: (a.edits, a.start, a.end))


def _bounded_levenshtein(s, t, bound):
    """
    Levenshtein distance between ``s`` and ``t``, returning early with
    a value strictly greater than ``bound`` if exceeded.  Uses O(min(|s|,|t|))
    rolling rows.
    """
    if abs(len(s) - len(t)) > bound:
        return bound + 1
    if len(s) < len(t):
        s, t = t, s
    n, m = len(s), len(t)
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        row_min = curr[0]
        for j in range(1, m + 1):
            cost = 0 if s[i - 1] == t[j - 1] else 1
            curr[j] = min(
                prev[j] + 1,  # deletion
                curr[j - 1] + 1,  # insertion
                prev[j - 1] + cost,  # substitution
            )
            if curr[j] < row_min:
                row_min = curr[j]
        if row_min > bound:
            return bound + 1
        prev = curr
    return prev[m]

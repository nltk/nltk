# Natural Language Toolkit: Interactive Transcription -- Word Completion
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interactive word completion for morphologically complex languages.

This module is a Python port of the Local Word Discovery with implicit
alignment (LWD-A) algorithm of Lane and Bird (2022).  The algorithm
takes a noisy phone string from a phone recogniser plus a set of
*known lexemes* identified by a human transcriber, and proposes
ranked, morphotactically valid completions anchored at each known
lexeme.  The constraint hierarchy ``anchored >> attested >> topical >>
edit`` is evaluated using lenient composition (Karttunen, 1998) over
the candidate set.

The module is dependency-free: no FOMA, HFST or pynini binding is
required.  Users with an existing FST analyser may plug it in by
subclassing :class:`~nltk.transcribe.acceptor.MorphologicalAcceptor`,
in which case GEN reduces to its Lane and Bird (2022, Fig. 5)
formulation.

Examples
--------
A miniature reproduction of the worked example from Lane and Bird
(2022, Example (1))::

    >>> from nltk.transcribe import (
    ...     PhoneOrthMapping, WordlistAcceptor, Lexicon,
    ...     InteractiveTranscriber)
    >>> phones2orth = PhoneOrthMapping({})  # identity mapping for this toy example
    >>> lexicon = WordlistAcceptor([
    ...     "kabirri", "kabirridurrkmirri", "kabirriudujmanme",
    ...     "manme", "manmebedberre", "bedberre",
    ... ])
    >>> attested = Lexicon([
    ...     "kabirri", "kabirridurrkmirri", "manme",
    ...     "bedberre", "manmebedberre", "kabirriudujmanme"])
    >>> trans = InteractiveTranscriber(
    ...     phone_orth=phones2orth, acceptor=lexicon, attested=attested)
    >>> phone_string = "kabirridurrkmirrikabirriudujmanmebedberre"
    >>> seen = set()
    >>> for s in trans.suggest(phone_string, ["kabirri", "manme"]):
    ...     if s.word in seen: continue
    ...     seen.add(s.word)
    ...     print(s.anchor, "->", s.word, "edits=%d" % s.edits)
    kabirri -> kabirri edits=0
    kabirri -> kabirridurrkmirri edits=0
    kabirri -> kabirriudujmanme edits=0
    manme -> manme edits=0
    manme -> manmebedberre edits=0

References
----------
Karttunen, L. (1998). The proper treatment of optimality in
computational phonology. In *Finite State Methods in Natural Language
Processing*.

Lane, W. and Bird, S. (2022). A Finite State Approach to Interactive
Transcription. In *Proceedings of the First Workshop on NLP
Applications to Field Linguistics*, 1-10.
"""

from dataclasses import dataclass, field

from nltk.transcribe.acceptor import MorphologicalAcceptor, WordlistAcceptor
from nltk.transcribe.align import PhoneOrthMapping, anchor_positions
from nltk.transcribe.constraints import (
    AnchoredConstraint,
    EditConstraint,
    LexicalConstraint,
    lenient_compose,
)


class Lexicon(frozenset):
    """
    A read-only set of words.

    Used as the underlying data for ``topical`` and ``attested`` lexica
    of a :class:`InteractiveTranscriber`.  Subclasses
    :class:`frozenset` so that membership is O(1) and the set is
    immutable.
    """

    def __new__(cls, words):
        return super().__new__(cls, words)


@dataclass(frozen=True)
class Suggestion:
    """
    A single ranked word completion proposed by the transcriber.

    Attributes
    ----------
    word : str
        The full word predicted.
    anchor : str
        The known lexeme this candidate was anchored on.
    edits : int
        Number of edit-distance violations between the candidate's
        surface form and the corresponding span of the orthographic
        string, summed over the lexeme alignment and the word
        expansion (the ``"^"`` count in Lane and Bird, 2022, Fig. 5).
    start : int
        Character offset in the canonical orthographic string where
        the placed word begins.
    end : int
        Exclusive character offset where the placed word ends.
    """

    word: str
    anchor: str
    edits: int
    start: int = 0
    end: int = 0
    _violations: tuple = field(default=(), repr=False, compare=False)

    def __str__(self):
        return f"{self.word} (anchor={self.anchor!r}, edits={self.edits})"


class InteractiveTranscriber:
    """
    Interactive word completion for morphologically complex languages.

    Implements the Lane and Bird (2022) GEN/EVAL pipeline:

    * **GEN.**  Convert the phone string to its canonical orthographic
      realisation via the phone-to-orth map; for each known lexeme,
      find every alignment within the per-lexeme edit budget; for each
      anchor, expand into all morphotactically valid words licensed by
      the acceptor that contain the lexeme; place each candidate word
      around its anchor and score the alignment.
    * **EVAL.**  Apply lenient composition over the constraint
      hierarchy ``anchored >> attested >> topical >> edit``.  See
      :mod:`nltk.transcribe.constraints` for definitions.

    The default per-lexeme edit budget follows Lane and Bird (2022):
    1 edit for short lexemes (length <= 3), 2 otherwise.

    Parameters
    ----------
    phone_orth : PhoneOrthMapping
        Mapping from phone symbols to orthographic realisations.
    acceptor : MorphologicalAcceptor
        Decides which words are morphotactically valid.  A
        :class:`~nltk.transcribe.acceptor.WordlistAcceptor` is fine for
        early-stage fieldwork; field-tested FSTs (Lane and Bird, 2019)
        can be plugged in by subclassing.
    attested : Iterable[str], optional
        Words attested in a wider corpus of the language.  Used as the
        ``Attested`` lexical constraint.  Defaults to an empty set,
        which makes the constraint vacuous (it filters nothing).
    topical : Iterable[str], optional
        Words attested in audio related to the current recording.
        Used as the ``Topical`` lexical constraint.  Defaults to empty.
    max_word_edit : int, optional
        Maximum edits permitted between a candidate word and the
        underlying orthographic span when scoring placement.  Defaults
        to 2, matching Lane and Bird (2022, Fig. 5, lines 29-32).
    edit_budget : Callable[[str], int], optional
        Function from a lexeme to its edit budget.  Defaults to ``1``
        if ``len(lexeme) <= 3`` else ``2``, per Lane and Bird (2022).
    """

    def __init__(
        self,
        phone_orth,
        acceptor,
        attested=(),
        topical=(),
        max_word_edit=2,
        edit_budget=None,
    ):
        if not isinstance(phone_orth, PhoneOrthMapping):
            raise TypeError("phone_orth must be a PhoneOrthMapping")
        if not isinstance(acceptor, MorphologicalAcceptor):
            raise TypeError(
                "acceptor must be a MorphologicalAcceptor; "
                "use WordlistAcceptor for a simple wordlist"
            )
        self.phone_orth = phone_orth
        self.acceptor = acceptor
        self.attested = Lexicon(attested)
        self.topical = Lexicon(topical)
        self.max_word_edit = int(max_word_edit)
        self._edit_budget = edit_budget or _default_edit_budget

    def suggest(self, phone_string, known_lexemes):
        """
        Return ranked :class:`Suggestion` objects for ``phone_string``.

        Parameters
        ----------
        phone_string : str
            Phone-recogniser output for the utterance.  In NLTK we
            represent phones as ordinary characters; users with
            multi-character phone symbols should pre-tokenise into a
            string where each phone has been mapped to a unique
            character, or pass a list and adapt
            :class:`PhoneOrthMapping` accordingly.
        known_lexemes : Iterable[str]
            The lexemes the transcriber has already identified, in the
            order they occur in the audio.

        Returns
        -------
        list[Suggestion]
            The optimal candidate set after lenient composition over
            the OT constraint hierarchy.  Sorted by edit count then
            anchor position.
        """
        candidates = list(self._gen(phone_string, list(known_lexemes)))
        if not candidates:
            return []

        constraints = self._build_constraints(known_lexemes)
        survivors = lenient_compose(candidates, *constraints)
        survivors.sort(key=lambda s: (s.edits, s.start, s.word))
        return survivors

    # ------------------------------------------------------------------
    # GEN
    # ------------------------------------------------------------------
    def _gen(self, phone_string, known_lexemes):
        """Generate all candidate completions anchored at known lexemes."""
        orth = self.phone_orth.to_canonical(phone_string)
        seen = set()
        for lexeme in known_lexemes:
            anchors = anchor_positions(orth, lexeme, self._edit_budget(lexeme))
            for anchor in anchors:
                for word in self.acceptor.expand(lexeme):
                    for placement in self._place(word, lexeme, anchor, orth):
                        key = (
                            placement.word,
                            placement.anchor,
                            placement.start,
                            placement.end,
                        )
                        if key in seen:
                            continue
                        seen.add(key)
                        yield placement

    def _place(self, word, lexeme, anchor, orth):
        """
        Try every occurrence of ``lexeme`` within ``word`` and yield
        placements whose total edit distance against ``orth`` is within
        budget.  The total edit count is the anchor's edits plus the
        edits required to align the rest of ``word`` with ``orth``.
        """
        if not lexeme or lexeme not in word:
            return
        # Each occurrence of lexeme inside word gives one placement.
        offset = 0
        while True:
            p = word.find(lexeme, offset)
            if p < 0:
                break
            offset = p + 1

            start = anchor.start - p
            end = start + len(word)
            if start < 0 or end > len(orth):
                # Word would extend past the orthographic string.
                # We allow partial overlap with a one-edit-per-missing-char penalty.
                pad_left = max(0, -start)
                pad_right = max(0, end - len(orth))
                start_clamped = max(0, start)
                end_clamped = min(len(orth), end)
                if end_clamped <= start_clamped:
                    continue
                window = orth[start_clamped:end_clamped]
                target = word[pad_left : len(word) - pad_right]
                edits = (
                    anchor.edits
                    + _hamming_or_lev(target, window)
                    + pad_left
                    + pad_right
                )
            else:
                window = orth[start:end]
                edits = anchor.edits + _hamming_or_lev(word, window)

            if edits <= self.max_word_edit + anchor.edits:
                yield Suggestion(
                    word=word,
                    anchor=lexeme,
                    edits=edits,
                    start=max(0, start),
                    end=min(len(orth), end),
                )

    # ------------------------------------------------------------------
    # EVAL
    # ------------------------------------------------------------------
    def _build_constraints(self, known_lexemes):
        """Build the ranked constraint hierarchy for this utterance."""
        constraints = [AnchoredConstraint(known_lexemes)]
        if self.attested:
            constraints.append(LexicalConstraint(self.attested, "Attested"))
        if self.topical:
            constraints.append(LexicalConstraint(self.topical, "Topical"))
        # Edit constraints are layered: every step of the budget is its
        # own constraint, ranked from strict (0) to lax (max_word_edit),
        # so that fewer-edit candidates outrank looser ones, mirroring
        # the ``edit1Words`` / ``edit2Words`` cascade of Lane and Bird
        # (2022, Fig. 5, lines 38-39, 44-45).
        for k in range(self.max_word_edit + 1):
            constraints.append(EditConstraint(max_edits=k, name=f"Edit<={k}"))
        return constraints


def _default_edit_budget(lexeme):
    """Lane and Bird (2022): 1 edit for short lexemes, 2 otherwise."""
    return 1 if len(lexeme) <= 3 else 2


def _hamming_or_lev(a, b):
    """Edit distance with equal-length fast path."""
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y)
    # Fall back to Levenshtein
    n, m = len(a), len(b)
    if n < m:
        a, b = b, a
        n, m = m, n
    prev = list(range(m + 1))
    for i in range(1, n + 1):
        curr = [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev = curr
    return prev[m]

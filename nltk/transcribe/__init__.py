# Natural Language Toolkit: Interactive Transcription
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Interactive word completion for morphologically complex, low-resource,
oral languages.

This package is a Python port of the Local Word Discovery with
implicit alignment algorithm of Lane and Bird (2022), "A Finite State
Approach to Interactive Transcription".  It is designed for the
*sparse transcription* setting (Bird, 2020): a transcriber listens to
a recording, identifies a few familiar lexemes, and an Optimality
Theory pipeline proposes ranked, morphotactically valid completions
anchored at each known lexeme.

The package is dependency-free.  Field linguists with an existing FOMA
or HFST analyser may plug it in by subclassing
:class:`MorphologicalAcceptor`; the constraint and completion logic is
unchanged.

Quick start
-----------

    >>> from nltk.transcribe import (
    ...     PhoneOrthMapping, WordlistAcceptor, Lexicon,
    ...     InteractiveTranscriber)
    >>> phones2orth = PhoneOrthMapping({})
    >>> lex = WordlistAcceptor(["kabirri", "kabirridurrkmirri",
    ...                         "manme", "bedberre", "manmebedberre"])
    >>> trans = InteractiveTranscriber(
    ...     phone_orth=phones2orth, acceptor=lex,
    ...     attested=Lexicon(["kabirridurrkmirri", "bedberre"]),
    ...     topical=Lexicon(["kabirridurrkmirri"]))
    >>> phones = "kabirridurrkmirrikabirriudujmanmebedberre"
    >>> first = trans.suggest(phones, ["kabirri"])[0]
    >>> first.word
    'kabirridurrkmirri'

References
----------
Bird, S. (2020). Sparse transcription. *Computational Linguistics*,
46(4), 713-744.

Lane, W. and Bird, S. (2022). A Finite State Approach to Interactive
Transcription. In *Proceedings of the First Workshop on NLP
Applications to Field Linguistics*, 1-10.
"""

from nltk.transcribe.acceptor import MorphologicalAcceptor, WordlistAcceptor
from nltk.transcribe.align import Anchor, PhoneOrthMapping, anchor_positions
from nltk.transcribe.completion import (
    InteractiveTranscriber,
    Lexicon,
    Suggestion,
)
from nltk.transcribe.constraints import (
    AnchoredConstraint,
    Constraint,
    EditConstraint,
    LexicalConstraint,
    lenient_compose,
)
from nltk.transcribe.tableau import Tableau

__all__ = [
    "Anchor",
    "AnchoredConstraint",
    "Constraint",
    "EditConstraint",
    "InteractiveTranscriber",
    "LexicalConstraint",
    "Lexicon",
    "MorphologicalAcceptor",
    "PhoneOrthMapping",
    "Suggestion",
    "Tableau",
    "WordlistAcceptor",
    "anchor_positions",
    "lenient_compose",
]

# Natural Language Toolkit: Interactive Transcription -- OT Tableau Pretty-Printer
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Andrew Bird <andrew@affinda.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""
Render an Optimality-Theoretic constraint tableau.

A *tableau* is the canonical OT representation: rows are candidates,
columns are constraints (left to right by rank), and cells are
violation counts (rendered as ``*``).  The optimal candidate(s) are
marked with ``->``.  This is the same picture shown in Lane and Bird
(2022, Fig. 4).

This module is for human inspection only --- it is the pedagogical
counterpart to :func:`nltk.transcribe.constraints.lenient_compose`.
"""

from nltk.transcribe.constraints import lenient_compose


class Tableau:
    """
    An OT tableau over a fixed candidate set and constraint hierarchy.

    Parameters
    ----------
    candidates : Iterable
        The candidate set output by GEN.
    constraints : Iterable[Constraint]
        Constraints in rank order, highest first.
    label : Callable, optional
        Function that converts a candidate to a display string.

    Examples
    --------
    >>> from nltk.transcribe.constraints import (
    ...     AnchoredConstraint, LexicalConstraint, EditConstraint)
    >>> from nltk.transcribe.tableau import Tableau
    >>> cands = ["kabirridurrkmirri", "kabirriXX", "bedberre"]
    >>> t = Tableau(
    ...     cands,
    ...     [AnchoredConstraint(["kabirri"]),
    ...      LexicalConstraint({"kabirridurrkmirri"}, "Attested"),
    ...      EditConstraint(0, "Edit<=0")])
    >>> print(t.render())  # doctest: +NORMALIZE_WHITESPACE
    candidate           Anchored  Attested  Edit<=0
    -> kabirridurrkmirri    .          .         .
       kabirriXX            .          *!        .
       bedberre             *!         *         .
    """

    def __init__(self, candidates, constraints, label=str):
        self.candidates = list(candidates)
        self.constraints = list(constraints)
        self.label = label

    def winners(self):
        """Return the lenient-composition winners."""
        return lenient_compose(self.candidates, *self.constraints)

    def render(self) -> str:
        """Return the tableau as a multi-line string."""
        winners = set(map(id, self.winners()))
        rows = []
        # Header
        labels = [self.label(c) for c in self.candidates]
        col_w = max([len("candidate")] + [len(l) for l in labels]) + 2
        constraint_widths = [max(len(c.name), 6) for c in self.constraints]
        header = (
            "   "
            + "candidate".ljust(col_w)
            + "".join(
                c.name.ljust(w + 2) for c, w in zip(self.constraints, constraint_widths)
            )
        )
        rows.append(header.rstrip())

        # Compute strikes per (candidate, constraint).  A "fatal" strike
        # is the first violation that knocks out the candidate, given
        # the survivors at that point.
        survivors = list(self.candidates)
        fatal = {}  # (id(cand), idx) -> True
        for idx, c in enumerate(self.constraints):
            passing = [x for x in survivors if c(x) == 0]
            if passing:
                for x in survivors:
                    if c(x) > 0:
                        fatal[(id(x), idx)] = True
                survivors = passing

        for cand in self.candidates:
            mark = "-> " if id(cand) in winners else "   "
            cells = []
            for idx, c in enumerate(self.constraints):
                v = c(cand)
                w = constraint_widths[idx] + 2
                if v == 0:
                    cells.append(".".ljust(w))
                else:
                    s = "*" * v
                    if (id(cand), idx) in fatal:
                        s += "!"
                    cells.append(s.ljust(w))
            row = mark + self.label(cand).ljust(col_w) + "".join(cells)
            rows.append(row.rstrip())

        return "\n".join(rows)

    def __str__(self):
        return self.render()

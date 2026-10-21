"""GHSA-v8f3-6phw-6mh9 [moderate]: Algorithmic DoS (CWE-407) in the CoNLL SRL
reader. A per-predicate spanlist rescan makes srl_instances O(P**2*R) in the
number of predicates P and spans R, so one crafted sentence with many predicates
burns quadratic CPU.
"""

import os
import shutil
import tempfile

from ._base import (
    FIXED,
    QUADRATIC_RATIO,
    STATIC,
    VULNERABLE,
    probe,
    register_data_root,
    scaling_ratio,
)

# Predicate counts fed to the sink over a sentence of _WORDS words; big is
# 4*small so a linear method scales ~4x and the pre-fix rescan ~16x. The word
# count is fixed because the format gives every predicate its own column.
_WORDS = 600
_SMALL = 70
_BIG = 4 * _SMALL


def _build_grid(predicates, words=_WORDS):
    """A one-sentence CoNLL-2005 SRL grid: ``words`` rows, the first
    ``predicates`` of them predicates, and one span column per predicate.

    Columns: words, pos, tree, roleset, predicate, then the span columns.
    Column j carries the '(V*)' verb for predicate j on row j and a decoy
    '(A1*)' span on every other row, so each spanlist holds ``words`` spans and
    predicate j's verb sits in spanlist j. The grid is words * predicates cells,
    so growing the predicates alone grows the input linearly: a grid that grew
    both (n predicates over n words) was itself quadratic in n and read the
    one-pass reader as 16x too, hidden only by the noise floor on the small run.
    """
    grid = []
    for i in range(words):
        if i < predicates:
            row = ["w", "NN", "*", "verb.01", "p"]
        else:
            row = ["w", "NN", "*", "-", "-"]
        for j in range(predicates):
            row.append("(V*)" if i == j else "(A1*)")
        grid.append(row)
    return grid


@probe("GHSA-v8f3-6phw-6mh9")
def _conll_srl_quadratic_rescan():
    """Drive the real reader's _get_srl_instances on grids of n and 4n predicates.

    The fixed sink indexes wordnum to spanlist in one pass (O(P*R)); the pre-fix
    code rescanned every spanlist per predicate (O(P**2*R)). A scaling factor at
    or above QUADRATIC_RATIO over the 4x jump is the regression.
    """
    from nltk.corpus.reader.conll import ConllCorpusReader

    box = tempfile.mkdtemp()
    undo = register_data_root(box)
    try:
        root = os.path.join(box, "corpus")
        os.makedirs(root)
        # A placeholder fileid so the reader constructs; the grids are handed to
        # the sink directly, so the file is never read.
        open(os.path.join(root, "srl.conll"), "w").close()
        try:
            reader = ConllCorpusReader(
                root, ["srl.conll"], ("words", "pos", "tree", "srl")
            )
        except Exception as exc:
            return STATIC, "reader would not construct (%s)" % type(exc).__name__

        grids = {_SMALL: _build_grid(_SMALL), _BIG: _build_grid(_BIG)}

        def op(n):
            reader._get_srl_instances(grids[n], False)

        ratio = scaling_ratio(op, _SMALL, _BIG, cpu_bound=True)  # the sink computes
        if ratio >= QUADRATIC_RATIO:
            return (
                VULNERABLE,
                "srl_instances scaled %.1fx over 4x predicates (per-predicate rescan)"
                % ratio,
            )
        return (
            FIXED,
            "srl_instances scaled %.1fx over 4x predicates (one-pass spanlist index)"
            % ratio,
        )
    finally:
        undo()
        shutil.rmtree(box, ignore_errors=True)

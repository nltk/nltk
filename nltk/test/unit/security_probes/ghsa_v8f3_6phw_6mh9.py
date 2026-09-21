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

# Predicate counts fed to the sink; big is 4*small so a linear method scales ~4x
# and the pre-fix quadratic rescan scales ~16x. Sizes keep the fixed sink in tens
# of milliseconds and a reverted quadratic run well under a couple of seconds.
_SMALL = 70
_BIG = 4 * _SMALL


def _build_grid(n):
    """A one-sentence CoNLL-2005 SRL grid with n predicates and n span columns.

    Columns: words, pos, tree, roleset, predicate, then one span column per
    predicate. Column j carries the '(V*)' verb for predicate j on its diagonal
    row and a decoy '(A1*)' span on every other row, so each spanlist holds n
    spans and predicate j's verb sits in spanlist j.
    """
    grid = []
    for i in range(n):
        row = ["w", "NN", "*", "verb.01", "p"]
        for j in range(n):
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

        ratio = scaling_ratio(op, _SMALL, _BIG)
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

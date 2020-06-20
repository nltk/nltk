# -*- coding: utf-8 -*-


# FIXME: the entire discourse.doctest is skipped if Prover9/Mace4 is
# not installed, but there are pure-python parts that don't need Prover9.
def setup_module(module):
    from nose import SkipTest
    from nltk.inference.mace import Mace

    try:
        m = Mace()
        m._find_binary("mace4")
    except LookupError as e:
        raise SkipTest(
            "Mace4/Prover9 is not available so discourse.doctest is skipped"
        ) from e

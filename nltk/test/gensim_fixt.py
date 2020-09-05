# -*- coding: utf-8 -*-


def setup_module():
    import pytest

    try:
        import gensim
    except ImportError:
        pytest.skip("Gensim doctest requires gensim")

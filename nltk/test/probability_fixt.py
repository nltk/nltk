# -*- coding: utf-8 -*-


# probability.doctest uses HMM which requires numpy;
# skip probability.doctest if numpy is not available


def setup_module(module):
    import pytest

    try:
        import numpy
    except ImportError:
        pytest.skip("probability.doctest requires numpy")

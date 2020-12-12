# -*- coding: utf-8 -*-


# most of classify.doctest requires numpy
def setup_module():
    import pytest

    try:
        import numpy
    except ImportError:
        pytest.skip("classify.doctest requires numpy")

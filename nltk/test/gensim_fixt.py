# -*- coding: utf-8 -*-


def setup_module():
    import pytest
    pytest.importorskip("gensim")

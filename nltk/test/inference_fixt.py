def setup_module():
    import pytest

    from nltk.inference.mace import Mace

    try:
        m = Mace()
        m._find_binary("mace4")
    except LookupError:
        pytest.skip("Mace4/Prover9 is not available so inference.doctest was skipped")

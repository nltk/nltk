def setup_module():
    import pytest

    from nltk.parse.malt import MaltParser

    try:
        depparser = MaltParser("maltparser")
    except LookupError as e:
        pytest.skip("MaltParser is not available")

def setup_module():
    import pytest

    from nltk.parse.malt import MaltParser

    try:
        depparser = MaltParser("maltparser-1.7.2")
    except LookupError as e:
        pytest.skip("MaltParser is not available")

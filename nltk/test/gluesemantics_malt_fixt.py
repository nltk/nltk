def setup_module():
    import pytest

    from nltk.parse.malt import MaltParser
    from nltk.test.setup_fixt import check_binary

    try:
        depparser = MaltParser()
    except (AssertionError, LookupError) as e:
        pytest.skip("MaltParser is not available")
    # readings[0].equiv(readings[1]) runs Prover9; look where nltk.inference does
    check_binary("prover9", env_vars=["PROVER9"])

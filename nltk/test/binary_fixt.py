from nltk.internals import find_binary


def check_binary(binary):
    import pytest

    try:
        find_binary(binary)
    except:
        pytest.skip("Skipping test because the {binary} binary was not found")
        return False

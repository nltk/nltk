# Skip doctest when a required binary is not available
from nltk.internals import find_binary


def check_binary(binary):
    import pytest

    try:
        find_binary(binary)
    except LookupError:
        pytest.skip(f"Skipping test because the {binary} binary was not found")

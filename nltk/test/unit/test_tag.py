def test_basic():
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize

    result = pos_tag(word_tokenize("John's big idea isn't all that bad."))
    assert result == [
        ("John", "NNP"),
        ("'s", "POS"),
        ("big", "JJ"),
        ("idea", "NN"),
        ("is", "VBZ"),
        ("n't", "RB"),
        ("all", "PDT"),
        ("that", "DT"),
        ("bad", "JJ"),
        (".", "."),
    ]


def test_pos_tag_return_types():
    from nltk.tag import pos_tag
    from nltk.tokenize import word_tokenize

    result = pos_tag(word_tokenize("Hello world."))
    assert isinstance(result, list)
    assert all(isinstance(item, tuple) and len(item) == 2 for item in result)
    assert all(isinstance(token, str) and isinstance(tag, str) for token, tag in result)


def setup_module(module):
    import pytest

    pytest.importorskip("numpy")

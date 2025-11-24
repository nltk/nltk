import pytest
from nltk.data import split_resource_url

@pytest.mark.parametrize(
    "input_url, expected",
    [
        ("corpora/wordnet", ("nltk", "corpora/wordnet")),
        ("nltk:home/nltk", ("nltk", "home/nltk")),
        ("file:/dir/file", ("file", "/dir/file")),
        ("https://example.com/dir/file", ("https", "example.com/dir/file")),
        ("http:/example.com/path", ("http", "example.com/path")),
        ("nltk:tokenizers/punkt/english.pickle", ("nltk", "tokenizers/punkt/english.pickle")),
        ("custom:some:extra/path", ("custom", "some:extra/path")),
    ],
)
def test_split_resource_url_variants(input_url, expected):
    assert split_resource_url(input_url) == expected
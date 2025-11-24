import os
import inspect
import importlib.metadata as m
import pytest

import nltk
import nltk.data as nd
from nltk.data import find


###############################################################################
# 0. Verify Local NLTK Clone
###############################################################################

def test_local_nltk_clone_active():
    nltk_path = os.path.abspath(nltk.__file__)
    data_path = os.path.abspath(inspect.getfile(nd))

    assert "nltk_Group1_ENGG4450" in nltk_path.replace("\\", "/"), \
        f"NLTK imported from wrong location:\n{nltk_path}"

    assert "nltk_Group1_ENGG4450" in data_path.replace("\\", "/"), \
        f"data.py imported from wrong location:\n{data_path}"


###############################################################################
# 1. Verify nltk-punkt Installed
###############################################################################

def test_nltk_punkt_installed():
    d = m.distribution("nltk-punkt")  # raises PackageNotFoundError if missing
    version = d.version
    assert version.startswith("0.1.0"), f"Unexpected nltk-punkt version: {version}"


###############################################################################
# 2. Verify ALL Entry Points
###############################################################################

REQUIRED_ENTRYPOINTS = {
    "punkt",
    "averaged_perceptron_tagger",
    "stopwords",
    "wordnet",
    "omw-1.4",
    "snowball_data",
    "names",
    "brown",
    "movie_reviews",
}

def test_entry_points_exist():
    eps = m.entry_points(group="nltk_data")
    present = {ep.name for ep in eps}

    missing = REQUIRED_ENTRYPOINTS - present
    assert not missing, f"Missing nltk_data entry points: {missing}"


###############################################################################
# 3. Verify find() Resolves From nltk_punkt/data
###############################################################################

DATA_TESTS = {
    "tokenizers/punkt/english.pickle": "punkt",
    "taggers/averaged_perceptron_tagger/averaged_perceptron_tagger.pickle": "tagger",
    "corpora/stopwords": "stopwords",
    "corpora/wordnet": "wordnet",
    "corpora/omw-1.4": "omw",
    "snowball_data": "snowball",
    "corpora/names": "names",
    "corpora/brown": "brown",
    "corpora/movie_reviews": "movie_reviews",
}

@pytest.mark.parametrize("resource", DATA_TESTS.keys())
def test_find_resolves_to_wheel(resource):
    p = find(resource)
    loc = str(p._path).replace("\\", "/").lower()

    assert "nltk_punkt" in loc, \
        f"Resource '{resource}' not loaded from nltk_punkt package:\n{loc}"


###############################################################################
# 4. Verify Actual NLTK Functionality (No Downloads!)
###############################################################################

def test_real_nltk_functionality():
    from nltk.tokenize import sent_tokenize, word_tokenize
    from nltk.corpus import stopwords, wordnet as wn, names, brown, movie_reviews
    from nltk import pos_tag

    # Punkt Sentence Tokenization
    sents = sent_tokenize("Hello world. This is a test. Another sentence here.")
    assert len(sents) == 3

    # Stopwords
    sw = stopwords.words("english")
    assert "the" in sw

    # WordNet
    syns = wn.synsets("dog")
    assert len(syns) > 0

    # Names corpus
    assert len(names.words()) > 0

    # Brown corpus
    assert len(brown.categories()) > 0

    # Movie reviews
    assert len(movie_reviews.fileids()) > 0

    # POS tagger
    tagged = pos_tag(word_tokenize("Hello there friend."))
    assert len(tagged) == 3  # Hello / there / friend.


###############################################################################
# 5. Combined End-to-End Test
###############################################################################

def test_end_to_end():
    """
    Ensures everything works as a full system:
    - Local clone
    - Entry points
    - find()
    - Real NLTK usage
    """
    # Local clone
    assert "nltk_Group1_ENGG4450" in nltk.__file__.replace("\\", "/")

    # Entry points
    eps = {ep.name for ep in m.entry_points(group="nltk_data")}
    assert REQUIRED_ENTRYPOINTS.issubset(eps)

    # One key resource check
    punkt_path = find("tokenizers/punkt/english.pickle")._path
    assert "nltk_punkt" in str(punkt_path).replace("\\", "/").lower()

    # Tokenizer
    from nltk.tokenize import sent_tokenize
    out = sent_tokenize("A. B. C.")
    assert out == ["A.", "B.", "C."]


###############################################################################
# Runner for `python test_pip_data_loading.py`
###############################################################################

if __name__ == "__main__":
    import sys
    sys.exit(pytest.main([__file__]))

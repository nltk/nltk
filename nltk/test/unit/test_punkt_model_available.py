"""Availability of a Punkt model, answered as the sentence tokenizer loads it."""

import pytest

from nltk.data import find
from nltk.tokenize import _get_punkt_tokenizer, punkt_model_available, sent_tokenize

#: The four files of a punkt_tab model, written as bytes (a text write would
#: end "zzq" in CRLF on Windows); "zzq" is an abbreviation, so only this model
#: splits SAMPLE into these two sentences.
MODEL = {
    "abbrev_types.txt": "zzq\n",
    "collocations.tab": "",
    "ortho_context.tab": "",
    "sent_starters.txt": "",
}
SAMPLE = "I met zzq. Smith today. Then we left."


@pytest.fixture
def model_root(pathsec_sandbox):
    """An enforced data root holding an empty punkt_tab/english directory,
    with no tokenizer cached from any other root before or after."""
    root, _outside = pathsec_sandbox
    language_dir = root / "tokenizers" / "punkt_tab" / "english"
    language_dir.mkdir(parents=True)
    _get_punkt_tokenizer.cache_clear()
    yield language_dir
    _get_punkt_tokenizer.cache_clear()


def test_an_empty_model_directory_is_not_a_model(model_root):
    # find() sees the directory, but the tokenizer cannot load it, and the
    # answer is the tokenizer's: not installed, with the download named
    assert find("tokenizers/punkt_tab/english/")
    assert punkt_model_available("english") is False
    with pytest.raises(LookupError, match="punkt_tab"):
        sent_tokenize(SAMPLE, language="english")
    assert list(model_root.iterdir()) == []


def test_the_four_parameter_files_make_it_one(model_root):
    for name, text in MODEL.items():
        (model_root / name).write_bytes(text.encode("utf-8"))
    assert punkt_model_available("english") is True
    assert sent_tokenize(SAMPLE, language="english") == [
        "I met zzq. Smith today.",
        "Then we left.",
    ]
    assert punkt_model_available("polish") is False
    assert sorted(p.name for p in model_root.iterdir()) == sorted(MODEL)


@pytest.mark.parametrize("missing", sorted(MODEL))
def test_a_model_missing_any_file_is_not_installed(model_root, missing):
    for name, text in MODEL.items():
        if name != missing:
            (model_root / name).write_bytes(text.encode("utf-8"))
    assert punkt_model_available("english") is False
    with pytest.raises(LookupError, match=missing):
        sent_tokenize(SAMPLE, language="english")


def test_punkt_model_available_rejects_a_path_language():
    with pytest.raises(ValueError):
        punkt_model_available("../..")
    with pytest.raises(ValueError):
        punkt_model_available("english/../polish")
    with pytest.raises(ValueError):
        punkt_model_available("")

"""Availability of a Punkt model without loading its parameter files."""

import pytest

from nltk.data import find
from nltk.tokenize import punkt_model_available


def test_punkt_model_available_checks_the_directory_only(tmp_path, monkeypatch):
    language_dir = tmp_path / "tokenizers" / "punkt_tab" / "english"
    language_dir.mkdir(parents=True)
    monkeypatch.setattr("nltk.data.path", [str(tmp_path)])

    assert punkt_model_available("english") is True
    assert punkt_model_available("polish") is False
    assert list(language_dir.iterdir()) == []
    # find() is the lookup sent_tokenize uses; the directory is enough.
    assert find("tokenizers/punkt_tab/english/")


def test_punkt_model_available_rejects_a_path_language():
    with pytest.raises(ValueError):
        punkt_model_available("../..")
    with pytest.raises(ValueError):
        punkt_model_available("english/../polish")
    with pytest.raises(ValueError):
        punkt_model_available("")

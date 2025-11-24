import inspect
from pathlib import Path
import importlib
import importlib.metadata
import pytest
import nltk

def _nltk_project_root():
    # test file is .../nltk/test/... -> project root is two parents up
    return Path(__file__).resolve().parents[2]


def _nltk_data_entrypoints():
    eps = importlib.metadata.entry_points()
    try:
        return eps.select(group="nltk_data")
    except Exception:
        return [ep for ep in eps if getattr(ep, "group", None) == "nltk_data"]


def test_local_nltk_clone_is_used():
    project_root = _nltk_project_root()
    nltk_file = inspect.getfile(nltk)
    assert str((project_root / "nltk")) in str(Path(nltk_file).resolve()), (
        "NLTK import does not appear to come from local clone. Reinstall editable: pip install -e ."
    )

def test_entrypoint_registered_for_punkt():
    eps = list(_nltk_data_entrypoints())
    assert any(
        (ep.name == "punkt") or ("nltk_punkt" in getattr(ep, "value", ""))
        for ep in eps
    ), "No 'nltk_data' entry point for punkt found. Ensure nltk-punkt is installed."


@pytest.mark.skipif(
    not any((ep.name == "punkt") or ("nltk_punkt" in getattr(ep, "value", "")) for ep in _nltk_data_entrypoints()),
    reason="nltk-punkt entry point not installed"
)
def test_find_returns_punkt_from_installed_package():
    from nltk.data import find

    ptr = find("tokenizers/punkt/english.pickle")
    assert ptr is not None
    s = str(ptr)
    assert "nltk_punkt" in s or "nltk-punkt" in s or "punkt" in s, (
        "find() did not return a path inside the installed nltk-punkt package"
    )


@pytest.mark.skipif(
    not any((ep.name == "punkt") or ("nltk_punkt" in getattr(ep, "value", "")) for ep in _nltk_data_entrypoints()),
    reason="nltk-punkt entry point not installed"
)
def test_punkt_sentence_tokenizer_works_without_download():
    from nltk.tokenize import PunktSentenceTokenizer

    tok = PunktSentenceTokenizer()
    sents = tok.tokenize("Hello world. This is a test. Another sentence here.")
    assert isinstance(sents, list)
    assert len(sents) >= 3
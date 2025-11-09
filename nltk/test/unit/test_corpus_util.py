"""
Simple tests for nltk.corpus.util.LazyCorpusLoader

These tests avoid real corpus access by monkeypatching nltk.data.find,
and use a minimal dummy reader that subclasses CorpusReader without
requiring any actual files.
"""

import pytest

from nltk.corpus.util import LazyCorpusLoader


@pytest.fixture
def monkeypatch_find(monkeypatch, tmp_path):
    # Always return a temporary directory for data.find
    def fake_find(path_spec):
        return str(tmp_path)

    monkeypatch.setattr("nltk.data.find", fake_find)
    return tmp_path


@pytest.fixture
def dummy_reader_cls():
    # Minimal CorpusReader subclass that doesn't touch the filesystem.
    from nltk.corpus.reader.api import CorpusReader

    class DummyCorpusReader(CorpusReader):
        def __init__(self, root, *args, **kwargs):
            # Call base class __init__ with safe parameters to avoid FS ops
            super().__init__(root, fileids=[])
            self._root = root  # CorpusReader.root property reads from _root
            self.payload = ["ok"]  # something to show attributes exist

        def marker(self):
            return f"ok:{self._root}"

    return DummyCorpusReader


def test_repr_not_loaded(dummy_reader_cls):
    loader = LazyCorpusLoader("dummy_corpus", dummy_reader_cls)
    # Should indicate not loaded yet
    assert "not loaded yet" in repr(loader)


def test_load_unload_reload_cycle(monkeypatch_find, dummy_reader_cls):
    loader = LazyCorpusLoader("dummy_corpus", dummy_reader_cls)

    # Initially still a lazy loader
    assert loader.__class__ is LazyCorpusLoader

    # Trigger load via a simple method
    assert loader.marker().startswith("ok:")
    assert loader.__class__ is dummy_reader_cls

    # Unload restores lazy proxy
    loader._unload()
    assert loader.__class__ is LazyCorpusLoader

    # Access again to reload
    assert loader.marker().startswith("ok:")
    assert loader.__class__ is dummy_reader_cls


def test_dunder_access_does_not_trigger_load(dummy_reader_cls):
    # Ensure introspection-style dunder lookups don't load the corpus
    loader = LazyCorpusLoader("dummy_corpus", dummy_reader_cls)
    with pytest.raises(AttributeError):
        _ = loader.__wrapped__
    assert loader.__class__ is LazyCorpusLoader

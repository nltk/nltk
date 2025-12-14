"""
Combined tests for nltk.corpus.util:

- Original _make_bound_method unit tests (ensure binding semantics).
- New LazyCorpusLoader behavioral tests (lazy load/unload cycle,
  dunder attribute guard, representation before load).

Retaining both suites ensures we preserve earlier guarantees while
validating the newer unload & dunder-guard behavior.
"""

import pytest

from nltk.corpus.util import LazyCorpusLoader, _make_bound_method

# ----------------------------------------------------------------------
# Tests for _make_bound_method
# ----------------------------------------------------------------------


class TestMakeBoundMethod:
    """Tests for _make_bound_method function"""

    def test_creates_bound_method(self):
        """Test that _make_bound_method creates a proper bound method"""

        class TestClass:
            def __init__(self, value):
                self.value = value

        def test_func(self):
            return self.value * 2

        obj = TestClass(5)
        bound_method = _make_bound_method(test_func, obj)

        # verify it's callable
        assert callable(bound_method)

        # verify it returns the correct value
        assert bound_method() == 10

    def test_bound_method_has_correct_self(self):
        """Test that the bound method has correct self binding"""

        class Counter:
            def __init__(self):
                self.count = 0

        def increment(self):
            self.count += 1
            return self.count

        obj = Counter()
        bound_increment = _make_bound_method(increment, obj)

        # call multiple times and verify state changes
        assert bound_increment() == 1
        assert bound_increment() == 2
        assert obj.count == 2

    def test_bound_method_with_arguments(self):
        """Test that bound method works with additional arguments"""

        class Multiplier:
            def __init__(self, base):
                self.base = base

        def multiply(self, factor):
            return self.base * factor

        obj = Multiplier(3)
        bound_multiply = _make_bound_method(multiply, obj)

        assert bound_multiply(4) == 12
        assert bound_multiply(10) == 30


# ----------------------------------------------------------------------
# New tests for LazyCorpusLoader behavior
# ----------------------------------------------------------------------


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

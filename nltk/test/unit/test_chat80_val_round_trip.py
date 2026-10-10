# Natural Language Toolkit: chat80 valuation store round trip
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``val_load`` reads back exactly what ``val_dump`` wrote.

``val_dump`` stores the Valuation that ``make_valuation`` builds, whose
relations are the sorted ``Concept.extension`` lists. ``val_load`` used to pass
every stored pair to the ``Valuation`` constructor, which accepts only ``str``,
``bool`` and ``set`` values, so reading back any real store raised ValueError.
These tests dump the real Chat-80 relations into a staging directory under a
data root, on every dbm backend this interpreter has, load them back through
the public function and compare the result with the dumped Valuation. Values
that ``val_dump`` never writes are still refused. Nothing is mocked.
"""

import dbm
import os
import shelve
import shutil

import pytest

import nltk.data
from nltk.sem import Assignment, Model, Valuation, chat80

BACKENDS = ["dbm.dumb", "dbm.ndbm", "dbm.gnu", "dbm.sqlite3"]


@pytest.fixture
def stage():
    # read the installed corpus, not a test corpus another test left in the cache
    nltk.data.clear_cache()
    directory = nltk.data.make_staging_dir(prefix="nltk_chat80_rt_")
    yield directory
    shutil.rmtree(directory, ignore_errors=True)
    nltk.data.clear_cache()


def _dumped(rels):
    """The Valuation ``val_dump`` stores for ``rels``, built the same way."""
    try:
        return chat80.make_valuation(chat80.process_bundle(rels).values(), read=True)
    except LookupError:
        pytest.skip("the chat80 corpus is not installed")


def _use_backend(monkeypatch, name):
    try:
        module = __import__(name, fromlist=["open"])
    except ImportError:
        pytest.skip(f"{name} is not available on this interpreter")
    monkeypatch.setattr(dbm, "_defaultmod", module)
    monkeypatch.setitem(dbm._modules, name, module)


def _write_store(base, values):
    with shelve.open(base, "n") as store:
        store.update(values)


def _assert_round_trip(base, dumped):
    """``val_load(base)`` must equal the dumped Valuation, pair for pair."""
    loaded = chat80.val_load(base)
    assert type(loaded) is Valuation
    with shelve.open(base, "r") as store:
        stored = dict(store.items())
    assert loaded == stored
    lost = set(dumped) - set(stored)
    if lost:
        # macOS ndbm can skip a key when it iterates a store holding a large
        # value (the plain shelf above skips it too); other backends return all.
        assert dbm.whichdb(base) == "dbm.ndbm", sorted(lost)
        assert loaded == {k: v for k, v in dumped.items() if k not in lost}
    else:
        assert loaded == dumped
    return loaded


def test_real_city_valuation_round_trips(stage):
    dumped = _dumped([chat80.city])
    base = os.path.join(stage, "city")
    chat80.val_dump([chat80.city], base)
    loaded = _assert_round_trip(base, dumped)
    assert loaded["city"] == dumped["city"]
    assert isinstance(loaded["city"], list) and len(loaded["city"]) > 50
    assert "calcutta" in loaded["city"]
    # the store is closed: the directory holding it can be removed (Windows too)
    shutil.rmtree(stage)
    assert not os.path.exists(stage)


def test_real_full_valuation_round_trips_and_evaluates(stage):
    rels = list(chat80.rels)
    dumped = _dumped(rels)
    base = os.path.join(stage, "all")
    chat80.val_dump(rels, base)
    loaded = _assert_round_trip(base, dumped)
    assert len(loaded) > 1000
    assert {type(value) for value in loaded.values()} == {str, list}
    india = [town for (town, country) in loaded["country_of"] if country == "india"]
    assert india == ["bombay", "calcutta", "delhi", "hyderabad", "madras"]
    model = Model(loaded.domain, loaded)
    assignment = Assignment(loaded.domain)
    assert model.evaluate(r"population_of(jakarta, 533)", assignment) is True
    assert model.evaluate(r"population_of(jakarta, 1368)", assignment) is False


@pytest.mark.parametrize("backend", BACKENDS)
def test_round_trip_on_every_dbm_backend(stage, monkeypatch, backend):
    _use_backend(monkeypatch, backend)
    rels = [chat80.city, chat80.borders]
    dumped = _dumped(rels)
    base = os.path.join(stage, "store")
    chat80.val_dump(rels, base)
    assert dbm.whichdb(base) == backend
    _assert_round_trip(base, dumped)


def test_a_set_valued_store_still_loads_through_the_constructor(stage):
    base = os.path.join(stage, "sets")
    _write_store(base, {"dog": {"d1", "d2"}, "see": {("d1", "d2")}, "d1": "d1"})
    loaded = chat80.val_load(base)
    assert loaded == Valuation(
        [("dog", {"d1", "d2"}), ("see", {("d1", "d2")}), ("d1", "d1")]
    )
    assert loaded["dog"] == {("d1",), ("d2",)}


@pytest.mark.parametrize(
    "value",
    [
        533,
        {"a": "b"},
        ["athens", 533],
        [["athens", "greece"]],
        [("athens", 533)],
        [{"athens"}],
        ("athens", "greece"),
        frozenset({"athens"}),
        None,
    ],
    ids=repr,
)
def test_values_val_dump_never_writes_are_still_refused(stage, value):
    base = os.path.join(stage, "odd")
    _write_store(base, {"city": ["athens"], "odd": value})
    with pytest.raises(ValueError, match=r"Unrecognized value for symbol\s+'odd'"):
        chat80.val_load(base)


def test_an_empty_relation_round_trips(stage):
    base = os.path.join(stage, "empty")
    _write_store(base, {"sea": [], "athens": "athens"})
    loaded = chat80.val_load(base)
    assert loaded == {"sea": [], "athens": "athens"}
    assert type(loaded) is Valuation

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
import sys

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
    # the manifest makes the load exact on every backend, ndbm included
    assert loaded == dumped
    with shelve.open(base, "r") as store:
        stored = {k: v for k, v in store.items() if k != chat80._STORE_MANIFEST_KEY}
    if dbm.whichdb(base) != "dbm.ndbm":
        assert loaded == stored
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
        ["athens", ("athens", "greece")],
        [("athens",), ("bangkok",)],
        [("athens", "greece", "europe")],
        [("athens",), ("athens", "greece")],
        [()],
        ["bangkok", "athens"],
        ["athens", "athens"],
        [("bangkok", "thailand"), ("athens", "greece")],
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


@pytest.mark.parametrize("backend", BACKENDS)
def test_every_list_the_real_dump_writes_is_a_sorted_extension(
    stage, monkeypatch, backend
):
    _use_backend(monkeypatch, backend)
    rels = list(chat80.rels)
    dumped = _dumped(rels)
    base = os.path.join(stage, "all")
    chat80.val_dump(rels, base)
    # looked up by key: macOS ndbm can skip a key when iterating (see above)
    keys = [key for key, value in dumped.items() if isinstance(value, list)]
    with shelve.open(base, "r") as store:
        lists = [store[key] for key in keys]
    assert len(lists) == 20
    assert lists == [dumped[key] for key in keys]
    assert all(chat80._is_extension_list(value) for value in lists)


def test_a_reordered_real_relation_is_refused(stage):
    dumped = _dumped([chat80.city])
    base = os.path.join(stage, "reordered")
    _write_store(base, {"city": list(reversed(dumped["city"])), "athens": "athens"})
    with pytest.raises(ValueError, match=r"Unrecognized value for symbol\s+'city'"):
        chat80.val_load(base)


# =========================================================================
# The key manifest: loads never depend on backend iteration
# =========================================================================
def _dump_and_load(stage, monkeypatch, backend, values=None):
    _use_backend(monkeypatch, backend)
    base = os.path.join(stage, "manifest")
    if values is None:
        chat80.val_dump(list(chat80.rels), base)
    else:
        _write_store(base, values)
    return base, chat80.val_load(base)


def test_ndbm_drops_a_key_from_iteration_once_a_value_is_large(stage):
    """The backend defect itself, outside nltk: with one value of 4096 bytes the
    iteration returns one key fewer than the store holds."""
    ndbm = pytest.importorskip("dbm.ndbm")
    base = os.path.join(stage, "plain")
    db = ndbm.open(base, "n")
    for i in range(20):
        db[f"k{i:02d}"] = b"x" * (chat80._NDBM_UNSAFE_VALUE if i == 10 else 8)
    db.close()
    db = ndbm.open(base, "r")
    seen = len(list(db.keys()))
    found = sum(1 for i in range(20) if f"k{i:02d}".encode() in db)
    db.close()
    assert found == 20
    if seen != 20:
        assert seen == 19
    else:
        pytest.skip("this ndbm build iterates completely")


@pytest.mark.parametrize("backend", BACKENDS)
def test_a_store_with_a_large_value_round_trips_through_the_manifest(
    stage, monkeypatch, backend
):
    dumped = _dumped(list(chat80.rels))
    big = {"size": "x" * (1024 * 1024)}
    values = dict(dumped)
    values.update(big)
    base, loaded = _dump_and_load(stage, monkeypatch, backend, values=None)
    assert chat80._STORE_MANIFEST_KEY not in loaded
    assert len(loaded) == len(dumped)
    store = shelve.open(base, "w")
    try:
        store["size"] = big["size"]
        store[chat80._STORE_MANIFEST_KEY] = sorted(
            set(store[chat80._STORE_MANIFEST_KEY]) | {"size"}
        )
    finally:
        store.close()
    reloaded = chat80.val_load(base)
    assert reloaded["size"] == big["size"]
    assert len(reloaded) == len(dumped) + 1


@pytest.mark.parametrize("backend", BACKENDS)
def test_val_dump_writes_a_sorted_manifest_of_every_key(stage, monkeypatch, backend):
    base, loaded = _dump_and_load(stage, monkeypatch, backend)
    store = chat80._restricted_shelve_open(base)
    try:
        manifest = store[chat80._STORE_MANIFEST_KEY]
    finally:
        store.close()
    assert manifest == sorted(loaded)
    assert len(manifest) == len(set(manifest))


def test_a_manifest_naming_a_missing_key_is_refused(stage, monkeypatch):
    base, _ = _dump_and_load(stage, monkeypatch, "dbm.dumb")
    store = shelve.open(base, "w")
    try:
        store[chat80._STORE_MANIFEST_KEY] = store[chat80._STORE_MANIFEST_KEY] + [
            "zzz_absent"
        ]
    finally:
        store.close()
    with pytest.raises(ValueError, match="manifest names"):
        chat80.val_load(base)


def test_a_store_holding_keys_its_manifest_does_not_name_is_refused(stage, monkeypatch):
    base, _ = _dump_and_load(stage, monkeypatch, "dbm.dumb")
    store = shelve.open(base, "w")
    try:
        store["planted"] = "x"
    finally:
        store.close()
    with pytest.raises(ValueError, match="does not name"):
        chat80.val_load(base)


@pytest.mark.parametrize(
    "manifest",
    ["notalist", ["b", "a"], ["a", "a"], [1, 2], [chat80._STORE_MANIFEST_KEY]],
)
def test_a_manifest_that_is_not_a_sorted_list_of_names_is_refused(
    stage, monkeypatch, manifest
):
    base, _ = _dump_and_load(stage, monkeypatch, "dbm.dumb")
    store = shelve.open(base, "w")
    try:
        store[chat80._STORE_MANIFEST_KEY] = manifest
    finally:
        store.close()
    with pytest.raises(ValueError, match="manifest"):
        chat80.val_load(base)


def test_a_store_without_a_manifest_still_loads_on_a_complete_backend(
    stage, monkeypatch
):
    _use_backend(monkeypatch, "dbm.dumb")
    base = os.path.join(stage, "old")
    _write_store(base, _dumped(list(chat80.rels)))
    assert len(chat80.val_load(base)) == len(_dumped(list(chat80.rels)))


@pytest.mark.skipif(sys.platform != "darwin", reason="the loss is in macOS ndbm")
def test_a_lossy_store_without_a_manifest_is_refused_on_macos_ndbm(stage, monkeypatch):
    pytest.importorskip("dbm.ndbm")
    _use_backend(monkeypatch, "dbm.ndbm")
    base = os.path.join(stage, "old")
    _write_store(base, {"size": "x" * chat80._NDBM_UNSAFE_VALUE, "small": "v"})
    if dbm.whichdb(base) != "dbm.ndbm":
        pytest.skip("the store was not written by dbm.ndbm")
    with pytest.raises(ValueError, match="dbm.ndbm"):
        chat80.val_load(base)


def test_a_small_valued_store_without_a_manifest_still_loads_on_ndbm(
    stage, monkeypatch
):
    pytest.importorskip("dbm.ndbm")
    _use_backend(monkeypatch, "dbm.ndbm")
    base = os.path.join(stage, "old_small")
    _write_store(base, {"size": "large", "n": "1"})
    assert dict(chat80.val_load(base)) == {"size": "large", "n": "1"}


def test_the_manifest_lookup_is_load_bearing_on_ndbm(stage, monkeypatch):
    """With the manifest ignored, iteration on ndbm loses a key again."""
    pytest.importorskip("dbm.ndbm")
    _use_backend(monkeypatch, "dbm.ndbm")
    base = os.path.join(stage, "teeth")
    values = {
        f"k{i:02d}": "x" * (chat80._NDBM_UNSAFE_VALUE if i == 10 else 1)
        for i in range(20)
    }
    _write_store(base, values)
    if dbm.whichdb(base) != "dbm.ndbm":
        pytest.skip("the store was not written by dbm.ndbm")
    store = shelve.open(base, "w")
    try:
        store[chat80._STORE_MANIFEST_KEY] = sorted(values)
    finally:
        store.close()
    assert len(chat80.val_load(base)) == 20
    monkeypatch.setattr(chat80, "_stored_items", lambda db_in, db: list(db_in.items()))
    lost = chat80.val_load(base)
    if len(lost) == 21:
        pytest.skip("this ndbm build iterates completely; see the simulated teeth")
    assert len(lost) < 21


class _LossyShelf:
    """A shelf whose iteration drops one key but whose lookups are complete,
    the shape of the macOS ndbm defect, independent of the platform."""

    def __init__(self, values, manifest=True):
        self._values = dict(values)
        if manifest:
            self._values[chat80._STORE_MANIFEST_KEY] = sorted(values)

    def __iter__(self):
        return iter(list(self._values)[1:])

    def __len__(self):
        return len(self._values) - 1

    def __contains__(self, key):
        return key in self._values

    def __getitem__(self, key):
        return self._values[key]

    def items(self):
        for key in self:
            yield key, self._values[key]

    def raw_value_sizes(self):
        return [1 for _ in self._values]


def test_the_manifest_defeats_a_lossy_iteration_on_every_platform(stage):
    values = {f"k{i:02d}": "v" for i in range(20)}
    with_manifest = chat80._stored_items(_LossyShelf(values), os.path.join(stage, "m"))
    assert sorted(k for k, _ in with_manifest) == sorted(values)
    without = chat80._stored_items(
        _LossyShelf(values, manifest=False), os.path.join(stage, "n")
    )
    assert len(without) == 19

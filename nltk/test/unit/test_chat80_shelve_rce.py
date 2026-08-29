# Natural Language Toolkit: chat80 shelve deserialization
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""chat80.val_load must not run a pickle gadget from a hostile shelf.

shelve unpickles each stored value with the default, unrestricted
pickle.Unpickler. Validating the .db PATH (which chat80 does) checks WHERE the
file is, not WHAT is in it, so a shelf whose value bytes are a crafted gadget
ran arbitrary code when val_load read it back. The values are now read through
nltk.picklesec.RestrictedUnpickler, which blocks every global while still
loading the plain containers that real chat80 valuations use.

Every shelf here is created and reopened through shelve.open(base), so the tests
run on whatever dbm backend the platform selects (dbm.gnu, dbm.ndbm,
dbm.sqlite3 or dbm.dumb) and never assume a particular on-disk filename.
"""

import os
import pickle
import shelve

import pytest

from nltk import pathsec


class _Gadget:
    """A value whose pickle references a module global (os.system).

    RestrictedUnpickler refuses it at find_class before the reduce is applied;
    the stock unpickler would instead run the command and create the marker.
    """

    def __init__(self, marker):
        self._marker = marker

    def __reduce__(self):
        return (os.system, (f"touch {self._marker}",))


def _make_shelf(base, values):
    with shelve.open(base, "n") as shelf:
        shelf.update(values)


def _gate_shelf(base):
    """Satisfy val_load's os.access(base + '.db') gate on any dbm backend.

    Several backends name the file differently (dbm.gnu writes ``base``,
    dbm.dumb writes ``base.dir`` / ``base.dat``), so hard-link the real backend
    file to ``base + '.db'`` rather than assuming a suffix. Return the shelf keys
    if the shelf still reopens on this backend, else None so the caller can skip.
    """
    gate = base + ".db"
    try:
        if not os.path.exists(gate):
            directory, name = os.path.split(base)
            for entry in sorted(os.listdir(directory or ".")):
                full = os.path.join(directory, entry)
                if (
                    entry.startswith(name)
                    and not entry.endswith(".db")
                    and os.path.isfile(full)
                ):
                    os.link(full, gate)
                    break
        with shelve.open(base, "r") as shelf:
            return set(shelf.keys())
    except Exception:
        return None


def test_restricted_shelf_refuses_a_gadget_value(tmp_path):
    """Core invariant: a value whose pickle needs a global is refused, not run."""
    from nltk.sem.chat80 import _restricted_shelve_open

    base = os.fspath(tmp_path / "hostile")
    marker = os.fspath(tmp_path / "PWNED")
    _make_shelf(base, {"ok": {("chile", "argentina")}, "bad": _Gadget(marker)})

    restricted = _restricted_shelve_open(base)
    try:
        assert restricted["ok"] == {("chile", "argentina")}
        with pytest.raises(pickle.UnpicklingError):
            _ = restricted["bad"]
    finally:
        restricted.close()
    assert not os.path.exists(marker), "reading the shelf executed a pickle gadget"


def test_restricted_shelf_round_trips_benign_valuations(tmp_path):
    """Over-block control: chat80 valuations are sets and tuples of strings,
    which the restricted unpickler must still load."""
    from nltk.sem.chat80 import _restricted_shelve_open

    base = os.fspath(tmp_path / "good")
    values = {
        "adjacent": {("chile", "argentina"), ("uk", "france")},
        "size": {("uk", "244820")},
    }
    _make_shelf(base, values)

    restricted = _restricted_shelve_open(base)
    try:
        assert sorted(restricted.keys()) == ["adjacent", "size"]
        assert restricted["adjacent"] == {("chile", "argentina"), ("uk", "france")}
        assert dict(restricted.items()) == values
    finally:
        restricted.close()


def test_val_load_end_to_end_does_not_execute_gadget(tmp_path, monkeypatch):
    """val_load (path gate, restricted read and Valuation wiring) must refuse a
    gadget rather than run it. Skips only on a backend whose files cannot satisfy
    val_load's '.db' gate here; the invariant still holds via the direct tests.
    """
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    from nltk.sem import chat80

    base = os.fspath(tmp_path / "hostile")
    marker = os.fspath(tmp_path / "PWNED")
    _make_shelf(base, {"bad": _Gadget(marker)})

    keys = _gate_shelf(base)
    if keys is None or "bad" not in keys:
        pytest.skip("dbm backend cannot satisfy val_load's .db gate portably here")

    with pytest.raises(pickle.UnpicklingError):
        valuation = chat80.val_load(base)
        list(valuation.items())
    assert not os.path.exists(marker), "chat80.val_load executed a pickle gadget"

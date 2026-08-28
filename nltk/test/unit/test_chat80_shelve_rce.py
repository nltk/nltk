# Natural Language Toolkit: chat80 shelve deserialization
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""chat80.val_load must not run a pickle gadget from a hostile .db file.

shelve unpickles each stored value with the default, unrestricted
pickle.Unpickler. Validating the .db PATH (which chat80 does) checks WHERE the
file is, not WHAT is in it, so a .db whose value bytes are a crafted gadget --
planted inside the sandbox, e.g. shipped in a data package -- ran arbitrary code
when val_load read it back through Valuation.

chat80 valuations are only sets and tuples of strings, so the values are read
with RestrictedUnpickler, which blocks every global while still loading plain
containers.
"""

import dbm
import os
import pickle
import shelve
import shutil
import tempfile

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def sandbox_root(monkeypatch):
    root = tempfile.mkdtemp(prefix="nltk_sandbox_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _ensure_db_suffix(root, db):
    """val_load's access check needs a readable <db>.db; link the backend file."""
    if os.path.exists(db + ".db"):
        return
    base = os.path.basename(db)
    for name in os.listdir(root):
        if name.startswith(base) and not name.endswith(".db"):
            os.link(os.path.join(root, name), db + ".db")
            return


def _plant_gadget_db(root, marker):
    db = os.path.join(root, "evil")

    class _Rce:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    shelf = shelve.open(db, "n")
    shelf["k"] = "benign"
    shelf.close()
    backend = dbm.open(db, "w")
    backend["k"] = pickle.dumps(_Rce())
    backend.close()
    _ensure_db_suffix(root, db)
    return db


def test_a_gadget_db_does_not_execute(sandbox_root):
    from nltk.sem import chat80

    marker = os.path.join(sandbox_root, "PWNED")
    db = _plant_gadget_db(sandbox_root, marker)
    with pytest.raises((pickle.UnpicklingError, ValueError, KeyError, Exception)):
        valuation = chat80.val_load(db)
        list(valuation.items())
    assert not os.path.exists(marker), "chat80.val_load executed a pickle gadget"


def test_legitimate_valuations_round_trip(sandbox_root):
    """Over-block control: real chat80 data is sets/tuples of strings, which the
    restricted unpickler must still load."""
    from nltk.sem import chat80

    db = os.path.join(sandbox_root, "good")
    valuation = {
        "adjacent": {("chile", "argentina"), ("uk", "france")},
        "size": {("uk", "244820")},
    }
    shelf = shelve.open(db, "n")
    shelf.update(valuation)
    shelf.close()
    _ensure_db_suffix(sandbox_root, db)

    loaded = chat80.val_load(db)
    assert sorted(loaded.keys()) == ["adjacent", "size"]
    assert loaded["adjacent"] == {("chile", "argentina"), ("uk", "france")}


def test_restricted_shelf_blocks_a_global_but_allows_containers(sandbox_root):
    """Directly exercise the helper's read path."""
    from nltk.sem.chat80 import _restricted_shelve_open

    db = os.path.join(sandbox_root, "mix")
    shelf = shelve.open(db, "n")
    shelf["ok"] = {("a", "b")}
    shelf.close()
    backend = dbm.open(db, "w")
    backend["bad"] = b"cposix\nsystem\n0."
    backend.close()

    restricted = _restricted_shelve_open(db)
    assert restricted["ok"] == {("a", "b")}
    with pytest.raises((pickle.UnpicklingError, ValueError)):
        _ = restricted["bad"]
    restricted.close()

# Natural Language Toolkit: pickle gadgets must be refused BY THE UNPICKLER
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Gadget pickles must be refused by picklesec, not merely by the path check.

The first version of this probe put its payloads outside the data roots. Every
one was "blocked" -- by ``validate_path``, before the unpickler ever ran. That
is a false pass: it would have stayed green with the entire allowlist deleted.

So each payload here is written INSIDE the sandbox under a legitimate resource
name, and the assertion is on the error itself: an ``UnpicklingError`` naming the
forbidden global. A ``PermissionError`` or ``ValueError`` from the path layer
fails these tests, because it means the gadget was never actually tried.
"""

import os
import pickle
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


def _stage(root, name, payload):
    with pathsec.open(os.path.join(root, name), "wb", context="test") as handle:
        handle.write(payload)
    return name


def _assert_refused_by_the_unpickler(excinfo, needle):
    error = excinfo.value
    assert isinstance(error, pickle.UnpicklingError), (
        f"refused by {type(error).__name__}, not the unpickler: the payload never "
        "reached picklesec, so this proves nothing"
    )
    assert needle in str(error), str(error)


@pytest.mark.parametrize(
    "module, attribute",
    [
        ("posixpath", "expandvars"),
        ("ntpath", "expandvars"),
        ("subprocess", "Popen"),
        ("os", "popen"),
        ("os", "system"),
        ("builtins", "eval"),
        ("builtins", "exec"),
        ("shutil", "rmtree"),
        ("nt", "system"),
        ("webbrowser", "open"),
    ],
)
def test_dotted_name_gadgets_are_refused_by_picklesec(sandbox_root, module, attribute):
    payload = f"c{module}\n{attribute}\n(S'x'\ntR.".encode()
    name = _stage(sandbox_root, "gadget.pickle", payload)
    with pytest.raises(Exception) as excinfo:
        nltk.data.load(name, format="pickle")
    _assert_refused_by_the_unpickler(excinfo, attribute)


def test_a_reduce_based_rce_gadget_is_refused_and_does_not_run(sandbox_root):
    """The concrete proof: the command must not execute."""
    marker = os.path.join(sandbox_root, "PWNED")

    class _Rce:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    name = _stage(sandbox_root, "rce.pickle", pickle.dumps(_Rce()))
    with pytest.raises(Exception) as excinfo:
        nltk.data.load(name, format="pickle")
    _assert_refused_by_the_unpickler(excinfo, "system")
    assert not os.path.exists(marker), "the gadget executed"


def test_benign_pickles_still_load(sandbox_root):
    """Over-block control: the allowlist must not refuse ordinary data."""
    name = _stage(sandbox_root, "ok.pickle", pickle.dumps({"a": [1, 2, 3]}))
    assert nltk.data.load(name, format="pickle") == {"a": [1, 2, 3]}


def test_the_payloads_really_are_inside_the_sandbox(sandbox_root):
    """Guards the guard: if staging drifted back outside the roots, every test
    above would pass for the wrong reason."""
    name = _stage(sandbox_root, "probe.pickle", pickle.dumps([1]))
    pathsec.validate_path(os.path.join(sandbox_root, name), context="test")
    assert nltk.data.load(name, format="pickle") == [1]

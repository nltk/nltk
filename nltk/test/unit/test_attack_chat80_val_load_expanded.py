# Natural Language Toolkit: deserialization attack tests (chat80 val_load)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Deserialization attack tests for ``chat80.val_load`` (CWE-502).

A chat80 store is attacker-reachable data: a file under a data root another
process, a downloaded package or a planted dbm/sqlite file could shape. ``shelve``
unpickles each stored value, so a crafted value could run code when read back.
``val_load`` reads values through :class:`nltk.picklesec.RestrictedUnpickler`,
which refuses every class or function global, and only then rebuilds the
Valuation, accepting the exact shapes ``val_dump`` writes and refusing the rest.

Every payload is planted only in a store under a throwaway directory, each marker
is a benign file whose presence would mean a sink ran, and the heavy cases run on
a daemon thread with a hard deadline. The teeth: the same bytes under the stock
``pickle.loads`` do create the marker, so each payload is a real gadget that the
restricted read refuses before it fires. ``pathsec.ENFORCE`` is turned off so the
path guards (tested in ``test_attack_chat80_store_expanded``) do not mask the
deserialization guard under test.
"""

import os
import pickle
import subprocess
import unicodedata

import pytest

from nltk import pathsec
from nltk.test.unit import timing

BACKENDS = ["dbm.sqlite3", "dbm.dumb", "dbm.ndbm", "dbm.gnu"]


def _backend(name):
    try:
        return __import__(name, fromlist=["open"])
    except ImportError:
        pytest.skip(f"{name} not available on this interpreter")


@pytest.fixture
def unenforced(monkeypatch):
    """Turn pathsec enforcement off so this suite isolates the pickle guard."""
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)


# ---------------------------------------------------------------------------
# Gadgets: each pickles to a stream that reaches a global the restricted
# unpickler must refuse. ``open(path, "w")`` is the portable marker sink (it
# creates the file on every platform); os.system / subprocess.call are the
# canonical RCE globals, with a POSIX marker command for the teeth.
# ---------------------------------------------------------------------------
class _OpenGadget:
    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (open, (self.path, "w"))


class _OpenReduceExGadget:
    def __init__(self, path):
        self.path = path

    def __reduce_ex__(self, protocol):
        return (open, (self.path, "w"))


class _SystemGadget:
    def __init__(self, cmd):
        self.cmd = cmd

    def __reduce__(self):
        return (os.system, (self.cmd,))


class _SubprocessGadget:
    def __init__(self, args):
        self.args = args

    def __reduce__(self):
        return (subprocess.call, (self.args,))


class _EvilStr(str):
    """A str subclass; pickling it needs the subclass global, which is refused,
    and ``_is_extension_list`` would reject it anyway (it tests ``type is str``)."""

    def __reduce__(self):
        return (open, (str.__str__(self), "w"))


def _marker(tmp_path, tag):
    path = os.fspath(tmp_path / f"MARK_{tag}")
    for p in (path,):
        try:
            os.remove(p)
        except FileNotFoundError:
            pass
    return path


def _plant(module, base, key, raw):
    """Write benign and payload bytes straight into the backend, bypassing
    shelve's pickler so the payload bytes are exactly ``raw``."""
    from nltk.sem import chat80

    db = module.open(base, "n")
    try:
        db[b"ok"] = pickle.dumps(["athens", "bangkok"])
        db[key] = raw
        names = ["ok"]
        try:
            names.append(key.decode() if isinstance(key, bytes) else key)
        except UnicodeDecodeError:
            pass
        names = sorted(set(names))
        db[chat80._STORE_MANIFEST_KEY.encode()] = pickle.dumps(names)
    finally:
        db.close()


def _val_load_items(base):
    from nltk.sem import chat80

    return list(chat80.val_load(base).items())


def _drive(base, seconds=20):
    """Run val_load on a daemon thread; return (finished, exception)."""
    finished, exc, _ = timing.finishes_within(seconds, lambda: _val_load_items(base))
    return finished, exc


# ===========================================================================
# REDUCE gadgets naming a dangerous global, one per backend
# ===========================================================================
@pytest.mark.parametrize("backend", BACKENDS)
def test_open_gadget_is_refused_before_it_creates_the_marker(
    unenforced, tmp_path, backend
):
    module = _backend(backend)
    marker = _marker(tmp_path, "open")
    base = os.fspath(tmp_path / "open_store")
    raw = pickle.dumps(_OpenGadget(marker))
    _plant(module, base, b"bad", raw)

    # teeth: the stock unpickler runs the reduce and creates the marker
    assert not os.path.exists(marker)
    pickle.loads(raw)
    assert os.path.exists(marker), "payload is not actually a gadget"
    os.remove(marker)

    finished, exc = _drive(base)
    assert finished
    assert isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker), "val_load ran the gadget"


@pytest.mark.parametrize("backend", BACKENDS)
def test_reduce_ex_gadget_is_refused(unenforced, tmp_path, backend):
    module = _backend(backend)
    marker = _marker(tmp_path, "rex")
    base = os.fspath(tmp_path / "rex_store")
    raw = pickle.dumps(_OpenReduceExGadget(marker))
    _plant(module, base, b"bad", raw)
    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker)


@pytest.mark.skipif(os.name != "posix", reason="POSIX marker command")
@pytest.mark.parametrize("gadget_name", ["system", "subprocess"])
def test_os_command_gadgets_are_refused(unenforced, tmp_path, gadget_name):
    module = _backend("dbm.sqlite3")
    marker = _marker(tmp_path, gadget_name)
    base = os.fspath(tmp_path / f"{gadget_name}_store")
    if gadget_name == "system":
        gadget = _SystemGadget(f"touch {marker}")
    else:
        gadget = _SubprocessGadget(["touch", marker])
    raw = pickle.dumps(gadget)
    _plant(module, base, b"bad", raw)

    pickle.loads(raw)
    assert os.path.exists(marker), "payload is not actually a gadget"
    os.remove(marker)

    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker)


# ===========================================================================
# The same gadget at every pickle protocol
# ===========================================================================
@pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
def test_every_protocol_of_the_open_gadget_is_refused(unenforced, tmp_path, protocol):
    module = _backend("dbm.sqlite3")
    marker = _marker(tmp_path, f"proto{protocol}")
    base = os.fspath(tmp_path / f"proto{protocol}_store")
    raw = pickle.dumps(_OpenGadget(marker), protocol=protocol)
    _plant(module, base, b"bad", raw)

    assert not os.path.exists(marker)
    pickle.loads(raw)
    assert os.path.exists(marker)
    os.remove(marker)

    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker)


# ===========================================================================
# A gadget hidden INSIDE the exact list-of-pairs shape _is_extension_list takes
# ===========================================================================
def test_gadget_nested_in_an_accepted_pair_is_refused(unenforced, tmp_path):
    """A tuple whose second element is a REDUCE gadget: the stream still carries
    the forbidden global, so the restricted read refuses it before the tuple
    (and the list that would pass _is_extension_list) is ever built."""
    module = _backend("dbm.sqlite3")
    marker = _marker(tmp_path, "nested")
    base = os.fspath(tmp_path / "nested_store")
    raw = pickle.dumps([("athens", _OpenGadget(marker))])
    _plant(module, base, b"border", raw)

    pickle.loads(raw)
    assert os.path.exists(marker)
    os.remove(marker)

    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker)


def test_str_subclass_value_is_refused(unenforced, tmp_path):
    module = _backend("dbm.sqlite3")
    marker = _marker(tmp_path, "evilstr")
    base = os.fspath(tmp_path / "evilstr_store")
    raw = pickle.dumps([_EvilStr(marker)])
    _plant(module, base, b"city", raw)

    pickle.loads(raw)
    assert os.path.exists(marker)
    os.remove(marker)

    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert not os.path.exists(marker)


def test_is_extension_list_rejects_non_exact_str_and_tuple_types():
    """Unit guard: _is_extension_list uses exact types, so a str subclass, a
    bool (an int subclass) or a nested list is never treated as a relation."""
    from nltk.sem.chat80 import _is_extension_list

    assert _is_extension_list(["athens", "bangkok"]) is True
    assert _is_extension_list([("a", "b")]) is True
    assert _is_extension_list([_EvilStr("x"), _EvilStr("y")]) is False
    assert _is_extension_list([True, False]) is False
    assert _is_extension_list([("a", 1)]) is False
    assert _is_extension_list([["a"]]) is False
    assert _is_extension_list(["bangkok", "athens"]) is False  # not sorted
    assert _is_extension_list(["a", "a"]) is False  # not distinct


def test_a_numpy_global_value_is_refused(unenforced, tmp_path):
    """A third-party global (numpy) is refused at find_class without importing
    or running anything, so the module need not even be installed."""
    module = _backend("dbm.sqlite3")
    base = os.fspath(tmp_path / "numpy_store")
    # a GLOBAL opcode for numpy.save, then an empty-tuple REDUCE: find_class is
    # invoked at the GLOBAL and refuses before numpy is imported or touched
    raw = b"cnumpy\nsave\n)R."
    _plant(module, base, b"bad", raw)
    finished, exc = _drive(base)
    assert finished and isinstance(exc, pickle.UnpicklingError), exc
    assert "numpy.save" in str(exc), exc


# ===========================================================================
# Benign-but-malformed values: no code runs; a clean refusal or a clean error
# ===========================================================================
def test_a_dict_in_place_of_a_pair_is_refused_by_the_constructor(unenforced, tmp_path):
    module = _backend("dbm.sqlite3")
    base = os.fspath(tmp_path / "dict_store")
    _plant(module, base, b"border", pickle.dumps([{"athens": "greece"}]))
    finished, exc = _drive(base)
    assert finished and isinstance(exc, ValueError), exc
    assert "Unrecognized value for symbol" in str(exc)


@pytest.mark.parametrize("backend", BACKENDS)
def test_a_non_utf8_key_raises_a_clean_error_not_code(unenforced, tmp_path, backend):
    module = _backend(backend)
    base = os.fspath(tmp_path / "byteskey_store")
    _plant(module, base, b"\xff\xfe", pickle.dumps(["athens"]))
    finished, exc = _drive(base)
    # shelve decodes keys as utf-8; a non-utf8 key is a clean decode error
    assert finished and isinstance(exc, (UnicodeDecodeError, ValueError)), exc


def test_a_unicode_normalising_key_does_not_collide_or_run_code(unenforced, tmp_path):
    module = _backend("dbm.sqlite3")
    base = os.fspath(tmp_path / "nfd_store")
    key = unicodedata.normalize("NFD", "café").encode()
    _plant(module, base, key, pickle.dumps(["athens"]))
    finished, exc = _drive(base)
    assert finished and exc is None, exc


def test_a_deeply_nested_value_does_not_recurse_without_bound_or_run_code(
    unenforced, tmp_path
):
    """A crafted stream of 10000 nested lists (MARK*d then LIST*d): the loader
    builds it iteratively, so no gadget runs; the value is refused (it is not a
    relation) with a bounded error, never a hang."""
    module = _backend("dbm.sqlite3")
    base = os.fspath(tmp_path / "deep_store")
    depth = 10000
    _plant(module, base, b"city", b"(" * depth + b"l" * depth + b".")
    finished, exc = _drive(base, seconds=20)
    assert finished, "val_load did not finish on a deeply nested value"
    assert isinstance(exc, (ValueError, RecursionError)), exc


def test_a_giant_value_loads_in_bounded_time_without_running_code(unenforced, tmp_path):
    """A large sorted list of distinct strings is a legitimate relation shape,
    so it loads; the point is that it does so in linear time and runs no code."""
    module = _backend("dbm.sqlite3")
    base = os.fspath(tmp_path / "giant_store")
    value = sorted("s%08d" % i for i in range(300000))
    _plant(module, base, b"city", pickle.dumps(value))
    finished, exc = _drive(base, seconds=60)
    assert finished, "val_load did not finish on a large value"
    assert exc is None and not isinstance(exc, MemoryError), exc

# Natural Language Toolkit: broad pickle gadget landscape
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""A wide sweep of pickle gadget primitives against the allowlisted unpickler.

Compiled from published RCE research on NLTK and comparable ML libraries
(CVE-2024-39705, CVE-2026-78683, CVE-2026-71513, and the general gadget
landscape). Each is a regression probe: the guards already deny them, and this
keeps them denied.

Two failure modes these tests are built to avoid:

* Staging OUTSIDE the sandbox, so validate_path blocks before the unpickler
  runs. Everything is staged inside a data root.
* A malformed pickle that raises "data was truncated" from the C unpickler
  before find_class is reached, which proves nothing. Global gadgets use the
  well-formed ``c<module>\\n<name>\\n0.`` form (GLOBAL, POP, STOP), and the
  extension and reduce forms are exercised through pickle's own machinery.
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


def _load(root, payload):
    with pathsec.open(os.path.join(root, "g.pickle"), "wb", context="test") as handle:
        handle.write(payload)
    return nltk.data.load("g.pickle", format="pickle")


@pytest.mark.parametrize(
    "opcode, label",
    [(b"\x82\x01.", "EXT1"), (b"\x83\x01\x00.", "EXT2"), (b"\x84\x01\x00\x00\x00.", "EXT4")],
)
def test_extension_registry_opcodes_are_refused(sandbox_root, opcode, label):
    """These resolve through copyreg WITHOUT calling find_class, so a name
    allowlist alone does not stop them. The opcode itself must be rejected."""
    with pytest.raises(pickle.UnpicklingError) as excinfo:
        _load(sandbox_root, opcode)
    assert "extension" in str(excinfo.value).lower()


@pytest.mark.parametrize(
    "module, name",
    [
        ("os", "system"),
        ("posix", "system"),
        ("nt", "system"),
        ("os", "popen"),
        ("subprocess", "Popen"),
        ("subprocess", "getoutput"),
        ("subprocess", "call"),
        ("builtins", "getattr"),
        ("operator", "attrgetter"),
        ("functools", "partial"),
        ("functools", "reduce"),
        ("marshal", "loads"),
        ("copyreg", "_reconstructor"),
        ("types", "FunctionType"),
        ("types", "CodeType"),
        ("numpy", "load"),
        ("numpy", "fromfile"),
        ("pandas", "read_pickle"),
        ("webbrowser", "open"),
        ("pty", "spawn"),
        ("importlib", "import_module"),
        ("__builtin__", "eval"),
    ],
)
def test_dangerous_globals_are_forbidden_by_name(sandbox_root, module, name):
    """GLOBAL, POP, STOP: find_class IS reached, then the name is refused."""
    payload = f"c{module}\n{name}\n0.".encode()
    with pytest.raises(pickle.UnpicklingError) as excinfo:
        _load(sandbox_root, payload)
    assert "forbidden" in str(excinfo.value) or name in str(excinfo.value)


@pytest.mark.parametrize(
    "module, name",
    [("os", "system"), ("os", "popen"), ("subprocess", "Popen"), ("builtins", "eval")],
)
def test_stack_global_form_is_also_refused(sandbox_root, module, name):
    """proto>=4 STACK_GLOBAL takes module and name off the stack, which the C
    unpickler handles differently from the GLOBAL opcode. Both must be blocked."""
    import io
    import pickletools

    buffer = io.BytesIO()
    pickler = pickle.Pickler(buffer, protocol=5)
    # Force the STACK_GLOBAL opcode by pickling a reference to the callable,
    # then rewrite the target to the dangerous one via a raw opcode stream.
    payload = (
        b"\x80\x05"
        + b"\x8c" + bytes([len(module)]) + module.encode()
        + b"\x8c" + bytes([len(name)]) + name.encode()
        + b"\x93" + b"0."
    )
    with pytest.raises(pickle.UnpicklingError):
        _load(sandbox_root, payload)


def test_a_reduce_eval_import_chain_does_not_execute(sandbox_root):
    """The weaponised form: REDUCE over builtins.eval running an os.system."""
    marker = os.path.join(sandbox_root, "PWNED")

    class _EvalChain:
        def __reduce__(self):
            return (eval, (f"__import__('os').system('touch {marker}')",))

    with pytest.raises(pickle.UnpicklingError) as excinfo:
        _load(sandbox_root, pickle.dumps(_EvalChain()))
    assert "forbidden" in str(excinfo.value)
    assert not os.path.exists(marker), "the gadget executed"


def test_a_reduce_os_system_gadget_does_not_execute(sandbox_root):
    marker = os.path.join(sandbox_root, "PWNED2")

    class _Sys:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    with pytest.raises(pickle.UnpicklingError):
        _load(sandbox_root, pickle.dumps(_Sys()))
    assert not os.path.exists(marker)


def test_benign_pickles_are_unaffected(sandbox_root):
    """Over-block control across the container types NLTK actually pickles."""
    # Distinct filenames: nltk.data.load caches by resource name, so reusing one
    # would hand back the first value for every case.
    for index, value in enumerate(
        ({"a": [1, 2, 3]}, [1, "two", 3.0], ("t", 1), {1, 2, 3}, "plain")
    ):
        name = f"ok{index}.pickle"
        with pathsec.open(
            os.path.join(sandbox_root, name), "wb", context="test"
        ) as handle:
            pickle.dump(value, handle)
        assert nltk.data.load(name, format="pickle") == value

"""Adversarial proof that excluding pytest's basetemp from the pickle-asset
scanner opens no load-time hole.

``test_all_nltk_data_pickle_assets_load`` skips pytest's ephemeral session base
(a conftest-authorized nltk.data.path root) so it only validates real installed
assets. That scanner is a regression test, not the security boundary: the
boundary is ``nltk.data.load``'s restricted unpickler, which refuses dangerous
globals, hand-written opcodes, nested loads and unsafe resource paths on EVERY
load, no matter which root the file lives in or which roots the scanner skips.

These tests attack that boundary directly -- including from inside a trusted,
scanner-excluded root and from behind a symlink -- and confirm nothing executes
and nothing is read outside the roots (CWE-502 / CWE-22 / CWE-59). If the
scanner exclusion were a hole, one of these would load.
"""

import importlib
import os
import pickle

import pytest


@pytest.fixture
def authorized_root(monkeypatch, tmp_path):
    """A trusted, authorized nltk.data.path root -- the same kind conftest
    authorizes for pytest's basetemp, and the kind the scanner now excludes."""
    import nltk.data as _data
    from nltk import pathsec

    (tmp_path / "corpora").mkdir()
    monkeypatch.setattr(_data, "path", [str(tmp_path), *_data.path])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    return tmp_path


def _drop(root, raw):
    (root / "corpora" / "g.pickle").write_bytes(raw)
    return "corpora/g.pickle"


# Every dangerous global a gadget could name: process / exec / eval / import /
# native / file / socket / nested-unpickle / call-traversal primitives.
_DANGEROUS = [
    ("os", "system"), ("os", "popen"), ("os", "execv"), ("os", "spawnv"),
    ("os", "remove"), ("os", "unlink"), ("os", "rmdir"), ("os", "chmod"),
    ("os", "rename"), ("posix", "system"), ("subprocess", "call"),
    ("subprocess", "Popen"), ("subprocess", "run"), ("subprocess", "check_output"),
    ("subprocess", "getoutput"), ("builtins", "eval"), ("builtins", "exec"),
    ("builtins", "__import__"), ("builtins", "compile"), ("builtins", "open"),
    ("builtins", "getattr"), ("builtins", "setattr"), ("importlib", "import_module"),
    ("ctypes", "CDLL"), ("shutil", "rmtree"), ("shutil", "copy"),
    ("socket", "socket"), ("webbrowser", "open"), ("io", "open"),
    ("codecs", "open"), ("pickle", "loads"), ("operator", "attrgetter"),
    ("operator", "methodcaller"), ("functools", "partial"),
]  # fmt: skip


def _forbidden(exc):
    text = str(exc).lower()
    return (
        "forbidden" in text
        or "restrict" in text
        or "not allowed" in text
        or type(exc).__name__ == "UnpicklingError"
    )


@pytest.mark.parametrize("module,qualname", _DANGEROUS)
def test_reduce_gadget_global_is_refused_from_authorized_root(
    authorized_root, module, qualname
):
    """A __reduce__ gadget naming a dangerous global is refused even when the
    pickle sits in a trusted, scanner-excluded root, and nothing executes."""
    import nltk

    try:
        obj = importlib.import_module(module)
        for part in qualname.split("."):
            obj = getattr(obj, part)
    except (ImportError, AttributeError):  # pragma: no cover - platform dependent
        pytest.skip(f"{module}.{qualname} unavailable on this platform")

    marker = authorized_root / "PWNED"

    class _Gadget:
        def __reduce__(self):
            return (obj, (f"touch {marker}",) if callable(obj) else ())

    res = _drop(authorized_root, pickle.dumps(_Gadget()))
    with pytest.raises(Exception) as exc:
        nltk.data.load(res)
    assert _forbidden(exc.value)
    assert not marker.exists()


@pytest.mark.parametrize(
    "raw,label",
    [
        (
            b"\x80\x04\x95\x1a\x00\x00\x00\x00\x00\x00\x00\x8c\x02os\x94"
            b"\x8c\x06system\x94\x93\x94\x8c\x02id\x94\x85\x94R\x94.",
            "STACK_GLOBAL os.system",
        ),
        (b"cposix\nsystem\n(S'id'\ntR.", "GLOBAL posix.system"),
        (b"\x80\x02\x82\x01.", "EXT1 extension registry"),
    ],
)
def test_hand_written_opcode_gadget_is_refused(authorized_root, raw, label):
    """Raw GLOBAL / STACK_GLOBAL / extension-registry opcodes are refused, not
    just __reduce__ pickles."""
    import nltk

    with pytest.raises(Exception):
        nltk.data.load(_drop(authorized_root, raw))


def test_nested_pickle_loads_gadget_is_refused(authorized_root):
    """A pickle whose reduce calls pickle.loads(<inner gadget>) is refused: the
    outer load never reaches the inner bytes (pickle.loads is itself forbidden)."""
    import nltk

    marker = authorized_root / "PWNED"
    inner = b"cposix\nsystem\n(S'touch %s'\ntR." % str(marker).encode()

    class _Nest:
        def __reduce__(self):
            return (pickle.loads, (inner,))

    with pytest.raises(Exception):
        nltk.data.load(_drop(authorized_root, pickle.dumps(_Nest())))
    assert not marker.exists()


@pytest.mark.parametrize(
    "resource",
    [
        "../../../../etc/passwd",
        "corpora/../../../../etc/passwd",
        "/etc/passwd",
        "corpora/a\x00b.pickle",
        "file:///etc/passwd",
    ],
)
def test_unsafe_resource_path_is_refused(resource):
    """Traversal, absolute, NUL-byte and file:// resource names are refused before
    any content is returned (CWE-22 / CWE-59)."""
    import nltk

    with pytest.raises(Exception):
        nltk.data.load(resource)


def test_gadget_behind_a_symlinked_authorized_root_is_refused(monkeypatch, tmp_path):
    """A trusted root reached through a symlink is realpath-resolved, and a gadget
    behind it is still refused -- no symlink-hijack bypass (CWE-59)."""
    import nltk
    import nltk.data as _data
    from nltk import pathsec

    real = tmp_path / "real"
    (real / "corpora").mkdir(parents=True)
    link = tmp_path / "link"
    os.symlink(real, link)
    marker = real / "PWNED"

    class _Gadget:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    (real / "corpora" / "g.pickle").write_bytes(pickle.dumps(_Gadget()))
    monkeypatch.setattr(_data, "path", [str(link), *_data.path])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    with pytest.raises(Exception):
        nltk.data.load("corpora/g.pickle")
    assert not marker.exists()

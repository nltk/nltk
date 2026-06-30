"""
Path-traversal regression tests for ``nltk.data`` resource resolution.

Covers issue nltk/nltk#3504 / CVE-2026-54293: arbitrary file read via
percent-encoded sequences that bypass the path-safety checks and are then
decoded into a real traversal path by ``urllib.request.url2pathname()``.

The committed payloads only ever target a synthetic sentinel file created
inside the test's own temporary directory; no real system file is read.
"""

import os
import pickle
import types
import zipfile
from pathlib import Path

import pytest

import nltk.data as data
from nltk import pathsec

SENTINEL = b"OUTSIDE-ROOT-SENTINEL-DO-NOT-READ"


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A hermetic nltk_data root plus an out-of-root sentinel file."""
    root = tmp_path / "nltk_data"
    corp = root / "corpora" / "mycorp"
    corp.mkdir(parents=True)
    (corp / "data.txt").write_text("hello world", encoding="utf-8")
    (corp / "a.b.c.txt").write_text("dotted", encoding="utf-8")
    (corp / "obj.pickle").write_bytes(pickle.dumps({"a": 1}))

    deep = corp.joinpath(*list("abcdefgh"))
    deep.mkdir(parents=True)
    (deep / "deep.txt").write_text("deep-ok", encoding="utf-8")

    (root / "grammars").mkdir()
    (root / "grammars" / "toy.cfg").write_text("S -> 'a'\n", encoding="utf-8")

    with zipfile.ZipFile(root / "corpora" / "zc.zip", "w") as zf:
        zf.writestr("zc/inside.txt", "zipped-bytes")

    secret = tmp_path / "secret.txt"
    secret.write_bytes(SENTINEL)

    monkeypatch.setattr(data, "path", [str(root)])
    monkeypatch.setattr(data, "_resource_cache", {})
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {root.resolve()})
    return types.SimpleNamespace(root=root, secret=secret, tmp=tmp_path)


def _read_or_none(resource, paths):
    """find()+open() the resource, returning its bytes or None if it is refused."""
    try:
        ptr = data.find(resource, paths=paths)
        stream = ptr.open()
    except (ValueError, LookupError, OSError, PermissionError):
        return None
    try:
        return stream.read()
    except (ValueError, LookupError, OSError, PermissionError):
        return None
    finally:
        try:
            stream.close()
        except Exception:
            pass


_MUST_RAISE_VALUEERROR = [
    "%2e%2e/secret",
    "..%2f",
    "..%2fsecret",
    "%2E%2E",
    ".%2e",
    "%2E%2e",
    "%2e%2E/secret",
    "%2e%2e%2fsecret",
    "corpora/..%2f..%2fsecret",
    "corpora/%2e%2e/%2e%2e/secret",
    "corpora/%2E%2E/%2E%2E/secret",
    "%2fetc%2fpasswd",
    "%2Fetc%2Fpasswd",
    "%5c..%5csecret",
    "%43%3a%5csecret",
    r"..\..\secret",
    r"corpora\..\..\secret",
    "C:/secret",
    r"C:\secret",
]


@pytest.mark.parametrize("payload", _MUST_RAISE_VALUEERROR)
def test_find_rejects_traversal_variants(env, payload):
    with pytest.raises(ValueError):
        data.find(payload, paths=[str(env.root)])


@pytest.mark.parametrize("payload", _MUST_RAISE_VALUEERROR)
def test_normalize_rejects_traversal_variants(env, payload):
    with pytest.raises(ValueError):
        data.normalize_resource_url("nltk:" + payload)


@pytest.mark.parametrize("payload", _MUST_RAISE_VALUEERROR)
def test_load_rejects_traversal_variants(env, payload):
    with pytest.raises(ValueError):
        data.load("nltk:" + payload, format="raw")


_SENTINEL_PAYLOADS = [
    "%2e%2e/secret.txt",
    "..%2fsecret.txt",
    "%2e%2e%2fsecret.txt",
    "corpora/%2e%2e/%2e%2e/secret.txt",
    "corpora/..%2f..%2fsecret.txt",
    "%252e%252e/secret.txt",
    "%252e%252e%252fsecret.txt",
    "%2e%2e/secret.txt%00",
    "%2e%2e/secret.txt%00.txt",
    r"..\secret.txt",
    "%2e%2e%5csecret.txt",
    "%2fsecret.txt",
]


@pytest.mark.parametrize("payload", _SENTINEL_PAYLOADS)
def test_payload_never_reads_out_of_root_sentinel(env, payload):
    """The /etc/passwd-equivalent read attempt, against a synthetic sentinel."""
    assert _read_or_none(payload, [str(env.root)]) != SENTINEL


def test_absolute_file_uri_to_sentinel_is_blocked(env):
    """A ``file://`` URI to the out-of-root sentinel is denied by the sandbox."""
    with pytest.raises((PermissionError, ValueError, LookupError)):
        data.load(env.secret.resolve().as_uri(), format="raw")


def test_double_encoded_resolves_in_root_not_host(env):
    """Double-encoding decodes once: a literal in-root name, never the sentinel."""
    with pytest.raises((LookupError, ValueError)):
        data.load("nltk:%252e%252e/secret.txt", format="raw")
    assert _read_or_none("%252e%252e/secret.txt", [str(env.root)]) != SENTINEL


def test_symlink_escape_is_blocked(env):
    """An in-root symlink pointing outside the root is refused (realpath guard).

    This is the case a substring/regex blocklist cannot catch: the resource
    name is a perfectly ordinary in-root name, and only realpath resolution
    reveals that it escapes the data directory.
    """
    link = env.root / "corpora" / "escape.txt"
    try:
        os.symlink(env.secret, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported in this environment")

    with pytest.raises(ValueError):
        data.find("corpora/escape.txt", paths=[str(env.root)])
    assert _read_or_none("corpora/escape.txt", [str(env.root)]) != SENTINEL


def test_null_byte_payloads_never_read_sentinel(env):
    for payload in ("corpora/%00/secret.txt", "corpora/secret%00.txt"):
        assert _read_or_none(payload, [str(env.root)]) != SENTINEL


def test_guard_is_independent_of_pathsec_enforce(env, monkeypatch):
    """find()'s containment guard rejects traversal even with ENFORCE disabled."""
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    with pytest.raises(ValueError):
        data.find("%2e%2e/secret.txt", paths=[str(env.root)])


def test_nltk_scheme_raw(env):
    assert data.load("nltk:corpora/mycorp/data.txt", format="raw") == b"hello world"


def test_no_scheme_text(env):
    assert data.load("corpora/mycorp/data.txt", format="text") == "hello world"


def test_file_scheme_raw(env):
    uri = (env.root / "corpora" / "mycorp" / "data.txt").resolve().as_uri()
    assert data.load(uri, format="raw") == b"hello world"


def test_pickle_format(env):
    assert data.load("corpora/mycorp/obj.pickle", format="pickle") == {"a": 1}


def test_grammar_cfg_each_scheme(env):
    for url in ("nltk:grammars/toy.cfg", "grammars/toy.cfg"):
        grammar = data.load(url)
        assert any(str(p.lhs()) == "S" for p in grammar.productions())


def test_zip_entry_access(env):
    ptr = data.find("corpora/zc.zip/zc/inside.txt", paths=[str(env.root)])
    assert ptr.open().read() == b"zipped-bytes"


def test_zip_second_pass_fallback(env):
    ptr = data.find("corpora/zc/inside.txt", paths=[str(env.root)])
    assert ptr.open().read() == b"zipped-bytes"


def test_empty_resource_name_stays_in_root(env):
    ptr = data.find("", paths=[str(env.root)])
    resolved = Path(str(ptr.path)).resolve()
    assert resolved == env.root.resolve() or resolved.is_relative_to(env.root.resolve())


def test_legitimate_dotted_name(env):
    assert data.load("corpora/mycorp/a.b.c.txt", format="raw") == b"dotted"


def test_safe_percent_encoded_dot_is_allowed(env):
    assert data.load("nltk:corpora/mycorp/data%2Etxt", format="raw") == b"hello world"


def test_long_nested_legitimate_path(env):
    nested = "corpora/mycorp/" + "/".join("abcdefgh") + "/deep.txt"
    assert data.load(nested, format="raw") == b"deep-ok"
    ptr = data.find(nested, paths=[str(env.root)])
    assert Path(str(ptr.path)).resolve().is_relative_to(env.root.resolve())

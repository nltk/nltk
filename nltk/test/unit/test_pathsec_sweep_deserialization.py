"""Whole-tree deserialization sweep (CWE-502 / pickle-RCE regression matrix).

This is a *sweep* test: it does not re-prove the internals of
:mod:`nltk.picklesec` (that is :mod:`test_pickle_allowlist_security`), it proves
that **every** place in the ``nltk`` tree that turns bytes back into Python
objects is either

  (a) routed through an allowlisting / restricted unpickler that refuses an
      ``os.system`` / ``builtins.eval`` / dotted-name / ``scipy.io.mmwrite`` /
      ``numpy.load`` gadget, or
  (b) plain ``json`` off a pathsec-guarded handle (parsing, not code execution),
      and

  (c) that no reachable ``numpy.load`` / ``np.load(allow_pickle=True)`` and no
      raw ``pickle.load`` / ``pickle.loads`` / ``pickle.Unpickler`` bypass those
      unpicklers on a caller/dataset-controlled path.

The audited pickle load sites and their routing:

    nltk/parse/transitionparser.py:609  TransitionParser.parse(modelFile)
        -> allowlisted_pickle_load(_MODEL_ALLOWED_MODULES/_GLOBALS)  [caller path]
    nltk/data.py:1144  load(<*.pickle>)  -> restricted_pickle_load
        -> RestrictedUnpickler (blocks ALL globals)                 [dataset path]
    nltk/app/wordnet_app.py:741  Reference.decode(<base64 from HTTP>)
        -> RestrictedUnpickler + type/shape check                   [untrusted web]
    nltk/tokenize/punkt.py:159  punkt_pickle_load(file)
        -> allowlisted_pickle_load(_PUNKT_ALLOWED_GLOBALS)          [legacy pickle]

Warn-only residuals (interactive GUI / developer demo, user-selected path, not an
untrusted dataset; documented, deliberately NOT allowlisted):

    nltk/app/chartparser_app.py:816,2273,2311  pickle_load(<GUI file dialog>)
    nltk/tbl/demo.py:263,339                    pickle_load(<dev demo cache>)

json / json.loads sites (not RCE; file open is pathsec-guarded where the path is
caller/dataset-controlled):

    nltk/help.py:49, nltk/data.py:1150, nltk/tag/perceptron.py:186,414,
    nltk/twitter/common.py:126,201, nltk/corpus/reader/twitter.py:134,
    nltk/sentiment/util.py:375
"""

import os
import pickle
import re
from io import BytesIO
from pathlib import Path

import pytest

from nltk.picklesec import RestrictedUnpickler, allowlisted_pickle_load

# ---------------------------------------------------------------------------
# Gadget payload builders
# ---------------------------------------------------------------------------


def _su(s: str) -> bytes:
    """A SHORT_BINUNICODE opcode for a short (<256 byte) string."""
    b = s.encode()
    return pickle.SHORT_BINUNICODE + bytes([len(b)]) + b


def _reduce_global_pickle(module: str, name: str, arg: str) -> bytes:
    """A protocol-4 pickle: ``REDUCE(<module>.<name>, (arg,))``.

    Hand-assembled so it does not depend on the gadget being importable at build
    time. When loaded through a guarded unpickler, ``find_class`` runs (and must
    raise) at the STACK_GLOBAL step, *before* the REDUCE would call anything.
    """
    return (
        pickle.PROTO
        + bytes([4])
        + _su(module)
        + _su(name)
        + pickle.STACK_GLOBAL
        + _su(arg)
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )


def _bare_global_pickle(module: str, name: str) -> bytes:
    """A protocol-4 pickle that just resolves ``<module>.<name>`` and returns it.

    No REDUCE: loading it exercises pure ``find_class`` resolution, so a refusal
    proves the global can never even be *named*, let alone called.
    """
    return (
        pickle.PROTO
        + bytes([4])
        + _su(module)
        + _su(name)
        + pickle.STACK_GLOBAL
        + pickle.STOP
    )


class _OsSystemReduce:
    """A ``__reduce__`` gadget: unpickling would run a shell command."""

    def __init__(self, cmd: str):
        self._cmd = cmd

    def __reduce__(self):
        return (os.system, (self._cmd,))


# Dangerous globals that must never be reconstructable from an untrusted pickle,
# spanning code-exec, subprocess, file-write/read, network/SSRF and nested
# unpickle sinks. Every one is on picklesec's denylist or simply unlisted.
_GADGETS = [
    ("os", "system"),  # classic command execution
    ("subprocess", "Popen"),  # subprocess
    ("builtins", "eval"),  # arbitrary eval
    ("builtins", "exec"),  # arbitrary exec
    ("builtins", "__import__"),  # dunder / import
    ("scipy.io", "mmwrite"),  # arbitrary file WRITE
    ("scipy.io", "loadmat"),  # arbitrary file read
    ("sklearn.datasets", "fetch_openml"),  # network / SSRF
    ("sklearn.datasets", "load_svmlight_file"),  # file read
    ("numpy", "load"),  # nested-unpickle sink
    ("numpy", "apply_along_axis"),  # invokes a supplied callable
    ("scipy", "LowLevelCallable"),  # low-level C callback
    ("pickle", "Unpickler"),  # unpickler-in-unpickler
]

# The real, in-production load configurations. Each entry loads bytes exactly the
# way the corresponding call site does.


def _load_transitionparser(data: bytes):
    from nltk.parse.transitionparser import (
        _MODEL_ALLOWED_GLOBALS,
        _MODEL_ALLOWED_MODULES,
    )

    return allowlisted_pickle_load(
        BytesIO(data),
        allowed_modules=_MODEL_ALLOWED_MODULES,
        allowed_globals=_MODEL_ALLOWED_GLOBALS,
    )


def _load_punkt(data: bytes):
    from nltk.tokenize.punkt import punkt_pickle_load

    return punkt_pickle_load(BytesIO(data))


def _load_restricted(data: bytes):
    # Exactly what nltk.data.load(<*.pickle>) uses for any non-redirected pickle.
    from nltk.data import restricted_pickle_load

    return restricted_pickle_load(data)


_LOAD_CONFIGS = [
    ("transitionparser", _load_transitionparser),
    ("punkt", _load_punkt),
    ("data.restricted", _load_restricted),
]


# ---------------------------------------------------------------------------
# (a) Every allowlisted / restricted load site refuses every gadget
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
@pytest.mark.parametrize("module,name", _GADGETS)
def test_every_load_site_refuses_gadget_bare_resolution(site, module, name):
    """The gadget cannot even be *resolved* at any real load site."""
    loader = dict(_LOAD_CONFIGS)[site]
    with pytest.raises(pickle.UnpicklingError):
        loader(_bare_global_pickle(module, name))


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
@pytest.mark.parametrize("module,name", _GADGETS)
def test_every_load_site_refuses_gadget_reduce(site, module, name):
    """A full REDUCE payload built on the gadget is refused, not executed."""
    loader = dict(_LOAD_CONFIGS)[site]
    with pytest.raises(pickle.UnpicklingError):
        loader(_reduce_global_pickle(module, name, "echo pathsec-sweep-rce"))


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
def test_every_load_site_refuses_os_system_reduce_no_exec(site, tmp_path):
    """A genuine ``__reduce__`` -> os.system gadget must refuse AND not run."""
    loader = dict(_LOAD_CONFIGS)[site]
    marker = tmp_path / f"pwned_{site.replace('.', '_')}"
    payload = pickle.dumps(_OsSystemReduce(f"touch {marker}"))
    with pytest.raises(pickle.UnpicklingError):
        loader(payload)
    assert not marker.exists(), f"{site}: os.system gadget executed (RCE not blocked)"


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
def test_every_load_site_refuses_dotted_name_traversal(site, tmp_path):
    """GHSA-4489: a dotted name (`sklearn.os.system`) must be refused."""
    loader = dict(_LOAD_CONFIGS)[site]
    marker = tmp_path / f"pwned_4489_{site.replace('.', '_')}"
    payload = _reduce_global_pickle("sklearn", "os.system", f"touch {marker}")
    with pytest.raises(pickle.UnpicklingError):
        loader(payload)
    assert not marker.exists()


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
def test_every_load_site_refuses_scipy_io_mmwrite(site):
    """The task's named file-WRITE sink is refused at every real load site."""
    loader = dict(_LOAD_CONFIGS)[site]
    with pytest.raises(pickle.UnpicklingError):
        loader(_reduce_global_pickle("scipy.io", "mmwrite", "/tmp/should-not-write"))


@pytest.mark.parametrize("site", [c[0] for c in _LOAD_CONFIGS])
def test_every_load_site_refuses_extension_opcode(site, tmp_path):
    """The EXT1/EXT2/EXT4 extension-registry opcodes resolve a global through
    copyreg (not find_class); on a warm copyreg._extension_cache the C unpickler
    returns the cached object without find_class, bypassing the allowlist. Every
    real load site must refuse EXT up front, even with the cache poisoned."""
    import copyreg

    loader = dict(_LOAD_CONFIGS)[site]
    code = 199
    marker = tmp_path / f"pwned_ext_{site.replace('.', '_')}"
    payload = (
        pickle.PROTO
        + bytes([2])
        + pickle.EXT1
        + bytes([code])
        + _su(f"touch {marker}")
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )
    copyreg._extension_cache[code] = os.system
    try:
        with pytest.raises(pickle.UnpicklingError):
            loader(payload)
        assert not marker.exists(), f"{site}: EXT warm-cache gadget executed"
    finally:
        copyreg._extension_cache.pop(code, None)


# ---------------------------------------------------------------------------
# Legitimate loads must still succeed (allowlists are not "block everything")
# ---------------------------------------------------------------------------


def test_transitionparser_allowlist_loads_real_svc():
    """The exact TransitionParser allowlist still round-trips a fitted SVC."""
    np = pytest.importorskip("numpy")
    sparse = pytest.importorskip("scipy.sparse")
    svm = pytest.importorskip("sklearn.svm")

    X = np.array(
        [[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [0.5, 0.5], [0.2, 0.8]]
    )
    y = [0, 1, 0, 1, 0, 1]
    for data in (X, sparse.csr_matrix(X)):
        model = svm.SVC(kernel="poly", degree=2, gamma=0.2, C=0.5).fit(data, y)
        restored = _load_transitionparser(pickle.dumps(model))
        assert np.array_equal(model.predict(X[:3]), restored.predict(X[:3]))


def test_punkt_allowlist_round_trips_real_tokenizer():
    """A genuine Punkt tokenizer round-trips through punkt_pickle_load."""
    from nltk.tokenize.punkt import PunktSentenceTokenizer

    text = "Mr. Smith went to Washington. He met Dr. Jones at 3 p.m. It was great!"
    tok = PunktSentenceTokenizer()
    tok.train(text)
    restored = _load_punkt(pickle.dumps(tok, protocol=4))
    assert restored.tokenize(text) == tok.tokenize(text)


def test_restricted_load_allows_globals_free_payload_but_no_globals():
    """nltk.data's pickle path loads plain data yet refuses any global."""
    # A globals-free structure (no GLOBAL opcode) loads fine.
    payload = pickle.dumps({"a": [1, 2, 3], "b": ("x", "y")}, protocol=4)
    assert _load_restricted(payload) == {"a": [1, 2, 3], "b": ("x", "y")}
    # Any global at all is refused (RestrictedUnpickler blocks the lot).
    with pytest.raises(pickle.UnpicklingError):
        _load_restricted(_bare_global_pickle("collections", "OrderedDict"))


# ---------------------------------------------------------------------------
# wordnet_app.Reference.decode: untrusted base64 -> RestrictedUnpickler + shape
# ---------------------------------------------------------------------------


def _reference_cls():
    try:
        from nltk.app.wordnet_app import Reference
    except Exception as exc:  # pragma: no cover - optional import surface
        pytest.skip(f"nltk.app.wordnet_app unavailable: {exc}")
    return Reference


def test_wordnet_reference_round_trips_genuine_payload():
    Reference = _reference_cls()
    ref = Reference("dog", {"key-1": {"hypernym"}, "key-2": {"hyponym"}})
    restored = Reference.decode(ref.encode())
    assert restored.word == "dog"
    assert restored.synset_relations == {"key-1": {"hypernym"}, "key-2": {"hyponym"}}


def test_wordnet_reference_decode_refuses_malicious_pickle_no_exec(tmp_path):
    import base64

    Reference = _reference_cls()
    marker = tmp_path / "pwned_wordnet"
    raw = pickle.dumps(_OsSystemReduce(f"touch {marker}"))
    encoded = base64.urlsafe_b64encode(raw).decode()
    # decode() normalises the UnpicklingError to ValueError; the gadget must not run.
    with pytest.raises(ValueError):
        Reference.decode(encoded)
    assert not marker.exists(), "wordnet_app Reference.decode executed a pickle gadget"


@pytest.mark.parametrize(
    "payload",
    [
        (12345, {}),  # word is an int, not a str
        ("dog", ["not", "a", "dict"]),  # synset_relations is a list, not a dict
        ("dog", {123: {"x"}}),  # a non-str relation key
        ("dog", {"k": frozenset({"x"})}),  # a frozenset value (not a mutable set)
        ("dog", {"k": ["x"]}),  # a list value, not a set
        [1, 2, 3],  # not even a 2-tuple to unpack
    ],
)
def test_wordnet_reference_decode_rejects_non_reference_shape(payload):
    """GHSA-7pvm: RestrictedUnpickler blocks class/function reconstruction but not
    the *type/shape* of plain data, so a non-string / wrong-shaped value smuggled
    through the pickle-based wordnet URL must be rejected with a plain ValueError
    (never an unhandled crash) before it reaches Reference internals."""
    import base64

    Reference = _reference_cls()
    encoded = base64.urlsafe_b64encode(pickle.dumps(payload)).decode()
    with pytest.raises(ValueError, match="Malformed wordnet_app reference"):
        Reference.decode(encoded)


def test_restricted_unpickler_directly_blocks_every_gadget():
    """The shared RestrictedUnpickler (wordnet_app + data.py) blocks find_class."""
    for module, name in _GADGETS + [
        ("collections", "OrderedDict"),
        ("builtins", "int"),
    ]:
        u = RestrictedUnpickler(BytesIO(b""))
        with pytest.raises(pickle.UnpicklingError):
            u.find_class(module, name)


# ---------------------------------------------------------------------------
# (c) Source-tree invariants: no np.load pickle path, no raw pickle.load bypass
# ---------------------------------------------------------------------------

_NLTK_ROOT = Path(__file__).resolve().parents[2]  # .../nltk


def _iter_source_files():
    for path in _NLTK_ROOT.rglob("*.py"):
        parts = set(path.parts)
        if "test" in parts or "tests" in parts:
            continue
        yield path


def test_no_numpy_load_or_allow_pickle_anywhere():
    """No reachable ``numpy.load`` / ``np.load`` and no ``allow_pickle=True``.

    A ``numpy.load`` on a caller path (or ``allow_pickle=True`` on an object
    array) is a pickle-RCE sink. There are none in the tree; picklesec.py only
    *names* them in its denylist, so it is exempted. This guards against a future
    reintroduction that would bypass the allowlist entirely.
    """
    pat = re.compile(r"\b(?:np|numpy)\.load\s*\(|allow_pickle\s*=\s*True")
    offenders = []
    for path in _iter_source_files():
        if path.name == "picklesec.py":
            continue  # denylist definitions, not calls
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            if pat.search(line):
                offenders.append(f"{path.relative_to(_NLTK_ROOT)}:{i}: {line.strip()}")
    assert not offenders, "numpy.load / allow_pickle sink(s) found:\n" + "\n".join(
        offenders
    )


def test_no_raw_pickle_load_bypasses_the_unpicklers():
    """No ``pickle.load`` / ``pickle.loads`` / ``pickle.Unpickler`` outside
    picklesec.py; every load must go through a guarded wrapper."""
    pat = re.compile(r"\bpickle\.(?:load|loads|Unpickler)\s*\(")
    offenders = []
    for path in _iter_source_files():
        if path.name == "picklesec.py":
            continue  # defines RestrictedUnpickler/AllowlistUnpickler/pickle_load
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            # skip comments/docstring mentions like "similar to pickle.load(file)"
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pat.search(line):
                offenders.append(f"{path.relative_to(_NLTK_ROOT)}:{i}: {line.strip()}")
    assert not offenders, "raw pickle.load bypass(es) found:\n" + "\n".join(offenders)


def test_transitionparser_allowlist_stays_exact_no_broad_namespace():
    """Teeth: if a broad numpy/scipy/sklearn namespace ever comes back, the
    I/O / network gadgets above become reachable again."""
    from nltk.parse.transitionparser import _MODEL_ALLOWED_MODULES

    assert tuple(_MODEL_ALLOWED_MODULES) == ()

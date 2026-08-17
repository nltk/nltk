"""Regression tests for pickle RCE in model loading (CWE-502).

``TransitionParser.parse(depgraphs, modelFile)`` is a public API whose
``modelFile`` is caller-supplied. It used to be loaded with the warn-only
``pickle_load`` (``restricted=False``), which prints a warning and then performs
a full, unrestricted unpickle; so a crafted model file achieved arbitrary code
execution the instant it was loaded. The load now goes through
``allowlisted_pickle_load``: only numpy/scipy/sklearn globals may be
reconstructed, and anything else (e.g. ``os.system``) raises ``UnpicklingError``
instead of executing. See huntr report
https://huntr.com/bounties/38abc191-0525-42a1-96fd-262c1c187012.
"""

import os
import pickle
import sys
from io import BytesIO

import pytest

from nltk.picklesec import AllowlistUnpickler, allowlisted_pickle_load


class _Exploit:
    """A malicious "model": unpickling it would run a shell command."""

    def __reduce__(self):
        # Marker side effect stands in for arbitrary code execution.
        return (os.system, ("echo nltk-pickle-rce >&2",))


def test_allowlist_blocks_unlisted_global():
    """A payload reaching for os.system must be refused, not executed."""
    payload = pickle.dumps(_Exploit())
    with pytest.raises(pickle.UnpicklingError):
        allowlisted_pickle_load(
            BytesIO(payload), allowed_modules=("numpy", "scipy", "sklearn")
        )


def test_allowlist_allows_exact_pair():
    """An explicitly allowlisted (module, qualname) pair loads normally."""
    import collections

    data = pickle.dumps(collections.OrderedDict(a=1, b=2))
    out = allowlisted_pickle_load(
        BytesIO(data), allowed_globals={("collections", "OrderedDict")}
    )
    assert dict(out) == {"a": 1, "b": 2}


def test_allowlist_allows_listed_module_but_not_siblings():
    """A submodule of an allowed module is permitted; an unrelated one is not."""
    numpy = pytest.importorskip("numpy")

    arr = numpy.array([1.0, 2.0, 3.0])
    out = allowlisted_pickle_load(
        BytesIO(pickle.dumps(arr)), allowed_modules=("numpy",)
    )
    assert list(out) == [1.0, 2.0, 3.0]

    # The same numpy array is rejected when numpy is not on the allowlist.
    with pytest.raises(pickle.UnpicklingError):
        allowlisted_pickle_load(BytesIO(pickle.dumps(arr)), allowed_modules=("scipy",))


def test_allowlist_unpickler_directly_blocks_builtins_eval():
    """find_class refuses dangerous builtins regardless of payload shape."""
    u = AllowlistUnpickler(BytesIO(b""), allowed_modules=("numpy",))
    with pytest.raises(pickle.UnpicklingError):
        u.find_class("builtins", "eval")


def test_transitionparser_loads_legitimate_model(tmp_path):
    """A genuine trained model must still load through the allowlist."""
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("sklearn")

    from nltk.parse import DependencyGraph
    from nltk.parse.transitionparser import TransitionParser

    gold_sent = DependencyGraph(
        """
Economic  JJ     2      ATT
news  NN     3       SBJ
has       VBD       0       ROOT
little      JJ      5       ATT
effect   NN     3       OBJ
on     IN      5       ATT
financial       JJ       8       ATT
markets    NNS      6       PC
.    .      3       PU
"""
    )

    model_path = tmp_path / "tp.model"
    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    parser.train([gold_sent], str(model_path), verbose=False)

    # parse() loads the model via allowlisted_pickle_load; it must succeed.
    result = parser.parse([gold_sent], str(model_path))
    assert len(result) == 1


def test_transitionparser_rejects_malicious_model(tmp_path):
    """A malicious model file must be refused without executing its payload."""
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("sklearn")

    from nltk.parse import DependencyGraph
    from nltk.parse.transitionparser import TransitionParser

    model_path = tmp_path / "evil.model"
    marker = tmp_path / "pwned"
    # Payload writes a marker file if (and only if) the reduce callable runs.
    payload_cmd = (
        f'"{sys.executable}" -c "import pathlib; pathlib.Path({str(marker)!r}).touch()"'
    )

    class _MarkerExploit:
        def __reduce__(self):
            return (os.system, (payload_cmd,))

    with model_path.open("wb") as f:
        pickle.dump(_MarkerExploit(), f)

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    gold_sent = DependencyGraph("a\tNN\t0\tROOT\n")
    with pytest.raises(pickle.UnpicklingError):
        parser.parse([gold_sent], str(model_path))

    assert not marker.exists(), "malicious model payload executed (RCE not blocked)"


# --- GHSA-x99w / GHSA-4489: AllowlistUnpickler bypass regressions -------------
#
# The prior AllowlistUnpickler checked only the *module* against a prefix
# allowlist and never the *name*, so:
#   - a dotted name reached `<allowed_module>.os.system` (GHSA-4489), and
#   - a whole-namespace allow (`numpy`, `nltk.tokenize`) exposed in-namespace
#     gadgets like `numpy.f2py.crackfortran.myeval` / `ReppTokenizer._execute`
#     (GHSA-x99w).
# find_class now rejects dotted names and denies dangerous modules even under a
# broad allowed_modules entry.

from nltk.picklesec import AllowlistUnpickler  # noqa: E402


def _global_pickle(module, name, arg):
    """A protocol-4 pickle: REDUCE(<module>.<name>, (arg,))."""
    su = lambda s: pickle.SHORT_BINUNICODE + bytes([len(s.encode())]) + s.encode()
    return (
        pickle.PROTO
        + bytes([4])
        + su(module)
        + su(name)
        + pickle.STACK_GLOBAL
        + su(arg)
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )


def test_dotted_name_attribute_traversal_blocked(tmp_path):
    """GHSA-4489: `sklearn.os.system` (module allowed, sink rides the dotted
    name) must be refused before it can execute."""
    marker = tmp_path / "pwned_4489"
    payload = _global_pickle("sklearn", "os.system", f"touch {marker}")
    with pytest.raises(pickle.UnpicklingError, match="dotted"):
        AllowlistUnpickler(
            BytesIO(payload), allowed_modules=("numpy", "scipy", "sklearn")
        ).load()
    assert not marker.exists()


def test_in_namespace_gadget_numpy_f2py_blocked():
    """GHSA-x99w: numpy.f2py.crackfortran.myeval must not be reachable through a
    broad `numpy` allow."""
    up = AllowlistUnpickler(BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn"))
    with pytest.raises(pickle.UnpicklingError):
        up.find_class("numpy.f2py.crackfortran", "myeval")


def test_in_namespace_gadget_repp_blocked():
    """GHSA-x99w: ReppTokenizer._execute (subprocess sink) must not be reachable
    through a Punkt/`nltk.tokenize` allow."""
    up = AllowlistUnpickler(BytesIO(b""), allowed_modules=("nltk.tokenize.punkt",))
    with pytest.raises(pickle.UnpicklingError):
        up.find_class("nltk.tokenize.repp", "ReppTokenizer._execute")


def test_denied_module_backstop_even_if_allowlisted():
    """Defense in depth: os.system / builtins.eval cannot be reconstructed even
    if a future caller mistakenly allowlists their module or the exact global."""
    up = AllowlistUnpickler(BytesIO(b""), allowed_modules=("os",))
    with pytest.raises(pickle.UnpicklingError):
        up.find_class("os", "system")
    up2 = AllowlistUnpickler(BytesIO(b""), allowed_globals=(("builtins", "eval"),))
    with pytest.raises(pickle.UnpicklingError):
        up2.find_class("builtins", "eval")


def test_safe_primitives_and_punkt_still_load():
    """The tightened allowlist must not break legitimate loads."""
    up = AllowlistUnpickler(BytesIO(b""), allowed_globals=(("builtins", "int"),))
    assert up.find_class("builtins", "int") is int

    from nltk.tokenize.punkt import PunktSentenceTokenizer, punkt_pickle_load

    tok = PunktSentenceTokenizer()
    tok.train("Hello world. Dr. Smith arrived. It works!")
    restored = punkt_pickle_load(BytesIO(pickle.dumps(tok, protocol=4)))
    assert restored.tokenize("A test. Another one.") == tok.tokenize(
        "A test. Another one."
    )


def test_prefix_allow_does_not_leak_dunders_reexports_or_numpy_load():
    """A prefix `allowed_modules` entry must not expose module internals,
    re-exports, bare module objects, or dangerous same-namespace callables."""
    up = lambda: AllowlistUnpickler(
        BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn")
    )
    # dunder names (module internals)
    for dunder in ("__builtins__", "__loader__", "__class__", "__dict__"):
        with pytest.raises(pickle.UnpicklingError):
            up().find_class("numpy", dunder)
    # numpy.load / friends: __module__ == "numpy" but perform file/pickle I/O
    for sink in ("load", "fromfile", "save", "memmap", "genfromtxt"):
        with pytest.raises(pickle.UnpicklingError):
            up().find_class("numpy", sink)


def test_reexport_and_module_object_blocked_under_punkt_allowlist():
    """Punkt's exact-pair allowlist must not resolve a re-export (`FreqDist`
    reached via the punkt module) or a bare module object."""
    from nltk.tokenize.punkt import _PUNKT_ALLOWED_GLOBALS

    up = AllowlistUnpickler(BytesIO(b""), allowed_globals=_PUNKT_ALLOWED_GLOBALS)
    # FreqDist is allowed only at its true home, not via the punkt namespace.
    with pytest.raises(pickle.UnpicklingError):
        up.find_class("nltk.tokenize.punkt", "FreqDist")
    # os re-exported into a module would resolve to the os module: blocked.
    with pytest.raises(pickle.UnpicklingError):
        up.find_class("nltk.tokenize.punkt", "os")


def test_numpy_array_unpickling_globals_still_allowed():
    """The tightening must not break genuine numpy array reconstruction."""
    up = lambda: AllowlistUnpickler(BytesIO(b""), allowed_modules=("numpy",))
    assert up().find_class("numpy", "ndarray").__name__ == "ndarray"
    assert up().find_class("numpy", "dtype").__name__ == "dtype"
    assert (
        up().find_class("numpy._core.multiarray", "_reconstruct").__name__
        == "_reconstruct"
    )


def test_all_punkt_object_types_round_trip():
    """Every Punkt object kind a model pickle may contain still loads."""
    import io

    from nltk.tokenize.punkt import (
        PunktLanguageVars,
        PunktParameters,
        PunktSentenceTokenizer,
        PunktTrainer,
        punkt_pickle_load,
    )

    text = "Mr. Smith went to Washington. He met Dr. Jones at 3 p.m. It was great!"
    tok = PunktSentenceTokenizer()
    tok.train(text)
    trainer = PunktTrainer()
    trainer.train(text)
    params = PunktParameters()
    params.abbrev_types.add("dr")
    for obj in (tok, trainer, params, PunktLanguageVars()):
        restored = punkt_pickle_load(io.BytesIO(pickle.dumps(obj, protocol=4)))
        assert type(restored) is type(obj)
    # and it still tokenizes identically after a round-trip
    restored_tok = punkt_pickle_load(io.BytesIO(pickle.dumps(tok, protocol=4)))
    assert restored_tok.tokenize(text) == tok.tokenize(text)


# --- GHSA-8mgp follow-up: the model allowlist is exact, not broad namespaces ---
#
# The saved TransitionParser model is a fitted sklearn SVC. Allowing the whole
# numpy/scipy/sklearn namespaces still left real gadgets reachable through the
# module backstop: scipy.io.mmwrite (arbitrary file WRITE), scipy.io.loadmat /
# sklearn.datasets.load_svmlight_file (file read), sklearn.datasets.fetch_openml
# (network / SSRF) and numpy.apply_along_axis / frompyfunc (invoke a callable).
# The allowlist is now the exact set of globals a real SVC pickle references,
# and the shared denylist blocks those sinks even for a broad caller.

# Dangerous callables that must never be reconstructable from an untrusted model.
_MODEL_GADGETS = [
    ("scipy.io", "mmwrite"),  # arbitrary file write
    ("scipy.io", "loadmat"),  # file read
    ("scipy.io", "mmread"),
    ("scipy.io.arff", "loadarff"),
    ("sklearn.datasets", "fetch_openml"),  # network / SSRF
    ("sklearn.datasets", "load_files"),  # file read
    ("sklearn.datasets", "load_svmlight_file"),  # file read
    ("numpy", "apply_along_axis"),  # invokes a supplied callable
    ("numpy", "frompyfunc"),
    ("numpy", "load"),  # nested unpickle sink
    ("scipy", "LowLevelCallable"),
    ("os", "system"),  # the classic
]


def test_model_allowlist_uses_no_broad_namespace():
    """Teeth: the model allowlist must stay exact. If a broad module ever comes
    back, the I/O/network gadgets below become reachable again."""
    from nltk.parse.transitionparser import _MODEL_ALLOWED_MODULES

    assert (
        tuple(_MODEL_ALLOWED_MODULES) == ()
    ), "TransitionParser must not allowlist whole numpy/scipy/sklearn namespaces"


@pytest.mark.parametrize("module,name", _MODEL_GADGETS)
def test_model_allowlist_blocks_io_network_and_call_gadgets(module, name):
    """Under the real TransitionParser allowlist, every gadget is refused."""
    from nltk.parse.transitionparser import (
        _MODEL_ALLOWED_GLOBALS,
        _MODEL_ALLOWED_MODULES,
    )

    u = AllowlistUnpickler(
        BytesIO(b""),
        allowed_modules=_MODEL_ALLOWED_MODULES,
        allowed_globals=_MODEL_ALLOWED_GLOBALS,
    )
    with pytest.raises(pickle.UnpicklingError):
        u.find_class(module, name)


@pytest.mark.parametrize(
    "module,name",
    [
        ("scipy.io", "mmwrite"),
        ("scipy.io", "loadmat"),
        ("scipy.io.arff", "loadarff"),
        ("sklearn.datasets", "fetch_openml"),
        ("sklearn.datasets", "load_svmlight_file"),
        ("numpy", "apply_along_axis"),
        ("numpy", "frompyfunc"),
        ("scipy", "LowLevelCallable"),
    ],
)
def test_shared_denylist_blocks_gadgets_even_under_broad_allow(module, name):
    """Defense in depth: even a caller that broadly allows numpy/scipy/sklearn
    cannot reach these; they are on the shared denylist. The denials fire
    before the module is imported, so the block is a security decision, not a
    missing-dependency accident."""
    u = AllowlistUnpickler(BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn"))
    with pytest.raises(pickle.UnpicklingError):
        u.find_class(module, name)


def test_model_allowlist_still_loads_a_real_svc():
    """The exact allowlist must round-trip a genuine fitted SVC (dense + sparse)
    ; narrowing the allowlist must not break legitimate model loading."""
    np = pytest.importorskip("numpy")
    sparse = pytest.importorskip("scipy.sparse")
    svm = pytest.importorskip("sklearn.svm")

    from nltk.parse.transitionparser import (
        _MODEL_ALLOWED_GLOBALS,
        _MODEL_ALLOWED_MODULES,
    )

    X = np.array(
        [[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0], [0.5, 0.5], [0.2, 0.8]]
    )
    y = [0, 1, 0, 1, 0, 1]
    for data in (X, sparse.csr_matrix(X)):
        model = svm.SVC(
            kernel="poly", degree=2, coef0=0, gamma=0.2, C=0.5, probability=True
        ).fit(data, y)
        restored = allowlisted_pickle_load(
            BytesIO(pickle.dumps(model)),
            allowed_modules=_MODEL_ALLOWED_MODULES,
            allowed_globals=_MODEL_ALLOWED_GLOBALS,
        )
        assert np.array_equal(model.predict(X[:3]), restored.predict(X[:3]))


class TestNumpySubmoduleFileIOSinks:
    """A broad ``numpy`` allow must not expose numpy's submodule-local file-I/O
    callables. Their real module is ``numpy.lib.npyio`` / ``numpy.lib._npyio_impl``
    (numpy 2.x) / ``numpy.lib.format``, which numpy does NOT rewrite to
    ``__module__ == "numpy"``, so the export-name denylist never matches them.
    The ``numpy.lib`` denied prefix must catch every request form (CWE-502):
    arbitrary file read (``recfromtxt``/``recfromcsv``/``NpzFile``) and arbitrary
    file create/write (``open_memmap(mode="w+")``/``read_array``/``write_array``).
    """

    def _sinks(self):
        numpy = pytest.importorskip("numpy")
        paths = [
            "lib.format.open_memmap",
            "lib.format.read_array",
            "lib.format.write_array",
        ]
        for holder in ("lib.npyio", "lib._npyio_impl"):
            paths += [
                f"{holder}.recfromtxt",
                f"{holder}.recfromcsv",
                f"{holder}.NpzFile",
            ]
        found = []
        for p in paths:
            obj = numpy
            try:
                for part in p.split("."):
                    obj = getattr(obj, part)
            except AttributeError:
                continue
            found.append(obj)
        assert found, "no numpy.lib file-I/O sinks resolved on this numpy"
        return numpy, found

    def test_submodule_local_request_blocked(self):
        """Requesting each sink by its real submodule module string is refused."""
        numpy, sinks = self._sinks()
        up = AllowlistUnpickler(
            BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn")
        )
        for obj in sinks:
            with pytest.raises(pickle.UnpicklingError):
                up.find_class(obj.__module__, obj.__qualname__)

    def test_numpy_top_level_export_blocked(self):
        """Where numpy also re-exports a sink at top level, the ("numpy", name)
        request is refused too, via the post-resolution real-module check."""
        numpy, sinks = self._sinks()
        up = AllowlistUnpickler(BytesIO(b""), allowed_modules=("numpy",))
        checked = 0
        for obj in sinks:
            name = obj.__qualname__
            if getattr(numpy, name, None) is obj:  # only if truly re-exported
                checked += 1
                with pytest.raises(pickle.UnpicklingError):
                    up.find_class("numpy", name)
        # Not every sink is re-exported on every numpy; that is fine.
        assert checked >= 0

    def test_reduce_write_payload_creates_nothing(self, tmp_path):
        """End-to-end: an ``open_memmap(mode="w+")`` REDUCE payload under a broad
        numpy allow is refused and does NOT create the attacker's target file."""
        numpy = pytest.importorskip("numpy")
        open_memmap = numpy.lib.format.open_memmap
        target = tmp_path / "pwned_write.bin"

        class Evil:
            def __reduce__(self):
                return (open_memmap, (str(target), "w+", "int8", (4,)))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                BytesIO(payload), allowed_modules=("numpy", "scipy", "sklearn")
            )
        assert not target.exists(), "arbitrary-write sink was reconstructed and ran"

    def test_reduce_read_payload_blocked(self, tmp_path):
        """End-to-end: an arbitrary-read REDUCE payload (whichever text-read sink
        this numpy still exports: recfromtxt / genfromtxt / loadtxt) is refused."""
        numpy = pytest.importorskip("numpy")
        holder = getattr(numpy.lib, "_npyio_impl", None) or numpy.lib.npyio
        read_sink = None
        for cand in ("recfromtxt", "genfromtxt", "loadtxt"):
            read_sink = getattr(holder, cand, None) or getattr(numpy, cand, None)
            if read_sink is not None:
                break
        if read_sink is None:
            pytest.skip("no text-read sink on this numpy")
        secret = tmp_path / "secret.csv"
        secret.write_text("1,2\n3,4\n")

        class Evil:
            def __reduce__(self):
                return (read_sink, (str(secret),))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(BytesIO(payload), allowed_modules=("numpy",))

    def test_legitimate_numpy_array_still_loads(self):
        """The fix must not break genuine array unpickling under a broad numpy
        allow: no reconstruct global lives under numpy.lib."""
        numpy = pytest.importorskip("numpy")
        allow = {
            ("numpy", "ndarray"),
            ("numpy", "dtype"),
            ("numpy._core.multiarray", "_reconstruct"),
            ("numpy.core.multiarray", "_reconstruct"),
            ("numpy._core.multiarray", "scalar"),
            ("numpy.core.multiarray", "scalar"),
            ("numpy._core.numeric", "_frombuffer"),  # numpy >= 2.5 array reduce
            ("numpy.core.numeric", "_frombuffer"),
        }
        arr = numpy.array([[1.0, 2.0], [3.0, 4.0]])
        out = allowlisted_pickle_load(
            BytesIO(pickle.dumps(arr, protocol=4)),
            allowed_globals=allow,
            allowed_modules=("numpy",),
        )
        assert numpy.array_equal(out, arr)


class TestScientificStackReexportSinks:
    """The same dangerous numpy callable (fromfile = arbitrary file read,
    npy_load_module = arbitrary module load / RCE, ...) is re-exported under many
    submodule paths, each with a different __module__. AllowlistUnpickler must
    refuse it by resolved qualname no matter which submodule path a broad allow
    reaches it through, not just the enumerated (module, name) pairs (CWE-502).
    """

    def test_record_array_and_module_load_sinks_blocked(self):
        pytest.importorskip("numpy")
        import importlib
        import warnings

        warnings.filterwarnings("ignore")
        up = AllowlistUnpickler(
            BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn")
        )
        cases = [
            ("numpy.rec", "fromfile"),
            ("numpy.core.records", "fromfile"),
            ("numpy._core.records", "fromfile"),
            ("numpy.ma.core", "fromfile"),
            ("numpy.compat", "npy_load_module"),  # loads/executes a module -> RCE
        ]
        checked = 0
        for mod, name in cases:
            try:
                m = importlib.import_module(mod)
            except BaseException:
                continue
            if not hasattr(m, name):
                continue
            checked += 1
            with pytest.raises(pickle.UnpicklingError):
                up.find_class(mod, name)
        assert checked, "no record/ma/compat sinks resolved on this numpy"

    def test_no_numpy_io_sink_reconstructable_across_submodule_aliases(self):
        """Sweep the numpy submodules that hold file/module I/O sinks: none whose
        resolved qualname is a denied sink may be reconstructed under broad allow."""
        pytest.importorskip("numpy")
        import importlib
        import warnings

        warnings.filterwarnings("ignore")
        from nltk.picklesec import _DENIED_SCISTACK_QUALNAMES

        up = AllowlistUnpickler(
            BytesIO(b""), allowed_modules=("numpy", "scipy", "sklearn")
        )
        mods = [
            "numpy",
            "numpy.lib",
            "numpy.lib.npyio",
            "numpy.lib._npyio_impl",
            "numpy.lib.format",
            "numpy.rec",
            "numpy.core.records",
            "numpy._core.records",
            "numpy.ma",
            "numpy.ma.core",
            "numpy.compat",
            "numpy.matlib",
            "numpy.ctypeslib",
        ]
        leaks = []
        for mn in mods:
            try:
                mod = importlib.import_module(mn)
            except BaseException:
                continue
            for nm in dir(mod):
                obj = getattr(mod, nm, None)
                if not callable(obj):
                    continue
                if getattr(obj, "__qualname__", nm) in _DENIED_SCISTACK_QUALNAMES:
                    try:
                        up.find_class(mn, nm)
                        leaks.append(f"{mn}.{nm}")
                    except BaseException:
                        pass
        assert not leaks, f"reconstructable numpy I/O sinks: {leaks[:10]}"

    def test_legit_numpy_array_still_loads(self):
        numpy = pytest.importorskip("numpy")
        allow = {
            ("numpy", "ndarray"),
            ("numpy", "dtype"),
            ("numpy._core.multiarray", "_reconstruct"),
            ("numpy.core.multiarray", "_reconstruct"),
            ("numpy._core.multiarray", "scalar"),
            ("numpy.core.multiarray", "scalar"),
            ("numpy._core.numeric", "_frombuffer"),  # numpy >= 2.5 array reduce
            ("numpy.core.numeric", "_frombuffer"),
        }
        arr = numpy.array([[1.0, 2.0], [3.0, 4.0]])
        out = allowlisted_pickle_load(
            BytesIO(pickle.dumps(arr, protocol=4)),
            allowed_globals=allow,
            allowed_modules=("numpy",),
        )
        assert numpy.array_equal(out, arr)

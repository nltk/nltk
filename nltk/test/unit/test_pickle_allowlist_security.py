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
        # When no sink is re-exported at top level, skip rather than pass vacuously.
        if checked == 0:
            pytest.skip(
                "no numpy.lib file-I/O sink is re-exported at numpy top level "
                "on this build"
            )

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


class TestBroadAllowGadgetContainment:
    """Threat model: a downstream over-allows the whole scientific stack
    (``allowed_modules=("numpy","scipy","sklearn","pandas")``). Even then, no
    file/module I/O sink or classic RCE gadget may be reconstructed through it.
    Where a sink takes a path we build a real REDUCE payload and assert no file
    is created; the rest assert ``find_class`` refuses the global.
    """

    BROAD = {"allowed_modules": ("numpy", "scipy", "sklearn", "pandas")}

    def _blocked(self, module, name):
        up = AllowlistUnpickler(BytesIO(b""), **self.BROAD)
        try:
            up.find_class(module, name)
            return False
        except pickle.UnpicklingError:
            return True
        except Exception:
            return True  # never resolved -> not reachable

    @pytest.mark.parametrize(
        "module,name",
        [
            ("os", "system"),
            ("posix", "system"),
            ("nt", "system"),
            ("subprocess", "Popen"),
            ("subprocess", "run"),
            ("subprocess", "call"),
            ("builtins", "eval"),
            ("builtins", "exec"),
            ("builtins", "__import__"),
            ("builtins", "compile"),
            ("builtins", "getattr"),
            ("builtins", "open"),
            ("io", "open"),
            ("codecs", "open"),
            ("os", "popen"),
            ("pty", "spawn"),
            ("webbrowser", "open"),
            ("shutil", "rmtree"),
            ("importlib", "import_module"),
            ("functools", "partial"),
            ("operator", "methodcaller"),
            ("operator", "attrgetter"),
            ("copyreg", "_reconstructor"),
            ("copyreg", "__newobj__"),
            ("pickle", "loads"),
            ("_pickle", "loads"),
        ],
    )
    def test_classic_rce_gadget_refused(self, module, name):
        """A broad *scientific-stack* allow does not reach os/subprocess/builtins
        (or any other) code-exec gadget: their module is not on the allowlist."""
        assert self._blocked(module, name), f"{module}.{name} is reconstructable"

    @pytest.mark.parametrize(
        "module,name",
        [
            ("numpy", "f2py.crackfortran.myeval"),  # dotted -> getattr-chain
            ("numpy", "os.system"),
            ("sklearn", "os.system"),
            ("numpy", "__loader__"),  # dunder
            ("numpy", "__builtins__"),
            ("numpy", "__class__"),
            ("numpy", "__dict__"),
        ],
    )
    def test_attribute_traversal_refused(self, module, name):
        assert self._blocked(module, name), f"{module}.{name} is reconstructable"

    @pytest.mark.parametrize(
        "module,name", [("numpy", "linalg"), ("numpy", "core"), ("scipy", "sparse")]
    )
    def test_bare_module_object_refused(self, module, name):
        """A bare submodule object is not a reconstructable class/function."""
        assert self._blocked(module, name), f"{module}.{name} resolved to a module"

    def test_scipy_sklearn_pandas_sinks_refused(self):
        import importlib

        checked = 0
        for mod, name in [
            ("scipy.io", "loadmat"),
            ("scipy.io", "savemat"),
            ("scipy.io", "mmread"),
            ("scipy.io", "mmwrite"),
            ("scipy.io", "readsav"),
            # scipy.datasets: network download + on-disk cache write.
            ("scipy.datasets", "download_all"),
            ("scipy.datasets", "face"),
            ("scipy.datasets", "ascent"),
            ("scipy.datasets", "electrocardiogram"),
            ("sklearn.datasets", "load_svmlight_file"),
            ("sklearn.datasets", "dump_svmlight_file"),
            ("sklearn.datasets", "fetch_openml"),
            # Every pandas.io reader is an arbitrary file/URL/DB read sink; a
            # top-level ``pandas.read_*`` request must be denied under a broad
            # ``pandas`` allow via the resolved pandas.io __module__.
            ("pandas", "read_pickle"),
            ("pandas", "read_csv"),
            ("pandas", "read_table"),
            ("pandas", "read_fwf"),
            ("pandas", "read_json"),
            ("pandas", "read_html"),
            ("pandas", "read_xml"),
            ("pandas", "read_excel"),
            ("pandas", "read_hdf"),
            ("pandas", "read_parquet"),
            ("pandas", "read_orc"),
            ("pandas", "read_feather"),
            ("pandas", "read_stata"),
            ("pandas", "read_sas"),
            ("pandas", "read_spss"),
            ("pandas", "read_sql"),
            ("pandas", "read_sql_query"),
            ("pandas", "read_sql_table"),
            ("pandas", "read_gbq"),
            ("pandas", "read_clipboard"),
            ("pandas", "HDFStore"),
            ("pandas", "ExcelFile"),
        ]:
            try:
                m = importlib.import_module(mod)
            except BaseException:
                continue
            if not hasattr(m, name):
                continue
            checked += 1
            assert self._blocked(mod, name), f"{mod}.{name} is reconstructable"
        if not checked:
            pytest.skip("no scipy/sklearn/pandas sinks available")

    def test_pandas_reader_reduce_reads_no_file(self, tmp_path):
        """A REDUCE payload calling pandas.read_csv on a real file is refused at
        global resolution, before the reader runs, so the file is never read."""
        pd = pytest.importorskip("pandas")
        secret = tmp_path / "secret.csv"
        secret.write_text("col\n1\n", encoding="utf-8")

        class Evil:
            def __reduce__(self):
                return (pd.read_csv, (str(secret),))

        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                BytesIO(pickle.dumps(Evil(), protocol=4)), **self.BROAD
            )

    @pytest.mark.parametrize(
        "module,name",
        [
            # nested-unpickle (RCE) helpers under pandas.compat.
            ("pandas.compat.pickle_compat", "loads"),
            ("pandas.compat.pickle_compat", "load_reduce"),
            ("pandas.compat.pickle_compat", "Unpickler"),
            # file read/write under the model-allowed scipy.sparse namespace.
            ("scipy.sparse", "load_npz"),
            ("scipy.sparse", "save_npz"),
            # file-open-by-path in numpy record arrays.
            ("numpy.ma.mrecords", "openfile"),
            ("numpy.ma.mrecords", "fromtextfile"),
            # path / file-like readers deep in the allowed stacks.
            ("pandas._libs.parsers", "TextReader"),
            ("numpy._core._multiarray_umath", "_load_from_filelike"),
        ],
    )
    def test_deep_submodule_file_and_code_sinks_refused(self, module, name):
        """A broad scientific-stack allow reaches deep submodules; file-read/open
        and nested-unpickle sinks living in otherwise-allowed namespaces must still
        be refused. Import-guarded: skipped where absent."""
        import importlib

        try:
            m = importlib.import_module(module)
        except BaseException:
            pytest.skip(f"{module} unavailable")
        if not hasattr(m, name):
            pytest.skip(f"{module}.{name} unavailable")
        assert self._blocked(module, name), f"{module}.{name} is reconstructable"

    def test_frozen_importlib_reexport_refused(self, monkeypatch):
        """``spec_from_file_location`` loads/executes code from a file path (RCE).
        It is re-exported into some allowed sci submodules, where it resolves to
        ``__module__ == _frozen_importlib_external`` (not ``importlib``). Injecting
        that re-export under an allowed namespace confirms the frozen-importlib
        denylist refuses it at resolution, independent of stdlib layout."""
        import importlib
        import sys
        import types

        spec = getattr(
            importlib.import_module("importlib.util"), "spec_from_file_location"
        )
        if not getattr(spec, "__module__", "").startswith("_frozen_importlib"):
            pytest.skip("spec_from_file_location is not from frozen importlib here")
        numpy = pytest.importorskip("numpy")
        fake = types.ModuleType("numpy._evil_reexport")
        fake.spec_from_file_location = spec
        monkeypatch.setitem(sys.modules, "numpy._evil_reexport", fake)
        monkeypatch.setattr(numpy, "_evil_reexport", fake, raising=False)
        assert self._blocked(
            "numpy._evil_reexport", "spec_from_file_location"
        ), "frozen-importlib code-load sink is reconstructable via a re-export"

    def test_scipy_sparse_load_npz_reduce_reads_no_file(self, tmp_path):
        """A REDUCE payload calling scipy.sparse.load_npz on a real .npz is refused
        at global resolution, before the read runs (the sink lives under the
        model-allowed scipy.sparse namespace)."""
        sparse = pytest.importorskip("scipy.sparse")
        target = tmp_path / "m.npz"
        sparse.save_npz(str(target), sparse.csr_matrix([[1, 0], [0, 1]]))

        class Evil:
            def __reduce__(self):
                return (sparse.load_npz, (str(target),))

        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                BytesIO(pickle.dumps(Evil(), protocol=4)), **self.BROAD
            )

    def test_real_write_sink_payloads_create_no_file(self, tmp_path):
        """REDUCE payloads that call a numpy write sink are refused *before* the
        callable runs, so the attacker's target file is never created."""
        numpy = pytest.importorskip("numpy")
        import importlib

        made = []
        for mod, name, mkargs in [
            ("numpy", "save", lambda t: (str(t), numpy.arange(4))),
            ("numpy", "savetxt", lambda t: (str(t), numpy.arange(4))),
            ("numpy.lib.format", "open_memmap", lambda t: (str(t), "w+", "int8", (8,))),
        ]:
            try:
                fn = getattr(importlib.import_module(mod), name)
            except BaseException:
                continue
            target = tmp_path / f"pwn_{name}"

            class Evil:
                def __reduce__(self):
                    return (fn, mkargs(target))

            with pytest.raises(pickle.UnpicklingError):
                allowlisted_pickle_load(
                    BytesIO(pickle.dumps(Evil(), protocol=4)), **self.BROAD
                )
            assert not target.exists(), f"{mod}.{name} wrote {target}"
            made.append(name)
        assert made, "no numpy write sinks available to exercise"

    def test_bounded_cross_stack_sink_sweep_finds_no_leak(self):
        """Across the sink-bearing modules of every allowed stack, no callable
        whose resolved qualname is a denied sink is reconstructable."""
        pytest.importorskip("numpy")
        import importlib

        from nltk.picklesec import _DENIED_SCISTACK_QUALNAMES

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
            "numpy.ctypeslib",
            "numpy.ma.mrecords",
            "numpy._core._multiarray_umath",
            "scipy.io",
            "scipy.io.matlab",
            "scipy.sparse",
            "scipy.sparse._matrix_io",
            "sklearn.datasets",
            "pandas",
            "pandas.io.pickle",
            "pandas._libs.parsers",
            "pandas.compat.pickle_compat",
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
                    if not self._blocked(mn, nm):
                        leaks.append(f"{mn}.{nm}")
        assert not leaks, f"reconstructable sinks: {leaks[:10]}"


class TestGuardsAreLoadBearing:
    """Mutation tests. Each neuters exactly one guard and confirms the synthetic
    exploit that guard is the SOLE defense against becomes reconstructable. This
    proves the guard is load-bearing (not dead code masked by another layer) and
    that the surrounding attack corpus would actually catch its removal.
    ``monkeypatch`` restores the guard (and sys.modules) after every test.
    """

    @staticmethod
    def _inject(monkeypatch, module_name, attr, qualname):
        """Install a synthetic callable at module_name.attr and return it."""
        import sys
        import types

        pytest.importorskip("numpy")
        import numpy

        fake = types.ModuleType(module_name)

        def sink(*a, **k):  # a stand-in for a re-exported dangerous callable
            return "PWNED"

        sink.__module__ = module_name
        sink.__qualname__ = qualname
        setattr(fake, attr, sink)
        monkeypatch.setitem(sys.modules, module_name, fake)
        # also expose it as an attribute of the parent package so the base
        # unpickler's getattr-after-import path resolves it
        parent, _, child = module_name.rpartition(".")
        if parent == "numpy":
            monkeypatch.setattr(numpy, child, fake, raising=False)
        return sink

    def test_qualname_catchall_is_load_bearing(self, monkeypatch):
        """A denied sink qualname re-exported under a numpy submodule that is
        neither a denied prefix nor an exact denied global is blocked ONLY by the
        resolved-qualname catch-all."""
        import nltk.picklesec as ps

        sink = self._inject(monkeypatch, "numpy._mut_qualname", "fromfile", "fromfile")
        broad = {"allowed_modules": ("numpy",)}

        up = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        with pytest.raises(pickle.UnpicklingError):
            up.find_class("numpy._mut_qualname", "fromfile")

        monkeypatch.setattr(ps, "_DENIED_SCISTACK_QUALNAMES", frozenset())
        up2 = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        assert (
            up2.find_class("numpy._mut_qualname", "fromfile") is sink
        ), "removing the catch-all did not expose the sink -> guard is not load-bearing"

    def test_denied_module_prefix_is_load_bearing(self, monkeypatch):
        """A callable whose real module sits under a denied prefix (numpy.lib) but
        whose qualname is not a known sink is blocked ONLY by the prefix denylist."""
        import nltk.picklesec as ps

        sink = self._inject(monkeypatch, "numpy.lib._mut_prefix", "gadget", "gadget")
        # numpy.lib._mut_prefix's parent is numpy.lib, not numpy; expose it there
        import numpy.lib

        monkeypatch.setattr(
            numpy.lib,
            "_mut_prefix",
            __import__("sys").modules["numpy.lib._mut_prefix"],
            raising=False,
        )
        broad = {"allowed_modules": ("numpy",)}

        up = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        with pytest.raises(pickle.UnpicklingError):
            up.find_class("numpy.lib._mut_prefix", "gadget")

        monkeypatch.setattr(ps, "_DENIED_MODULE_PREFIXES", ())
        up2 = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        assert (
            up2.find_class("numpy.lib._mut_prefix", "gadget") is sink
        ), "removing the denied prefixes did not expose the sink -> guard is not load-bearing"

    def test_exact_denied_globals_is_load_bearing(self, monkeypatch):
        """A callable pinned only by the exact ``_DENIED_GLOBALS`` set (module not
        prefix-denied, qualname not a sink) is blocked ONLY by that set."""
        import nltk.picklesec as ps

        sink = self._inject(monkeypatch, "numpy._mut_exact", "gadget", "gadget")
        broad = {"allowed_modules": ("numpy",)}
        pinned = ("numpy._mut_exact", "gadget")
        monkeypatch.setattr(ps, "_DENIED_GLOBALS", ps._DENIED_GLOBALS | {pinned})

        up = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        with pytest.raises(pickle.UnpicklingError):
            up.find_class(*pinned)

        # restore to the original set (drops our pin) -> now reconstructable
        monkeypatch.setattr(
            ps,
            "_DENIED_GLOBALS",
            frozenset(g for g in ps._DENIED_GLOBALS if g != pinned),
        )
        up2 = ps.AllowlistUnpickler(BytesIO(b""), **broad)
        assert up2.find_class(*pinned) is sink


def _ext_reduce_payload(code, cmd):
    """A protocol-2 pickle: ``EXT1(code)`` resolves a global through copyreg's
    extension registry (NOT find_class), then ``REDUCE`` would call it with cmd.
    Hand-assembled so it depends on nothing being registered at build time."""

    def _su(s):
        b = s.encode()
        return pickle.SHORT_BINUNICODE + bytes([len(b)]) + b

    return (
        pickle.PROTO
        + bytes([2])
        + pickle.EXT1
        + bytes([code])
        + _su(cmd)
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )


class TestExtensionOpcodeBypassBlocked:
    """The EXT1/EXT2/EXT4 extension-registry opcodes resolve a global through
    copyreg's process-wide registry, not through find_class. On a warm
    ``copyreg._extension_cache`` the (C) unpickler returns the cached object
    without ever calling find_class, so a find_class-only allowlist is bypassed
    (verified: neutering the scan below re-opens the hole). Both unpicklers scan
    for and refuse any EXT opcode up front; nltk pickles never use them.
    """

    _EXT_CODE = 173  # an arbitrary, unregistered extension code

    def _loaders(self):
        from nltk.parse.transitionparser import (
            _MODEL_ALLOWED_GLOBALS,
            _MODEL_ALLOWED_MODULES,
        )

        def allowlist(data):
            return allowlisted_pickle_load(
                BytesIO(data),
                allowed_globals=_MODEL_ALLOWED_GLOBALS,
                allowed_modules=_MODEL_ALLOWED_MODULES,
            )

        def restricted(data):
            from nltk.picklesec import RestrictedUnpickler

            return RestrictedUnpickler(BytesIO(data)).load()

        return {"allowlist": allowlist, "restricted": restricted}

    @pytest.mark.parametrize("loader", ["allowlist", "restricted"])
    def test_cold_ext_opcode_refused(self, loader):
        """With nothing registered, an EXT payload is refused before resolution."""
        load = self._loaders()[loader]
        with pytest.raises(pickle.UnpicklingError):
            load(_ext_reduce_payload(self._EXT_CODE, "echo cold"))

    @pytest.mark.parametrize("loader", ["allowlist", "restricted"])
    def test_warm_cache_ext_opcode_refused_and_no_exec(self, loader, tmp_path):
        """The real bypass: poison copyreg._extension_cache with os.system so the
        opcode would resolve WITHOUT find_class, then confirm it is still refused
        and the gadget does not run."""
        import copyreg

        load = self._loaders()[loader]
        marker = tmp_path / f"pwned_ext_{loader}"
        copyreg._extension_cache[self._EXT_CODE] = os.system
        try:
            with pytest.raises(pickle.UnpicklingError):
                load(_ext_reduce_payload(self._EXT_CODE, f"touch {marker}"))
            assert (
                not marker.exists()
            ), "EXT warm-cache gadget executed; the find_class bypass is not closed"
        finally:
            copyreg._extension_cache.pop(self._EXT_CODE, None)

    @pytest.mark.parametrize(
        "opcode,arg",
        [
            (pickle.EXT1, bytes([173])),
            (pickle.EXT2, (173).to_bytes(2, "little")),
            (pickle.EXT4, (173).to_bytes(4, "little")),
        ],
    )
    def test_all_ext_widths_refused(self, opcode, arg):
        """EXT1, EXT2 and EXT4 all bypass find_class, so each is refused."""
        from nltk.picklesec import RestrictedUnpickler

        payload = pickle.PROTO + bytes([2]) + opcode + arg + pickle.STOP
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(BytesIO(payload)).load()

    def test_persistent_id_refused(self):
        """PERSID would call persistent_load (another find_class bypass); neither
        unpickler defines one, so the default refuses it."""
        persid = pickle.PROTO + bytes([2]) + b"P" + b"1\n" + pickle.STOP
        for load in self._loaders().values():
            with pytest.raises(pickle.UnpicklingError):
                load(persid)

    def test_ext_scan_is_load_bearing(self, monkeypatch, tmp_path):
        """Neuter the EXT scan and confirm the warm-cache gadget then executes,
        proving the scan is the sole defense (find_class never fires for EXT)."""
        import copyreg

        import nltk.picklesec

        monkeypatch.setattr(
            nltk.picklesec, "_reject_extension_opcodes", lambda pickle_source: None
        )
        marker = tmp_path / "pwned_ext_mut"
        copyreg._extension_cache[self._EXT_CODE] = os.system
        try:
            nltk.picklesec.RestrictedUnpickler(
                BytesIO(_ext_reduce_payload(self._EXT_CODE, f"touch {marker}"))
            ).load()
            assert (
                marker.exists()
            ), "neutering the EXT scan did not expose the gadget; scan is not load-bearing"
        finally:
            copyreg._extension_cache.pop(self._EXT_CODE, None)

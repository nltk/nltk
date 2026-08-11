"""Regression tests for pickle RCE in model loading (CWE-502).

``TransitionParser.parse(depgraphs, modelFile)`` is a public API whose
``modelFile`` is caller-supplied. It used to be loaded with the warn-only
``pickle_load`` (``restricted=False``), which prints a warning and then performs
a full, unrestricted unpickle -- so a crafted model file achieved arbitrary code
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

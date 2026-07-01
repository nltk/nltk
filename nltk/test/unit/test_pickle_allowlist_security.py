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

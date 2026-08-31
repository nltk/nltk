# Natural Language Toolkit: allowlist-surface attack harness for the remaining
# AllowlistUnpickler callers (nltk.tokenize.punkt, nltk.parse.transitionparser)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack harness for the two non-``tbl.demo`` allowlisting unpickler callers.

``AllowlistUnpickler`` only gates ``find_class`` (WHICH class the pickle may
build); it does not constrain the ``REDUCE`` args or the ``BUILD`` /
``__setstate__`` STATE those classes are handed. The reference exploit (GHSA
umbrella / #3823) rode exactly that gap: a ``RegexpTagger`` built from only
allowlisted names, then handed a catastrophic ReDoS regex via BUILD (bypassing
its ``__init__`` guard). ``tbl.demo`` was hardened for that. This harness applies
the same technique to the other two callers and proves, with real runs, that
each surface is either refused, provably inert, or now hardened.

Caller 1: ``nltk.tokenize.punkt.punkt_pickle_load``
    Allowlist: the Punkt classes, ``nltk.probability.FreqDist``,
    ``collections.defaultdict`` and ``builtins.int``. This surface is PROVEN SAFE
    against the planted-regex vector, for two independent reasons:
      * No regex compile primitive is on the allowlist (``re.compile`` /
        ``re._compile`` / ``regex._regex.compile`` are all refused), so a compiled
        catastrophic pattern object cannot be reconstructed AT ALL.
      * The only instance level regex caches are ``PunktLanguageVars`` slots
        (``_re_period_context`` / ``_re_word_tokenizer``), and that class overrides
        ``__setstate__`` to DISCARD state, so a BUILD cannot poison them. Every
        other Punkt regex is a class level constant compiled at import.
    A genuinely trained tokenizer still round-trips and tokenizes identically.

Caller 2: ``nltk.parse.transitionparser.TransitionParser.parse``
    Allowlist: a fitted ``sklearn.svm.SVC`` plus the numpy / scipy globals it
    reconstructs. It carries NO regex, so the ReDoS vector does not apply. The
    compact numpy OOM bomb (huge shape, tiny buffer) is refused by numpy's own
    size validation. The one real gadget is numpy's object dtype nested unpickle:
    ``numpy.*.multiarray.scalar(dtype('O'), payload)`` deserializes ``payload``
    with numpy's own unrestricted unpickler, AT REDUCE time inside the call, so a
    post load check cannot undo it. The caller now wraps ``scalar`` to refuse an
    object bearing dtype before numpy runs, and walks the reconstructed graph to
    refuse any residual object dtype array. A genuinely trained model still loads
    and parses.

Cross-platform notes: the hang proof uses a subprocess wall-clock timeout
(``subprocess.run(timeout=...)``), never a Unix signal; pickle fixtures under the
``pathsec_sandbox`` root are opened ``"rb"`` / ``"wb"``.
"""

import io
import os
import pickle
import subprocess
import sys
import textwrap

import pytest

from nltk.tokenize.punkt import (  # noqa: E402
    _PUNKT_ALLOWED_GLOBALS,
    PunktLanguageVars,
    PunktSentenceTokenizer,
    PunktTrainer,
    punkt_pickle_load,
)

# ===========================================================================
# Caller 1: nltk.tokenize.punkt.punkt_pickle_load
# ===========================================================================


def _su(s):
    """Encode ``s`` as a protocol-4 SHORT_BINUNICODE opcode fragment."""
    raw = s.encode()
    return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw


# A pattern the regex engine does not collapse to linear time: identical
# alternatives still backtrack exponentially. 40 matching chars then a
# non-matching one is ~2**40 steps, i.e. effectively unbounded under any loader
# with no cap.
_CATASTROPHIC = r"(a|a)+$"
_BAIT = "a" * 40 + "!"


@pytest.mark.parametrize(
    "module,name",
    [
        ("re", "compile"),
        ("re", "_compile"),
        ("regex", "compile"),
        ("regex._regex", "compile"),
        ("_sre", "compile"),
    ],
)
def test_punkt_no_regex_compile_primitive_is_reconstructable(module, name):
    """No regex compile primitive is on the Punkt allowlist, so a compiled
    catastrophic pattern object can never be reconstructed to plant in the
    tokenizer. Every spelling is refused at ``find_class``."""
    payload = (
        pickle.PROTO
        + bytes([4])
        + _su(module)
        + _su(name)
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        punkt_pickle_load(io.BytesIO(payload))


def test_punkt_build_cannot_poison_langvars_regex_slot():
    """The #3823 technique applied to Punkt: build an allowlisted
    ``PunktLanguageVars`` and try to plant a value in its cached
    ``_re_period_context`` regex slot via BUILD. ``PunktLanguageVars.__setstate__``
    discards the state, so the slot stays unset and ``period_context_re`` recompiles
    the safe hardcoded pattern. Name-checking is not even relied on here: the class
    IS allowlisted, yet the state cannot ride it."""
    payload = (
        pickle.PROTO
        + bytes([4])
        + _su("nltk.tokenize.punkt")
        + _su("PunktLanguageVars")
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.EMPTY_DICT
        + _su("_re_period_context")
        + _su("POISON")
        + pickle.SETITEM
        + pickle.BUILD
        + pickle.STOP
    )
    obj = punkt_pickle_load(io.BytesIO(payload))
    assert isinstance(obj, PunktLanguageVars)
    # The attacker's slot value was discarded by __setstate__ ...
    assert not hasattr(obj, "_re_period_context")
    # ... so the runtime regex is recompiled from the trusted class source.
    assert obj.period_context_re() is not None
    assert obj._re_period_context is not None  # now cached, but the SAFE pattern


def test_punkt_gadget_hidden_in_build_state_is_refused():
    """A code-exec global placed as a BUILD state VALUE (not the reduce callable)
    is still routed through ``find_class`` and refused."""
    payload = (
        pickle.PROTO
        + bytes([4])
        + _su("nltk.tokenize.punkt")
        + _su("PunktSentenceTokenizer")
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.EMPTY_DICT
        + _su("_lang_vars")
        + _su("os")
        + _su("system")
        + pickle.STACK_GLOBAL  # os.system as a state value
        + pickle.SETITEM
        + pickle.BUILD
        + pickle.STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        punkt_pickle_load(io.BytesIO(payload))


def test_punkt_reduce_code_exec_gadget_refused():
    """A top-level REDUCE naming ``os.system`` is refused before the call."""
    payload = (
        pickle.PROTO
        + bytes([4])
        + _su("os")
        + _su("system")
        + pickle.STACK_GLOBAL
        + _su("echo pwned")
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        punkt_pickle_load(io.BytesIO(payload))


def test_punkt_allowlist_is_exactly_the_stateless_surface():
    """Documents the audited allowlist: only Punkt classes plus the FreqDist /
    defaultdict / int primitives a Punkt parameter table needs. None of them holds
    an attacker-settable compiled regex or an executable callable, which is why the
    planted-regex vector has no landing site."""
    names = {name for _mod, name in _PUNKT_ALLOWED_GLOBALS}
    assert names == {
        "PunktSentenceTokenizer",
        "PunktParameters",
        "PunktLanguageVars",
        "PunktToken",
        "PunktTrainer",
        "PunktBaseClass",
        "PunktTokenizer",
        "FreqDist",
        "defaultdict",
        "int",
    }
    # No regex compile primitive anywhere in the allowlist.
    assert not any("compile" in name for _mod, name in _PUNKT_ALLOWED_GLOBALS)


def test_punkt_benign_trained_tokenizer_roundtrips(pathsec_sandbox):
    """Benign control: a genuinely trained ``PunktSentenceTokenizer`` saved and
    reloaded through ``punkt_pickle_load`` tokenizes identically (the hardening
    does not change legitimate behaviour), and the reloaded tokenizer runs the
    ReDoS bait FAST, proof that no catastrophic pattern was planted and the
    runtime regexes are the safe hardcoded ones."""
    train_text = (
        "Mr. Smith went to Washington. He met Dr. Jones at 3 p.m. "
        "The meeting, held on Jan. 5, went well. She said hello. They left."
    ) * 40
    trainer = PunktTrainer()
    trainer.train(train_text, finalize=True)
    tok = PunktSentenceTokenizer(trainer.get_params())
    sample = "Dr. Brown arrived. He was late. The class, however, waited."
    expected = tok.tokenize(sample)

    path = pathsec_sandbox.root / "punkt.pkl"
    with open(path, "wb") as fh:
        pickle.dump(tok, fh, protocol=4)
    with open(path, "rb") as fh:
        reloaded = punkt_pickle_load(fh)

    assert isinstance(reloaded, PunktSentenceTokenizer)
    assert reloaded.tokenize(sample) == expected
    # The bait would hang a catastrophic regex; on the safe hardcoded regexes it
    # tokenizes in microseconds. (word_tokenize exercises _word_tokenizer_re.)
    reloaded._lang_vars.word_tokenize(_BAIT)
    reloaded.tokenize(_BAIT + " Next sentence.")


# Teeth: the planted-regex vector is real, the allowlist closes it.

# Child: load a pickled compiled regex with a plain (unbounded) ``pickle.load``
# and run it on the bait. That is what a planted-regex attack ultimately needs to
# execute; the Punkt allowlist refuses to reconstruct the regex object at all, so
# this hang can only be reached OUTSIDE the allowlisted loader.
_REGEX_HANG_CHILD = textwrap.dedent(
    """
    import pickle, sys
    with open(sys.argv[1], "rb") as fh:
        data = fh.read()
    pat = pickle.loads(data)          # unbounded reference loader (teeth)
    list(pat.finditer(sys.argv[2]))   # catastrophic backtracking -> hangs
    print("RETURNED")
    """
)


def _pkg_env():
    env = os.environ.copy()
    import nltk

    pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(nltk.__file__)))
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    return env


def test_punkt_teeth_pickled_catastrophic_regex_hangs_and_is_refused(pathsec_sandbox):
    """Teeth + closure. A pickled compiled catastrophic regex, loaded by a plain
    ``pickle.load`` and used, hangs past the wall-clock timeout (the vector is
    genuinely dangerous). The SAME bytes handed to ``punkt_pickle_load`` are
    refused, because the ``re._compile`` global a compiled pattern needs is not on
    the Punkt allowlist, so this payload can never reach the tokenizer."""
    import re

    payload = pickle.dumps(re.compile(_CATASTROPHIC), protocol=4)
    path = pathsec_sandbox.root / "evil_regex.pkl"
    with open(path, "wb") as fh:
        fh.write(payload)

    # Teeth: plain loader + use hangs.
    try:
        subprocess.run(
            [sys.executable, "-c", _REGEX_HANG_CHILD, str(path), _BAIT],
            capture_output=True,
            text=True,
            timeout=8,
            env=_pkg_env(),
        )
        pytest.fail("plain loader unexpectedly returned; bait was not catastrophic")
    except subprocess.TimeoutExpired:
        pass  # expected: the catastrophic regex hangs

    # Closure: the allowlisting loader refuses to reconstruct the regex object.
    with open(path, "rb") as fh:
        with pytest.raises(pickle.UnpicklingError):
            punkt_pickle_load(fh)


# ===========================================================================
# Caller 2: nltk.parse.transitionparser.TransitionParser.parse
# ===========================================================================

numpy = pytest.importorskip("numpy")


def _tp():
    """Import the transition-parser hardening helpers (skip if deps missing)."""
    pytest.importorskip("scipy")
    pytest.importorskip("sklearn")
    from nltk.parse import transitionparser as tp

    return tp


def _canary_bytes():
    """Bytes of a pickle whose reduce has an observable effect (a marker dict),
    standing in for an arbitrary-code payload."""

    class Canary:
        def __reduce__(self):
            return (dict, ([("PWNED", 1)],))

    return pickle.dumps(Canary())


def _scalar_object_payload():
    """A pickle that calls ``numpy.*.multiarray.scalar(dtype('O'), <bytes>)``, the
    numpy object dtype nested unpickle gadget, built from only allowlisted names."""

    class ScalarEscape:
        def __reduce__(self):
            import numpy.core.multiarray as ma

            return (ma.scalar, (numpy.dtype("O"), _canary_bytes()))

    return pickle.dumps(ScalarEscape(), protocol=5)


def _object_ndarray_payload():
    """An object dtype ndarray reconstructed via ``_reconstruct`` + ``__setstate__``
    whose elements are plain ints (so no denied global is named and the array
    slips past ``find_class`` to the post-load walk)."""

    class ObjArr:
        def __reduce__(self):
            import numpy.core.multiarray as ma

            state = (1, (2,), numpy.dtype("O"), False, [1, 2])
            return (ma._reconstruct, (numpy.ndarray, (0,), b"b"), state)

    return pickle.dumps(ObjArr(), protocol=5)


def test_tp_scalar_object_dtype_gadget_passes_the_bare_name_allowlist():
    """Teeth. The name allowlist is NOT what stops the object dtype ``scalar``
    gadget: ``find_class`` accepts both ``scalar`` and ``numpy.dtype``, so the
    gadget is assembled from only allowlisted names and reaches numpy's own object
    dtype scalar handler. What numpy does then is version dependent (numpy < 1.25
    deserializes the attacker bytes with its own unrestricted unpickler = RCE;
    numpy >= ~2.4 hard-refuses), which is exactly why the fix must intercept BEFORE
    numpy rather than rely on name-checking."""
    tp = _tp()
    import warnings

    from nltk.picklesec import AllowlistUnpickler, allowlisted_pickle_load

    # 1) Both building blocks resolve through the bare allowlist (not refused).
    resolver = AllowlistUnpickler(
        io.BytesIO(b""),
        allowed_globals=tp._MODEL_ALLOWED_GLOBALS,
        allowed_modules=tp._MODEL_ALLOWED_MODULES,
    )
    assert callable(resolver.find_class("numpy._core.multiarray", "scalar"))
    assert resolver.find_class("numpy", "dtype") is numpy.dtype

    # 2) Loading the assembled gadget through the bare allowlist is NOT stopped by
    # the allowlist's own name refusal: it reaches numpy, which then handles it in
    # a version-dependent way (returns on old numpy, raises its own error on new).
    name_refusal = None
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            allowlisted_pickle_load(
                io.BytesIO(_scalar_object_payload()),
                allowed_globals=tp._MODEL_ALLOWED_GLOBALS,
                allowed_modules=tp._MODEL_ALLOWED_MODULES,
            )
    except pickle.UnpicklingError as exc:
        name_refusal = exc
    except Exception:
        pass  # numpy's own version-dependent handling; the gadget reached numpy
    assert (
        name_refusal is None
    ), f"name allowlist unexpectedly stopped it: {name_refusal}"


def test_tp_scalar_object_dtype_gadget_refused_by_hardened_loader():
    """The hardened loader wraps ``scalar`` to refuse an object bearing dtype
    before numpy deserializes anything, so the gadget is closed at reconstruction
    time (the only place it can be, since numpy runs it inside the REDUCE)."""
    tp = _tp()
    with pytest.raises(pickle.UnpicklingError):
        tp._load_transitionparser_model(io.BytesIO(_scalar_object_payload()))


def test_tp_object_dtype_ndarray_refused_by_post_load_walk():
    """An object dtype ndarray assembled from allowlisted-only elements slips past
    ``find_class`` (no denied global is named). Teeth: a plain ``pickle.load``
    builds it (an object array is the container the gadget rides). The hardened
    loader's bounded post-load walk refuses it. No fitted SVC carries an object
    dtype array."""
    tp = _tp()
    payload = _object_ndarray_payload()
    plain = pickle.loads(payload)  # teeth: plain loader builds an object array
    assert isinstance(plain, numpy.ndarray) and plain.dtype.hasobject
    with pytest.raises(pickle.UnpicklingError):
        tp._load_transitionparser_model(io.BytesIO(payload))


def test_tp_numeric_scalar_still_reconstructs():
    """Benign control for the ``scalar`` wrapper: a real numeric numpy scalar
    (float64) reconstructs unchanged; the guard only refuses object bearing
    dtypes, not the numeric scalars a genuine model carries."""
    tp = _tp()

    class FloatScalar:
        def __reduce__(self):
            import numpy.core.multiarray as ma

            return (ma.scalar, (numpy.dtype("float64"), numpy.float64(3.14).tobytes()))

    obj = tp._load_transitionparser_model(io.BytesIO(pickle.dumps(FloatScalar(), 5)))
    assert float(obj) == pytest.approx(3.14)


def test_tp_compact_oom_bomb_is_refused():
    """The compact numpy OOM bomb (huge shape, tiny data buffer) is refused by
    numpy's own ``__setstate__`` size validation, so it never allocates."""
    tp = _tp()

    class HugeArr:
        def __reduce__(self):
            import numpy.core.multiarray as ma

            state = (1, (10**9,), numpy.dtype("float64"), False, b"\x00" * 5)
            return (ma._reconstruct, (numpy.ndarray, (0,), b"b"), state)

    with pytest.raises((ValueError, pickle.UnpicklingError)):
        tp._load_transitionparser_model(io.BytesIO(pickle.dumps(HugeArr(), 5)))


def test_tp_code_exec_gadget_refused():
    """A top-level REDUCE naming ``os.system`` is refused by the name allowlist."""
    tp = _tp()
    payload = (
        pickle.PROTO
        + bytes([4])
        + _su("os")
        + _su("system")
        + pickle.STACK_GLOBAL
        + _su("echo pwned")
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        tp._load_transitionparser_model(io.BytesIO(payload))


def test_tp_benign_trained_model_roundtrips_and_parses(pathsec_sandbox):
    """Functional control (real, not mocked): train an ``arc-standard`` transition
    parser to a fitted SVC, then load it back through the hardened loader and parse
    a sentence. The reconstructed model is a real ``SVC`` with numeric (float64)
    ``classes_`` and produces a dependency graph."""
    _tp()
    from nltk.parse import DependencyGraph
    from nltk.parse.transitionparser import (
        TransitionParser,
        _load_transitionparser_model,
    )

    gold = DependencyGraph(
        "Economic  JJ     2      ATT\n"
        "news  NN     3       SBJ\n"
        "has       VBD       0       ROOT\n"
        "little      JJ      5       ATT\n"
        "effect   NN     3       OBJ\n"
        "on     IN      5       ATT\n"
        "financial       JJ       8       ATT\n"
        "markets    NNS      6       PC\n"
        ".    .      3       PU\n"
    )
    model = pathsec_sandbox.root / "tp.model"
    parser = TransitionParser("arc-standard")
    parser.train([gold], str(model), verbose=False)

    with open(model, "rb") as fh:
        reconstructed = _load_transitionparser_model(fh)
    from sklearn.svm import SVC

    assert isinstance(reconstructed, SVC)
    assert reconstructed.classes_.dtype.kind in ("f", "i")

    parsed = parser.parse([gold], str(model))
    assert len(parsed) == 1
    assert len(parsed[0].nodes) == len(gold.nodes)

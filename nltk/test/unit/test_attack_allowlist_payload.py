# Natural Language Toolkit: allowlist-surface attack harness for nltk.tbl.demo
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack harness for the ``nltk.tbl.demo`` allowlisting unpickler (GHSA-8mgp).

The companion suite ``test_tbl_demo_allowlist_load.py`` proves the *name* guard:
a global outside :data:`nltk.tbl.demo._TBL_MODEL_ALLOWED_GLOBALS` cannot be
reconstructed. That is necessary but not sufficient. ``AllowlistUnpickler`` only
gates ``find_class`` (which class the pickle may build); it does not constrain
the ``REDUCE`` args or the ``BUILD`` / ``__setstate__`` *state* those classes are
handed. So an attacker who uses *only* allowlisted names can still steer a
reconstructed object into hostile territory.

This harness enumerates that second surface and proves, with real runs, that
every path is either refused, provably inert, or bounded:

* **ReDoS (the one genuine leak, now fixed).** A ``RegexpTagger`` can be handed a
  catastrophic pattern either raw in ``_regexps`` (no wall-clock cap) or wrapped
  in a ``TimedPattern`` whose ``_timeout`` the attacker sets to ``None`` (cap
  disabled). Both use only allowlisted names, both are accepted by the name
  guard, and under a plain / warn-only loader both hang the process the moment
  the reloaded tagger tags a crafted token (CWE-1333). The demo loader now
  re-derives every reconstructed regex from its source string through
  :func:`nltk.redos.compile`, so the pattern is bounded by the redos wall-clock
  cap. Teeth: the *same* payload hangs under ``pickle.load`` (subprocess proof).
* **BUILD / __setstate__ abuse, args-controlled construction, type confusion.**
  Hostile state / args on the other allowlisted classes yield at worst a bounded
  ``AttributeError`` / ``TypeError``, never code execution and never a hang.
  Any global named inside the state (``os.system`` as a Rule condition, ...) is
  still gated by ``find_class``.
* **Memory / recursion bomb.** A deeply nested or self-referential graph of
  allowlisted nodes is bounded (``RecursionError`` / linear memory), and the
  post-load hardening walk that re-derives regexes is itself node-bounded so it
  cannot be turned into the DoS it prevents.
* **object sentinel.** ``builtins.object`` reconstructs a bare, state-less
  instance with no ``__reduce__`` / ``__setstate__`` hook to ride.

Cross-platform notes: the hang proof uses a **subprocess wall-clock timeout**
(``subprocess.run(timeout=...)``), never a Unix signal, so it runs on Windows
too; pickle fixtures live under the ``pathsec_sandbox`` registered root and are
opened ``"rb"`` / ``"wb"``.
"""

import io
import os
import pickle
import subprocess
import sys
import textwrap
import time

import pytest
import regex

from nltk import redos
from nltk.redos import _UNSET, TimedPattern
from nltk.tag import DefaultTagger, RegexpTagger, UnigramTagger
from nltk.tag.brill import BrillTagger, Pos, Word
from nltk.tbl import demo
from nltk.tbl.rule import Rule

# A pattern the ``regex`` engine's optimiser does NOT collapse to linear time:
# an alternation of identical branches still backtracks exponentially, so it is
# the canonical ReDoS vector the redos wall-clock cap exists to bound.
CATASTROPHIC = r"(a|a)*$"
# 40 matching chars then a non-matching one -> ~2**40 backtracking steps, i.e.
# effectively unbounded (minutes to years) under a loader with no cap, while the
# redos cap trips in well under its DEFAULT_TIMEOUT.
BAIT = "a" * 40 + "!"


# ===========================================================================
# Builders: malicious taggers assembled from ONLY allowlisted names.
# NEWOBJ + BUILD means __init__ never runs, so the ReDoS guard inside
# RegexpTagger.__init__ (redos.compile) is bypassed at reconstruction time.
# ===========================================================================


def _regexp_tagger_with(pattern_obj):
    """A RegexpTagger whose single ``_regexps`` entry is ``pattern_obj`` as-is.

    ``pattern_obj`` is inserted verbatim (no ``__init__``), so the caller decides
    whether it is a raw compiled ``regex``, a ``TimedPattern`` with a disabled
    cap, or a legitimate capped ``TimedPattern``.
    """
    t = RegexpTagger.__new__(RegexpTagger)
    t.__dict__["_taggers"] = [t]
    t.__dict__["_regexps"] = [(pattern_obj, "X")]
    return t


def _payload_timeout_none():
    """Vector 1: a TimedPattern with attacker-supplied ``timeout=None`` (cap off)."""
    tp = TimedPattern(regex.compile(CATASTROPHIC), timeout=None)
    return pickle.dumps(_regexp_tagger_with(tp), protocol=4)


def _payload_raw_pattern():
    """Vector 2: a raw compiled ``regex`` object in ``_regexps`` (no cap at all)."""
    raw = regex.compile(CATASTROPHIC)
    return pickle.dumps(_regexp_tagger_with(raw), protocol=4)


def _payload_nested_backoff():
    """Vector 3: the catastrophic RegexpTagger buried as a UnigramTagger backoff."""
    tp = TimedPattern(regex.compile(CATASTROPHIC), timeout=None)
    rt = _regexp_tagger_with(tp)
    uni = UnigramTagger.__new__(UnigramTagger)
    uni.__dict__["_taggers"] = [uni, rt]
    uni.__dict__["_context_to_tag"] = {}
    return pickle.dumps(uni, protocol=4)


# ===========================================================================
# Payload class 1: ReDoS through the allowlisted regex surface
# ===========================================================================


@pytest.mark.parametrize(
    "build",
    [_payload_timeout_none, _payload_raw_pattern, _payload_nested_backoff],
    ids=["timeout_none", "raw_pattern", "nested_backoff"],
)
def test_redos_payloads_pass_the_name_allowlist(build):
    """Each ReDoS payload is *accepted* by the name guard: ``demo._load_tbl_model``
    loads it without raising ``UnpicklingError``. That is exactly the point: every
    global it names is on the tbl allowlist, so name-checking alone cannot stop
    it and the defence has to be structural (the post-load re-derivation below)."""
    obj = demo._load_tbl_model(io.BytesIO(build()))
    assert obj is not None  # find_class accepted every global in the payload


@pytest.mark.parametrize(
    "build",
    [_payload_timeout_none, _payload_raw_pattern, _payload_nested_backoff],
    ids=["timeout_none", "raw_pattern", "nested_backoff"],
)
def test_redos_reconstructed_pattern_is_capped(build):
    """After the demo loader runs, every reconstructed pattern is a TimedPattern
    whose ``_timeout`` is the enforced default sentinel (not the attacker's
    ``None`` and not a raw uncapped ``regex`` object)."""
    obj = demo._load_tbl_model(io.BytesIO(build()))
    tagger = obj if isinstance(obj, RegexpTagger) else obj._taggers[1]
    assert isinstance(tagger, RegexpTagger)
    for pattern, _tag in tagger._regexps:
        assert isinstance(pattern, TimedPattern)
        assert pattern._timeout is _UNSET  # -> uses redos.DEFAULT_TIMEOUT at match


# Subprocess hang proof (cross-platform, wall-clock, no signals).

# Child: load a pickle either through the hardened demo loader or a plain
# unbounded ``pickle.load`` (teeth), then tag the bait. The redos cap is lowered
# so a *bounded* run finishes quickly while an *unbounded* run runs until the
# parent's ``subprocess.run(timeout=...)`` kills it.
_CHILD = textwrap.dedent(
    """
    import io, pickle, sys
    import nltk.redos as redos
    redos.DEFAULT_TIMEOUT = float(sys.argv[3])
    from nltk.tbl import demo
    from nltk.tag.sequential import RegexpTagger
    path, mode, _cap, bait = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
    with open(path, "rb") as fh:
        data = fh.read()
    if mode == "hardened":
        obj = demo._load_tbl_model(io.BytesIO(data))
    else:
        obj = pickle.loads(data)          # unbounded reference loader (teeth)
    tagger = obj if isinstance(obj, RegexpTagger) else obj._taggers[1]
    try:
        tagger.tag([bait])
        print("RETURNED")
    except TimeoutError:
        print("BOUNDED")                  # the redos cap tripped -> bounded
    """
)


def _run_child(pickle_path, mode, cap, bait, wall_timeout):
    """Run the child on ``pickle_path``; return (timed_out, stdout)."""
    env = os.environ.copy()
    pkg_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(demo.__file__)))
        )
    )
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD, str(pickle_path), mode, str(cap), bait],
            capture_output=True,
            text=True,
            timeout=wall_timeout,
            env=env,
        )
        return False, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return True, ""


@pytest.mark.parametrize(
    "build",
    [_payload_timeout_none, _payload_raw_pattern, _payload_nested_backoff],
    ids=["timeout_none", "raw_pattern", "nested_backoff"],
)
def test_redos_hardened_loader_is_bounded_in_subprocess(build, pathsec_sandbox):
    """USE the reconstructed tagger on the bait string in a subprocess: with the
    hardened demo loader the tag call returns (redos cap tripped) well before the
    wall-clock timeout, i.e. it does NOT hang."""
    path = pathsec_sandbox.root / "redos_payload.pcl"
    with open(path, "wb") as fh:
        fh.write(build())
    t0 = time.time()
    timed_out, out = _run_child(path, "hardened", cap=1.0, bait=BAIT, wall_timeout=25)
    elapsed = time.time() - t0
    assert not timed_out, f"hardened loader HUNG on {build.__name__} ({elapsed:.1f}s)"
    assert out == "BOUNDED", f"unexpected child output {out!r}"


def test_redos_teeth_unbounded_loader_hangs(pathsec_sandbox):
    """Teeth: the SAME payload, loaded by a plain (unbounded) ``pickle.load`` and
    used, hangs past the wall-clock timeout, proving the payload is a genuine
    DoS that only the structural fix (not the name allowlist) neutralises."""
    path = pathsec_sandbox.root / "redos_payload_teeth.pcl"
    with open(path, "wb") as fh:
        fh.write(_payload_raw_pattern())
    # Cap is irrelevant to the unbounded child (it never wraps in a TimedPattern).
    timed_out, out = _run_child(path, "unbounded", cap=1.0, bait=BAIT, wall_timeout=8)
    assert timed_out, (
        "the unbounded reference loader unexpectedly returned "
        f"({out!r}); the bait was not catastrophic enough to prove teeth"
    )


def test_redos_legit_regexp_tagger_still_tags_after_load(pathsec_sandbox):
    """Benign control: a legitimately built RegexpTagger round-trips through the
    demo loader and still tags correctly (the fix re-derives the identical
    capped pattern, so behaviour is unchanged)."""
    tagger = RegexpTagger([(r"^-?[0-9]+$", "CD"), (r".*s$", "NNS"), (r".*", "NN")])
    path = pathsec_sandbox.root / "legit_regexp.pcl"
    with open(path, "wb") as fh:
        pickle.dump(tagger, fh)
    with open(path, "rb") as fh:
        reloaded = demo._load_tbl_model(fh)
    assert isinstance(reloaded, RegexpTagger)
    assert reloaded.tag(["12", "cats", "sleep"]) == [
        ("12", "CD"),
        ("cats", "NNS"),
        ("sleep", "NN"),
    ]
    for pattern, _tag in reloaded._regexps:
        assert isinstance(pattern, TimedPattern) and pattern._timeout is _UNSET


# ===========================================================================
# Payload class 2: BUILD / __setstate__ abuse on the other allowlisted classes
# ===========================================================================


def test_build_hostile_brilltagger_state_is_bounded():
    """A BrillTagger reconstructed with attacker-chosen ``_initial_tagger`` /
    ``_rules`` cannot execute code; using it either tags or raises a bounded
    error. Here the rules carry hostile, wrong-typed state."""
    rule = Rule.__new__(Rule)
    rule.__dict__.update(
        original_tag="X",
        replacement_tag="Y",
        templateid="0",
        _conditions=(),  # empty -> rule always applies to X-tagged tokens
    )
    b = BrillTagger.__new__(BrillTagger)
    b.__dict__["_initial_tagger"] = DefaultTagger("X")
    b.__dict__["_rules"] = (rule,)
    b.__dict__["_training_stats"] = None
    loaded = demo._load_tbl_model(io.BytesIO(pickle.dumps(b, protocol=4)))
    assert isinstance(loaded, BrillTagger)
    # No hang, no exec: it simply tags (DefaultTagger 'X' then rule X->Y).
    assert loaded.tag(["a", "b", "c"]) == [("a", "Y"), ("b", "Y"), ("c", "Y")]


def test_build_hostile_rule_conditions_bounded_crash():
    """A Rule whose ``_conditions`` reference a feature with a non-int
    ``positions`` produces a bounded ``TypeError`` at tag time, not a hang or
    execution."""
    feat = Word.__new__(Word)
    feat.__dict__["positions"] = ("not-an-int",)  # hostile: breaks index+pos math
    rule = Rule.__new__(Rule)
    rule.__dict__.update(
        original_tag="X",
        replacement_tag="Y",
        templateid="0",
        _conditions=((feat, "v"),),
    )
    b = BrillTagger.__new__(BrillTagger)
    b.__dict__["_initial_tagger"] = DefaultTagger("X")
    b.__dict__["_rules"] = (rule,)
    b.__dict__["_training_stats"] = None
    loaded = demo._load_tbl_model(io.BytesIO(pickle.dumps(b, protocol=4)))
    with pytest.raises((TypeError, ValueError)):
        loaded.tag(["a", "b", "c"])


# ===========================================================================
# Payload class 3: args-controlled constructor side effects (REDUCE)
# ===========================================================================


def test_reduce_constructor_args_no_exec():
    """A REDUCE that calls an allowlisted constructor with attacker args builds an
    object without executing code. A DefaultTagger built via REDUCE with a hostile
    tag string is inert (it just returns that tag)."""
    import pickletools

    # Protocol-4 pickle equivalent to REDUCE(DefaultTagger, ('PWNED',)).
    def su(s):
        raw = s.encode()
        return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw

    payload = (
        pickle.PROTO
        + bytes([4])
        + su("nltk.tag.sequential")
        + su("DefaultTagger")
        + pickle.STACK_GLOBAL
        + su("PWNED")
        + pickle.TUPLE1
        + pickle.REDUCE
        + pickle.STOP
    )
    obj = demo._load_tbl_model(io.BytesIO(payload))
    assert isinstance(obj, DefaultTagger)
    assert obj.tag(["w"]) == [("w", "PWNED")]  # inert: no side effect beyond tagging
    # The opcode stream really did drive a REDUCE.
    assert any(op.name == "REDUCE" for op, _a, _p in pickletools.genops(payload))


# ===========================================================================
# Payload class 4: memory / recursion bomb
# ===========================================================================


def _deep_nested_list_pickle(depth):
    """Raw protocol-4 pickle of a ``depth``-deep right-nested list ``[[[...]]]``.

    Assembled from opcodes so that neither the *build* (``pickle.dump`` would
    recurse and blow the stack at this depth) nor the *load* recurses: pickle's
    loader applies ``APPEND`` iteratively, and the post-load hardening walk uses
    an explicit stack, so a very deep graph exercises the *bounded* paths of
    both without a native recursion limit getting in the way."""
    return (
        pickle.PROTO
        + bytes([4])
        + pickle.EMPTY_LIST * depth
        + pickle.APPEND * (depth - 1)
        + pickle.STOP
    )


def test_deeply_nested_graph_is_bounded(pathsec_sandbox):
    """A very deeply nested list of nodes loads in bounded time and does NOT hang
    or stack-overflow: the loader's APPEND is iterative and the post-load walk is
    iterative with a visited-set, so a 200k-deep graph finishes quickly. Run in a
    subprocess with a wall-clock timeout so a regression to recursion is caught as
    a timeout rather than crashing the runner."""
    path = pathsec_sandbox.root / "nested.pcl"
    with open(path, "wb") as fh:
        fh.write(_deep_nested_list_pickle(200_000))
    child = textwrap.dedent(
        """
        import io, sys
        from nltk.tbl import demo
        with open(sys.argv[1], "rb") as fh:
            data = fh.read()
        obj = demo._load_tbl_model(io.BytesIO(data))
        # walk to the bottom to prove the whole graph really materialised
        depth = 0
        while isinstance(obj, list) and obj:
            obj = obj[0]; depth += 1
        print("LOADED", depth)
        """
    )
    env = os.environ.copy()
    pkg_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(demo.__file__)))
        )
    )
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", child, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert proc.stdout.startswith(
        "LOADED"
    ), f"child failed: {proc.stdout!r} / {proc.stderr!r}"


def test_huge_flat_graph_is_linear(pathsec_sandbox):
    """A large *flat* list of allowlisted-only nodes costs memory linear in the
    pickle size (pickle has no billion-laughs amplification: memo references are
    shared, not copied), so it is bounded. Proven by loading a 500k-element list
    inside the wall-clock-bounded subprocess."""
    n = 500_000
    payload = (
        pickle.PROTO
        + bytes([4])
        + pickle.EMPTY_LIST
        + pickle.MARK
        + pickle.NONE * n
        + pickle.APPENDS
        + pickle.STOP
    )
    path = pathsec_sandbox.root / "flat.pcl"
    with open(path, "wb") as fh:
        fh.write(payload)
    child = textwrap.dedent(
        """
        import io, sys
        from nltk.tbl import demo
        with open(sys.argv[1], "rb") as fh:
            data = fh.read()
        obj = demo._load_tbl_model(io.BytesIO(data))
        print("LOADED", len(obj))
        """
    )
    env = os.environ.copy()
    pkg_root = os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(demo.__file__)))
        )
    )
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, "-c", child, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )
    assert (
        proc.stdout.strip() == f"LOADED {n}"
    ), f"child failed: {proc.stdout!r} / {proc.stderr!r}"


def test_self_referential_graph_terminates(pathsec_sandbox):
    """A self-referential (cyclic) tagger graph must not send the post-load
    hardening walk into an infinite loop; the walk's visited-set makes it
    terminate. A RegexpTagger whose backoff list points back at itself is the
    minimal cycle."""
    t = RegexpTagger.__new__(RegexpTagger)
    t.__dict__["_regexps"] = [(TimedPattern(regex.compile(r".*"), timeout=None), "NN")]
    t.__dict__["_taggers"] = [t, t]  # cycle: references itself
    path = pathsec_sandbox.root / "cyclic.pcl"
    with open(path, "wb") as fh:
        pickle.dump(t, fh, protocol=4)
    with open(path, "rb") as fh:
        loaded = demo._load_tbl_model(fh)  # must terminate
    # and the cyclic tagger's pattern is still capped
    assert loaded._regexps[0][0]._timeout is _UNSET


# ===========================================================================
# Payload class 5: type confusion (globals hidden inside BUILD state)
# ===========================================================================


def test_gadget_hidden_in_build_state_is_refused():
    """A gadget global placed inside a class's BUILD state (not as the top-level
    reduce callable) is still routed through ``find_class`` and refused."""

    def su(s):
        raw = s.encode()
        return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw

    payload = (
        pickle.PROTO
        + bytes([4])
        + su("nltk.tag.brill")
        + su("BrillTagger")
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.EMPTY_DICT
        + su("x")
        + su("os")
        + su("system")
        + pickle.STACK_GLOBAL  # os.system as a *state value*
        + pickle.SETITEM
        + pickle.BUILD
        + pickle.STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        demo._load_tbl_model(io.BytesIO(payload))


def test_type_confused_backoff_is_bounded():
    """A tagger whose backoff is a hostile-but-allowlisted object (a Rule, which
    has no ``.tag``) is not an execution primitive: tagging raises a bounded
    ``AttributeError``, it does not hang or run code."""
    rule = Rule.__new__(Rule)
    rule.__dict__.update(
        original_tag="X", replacement_tag="Y", templateid="0", _conditions=()
    )
    uni = UnigramTagger.__new__(UnigramTagger)
    uni.__dict__["_taggers"] = [uni, rule]  # backoff is a Rule, not a tagger
    uni.__dict__["_context_to_tag"] = {}
    loaded = demo._load_tbl_model(io.BytesIO(pickle.dumps(uni, protocol=4)))
    with pytest.raises((AttributeError, TypeError)):
        loaded.tag(["unseen-word"])  # falls through to the bogus backoff


# ===========================================================================
# Payload class 6: object sentinel abuse
# ===========================================================================


def test_object_sentinel_is_inert():
    """``builtins.object`` reconstructs a bare, state-less instance. It exposes no
    ``__reduce__`` override and no ``__setstate__``/``__setattr__`` hook that a
    BUILD could ride, so it cannot be leveraged into a gadget."""

    def su(s):
        raw = s.encode()
        return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw

    payload = (
        pickle.PROTO
        + bytes([4])
        + su("builtins")
        + su("object")
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.STOP
    )
    obj = demo._load_tbl_model(io.BytesIO(payload))
    assert type(obj) is object
    # A bare object has no instance ``__dict__`` and no ``__setstate__`` hook, so
    # a BUILD has no attribute surface to poison and no setstate to ride.
    assert not hasattr(obj, "__dict__")
    assert not hasattr(object, "__setstate__")


def test_object_sentinel_cannot_take_build_state():
    """A bare ``object()`` has no ``__dict__`` and no ``__setstate__``, so a BUILD
    that tries to give it attacker state fails; it is not a state sink."""

    def su(s):
        raw = s.encode()
        return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw

    payload = (
        pickle.PROTO
        + bytes([4])
        + su("builtins")
        + su("object")
        + pickle.STACK_GLOBAL
        + pickle.EMPTY_TUPLE
        + pickle.NEWOBJ
        + pickle.EMPTY_DICT
        + su("evil")
        + su("payload")
        + pickle.SETITEM
        + pickle.BUILD
        + pickle.STOP
    )
    with pytest.raises((AttributeError, pickle.UnpicklingError, TypeError)):
        demo._load_tbl_model(io.BytesIO(payload))


# ===========================================================================
# Functionality control: a genuinely trained Brill tagger still round-trips
# ===========================================================================


def test_trained_brill_roundtrip_tags_correctly(pathsec_sandbox):
    """End-to-end: really train a rule-bearing Brill tagger over a baseline whose
    backoff is a RegexpTagger, save + reload both through the demo loader inside a
    registered root, and confirm the reloaded taggers tag identically to the
    originals (so the hardening did not change legitimate behaviour)."""
    from nltk.tag import BrillTaggerTrainer
    from nltk.tbl import Template

    train = [
        [("the", "AT"), ("dog", "NN"), ("bit", "VB"), ("the", "AT"), ("man", "NN")],
        [("the", "AT"), ("man", "NN"), ("bit", "NN"), ("the", "AT"), ("dog", "NN")],
    ] * 30
    backoff = RegexpTagger(
        [(r".*s$", "NNS"), (r".*", "NN")], backoff=DefaultTagger("NN")
    )
    baseline = UnigramTagger(train, backoff=backoff)
    templates = [
        Template(Pos([-1])),
        Template(Word([0])),
        Template(Pos([-1]), Word([0])),
    ]
    brill = BrillTaggerTrainer(baseline, templates, trace=0).train(train, max_rules=10)

    sent = ["the", "dog", "bit", "the", "man"]
    expected_baseline = baseline.tag(sent)
    expected_brill = brill.tag(sent)

    cache = pathsec_sandbox.root / "baseline.pcl"
    serial = pathsec_sandbox.root / "brill.pcl"
    with open(cache, "wb") as fh:
        pickle.dump(baseline, fh)
    with open(serial, "wb") as fh:
        pickle.dump(brill, fh)

    with open(cache, "rb") as fh:
        reloaded_baseline = demo._load_tbl_model(fh)
    with open(serial, "rb") as fh:
        reloaded_brill = demo._load_tbl_model(fh)

    assert reloaded_baseline.tag(sent) == expected_baseline
    assert isinstance(reloaded_brill, BrillTagger)
    assert reloaded_brill.tag(sent) == expected_brill
    # the reconstructed RegexpTagger backoff is bounded
    reg = reloaded_baseline._taggers[1]
    assert isinstance(reg, RegexpTagger)
    for pattern, _tag in reg._regexps:
        assert isinstance(pattern, TimedPattern) and pattern._timeout is _UNSET

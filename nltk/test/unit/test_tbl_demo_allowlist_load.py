# Natural Language Toolkit: allowlist unpickler tests for nltk.tbl.demo
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Deserialization hardening tests for ``nltk.tbl.demo`` (GHSA-8mgp umbrella).
The two model files ``postag`` reads back used the warn-only loader; these prove
the allowlisting loader refuses gadgets yet still round-trips a real tagger."""

import io
import os
import pickle

import pytest

from nltk.tag import DefaultTagger, RegexpTagger
from nltk.tbl import demo

# A tiny synthetic tagged corpus so postag() never needs the treebank; postag
# skips corpus loading when tagged_data is supplied. Every word is seen in
# training, so reloaded taggers tag the demo sentence without an unseen path.
TINY_TAGGED = [
    [("the", "AT"), ("dog", "NN"), ("runs", "VBZ")],
    [("a", "AT"), ("cat", "NN"), ("sleeps", "VBZ")],
] * 10

DEMO_SENT = ["the", "dog", "runs"]


# ---------------------------------------------------------------------------
# Hand-assembled pickle builders. find_class runs at STACK_GLOBAL, before REDUCE.
# ---------------------------------------------------------------------------


def _su(s: str) -> bytes:
    b = s.encode()
    return pickle.SHORT_BINUNICODE + bytes([len(b)]) + b


def _reduce_global_pickle(module: str, name: str, arg: str) -> bytes:
    """A protocol 4 pickle equivalent to ``REDUCE(<module>.<name>, (arg,))``."""
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
    """A protocol 4 pickle that only resolves ``<module>.<name>`` and returns it."""
    return (
        pickle.PROTO
        + bytes([4])
        + _su(module)
        + _su(name)
        + pickle.STACK_GLOBAL
        + pickle.STOP
    )


def _exec_write_sentinel_pickle(path: str) -> bytes:
    """A reduce gadget that, if executed, creates ``path`` on any platform.
    ``exec`` of ``open(path, "w").close()`` writes an empty file with no shell;
    the allowlisting unpickler refuses ``builtins.exec`` before it runs."""
    return _reduce_global_pickle("builtins", "exec", f"open({path!r}, 'w').close()")


# Dangerous globals that must never be reconstructable from an untrusted tbl model:
# code exec, subprocess, import, nested unpickle, scientific-stack file/network
# sinks. Every one is on picklesec's denylist or absent from the tbl allowlist.
_GADGETS = [
    ("os", "system"),
    ("subprocess", "Popen"),
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("builtins", "__import__"),
    ("importlib", "import_module"),
    ("pickle", "Unpickler"),
    ("scipy.io", "mmwrite"),
    ("sklearn.datasets", "fetch_openml"),
    ("numpy", "load"),
]

# Primitives that would be catastrophic if any of them leaked into the allowlist.
_FORBIDDEN_IN_ALLOWLIST = {
    ("os", "system"),
    ("posix", "system"),
    ("nt", "system"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("builtins", "eval"),
    ("builtins", "exec"),
    ("builtins", "__import__"),
    ("builtins", "compile"),
    ("importlib", "import_module"),
    ("pickle", "Unpickler"),
    ("marshal", "loads"),
}


# ---------------------------------------------------------------------------
# The allowlist itself carries no execution primitive
# ---------------------------------------------------------------------------


def test_allowlist_contains_no_exec_primitive():
    allow = set(demo._TBL_MODEL_ALLOWED_GLOBALS)
    leaked = allow & _FORBIDDEN_IN_ALLOWLIST
    assert not leaked, f"execution primitive present in tbl allowlist: {leaked}"
    # No entry may live in a code exec / subprocess / import / os module either.
    banned_modules = {
        "os",
        "posix",
        "nt",
        "subprocess",
        "builtins",
        "importlib",
        "pickle",
        "marshal",
        "ctypes",
        "sys",
    }
    for module, name in allow:
        assert (
            module.split(".")[0] not in banned_modules
        ), f"tbl allowlist names a dangerous module: {module}.{name}"


# ---------------------------------------------------------------------------
# Teeth: every gadget is refused by the demo loader
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module,name", _GADGETS)
def test_reduce_gadget_refused(module, name):
    payload = _reduce_global_pickle(module, name, "echo tbl-demo-rce")
    with pytest.raises(pickle.UnpicklingError):
        demo._load_tbl_model(io.BytesIO(payload))


@pytest.mark.parametrize("module,name", _GADGETS)
def test_bare_gadget_resolution_refused(module, name):
    payload = _bare_global_pickle(module, name)
    with pytest.raises(pickle.UnpicklingError):
        demo._load_tbl_model(io.BytesIO(payload))


def test_dotted_name_traversal_refused():
    # GHSA-4489: a dotted name would getattr-chain to os.system under a broad
    # allow. The tbl allowlist has no broad namespace, but the base guard is
    # pinned here too.
    payload = _reduce_global_pickle("nltk.tag.brill", "os.system", "echo nope")
    with pytest.raises(pickle.UnpicklingError):
        demo._load_tbl_model(io.BytesIO(payload))


def test_warn_only_executes_gadget_but_allowlist_refuses(pathsec_sandbox):
    """The before/after proof: the old warn-only loader runs the gadget, the new
    allowlisting loader refuses it, and the sentinel file is never created."""
    from nltk.picklesec import pickle_load

    sentinel = pathsec_sandbox.root / "PWNED_warn_only"
    payload = _exec_write_sentinel_pickle(str(sentinel))

    # BEFORE: the warn-only unpickler (what demo.py used on develop) executes it.
    if sentinel.exists():
        sentinel.unlink()
    with pytest.warns(RuntimeWarning):
        pickle_load(io.BytesIO(payload))
    assert sentinel.exists(), "warn-only loader did not execute the gadget"
    sentinel.unlink()

    # AFTER: the demo loader refuses before the gadget runs.
    with pytest.raises(pickle.UnpicklingError):
        demo._load_tbl_model(io.BytesIO(payload))
    assert not sentinel.exists(), "allowlist loader executed the gadget (RCE)"


def test_planted_gadget_in_data_root_refused_via_postag(pathsec_sandbox):
    """A gadget planted at the ``cache_baseline_tagger`` path inside a data root is
    refused by the real ``postag`` reload branch (the file pre-exists, so postag
    skips training and loads it), and nothing runs."""
    root = pathsec_sandbox.root
    sentinel = root / "PWNED_planted"
    planted = root / "planted_baseline.pcl"
    with open(planted, "wb") as fh:
        fh.write(_exec_write_sentinel_pickle(str(sentinel)))

    if sentinel.exists():
        sentinel.unlink()
    with pytest.raises(pickle.UnpicklingError):
        demo.postag(
            tagged_data=list(TINY_TAGGED),
            num_sents=20,
            trace=0,
            max_rules=5,
            cache_baseline_tagger=str(planted),
        )
    assert not sentinel.exists(), "planted gadget executed through postag (RCE)"


# ---------------------------------------------------------------------------
# Functionality: a real trained Brill tagger + baseline still round-trip
# ---------------------------------------------------------------------------


def _assert_tagged_sane(tagged):
    assert isinstance(tagged, list) and len(tagged) == len(DEMO_SENT)
    for (word, tag), expected in zip(tagged, DEMO_SENT):
        assert word == expected
        assert isinstance(tag, str) and tag


def test_legit_brill_roundtrip_default_backoff(pathsec_sandbox):
    """postag() with a DefaultTagger backoff trains, caches, serializes and reloads
    a Brill tagger through the new loader; both reloaded taggers tag. Exercises the
    BrillTagger, UnigramTagger, DefaultTagger, Word, Pos and Rule allowlist entries."""
    root = pathsec_sandbox.root
    cache = root / "baseline_default.pcl"
    serial = root / "tagger_default.pcl"

    demo.postag(
        tagged_data=list(TINY_TAGGED),
        num_sents=20,
        trace=0,
        max_rules=5,
        baseline_backoff_tagger=DefaultTagger("NN"),
        cache_baseline_tagger=str(cache),
        serialize_output=str(serial),
    )
    assert cache.exists() and serial.exists()

    # Independently reload each file through the exact demo loader and tag.
    from nltk.tag.brill import BrillTagger

    with open(serial, "rb") as fh:
        brill = demo._load_tbl_model(fh)
    assert isinstance(brill, BrillTagger)
    _assert_tagged_sane(brill.tag(DEMO_SENT))

    with open(cache, "rb") as fh:
        baseline = demo._load_tbl_model(fh)
    _assert_tagged_sane(baseline.tag(DEMO_SENT))


def test_legit_brill_roundtrip_regexp_backoff(pathsec_sandbox):
    """postag() with a RegexpTagger backoff round-trips through the new loader; this
    is what pulls in the TimedPattern wrapper, its ``regex._regex.compile`` reduce
    and the inert ``object`` timeout sentinel, proving the allowlist accepts them."""
    root = pathsec_sandbox.root
    cache = root / "baseline_regexp.pcl"
    serial = root / "tagger_regexp.pcl"

    demo.postag(
        tagged_data=list(TINY_TAGGED),
        num_sents=20,
        trace=0,
        max_rules=5,
        baseline_backoff_tagger=RegexpTagger([(r".*", "ZZ")]),
        cache_baseline_tagger=str(cache),
        serialize_output=str(serial),
    )
    assert cache.exists() and serial.exists()

    from nltk.tag.brill import BrillTagger

    with open(serial, "rb") as fh:
        brill = demo._load_tbl_model(fh)
    assert isinstance(brill, BrillTagger)
    _assert_tagged_sane(brill.tag(DEMO_SENT))
    # The reconstructed baseline really does carry a RegexpTagger backoff, i.e.
    # the TimedPattern / regex / object globals were accepted, not stripped.
    assert isinstance(brill._initial_tagger.backoff, RegexpTagger)
    assert brill._initial_tagger.backoff._regexps


def test_allowlist_accepts_regexp_object_sentinel(pathsec_sandbox):
    """A bare RegexpTagger pickle (embedding the ``object`` timeout sentinel,
    ``TimedPattern`` and ``regex._regex.compile``) loads through the demo loader
    and its patterns reconstruct. Tagging is skipped: a redos round-trip limitation."""
    from nltk.redos import TimedPattern

    root = pathsec_sandbox.root
    tagger = RegexpTagger([(r"^-?[0-9]+$", "CD"), (r".*", "NN")])
    path = root / "regexp_tagger.pcl"
    with open(path, "wb") as fh:
        pickle.dump(tagger, fh)
    with open(path, "rb") as fh:
        reloaded = demo._load_tbl_model(fh)
    assert isinstance(reloaded, RegexpTagger)
    assert len(reloaded._regexps) == 2
    for compiled, tag in reloaded._regexps:
        assert isinstance(compiled, TimedPattern)
        assert isinstance(tag, str)

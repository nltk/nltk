# Natural Language Toolkit: picklesec bytes loader and round trip
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``picklesec.pickle_loads`` and ``picklesec.roundtrip`` are conveniences, not
a second loader: both must refuse exactly what ``allowlisted_pickle_load`` does.

They exist so the howtos can show a pickle round trip in one call with the
allowlist in plain sight. Each attack below is first shown to be live under a
plain ``pickle.loads``, so a helper that fell back to an unrestricted load, or
widened the allowlist it was given, fails here.
"""

import copyreg
import functools
import os
import pickle
import posixpath

import pytest

from nltk import picklesec
from nltk.collections import Trie
from nltk.grammar import Production
from nltk.probability import ConditionalFreqDist, FreqDist, MLEProbDist
from nltk.tokenize import MWETokenizer
from nltk.tree import ParentedTree, Tree


class _MakeDir:
    """A REDUCE gadget: unpickling it calls ``os.mkdir(path)``."""

    def __init__(self, path):
        self.path = path

    def __reduce__(self):
        return (os.mkdir, (self.path,))


def _stack_global(module, name):
    """A protocol 4 pickle that only resolves the global ``module.name``."""
    m, n = module.encode(), name.encode()
    return (
        b"\x80\x04\x8c" + bytes([len(m)]) + m + b"\x8c" + bytes([len(n)]) + n + b"\x93."
    )


def _cfd():
    cfd = ConditionalFreqDist()
    cfd["foo"]["hello"] += 2
    cfd["bar"]["hello"] += 1
    return cfd


def _tokenize(tokenizer):
    return tokenizer.tokenize("An hors d'oeuvre tonight, sir?".split())


# (object, allowlist, how to compare the copy with the original)
_REAL_OBJECTS = {
    "FreqDist": (FreqDist("abracadabra"), ["nltk.probability"], None),
    "ConditionalFreqDist": (_cfd(), ["nltk.probability"], None),
    "MLEProbDist": (
        MLEProbDist(FreqDist("abracadabra")),
        ["nltk.probability"],
        lambda pd: sorted(pd.samples()),
    ),
    "Tree": (Tree.fromstring("(S (NP x) (VP y))"), ["nltk.tree"], None),
    "ParentedTree": (
        ParentedTree.fromstring("(S (NN x) (NP x) (NN x))"),
        ["nltk.tree"],
        str,
    ),
    "Trie": (Trie(["a", "ab"]), ["nltk.collections"], None),
    "MWETokenizer": (
        MWETokenizer([("hors", "d'oeuvre")], separator="+"),
        ["nltk.tokenize.mwe", "nltk.collections"],
        _tokenize,
    ),
    "Production": (Production("S", ["NP", "VP"]), ["nltk.grammar"], hash),
}


@pytest.mark.parametrize("kind", sorted(_REAL_OBJECTS))
def test_real_objects_come_back_equal(kind):
    obj, allowed, key = _REAL_OBJECTS[kind]
    key = key or (lambda x: x)
    data = picklesec.pickle_dumps(obj)
    loaded = picklesec.pickle_loads(data, allowed_modules=allowed)
    copied = picklesec.roundtrip(obj, allowed_modules=allowed)
    assert key(loaded) == key(obj)
    assert key(copied) == key(obj)
    assert copied is not obj


def test_the_partial_idiom_of_the_howtos():
    roundtrip = functools.partial(
        picklesec.roundtrip, allowed_modules=["nltk.probability"]
    )
    fd = FreqDist("abracadabra")
    assert roundtrip(fd) == fd
    assert roundtrip(_cfd()) == _cfd()


def test_plain_data_needs_no_allowlist():
    data = [1, "a", {"b": 2.0}, (None, True), b"\x00"]
    assert picklesec.pickle_loads(picklesec.pickle_dumps(data)) == data
    assert picklesec.roundtrip(data) == data


def test_no_allowlist_rebuilds_no_class():
    with pytest.raises(pickle.UnpicklingError, match="not in the pickle allowlist"):
        picklesec.roundtrip(FreqDist("ab"))


def test_a_class_from_an_unlisted_module_is_refused():
    with pytest.raises(pickle.UnpicklingError, match="not in the pickle allowlist"):
        picklesec.roundtrip(FreqDist("ab"), allowed_modules=["nltk.tree"])
    data = picklesec.pickle_dumps(Tree.fromstring("(S x)"))
    with pytest.raises(pickle.UnpicklingError, match="not in the pickle allowlist"):
        picklesec.pickle_loads(data, allowed_modules=["nltk.probability"])


def test_a_reduce_gadget_is_refused_not_run(tmp_path):
    marker = tmp_path / "gadget_ran"
    payload = picklesec.pickle_dumps(_MakeDir(str(marker)))
    pickle.loads(payload)  # the control: a plain load runs the gadget
    assert marker.is_dir()
    marker.rmdir()
    with pytest.raises(pickle.UnpicklingError, match="denied module"):
        picklesec.pickle_loads(payload, allowed_modules=["nltk.probability"])
    with pytest.raises(pickle.UnpicklingError, match="denied module"):
        picklesec.roundtrip(_MakeDir(str(marker)), allowed_modules=["nltk"])
    assert not marker.exists()


@pytest.mark.parametrize(
    "allowlist",
    [
        {"allowed_modules": ["os"]},
        {"allowed_modules": ["subprocess"]},
        {"allowed_modules": ["builtins"]},
        {"allowed_globals": [("builtins", "eval")]},
        {"allowed_globals": [("posix", "system")]},
    ],
    ids=["os", "subprocess", "builtins", "eval", "posix.system"],
)
def test_a_denied_module_cannot_be_allowlisted(allowlist):
    """The helpers pass the caller's allowlist on unchanged, so the loader's
    up-front validation still refuses an entry naming a denied module."""
    data = picklesec.pickle_dumps([1])
    with pytest.raises(pickle.UnpicklingError):
        picklesec.pickle_loads(data, **allowlist)
    with pytest.raises(pickle.UnpicklingError):
        picklesec.roundtrip([1], **allowlist)


def test_an_in_namespace_gadget_is_refused_under_a_broad_allow():
    """Allowing all of ``nltk`` still does not reach ``nltk.internals``."""
    payload = _stack_global("nltk.internals", "java")
    with pytest.raises(pickle.UnpicklingError, match="denied module"):
        picklesec.pickle_loads(payload, allowed_modules=["nltk"])


def test_attribute_traversal_is_refused():
    """GHSA-4489: protocol 4 resolves a dotted name by getattr chaining."""
    payload = _stack_global("nltk.probability", "FreqDist.copy")
    assert pickle.loads(payload) is FreqDist.copy  # the control: it is live
    with pytest.raises(pickle.UnpicklingError, match="dotted name"):
        picklesec.pickle_loads(payload, allowed_modules=["nltk.probability"])


def test_an_extension_opcode_is_refused():
    """EXT1 resolves through copyreg's registry without find_class."""
    code = 241  # unregistered; the EXT tests in the allowlist suite use 173
    copyreg.add_extension("posixpath", "join", code)
    try:
        payload = b"\x80\x02" + pickle.EXT1 + bytes([code]) + pickle.STOP
        assert pickle.loads(payload) is posixpath.join  # the control: it is live
        with pytest.raises(pickle.UnpicklingError, match="extension-registry"):
            picklesec.pickle_loads(payload, allowed_modules=["nltk"])
    finally:
        copyreg.remove_extension("posixpath", "join", code)


def test_sanitize_is_applied_to_the_result():
    def refuse_freqdists(node):
        if isinstance(node, FreqDist):
            raise pickle.UnpicklingError("FreqDist refused by the visit")

    data = picklesec.pickle_dumps([FreqDist("ab")])
    with pytest.raises(pickle.UnpicklingError, match="refused by the visit"):
        picklesec.pickle_loads(
            data, allowed_modules=["nltk.probability"], sanitize=refuse_freqdists
        )

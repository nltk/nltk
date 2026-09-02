# Natural Language Toolkit: decorators eval-injection guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""nltk.decorators builds a signature-preserving wrapper by interpolating a
function's signature into a ``lambda`` and ``eval``-ing it. The eval is kept
because it is what makes ``inspect.getfullargspec`` report the true signature on
every supported Python (older versions ignore ``__signature__``). These tests
pin the identifier-only guard that runs before the eval, so a crafted signature
can never turn it into a code-execution primitive (CVE-2026-14727), and that
signature preservation still works."""

import inspect

import pytest

from nltk.decorators import _assert_safe_signature, decorator, getinfo, new_wrapper


def test_legit_decoration_preserves_signature_and_calls():
    @decorator
    def trace(f, *args, **kw):
        return f(*args, **kw)

    @trace
    def add(a, b=2, *rest, **kw):
        return a + b

    assert add(3) == 5 and add(3, 4) == 7
    assert add.__name__ == "add"
    assert str(inspect.signature(add)) == "(a, b=2, *rest, **kw)"
    # getfullargspec (older Python relies on the real signature, not __signature__)
    spec = inspect.getfullargspec(add)
    assert spec.args == ["a", "b"] and spec.varargs == "rest" and spec.varkw == "kw"


@pytest.mark.parametrize(
    "hostile",
    [
        "x=__import__('os').system('echo pwned')",  # executes as a lambda default
        "__import__('os').system('id')",
        "x: int",  # annotation form
        "x)+__import__('os').system('id')+(",
        "a; b",
        "a=(lambda: 1)()",
    ],
)
def test_hostile_signatures_are_refused(hostile):
    with pytest.raises(ValueError, match="non-identifier signature"):
        _assert_safe_signature(hostile)


def test_star_and_plain_params_are_allowed():
    for sig in ("self, x, y, *args, **kw", "*a", "**kw", "a, *b, **c", ""):
        _assert_safe_signature(sig)  # must not raise


def test_new_wrapper_refuses_a_crafted_signature_infodict():
    # An attacker able to hand new_wrapper a crafted infodict (the eval sink) is
    # stopped before the eval; no code runs.
    infodict = {
        "signature": "x=__import__('os').system('echo should_not_run')",
        "argnames": ["x"],
        "name": "f",
        "doc": None,
        "module": "m",
        "dict": {},
        "defaults": (),
        "fullsignature": None,
    }
    with pytest.raises(ValueError, match="non-identifier signature"):
        new_wrapper(lambda *a, **k: None, infodict)


def test_new_wrapper_from_dict_model_preserves_real_signature():
    info = getinfo(lambda x, y=1: None)
    wrapped = new_wrapper(lambda *a, **k: "ok", info)
    assert wrapped(1) == "ok" and wrapped(1, 2) == "ok"
    assert str(inspect.signature(wrapped)) == "(x, y=1)"


def test_memoize_decorator_still_works():
    from nltk.decorators import memoize

    calls = []

    @memoize
    def slow(n):
        calls.append(n)
        return n * n

    assert slow(4) == 16 and slow(4) == 16
    assert calls == [4]

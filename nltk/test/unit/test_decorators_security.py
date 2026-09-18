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

from nltk.decorators import (
    _assert_safe_signature,
    decorator,
    getinfo,
    new_wrapper,
)


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
        "a=1",  # any default at all
        "a.b",  # attribute access
        "a[0]",  # subscript
        "a+b",  # operator
        "a\nb",  # newline (would make eval src a SyntaxError, refused cleanly)
        "a\tb",  # tab is not an allowed separator
        "lambda: 1",
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


def test_str_subclass_signature_cannot_inject_via_format():
    # A str subclass can pass the regex on its underlying characters yet override
    # __format__ to emit arbitrary source when interpolated into the eval. The
    # exact-str check refuses it before the eval runs (CVE-2026-14727).
    import os

    class EvilSig(str):
        def __format__(self, spec):
            return "a=__import__('os').environ.setdefault('NLTK_DEC_PWNED', '1')"

    os.environ.pop("NLTK_DEC_PWNED", None)
    info = getinfo(lambda a: None)
    info["signature"] = EvilSig("a")
    with pytest.raises(ValueError, match="non-str signature"):
        new_wrapper(lambda *a, **k: None, info)
    assert os.environ.get("NLTK_DEC_PWNED") is None  # no injected code ran


def test_crafted_fullsignature_parameter_name_cannot_inject():
    # The call args are built from parameter names; a duck-typed Signature whose
    # "parameter" is not a real inspect.Parameter (name is an expression) must be
    # refused before it reaches the eval body.
    class FakeParam:
        def __init__(self, name):
            self.name = name
            self.kind = inspect.Parameter.POSITIONAL_OR_KEYWORD

    class FakeSig:
        def __init__(self, names):
            self._p = {n: FakeParam(n) for n in names}

        @property
        def parameters(self):
            return self._p

    info = getinfo(lambda a: None)
    info["fullsignature"] = FakeSig(["a, __import__('os').system('echo pwned')"])
    with pytest.raises(ValueError, match="non-identifier parameter name"):
        new_wrapper(lambda *a, **k: None, info)


def test_keyword_only_and_positional_only_signatures_work():
    @decorator
    def trace(f, *a, **k):
        return f(*a, **k)

    @trace
    def f(a, *, b=5):  # keyword-only with a default
        return (a, b)

    @trace
    def g(a, /, b, *, c):  # positional-only + keyword-only
        return (a, b, c)

    assert f(1) == (1, 5) and f(1, b=9) == (1, 9)  # kw-only default preserved
    assert g(1, 2, c=3) == (1, 2, 3)


def test_unicode_parameter_name_is_accepted():
    # A valid Python identifier with non-ASCII letters must still decorate.
    @decorator
    def trace(f, *a, **k):
        return f(*a, **k)

    ns = {}
    exec("def h(é): return é", ns)  # def h(e-acute): ...
    assert trace(ns["h"])(42) == 42


def test_legacy_model_dict_without_fullsignature_still_works():
    wrapped = new_wrapper(
        lambda *a, **k: "ok",
        {
            "signature": "a, b",
            "argnames": ["a", "b"],
            "name": "f",
            "doc": None,
            "module": "m",
            "dict": {},
            "defaults": None,
        },
    )
    assert wrapped(1, 2) == "ok"

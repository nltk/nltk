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

import ast
import inspect
import os
import subprocess
import sys
import textwrap

import pytest

from nltk import decorators as _decorators
from nltk.decorators import (
    _assert_safe_signature,
    decorator,
    getinfo,
    new_wrapper,
)
from nltk.test.unit import timing


class _FakeSig:
    """A duck-typed Signature whose parameters are whatever the test hands in."""

    def __init__(self, params):
        self._p = {p.name: p for p in params}

    @property
    def parameters(self):
        return self._p


def _passthrough(func, *a, **k):
    return func(*a, **k)


def _infodict(signature, fullsignature=None):
    return {
        "signature": signature,
        "argnames": [],
        "name": "victim",
        "doc": None,
        "module": "m",
        "dict": {},
        "defaults": (),
        "fullsignature": fullsignature,
    }


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


# === The four scratch-probe bypasses, pinned through the real eval sink with a
# canary file, so a regression that only breaks an earlier assertion (not the
# actual code-execution outcome) still fails here. ===


def test_lying_signature_format_cannot_inject_via_top_level_signature(tmp_path):
    marker = tmp_path / "pwned1"

    class EvilSig(str):
        def __format__(self, spec):
            return f"x=open({str(marker)!r}, 'w').close()"

    infodict = getinfo(lambda x: None)
    infodict["signature"] = EvilSig("x")
    with pytest.raises(ValueError, match="non-str signature"):
        new_wrapper(lambda *a, **k: None, infodict)
    assert not marker.exists()


def test_inspect_parameter_subclass_with_lying_name_property_is_refused(tmp_path):
    # A genuine inspect.Parameter SUBCLASS (type(p) is inspect.Parameter is
    # False for it, though isinstance is True) whose .name PROPERTY returns a
    # lying str subclass, reached through the fullsignature channel.
    marker = tmp_path / "pwned2"

    class LyingName(str):
        def __format__(self, spec):
            return f"y=open({str(marker)!r}, 'w').close()"

    class EvilParam(inspect.Parameter):
        @property
        def name(self):
            return LyingName("y")

    info = getinfo(lambda y: None)
    info["fullsignature"] = _FakeSig(
        [EvilParam("y", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
    )
    with pytest.raises(ValueError, match="non-standard or non-identifier"):
        new_wrapper(lambda *a, **k: None, info)
    assert not marker.exists()


@pytest.mark.parametrize("reserved_name", sorted(_decorators._RESERVED_NAMES))
@pytest.mark.parametrize(
    "shape",
    [
        "{name}",
        "a, {name}",
        "a, *, {name}=None",
        "*{name}",
        "**{name}",
        "{name}, /, a",
    ],
)
def test_reserved_parameter_of_any_kind_cannot_shadow_a_wrapper_global(
    reserved_name, shape
):
    # A parameter LITERALLY named _call_/_func_/_wrapper_ would shadow the
    # wrapper's own dispatcher global inside the generated lambda; every kind
    # is refused at BOTH eval sinks, whichever global that sink happens to use.
    ns = {}
    exec(  # bare-exec ok: builds the victim function with the reserved name
        f"def victim({shape.format(name=reserved_name)}):\n    return 1", ns
    )
    with pytest.raises(ValueError, match="reserved argument name"):
        decorator(_passthrough)(ns["victim"])
    with pytest.raises(ValueError, match="reserved argument name"):
        new_wrapper(lambda *a, **k: None, ns["victim"])


def test_no_guard_on_the_eval_path_is_an_assert():
    # `assert` is stripped by `python -O`; every guard between a signature and
    # the eval must be a real `raise`, or -O silently reopens CVE-2026-14727.
    for guard in (
        _decorators._fenced_parameters,
        _decorators._assert_safe_signature,
        _decorators._refuse_reserved,
        _decorators._call_arguments,
        _decorators._call_arguments_from_signature,
        _decorators.new_wrapper,
        _decorators.decorator,
    ):
        tree = ast.parse(textwrap.dedent(inspect.getsource(guard)))
        assert not [n for n in ast.walk(tree) if isinstance(n, ast.Assert)], guard


def test_guards_hold_under_python_O(tmp_path):
    # The same four bypasses, run in a child interpreter started with -O, each
    # judged by the canary the injected source would have written.
    marker = tmp_path / "pwned_O"
    script = textwrap.dedent(
        """
        import inspect, os, sys
        from nltk.decorators import decorator, getinfo, new_wrapper
        marker = sys.argv[1]
        assert marker == "stripped", "asserts are live: this is not -O"

        class FakeSig:
            def __init__(self, params):
                self._p = {p.name: p for p in params}

            @property
            def parameters(self):
                return self._p

        class EvilSig(str):
            def __format__(self, spec):
                return "x=open(%r, 'w').close()" % marker

        class LyingName(str):
            def __format__(self, spec):
                return "y=open(%r, 'w').close()" % marker

        class EvilParam(inspect.Parameter):
            @property
            def name(self):
                return LyingName("y")

        failures = []
        info = getinfo(lambda x: None)
        info["signature"] = EvilSig("x")
        try:
            new_wrapper(lambda *a, **k: None, info)
            failures.append("format")
        except ValueError:
            pass
        info = getinfo(lambda y: None)
        info["fullsignature"] = FakeSig(
            [EvilParam("y", inspect.Parameter.POSITIONAL_OR_KEYWORD)]
        )
        try:
            new_wrapper(lambda *a, **k: None, info)
            failures.append("param-subclass")
        except ValueError:
            pass
        for reserved in ("_call_", "_func_", "_wrapper_"):
            ns = {}
            exec("def victim(a, *, %s=None):\\n    return a" % reserved, ns)
            for sink in (
                lambda f: decorator(lambda func, *a, **k: func(*a, **k))(f),
                lambda f: new_wrapper(lambda *a, **k: None, f),
            ):
                try:
                    sink(ns["victim"])
                    failures.append(reserved)
                except ValueError:
                    pass
        fullwidth = "_" + "".join(
            chr(c) for c in (0xFF57, 0xFF52, 0xFF41, 0xFF50, 0xFF50, 0xFF45, 0xFF52)
        ) + "_"
        try:
            new_wrapper(
                lambda *a, **k: None,
                {
                    "signature": "a, *, " + fullwidth,
                    "argnames": ["a", fullwidth],
                    "name": "v", "doc": None, "module": "m", "dict": {},
                    "defaults": (), "fullsignature": None,
                },
            )
            failures.append("fullwidth")
        except ValueError:
            pass
        print("FAILURES:" + ",".join(failures))
        print("CANARY:" + str(os.path.exists(marker)))
        """
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = os.path.dirname(os.path.dirname(_decorators.__file__))
    proc = subprocess.run(
        [sys.executable, "-O", "-c", script, str(marker)],
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert "FAILURES:\n" in proc.stdout, proc.stdout
    assert "CANARY:False" in proc.stdout, proc.stdout
    assert not marker.exists()


def test_fullwidth_nfkc_spelling_of_reserved_name_is_refused():
    # A genuine inspect.Parameter, built directly (bypassing the parser's own
    # NFKC normalisation that a real `def` statement applies), named with
    # fullwidth letters that NFKC-normalise to "_wrapper_".
    fullwidth_wrapper = (
        "_"
        + "".join(
            chr(c) for c in (0xFF57, 0xFF52, 0xFF41, 0xFF50, 0xFF50, 0xFF45, 0xFF52)
        )
        + "_"
    )
    assert fullwidth_wrapper.isidentifier()
    infodict = _infodict(
        f"a, *, {fullwidth_wrapper}",
        _FakeSig(
            [
                inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
                inspect.Parameter(
                    fullwidth_wrapper, inspect.Parameter.KEYWORD_ONLY, default=None
                ),
            ]
        ),
    )
    with pytest.raises(ValueError, match="non-NFKC-normalised"):
        new_wrapper(lambda *a, **k: None, infodict)


def test_fullwidth_spelling_of_a_keyword_is_refused():
    # NFKC turns fullwidth "lambda" into the keyword; it must not be a name.
    fullwidth_lambda = "".join(
        chr(c) for c in (0xFF4C, 0xFF41, 0xFF4D, 0xFF42, 0xFF44, 0xFF41)
    )
    assert fullwidth_lambda.isidentifier()
    with pytest.raises(ValueError, match="non-NFKC-normalised"):
        _assert_safe_signature(fullwidth_lambda)


# === Further forged-signature forms ===


@pytest.mark.parametrize(
    "name",
    ["match", "case", "type", "_", "__class__", "__import__", "__builtins__"],
)
def test_soft_keywords_and_dunder_names_are_ordinary_parameters(name):
    # Not keywords, so legal parameter names; inside the lambda they are
    # locals that cannot reach the wrapper's globals or builtins lookup.
    ns = {}
    exec(  # bare-exec ok: builds a victim with the soft-keyword/dunder name
        f"def victim({name}):\n    return {name}", ns
    )
    wrapped = decorator(_passthrough)(ns["victim"])
    assert wrapped(7) == 7
    assert list(inspect.signature(wrapped).parameters) == [name]


def test_very_long_name_and_many_parameters_stay_bounded():
    long_name = "x" * 100000
    many = ", ".join(f"p{i}" for i in range(5000))
    with timing.budget(10.0):
        ns = {}
        exec(  # bare-exec ok: builds the two victims
            f"def long_one({long_name}):\n    return {long_name}\n"
            f"def many_one({many}):\n    return p0 + p4999",
            ns,
        )
        assert decorator(_passthrough)(ns["long_one"])(3) == 3
        assert decorator(_passthrough)(ns["many_one"])(*range(5000)) == 4999


def test_signature_object_lying_about_its_length_is_refused():
    class LyingMap(dict):
        def __len__(self):
            return 1

    class LyingLenSig:
        def __init__(self, params):
            self._p = LyingMap({p.name: p for p in params})

        @property
        def parameters(self):
            return self._p

    info = getinfo(lambda a: None)
    info["fullsignature"] = LyingLenSig(
        [
            inspect.Parameter("a", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("b", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ]
    )
    with pytest.raises(ValueError, match="does not match the fenced signature"):
        new_wrapper(lambda *a, **k: None, info)


@pytest.mark.parametrize(
    "kinds",
    [
        (inspect.Parameter.VAR_KEYWORD, inspect.Parameter.POSITIONAL_OR_KEYWORD),
        (inspect.Parameter.KEYWORD_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD),
        (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.VAR_POSITIONAL),
        (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_ONLY),
    ],
)
def test_signature_object_lying_about_a_kind_is_refused_before_the_eval(kinds):
    # The fenced string "a, b" says both are positional-or-keyword; a Signature
    # claiming otherwise must be refused with ValueError, never let the eval
    # raise SyntaxError or build a call the fenced signature did not describe.
    info = getinfo(lambda a, b: None)
    info["fullsignature"] = _FakeSig(
        [inspect.Parameter("a", kinds[0]), inspect.Parameter("b", kinds[1])]
    )
    with pytest.raises(ValueError, match="disagrees with the fenced signature"):
        new_wrapper(lambda *a, **k: None, info)


def test_forged_wrapped_and_signature_attributes_cannot_inject(tmp_path):
    # inspect.signature follows __wrapped__ and honours __signature__; neither
    # channel may carry text of its own into the eval.
    marker = tmp_path / "pwned3"

    class LyingName(str):
        def __format__(self, spec):
            return f"q=open({str(marker)!r}, 'w').close()"

    class EvilParam(inspect.Parameter):
        @property
        def name(self):
            return LyingName("q")

    class EvilSignature(inspect.Signature):
        @property
        def parameters(self):
            return {"q": EvilParam("q", inspect.Parameter.POSITIONAL_OR_KEYWORD)}

    def target(evil_a, evil_b=1):
        return None

    target.__signature__ = EvilSignature()

    def victim(a):
        return a

    victim.__wrapped__ = target
    with pytest.raises(ValueError, match="non-standard or non-identifier"):
        decorator(_passthrough)(victim)
    assert not marker.exists()

    del target.__signature__
    wrapped = decorator(_passthrough)(victim)
    # only the followed function's own plain identifiers reach the wrapper
    assert list(inspect.signature(wrapped).parameters) == ["evil_a", "evil_b"]
    assert not marker.exists()


def test_radd_str_subclass_name_cannot_inject_through_legacysignature(tmp_path):
    # __legacysignature builds "*" + p.name; a str subclass whose __radd__
    # returns arbitrary text is caught by the fence on the final characters.
    marker = tmp_path / "pwned4"

    class Radd(str):
        def __radd__(self, other):
            return f"x=open({str(marker)!r}, 'w').close()"

    class RaddParam(inspect.Parameter):
        @property
        def name(self):
            return Radd("z")

    class RaddSignature(inspect.Signature):
        @property
        def parameters(self):
            return {"z": RaddParam("z", inspect.Parameter.VAR_POSITIONAL)}

    def victim(a):
        return a

    victim.__signature__ = RaddSignature()
    with pytest.raises(ValueError, match="non-identifier signature"):
        decorator(_passthrough)(victim)
    assert not marker.exists()


@pytest.mark.parametrize(
    "malformed",
    [
        "*",
        "/",
        "a, *, *, b",
        "a, *b, *c",
        "a, *b, *, c",
        "a, *, /",
        "a, /, *, /",
        "**k, a",
        "a, **k, **j",
        "a, **k, *b",
        "a, a",
        "a, *, **k",
        "/, a",
        "a, /, b, /",
        "*, **k",
    ],
)
def test_malformed_marker_structure_is_refused_not_left_to_the_eval(malformed):
    # Every token is a fine identifier or marker; the STRUCTURE is what the
    # parser would reject, so the fence refuses it before any eval can raise.
    with pytest.raises(ValueError, match="malformed"):
        new_wrapper(lambda *a, **k: None, _infodict(malformed))


@pytest.mark.parametrize(
    "well_formed",
    ["a, /", "a, /, b, *, c, **k", "*a, **k", "a, *, b", "**k", "a, b, /, c"],
)
def test_well_formed_marker_structure_still_builds_a_wrapper(well_formed):
    wrapped = new_wrapper(lambda *a, **k: "ok", _infodict(well_formed))
    assert callable(wrapped)

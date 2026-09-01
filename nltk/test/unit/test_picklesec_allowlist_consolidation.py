# Natural Language Toolkit: attack harness for the picklesec allowlist consolidation
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack harness for consolidating every allowlisting unpickler into picklesec.

The GHSA-8mgp hardening once carried a per-caller ``AllowlistUnpickler`` subclass
in each model loader (``tbl.demo._TblModelUnpickler``,
``transitionparser._TransitionParserModelUnpickler``) plus an ``unpickler_cls=``
hook on :func:`~nltk.picklesec.allowlisted_pickle_load` so a caller could inject
its own subclass. That hook is itself attack surface (a caller, or a future
refactor, can substitute an unpickler that weakens ``find_class``), and the two
subclasses only differed in what they added on top of the same base guards. This
harness proves the consolidated design is strictly safe:

* ``unpickler_cls`` is GONE; no caller can substitute the unpickler.
* ``allowed_globals`` is a caller-controlled input, but it CANNOT widen past the
  base hard guards: allowlisting ``os.system`` / ``builtins.eval`` / a dotted or
  dunder name is still refused.
* ``builtins.object`` (which ``tbl.demo`` needs on its allowlist) is inert: it
  reconstructs a bare sentinel and cannot be weaponised via REDUCE args or BUILD
  state, so it earns its place in ``_SAFE_DENIED_GLOBALS``.
* the numpy object-dtype ``scalar`` nested-unpickle sink is refused by the BASE
  unpickler for every caller (``_GUARDED_GLOBALS``), which is why no per-caller
  subclass is needed.
* ``pickle_dump`` / ``pickle_dumps`` round-trip through the allowlist loader.
* every pickle in the shipped tree routes through picklesec (the CI guard passes
  AND has teeth).

Every payload is executed against the real loader (no mocks): a leak would run
the gadget, so a green run is a real refusal.
"""

import ast
import importlib.util
import inspect
import io
import os
import pickle
import subprocess
import sys

import pytest

from nltk.picklesec import (
    _SAFE_DENIED_GLOBALS,
    AllowlistUnpickler,
    allowlisted_pickle_load,
    pickle_dump,
    pickle_dumps,
)

_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
)


def _reduce_payload(target, args):
    """Pickle bytes whose REDUCE is ``target(*args)`` at load time. The class is
    local and never referenced in the output: only the ``(target, args)`` reduce
    tuple is serialised, so this builds an arbitrary gadget from any callable."""

    class _Gadget:
        def __reduce__(self):
            return (target, args)

    return pickle.dumps(_Gadget(), protocol=pickle.HIGHEST_PROTOCOL)


def _load(payload, **kw):
    return allowlisted_pickle_load(io.BytesIO(payload), **kw)


# ===========================================================================
# 1) The unpickler_cls injection hook is gone
# ===========================================================================


def test_allowlisted_pickle_load_has_no_unpickler_cls_hook():
    """A caller can no longer swap in a weaker unpickler: the ``unpickler_cls``
    parameter does not exist, so passing one is a hard ``TypeError``."""
    params = inspect.signature(allowlisted_pickle_load).parameters
    assert "unpickler_cls" not in params, params
    with pytest.raises(TypeError):
        allowlisted_pickle_load(io.BytesIO(b""), unpickler_cls=object)


def test_no_stray_unpickler_subclasses_in_consolidated_callers():
    """The per-caller subclasses were folded into the base; the loaders that used
    them expose no such class any more (the base ``AllowlistUnpickler`` does the
    work). ``tbl.demo`` is checked here; the transition-parser caller is covered by
    ``test_attack_allowlist_callers_expanded``."""
    from nltk.tbl import demo

    assert not hasattr(demo, "_TblModelUnpickler")


# ===========================================================================
# 2) allowed_globals cannot widen past the base hard guards
# ===========================================================================

# Even if a caller allowlists these EXACTLY (and their module), the base guards
# still refuse them. Each is resolved dynamically so the (module, qualname) the
# pickle actually stores is exactly what we allowlist, the strongest test.
_DANGEROUS_CALLABLES = [
    (os.system, ("echo picklesec-consolidation-canary",)),
    (eval, ("__import__('os').getpid()",)),
    (exec, ("pass",)),
    (compile, ("1", "<s>", "eval")),
    (__import__, ("os",)),
    (__import__("subprocess").Popen, (["true"],)),
    (__import__("importlib").import_module, ("os",)),
    (__import__("marshal").loads, (b"",)),
]


@pytest.mark.parametrize("target,args", _DANGEROUS_CALLABLES)
def test_allowlist_cannot_widen_to_dangerous_callable(target, args):
    module = target.__module__
    qualname = getattr(target, "__qualname__", target.__name__)
    payload = _reduce_payload(target, args)
    # Maximally permissive caller: allowlist the exact global AND its module.
    with pytest.raises(pickle.UnpicklingError):
        _load(
            payload,
            allowed_globals=[(module, qualname)],
            allowed_modules=[module],
        )


def test_allowlist_cannot_widen_to_numpy_denied_sink():
    """A denied scientific-stack I/O sink (``numpy.load``) stays refused even when
    the caller allowlists it and its whole namespace."""
    numpy = pytest.importorskip("numpy")
    payload = _reduce_payload(numpy.load, ("evil.npy",))
    with pytest.raises(pickle.UnpicklingError):
        _load(
            payload,
            allowed_globals=[("numpy", "load")],
            allowed_modules=["numpy"],
        )


def test_allowlist_cannot_admit_a_dunder_name():
    """A dunder global name is refused at the BOUNDARY (constructing a loader that
    allowlists it raises), and find_class refuses one at runtime too (dunders
    reach module internals like ``__builtins__``)."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(b""), allowed_globals=[("os", "__loader__")])
    benign = AllowlistUnpickler(io.BytesIO(b""), allowed_modules=["nltk"])
    with pytest.raises(pickle.UnpicklingError):
        benign.find_class("nltk", "__class__")


def test_allowlist_cannot_admit_a_dotted_name():
    """A dotted global name is refused at the BOUNDARY and at find_class time
    (attribute-traversal RCE, GHSA-4489)."""
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(b""), allowed_globals=[("os", "path.join")])
    benign = AllowlistUnpickler(io.BytesIO(b""), allowed_modules=["nltk"])
    with pytest.raises(pickle.UnpicklingError):
        benign.find_class("nltk", "path.join")


# ===========================================================================
# 2b) the caller allowlists are validated UP FRONT, at construction
# ===========================================================================

# A dangerous allowed_globals entry is refused when the loader is BUILT, before a
# byte is read, so a caller "randomly defining stuff" cannot even configure a
# permissive loader (it does not depend on a hostile pickle naming the entry).
_BAD_ALLOWED_GLOBALS = [
    ("os.system", ("posix", "system")),
    ("os.system (os spelling)", ("os", "system")),
    ("builtins.eval", ("builtins", "eval")),
    ("builtins.exec", ("builtins", "exec")),
    ("subprocess.Popen", ("subprocess", "Popen")),
    ("marshal.loads", ("marshal", "loads")),
    ("pickle.Unpickler", ("pickle", "Unpickler")),
    ("operator.attrgetter", ("operator", "attrgetter")),
    ("functools.partial", ("functools", "partial")),
    ("importlib.import_module", ("importlib", "import_module")),
    ("numpy.load (denied global)", ("numpy", "load")),
    ("numpy.lib npyio sink", ("numpy.lib.npyio", "load")),
    ("pandas read_csv sink", ("pandas", "read_csv")),
    ("scipy.io loadmat sink", ("scipy.io.matlab", "loadmat")),
    ("dotted name", ("nltk.x", "os.system")),
    ("dunder name", ("nltk.x", "__reduce_ex__")),
]


@pytest.mark.parametrize(
    "label,entry", _BAD_ALLOWED_GLOBALS, ids=[c[0] for c in _BAD_ALLOWED_GLOBALS]
)
def test_dangerous_allowed_globals_refused_at_construction(label, entry):
    # Empty bytes: proves the refusal is at construction, not at load of a payload.
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(b""), allowed_globals=[entry])
    # ...and allowlisted_pickle_load refuses the same config before reading.
    with pytest.raises(pickle.UnpicklingError):
        allowlisted_pickle_load(io.BytesIO(b""), allowed_globals=[entry])


_BAD_ALLOWED_MODULES = [
    "os",
    "posix",
    "posixpath",
    "ntpath",
    "genericpath",
    "subprocess",
    "builtins",
    "importlib",
    "marshal",
    "pickle",
    "operator",
    "functools",
    "ctypes",
    "socket",
    "numpy.lib",
    "numpy.rec",
    "scipy.io",
    "pandas.io",
]


@pytest.mark.parametrize("module", _BAD_ALLOWED_MODULES)
def test_dangerous_allowed_modules_refused_at_construction(module):
    with pytest.raises(pickle.UnpicklingError):
        AllowlistUnpickler(io.BytesIO(b""), allowed_modules=[module])
    with pytest.raises(pickle.UnpicklingError):
        allowlisted_pickle_load(io.BytesIO(b""), allowed_modules=[module])


def test_every_real_allowlist_still_constructs():
    """The boundary validator must not reject any allowlist a real caller uses.
    Every allowlist that ships in this tree (tbl, punkt, transition parser, and
    the chart parser where it uses AllowlistUnpickler) must construct cleanly.
    Each is gathered defensively so the test is portable across branches that
    wire a different set of callers through the allowlisting loader."""
    reals = []

    def _add(import_path, *names):
        import importlib

        try:
            mod = importlib.import_module(import_path)
            reals.append(tuple(getattr(mod, n) for n in names))
        except (ImportError, AttributeError):
            pass  # this caller does not exist / does not use an allowlist here

    _add("nltk.tbl.demo", "_TBL_MODEL_ALLOWED_GLOBALS")
    _add("nltk.tokenize.punkt", "_PUNKT_ALLOWED_GLOBALS")
    _add(
        "nltk.parse.transitionparser",
        "_MODEL_ALLOWED_GLOBALS",
        "_MODEL_ALLOWED_MODULES",
    )
    _add("nltk.app.chartparser_app", "_CHART_GRAMMAR_ALLOWED_GLOBALS")

    assert reals, "no real allowlists were found to validate"
    for entry in reals:
        allowed_globals = entry[0]
        allowed_modules = entry[1] if len(entry) > 1 else ()
        # Must NOT raise.
        AllowlistUnpickler(
            io.BytesIO(b""),
            allowed_globals=allowed_globals,
            allowed_modules=allowed_modules,
        )


@pytest.mark.parametrize(
    "entry", [("builtins", "int"), ("builtins", "float"), ("builtins", "object")]
)
def test_audited_safe_primitives_are_still_allowlistable(entry):
    """The audited ``_SAFE_DENIED_GLOBALS`` primitives live in denied ``builtins``
    but keep their exemption, so a legitimate model can still name them."""
    AllowlistUnpickler(io.BytesIO(b""), allowed_globals=[entry])


# ===========================================================================
# 3) builtins.object is inert (earns its _SAFE_DENIED_GLOBALS place)
# ===========================================================================


def test_builtins_object_is_registered_safe():
    assert ("builtins", "object") in _SAFE_DENIED_GLOBALS


def test_builtins_object_reconstructs_as_inert_sentinel():
    """A bare ``object()`` reconstructs (tbl models carry it as a default marker)
    and is exactly a featureless instance: no ``__dict__``, nothing to run."""
    payload = _reduce_payload(object, ())
    obj = _load(payload, allowed_globals=[("builtins", "object")])
    assert type(obj) is object
    assert not hasattr(obj, "__dict__")


def test_builtins_object_cannot_be_weaponised_via_reduce_args():
    """``object`` takes no constructor args, so a REDUCE that hands it a payload is
    a load-time error, not a code path: nothing in ``args`` is ever executed."""
    payload = _reduce_payload(object, ({"PWNED": 1},))
    with pytest.raises((TypeError, pickle.UnpicklingError)):
        _load(payload, allowed_globals=[("builtins", "object")])


def test_builtins_object_cannot_be_weaponised_via_build_state():
    """A BUILD that tries to graft state onto a bare ``object`` fails: it has no
    ``__dict__`` to update and no ``__setstate__`` to invoke, so poisoned STATE
    cannot ride in on the sentinel."""

    class _StatefulObject:
        def __reduce__(self):
            # (callable, args, state) -> object() then BUILD with a __dict__.
            return (object, (), {"injected": "payload"})

    payload = pickle.dumps(_StatefulObject(), protocol=pickle.HIGHEST_PROTOCOL)
    with pytest.raises((TypeError, AttributeError, pickle.UnpicklingError)):
        _load(payload, allowed_globals=[("builtins", "object")])


# ===========================================================================
# 4) numpy object-dtype scalar sink refused by the BASE unpickler
# ===========================================================================


def _scalar_payload(dtype_str, data_bytes):
    numpy = pytest.importorskip("numpy")
    ma = pytest.importorskip("numpy.core.multiarray")

    class _Scalar:
        def __reduce__(self):
            return (ma.scalar, (numpy.dtype(dtype_str), data_bytes))

    return pickle.dumps(_Scalar(), protocol=pickle.HIGHEST_PROTOCOL)


_SCALAR_ALLOW = [
    ("numpy.core.multiarray", "scalar"),
    ("numpy._core.multiarray", "scalar"),
    ("numpy", "dtype"),
]


def test_numpy_object_dtype_scalar_refused_by_base_allowlist():
    """No per-caller loader here: the plain ``allowlisted_pickle_load`` refuses the
    object-dtype ``scalar`` gadget because ``_GUARDED_GLOBALS`` wraps ``scalar`` in
    the base unpickler for every caller."""
    numpy = pytest.importorskip("numpy")
    payload = _scalar_payload("O", _reduce_payload(dict, ([("PWNED", 1)],)))
    with pytest.raises(pickle.UnpicklingError):
        _load(payload, allowed_globals=_SCALAR_ALLOW, allowed_modules=["numpy"])


def test_numpy_numeric_scalar_still_reconstructs_through_base():
    """The wrapper only refuses object dtypes: a genuine numeric scalar (the only
    kind a real model carries) reconstructs unchanged through the base loader."""
    numpy = pytest.importorskip("numpy")
    payload = _scalar_payload("float64", numpy.float64(3.14).tobytes())
    obj = _load(payload, allowed_globals=_SCALAR_ALLOW, allowed_modules=["numpy"])
    assert float(obj) == pytest.approx(3.14)


def test_find_class_returns_the_guarded_scalar_wrapper_not_raw_numpy():
    """Teeth: ``find_class`` accepts ``scalar`` by name but hands back the guarded
    wrapper, never the raw numpy callable the gadget needs."""
    numpy = pytest.importorskip("numpy")
    ma = pytest.importorskip("numpy.core.multiarray")
    resolver = AllowlistUnpickler(
        io.BytesIO(b""), allowed_globals=_SCALAR_ALLOW, allowed_modules=["numpy"]
    )
    resolved = resolver.find_class("numpy._core.multiarray", "scalar")
    assert callable(resolved) and resolved is not ma.scalar


# ===========================================================================
# 5) pickle_dump / pickle_dumps round-trip through the allowlist loader
# ===========================================================================


def test_pickle_dump_roundtrips_through_allowlist_loader():
    payload = {"a": [1, 2, 3], "b": ("x", "y"), "c": {1, 2}}
    buf = io.BytesIO()
    pickle_dump(payload, buf)
    buf.seek(0)
    got = allowlisted_pickle_load(buf, allowed_globals=(), allowed_modules=())
    assert got == payload


def test_pickle_dumps_roundtrips_through_allowlist_loader():
    payload = [1, "two", (3.0,), {"four": 4}]
    got = _load(pickle_dumps(payload), allowed_globals=(), allowed_modules=())
    assert got == payload


# ===========================================================================
# 6) the all-through-picklesec CI guard passes AND has teeth
# ===========================================================================


def _load_guard_module():
    path = os.path.join(_REPO_ROOT, "tools", "check_all_pickle_through_picklesec.py")
    if not os.path.exists(path):
        pytest.skip("pickle guard tool not present in this checkout")
    spec = importlib.util.spec_from_file_location("_pickle_guard", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_pickle_guard_tool_reports_clean_tree():
    """Every pickle call in the shipped tree routes through picklesec: the guard
    exits 0 when run over the real repository."""
    tool = os.path.join(_REPO_ROOT, "tools", "check_all_pickle_through_picklesec.py")
    if not os.path.exists(tool):
        pytest.skip("guard tool not present in this checkout")
    proc = subprocess.run(
        [sys.executable, tool],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize(
    "src",
    [
        "import pickle\npickle.load(f)",
        "import pickle as p\np.loads(b)",
        "from pickle import loads\nloads(b)",
        "from pickle import *",
        "import pickle\npickle.Unpickler(f).load()",
        "import cPickle\ncPickle.dump(x, f)",
    ],
)
def test_pickle_guard_visitor_has_teeth(src):
    """The guard flags every bare-pickle bypass vector (attribute, alias, from- and
    star-import) so a future raw pickle cannot slip in."""
    guard = _load_guard_module()
    visitor = guard._PickleCallVisitor("<synthetic>")
    visitor.visit(ast.parse(src))
    assert visitor.violations, f"guard missed a bypass: {src!r}"


@pytest.mark.parametrize(
    "src",
    [
        "import pickle\nraise pickle.UnpicklingError('x')",
        "import pickle\np = pickle.HIGHEST_PROTOCOL",
        "from nltk.picklesec import RestrictedUnpickler\nRestrictedUnpickler(f).load()",
        "from nltk.picklesec import pickle_dump\npickle_dump(x, f)",
        "import json\njson.dumps(x)",
    ],
)
def test_pickle_guard_visitor_no_false_positives(src):
    """It must NOT flag exceptions/constants, picklesec's own unpickler instances,
    the picklesec dump helpers, or unrelated serialisers."""
    guard = _load_guard_module()
    visitor = guard._PickleCallVisitor("<synthetic>")
    visitor.visit(ast.parse(src))
    assert (
        not visitor.violations
    ), f"guard false-flagged: {src!r} -> {visitor.violations}"

# Natural Language Toolkit: systematic picklesec denylist / evasion attack matrix
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Systematic candidate sweep for :mod:`nltk.picklesec` (GHSA-8mgp).

The sibling suites (``test_attack_deser_rce_expanded``, ``test_pickle_gadget*``,
``test_pickle_allowlist_security``, ``test_attack_allowlist_*``,
``test_attack_warnonly_loaders_expanded``) exercise hand picked gadgets and the
opcode landscape. This file closes the coverage in the other direction: it walks
picklesec's OWN guard tables and proves, entry by entry and through the REAL
unpicklers, that every denied thing is denied and every audited safe thing still
loads. Concretely it asserts:

* every module in :data:`~nltk.picklesec._DENIED_MODULE_PREFIXES` is refused at
  ``find_class`` (as the bare module, as a submodule) AND is refused as an
  ``allowed_modules`` configuration entry;
* every pair in :data:`~nltk.picklesec._DENIED_GLOBALS` is refused at
  ``find_class`` and as an ``allowed_globals`` entry;
* every qualname in :data:`~nltk.picklesec._DENIED_SCISTACK_QUALNAMES` is refused
  when re exported under a numpy submodule, and as an ``allowed_globals`` entry;
* every pair in :data:`~nltk.picklesec._GUARDED_GLOBALS` resolves to the guarded
  wrapper (not the raw callable), and the wrapper refuses an object bearing dtype;
* every audited primitive in :data:`~nltk.picklesec._SAFE_DENIED_GLOBALS` still
  loads when explicitly allowlisted, yet stays refused when it is not;
* ``__reduce_ex__`` protocols 0 through 5 of an RCE gadget are each refused with
  no side effect (a stock unpickler runs the same payload, proving the teeth);
* allowlist evasion by case, whitespace, unicode confusable, FRAME framing, memo
  reference and nested pickle in pickle is refused, never executed; and
* the warn only :class:`~nltk.picklesec.WarningUnpickler` still warns (once per
  instance, with its context) while the restricted path refuses the same gadget.

Every malicious vector is driven through a real ``RestrictedUnpickler`` /
``AllowlistUnpickler`` (or ``allowlisted_pickle_load``); nothing is mocked. A
refusal must be a ``pickle.UnpicklingError`` (picklesec), not a path or import
error, and no attacker side effect (a sentinel file) may appear.
"""

import io
import os
import pickle
import sys
import types
import warnings

import pytest

from nltk.picklesec import (
    _DENIED_GLOBALS,
    _DENIED_MODULE_PREFIXES,
    _DENIED_SCISTACK_QUALNAMES,
    _GUARDED_GLOBALS,
    _SAFE_DENIED_GLOBALS,
    PICKLE_WARNING,
    AllowlistUnpickler,
    RestrictedUnpickler,
    WarningUnpickler,
    _guarded_scalar,
    allowlisted_pickle_load,
    pickle_load,
)

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX only global")

_THIS = __name__

# A broad, over permissive scientific stack allow: the worst case a careless
# downstream caller could configure. Even here nothing dangerous may resolve.
_BROAD = ("numpy", "scipy", "sklearn", "pandas")


def record_execution(path=None, *args, **kwargs):
    """Stand in for an arbitrary code execution sink; writes a marker if reached."""
    if path:
        with open(path, "wb") as handle:
            handle.write(b"executed")
    return 0


class _MarkerGadget:
    """A reduce gadget whose reconstruction calls :func:`record_execution`.

    The callable is a global of THIS test module, so a stock unpickler resolves
    and runs it (teeth), while every guarded unpickler refuses the global.
    """

    def __init__(self, marker):
        self._marker = marker

    def __reduce__(self):
        return (record_execution, (self._marker,))


def _benign_loader():
    """An ``AllowlistUnpickler`` whose only allowance is ``builtins.int``.

    ``find_class`` on it exercises the guards in isolation: nothing dangerous is
    allowlisted, so any refusal comes from a denylist / module guard, never from a
    permissive allowance.
    """
    return AllowlistUnpickler(io.BytesIO(b""), allowed_globals=(("builtins", "int"),))


def _broad_loader():
    return AllowlistUnpickler(io.BytesIO(b""), allowed_modules=_BROAD)


def _su(text):
    raw = text.encode()
    return pickle.SHORT_BINUNICODE + bytes([len(raw)]) + raw


# ===========================================================================
# A. Denylist coverage: every guard table entry is actually denied.
# ===========================================================================


class TestDeniedModulePrefixesAreEnforced:
    """Every :data:`_DENIED_MODULE_PREFIXES` entry must be unreachable at
    ``find_class`` and unconfigurable as an ``allowed_modules`` entry."""

    @pytest.mark.parametrize("module", sorted(_DENIED_MODULE_PREFIXES))
    def test_bare_denied_module_is_refused_by_find_class(self, module):
        with pytest.raises(pickle.UnpicklingError):
            _benign_loader().find_class(module, "some_attr")

    @pytest.mark.parametrize("module", sorted(_DENIED_MODULE_PREFIXES))
    def test_submodule_of_denied_module_is_refused(self, module):
        """The prefix guard matches ``module == deny`` or ``deny + "."``; a crafted
        submodule under a denied namespace must be refused too."""
        with pytest.raises(pickle.UnpicklingError):
            _benign_loader().find_class(module + ".evil", "some_attr")

    @pytest.mark.parametrize("module", sorted(_DENIED_MODULE_PREFIXES))
    def test_denied_module_cannot_be_allowlisted_at_construction(self, module):
        """A caller cannot re open a denied namespace: the constructor validates
        ``allowed_modules`` and refuses a denied entry before any byte is read."""
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(b""), allowed_modules=(module,))


class TestDeniedGlobalsAreEnforced:
    """Every :data:`_DENIED_GLOBALS` pair must be refused by the exact match guard
    and rejected as a caller supplied ``allowed_globals`` entry."""

    @pytest.mark.parametrize("pair", sorted(_DENIED_GLOBALS))
    def test_exact_denied_global_is_refused_by_find_class(self, pair):
        module, name = pair
        with pytest.raises(pickle.UnpicklingError):
            _benign_loader().find_class(module, name)

    @pytest.mark.parametrize("pair", sorted(_DENIED_GLOBALS))
    def test_denied_global_cannot_be_allowlisted_at_construction(self, pair):
        module, name = pair
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(b""), allowed_globals=(pair,))


class TestScistackQualnameSinksAreEnforced:
    """Every :data:`_DENIED_SCISTACK_QUALNAMES` entry is refused wherever it
    resolves in the scientific stack, even under a submodule the export name /
    prefix denylists never enumerate (CWE-502). Proven by re exporting a synthetic
    callable carrying the denied qualname under a fresh numpy submodule."""

    numpy = pytest.importorskip("numpy")

    @pytest.mark.parametrize("qualname", sorted(_DENIED_SCISTACK_QUALNAMES))
    def test_reexported_sink_qualname_is_refused_under_broad_allow(
        self, qualname, monkeypatch
    ):
        import numpy

        modname = "numpy._candidate_probe_" + qualname.lower().replace("-", "_")

        def sink(*args, **kwargs):
            return "PWNED"

        sink.__module__ = modname
        sink.__qualname__ = qualname
        fake = types.ModuleType(modname)
        setattr(fake, qualname, sink)
        monkeypatch.setitem(sys.modules, modname, fake)
        monkeypatch.setattr(numpy, modname.split(".", 1)[1], fake, raising=False)

        with pytest.raises(pickle.UnpicklingError):
            _broad_loader().find_class(modname, qualname)

    @pytest.mark.parametrize("qualname", sorted(_DENIED_SCISTACK_QUALNAMES))
    def test_sink_qualname_cannot_be_allowlisted_under_a_sci_root(self, qualname):
        """Configuring ``allowed_globals`` with a sci stack I/O sink qualname is
        refused at construction, independent of whether it currently resolves."""
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(b""), allowed_globals=(("numpy", qualname),))


# ===========================================================================
# B. Guarded globals and audited safe primitives.
# ===========================================================================


class TestGuardedGlobalsAreWrapped:
    numpy = pytest.importorskip("numpy")

    @pytest.mark.parametrize("pair", sorted(_GUARDED_GLOBALS))
    def test_guarded_global_resolves_to_the_wrapper_not_the_raw_callable(self, pair):
        """``find_class`` must hand back the guarded wrapper for every
        :data:`_GUARDED_GLOBALS` spelling, never numpy's raw ``scalar`` (which is a
        nested unpickle sink for an object dtype)."""
        module, name = pair
        real = getattr(__import__(module, fromlist=[name]), name)
        resolved = _broad_loader().find_class(module, name)
        assert callable(resolved)
        assert resolved is not real, f"{module}.{name} resolved to the raw callable"

    def test_guarded_scalar_refuses_object_dtype_but_allows_numeric(self):
        """The wrapper refuses an object bearing dtype (the gadget) before numpy
        deserializes anything, and passes a genuine numeric scalar unchanged."""
        import numpy

        real = getattr(numpy, "_core", getattr(numpy, "core", None)).multiarray.scalar
        wrapped = _guarded_scalar(real)
        with pytest.raises(pickle.UnpicklingError):
            wrapped(numpy.dtype("O"), b"")
        value = wrapped(numpy.dtype("float64"), numpy.float64(2.5).tobytes())
        assert float(value) == pytest.approx(2.5)

    def test_object_dtype_scalar_reduce_is_refused_end_to_end(self):
        """The full REDUCE gadget (``scalar(dtype('O'), <bytes>)``), built from only
        allowlisted names, is refused by ``allowlisted_pickle_load`` itself."""
        import numpy

        marker = {"reached": False}

        class Canary:
            def __reduce__(self):
                marker["reached"] = True
                return (dict, ([("PWNED", 1)],))

        class ScalarEscape:
            def __reduce__(self):
                ma = getattr(numpy, "_core", getattr(numpy, "core", None)).multiarray
                return (ma.scalar, (numpy.dtype("O"), pickle.dumps(Canary())))

        allow = {
            ("numpy", "dtype"),
            ("numpy._core.multiarray", "scalar"),
            ("numpy.core.multiarray", "scalar"),
        }
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                io.BytesIO(pickle.dumps(ScalarEscape(), protocol=5)),
                allowed_globals=allow,
            )


class TestSafeDeniedPrimitives:
    """The audited :data:`_SAFE_DENIED_GLOBALS` primitives (a few immutable builtin
    types plus the inert ``object`` sentinel) must load when explicitly named, yet
    stay refused when the caller did not allowlist them."""

    @pytest.mark.parametrize("pair", sorted(_SAFE_DENIED_GLOBALS))
    def test_safe_primitive_loads_when_explicitly_allowlisted(self, pair):
        import builtins

        module, name = pair
        loader = AllowlistUnpickler(io.BytesIO(b""), allowed_globals=(pair,))
        assert loader.find_class(module, name) is getattr(builtins, name)

    @pytest.mark.parametrize("pair", sorted(_SAFE_DENIED_GLOBALS))
    def test_safe_primitive_refused_when_not_allowlisted(self, pair):
        """The exemption is opt in: a loader that allowlists only ``builtins.int``
        must still refuse ``builtins.str`` / ``builtins.object`` and the rest."""
        module, name = pair
        if pair == ("builtins", "int"):
            pytest.skip("int is the single primitive the benign loader allowlists")
        with pytest.raises(pickle.UnpicklingError):
            _benign_loader().find_class(module, name)

    def test_defaultdict_int_container_round_trips(self):
        """Benign control that leans on the ``builtins.int`` exemption: a
        ``defaultdict(int)`` (the shape a Punkt parameter table carries) round trips
        through the allowlist without a false positive."""
        import collections

        dd = collections.defaultdict(int)
        dd["a"] += 3
        dd["b"] += 1
        out = allowlisted_pickle_load(
            io.BytesIO(pickle.dumps(dd, protocol=4)),
            allowed_globals={
                ("collections", "defaultdict"),
                ("builtins", "int"),
            },
        )
        assert out == {"a": 3, "b": 1}


# ===========================================================================
# C. __reduce_ex__ protocol matrix: an RCE gadget refused at every protocol.
# ===========================================================================


class TestReduceProtocolMatrix:
    """A reduce gadget serialized at each pickle protocol (0 through 5) drives a
    different opcode shape (text GLOBAL at proto 0/1, STACK_GLOBAL at proto 4/5),
    yet every shape routes the callable through ``find_class`` and is refused."""

    @pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
    def test_stock_unpickler_executes_each_protocol(self, protocol, tmp_path):
        """Teeth: without the guard, the gadget runs and writes the marker at every
        protocol, so the guarded assertions below are not vacuous."""
        marker = tmp_path / f"stock_p{protocol}"
        payload = pickle.dumps(_MarkerGadget(str(marker)), protocol=protocol)
        pickle.Unpickler(io.BytesIO(payload)).load()
        assert marker.exists(), f"protocol {protocol} gadget is not armed"

    @pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
    @pytest.mark.parametrize("loader", ["restricted", "allowlist"])
    def test_guarded_unpicklers_refuse_each_protocol(self, protocol, loader, tmp_path):
        marker = tmp_path / f"guarded_{loader}_p{protocol}"
        payload = pickle.dumps(_MarkerGadget(str(marker)), protocol=protocol)
        if loader == "restricted":
            run = lambda: RestrictedUnpickler(io.BytesIO(payload)).load()
        else:
            run = lambda: AllowlistUnpickler(io.BytesIO(payload)).load()
        with pytest.raises(pickle.UnpicklingError):
            run()
        assert not marker.exists(), f"protocol {protocol} executed via {loader}"

    @POSIX_ONLY
    @pytest.mark.parametrize("protocol", range(pickle.HIGHEST_PROTOCOL + 1))
    def test_os_system_reduce_refused_at_each_protocol(self, protocol, tmp_path):
        """The classic ``os.system`` reduce (a real shell touch) is refused at every
        protocol and never runs."""
        marker = tmp_path / f"ossys_p{protocol}"

        class OsGadget:
            def __reduce__(self):
                return (os.system, (f"touch {marker}",))

        payload = pickle.dumps(OsGadget(), protocol=protocol)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(io.BytesIO(payload), allowed_modules=_BROAD)
        assert not marker.exists()


# ===========================================================================
# D. Allowlist evasion: case, whitespace, confusables, framing, memo, nesting.
# ===========================================================================


class TestAllowlistEvasion:
    _CASE_VARIANTS = ["OS", "Os", "oS", "SUBPROCESS", "Builtins", "BUILTINS"]
    _WHITESPACE_VARIANTS = [" os", "os ", "os\t", "\tos", "os\n", " subprocess"]
    # Cyrillic small letter 'o' (U+043E) and 'ѕ' (U+0455) resemble ASCII o / s.
    _CONFUSABLE_VARIANTS = ["оs", "oѕ", "оѕ", "subprocesѕ"]

    @pytest.mark.parametrize("module", _CASE_VARIANTS)
    def test_case_variant_module_is_not_reconstructable(self, module):
        """A case altered module name is neither denied nor allowlisted, so under a
        broad sci stack allow it is refused, not silently resolved to ``os``."""
        with pytest.raises(pickle.UnpicklingError):
            _broad_loader().find_class(module, "system")

    @pytest.mark.parametrize("module", _WHITESPACE_VARIANTS)
    def test_whitespace_padded_module_is_not_reconstructable(self, module):
        with pytest.raises(pickle.UnpicklingError):
            _broad_loader().find_class(module, "system")

    @pytest.mark.parametrize("module", _CONFUSABLE_VARIANTS)
    def test_unicode_confusable_module_is_not_reconstructable(self, module):
        with pytest.raises(pickle.UnpicklingError):
            _broad_loader().find_class(module, "system")

    def test_framed_gadget_is_refused_and_does_not_execute(self, tmp_path):
        """A FRAME (0x95) wrapped pickle does not bypass ``find_class``: the framed
        gadget global is still refused, and the marker is never written."""
        marker = tmp_path / "framed"
        body = (
            _su(_THIS)
            + _su("record_execution")
            + pickle.STACK_GLOBAL
            + _su(str(marker))
            + pickle.TUPLE1
            + pickle.REDUCE
            + pickle.STOP
        )
        payload = (
            pickle.PROTO
            + bytes([4])
            + pickle.FRAME
            + len(body).to_bytes(8, "little")
            + body
        )
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(payload)).load()
        assert not marker.exists()

    def test_memo_cannot_prestage_a_denied_global(self):
        """A GLOBAL then BINPUT (memoize) then BINGET (reuse) cannot smuggle a
        denied global: the global is refused when it is FIRST created, before any
        memo slot is filled."""
        payload = (
            pickle.PROTO
            + bytes([4])
            + _su("os")
            + _su("system")
            + pickle.STACK_GLOBAL
            + pickle.BINPUT
            + bytes([0])
            + pickle.STOP
        )
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(payload), allowed_modules=_BROAD).load()

    def test_get_of_unfilled_memo_slot_is_refused(self):
        """A BINGET referencing an empty memo slot cannot conjure an object; the
        load is refused, and nothing is executed."""
        payload = pickle.PROTO + bytes([4]) + pickle.BINGET + bytes([0]) + pickle.STOP
        with pytest.raises((pickle.UnpicklingError, KeyError)):
            AllowlistUnpickler(io.BytesIO(payload)).load()

    @pytest.mark.parametrize(
        "module,name",
        [
            ("pickle", "loads"),
            ("_pickle", "loads"),
            ("marshal", "loads"),
        ],
    )
    def test_nested_pickle_in_pickle_loader_is_refused(self, module, name, tmp_path):
        """Pickle in pickle: an outer REDUCE that calls a nested deserializer
        (``pickle.loads`` / ``_pickle.loads`` / ``marshal.loads``) on inner bytes is
        refused, so the inner (unrestricted) payload never runs. The inner bytes are
        a genuine ``os`` gadget to prove the nesting was real."""
        marker = tmp_path / f"nested_{module}_{name}"

        class InnerGadget:
            def __reduce__(self):
                return (record_execution, (str(marker),))

        inner = pickle.dumps(InnerGadget(), protocol=4)
        payload = (
            pickle.PROTO
            + bytes([4])
            + _su(module)
            + _su(name)
            + pickle.STACK_GLOBAL
            + pickle.SHORT_BINBYTES
            + bytes([len(inner)])
            + inner
            + pickle.TUPLE1
            + pickle.REDUCE
            + pickle.STOP
        )
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(payload), allowed_modules=_BROAD).load()
        assert not marker.exists()

    @pytest.mark.parametrize("name", ["_reconstructor", "__newobj__"])
    def test_copyreg_object_injection_gadgets_are_refused(self, name):
        """``copyreg._reconstructor`` / ``copyreg.__newobj__`` are object injection
        primitives; ``copyreg`` is a denied module, so both are refused even under a
        broad allow. ``__newobj__`` is additionally a dunder (a second guard)."""
        with pytest.raises(pickle.UnpicklingError):
            _broad_loader().find_class("copyreg", name)


# ===========================================================================
# E. WarningUnpickler and the warn only loader contract.
# ===========================================================================


class TestWarningUnpicklerContract:
    def test_warns_exactly_once_per_instance_across_two_loads(self):
        """``WarningUnpickler`` emits :data:`PICKLE_WARNING` on its first ``load``
        and never again on the same instance (the ``_warned`` latch), even when the
        stream carries two concatenated pickles."""
        buf = pickle.dumps({"a": 1}, protocol=4)
        unpickler = WarningUnpickler(io.BytesIO(buf + buf))
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            first = unpickler.load()
            second = unpickler.load()
        assert first == {"a": 1} and second == {"a": 1}
        runtime = [w for w in record if issubclass(w.category, RuntimeWarning)]
        assert len(runtime) == 1, f"expected one warning, got {len(runtime)}"
        assert PICKLE_WARNING in str(runtime[0].message)

    def test_context_is_included_in_the_warning(self):
        buf = pickle.dumps([1, 2, 3], protocol=4)
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            WarningUnpickler(io.BytesIO(buf), context="LoadChartMenu").load()
        assert any("LoadChartMenu" in str(w.message) for w in record)

    def test_no_context_gives_the_bare_warning(self):
        buf = pickle.dumps("plain", protocol=4)
        with warnings.catch_warnings(record=True) as record:
            warnings.simplefilter("always")
            WarningUnpickler(io.BytesIO(buf)).load()
        messages = [str(w.message) for w in record]
        assert any(m == PICKLE_WARNING for m in messages), messages

    def test_warn_only_executes_but_restricted_refuses_the_same_payload(self, tmp_path):
        """Boundary contract. The SAME reduce payload:

        * runs through ``WarningUnpickler`` after warning (it is warn only, not a
          security boundary): the marker is written; and
        * is REFUSED by ``RestrictedUnpickler`` (the boundary): the marker for the
          restricted attempt is never written.
        """
        warn_marker = tmp_path / "warnonly_ran"
        restricted_marker = tmp_path / "restricted_ran"

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            WarningUnpickler(
                io.BytesIO(pickle.dumps(_MarkerGadget(str(warn_marker)), protocol=4))
            ).load()
        assert warn_marker.exists(), "warn only loader did not execute; no teeth"

        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(
                io.BytesIO(
                    pickle.dumps(_MarkerGadget(str(restricted_marker)), protocol=4)
                )
            ).load()
        assert not restricted_marker.exists()

    def test_pickle_load_helper_warns_on_benign_and_restricted_refuses_gadget(
        self, tmp_path
    ):
        """``pickle_load(restricted=False)`` warns then returns benign data;
        ``pickle_load(restricted=True)`` refuses a gadget before it can run."""
        with pytest.warns(RuntimeWarning):
            out = pickle_load(io.BytesIO(pickle.dumps({"ok": [1, 2]}, protocol=4)))
        assert out == {"ok": [1, 2]}

        marker = tmp_path / "helper_restricted"
        with pytest.raises(pickle.UnpicklingError):
            pickle_load(
                io.BytesIO(pickle.dumps(_MarkerGadget(str(marker)), protocol=4)),
                restricted=True,
            )
        assert not marker.exists()


# ===========================================================================
# F. Benign controls: no false positive over blocking from the guard machinery.
# ===========================================================================


class TestBenignControlsStillLoad:
    def test_numpy_array_round_trips_under_broad_allow(self):
        """A genuine numeric numpy array reconstructs through a broad numpy allow;
        the guarded ``scalar`` wrapper and the denylists must not block it."""
        numpy = pytest.importorskip("numpy")
        allow = {
            ("numpy", "ndarray"),
            ("numpy", "dtype"),
            ("numpy._core.multiarray", "_reconstruct"),
            ("numpy.core.multiarray", "_reconstruct"),
            ("numpy._core.multiarray", "scalar"),
            ("numpy.core.multiarray", "scalar"),
            ("numpy._core.numeric", "_frombuffer"),
            ("numpy.core.numeric", "_frombuffer"),
        }
        arr = numpy.array([[1.5, 2.5], [3.5, 4.5]])
        out = allowlisted_pickle_load(
            io.BytesIO(pickle.dumps(arr, protocol=4)),
            allowed_globals=allow,
            allowed_modules=("numpy",),
        )
        assert numpy.array_equal(out, arr)

    def test_scipy_sparse_matrix_round_trips(self):
        """A real scipy sparse matrix (the shape a fitted model carries) loads under
        a numpy/scipy allow without a false positive."""
        numpy = pytest.importorskip("numpy")
        sparse = pytest.importorskip("scipy.sparse")
        matrix = sparse.csr_matrix(numpy.array([[1.0, 0.0], [0.0, 2.0]]))
        out = allowlisted_pickle_load(
            io.BytesIO(pickle.dumps(matrix, protocol=4)),
            allowed_modules=("numpy", "scipy"),
        )
        assert (out.toarray() == matrix.toarray()).all()

    def test_restricted_unpickler_round_trips_plain_containers(self):
        """The globals free container shapes NLTK actually pickles still load under
        the strictest (all globals denied) unpickler."""
        value = {"tags": ["NN", "VB"], "counts": (1, 2, 3), "seen": {1, 2}}
        out = RestrictedUnpickler(io.BytesIO(pickle.dumps(value, protocol=4))).load()
        assert out == value

    def test_real_svc_model_round_trips_through_model_allowlist(self):
        """A genuinely fitted sklearn SVC (the transition parser artifact) still
        loads through its exact model allowlist: the hardening does not over block a
        legitimate model."""
        numpy = pytest.importorskip("numpy")
        svm = pytest.importorskip("sklearn.svm")
        pytest.importorskip("scipy")
        from nltk.parse.transitionparser import (
            _MODEL_ALLOWED_GLOBALS,
            _MODEL_ALLOWED_MODULES,
        )

        features = numpy.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]])
        model = svm.SVC().fit(features, [0, 1, 0, 1])
        restored = allowlisted_pickle_load(
            io.BytesIO(pickle.dumps(model)),
            allowed_globals=_MODEL_ALLOWED_GLOBALS,
            allowed_modules=_MODEL_ALLOWED_MODULES,
        )
        assert (model.predict(features) == restored.predict(features)).all()

    def test_real_punkt_tokenizer_round_trips(self):
        """A trained Punkt tokenizer loads through ``punkt_pickle_load`` and
        tokenizes identically after the round trip."""
        from nltk.tokenize.punkt import PunktSentenceTokenizer, punkt_pickle_load

        tokenizer = PunktSentenceTokenizer()
        tokenizer.train("Dr. Smith arrived. It works! Mr. Jones left.")
        restored = punkt_pickle_load(io.BytesIO(pickle.dumps(tokenizer, protocol=4)))
        sample = "A test. Another one."
        assert restored.tokenize(sample) == tokenizer.tokenize(sample)

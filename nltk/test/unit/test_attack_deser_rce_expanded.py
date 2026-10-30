# Natural Language Toolkit: expanded deserialization / RCE attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded pickle / shelve / model deserialization attack matrix (GHSA-8mgp).

This file broadens the existing picklesec regression suite (test_pickle_*.py,
test_pickle_gadget*.py, test_chat80_shelve_rce.py, test_model_artifact_pathsec.py)
with vectors those files do not yet cover, and it holds each new hostile vector to
two hard properties:

* it is REFUSED by the relevant guard (``pickle.UnpicklingError`` from picklesec,
  never a ``PermissionError`` / ``ValueError`` from the path layer, which would
  mean the payload never reached the unpickler), and
* it produces NO side effect (an attacker sentinel file is never created).

The suite proves its own teeth: for every opcode class that can instantiate or
call a reconstructed global, the same payload is first run through the STOCK
``pickle.Unpickler`` and shown to execute (it writes the sentinel), so the
guarded assertion below it is real, not vacuous.

Net new relative to the existing files:

* the full opcode landscape that reaches ``find_class`` (INST, OBJ, NEWOBJ,
  NEWOBJ_EX, BUILD) exercised directly against ``RestrictedUnpickler`` and a
  bare ``AllowlistUnpickler``, each with a stock teeth demonstration,
* the ``BINPERSID`` persistent id opcode (the sibling of the already covered
  ``PERSID``),
* dotted and aliased backing module names resolved straight through the guard
  classes (not through ``nltk.data.load``),
* real scientific stack reduce chains routed through ``RestrictedUnpickler`` (the
  ``nltk.data.load`` contract blocks every global, even a benign array),
* a chat80 shelf staged under a REGISTERED data root with raw opcode bytes
  injected into the dbm, dbm backend agnostic, and
* the transition parser model allowlist attacked with opcode variety, not only
  the classic ``REDUCE`` shape.

Cross platform notes: fixtures are staged under the pytest basetemp (authorized
as a data root by conftest) or ``$HOME``, never ``/tmp``; every pickle and dbm is
opened binary; POSIX only globals are guarded with ``skipif``.
"""

import io
import os
import pickle
import shelve

import pytest

from nltk.picklesec import (
    PICKLE_WARNING,
    AllowlistUnpickler,
    RestrictedUnpickler,
    allowlisted_pickle_load,
    pickle_load,
)

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX only global")

# find_class resolves the sentinels below through this module's own name, so the
# stock teeth demonstration reconstructs a real, importable callable.
_THIS = __name__


# ===========================================================================
# Sentinels: reconstructing any of these writes a marker file. The guarded
# unpicklers must refuse them before that happens; the stock unpickler must run
# them (that is what proves the guarded assertion is not vacuous).
# ===========================================================================


def record_execution(path=None, *args, **kwargs):
    """A stand in for an arbitrary code execution sink (INST / REDUCE reach it)."""
    if path:
        with open(path, "wb") as handle:
            handle.write(b"executed")
    return 0


class NewObjSentinel:
    """Instantiated by the OBJ / NEWOBJ / NEWOBJ_EX opcodes."""

    def __new__(cls, path=None, *args, **kwargs):
        record_execution(path)
        return object.__new__(cls)


class BuildSentinel:
    """Reconstructed inert, then the BUILD opcode drives __setstate__."""

    def __new__(cls, *args, **kwargs):
        return object.__new__(cls)

    def __setstate__(self, state):
        record_execution(state)


# ===========================================================================
# Hand assembled opcode payloads. Each takes the sentinel path so the callable
# runs with a real, writable target under the stock unpickler.
# ===========================================================================

_PROTO = b"\x80\x04"
_MARK = b"("
_STOP = b"."


def _su(text):
    """SHORT_BINUNICODE opcode carrying ``text``."""
    raw = text.encode()
    return b"\x8c" + bytes([len(raw)]) + raw


def _global(module, name):
    return b"c" + module.encode() + b"\n" + name.encode() + b"\n"


def _stack_global(module, name):
    return _su(module) + _su(name) + b"\x93"


def _payload_inst(marker):
    # MARK, arg, INST module\nname\n : find_class(module, name), call(*stack)
    return _MARK + _su(marker) + b"i" + _THIS.encode() + b"\nrecord_execution\n" + _STOP


def _payload_obj(marker):
    # MARK, GLOBAL(class), arg, OBJ : class via find_class, then instantiate
    return _MARK + _global(_THIS, "NewObjSentinel") + _su(marker) + b"o" + _STOP


def _payload_newobj(marker):
    # STACK_GLOBAL(class), (arg,), NEWOBJ : cls.__new__(cls, arg)
    return (
        _PROTO
        + _stack_global(_THIS, "NewObjSentinel")
        + _su(marker)
        + b"\x85\x81"
        + _STOP
    )


def _payload_newobj_ex(marker):
    # STACK_GLOBAL(class), (arg,), {}, NEWOBJ_EX : cls.__new__(cls, arg, **{})
    return (
        _PROTO
        + _stack_global(_THIS, "NewObjSentinel")
        + _su(marker)
        + b"\x85"
        + b"}"
        + b"\x92"
        + _STOP
    )


def _payload_reduce(marker):
    # STACK_GLOBAL(callable), (arg,), REDUCE : callable(arg)
    return (
        _PROTO
        + _stack_global(_THIS, "record_execution")
        + _su(marker)
        + b"\x85R"
        + _STOP
    )


def _payload_build(marker):
    # NEWOBJ(BuildSentinel), state, BUILD : __setstate__(state)
    return (
        _PROTO
        + _stack_global(_THIS, "BuildSentinel")
        + b")"
        + b"\x81"
        + _su(marker)
        + b"b"
        + _STOP
    )


_OPCODE_BUILDERS = {
    "INST": _payload_inst,
    "OBJ": _payload_obj,
    "NEWOBJ": _payload_newobj,
    "NEWOBJ_EX": _payload_newobj_ex,
    "REDUCE": _payload_reduce,
    "BUILD": _payload_build,
}


def _assert_unpickling_error(excinfo):
    error = excinfo.value
    assert isinstance(error, pickle.UnpicklingError), (
        f"refused by {type(error).__name__}, not the unpickler: the payload never "
        "reached picklesec, so this proves nothing"
    )


# ===========================================================================
# 1. Opcode class matrix: every instantiate / call opcode reaches find_class
#    and is refused, with a stock teeth demonstration and no side effect.
# ===========================================================================


class TestOpcodeClassMatrixIsRefused:
    """INST, OBJ, NEWOBJ, NEWOBJ_EX, REDUCE and BUILD all route the reconstructed
    global through ``find_class``. Each guard must refuse them before the object
    is built or the callable is invoked.
    """

    @pytest.mark.parametrize("opcode", sorted(_OPCODE_BUILDERS))
    def test_stock_unpickler_executes_the_payload(self, opcode, tmp_path):
        """Teeth: without the guard, this exact payload runs and writes the marker."""
        marker = tmp_path / f"stock_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        pickle.Unpickler(io.BytesIO(payload)).load()
        assert marker.exists(), (
            f"{opcode} payload is not actually armed; the guarded checks below "
            "would be vacuous"
        )

    @pytest.mark.parametrize("opcode", sorted(_OPCODE_BUILDERS))
    def test_restricted_unpickler_refuses_and_does_not_execute(self, opcode, tmp_path):
        marker = tmp_path / f"restricted_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        with pytest.raises(pickle.UnpicklingError) as excinfo:
            RestrictedUnpickler(io.BytesIO(payload)).load()
        _assert_unpickling_error(excinfo)
        assert not marker.exists(), f"{opcode} executed through RestrictedUnpickler"

    @pytest.mark.parametrize("opcode", sorted(_OPCODE_BUILDERS))
    def test_bare_allowlist_unpickler_refuses_and_does_not_execute(
        self, opcode, tmp_path
    ):
        marker = tmp_path / f"allowlist_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        with pytest.raises(pickle.UnpicklingError) as excinfo:
            AllowlistUnpickler(io.BytesIO(payload)).load()
        _assert_unpickling_error(excinfo)
        assert not marker.exists(), f"{opcode} executed through AllowlistUnpickler"


# ===========================================================================
# 2. Persistent id opcodes. Neither unpickler defines persistent_load, so both
#    PERSID and BINPERSID are refused. The stock unpickler refuses them too
#    (no persistent_load either), so they are not a find_class bypass.
# ===========================================================================


class TestPersistentIdOpcodesRefused:
    _PERSID = _PROTO + b"P1\n" + _STOP
    _BINPERSID = b"\x80\x02" + b"K\x01" + b"Q" + _STOP  # int on stack, then BINPERSID

    @pytest.mark.parametrize(
        "payload", [_PERSID, _BINPERSID], ids=["PERSID", "BINPERSID"]
    )
    def test_restricted_refuses_persistent_id(self, payload):
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(payload)).load()

    @pytest.mark.parametrize(
        "payload", [_PERSID, _BINPERSID], ids=["PERSID", "BINPERSID"]
    )
    def test_allowlist_refuses_persistent_id(self, payload):
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(payload)).load()

    @pytest.mark.parametrize(
        "payload", [_PERSID, _BINPERSID], ids=["PERSID", "BINPERSID"]
    )
    def test_stock_also_refuses_so_it_is_not_a_bypass(self, payload):
        """Pinned: the stock unpickler has no persistent_load either, so a
        persistent id opcode cannot smuggle a global past find_class."""
        with pytest.raises(pickle.UnpicklingError):
            pickle.Unpickler(io.BytesIO(payload)).load()


# ===========================================================================
# 3. Dotted and aliased backing module names, resolved straight through the
#    guard classes (a different code path from the nltk.data.load probes).
# ===========================================================================

# Each pair is a code exec / file / process / attribute traversal primitive an
# attacker would name in a GLOBAL. RestrictedUnpickler refuses every global;
# AllowlistUnpickler with no allowlist refuses them as denied or unlisted.
_ALIASED_GLOBALS = [
    ("os.path", "system"),  # os.path is a module alias under the os subtree
    ("os", "popen"),
    ("nt", "system"),  # the Windows os backing module; refused before import
    ("nt", "popen"),
    ("importlib", "import_module"),
    ("pty", "spawn"),
    ("operator", "attrgetter"),
    ("operator", "itemgetter"),
    ("functools", "partial"),
    ("functools", "reduce"),
    ("copyreg", "_reconstructor"),
    ("copyreg", "__newobj__"),
    ("builtins", "getattr"),
    ("builtins", "__import__"),
    ("builtins", "exec"),
    ("builtins", "eval"),
    ("builtins", "compile"),
    ("subprocess", "Popen"),
    ("subprocess", "getoutput"),
    ("marshal", "loads"),
    ("_pickle", "loads"),
]

_POSIX_ALIASED_GLOBALS = [
    ("posix", "system"),
    ("posix", "popen"),
    ("_posixsubprocess", "fork_exec"),
]


class TestDottedAndAliasedBackingModules:
    @pytest.mark.parametrize("module,name", _ALIASED_GLOBALS)
    def test_restricted_refuses_every_global(self, module, name):
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(b"")).find_class(module, name)

    @pytest.mark.parametrize("module,name", _ALIASED_GLOBALS)
    def test_bare_allowlist_refuses_every_global(self, module, name):
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(b"")).find_class(module, name)

    @POSIX_ONLY
    @pytest.mark.parametrize("module,name", _POSIX_ALIASED_GLOBALS)
    def test_posix_only_globals_refused(self, module, name):
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(b"")).find_class(module, name)
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(b"")).find_class(module, name)

    def test_end_to_end_alias_reduce_writes_nothing(self, tmp_path):
        """A GLOBAL + REDUCE over an aliased sink is refused at resolution, so the
        callable never runs, even under a bare AllowlistUnpickler."""
        marker = tmp_path / "alias_reduce"
        payload = (
            _PROTO
            + _stack_global("importlib", "import_module")
            + _su("os")
            + b"\x85R"
            + _STOP
        )
        with pytest.raises(pickle.UnpicklingError):
            AllowlistUnpickler(io.BytesIO(payload)).load()
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(payload)).load()
        assert not marker.exists()


# ===========================================================================
# 4. Real scientific stack reduce chains. Import guarded, so a bare runner skips.
# ===========================================================================


class TestRealLibraryGadgetChains:
    def test_numpy_array_is_refused_by_the_restricted_loader(self):
        """The nltk.data.load contract (RestrictedUnpickler) blocks EVERY global,
        so even a benign numpy array (which carries numpy globals) cannot be
        reconstructed. This is the intended restriction, pinned here."""
        numpy = pytest.importorskip("numpy")
        data = pickle.dumps(numpy.array([1.0, 2.0, 3.0]), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(data)).load()

    def test_numpy_save_reduce_is_refused_and_writes_no_file(self, tmp_path):
        numpy = pytest.importorskip("numpy")
        target = tmp_path / "np_written.npy"

        class Evil:
            def __reduce__(self):
                return (numpy.save, (str(target), numpy.arange(3)))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            RestrictedUnpickler(io.BytesIO(payload)).load()
        assert not target.exists() and not (tmp_path / "np_written.npy.npy").exists()

    def test_pandas_read_pickle_refused_under_broad_allow(self, tmp_path):
        pandas = pytest.importorskip("pandas")
        secret = tmp_path / "secret.pkl"
        secret.write_bytes(pickle.dumps({"a": 1}))

        class Evil:
            def __reduce__(self):
                return (pandas.read_pickle, (str(secret),))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                io.BytesIO(payload),
                allowed_modules=("numpy", "scipy", "sklearn", "pandas"),
            )

    def test_scipy_mmwrite_reduce_refused_and_writes_no_file(self, tmp_path):
        numpy = pytest.importorskip("numpy")
        scipy_io = pytest.importorskip("scipy.io")
        target = tmp_path / "written.mtx"

        class Evil:
            def __reduce__(self):
                return (scipy_io.mmwrite, (str(target), numpy.array([[1, 2], [3, 4]])))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                io.BytesIO(payload),
                allowed_modules=("numpy", "scipy", "sklearn", "pandas"),
            )
        assert not target.exists() and not (tmp_path / "written.mtx.mtx").exists()

    def test_sklearn_fetch_openml_refused_under_broad_allow(self):
        datasets = pytest.importorskip("sklearn.datasets")

        class Evil:
            def __reduce__(self):
                return (datasets.fetch_openml, ("mnist_784",))

        payload = pickle.dumps(Evil(), protocol=4)
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                io.BytesIO(payload),
                allowed_modules=("numpy", "scipy", "sklearn", "pandas"),
            )


# ===========================================================================
# 5. chat80 shelf staged under a REGISTERED data root, dbm backend agnostic,
#    with raw opcode bytes injected straight into the dbm.
# ===========================================================================


class _ReduceGadget:
    """A shelf value whose pickle needs a module global (record_execution)."""

    def __init__(self, marker):
        self._marker = marker

    def __reduce__(self):
        return (record_execution, (self._marker,))


class TestChat80ShelveUnderDataRoot:
    def _open_restricted(self, base):
        from nltk.sem.chat80 import _restricted_shelve_open

        return _restricted_shelve_open(base)

    def test_benign_valuations_load_and_gadgets_are_refused(self, restricted_sandbox):
        """The shelf lives inside a registered data root (not /tmp). Sets, tuples
        and frozensets of strings load; a reduce gadget value is refused, and the
        sentinel it would have written never appears."""
        base = os.path.join(restricted_sandbox, "vals")
        marker = os.path.join(restricted_sandbox, "SHELF_PWNED")
        with shelve.open(base, "n") as shelf:
            shelf["adjacent"] = {("chile", "argentina"), ("uk", "france")}
            shelf["size"] = ("uk", "244820")
            shelf["frozen"] = frozenset({("a", "b")})
            shelf["bad"] = _ReduceGadget(marker)

        restricted = self._open_restricted(base)
        try:
            assert restricted["adjacent"] == {("chile", "argentina"), ("uk", "france")}
            assert restricted["size"] == ("uk", "244820")
            assert restricted["frozen"] == frozenset({("a", "b")})
            with pytest.raises(pickle.UnpicklingError):
                _ = restricted["bad"]
        finally:
            restricted.close()
        assert not os.path.exists(marker), "reading the shelf executed a pickle gadget"

    def test_raw_opcode_bytes_injected_into_the_dbm_are_refused(
        self, restricted_sandbox
    ):
        """shelve pickles values itself, so a raw GLOBAL / REDUCE and a raw
        BINPERSID are written directly into the underlying dbm. Both are refused on
        read. Skips only if a backend rejects raw byte assignment here."""
        base = os.path.join(restricted_sandbox, "raw")
        with shelve.open(base, "n") as shelf:
            shelf["ok"] = {("a", "b")}
            try:
                shelf.dict[b"g_global"] = b"cos\nsystem\n(S'echo hi'\ntR."
                shelf.dict[b"g_persid"] = b"\x80\x02K\x01Q."
            except Exception:
                pytest.skip("dbm backend rejects raw byte injection here")

        restricted = self._open_restricted(base)
        try:
            assert restricted["ok"] == {("a", "b")}
            for key in ("g_global", "g_persid"):
                with pytest.raises(pickle.UnpicklingError):
                    _ = restricted[key]
        finally:
            restricted.close()


# ===========================================================================
# 6. Model artifact loads: the transition parser allowlist attacked with opcode
#    variety, plus the nltk.data.load pickle route. Benign models still load.
# ===========================================================================


class TestModelArtifactGadgetRefused:
    def _model_allow(self):
        from nltk.parse.transitionparser import (
            _MODEL_ALLOWED_GLOBALS,
            _MODEL_ALLOWED_MODULES,
        )

        return _MODEL_ALLOWED_GLOBALS, _MODEL_ALLOWED_MODULES

    @pytest.mark.parametrize("opcode", ["INST", "OBJ", "NEWOBJ", "REDUCE", "BUILD"])
    def test_transition_parser_allowlist_refuses_every_opcode_gadget(
        self, opcode, tmp_path
    ):
        allowed_globals, allowed_modules = self._model_allow()
        marker = tmp_path / f"model_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        with pytest.raises(pickle.UnpicklingError):
            allowlisted_pickle_load(
                io.BytesIO(payload),
                allowed_globals=allowed_globals,
                allowed_modules=allowed_modules,
            )
        assert not marker.exists(), f"{opcode} executed through the model allowlist"

    def test_transition_parser_still_loads_a_real_svc(self):
        numpy = pytest.importorskip("numpy")
        svm = pytest.importorskip("sklearn.svm")
        allowed_globals, allowed_modules = self._model_allow()
        features = numpy.array([[0.0, 1.0], [1.0, 0.0], [1.0, 1.0], [0.0, 0.0]])
        model = svm.SVC().fit(features, [0, 1, 0, 1])
        restored = allowlisted_pickle_load(
            io.BytesIO(pickle.dumps(model)),
            allowed_globals=allowed_globals,
            allowed_modules=allowed_modules,
        )
        assert (model.predict(features) == restored.predict(features)).all()

    @pytest.mark.parametrize("opcode", ["INST", "OBJ", "NEWOBJ", "REDUCE"])
    def test_data_load_pickle_route_refuses_opcode_gadget(
        self, opcode, restricted_sandbox
    ):
        """A .pickle staged inside a data root and read via nltk.data.load
        (RestrictedUnpickler) is refused for each instantiate / call opcode."""
        import nltk.data
        from nltk import pathsec

        marker = os.path.join(restricted_sandbox, f"data_{opcode}")
        name = f"gadget_{opcode}.pickle"
        payload = _OPCODE_BUILDERS[opcode](marker)
        with pathsec.open(
            os.path.join(restricted_sandbox, name), "wb", context="test"
        ) as handle:
            handle.write(payload)
        with pytest.raises(pickle.UnpicklingError):
            nltk.data.load(name, format="pickle", cache=False)
        assert not os.path.exists(marker), f"{opcode} executed through nltk.data.load"

    def test_data_load_pickle_route_loads_a_benign_container(self, restricted_sandbox):
        import nltk.data
        from nltk import pathsec

        value = {"tags": ["NN", "VB"], "counts": (1, 2, 3)}
        with pathsec.open(
            os.path.join(restricted_sandbox, "ok.pickle"), "wb", context="test"
        ) as handle:
            pickle.dump(value, handle, protocol=4)
        assert nltk.data.load("ok.pickle", format="pickle", cache=False) == value


# ===========================================================================
# 7. Benign over block controls: the guards must not refuse ordinary data or a
#    legitimate small model.
# ===========================================================================


class TestBenignControlsLoad:
    @pytest.mark.parametrize(
        "value",
        [
            [1, 2, 3],
            {"a": 1, "b": [2, 3]},
            {1, 2, 3},
            (1, "two", 3.0),
            "plain string",
            123,
            3.14159,
            True,
            False,
            None,
            frozenset({1, 2, 3}),
            {"nested": {"list": [1, {"set": (2, 3)}]}},
        ],
    )
    def test_restricted_unpickler_round_trips_plain_containers(self, value):
        out = RestrictedUnpickler(io.BytesIO(pickle.dumps(value, protocol=4))).load()
        assert out == value

    def test_allowlist_honours_an_exact_pair(self):
        import collections

        data = pickle.dumps(collections.OrderedDict(a=1, b=2))
        out = allowlisted_pickle_load(
            io.BytesIO(data), allowed_globals={("collections", "OrderedDict")}
        )
        assert dict(out) == {"a": 1, "b": 2}

    def test_a_legitimate_punkt_tokenizer_round_trips(self):
        from nltk.tokenize.punkt import PunktSentenceTokenizer, punkt_pickle_load

        tokenizer = PunktSentenceTokenizer()
        tokenizer.train("Dr. Smith arrived. It works! Mr. Jones left.")
        restored = punkt_pickle_load(io.BytesIO(pickle.dumps(tokenizer, protocol=4)))
        assert restored.tokenize("A test. Another one.") == tokenizer.tokenize(
            "A test. Another one."
        )


# ===========================================================================
# 8. Boundary note: the warn only loader is not a security boundary. tbl.demo
#    and chartparser_app read with pickle_load(restricted=False), which warns
#    and then executes by contract. This pins that contract so a future change
#    that routes a restricted path through it (expecting a refusal) is caught,
#    and documents that the refusal guarantee holds only on the restricted path.
# ===========================================================================


class TestWarnOnlyLoaderIsNotASecurityBoundary:
    def test_default_pickle_load_emits_the_security_warning(self):
        payload = pickle.dumps({"benign": [1, 2, 3]}, protocol=4)
        with pytest.warns(RuntimeWarning) as record:
            result = pickle_load(io.BytesIO(payload))
        assert result == {"benign": [1, 2, 3]}
        assert any(PICKLE_WARNING in str(warning.message) for warning in record)

    def test_restricted_pickle_load_refuses_a_gadget(self, tmp_path):
        """The restricted variant (the security boundary) refuses a gadget the
        warn only variant would run."""
        marker = tmp_path / "restricted_flag"
        payload = _payload_reduce(str(marker))
        with pytest.raises(pickle.UnpicklingError):
            pickle_load(io.BytesIO(payload), restricted=True)
        assert not marker.exists()

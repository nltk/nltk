# Natural Language Toolkit: warn-only loader + deserialization sweep attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack harness for the chart-parser app warn-only pickle loads (GHSA-8mgp).

Background: ``nltk.app.chartparser_app`` used to load an operator-chosen chart /
grammar ``.pickle`` (the File menu's "Load Chart" / "Load Grammar") through the
warn-only :func:`nltk.picklesec.pickle_load`, which prints a security warning and
then EXECUTES the pickle. A user tricked into opening a malicious ``.pickle`` chart
gets remote code execution. Every other model loader in the tree was already
routed through an allowlisting unpickler; these three sites were the last
warn-only callers. They now go through
``nltk.app.chartparser_app._load_chart_pickle``,
an :class:`~nltk.picklesec.AllowlistUnpickler` pinned to
:data:`~nltk.app.chartparser_app._CHART_GRAMMAR_ALLOWED_GLOBALS`.

This file proves, with real runs:

* **Teeth.** The exact reduce gadget that a warn-only loader EXECUTES (writes a
  sentinel) is REFUSED by the hardened loader before it runs.
* **Opcode matrix (#3823).** Every instantiate / call opcode that reaches
  ``find_class`` (INST, OBJ, NEWOBJ, NEWOBJ_EX, REDUCE, BUILD), plus a gadget
  hidden in BUILD state and the extension-registry opcodes, is refused with no
  side effect; a stock ``pickle.Unpickler`` runs the same payload (teeth).
* **State abuse / ReDoS / memory bomb are bounded.** No allowlisted chart /
  grammar / tree / feature class carries a compiled regex, so (unlike
  ``nltk.tbl.demo``) there is no ReDoS surface to re-derive; hostile BUILD state
  yields at worst a bounded error; a deep / huge graph loads in bounded time.
* **Benign.** A real ``Tree`` / ``CFG`` / ``FeatureGrammar`` / ``FeatureChart`` /
  ``Chart`` and the ``(chart, tokens)`` tuple ``save_grammar`` writes all load
  correctly through the hardened path.
* **Sweep verdicts.** For every OTHER loader the deserialization sweep found
  (warn-only ``pickle_load`` callers, ``read_str`` / ``texttiling`` ``eval``,
  ``yaml``, ``marshal`` / ``numpy.load`` / ``tarfile`` / bare ``pickle``), a test
  pins the current safe state so a regression is caught.

Cross-platform notes: the module import is guarded with ``importorskip('tkinter')``
so a headless build with no Tk skips cleanly; no Tk widget is ever instantiated
(the load helper is tested directly). POSIX-only globals are guarded with
``skipif``. Pickle fixtures live under the ``pathsec_sandbox`` registered root and
are opened ``"rb"`` / ``"wb"``; the memory-bomb proofs use a subprocess wall-clock
timeout (never a Unix signal) so they run on Windows too.
"""

import io
import os
import pathlib
import pickle
import subprocess
import sys
import textwrap

import pytest

# A headless build with no Tk cannot import the app module at all (it imports
# tkinter at module top); skip the whole file cleanly in that case. No Tk root is
# ever created below, so importing the module is all that is needed.
pytest.importorskip("tkinter")

from nltk.app import chartparser_app as app
from nltk.grammar import CFG, FeatureGrammar
from nltk.parse.chart import ChartParser
from nltk.parse.featurechart import FeatureChartParser
from nltk.picklesec import WarningUnpickler
from nltk.tree import Tree

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX-only global")

_THIS = __name__


# ===========================================================================
# Sentinels: reconstructing any of these writes a marker file. The hardened
# loader must refuse them before that happens; a stock unpickler must run them
# (that is what proves the guarded assertion below is not vacuous).
# ===========================================================================


def record_execution(path=None, *args, **kwargs):
    """Stand-in for an arbitrary-code-execution sink (INST / REDUCE reach it)."""
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


class ReduceOSGadget:
    """A classic reduce gadget: reconstructing it runs ``os.system``."""

    def __init__(self, marker):
        self.marker = marker

    def __reduce__(self):
        # touch the marker to prove code execution on load
        return (os.system, (f"touch {self.marker}",))


# ===========================================================================
# Hand-assembled opcode payloads (mirrors test_attack_deser_rce_expanded).
# ===========================================================================

_PROTO = b"\x80\x04"
_MARK = b"("
_STOP = b"."


def _su(text):
    raw = text.encode()
    return b"\x8c" + bytes([len(raw)]) + raw


def _global(module, name):
    return b"c" + module.encode() + b"\n" + name.encode() + b"\n"


def _stack_global(module, name):
    return _su(module) + _su(name) + b"\x93"


def _payload_inst(marker):
    return _MARK + _su(marker) + b"i" + _THIS.encode() + b"\nrecord_execution\n" + _STOP


def _payload_obj(marker):
    return _MARK + _global(_THIS, "NewObjSentinel") + _su(marker) + b"o" + _STOP


def _payload_newobj(marker):
    return (
        _PROTO
        + _stack_global(_THIS, "NewObjSentinel")
        + _su(marker)
        + b"\x85\x81"
        + _STOP
    )


def _payload_newobj_ex(marker):
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
    return (
        _PROTO
        + _stack_global(_THIS, "record_execution")
        + _su(marker)
        + b"\x85R"
        + _STOP
    )


def _payload_build(marker):
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
        "reached the allowlist, so this proves nothing"
    )


# ===========================================================================
# 1. Teeth: the warn-only loader EXECUTES the gadget; the hardened loader refuses
# ===========================================================================


@POSIX_ONLY
def test_warnonly_loader_executes_gadget_but_hardened_loader_refuses(tmp_path):
    """The precise before/after teeth of this advisory.

    A reduce gadget in a chart / grammar ``.pickle`` file:
    * EXECUTES through the old warn-only ``WarningUnpickler`` (== what
      ``pickle_load`` used to run at the three sites): the sentinel appears, and
    * is REFUSED by the new ``_load_chart_pickle``: the sentinel never appears.
    """
    teeth = tmp_path / "warnonly_executed"
    payload = pickle.dumps(ReduceOSGadget(str(teeth)))

    # BEFORE: the warn-only unpickler warns, then runs the gadget.
    with pytest.warns(RuntimeWarning):
        WarningUnpickler(io.BytesIO(payload)).load()
    assert teeth.exists(), "warn-only loader did not execute the gadget; no teeth"
    teeth.unlink()

    # AFTER: the hardened loader refuses before the gadget can run.
    with pytest.raises(pickle.UnpicklingError) as excinfo:
        app._load_chart_pickle(io.BytesIO(payload))
    _assert_unpickling_error(excinfo)
    assert not teeth.exists(), "hardened loader EXECUTED the gadget (RCE not closed)"


@POSIX_ONLY
def test_gadget_buried_in_a_real_chart_is_refused(tmp_path):
    """A gadget smuggled alongside real chart data (a tuple of a genuine chart and
    the ``os.system`` gadget, the shape ``save_grammar`` pickles) is refused: the
    allowlist gates the gadget global even though the chart classes are allowed."""
    teeth = tmp_path / "buried_executed"
    cfg = CFG.fromstring("S -> NP VP\nNP -> 'I'\nVP -> V NP\nV -> 'saw'\nNP -> 'her'\n")
    chart = ChartParser(cfg).chart_parse("I saw her".split())
    payload = pickle.dumps((chart, ReduceOSGadget(str(teeth))))
    with pytest.raises(pickle.UnpicklingError):
        app._load_chart_pickle(io.BytesIO(payload))
    assert not teeth.exists()


# ===========================================================================
# 2. Opcode matrix (#3823): every find_class opcode is refused, with teeth
# ===========================================================================


class TestOpcodeClassMatrixIsRefused:
    """INST, OBJ, NEWOBJ, NEWOBJ_EX, REDUCE and BUILD all route the reconstructed
    global through ``find_class``. The hardened loader must refuse each before the
    object is built or the callable is invoked, and none may leave a side effect.
    """

    @pytest.mark.parametrize("opcode", sorted(_OPCODE_BUILDERS))
    def test_stock_unpickler_executes_the_payload(self, opcode, tmp_path):
        """Teeth: without the guard, this exact payload runs and writes the marker."""
        marker = tmp_path / f"stock_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        pickle.Unpickler(io.BytesIO(payload)).load()
        assert marker.exists(), f"{opcode} payload is not armed; guarded check vacuous"

    @pytest.mark.parametrize("opcode", sorted(_OPCODE_BUILDERS))
    def test_hardened_loader_refuses_and_does_not_execute(self, opcode, tmp_path):
        marker = tmp_path / f"hardened_{opcode}"
        payload = _OPCODE_BUILDERS[opcode](str(marker))
        with pytest.raises(pickle.UnpicklingError) as excinfo:
            app._load_chart_pickle(io.BytesIO(payload))
        _assert_unpickling_error(excinfo)
        assert not marker.exists(), f"{opcode} executed through the hardened loader"


def test_gadget_hidden_in_build_state_is_refused():
    """A gadget global placed inside a class's BUILD state (not as the top-level
    reduce callable) is still routed through ``find_class`` and refused. Here an
    allowlisted ``Nonterminal`` is given ``os.system`` as a state value."""
    payload = (
        _PROTO
        + _stack_global("nltk.grammar", "Nonterminal")
        + b")"
        + b"\x81"
        + b"}"
        + _su("x")
        + _stack_global("os", "system")
        + b"s"  # SETITEM: {"x": os.system}
        + b"b"  # BUILD
        + _STOP
    )
    with pytest.raises(pickle.UnpicklingError):
        app._load_chart_pickle(io.BytesIO(payload))


def test_extension_registry_opcode_is_refused():
    """The EXT1 extension-registry opcode bypasses ``find_class`` on a warm
    ``copyreg`` cache, so the base unpickler refuses any EXT opcode up front."""
    payload = _PROTO + b"\x82" + b"\x01" + _STOP  # EXT1 code 1
    with pytest.raises(pickle.UnpicklingError):
        app._load_chart_pickle(io.BytesIO(payload))


@pytest.mark.parametrize(
    "module,name",
    [
        ("os", "system"),
        ("subprocess", "Popen"),
        ("builtins", "eval"),
        ("builtins", "exec"),
        ("nltk.tokenize.repp", "ReppTokenizer"),
        ("posix", "system"),
    ],
)
def test_classic_gadget_globals_are_refused(module, name):
    """Every classic code-exec global is refused by name before resolution, even
    though the pickle otherwise names only allowlisted chart / grammar classes."""
    payload = _PROTO + _stack_global(module, name) + b")\x81" + _STOP
    with pytest.raises(pickle.UnpicklingError):
        app._load_chart_pickle(io.BytesIO(payload))


def test_dotted_name_attribute_traversal_is_refused():
    """A dotted ``name`` (GHSA-4489 attribute-traversal RCE) is refused even under
    an allowlisted module, because find_class would getattr-chain it."""
    payload = _PROTO + _stack_global("nltk.grammar", "CFG.__init__") + b")\x81" + _STOP
    with pytest.raises(pickle.UnpicklingError):
        app._load_chart_pickle(io.BytesIO(payload))


# ===========================================================================
# 3. ReDoS surface: N/A here because no allowlisted class carries a regex
# ===========================================================================


def test_no_allowlisted_class_carries_a_compiled_regex():
    """Documents why the tbl-style post-load regex re-derivation is not needed:
    none of the allowlisted chart / grammar / tree / feature classes stores a
    compiled regex on a legitimate instance, so an untrusted file cannot smuggle a
    catastrophic pattern through the allowlisted surface (there is no such surface).

    Instantiate a representative real object for each and assert no attribute on
    it (or on a fresh empty instance) is a compiled ``re`` / ``regex`` Pattern.
    """
    import re

    cfg = CFG.fromstring("S -> NP VP\nNP -> 'I'\nVP -> V NP\nV -> 'saw'\nNP -> 'her'\n")
    fg = FeatureGrammar.fromstring(
        "% start S\nS -> NP[NUM=?n] VP[NUM=?n]\n"
        "NP[NUM=sg] -> 'dog'\nVP[NUM=sg] -> 'runs'\n"
    )
    samples = [
        cfg,
        fg,
        ChartParser(cfg).chart_parse("I saw her".split()),
        FeatureChartParser(fg).chart_parse("dog runs".split()),
        Tree.fromstring("(S (NP I) (VP (V saw) (NP her)))"),
        list(cfg.productions())[0],
    ]
    pattern_types = (type(re.compile("")),)
    try:
        import regex

        pattern_types = pattern_types + (type(regex.compile("")),)
    except Exception:
        pass
    for obj in samples:
        state = getattr(obj, "__dict__", {}) or {}
        for value in state.values():
            assert not isinstance(
                value, pattern_types
            ), f"{type(obj).__name__} carries a compiled regex; ReDoS surface exists"


def test_hostile_build_state_on_allowlisted_class_is_bounded():
    """Hostile BUILD state on an allowlisted class cannot execute code; at worst it
    yields a bounded error when the object is later used. A ``Tree`` reconstructed
    with a wrong-typed ``_label`` loads fine and is inert; using it does not run
    code."""
    payload = (
        _PROTO
        + _stack_global("nltk.tree.tree", "Tree")
        + b")"
        + b"\x81"
        + b"}"
        + _su("_label")
        + _su("HOSTILE")
        + b"s"
        + b"b"
        + _STOP
    )
    obj = app._load_chart_pickle(io.BytesIO(payload))
    assert isinstance(obj, Tree)
    assert obj.label() == "HOSTILE"  # inert data, no execution


# ===========================================================================
# 4. Memory / recursion bomb: loads are bounded (subprocess wall-clock proof)
# ===========================================================================


def _run_child_bounded(pickle_path, wall_timeout):
    """Load ``pickle_path`` through the hardened loader in a child, wall-clock
    bounded. Returns (timed_out, stdout)."""
    env = os.environ.copy()
    pkg_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(app.__file__))))
    )
    env["PYTHONPATH"] = pkg_root + os.pathsep + env.get("PYTHONPATH", "")
    child = textwrap.dedent(
        """
        import io, sys
        from nltk.app import chartparser_app as app
        with open(sys.argv[1], "rb") as fh:
            data = fh.read()
        obj = app._load_chart_pickle(io.BytesIO(data))
        top_len = len(obj) if isinstance(obj, list) else -1
        depth, cur = 0, obj
        while isinstance(cur, list) and cur:
            cur = cur[0]; depth += 1
        print("LOADED", top_len, depth)
        """
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", child, str(pickle_path)],
            capture_output=True,
            text=True,
            timeout=wall_timeout,
            env=env,
        )
        return False, proc.stdout.strip()
    except subprocess.TimeoutExpired:
        return True, ""


def test_deeply_nested_graph_is_bounded(pathsec_sandbox):
    """A very deeply nested list loads in bounded time and does not stack-overflow:
    pickle's APPEND is iterative and the allowlist scan is a single opcode walk."""
    depth = 200_000
    payload = _PROTO + pickle.EMPTY_LIST * depth + pickle.APPEND * (depth - 1) + _STOP
    path = pathsec_sandbox.root / "nested.pcl"
    with open(path, "wb") as fh:
        fh.write(payload)
    timed_out, out = _run_child_bounded(path, wall_timeout=30)
    assert not timed_out, "hardened loader hung / overflowed on a deep graph"
    # out == "LOADED <top_len> <depth>": the whole deep graph materialised.
    assert out.startswith("LOADED"), f"unexpected child output {out!r}"
    reached_depth = int(out.split()[2])
    assert reached_depth >= depth - 1, f"graph not fully loaded: {out!r}"


def test_huge_flat_graph_is_linear(pathsec_sandbox):
    """A large flat list costs memory linear in the pickle size (pickle has no
    billion-laughs amplification), so the hardened loader is bounded."""
    n = 400_000
    payload = (
        _PROTO
        + pickle.EMPTY_LIST
        + pickle.MARK
        + pickle.NONE * n
        + pickle.APPENDS
        + _STOP
    )
    path = pathsec_sandbox.root / "flat.pcl"
    with open(path, "wb") as fh:
        fh.write(payload)
    timed_out, out = _run_child_bounded(path, wall_timeout=30)
    assert not timed_out, "hardened loader hung on a huge flat graph"
    # out == "LOADED <top_len> <depth>"; the flat list's length is the first field.
    assert out.startswith("LOADED"), f"unexpected child output {out!r}"
    assert int(out.split()[1]) == n, f"flat list not fully loaded: {out!r}"


# ===========================================================================
# 5. Benign: real chart / grammar / tree round-trips through the hardened path
# ===========================================================================


def _cfg():
    return CFG.fromstring(
        "S -> NP VP\nNP -> Det N | 'I'\nVP -> V NP\nDet -> 'the'\nN -> 'cat'\n"
        "V -> 'saw'\n"
    )


def _fg():
    return FeatureGrammar.fromstring(
        "% start S\nS -> NP[NUM=?n] VP[NUM=?n]\nNP[NUM=?n] -> N[NUM=?n]\n"
        "VP[NUM=?n] -> V[NUM=?n]\nN[NUM=sg] -> 'dog'\nN[NUM=pl] -> 'dogs'\n"
        "V[NUM=sg] -> 'runs'\nV[NUM=pl] -> 'run'\n"
    )


def test_benign_cfg_loads(pathsec_sandbox):
    grammar = _cfg()
    path = pathsec_sandbox.root / "grammar.pickle"
    with open(path, "wb") as fh:
        pickle.dump(grammar, fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    assert isinstance(loaded, CFG)
    assert set(loaded.productions()) == set(grammar.productions())


def test_benign_feature_grammar_loads(pathsec_sandbox):
    grammar = _fg()
    path = pathsec_sandbox.root / "fgrammar.pickle"
    with open(path, "wb") as fh:
        pickle.dump(grammar, fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    assert isinstance(loaded, FeatureGrammar)
    assert len(loaded.productions()) == len(grammar.productions())


def test_benign_tree_loads(pathsec_sandbox):
    tree = Tree.fromstring("(S (NP (Det the) (N cat)) (VP (V saw) (NP I)))")
    path = pathsec_sandbox.root / "tree.pickle"
    with open(path, "wb") as fh:
        pickle.dump(tree, fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    assert isinstance(loaded, Tree)
    assert loaded == tree
    assert loaded.leaves() == ["the", "cat", "saw", "I"]


def test_benign_chart_loads_and_is_usable(pathsec_sandbox):
    """A real chart (with edges -> non-empty OrderedDicts) round-trips and its
    parse trees are still recoverable, proving the hardening did not break the
    GUI's Load Chart feature."""
    grammar = _cfg()
    chart = ChartParser(grammar).chart_parse("the cat saw I".split())
    expected = {str(t) for t in chart.parses(grammar.start())}
    path = pathsec_sandbox.root / "chart.pickle"
    with open(path, "wb") as fh:
        pickle.dump(chart, fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    from nltk.parse.chart import Chart

    assert isinstance(loaded, Chart)
    assert loaded.num_edges() == chart.num_edges()
    assert {str(t) for t in loaded.parses(grammar.start())} == expected


def test_benign_feature_chart_loads(pathsec_sandbox):
    grammar = _fg()
    fchart = FeatureChartParser(grammar).chart_parse("dogs run".split())
    path = pathsec_sandbox.root / "fchart.pickle"
    with open(path, "wb") as fh:
        pickle.dump(fchart, fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    from nltk.parse.featurechart import FeatureChart

    assert isinstance(loaded, FeatureChart)
    assert loaded.num_edges() == fchart.num_edges()


def test_benign_chart_tokens_tuple_loads(pathsec_sandbox):
    """``save_grammar`` writes ``(self._chart, self._tokens)`` to a ``.pickle``;
    ``load_grammar`` reads it back. The tuple loads through the hardened path."""
    grammar = _cfg()
    tokens = "the cat saw I".split()
    chart = ChartParser(grammar).chart_parse(tokens)
    path = pathsec_sandbox.root / "chart_tokens.pickle"
    with open(path, "wb") as fh:
        pickle.dump((chart, tokens), fh)
    with open(path, "rb") as fh:
        loaded = app._load_chart_pickle(fh)
    assert isinstance(loaded, tuple)
    assert loaded[1] == tokens


# ===========================================================================
# 6. Sweep verdicts: pin every OTHER loader the deserialization audit found
# ===========================================================================

import nltk  # noqa: E402  (used only for its package directory below)

_NLTK_DIR = pathlib.Path(nltk.__file__).parent


def _library_sources():
    """Every nltk ``*.py`` that is library code (excludes the test tree)."""
    test_dir = _NLTK_DIR / "test"
    for path in _NLTK_DIR.rglob("*.py"):
        if test_dir in path.parents or path == test_dir:
            continue
        yield path


def test_no_warnonly_pickle_load_callers_remain_in_library():
    """The core audit finding: the warn-only ``pickle_load`` (which executes after
    warning) now has ZERO callers in library code. It is defined in picklesec.py
    and may be referenced there and in the test tree, but nowhere else. The three
    chartparser_app sites were the last callers and are now allowlisted."""
    import re

    call_re = re.compile(r"(?<![\w.])pickle_load\s*\(")
    offenders = []
    for path in _library_sources():
        if path.name == "picklesec.py":
            continue  # defines it; not a caller
        text = path.read_text(encoding="utf-8")
        if call_re.search(text):
            offenders.append(str(path.relative_to(_NLTK_DIR)))
    assert not offenders, f"warn-only pickle_load still called in: {offenders}"


def test_chartparser_app_uses_allowlisting_loader_not_warnonly_or_bare_pickle():
    """chartparser_app must not call bare ``pickle.load`` or the warn-only
    ``pickle_load``, and must route loads through ``AllowlistUnpickler``."""
    import ast
    import inspect

    src = inspect.getsource(app)
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "pickle"
                and node.func.attr in ("load", "loads")
            ):
                raise AssertionError("chartparser_app calls bare pickle.load(...)")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "pickle_load":
                raise AssertionError("chartparser_app calls warn-only pickle_load(...)")
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert "AllowlistUnpickler" in names
    assert "_load_chart_pickle" in names


def test_no_marshal_load_or_unsafe_yaml_or_numpy_load_in_library():
    """The sweep found no ``marshal.load``, no unsafe ``yaml.load``, no
    ``numpy.load`` and no ``tarfile.open`` in library code. Pin that: a regression
    that introduces one is caught here.

    ``picklesec.py`` (string-literal denylist entries) and ``pathsec.py`` (its
    secured ``ZipFile.extract`` / ``extractall`` overrides, which ARE the archive
    hardening) name these primitives legitimately and are exempt."""
    import re

    banned = {
        "marshal.load": re.compile(r"\bmarshal\.loads?\s*\("),
        "unsafe yaml.load": re.compile(r"\byaml\.(unsafe_load|full_load|load)\s*\("),
        "numpy.load": re.compile(r"\b(numpy|np)\.load\s*\("),
        "tarfile.open": re.compile(r"\btarfile\.open\s*\("),
    }
    exempt = {"picklesec.py", "pathsec.py"}
    offenders = []
    for path in _library_sources():
        if path.name in exempt:
            continue
        text = path.read_text(encoding="utf-8")
        for label, rx in banned.items():
            if rx.search(text):
                # yaml.safe_load contains "load" but the regex requires the exact
                # unsafe spellings, so a hit is a real offender.
                offenders.append(f"{path.relative_to(_NLTK_DIR)}: {label}")
    assert not offenders, f"unsafe loader(s) reintroduced: {offenders}"


def test_data_yaml_path_uses_safe_load():
    """``nltk.data`` reads YAML resources with ``yaml.safe_load`` (no tag /
    object construction). Verify the source and that safe_load refuses a
    ``!!python/object`` tag (so a malicious .yaml resource cannot build objects)."""
    yaml = pytest.importorskip("yaml")
    data_src = (_NLTK_DIR / "data.py").read_text(encoding="utf-8")
    assert "yaml.safe_load" in data_src
    assert "yaml.load(" not in data_src and "unsafe_load" not in data_src
    with pytest.raises(yaml.YAMLError):
        yaml.safe_load("!!python/object/apply:os.system ['echo hi']")


def test_read_str_eval_is_bounded_to_a_string_literal():
    """``nltk.internals.read_str`` uses ``eval`` on a substring the regex has
    bounded to a single quoted string literal (only ``u`` / ``r`` prefixes, no
    ``f``-string), so it returns a ``str`` and cannot execute embedded code.

    Teeth: an injection attempt right after the closing quote is NOT evaluated;
    ``read_str`` stops at the close quote and returns only the literal."""
    from nltk.internals import read_str

    marker = "READ_STR_SHOULD_NOT_RUN"
    # The eval only sees the leading "abc" literal; the trailing expression that
    # would set a global is left unparsed in the stream.
    value, end = read_str(f'"abc" + globals().__setitem__("{marker}", 1)', 0)
    assert value == "abc"
    assert marker not in globals(), "read_str evaluated past the string literal (RCE)"
    # A raw/unicode-prefixed literal still just yields a string.
    assert read_str('r"a\\d+"', 0)[0] == "a\\d+"


def test_texttiling_smooth_rejects_non_allowlisted_window():
    """``texttiling`` builds its smoothing window via ``eval('numpy.'+window+...)``
    but validates ``window`` against a fixed 5-name allowlist first, so an
    injection value raises ``ValueError`` before the eval."""
    np = pytest.importorskip("numpy")
    from nltk.tokenize.texttiling import smooth

    x = np.arange(10.0)
    with pytest.raises(ValueError):
        smooth(x, window_len=5, window="hanning'); __import__('os').system('x')#")
    # a legitimate window name still works
    assert len(smooth(x, window_len=5, window="hanning")) == len(x)

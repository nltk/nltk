import ast
import inspect
import pickle
from pathlib import Path

import pytest

from nltk.parse.chart import Chart
from nltk.picklesec import pickle_load

WARN_RE = r"Security warning: loading pickles can execute arbitrary code"


def test_pickle_load_emits_warning(tmp_path: Path):
    pkl = tmp_path / "obj.pickle"
    with pkl.open("wb") as f:
        pickle.dump(Chart(["a", "b"]), f)

    with pkl.open("rb") as f, pytest.warns(RuntimeWarning, match=WARN_RE):
        obj = pickle_load(f, context="test")

    assert isinstance(obj, Chart)


def test_transitionparser_loads_model_without_warning(tmp_path: Path):
    """TransitionParser.parse() uses AllowlistUnpickler — no RuntimeWarning expected."""
    pytest.importorskip("numpy")
    pytest.importorskip("scipy")
    pytest.importorskip("sklearn")

    from nltk.parse import DependencyGraph
    from nltk.parse.transitionparser import TransitionParser

    model_path = tmp_path / "tp.model"

    gold_sent = DependencyGraph(
        """
Economic  JJ     2      ATT
news  NN     3       SBJ
has       VBD       0       ROOT
little      JJ      5       ATT
effect   NN     3       OBJ
on     IN      5       ATT
financial       JJ       8       ATT
markets    NNS      6       PC
.    .      3       PU
"""
    )

    parser = TransitionParser(TransitionParser.ARC_STANDARD)
    parser.train([gold_sent], str(model_path), verbose=False)

    import warnings

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = parser.parse([gold_sent], str(model_path))

    pickle_warns = [
        w
        for w in caught
        if issubclass(w.category, RuntimeWarning) and WARN_RE in str(w.message)
    ]
    assert not pickle_warns, "parse() must not emit a pickle security warning"
    assert len(result) == 1


def test_chartparser_app_uses_allowlisting_loader():
    # The chart / grammar File-menu loads were hardened from the warn-only
    # ``pickle_load`` (which warns and then EXECUTES a reduce gadget: RCE on opening
    # a malicious file) to an allowlisting unpickler. Headless CI can't instantiate
    # Tk-based UI classes, so assert the invariant statically:
    #   - no bare pickle.load(...) / pickle.loads(...) calls,
    #   - no call to the warn-only pickle_load(...),
    #   - the module references AllowlistUnpickler and its _load_chart_pickle helper.
    import nltk.app.chartparser_app as chartparser_app

    src = inspect.getsource(chartparser_app)
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id == "pickle"
                and node.func.attr in ("load", "loads")
            ):
                raise AssertionError(
                    "Found a bare pickle.load(...) in nltk.app.chartparser_app; "
                    "expected the allowlisting _load_chart_pickle(...)"
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "pickle_load":
                raise AssertionError(
                    "nltk.app.chartparser_app calls the warn-only pickle_load(...); "
                    "expected the allowlisting _load_chart_pickle(...)"
                )

    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert (
        "AllowlistUnpickler" in names
    ), "Expected nltk.app.chartparser_app to route loads through AllowlistUnpickler"
    assert (
        "_load_chart_pickle" in names
    ), "Expected nltk.app.chartparser_app to define/use _load_chart_pickle"

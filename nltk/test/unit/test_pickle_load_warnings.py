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


def test_transitionparser_warns_on_model_unpickle(tmp_path: Path):
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

    with pytest.warns(RuntimeWarning, match=WARN_RE):
        result = parser.parse([gold_sent], str(model_path))

    assert len(result) == 1


def test_chartparser_app_uses_pickle_load_not_pickle_load_standard():
    # Headless CI can't instantiate Tk-based UI classes, so do a static check:
    # - no calls to pickle.load(...)
    # - references pickle_load(...)
    import nltk.app.chartparser_app as chartparser_app

    src = inspect.getsource(chartparser_app)
    tree = ast.parse(src)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "pickle":
                if node.func.attr == "load":
                    raise AssertionError(
                        "Found a call to pickle.load(...) in nltk.app.chartparser_app; expected pickle_load(...)"
                    )

    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert (
        "pickle_load" in names
    ), "Expected nltk.app.chartparser_app to reference pickle_load"

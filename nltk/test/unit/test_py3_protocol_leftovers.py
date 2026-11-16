"""
Python 2 protocol methods (``__getslice__``, ``__nonzero__``) are never called
by Python 3, and some demo/app code still used names that no longer exist.
"""

import xml.etree.ElementTree as ET

import pytest

from nltk.internals import ElementWrapper


def test_elementwrapper_slice_returns_wrapped_elements():
    wrapper = ElementWrapper(ET.fromstring("<a><b/><c/><d/></a>"))

    sliced = wrapper[0:2]
    assert isinstance(sliced, list)
    assert [type(elt) for elt in sliced] == [ElementWrapper, ElementWrapper]
    assert [elt.tag for elt in sliced] == ["b", "c"]
    assert wrapper[1].tag == "c"

    del wrapper[0:1]
    assert [elt.tag for elt in wrapper[:]] == ["c", "d"]


def test_clause_slice_is_a_clause():
    from nltk.inference.resolution import Clause
    from nltk.sem.logic import Expression

    atoms = [Expression.fromstring(x) for x in ["P(x)", "Q(x)", "R(x)"]]
    clause = Clause(atoms)

    assert isinstance(clause[1:], Clause)
    assert list(clause[1:]) == atoms[1:]
    assert clause[0] == atoms[0]


@pytest.mark.parametrize("data, expected", [({}, False), ({"a": 1}, True)])
def test_framenet_future_truth_value(data, expected):
    from nltk.corpus.reader.framenet import Future

    assert bool(Future(lambda: data)) is expected


def test_mace_demo_helpers_parse_assumptions(mocker):
    from nltk.inference import mace

    # Stub out the Mace4 binary; the helpers used to fail before reaching it.
    command = mocker.patch.object(mace, "MaceCommand")
    command.return_value.build_model.return_value = False
    mocker.patch.object(mace, "safe_print")

    mace.test_model_found([("mortal(Socrates)", ["man(Socrates)"])])
    mace.test_transform_output(("mortal(Socrates)", ["man(Socrates)"]))

    assert command.call_count == 2


def test_wordnet_app_unknown_wx_help_page():
    from nltk.app.wordnet_app import get_static_page_by_path

    with pytest.raises(FileNotFoundError):
        get_static_page_by_path("wx_help.html")

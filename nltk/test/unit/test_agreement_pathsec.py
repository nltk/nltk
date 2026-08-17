# Natural Language Toolkit: pathsec sweep attack tests (agreement)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file read hardened in
``nltk.metrics.agreement`` (GHSA-8mgp-746c-j5xp).

The ``__main__`` ``-f`` file read must refuse a path outside the NLTK data
sandbox and read nothing from it.
"""

import runpy
import sys

import pytest

import nltk.pathsec as pathsec

# The ``sandbox`` fixture is provided by nltk/test/unit/conftest.py.


def test_negative_control_open_outside_raises(sandbox):
    """The sandbox is wired correctly: a plain pathsec.open() of the outside
    target must be refused and write nothing."""
    target = sandbox / "neg_control.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


def test_agreement_main_file_read_refuses_outside(sandbox):
    target = sandbox / "evil_annotations.txt"
    target.write_text("a 1 x\n")  # content is irrelevant; read must be refused

    saved_argv = list(sys.argv)
    sys.argv = ["agreement", "-f", str(target)]
    try:
        with pytest.raises(PermissionError):
            # Runs the module's __main__ block in-process so the fixture's
            # ENFORCE / nltk.data.path settings apply to the patched open.
            runpy.run_module("nltk.metrics.agreement", run_name="__main__")
    finally:
        sys.argv = saved_argv

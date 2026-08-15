"""
Path-traversal sweep tests for NLTK infra modules (``harden-bare-open-sweep``).

Covers the sink patched in the sweep that routes a caller-named path through
``nltk.pathsec`` validation:

* ``nltk.xmlsec.parse(filename)`` -- a filename ``source`` is caller-controlled
  data I/O and is now validated against the NLTK data sandbox before either
  XML back end opens it.

Each patched sink must refuse a path that resolves *outside* the configured
data sandbox (GHSA-8mgp-746c-j5xp, CWE-22).
"""

import os
import tempfile
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec
from nltk import xmlsec


def _make_outside_target():
    """A real file OUTSIDE the data sandbox, under the user's home directory.

    Deliberately NOT under a temp dir: pathsec trusts a *private* system temp
    dir as a data root, so a temp-dir target would be (correctly) allowed and
    the negative control would prove nothing.
    """
    outside = Path.home() / f".nltk_sweep_infra_{os.getpid()}"
    outside.write_text("<corpus><item>x</item></corpus>")
    return outside


def test_infra_sinks_refuse_outside_path():
    prev_enforce = pathsec.ENFORCE
    prev_paths = list(nltk.data.path)
    prev_roots = pathsec._ALLOWED_ROOTS_CACHE
    prev_last = pathsec._LAST_DATA_PATHS
    sandbox = tempfile.mkdtemp()
    outside = _make_outside_target()
    try:
        pathsec.ENFORCE = True
        nltk.data.path[:] = [sandbox]
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None

        # NEGATIVE CONTROL: pathsec.open itself must refuse the outside path,
        # proving the sandbox is active for this configuration (if pathsec.open
        # allowed it, an "attack refused" below would be meaningless).
        with pytest.raises((PermissionError, ValueError)):
            pathsec.open(str(outside), "rb")

        # ATTACK: nltk.xmlsec.parse() given a caller-named filename that lands
        # outside the sandbox must be refused before it reads the file -- and
        # regardless of whether defusedxml is installed.
        with pytest.raises((PermissionError, ValueError)):
            xmlsec.parse(str(outside))
    finally:
        pathsec.ENFORCE = prev_enforce
        nltk.data.path[:] = prev_paths
        pathsec._ALLOWED_ROOTS_CACHE = prev_roots
        pathsec._LAST_DATA_PATHS = prev_last
        try:
            outside.unlink()
        except OSError:
            pass

# Natural Language Toolkit: find_file / find_dir CWD hardening
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""find_file / find_dir must not return a CWD-relative match for a bare name.

find_file_iter probes the current working directory for a bare filename before
the configured env vars and searchpath, so an attacker who can write to the CWD
could plant a model, corpus dir or tool there and have NLTK pick it up
(CWE-426 / CWE-427, issue #3624). find_binary already refused this; find_file
and find_dir did not, so a bare find_file("maltparser") returned "maltparser"
resolving against the CWD.

Only a bare name is filtered, and only when the match is not absolute: an
explicit path with a directory component, an absolute path, and an env-var /
searchpath hit (which are absolute) all survive.
"""

import os
import shutil
import tempfile

import pytest

from nltk.internals import find_dir, find_file


@pytest.fixture
def hostile_cwd():
    base = tempfile.mkdtemp(prefix=".nltk_cwd_", dir=os.path.expanduser("~"))
    for name in ("maltparser", "evil.mco"):
        with open(os.path.join(base, name), "w") as handle:
            handle.write("x")
    os.makedirs(os.path.join(base, "evildir"))
    with open(os.path.join(base, "evildir", "x"), "w") as handle:
        handle.write("y")
    saved = os.getcwd()
    os.chdir(base)
    try:
        yield base
    finally:
        os.chdir(saved)
        shutil.rmtree(base, ignore_errors=True)


@pytest.mark.parametrize("name", ["maltparser", "evil.mco"])
def test_find_file_refuses_a_cwd_planted_bare_name(hostile_cwd, name):
    with pytest.raises(LookupError):
        find_file(name)


def test_find_dir_refuses_a_cwd_planted_bare_name(hostile_cwd):
    with pytest.raises(LookupError):
        find_dir("evildir")


def test_an_explicit_relative_path_is_still_honoured(hostile_cwd):
    """A directory component means the caller chose it deliberately."""
    assert find_file("evildir/x") == "evildir/x"


def test_an_absolute_path_is_still_honoured(hostile_cwd):
    absolute = os.path.join(hostile_cwd, "maltparser")
    assert find_file(absolute) == absolute


def test_an_env_var_match_survives_the_filter(hostile_cwd, monkeypatch):
    """The legitimate discovery path: env var -> absolute -> allowed. A file of
    the same bare name in the CWD must not shadow it."""
    target_dir = os.path.join(hostile_cwd, "real")
    os.makedirs(target_dir)
    with open(os.path.join(target_dir, "maltparser"), "w") as handle:
        handle.write("real")
    monkeypatch.setenv("MALT_PARSER", target_dir)
    found = find_file("maltparser", env_vars=("MALT_PARSER",))
    assert os.path.isabs(found)
    assert found.startswith(target_dir)

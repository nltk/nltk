# Natural Language Toolkit: resource-name and staging-prefix guards
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Two small input guards added to ``nltk.data`` for the same "the name that was
validated must be the name that is used" rule.

``find`` refuses a resource name holding an ASCII tab, LF, CR, ``#`` or ``?``.
Python 3.14 made ``url2pathname`` follow the WHATWG URL rules, so it strips those
control characters and truncates at ``#`` / ``?``; the stripping can turn a name
with no ``..`` component into a traversal after validation has already run
(CWE-22). ``make_staging_dir`` refuses a prefix that is a path rather than a
plain filename fragment, so a caller-built prefix cannot place the directory
outside the data root.
"""

import os

import pytest

import nltk.data as data

# find(): characters url2pathname would silently rewrite


@pytest.mark.parametrize(
    "name",
    [
        "corpora\tbrown",
        "corpora\nbrown",
        "corpora\rbrown",
        "corpora#brown",
        "corpora?brown",
    ],
    ids=["tab", "lf", "cr", "hash", "question"],
)
def test_find_rejects_url_rewritten_characters(name, tmp_path):
    """None of these reaches the raw-form traversal check, so before this guard
    they passed validation and were only rewritten later inside url2pathname."""
    with pytest.raises(ValueError):
        data.find(name, paths=[str(tmp_path)])


def test_find_rejects_traversal_created_by_newline_stripping(tmp_path):
    """The headline case: ".\\n./x" holds no ".." run, yet stripping the LF joins
    the dots into "../x", which then escapes the data root (CWE-22)."""
    with pytest.raises(ValueError):
        data.find(".\n./x", paths=[str(tmp_path)])


def test_assert_no_normalized_bypass_allows_a_plain_name():
    """A normal posix-style resource name must pass the guard untouched."""
    assert data._assert_no_normalized_bypass("corpora/brown") is None


# make_staging_dir(): a prefix is a filename fragment, not a path


@pytest.mark.parametrize(
    "prefix",
    ["nltk_/evil", "nltk_\\evil", "nltk_\x00", "../evil"],
    ids=["slash", "backslash", "nul", "dotdot_slash"],
)
def test_make_staging_dir_rejects_path_like_prefix(prefix):
    """A separator or NUL in the prefix could steer the created directory out of
    the data root, so the fragment is refused before any directory is made."""
    with pytest.raises(ValueError):
        data.make_staging_dir(prefix=prefix)


def test_make_staging_dir_accepts_a_plain_prefix(restricted_sandbox):
    """A plain fragment still yields a fresh directory inside the data root."""
    staged = data.make_staging_dir(prefix="nltk_plain_")
    assert os.path.isdir(staged)
    assert os.path.realpath(staged).startswith(os.path.realpath(restricted_sandbox))

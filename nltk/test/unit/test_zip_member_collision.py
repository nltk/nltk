# Natural Language Toolkit: zip member name-collision guard
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Refuse archives whose members collide on a case/normalization-folding FS.

On macOS (APFS) and Windows, ``pkg/Weights.json`` and ``pkg/weights.json``, or an
NFC and NFD spelling of the same name, map to one file: the second silently
overwrites the first. A package could ship a benign ``Weights.json`` for a
reviewer and a colliding ``weights.json`` that replaces it with a poisoned model.
A legitimate archive never contains such a pair, so any collision is refused.
"""

import os
import shutil
import tempfile
import unicodedata
import zipfile

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def sandbox_root(monkeypatch):
    root = tempfile.mkdtemp(prefix="nltk_sandbox_root_")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _extract(root, members, name):
    archive = os.path.join(root, name + ".zip")
    with zipfile.ZipFile(archive, "w") as handle:
        for member, content in members:
            handle.writestr(member, content)
    with pathsec.ZipFile(archive) as handle:
        handle.extractall(os.path.join(root, name))


@pytest.mark.parametrize(
    "members, label",
    [
        ([("pkg/Weights.json", "B"), ("pkg/weights.json", "M")], "case"),
        (
            [
                ("pkg/" + unicodedata.normalize("NFC", "café.json"), "N"),
                ("pkg/" + unicodedata.normalize("NFD", "café.json"), "D"),
            ],
            "nfc-nfd",
        ),
        ([("pkg/file.txt", "x"), ("pkg/ﬁle.txt", "y")], "ligature"),
        ([("a/x.json", "1"), ("A/x.json", "2")], "case-dir"),
    ],
)
def test_colliding_members_are_refused(sandbox_root, members, label):
    with pytest.raises((PermissionError, ValueError)):
        _extract(sandbox_root, members, label)


def test_distinct_members_including_nested_dirs_are_allowed(sandbox_root):
    """Over-block control: same basename in different real directories is fine."""
    _extract(
        sandbox_root,
        [("pkg/a.json", "1"), ("pkg/b.json", "2"), ("pkg/sub/a.json", "3")],
        "ok",
    )
    extracted = os.path.join(sandbox_root, "ok", "pkg")
    assert sorted(os.listdir(extracted)) == ["a.json", "b.json", "sub"]
    assert os.path.exists(os.path.join(extracted, "sub", "a.json"))

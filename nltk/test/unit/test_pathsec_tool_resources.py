# Natural Language Toolkit: pathsec tool/resource guard tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Focused tests for the four caller-supplied path guards in :mod:`nltk.pathsec`.

These guards bound the values NLTK hands to external tools (Stanford, MaltParser,
CRF) and reads from the installed package:

* :func:`validate_tool_dir` bounds a directory a tool writes model files into.
* :func:`validate_tool_path` bounds a single file a tool opens to read or write.
* :func:`validate_model_resource` bounds a value that may be a real path OR a
  jar-internal resource name.

Refusals of blank, NUL and URL-shaped values are checked directly, since they
raise before any containment check. Containment (outside a data root, a ``..``
traversal) is checked through the shared ``sandbox`` / ``restricted_sandbox``
fixtures in ``nltk/test/unit/conftest.py``, which turn enforcement on and pin
``nltk.data.path`` to one throwaway data root. That matters for portability: on
Linux ``tempfile.mkdtemp()`` lands under world-writable ``/tmp``, which pathsec
refuses to trust, so a fixture that registers its own root is the only way these
containment tests pass on Linux, macOS and Windows alike.
"""

import os

import pytest

from nltk.pathsec import (
    validate_model_resource,
    validate_path,
    validate_tool_dir,
    validate_tool_path,
)

# validate_tool_dir


@pytest.mark.parametrize("blank", ["", "   ", "\t"])
def test_validate_tool_dir_refuses_blank_destination(blank):
    """A blank destination silently becomes a directory in the working dir."""
    with pytest.raises(PermissionError):
        validate_tool_dir(blank, context="test")


def test_validate_tool_dir_refuses_nul_byte():
    with pytest.raises(PermissionError):
        validate_tool_dir("models\x00evil", context="test")


@pytest.mark.parametrize(
    "url", ["http://evil/dir", "https://evil/dir", "ftp://evil/dir", "file:///etc"]
)
def test_validate_tool_dir_refuses_url_shaped(url):
    with pytest.raises(PermissionError):
        validate_tool_dir(url, context="test")


def test_validate_tool_dir_refuses_a_directory_outside_the_roots(sandbox):
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_dir(str(sandbox), context="test")


def test_validate_tool_dir_refuses_a_traversal_out_of_the_root(restricted_sandbox):
    escape = os.path.join(restricted_sandbox, "..", "..", "etc")
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_dir(escape, context="test")


def test_validate_tool_dir_allows_a_directory_inside_the_root(restricted_sandbox):
    """Over-block control: a destination inside a data root is returned as-is,
    and it need not exist yet (a tool creates it)."""
    dest = os.path.join(restricted_sandbox, "model_out")
    assert validate_tool_dir(dest, context="test") == dest


# validate_tool_path


def test_validate_tool_path_allows_an_in_root_file(restricted_sandbox):
    target = os.path.join(restricted_sandbox, "model.bin")
    with open(target, "w", encoding="utf-8") as handle:
        handle.write("weights")
    assert validate_tool_path(target, context="test") == target


def test_validate_tool_path_refuses_an_outside_file(sandbox):
    target = sandbox / "model.bin"
    target.write_text("weights")
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_path(str(target), context="test")


def test_validate_tool_path_accepts_a_nonexistent_write_target_in_root(
    restricted_sandbox,
):
    dest = os.path.join(restricted_sandbox, "new_model.bin")
    assert validate_tool_path(dest, context="test", must_exist=False) == dest


@pytest.mark.parametrize("bad", ["-loadClassifier", "../escape", "ok\x00.bin"])
def test_validate_tool_path_refuses_option_traversal_and_nul(bad):
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_path(bad, context="test")


# validate_model_resource


@pytest.mark.parametrize(
    "resource",
    ["edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz", "englishPCFG.ser.gz"],
)
def test_validate_model_resource_passes_bare_resource_names(resource):
    """A jar-internal resource name is neither absolute nor an existing file, so
    it is left untouched rather than bounded to a data root."""
    assert validate_model_resource(resource, context="test") == resource


def test_validate_model_resource_refuses_an_absolute_outside_path(sandbox):
    with pytest.raises((PermissionError, ValueError)):
        validate_model_resource("/etc/passwd", context="test")


@pytest.mark.parametrize("bad", ["-props", "../../etc/passwd", "http://evil/model"])
def test_validate_model_resource_refuses_option_traversal_and_url(bad):
    with pytest.raises((PermissionError, ValueError)):
        validate_model_resource(bad, context="test")


# Review regression locks: the URL-scheme bypass (GHSA-8mgp) and the hardlink
# alias (CWE-59 / GHSA-f794) must stay refused; reworded messages must not weaken them.


@pytest.mark.parametrize(
    "evil",
    [
        "http://../../../../etc/passwd",
        "https://../../../../etc/passwd",
        "ftp://../../etc/passwd",
        "HTTP://../../etc/passwd",
        "  http://../../etc/passwd",
        "file:///etc/passwd",
        "file://../../etc/passwd",
    ],
)
def test_validate_path_rejects_url_scheme_traversal(restricted_sandbox, evil):
    """GHSA-8mgp-746c-j5xp: a scheme prefix must never authorize a kernel
    traversal. validate_path once returned (authorized) for any '://' http/https/
    ftp string, but 'http://..' is the directory 'http:' then '..', escaping every
    allowed root. restricted_sandbox pins ENFORCE on so the refusal is exercised.
    """
    with pytest.raises((ValueError, PermissionError)):
        validate_path(evil, context="test")


@pytest.mark.parametrize(
    "guard", [validate_model_resource, validate_tool_path, validate_tool_dir]
)
@pytest.mark.parametrize(
    "evil",
    [
        "http://../../etc/passwd",
        "https://evil/x",
        "ftp://evil/x",
        "file:///etc",
        "HTTP://evil/x",
    ],
)
def test_all_caller_guards_reject_url_shapes(guard, evil):
    """Every caller-supplied guard refuses a URL shape whatever the error wording:
    the value is never a filesystem path and the tool would open it verbatim as a
    relative path. Locks the shared URL rejection after the message rewording."""
    with pytest.raises((ValueError, PermissionError)):
        guard(evil, context="test")


@pytest.mark.skipif(
    os.name != "posix", reason="the st_nlink hardlink guard is POSIX-only"
)
def test_validate_tool_path_refuses_a_hardlinked_file(restricted_sandbox):
    """CWE-59 / GHSA-f794 class: a hardlink names an inode that may live outside
    the roots, so a multiply-linked in-root file is refused for a read (the
    open-time st_nlink>1 guard) and a write (the aliased-write guard). Removing
    either check would resurface the hardlink-overwrite bypass."""
    real = os.path.join(restricted_sandbox, "real.bin")
    with open(real, "w", encoding="utf-8") as handle:
        handle.write("weights")
    alias = os.path.join(restricted_sandbox, "alias.bin")
    os.link(real, alias)
    with pytest.raises(PermissionError):
        validate_tool_path(alias, context="test")
    with pytest.raises(PermissionError):
        validate_tool_path(alias, context="test", for_write=True)

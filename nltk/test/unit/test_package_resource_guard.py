# Natural Language Toolkit: package-resource opener
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``pathsec.open_package_resource`` must not become a general read primitive.

It exists for one narrow case: files that ship INSIDE the installed package,
such as ``VERSION``, which sit beside the code and are never in an NLTK data
root, so :func:`validate_path` refuses them.

That makes it a second containment rule rather than an exemption from the
first, and the danger is obvious once stated: it takes the root to contain
against as an argument. A caller passing ``package_root="/"`` would turn it into
"read any file on the machine", which is exactly the bypass the rest of pathsec
exists to prevent, and it is exported, so any caller could do it. The root is
therefore itself bounded to the installed package.
"""

import os
import pathlib
import tempfile

import pytest

import nltk
from nltk.pathsec import open_package_resource

_PACKAGE = pathlib.Path(nltk.__file__).resolve().parent


@pytest.fixture
def outside_secret():
    base = pathlib.Path(
        tempfile.mkdtemp(prefix=".nltk_pkgres_", dir=str(pathlib.Path.home()))
    )
    secret = base / "SECRET"
    secret.write_text("TOP-SECRET")
    try:
        yield secret
    finally:
        import shutil

        shutil.rmtree(base, ignore_errors=True)


@pytest.mark.parametrize(
    "root",
    ["/", "/etc", os.path.join(str(_PACKAGE), ".."), str(pathlib.Path.home())],
    ids=["filesystem-root", "etc", "package-parent", "home"],
)
def test_a_caller_chosen_root_outside_the_package_is_refused(root):
    """The regression this file exists for: an unbounded root read anything."""
    with pytest.raises((PermissionError, ValueError)):
        open_package_resource("/etc/passwd", root, context="test")


def test_the_secret_is_not_readable_through_any_root(outside_secret):
    for root in ("/", str(outside_secret.parent), str(pathlib.Path.home())):
        with pytest.raises((PermissionError, ValueError)):
            open_package_resource(str(outside_secret), root, context="test")


@pytest.mark.parametrize(
    "path",
    [
        "/etc/passwd",
        os.path.join(str(_PACKAGE), "..", "..", "etc", "passwd"),
        os.path.join(str(_PACKAGE), "..", "setup.py"),
    ],
    ids=["absolute", "traversal", "parent-file"],
)
def test_paths_escaping_the_package_are_refused(path):
    """Even with a legitimate root, the path itself may not climb out."""
    with pytest.raises((PermissionError, ValueError)):
        open_package_resource(path, str(_PACKAGE), context="test")


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_a_symlink_planted_in_the_package_is_refused(outside_secret):
    """Containment resolves symlinks, so a link inside the package that points
    out of it does not become a read primitive either."""
    link = _PACKAGE / "_pkgres_test_link"
    try:
        os.symlink(str(outside_secret), link)
    except OSError:  # pragma: no cover - read-only install
        pytest.skip("cannot write into the installed package")
    try:
        with pytest.raises((PermissionError, ValueError)):
            open_package_resource(str(link), str(_PACKAGE), context="test")
    finally:
        if link.is_symlink():
            link.unlink()


@pytest.mark.parametrize("payload", ["", "   ", "VERSION\x00.evil", "-VERSION", "~/x"])
def test_malformed_resource_names_are_refused(payload):
    with pytest.raises((PermissionError, ValueError)):
        open_package_resource(payload, str(_PACKAGE), context="test")


def test_the_legitimate_case_still_works():
    """Over-block control, and the reason the helper exists at all."""
    version_file = _PACKAGE / "VERSION"
    if not version_file.exists():
        pytest.skip("no VERSION file in this checkout")
    with open_package_resource(
        str(version_file), str(_PACKAGE), context="test"
    ) as handle:
        assert handle.read().strip()


def test_nltk_version_is_populated():
    """The guard must not break __version__, which reads VERSION at import.

    A previous attempt used plain pathsec.open here; the data-root check refused
    the package directory and __version__ silently became an error string.
    """
    assert nltk.__version__
    assert "Security Violation" not in nltk.__version__
    assert nltk.__version__[0].isdigit()


class TestRequiredRootOnlyNarrows:
    """``validate_path(required_root=...)`` is the other caller-supplied root.

    Thirty-odd call sites pass one, so if it could WIDEN access it would be a
    bypass available almost everywhere. It is additive by design: Layer 1 is the
    scoped root, Layer 2 is the data roots, and a path must satisfy both. These
    pin that, since making it authoritative would look like a tidy
    simplification to a future reader.
    """

    @pytest.mark.parametrize(
        "target, root",
        [
            ("/etc/passwd", "/etc"),
            ("/etc/passwd", "/"),
        ],
        ids=["etc", "filesystem-root"],
    )
    def test_it_cannot_widen_beyond_the_data_roots(self, pathsec_sandbox, target, root):
        from nltk import pathsec

        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_path(target, context="test", required_root=root)

    def test_it_still_narrows_within_a_data_root(self, pathsec_sandbox):
        from nltk import pathsec

        root, _outside = pathsec_sandbox
        (root / "sub").mkdir()
        (root / "other").mkdir()
        (root / "other" / "f.txt").write_text("x")
        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_path(
                str(root / "other" / "f.txt"),
                context="test",
                required_root=str(root / "sub"),
            )

    def test_a_lying_root_object_cannot_widen(self, pathsec_sandbox):
        """validate_path reads .path in preference to __fspath__, so a root whose
        two answers differ must not be usable to smuggle access."""
        from nltk import pathsec

        root, outside = pathsec_sandbox
        secret = outside / "SECRET"
        secret.write_text("S")

        class _LyingRoot:
            def __init__(self, shown, real):
                self.path = shown
                self._real = real

            def __fspath__(self):
                return self._real

            def __str__(self):
                return self.path

        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_path(
                str(secret),
                context="test",
                required_root=_LyingRoot(str(root), str(outside)),
            )

    @pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
    def test_a_symlinked_root_cannot_widen(self, pathsec_sandbox):
        from nltk import pathsec

        root, outside = pathsec_sandbox
        secret = outside / "SECRET"
        secret.write_text("S")
        link = root / "rrlink"
        os.symlink(str(outside), link)
        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_path(str(secret), context="test", required_root=str(link))

# Natural Language Toolkit: staging a file that ships inside NLTK
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``nltk.data.stage_package_resource`` copies a file that ships inside NLTK,
such as the BNC howto's ``nltk/test/FX8.xml``, into a fresh staging directory
under a data root, where a corpus reader is allowed to open it.

It joins two guards: the read is ``pathsec.open_package_resource`` (contained
in a directory of the installed package) and the write is ``pathsec.open``
into a new ``make_staging_dir`` directory. It must refuse everything either one
refuses, leave nothing behind when it does, and take no destination, so it
can never write where a caller chooses.
"""

import os
import pathlib
import stat

import pytest

import nltk.data
import nltk.test
from nltk import pathsec
from nltk.corpus.reader import BNCCorpusReader
from nltk.data import stage_package_resource
from nltk.test.unit import timing

_TEST_DIR = pathlib.Path(nltk.test.__file__).resolve().parent
_SAMPLE = _TEST_DIR / "FX8.xml"


def _entries(directory):
    return sorted(os.listdir(directory))


@pytest.fixture
def fake_package(pathsec_sandbox, monkeypatch):
    """A stand-in for the installed package, OUTSIDE every data root, so a
    symlink or FIFO can be planted in it without touching the real tree.
    ``open_package_resource`` bounds its root by ``pathsec.__file__``."""
    _root, outside = pathsec_sandbox
    package = outside / "pkg"
    (package / "test").mkdir(parents=True)
    (package / "test" / "sample.txt").write_bytes(b"shipped sample\n")
    monkeypatch.setattr(pathsec, "__file__", str(package / "pathsec.py"))
    return package


def test_a_shipped_sample_is_staged_and_read_back(pathsec_sandbox):
    root, _outside = pathsec_sandbox
    staged = stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="bnc_unit_")
    staged_dir = os.path.dirname(staged)
    assert os.path.basename(staged) == "FX8.xml"
    assert os.path.dirname(staged_dir) == str(root)
    assert os.path.basename(staged_dir).startswith("bnc_unit_")
    with pathsec.open(staged, "rb") as copy:
        assert copy.read() == _SAMPLE.read_bytes()
    if os.name == "posix":
        assert stat.S_IMODE(os.stat(staged_dir).st_mode) == 0o700
        assert stat.S_IMODE(os.stat(staged).st_mode) == 0o600
    bnc = BNCCorpusReader(root=staged_dir, fileids="FX8.xml")
    assert bnc.words()[:6] == ["Ah", "there", "we", "are", ",", "."]
    assert len(bnc.words()) == 151


def test_each_call_gets_its_own_directory(pathsec_sandbox):
    first = stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="twice_")
    second = stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="twice_")
    assert os.path.dirname(first) != os.path.dirname(second)


def test_cleanup_is_passed_through(pathsec_sandbox, monkeypatch):
    registered = []
    monkeypatch.setattr(
        nltk.data.atexit, "register", lambda fn, *args, **kw: registered.append(args)
    )
    stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="keep_", cleanup=False)
    assert registered == []
    gone = stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="gone_")
    assert registered == [(os.path.dirname(gone),)]


@pytest.mark.parametrize(
    "path, why",
    [
        (os.path.abspath(os.path.join(os.sep, "etc", "passwd")), "escapes the package"),
        (str(_TEST_DIR.parent.parent / "setup.py"), "escapes the package"),
        (str(_TEST_DIR.parent / "probability.py"), "escapes the package"),
        (str(_TEST_DIR / "unit" / ".." / "FX8.xml"), "'..' component"),
    ],
    ids=["absolute", "out-of-the-package", "out-of-package-root", "dotdot"],
)
def test_a_path_escaping_the_package_root_is_refused(pathsec_sandbox, path, why):
    root, _outside = pathsec_sandbox
    with pytest.raises(PermissionError, match=why):
        stage_package_resource(path, str(_TEST_DIR), prefix="escape_")
    assert _entries(root) == []


def test_a_package_root_outside_the_package_is_refused(pathsec_sandbox):
    """The helper is no general copy: a file in a data root, or anywhere else,
    is not a package resource whatever root the caller names for it."""
    root, outside = pathsec_sandbox
    secret = outside / "SECRET"
    secret.write_text("TOP-SECRET")
    in_root = root / "data.txt"
    in_root.write_text("data")
    for path, package_root in (
        (secret, outside),
        (secret, pathlib.Path(secret.anchor)),
        (in_root, root),
    ):
        with pytest.raises(PermissionError, match="outside the installed NLTK"):
            stage_package_resource(str(path), str(package_root), prefix="root_")
    assert _entries(root) == ["data.txt"]


def test_the_fake_package_is_a_working_control(fake_package, pathsec_sandbox):
    staged = stage_package_resource(
        str(fake_package / "test" / "sample.txt"),
        str(fake_package / "test"),
        prefix="fake_",
    )
    with pathsec.open(staged, "rb") as copy:
        assert copy.read() == b"shipped sample\n"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_a_symlink_planted_in_the_package_is_refused(fake_package, pathsec_sandbox):
    root, outside = pathsec_sandbox
    secret = outside / "SECRET"
    secret.write_text("TOP-SECRET")
    link = fake_package / "test" / "sample_link.txt"
    try:
        os.symlink(secret, link)
    except OSError:  # pragma: no cover - no symlink privilege on Windows
        pytest.skip("cannot create a symlink here")
    with pytest.raises(PermissionError, match="escapes the package"):
        stage_package_resource(str(link), str(fake_package / "test"), prefix="link_")
    assert _entries(root) == []


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
def test_a_fifo_planted_in_the_package_is_refused_without_blocking(
    fake_package, pathsec_sandbox
):
    root, _outside = pathsec_sandbox
    fifo = fake_package / "test" / "planted.fifo"
    os.mkfifo(fifo)
    finished, exc, _charged = timing.finishes_within(
        10,
        lambda: stage_package_resource(
            str(fifo), str(fake_package / "test"), prefix="fifo_"
        ),
    )
    assert finished, "stage_package_resource blocked on a FIFO"
    assert isinstance(exc, PermissionError) and "not a regular file" in str(exc), exc
    assert _entries(root) == []


def test_a_directory_is_not_staged(pathsec_sandbox):
    root, _outside = pathsec_sandbox
    with pytest.raises(OSError):
        stage_package_resource(str(_TEST_DIR / "unit"), str(_TEST_DIR), prefix="dir_")
    assert _entries(root) == []


def test_a_staging_dir_outside_the_data_roots_is_refused(pathsec_sandbox, monkeypatch):
    """The write is guarded on its own: even if the staging directory were
    outside every data root, pathsec.open refuses the copy."""
    _root, outside = pathsec_sandbox
    elsewhere = outside / "staged"
    elsewhere.mkdir()
    monkeypatch.setattr(
        nltk.data, "make_staging_dir", lambda prefix, cleanup: str(elsewhere)
    )
    with pytest.raises(PermissionError, match="Unauthorized path"):
        stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="out_")
    assert not (elsewhere / "FX8.xml").exists()
    assert not elsewhere.exists()  # the failed staging dir is removed


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
@pytest.mark.parametrize("where", ["outside", "root"])
def test_a_symlink_at_the_destination_is_not_followed(
    pathsec_sandbox, monkeypatch, where
):
    """Outside the roots, or inside one but outside the staging directory
    (the scoped root refuses that), the link's target is never written."""
    root, outside = pathsec_sandbox
    victim = (outside if where == "outside" else root) / "victim.txt"
    victim.write_text("original")
    planted = root / "planted"
    planted.mkdir()
    try:
        os.symlink(victim, planted / "FX8.xml")
    except OSError:  # pragma: no cover - no symlink privilege on Windows
        pytest.skip("cannot create a symlink here")
    monkeypatch.setattr(
        nltk.data, "make_staging_dir", lambda prefix, cleanup: str(planted)
    )
    with pytest.raises((OSError, ValueError)):
        stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="dest_")
    assert victim.read_text() == "original"


def test_an_existing_file_is_not_overwritten(pathsec_sandbox, monkeypatch):
    root, _outside = pathsec_sandbox
    planted = root / "planted"
    planted.mkdir()
    (planted / "FX8.xml").write_text("someone else's file")
    monkeypatch.setattr(
        nltk.data, "make_staging_dir", lambda prefix, cleanup: str(planted)
    )
    with pytest.raises(FileExistsError):
        stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix="exists_")


@pytest.mark.parametrize("prefix", ["../escape_", "a/b_", "nul\x00_"])
def test_a_prefix_cannot_place_the_staging_dir(pathsec_sandbox, prefix):
    root, _outside = pathsec_sandbox
    before = _entries(root.parent)
    with pytest.raises(ValueError, match="filename fragment"):
        stage_package_resource(str(_SAMPLE), str(_TEST_DIR), prefix=prefix)
    assert _entries(root.parent) == before
    assert _entries(root) == []

# Natural Language Toolkit: staging scratch directory security
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""``nltk.data.staging_tempdir`` must stay inside a data root for its whole life.

The wrappers that shell out to an external tool stage an input file first.
Those used to go to the system temp dir, which on Linux is the shared,
world-writable ``/tmp`` and is deliberately not a pathsec root, so the scratch
file landed outside the sandbox. ``staging_tempdir`` fixes that by allocating a
0700 directory inside a data root.

Because it caches that directory in a module global, the cache is only as
trustworthy as the directory it names, which is what these tests attack.
"""

import os
import shutil
import stat

import pytest

import nltk.data
from nltk import pathsec


@pytest.fixture
def fresh_staging(pathsec_sandbox, monkeypatch):
    """A sandbox with no staging dir carried over from another test."""
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    yield pathsec_sandbox
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)


def _inside(path, root):
    return os.path.realpath(str(path)).startswith(os.path.realpath(str(root)))


def test_staging_dir_is_inside_a_root_and_private(fresh_staging):
    root, _outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    assert _inside(staged, root)
    if os.name == "posix":
        assert os.stat(staged).st_mode & 0o077 == 0


def test_staging_dir_is_stable_across_calls(fresh_staging):
    """One directory per process, or every call would leak another."""
    assert nltk.data.staging_tempdir() == nltk.data.staging_tempdir()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_cached_dir_swapped_for_a_symlink_is_discarded(fresh_staging):
    """The regression this file exists for.

    os.path.isdir FOLLOWS symlinks, so removing the cached directory and
    dropping a symlink in its place passed the cache check, and every later
    scratch file landed wherever the link pointed.
    """
    root, outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    shutil.rmtree(staged)
    os.symlink(str(outside), staged)
    assert _inside(nltk.data.staging_tempdir(), root)


def test_poisoned_cache_value_is_discarded(fresh_staging, monkeypatch):
    """A global set to an out-of-root path must not be handed back."""
    root, outside = fresh_staging
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", str(outside), raising=False)
    assert _inside(nltk.data.staging_tempdir(), root)


def test_deleted_cached_dir_is_reallocated(fresh_staging):
    root, _outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    shutil.rmtree(staged)
    assert _inside(nltk.data.staging_tempdir(), root)


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_a_real_scratch_file_cannot_escape_after_a_swap(fresh_staging):
    """End of the chain: what a wrapper actually writes must stay in the root."""
    import tempfile as _tempfile

    root, outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    shutil.rmtree(staged)
    os.symlink(str(outside), staged)
    handle, path = _tempfile.mkstemp(text=True, dir=nltk.data.staging_tempdir())
    os.close(handle)
    assert _inside(path, root), f"scratch file escaped to {path}"


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="requires symlinks")
def test_teeth_isdir_check_alone_would_reopen_the_swap(fresh_staging, monkeypatch):
    """Negative control: restore the old ``os.path.isdir`` test and the swapped
    symlink is accepted again, which is exactly the bug."""
    root, outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    shutil.rmtree(staged)
    os.symlink(str(outside), staged)
    monkeypatch.setattr(
        nltk.data, "_staging_dir_is_still_safe", lambda path: os.path.isdir(path)
    )
    assert not _inside(nltk.data.staging_tempdir(), root)


def test_a_regular_file_in_the_cache_slot_is_discarded(fresh_staging):
    root, _outside = fresh_staging
    staged = nltk.data.staging_tempdir()
    shutil.rmtree(staged)
    with pathsec.open(staged, "w", context="test") as handle:
        handle.write("not a directory")
    assert _inside(nltk.data.staging_tempdir(), root)
    assert stat.S_ISDIR(os.lstat(nltk.data.staging_tempdir()).st_mode)


class TestStagingDirLifetime:
    """make_staging_dir leaked a directory per call for every caller but one.

    The name is unpredictable, so nothing can find it again to clean up: 70 had
    accumulated under the data root on a development machine. Cleanup is opt-in
    rather than automatic because some callers stage a *saved model* there, and
    deleting the user's artifact at exit would be surprising.
    """

    def _run(self, script):
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path)),
        )
        assert result.returncode == 0, result.stderr
        return dict(
            line.split("=", 1)
            for line in result.stdout.strip().splitlines()
            if line.startswith("D")
        )

    def test_cleanup_true_removes_the_dir_at_exit(self):
        paths = self._run(
            "import nltk.data;"
            "print('D=' + nltk.data.make_staging_dir("
            "prefix='nltk_cleanup_t_', cleanup=True))"
        )
        assert not os.path.exists(paths["D"])

    def test_cleanup_defaults_to_keeping_the_dir(self):
        """A saved model must survive the interpreter exiting."""
        paths = self._run(
            "import nltk.data;"
            "print('D=' + nltk.data.make_staging_dir(prefix='nltk_cleanup_f_'))"
        )
        try:
            assert os.path.exists(paths["D"])
        finally:
            shutil.rmtree(paths["D"], ignore_errors=True)

    def test_staging_tempdir_always_cleans_up(self):
        """The shared scratch dir holds only throwaway files."""
        paths = self._run("import nltk.data; print('D=' + nltk.data.staging_tempdir())")
        assert not os.path.exists(paths["D"])

    def test_malt_working_dir_is_cleaned_up(self):
        """MaltParser stages malt_temp.mco there, which is temporary by name."""
        paths = self._run(
            "import nltk.data, nltk.parse.malt as m;"
            "p = m.MaltParser.__new__(m.MaltParser); p._working_dir = None;"
            "print('D=' + p.working_dir)"
        )
        assert not os.path.exists(paths["D"])

# Natural Language Toolkit: jar-sandbox containment regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests for the Stanford/CoreNLP jar sandbox (CWE-426/427/22): the
classpath handed to ``java()`` must be contained in a trusted root, and every
injection vector must be refused up front.

Two guarantees are locked here:

* the classic injection vectors (empty/CWD, relative, NUL, ``os.pathsep``
  smuggling, outside-root, prefix-sibling, symlink escape) are all refused;
* a source checkout trusts ONLY the third-party jar dir (``repo/third``), never
  the whole repo tree, so a stray jar committed or dropped anywhere else under
  the checkout cannot become executable.

Everything runs against the real ``_verify_jar_sandbox`` -- nothing is mocked.
"""

import os

import pytest

from nltk.internals import UntrustedJarError, _verify_jar_sandbox


@pytest.fixture
def only_root(tmp_path, monkeypatch):
    """Pin nltk.data.path to a single throwaway root so containment is
    deterministic (the trust boundary is exactly this dir plus repo/third)."""
    import nltk.data

    root = tmp_path / "nltk_data"
    root.mkdir()
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    return root


class TestInjectionVectorsRefused:
    def test_empty_entry_is_refused(self, only_root):
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([""])

    def test_relative_path_is_refused(self, only_root):
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox(["evil.jar"])

    def test_nul_byte_is_refused(self, only_root):
        good = only_root / "ok.jar"
        good.write_bytes(b"PK\x03\x04")
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([str(good) + "\x00.jar"])

    def test_pathsep_smuggling_is_refused(self, only_root):
        good = only_root / "ok.jar"
        good.write_bytes(b"PK\x03\x04")
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([str(good) + os.pathsep + "/etc/evil.jar"])

    def test_outside_every_root_is_refused(self, only_root):
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox(["/etc/evil.jar"])

    def test_prefix_sibling_is_not_a_child(self, only_root):
        # /root-evil must not be treated as inside /root (commonpath, not prefix).
        sibling = str(only_root) + "-evil"
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([os.path.join(sibling, "x.jar")])

    def test_symlink_escape_is_resolved_before_check(self, only_root):
        link = only_root / "escape.jar"
        os.symlink("/etc/hosts", link)  # target is outside the trusted root
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([str(link)])

    def test_jar_inside_trusted_root_is_accepted(self, only_root):
        good = only_root / "ok.jar"
        good.write_bytes(b"PK\x03\x04")
        _verify_jar_sandbox([str(good)])  # must not raise


class TestRepoTrustIsScopedToThird:
    """A source checkout trusts repo/third only, not the whole tree."""

    def _repo_root(self):
        import nltk

        pkg = os.path.dirname(os.path.realpath(nltk.__file__))
        return os.path.realpath(os.path.join(pkg, ".."))

    def _require_checkout(self, repo_root):
        marker = os.path.join(repo_root, ".git")
        if not (os.path.isdir(marker) or os.path.isfile(marker)):
            pytest.skip("not a source checkout (.git absent)")

    def test_stray_jar_under_repo_root_is_refused(self, tmp_path, monkeypatch):
        import nltk.data

        # Only a throwaway data root is trusted, so the sole thing that could
        # rescue a repo-tree jar is the (now removed) whole-repo trust.
        monkeypatch.setattr(nltk.data, "path", [str(tmp_path)])
        repo_root = self._repo_root()
        self._require_checkout(repo_root)
        stray = os.path.join(repo_root, "build", "evil_%d.jar" % os.getpid())
        with pytest.raises(UntrustedJarError):
            _verify_jar_sandbox([stray])

    def test_jar_under_repo_third_is_trusted(self, tmp_path, monkeypatch):
        import nltk.data

        monkeypatch.setattr(nltk.data, "path", [str(tmp_path)])
        repo_root = self._repo_root()
        self._require_checkout(repo_root)
        third = os.path.join(repo_root, "third")
        created = not os.path.isdir(third)
        os.makedirs(third, exist_ok=True)
        try:
            # Path containment only (the jar need not exist); must not raise.
            _verify_jar_sandbox([os.path.join(third, "stanford-corenlp", "x.jar")])
        finally:
            if created:
                try:
                    os.rmdir(third)
                except OSError:
                    pass

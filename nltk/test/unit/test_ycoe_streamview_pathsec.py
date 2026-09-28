# Natural Language Toolkit: corpus-reader path-containment tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests for two corpus-reader path-containment gaps (CWE-59/22):

* ``YCOECorpusReader`` trusted a ``psd``/``pos`` DIRECTORY symlink (join() does a
  string-prefix check only, not symlink resolution), so it read files outside the
  corpus root (GHSA-qg35-44qx-7vrr).
* ``StreamBackedCorpusView.__init__`` ran a bare ``os.stat`` on a raw string
  fileid, following a symlink and leaking existence/size/mtime of an out-of-root
  path before ``_open`` (GHSA-w674-vqhw-g3pg).

Every attack is staged the way a real corpus lives, inside a registered data
root (on Linux a bare temp dir is not a root, so an unregistered fixture would be
refused for the wrong reason, before the guard under test), and each verdict is
taken from what was actually stat'ed or read, not merely from what raised.
"""

import importlib
import os
import shutil
import zipfile

import pytest

import nltk.corpus.reader.ycoe as ycoe_module
from nltk.corpus.reader.util import StreamBackedCorpusView, read_whitespace_block
from nltk.corpus.reader.ycoe import YCOECorpusReader
from nltk.data import FileSystemPathPointer, ZipFilePathPointer
from nltk.pathsec import validate_path

# ``import nltk.corpus.reader.util as x`` would hand back the package attribute
# ``util``, which a star import in the package shadows with nltk.tokenize.util.
view_util = importlib.import_module("nltk.corpus.reader.util")

# A real file outside every data root; its content is never asserted, only
# whether it was stat'ed. Windows runners have no /etc, so they skip.
OUTSIDE_FILE = "/etc/hosts"

CANARY = "ycoeoutsidecanary"
PSD = "( (IP-MAT (NP-NOM (PRO^N Ic)) (VBP %s) (. .)) (ID cotest,1.1))\n"
POS = "Ic_PRO^N %s_VBP ._. cotest,1.1_ID\n"
REFUSED = (ValueError, PermissionError)


def _write_ycoe(root, token="wat", doc="cotest"):
    """A minimal YCOE layout under ``root``: psd/ and pos/ with one document."""
    for sub, template in (("psd", PSD), ("pos", POS)):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
        with open(os.path.join(root, sub, f"{doc}.{sub}"), "w", encoding="utf8") as f:
            f.write(template % token)
    return root


def _outside_fixture():
    if not os.path.exists(OUTSIDE_FILE):
        pytest.skip("no readable outside-root file on this platform")


class TestYCOEDirSymlinkContainment:
    def test_pos_symlink_escape_is_refused(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        corpus = _write_ycoe(str(root / "ycoe"))
        # replace the real pos/ with a symlink to a pos/ OUTSIDE every root
        _write_ycoe(str(outside / "elsewhere"), token=CANARY)
        shutil.rmtree(os.path.join(corpus, "pos"))
        os.symlink(
            str(outside / "elsewhere" / "pos"),
            os.path.join(corpus, "pos"),
            target_is_directory=True,
        )
        with pytest.raises(REFUSED, match="Security Violation"):
            YCOECorpusReader(corpus)

    def test_sibling_corpus_symlink_is_refused_by_the_scoped_check(
        self, pathsec_sandbox, monkeypatch
    ):
        """A pos/ symlink into ANOTHER corpus inside the same data root passes the
        global sandbox; only the scoped check against the YCOE root catches it.
        With that check removed the sibling corpus is read through the link,
        which is the leak the guard exists to stop."""
        root, _ = pathsec_sandbox
        corpus = _write_ycoe(str(root / "ycoe"))
        sibling = _write_ycoe(str(root / "other"), token=CANARY)
        shutil.rmtree(os.path.join(corpus, "pos"))
        os.symlink(
            os.path.join(sibling, "pos"),
            os.path.join(corpus, "pos"),
            target_is_directory=True,
        )

        with pytest.raises(ValueError, match="escapes root"):
            YCOECorpusReader(corpus)

        monkeypatch.setattr(ycoe_module, "validate_path", lambda *a, **k: None)
        leaked = YCOECorpusReader(corpus).words()
        assert CANARY in leaked, "guard removed but the sibling corpus was not read"

    def test_psd_symlink_is_refused_too(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        corpus = _write_ycoe(str(root / "ycoe"))
        sibling = _write_ycoe(str(root / "other"), token=CANARY)
        shutil.rmtree(os.path.join(corpus, "psd"))
        os.symlink(
            os.path.join(sibling, "psd"),
            os.path.join(corpus, "psd"),
            target_is_directory=True,
        )
        with pytest.raises(ValueError, match="escapes root"):
            YCOECorpusReader(corpus)

    def test_legit_subdir_is_accepted(self, pathsec_sandbox):
        # The fix's building block: a real psd/pos under the root passes the
        # realpath-containment check (kept separate from full-corpus construction).
        # The root is a registered data root: a bare temp dir is not one on Linux.
        root = str(pathsec_sandbox.root / "ycoe")
        os.makedirs(os.path.join(root, "psd"))
        validate_path(
            os.path.join(root, "psd"), context="YCOECorpusReader", required_root=root
        )

    def test_real_layout_reads_end_to_end(self, pathsec_sandbox):
        """BENIGN: a genuine psd/ and pos/ under the corpus root is constructed and
        read through every public accessor, so the guard costs nothing."""
        root, _ = pathsec_sandbox
        reader = YCOECorpusReader(_write_ycoe(str(root / "ycoe")))
        assert reader.fileids() == ["cotest.pos", "cotest.psd"]
        assert reader.documents() == ["cotest"]
        assert list(reader.words()) == ["Ic", "wat", "."]
        assert list(reader.tagged_words())[:2] == [("Ic", "PRO^N"), ("wat", "VBP")]
        assert list(reader.sents()) == [["Ic", "wat", "."]]
        assert [t.leaves() for t in reader.parsed_sents()] == [["Ic", "wat", "."]]

    def test_zip_pointer_root_passes_the_guard(self, pathsec_sandbox):
        """A zipped corpus root is a ZipFilePathPointer: the guard must accept the
        psd/pos entries of an in-root zip (it must not turn zip roots away). The
        reader itself cannot list a zip subdirectory through join() (a pre-existing
        limitation, the same with the guard removed), so only the guard is driven."""
        root, _ = pathsec_sandbox
        os.makedirs(str(root / "corpora"))
        archive = str(root / "corpora" / "ycoe.zip")
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("ycoe/psd/cotest.psd", PSD % "wat")
            zf.writestr("ycoe/pos/cotest.pos", POS % "wat")
        pointer = ZipFilePathPointer(archive, "ycoe/")
        for sub in ("psd/", "pos/"):
            validate_path(
                pointer.join(sub), context="YCOECorpusReader", required_root=pointer
            )


class TestStreamBackedViewStatContainment:
    """The size lookup at construction must never stat an out-of-root path."""

    @staticmethod
    def _stat_spy(monkeypatch):
        seen = []
        real = os.stat

        def spy(path, *args, **kwargs):
            seen.append(os.fspath(path) if not isinstance(path, int) else path)
            return real(path, *args, **kwargs)

        monkeypatch.setattr(os, "stat", spy)
        return seen

    def test_out_of_root_fileid_is_refused_before_stat(self, monkeypatch):
        _outside_fixture()
        seen = self._stat_spy(monkeypatch)
        view = StreamBackedCorpusView(OUTSIDE_FILE, read_whitespace_block)
        assert OUTSIDE_FILE not in seen, "out-of-root fileid was stat'ed"
        assert view._eofpos is None, "a size was learned for an out-of-root path"
        with pytest.raises(REFUSED, match="Security Violation"):
            view._open()
        with pytest.raises(REFUSED, match="Security Violation"):
            list(view)

    def test_out_of_root_pointer_is_refused_before_stat(self, monkeypatch):
        """A FileSystemPathPointer fileid sizes itself with os.stat too; the same
        containment applies before it."""
        _outside_fixture()
        # the pointer constructor's own existence check is not the view's stat
        pointer = FileSystemPathPointer(OUTSIDE_FILE)
        seen = self._stat_spy(monkeypatch)
        view = StreamBackedCorpusView(pointer, read_whitespace_block)
        assert OUTSIDE_FILE not in seen
        assert view._eofpos is None
        with pytest.raises(REFUSED, match="Security Violation"):
            list(view)

    def test_symlink_in_root_is_refused_before_stat(self, pathsec_sandbox, monkeypatch):
        _outside_fixture()
        root, _ = pathsec_sandbox
        link = str(root / "link.txt")
        os.symlink(OUTSIDE_FILE, link)
        seen = self._stat_spy(monkeypatch)
        view = StreamBackedCorpusView(link, read_whitespace_block)
        assert link not in seen and OUTSIDE_FILE not in seen
        assert view._eofpos is None
        with pytest.raises(REFUSED, match="Security Violation"):
            list(view)

    def test_no_existence_oracle_between_missing_and_present_outside_paths(self):
        """Before the fix a missing outside path raised at construction while a
        present one succeeded (an existence oracle); now both construct alike and
        both are refused at the sink."""
        _outside_fixture()
        missing = os.path.join(os.sep, "nonexistent_nltk_root_XYZ_123", "secret.txt")
        views = [
            StreamBackedCorpusView(path, read_whitespace_block)
            for path in (OUTSIDE_FILE, missing)
        ]
        assert [v._eofpos for v in views] == [None, None]
        for view in views:
            with pytest.raises(REFUSED, match="Security Violation"):
                list(view)

    def test_guard_removed_leaks_the_size(self, monkeypatch):
        """Teeth: with the containment check gone the constructor stats the outside
        file and learns its size, which is the leak the check prevents."""
        _outside_fixture()
        monkeypatch.setattr(view_util, "validate_path", lambda *a, **k: None)
        view = StreamBackedCorpusView(OUTSIDE_FILE, read_whitespace_block)
        assert view._eofpos == os.stat(OUTSIDE_FILE).st_size

    def test_in_root_string_and_pointer_still_size_eagerly_and_read(
        self, pathsec_sandbox
    ):
        """BENIGN: an in-root fileid is sized at construction as before and reads."""
        root, _ = pathsec_sandbox
        path = str(root / "ok.txt")
        with open(path, "w", encoding="utf8") as f:
            f.write("a bb ccc")
        for fileid in (path, FileSystemPathPointer(path)):
            view = StreamBackedCorpusView(fileid, read_whitespace_block)
            assert view._eofpos == 8
            assert list(view) == ["a", "bb", "ccc"]

    def test_missing_in_root_file_still_fails_eagerly(self, pathsec_sandbox):
        """BENIGN: a missing file inside the root keeps the historical eager
        ValueError, so a typo in a corpus fileid is still reported at once."""
        root, _ = pathsec_sandbox
        with pytest.raises(ValueError, match="Unable to open or access"):
            StreamBackedCorpusView(str(root / "missing.txt"), read_whitespace_block)

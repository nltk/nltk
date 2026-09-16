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
"""

import os
import tempfile

import pytest


class TestYCOEDirSymlinkContainment:
    def test_pos_symlink_escape_is_refused(self):
        from nltk.corpus.reader.ycoe import YCOECorpusReader

        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "psd"))
        outside = tempfile.mkdtemp()
        os.symlink(outside, os.path.join(root, "pos"))  # pos -> escape the root
        with pytest.raises((ValueError, PermissionError, OSError)):
            YCOECorpusReader(root)

    def test_legit_subdir_is_accepted(self):
        # The fix's building block: a real psd/pos under the root passes the
        # realpath-containment check (kept separate from full-corpus construction).
        from nltk.pathsec import validate_path

        root = tempfile.mkdtemp()
        os.makedirs(os.path.join(root, "psd"))
        validate_path(
            os.path.join(root, "psd"), context="YCOECorpusReader", required_root=root
        )


class TestStreamBackedViewStatContainment:
    def test_out_of_root_fileid_is_refused_before_stat(self):
        from nltk.corpus.reader.util import StreamBackedCorpusView

        # A raw string fileid outside every allowed root must be refused, so the
        # bare os.stat that would leak its size/mtime never runs.
        with pytest.raises((ValueError, PermissionError)):
            StreamBackedCorpusView("/etc/hosts")

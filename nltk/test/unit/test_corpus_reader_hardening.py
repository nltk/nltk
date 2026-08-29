# Natural Language Toolkit: corpus-reader file-IO hardening tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""File-IO hardening for three corpus readers.

This is the corpus-reader slice of the larger GHSA-8mgp effort. It covers only
what those readers changed:

* ``framenet``: ``_reject_unsafe_path_component`` now labels its refusal as a
  "Security violation" so a containment decision is distinguishable from an
  incidental lookup miss (the resolving choke point ``_validate_in_root`` is
  exercised too as an over-block control).
* ``nkjp`` and ``timit``: their scratch tempfiles used to default to the system
  temp dir, which on Linux is the shared, world-writable ``/tmp`` and is
  deliberately not a pathsec data root. They are now pinned to
  ``nltk.data.staging_tempdir()`` so the scratch file lands inside a data root.

The ``restricted_sandbox`` / ``pathsec_sandbox`` fixtures (see the shared
``conftest.py``) enforce pathsec against one throwaway data root registered on
``nltk.data.path``. That registration is what lets these tests run on Linux and
Windows, where a bare temp dir is not a data root, as well as on macOS.
"""

import os

import pytest

from nltk.data import staging_tempdir

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="requires POSIX symlink semantics"
)

_SECRET = "root:x:0:0:SECRET"


# ----------------------------------------------------------------------------
# framenet: the refusal is labelled, and the resolving choke point still holds
# ----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad",
    ["../evil", "a/b", "..", r"sub\evil", "C:evil", r"\\host\share"],
)
def test_framenet_reject_unsafe_component_flags_security_violation(bad):
    from nltk.corpus.reader.framenet import FramenetError, _reject_unsafe_path_component

    with pytest.raises(FramenetError, match="Security violation"):
        _reject_unsafe_path_component(bad, "frame name")


def test_framenet_reject_unsafe_component_accepts_a_plain_name():
    # Over-block control: a name with no separator, "..", or drive is allowed.
    from nltk.corpus.reader.framenet import _reject_unsafe_path_component

    assert _reject_unsafe_path_component("Communication", "frame name") is None


def test_framenet_validate_in_root_refuses_traversal_and_absolute(pathsec_sandbox):
    from nltk.corpus.reader.framenet import _validate_in_root

    root = str(pathsec_sandbox.root)
    outside_secret = os.path.join(str(pathsec_sandbox.outside), "SECRET")
    for locpath in (
        os.path.join(root, "frame", "..", "..", "outside", "SECRET"),
        outside_secret,
    ):
        with pytest.raises((PermissionError, ValueError)):
            _validate_in_root(locpath, root, "test")


@POSIX_ONLY
def test_framenet_validate_in_root_refuses_symlink_escape(pathsec_sandbox):
    from nltk.corpus.reader.framenet import _validate_in_root

    root = str(pathsec_sandbox.root)
    outside = str(pathsec_sandbox.outside)
    with open(os.path.join(outside, "SECRET"), "w", encoding="utf-8") as handle:
        handle.write(_SECRET)
    frame_dir = os.path.join(root, "frame")
    os.makedirs(frame_dir, exist_ok=True)
    symlink = os.path.join(frame_dir, "evil.xml")
    os.symlink(os.path.join(outside, "SECRET"), symlink)
    with pytest.raises((PermissionError, ValueError)):
        _validate_in_root(symlink, root, "test")


def test_framenet_validate_in_root_accepts_an_in_root_path(pathsec_sandbox):
    # Over-block control: a legitimate in-root path must not be refused.
    from nltk.corpus.reader.framenet import _validate_in_root

    root = str(pathsec_sandbox.root)
    frame_dir = os.path.join(root, "frame")
    os.makedirs(frame_dir, exist_ok=True)
    good = os.path.join(frame_dir, "good.xml")
    with open(good, "w", encoding="utf-8") as handle:
        handle.write("<frame/>")
    _validate_in_root(good, root, "test")


# ----------------------------------------------------------------------------
# nkjp: XML_Tool's scratch tempfile is pinned inside a data root
# ----------------------------------------------------------------------------


def test_nkjp_xml_tool_tempfile_is_pinned_to_a_data_root(restricted_sandbox):
    from nltk.corpus.reader.nkjp import XML_Tool

    root = restricted_sandbox
    tool = XML_Tool(root, "header.xml")
    try:
        scratch_dir = os.path.realpath(os.path.dirname(tool.write_file.name))
        assert scratch_dir == os.path.realpath(staging_tempdir())
        assert scratch_dir.startswith(os.path.realpath(root))
    finally:
        tool.write_file.close()
        if os.path.exists(tool.write_file.name):
            os.remove(tool.write_file.name)


# ----------------------------------------------------------------------------
# timit: the wav() scratch tempfile is pinned inside a data root
# ----------------------------------------------------------------------------


def _write_minimal_wav(path):
    import wave

    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(8000)
        handle.writeframes(b"\x00\x00" * 100)


def test_timit_wav_tempfile_is_pinned_to_a_data_root(restricted_sandbox, monkeypatch):
    import tempfile

    from nltk.corpus.reader import timit as timit_module
    from nltk.corpus.reader.timit import TimitCorpusReader
    from nltk.data import FileSystemPathPointer

    root = restricted_sandbox
    speaker_dir = os.path.join(root, "dr1-fabc0")
    os.makedirs(speaker_dir, exist_ok=True)
    _write_minimal_wav(os.path.join(speaker_dir, "sa1.wav"))

    recorded = {}
    real_temporaryfile = tempfile.TemporaryFile

    def recording_temporaryfile(*args, **kwargs):
        recorded["dir"] = kwargs.get("dir")
        return real_temporaryfile(*args, **kwargs)

    monkeypatch.setattr(timit_module.tempfile, "TemporaryFile", recording_temporaryfile)

    reader = TimitCorpusReader(FileSystemPathPointer(root))
    reader.wav("dr1-fabc0/sa1")

    assert recorded["dir"] == staging_tempdir()
    assert os.path.realpath(recorded["dir"]).startswith(os.path.realpath(root))

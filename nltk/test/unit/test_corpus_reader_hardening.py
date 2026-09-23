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
  ``timit.play()``'s pygame branch now runs on Python 3, so it is pinned to
  receive only the bytes ``wav()`` read through pathsec and re-encoded.

The ``restricted_sandbox`` / ``pathsec_sandbox`` fixtures (see the shared
``conftest.py``) enforce pathsec against one throwaway data root registered on
``nltk.data.path``. That registration is what lets these tests run on Linux and
Windows, where a bare temp dir is not a data root, as well as on macOS.
"""

import os
import sys

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


# ----------------------------------------------------------------------------
# timit: play() hands pygame only the bytes wav() already read and re-encoded
# ----------------------------------------------------------------------------


def _timit_reader(root, wav_bytes=None):
    from nltk.corpus.reader.timit import TimitCorpusReader
    from nltk.data import FileSystemPathPointer

    speaker_dir = os.path.join(root, "dr1-fabc0")
    os.makedirs(speaker_dir, exist_ok=True)
    wav_path = os.path.join(speaker_dir, "sa1.wav")
    if wav_bytes is None:
        _write_minimal_wav(wav_path)
    else:
        with open(wav_path, "wb") as handle:
            handle.write(wav_bytes)
    return TimitCorpusReader(FileSystemPathPointer(root))


@pytest.fixture
def pygame_mixer(monkeypatch):
    """The real pygame mixer on SDL's dummy audio driver, with ossaudiodev made
    unimportable so play() takes its pygame branch. Records each Sound() input."""
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    mixer = pytest.importorskip("pygame.mixer")
    monkeypatch.setitem(sys.modules, "ossaudiodev", None)

    played = []
    real_sound = mixer.Sound

    def recording_sound(buffer):
        played.append(buffer.getvalue())
        return real_sound(buffer)

    monkeypatch.setattr(mixer, "Sound", recording_sound)
    yield played
    mixer.quit()


def test_timit_play_reaches_pygame_on_python3(restricted_sandbox, pygame_mixer, capsys):
    # The pygame branch used to import the Python 2 ``StringIO`` module; the
    # ImportError was swallowed and play() always fell through to the
    # "install pygame" message, even with pygame installed.
    reader = _timit_reader(restricted_sandbox)
    reader.play("dr1-fabc0/sa1")

    assert "install pygame" not in capsys.readouterr().err
    assert pygame_mixer == [reader.wav("dr1-fabc0/sa1")]


def test_timit_play_refuses_escaping_utterance_before_pygame(
    pathsec_sandbox, pygame_mixer
):
    reader = _timit_reader(str(pathsec_sandbox.root))
    _write_minimal_wav(os.path.join(str(pathsec_sandbox.outside), "sa1.wav"))
    escaping = os.path.relpath(
        os.path.join(str(pathsec_sandbox.outside), "sa1"), str(pathsec_sandbox.root)
    )

    with pytest.raises((PermissionError, ValueError)):
        reader.play(escaping)
    assert pygame_mixer == []


def test_timit_play_rejects_non_wav_bytes_before_pygame(
    restricted_sandbox, pygame_mixer
):
    # wav() parses the file with the stdlib ``wave`` module and re-encodes it,
    # so bytes that are not a WAV never reach pygame's decoder.
    import wave

    reader = _timit_reader(restricted_sandbox, wav_bytes=b"RIFF\x00\x00\x00\x00junk")

    with pytest.raises((wave.Error, EOFError)):
        reader.play("dr1-fabc0/sa1")
    assert pygame_mixer == []

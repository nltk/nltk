"""
Attack tests for the bare-``open()`` path-traversal hardening
(GHSA-8mgp-746c-j5xp) in the tokenize package:

* ``nltk/tokenize/punkt.py`` -- ``save_punkt_params`` (4 param-file writes; its
  ``dir`` defaults to a fresh private temp) and ``PunktSentenceTokenizer.dump``
  (a debug write that now targets a fresh private temp, not a guessable /tmp).
* ``nltk/tokenize/stanford_segmenter.py`` -- ``StanfordSegmenter._sha256sum``
  (reads a caller-controlled classpath JAR).

Each patched sink is driven with a path OUTSIDE every allowed NLTK data root
and must raise ``PermissionError`` under pathsec ``ENFORCE``, writing nothing
outside the sandbox.
"""

import os
import pathlib
import shutil
import tempfile

import pytest

import nltk.data
import nltk.pathsec as pathsec


@pytest.fixture
def sandbox():
    """Restrict pathsec to a single private data root and hand back a fresh
    directory that is guaranteed OUTSIDE every allowed root.

    The outside directory is created under ``~`` -- never a temp dir, because a
    *private* system temp dir is itself an allowed root on macOS
    (``/var/folders/...`` is mode 0700), so an attack target staged there would
    be (correctly) permitted and the test would not exercise the guard.
    """
    saved_enforce = pathsec.ENFORCE
    saved_path = list(nltk.data.path)
    saved_cache = pathsec._ALLOWED_ROOTS_CACHE
    saved_last = pathsec._LAST_DATA_PATHS

    pathsec.ENFORCE = True
    nltk.data.path[:] = [tempfile.mkdtemp()]
    pathsec._ALLOWED_ROOTS_CACHE = None
    pathsec._LAST_DATA_PATHS = None

    outside = pathlib.Path.home() / f".nltk_sweep_tok_{os.getpid()}"
    outside.mkdir(parents=True, exist_ok=True)
    try:
        yield outside
    finally:
        shutil.rmtree(outside, ignore_errors=True)
        pathsec.ENFORCE = saved_enforce
        nltk.data.path[:] = saved_path
        pathsec._ALLOWED_ROOTS_CACHE = saved_cache
        pathsec._LAST_DATA_PATHS = saved_last


def test_negative_control(sandbox):
    """A plain write to a path outside all allowed roots must be refused -- proof
    that the sandbox is genuinely enforcing in this process."""
    target = sandbox / "control.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


def test_save_punkt_params_refuses_outside_dir(sandbox):
    """``save_punkt_params(dir=<outside>)`` must refuse the caller-controlled
    directory before creating it or writing any of its 4 param files."""
    from nltk.tokenize.punkt import PunktParameters, save_punkt_params

    outside_dir = sandbox / "punkt_tab"
    params = PunktParameters()
    with pytest.raises(PermissionError):
        save_punkt_params(params, dir=str(outside_dir))
    # validate_path rejects up front, so neither the dir nor any file is made.
    assert not outside_dir.exists()
    assert list(sandbox.iterdir()) == []


def test_save_punkt_params_default_is_private_dir_not_tmp(sandbox):
    """The default destination is a fresh private (0700), unpredictably-named
    directory (returned by the call) -- never the old guessable ``/tmp``."""
    from nltk.tokenize.punkt import PunktParameters, save_punkt_params

    out = save_punkt_params(PunktParameters())
    try:
        assert not out.startswith("/tmp/"), "must not default into shared /tmp"
        assert pathsec.is_private_dir(out)
        assert (pathlib.Path(out) / "collocations.tab").exists()
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_punkt_dump_writes_private_temp_not_hardcoded_tmp(sandbox):
    """The ``dump`` debug scaffold must write to a fresh private (0700) temp file
    and return its path -- never the old guessable ``/tmp/punkt.new``."""
    from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktToken

    tok = PunktSentenceTokenizer()
    out = tok.dump(iter([PunktToken("Hello"), PunktToken("world.")]))
    try:
        assert not out.startswith("/tmp/"), "must not write into shared /tmp"
        assert os.path.basename(out) == "punkt.new"
        assert pathsec.is_private_dir(os.path.dirname(out))
        assert os.path.exists(out)
    finally:
        shutil.rmtree(os.path.dirname(out), ignore_errors=True)


def test_stanford_sha256_refuses_outside_jar(sandbox):
    """``StanfordSegmenter._sha256sum`` reads a caller-controlled classpath JAR;
    a path outside all allowed roots must be refused."""
    pytest.importorskip("nltk.tokenize.stanford_segmenter")
    from nltk.tokenize.stanford_segmenter import StanfordSegmenter

    # A real file must exist so os.stat() succeeds and control reaches the
    # patched pathsec_open -- an absent file would raise FileNotFoundError first
    # and mask the security check.
    outside_jar = sandbox / "evil.jar"
    outside_jar.write_bytes(b"PK\x03\x04 not really a jar")

    # Bypass __init__ (which needs a real Stanford JAR on disk); _sha256sum only
    # touches self._jar_sha256_cache.
    seg = StanfordSegmenter.__new__(StanfordSegmenter)
    seg._jar_sha256_cache = {}
    with pytest.raises(PermissionError):
        seg._sha256sum(str(outside_jar))

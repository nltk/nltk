"""
Regression tests for the scratch-file hardening in ``nltk.classify.maxent``
(GHSA-8mgp-746c-j5xp, CWE-377/378).

The external-trainer wrappers ``train_maxent_classifier_with_megam`` and
``TadmMaxentClassifier.train`` used to stage their training / weight files with a
bare ``tempfile.mkstemp`` (no ``dir=``), which lands in the shared, world-writable
system temp on Linux, and they read the tadm weights back through the plain
builtin ``open``. Both now stage inside a private (mode 0700) directory under an
allowed data root via ``nltk.data.make_staging_dir`` and route the read/write
through ``nltk.pathsec.open`` so a path outside the sandbox is refused.

These tests never invoke the real megam / tadm binaries: the external call is
patched out after the scratch file has been created, which is exactly the point
at which the file's location matters.

The "outside" target is a fresh directory under the real ``$HOME`` supplied by the
``pathsec_sandbox`` fixture; never a temp dir, because a private system temp
directory is itself an allowed pathsec root on macOS, which would make a temp
target a false "outside".
"""

import os

import pytest

numpy = pytest.importorskip("numpy")

from nltk.classify import maxent

TRAIN = [
    (dict(a=1, b=1, c=1), "y"),
    (dict(a=1, b=1, c=1), "x"),
    (dict(a=1, b=1, c=0), "y"),
    (dict(a=0, b=1, c=1), "x"),
    (dict(a=0, b=1, c=1), "y"),
    (dict(a=0, b=0, c=1), "y"),
    (dict(a=0, b=1, c=0), "x"),
    (dict(a=0, b=0, c=0), "x"),
    (dict(a=0, b=1, c=1), "y"),
]


def _is_inside(path, root):
    """True iff *path* resolves to a location within *root*."""
    path = os.path.normcase(os.path.realpath(path))
    root = os.path.normcase(os.path.realpath(root))
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        # Different drives on Windows raise; that is genuinely "not inside".
        return False


class _StopBeforeExternalCall(Exception):
    """Raised by the patched trainer to abort once the scratch path is captured."""


def test_megam_training_file_is_staged_inside_a_data_root(
    monkeypatch, restricted_sandbox
):
    """The megam training file must be created inside the enforced data root, not
    on the shared system temp. The un-hardened bare ``mkstemp`` places it in the
    system temp, so this assertion fails against it."""
    data_root = restricted_sandbox
    captured = {}

    def fake_call_megam(options):
        trainfile_name = options[-1]
        captured["path"] = trainfile_name
        captured["exists"] = os.path.exists(trainfile_name)
        raise _StopBeforeExternalCall

    monkeypatch.setattr(maxent, "call_megam", fake_call_megam)

    with pytest.raises(_StopBeforeExternalCall):
        maxent.train_maxent_classifier_with_megam(TRAIN, trace=0)

    assert captured.get("exists"), "megam training file was not created"
    assert _is_inside(
        captured["path"], data_root
    ), f"megam scratch file {captured['path']!r} escaped data root {data_root!r}"


def test_tadm_scratch_files_are_staged_inside_a_data_root(
    monkeypatch, restricted_sandbox
):
    """Both tadm scratch files (events and weights) must be created inside the
    enforced data root. The un-hardened bare ``mkstemp`` calls place them in the
    system temp, so these assertions fail against it."""
    data_root = restricted_sandbox
    captured = {}

    def fake_call_tadm(options):
        captured["events"] = options[options.index("-events_in") + 1]
        captured["params"] = options[options.index("-params_out") + 1]
        raise _StopBeforeExternalCall

    monkeypatch.setattr(maxent, "call_tadm", fake_call_tadm)

    with pytest.raises(_StopBeforeExternalCall):
        maxent.TadmMaxentClassifier.train(TRAIN, trace=0)

    for kind in ("events", "params"):
        assert _is_inside(
            captured[kind], data_root
        ), f"tadm {kind} file {captured[kind]!r} escaped data root {data_root!r}"


def test_megam_write_outside_data_root_is_refused(monkeypatch, pathsec_sandbox):
    """If the scratch file somehow lands outside the sandbox, the pathsec-guarded
    write must refuse it and the external binary must never run. The un-hardened
    plain ``open`` writes it and reaches ``call_megam``, so this test fails
    against it."""
    real_mkstemp = maxent.tempfile.mkstemp

    def fake_mkstemp(*args, **kwargs):
        # Force the scratch file outside every allowed root, ignoring the
        # in-root dir the hardened code asked for.
        return real_mkstemp(prefix="nltk-evil-", dir=str(pathsec_sandbox.outside))

    monkeypatch.setattr(maxent.tempfile, "mkstemp", fake_mkstemp)
    monkeypatch.setattr(
        maxent,
        "call_megam",
        lambda options: pytest.fail("megam ran with an out-of-root scratch file"),
    )

    with pytest.raises(ValueError, match="megam training file"):
        maxent.train_maxent_classifier_with_megam(TRAIN, trace=0)

# Natural Language Toolkit: WekaClassifier model-path attack tests (expanded)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded attack tests for the WekaClassifier model path (GHSA-j456-xh4h-cpf2,
CWE-22 / CWE-73), beyond the cases in ``test_weka_model_path_security.py``.

The model path reaches the weka JVM as ``-l <path>`` (read, from
``classify_many``) or ``-d <path>`` (write, from ``train``). These tests judge
by what the JVM would actually receive: ``config_weka`` is neutralised and
``java`` is replaced by a spy that records ``argv``, so a refused path must
leave the spy untouched while a benign in-root path must reach it verbatim.
Nothing about the containment check itself is mocked.
"""

import os
import socket

import pytest

import nltk.classify.weka as weka_module
import nltk.pathsec as pathsec
from nltk.classify.weka import ARFF_Formatter, WekaClassifier
from nltk.test.unit import timing

FEATS = [({"a": 1}, "pos"), ({"a": 0}, "neg")]
REFUSED = (PermissionError, ValueError)


@pytest.fixture
def jvm_spy(monkeypatch):
    """Record every argv handed to java(); config_weka() needs no weka.jar."""
    seen = []

    def fake_java(cmd, classpath=None, stdout=None, stderr=None, **kwargs):
        seen.append(list(cmd))
        return ("inst#     actual  predicted error prediction\n1 1:pos 1:pos 1\n", "")

    monkeypatch.setattr(weka_module, "config_weka", lambda *a, **k: None)
    monkeypatch.setattr(weka_module, "java", fake_java)
    return seen


def _read_paths(path):
    """The two read-side entry points for a stored model path."""
    yield "construct", lambda: WekaClassifier(None, path)

    def classify():
        clf = object.__new__(WekaClassifier)
        clf._formatter = ARFF_Formatter.from_train(FEATS)
        clf._model = path
        return clf.classify_many([{"a": 1}])

    yield "classify_many", classify


def _assert_never_reaches_jvm(path, jvm_spy):
    for label, call in _read_paths(path):
        with pytest.raises(REFUSED):
            call()
    with pytest.raises(REFUSED):
        WekaClassifier.train(path, FEATS)
    assert jvm_spy == [], f"a refused path reached the JVM argv: {jvm_spy}"


class TestOutsidePathsNeverReachTheJvm:
    def test_absolute_outside_model(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        _assert_never_reaches_jvm(str(outside / "secret.model"), jvm_spy)

    def test_traversal_out_of_the_root(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        escape = os.path.join(
            str(root), "..", os.path.basename(str(outside)), "x.model"
        )
        _assert_never_reaches_jvm(escape, jvm_spy)
        _assert_never_reaches_jvm("../" * 6 + "etc/passwd", jvm_spy)

    def test_symlink_inside_root_to_outside_file(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        target = str(outside / "secret.model")
        with open(target, "wb") as f:
            f.write(b"model bytes")
        link = str(root / "link.model")
        os.symlink(target, link)
        _assert_never_reaches_jvm(link, jvm_spy)

    def test_symlinked_parent_directory(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        os.symlink(str(outside), str(root / "dirlink"), target_is_directory=True)
        _assert_never_reaches_jvm(str(root / "dirlink" / "x.model"), jvm_spy)

    def test_hardlink_inside_root_to_outside_file_write_side(
        self, pathsec_sandbox, jvm_spy
    ):
        """A hardlink cannot be resolved by name; the write side (-d) refuses a
        multiply-linked target so weka cannot overwrite the outside inode."""
        root, outside = pathsec_sandbox
        target = str(outside / "victim.model")
        with open(target, "wb") as f:
            f.write(b"original")
        planted = str(root / "hard.model")
        try:
            os.link(target, planted)
        except OSError:
            pytest.skip("cannot hardlink across these locations")
        with pytest.raises(REFUSED, match="hard links"):
            WekaClassifier.train(planted, FEATS)
        assert jvm_spy == []
        with open(target, "rb") as f:
            assert f.read() == b"original"

    def test_hardlink_read_side_is_refused_too(self, pathsec_sandbox, jvm_spy):
        """The read side (-l) also refuses a multiply-linked model: the tool-path
        check opens the file through the hardened opener, whose st_nlink test
        does not distinguish read from write, so no outside inode is ever named
        on the command line."""
        root, outside = pathsec_sandbox
        target = str(outside / "secret.model")
        with open(target, "wb") as f:
            f.write(b"x")
        planted = str(root / "hard.model")
        try:
            os.link(target, planted)
        except OSError:
            pytest.skip("cannot hardlink across these locations")
        for label, call in _read_paths(planted):
            with pytest.raises(REFUSED, match="multiply-linked|hard links"):
                call()
        assert jvm_spy == []


class _LyingModel(str):
    def __new__(cls, real, shown):
        obj = str.__new__(cls, real)
        obj._shown = shown
        return obj

    def __str__(self):
        return self._shown

    def __repr__(self):
        return repr(self._shown)

    def startswith(self, *a, **k):
        return self._shown.startswith(*a, **k)

    def replace(self, *a, **k):
        return self._shown.replace(*a, **k)

    def split(self, *a, **k):
        return self._shown.split(*a, **k)

    def __contains__(self, item):
        return item in self._shown

    @property
    def path(self):
        return self._shown


class _ShiftingModel:
    def __init__(self, first, then):
        self._answers = [first, then]
        self.calls = 0

    def __fspath__(self):
        self.calls += 1
        return self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]


class TestNamesThatAreNotPlainStrings:
    def test_lying_str_subclass_is_judged_on_real_characters(
        self, pathsec_sandbox, jvm_spy
    ):
        root, outside = pathsec_sandbox
        lying = _LyingModel(str(outside / "secret.model"), str(root / "ok.model"))
        _assert_never_reaches_jvm(lying, jvm_spy)

    def test_lying_option_shaped_subclass_is_refused(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        lying = _LyingModel("-loadModel", str(root / "ok.model"))
        _assert_never_reaches_jvm(lying, jvm_spy)

    def test_shifting_path_like_is_resolved_once_then_used_as_that_string(
        self, pathsec_sandbox, jvm_spy
    ):
        """validate_tool_path calls __fspath__ exactly once and the JVM gets the
        validated string; a second answer pointing outside is never consulted
        for the command line."""
        root, outside = pathsec_sandbox
        shifting = _ShiftingModel(str(root / "ok.model"), str(outside / "secret.model"))
        clf = WekaClassifier(None, shifting)
        # the constructor stores the object; classify re-validates the model:
        # the object's second answer is the outside path and must be refused
        clf._formatter = ARFF_Formatter.from_train(FEATS)
        with pytest.raises(REFUSED):
            clf.classify_many([{"a": 1}])
        assert jvm_spy == []

    def test_bytes_and_none_are_refused(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        with pytest.raises(REFUSED):
            WekaClassifier(None, None)
        with pytest.raises(REFUSED):
            WekaClassifier.train(str(outside / "x.model").encode(), FEATS)
        assert jvm_spy == []


class TestSyntacticallyHostileNames:
    @pytest.mark.parametrize(
        "name",
        ["-loadModel", "--outputFormat", "-d", "-", "-t"],
    )
    def test_option_shaped_in_root_name_is_refused(
        self, pathsec_sandbox, jvm_spy, name
    ):
        """Even inside the root an option-shaped basename could be read by the
        JVM as a flag; the shared name check refuses it before argv is built."""
        root, outside = pathsec_sandbox
        _assert_never_reaches_jvm(name, jvm_spy)

    @pytest.mark.parametrize("bad", ["\n", "\r", "\t", "\x0b", "\x0c", chr(0)])
    def test_control_characters_are_refused(self, pathsec_sandbox, jvm_spy, bad):
        root, outside = pathsec_sandbox
        _assert_never_reaches_jvm(str(root / ("model" + bad + ".bin")), jvm_spy)

    @pytest.mark.parametrize(
        "name", ["~/secret.model", "//server/share/m", "file:///etc/passwd"]
    )
    def test_tilde_unc_and_url_are_refused(self, pathsec_sandbox, jvm_spy, name):
        _assert_never_reaches_jvm(name, jvm_spy)


class TestSpecialAndOversizedFiles:
    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_fifo_at_model_path_is_refused_without_blocking(
        self, pathsec_sandbox, jvm_spy
    ):
        root, outside = pathsec_sandbox
        fifo = str(root / "pipe.model")
        os.mkfifo(fifo)
        finished, exc, _charged = timing.finishes_within(
            10, lambda: _assert_never_reaches_jvm(fifo, jvm_spy)
        )
        assert finished, "the model-path check blocked on a FIFO"
        assert exc is None, exc

    @pytest.mark.skipif(
        os.name != "posix" or not hasattr(socket, "AF_UNIX"), reason="POSIX only"
    )
    def test_unix_socket_at_model_path_is_refused(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        path = str(root / "s.model")
        if len(path) > 100:
            pytest.skip("socket path too long for AF_UNIX here")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(path)
            _assert_never_reaches_jvm(path, jvm_spy)
        finally:
            sock.close()

    def test_huge_sparse_in_root_model_is_passed_by_name_only(
        self, pathsec_sandbox, jvm_spy
    ):
        """A multi-gigabyte in-root model is inside the sandbox, so containment
        accepts it; the check must not read it (it only stats), and the JVM
        receives the name. Size bounding is the tool's own concern."""
        root, outside = pathsec_sandbox
        huge = str(root / "huge.model")
        with open(huge, "wb") as f:
            f.truncate(4 * 1024**3)
        clf = WekaClassifier(ARFF_Formatter.from_train(FEATS), huge)
        clf.classify_many([{"a": 1}])
        assert jvm_spy[0][jvm_spy[0].index("-l") + 1] == huge


class TestBenignInRootPathsReachTheJvmVerbatim:
    def test_read_side_argv_carries_the_in_root_model(self, pathsec_sandbox, jvm_spy):
        root, outside = pathsec_sandbox
        model = str(root / "trained.model")
        with open(model, "wb") as f:
            f.write(b"m")
        clf = WekaClassifier(ARFF_Formatter.from_train(FEATS), model)
        assert clf.classify_many([{"a": 1}]) == ["pos"]
        argv = jvm_spy[0]
        assert argv[argv.index("-l") + 1] == model
        assert all(str(outside) not in token for token in argv)

    def test_write_side_argv_carries_a_not_yet_existing_in_root_model(
        self, pathsec_sandbox, jvm_spy
    ):
        """must_exist=False on train: a fresh in-root destination is accepted and
        handed to the JVM as the -d target."""
        root, outside = pathsec_sandbox
        model = str(root / "fresh.model")
        assert not os.path.exists(model)
        WekaClassifier.train(model, FEATS)
        argv = jvm_spy[0]
        assert argv[argv.index("-d") + 1] == model

    def test_probe_is_fixed_here(self):
        from nltk.test.unit import security_probes as probes

        status, detail = probes.PROBES["GHSA-j456-xh4h-cpf2"]()
        assert status in (probes.FIXED, probes.STATIC), detail

    def test_probe_has_teeth_when_the_tool_path_guard_is_removed(self, monkeypatch):
        """Neuter validate_tool_path inside weka.py; the probe must flip to
        VULNERABLE (an out-of-root -l path is stored), then be FIXED again."""
        from nltk.test.unit import security_probes as probes

        probe = probes.PROBES["GHSA-j456-xh4h-cpf2"]
        status, detail = probe()
        if status == probes.STATIC:
            pytest.skip(detail)
        monkeypatch.setattr(
            weka_module, "validate_tool_path", lambda value, *a, **k: value
        )
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        monkeypatch.undo()
        assert probe()[0] == probes.FIXED
        assert weka_module.validate_tool_path is pathsec.validate_tool_path

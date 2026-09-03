# Natural Language Toolkit: WekaClassifier model-path containment tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""GHSA-j456-xh4h-cpf2: WekaClassifier passed a caller-controlled model path to
the weka JVM (``-d`` write on train, ``-l`` read on classify) with no pathsec
validation, a variant of the GHSA-8mgp-746c-j5xp / CVE-2026-81726 model-artifact
containment class weka.py was left out of. These tests drive the real code paths: the validation
runs before any weka/config lookup, so an out-of-root path is refused with
PermissionError even without weka installed, while a legitimate in-root staged
path still passes. Nothing is mocked."""

import os

import pytest

import nltk.pathsec as ps
from nltk.classify.weka import WekaClassifier
from nltk.data import make_staging_dir

OUT_OF_ROOT = [
    "/tmp/outside_sandbox/evil.model",  # absolute, outside any data root
    "/etc/cron.d/evil",  # absolute write to a sensitive dir
    "../../../home/victim/.ssh/authorized_keys",  # relative traversal
    "/home/victim/secret.model",  # absolute read oracle
    "/etc/passwd",  # absolute read of a sensitive file
    "..\\..\\windows\\system32\\x",  # backslash traversal
]

FEATS = [({"a": 1}, "pos"), ({"a": 0}, "neg")]


@pytest.fixture(autouse=True)
def _enforce():
    old = ps.ENFORCE
    ps.ENFORCE = True
    try:
        yield
    finally:
        ps.ENFORCE = old


class TestWekaWriteContainment:
    @pytest.mark.parametrize("path", OUT_OF_ROOT)
    def test_train_refuses_out_of_root_model(self, path):
        # -d write target: refused before config_weka() / java() is reached.
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier.train(path, FEATS)


class TestWekaReadContainment:
    @pytest.mark.parametrize("path", OUT_OF_ROOT)
    def test_construct_refuses_out_of_root_model(self, path):
        # -l read target is bounded at construction.
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier(None, path)

    @pytest.mark.parametrize("path", OUT_OF_ROOT)
    def test_classify_rechecks_reassigned_model(self, path):
        # even if _model is swapped after construction, classify re-validates.
        clf = object.__new__(WekaClassifier)
        clf._formatter = None
        clf._model = path
        with pytest.raises((PermissionError, ValueError)):
            clf.classify_many([{"a": 1}])


class TestWekaSymlinkEscape:
    def test_construct_refuses_symlink_escaping_the_root(self, tmp_path):
        # a symlink that lives inside a data root but points outside must not be
        # a bypass; validate_tool_path resolves the link before the containment
        # check.
        root = make_staging_dir(prefix="nltk_weka_symtest_")
        link = os.path.join(root, "escape.model")
        try:
            os.symlink("/etc/passwd", link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier(None, link)


SYNTACTICALLY_HOSTILE = [
    "model\x00.bin",  # NUL truncates the path in the JVM's native layer
    "-loadModel",  # option-shaped: would smuggle a second weka flag
    "--outputFormat",  # option-shaped (long form)
    "http://evil.example/model",  # URL, not a local path
    "file:///etc/passwd",  # file URL
]


class TestWekaSyntacticallyHostileModel:
    @pytest.mark.parametrize("path", SYNTACTICALLY_HOSTILE)
    def test_construct_refuses_syntactically_hostile_model(self, path):
        # A NUL/option-shaped/URL model is refused at construction (-l read), by
        # the shared name checks, before any weka/config lookup.
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier(None, path)

    @pytest.mark.parametrize("path", SYNTACTICALLY_HOSTILE)
    def test_train_refuses_syntactically_hostile_model(self, path):
        # Same value as a -d write target: refused before config_weka()/java().
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier.train(path, FEATS)


def _escapes_all_data_roots(path):
    """True if ``path`` resolves outside every pathsec-allowed data root.

    The symlink-escape vector only exists when the link genuinely resolves outside
    the sandbox; on a platform/layout where the chosen "outside" location happens
    to sit inside a data root (some Windows temp setups place pytest's tmp under a
    directory that is also a data root), there is nothing for the guard to refuse.
    Verifying the escape here keeps the assertion honest: where the link truly
    escapes the refusal is still required, so a real gap cannot hide behind a
    platform skip; where it does not escape the test skips instead of asserting a
    refusal that cannot apply.
    """
    resolved = os.path.realpath(path)
    for root in ps._get_allowed_roots():
        try:
            root_resolved = os.path.realpath(str(root))
            # commonpath raises ValueError on different Windows drives / mixed
            # absoluteness, i.e. genuinely not contained -> treat as "outside".
            if os.path.commonpath([resolved, root_resolved]) == root_resolved:
                return False
        except (OSError, ValueError):
            continue
    return True


class TestWekaWriteSymlinkEscape:
    def test_train_refuses_symlink_write_target_escaping_the_root(self, tmp_path):
        # A -d WRITE target that is an in-root symlink to an outside file must be
        # refused: for_write hardening resolves the link before the containment
        # check, so weka cannot be steered into overwriting an outside file.
        root = make_staging_dir(prefix="nltk_weka_wsym_")
        outside = tmp_path / "outside.model"
        outside.write_bytes(b"")
        link = os.path.join(root, "out.model")
        try:
            os.symlink(str(outside), link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
        if not _escapes_all_data_roots(link):
            pytest.skip("symlink target does not resolve outside a data root here")
        with pytest.raises((PermissionError, ValueError)):
            WekaClassifier.train(link, FEATS)


class TestWekaLegitimatePathsPass:
    def test_in_root_model_passes_at_construction(self):
        model = os.path.join(make_staging_dir(prefix="nltk_weka_ok_"), "name.model")
        clf = WekaClassifier(None, model)  # in-root -> validation passes
        assert clf._model == model

    def test_in_root_model_that_does_not_exist_yet_is_accepted(self):
        # must_exist=False: a not-yet-written in-root model validates (containment,
        # not existence, is the property), so a fresh train destination is allowed.
        model = os.path.join(make_staging_dir(prefix="nltk_weka_new_"), "fresh.model")
        assert not os.path.exists(model)
        clf = WekaClassifier(None, model)
        assert clf._model == model

    def test_in_root_train_path_is_not_refused_by_containment(self):
        model = os.path.join(make_staging_dir(prefix="nltk_weka_ok_"), "name.model")
        # validation passes for an in-root path; any subsequent failure is
        # weka-not-installed, NOT a containment refusal.
        try:
            WekaClassifier.train(model, FEATS)
        except PermissionError:
            pytest.fail("in-root model path wrongly refused by containment")
        except Exception:
            pass  # config_weka()/java() failing (no weka) is fine: validation passed

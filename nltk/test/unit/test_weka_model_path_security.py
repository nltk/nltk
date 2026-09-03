# Natural Language Toolkit: WekaClassifier model-path containment tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""GHSA-j456-xh4h-cpf2: WekaClassifier passed a caller-controlled model path to
the weka JVM (``-d`` write on train, ``-l`` read on classify) with no pathsec
validation, a variant of the GHSA-8mgp-746c-j5xp model-artifact containment class
weka.py was left out of. These tests drive the real code paths: the validation
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


class TestWekaLegitimatePathsPass:
    def test_in_root_model_passes_at_construction(self):
        model = os.path.join(make_staging_dir(prefix="nltk_weka_ok_"), "name.model")
        clf = WekaClassifier(None, model)  # in-root -> validation passes
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

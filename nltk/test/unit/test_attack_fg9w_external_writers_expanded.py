# Natural Language Toolkit: external-writer model-path attack tests (fg9w, second pass)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack tests for two more Bllip-type sinks found on the fg9w second pass: a
caller path handed to an external writer with no pathsec guard
(GHSA-fg9w-wfp5-j933, CWE-22 / CWE-59 / CWE-73).

* ``nltk.tbl.demo._demo_plot`` -> ``matplotlib.savefig`` writes the
  caller-supplied ``learning_curve_output`` itself.
* ``nltk.parse.malt.MaltParser.generate_malt_command`` in ``learn`` mode builds
  the ``-c`` argument the MaltParser JVM WRITES the ``.mco`` model to.

Both are writers, so the real teeth is a hardlink planted inside the data root
that aliases a file outside it: ``realpath`` cannot see the alias, only the
``st_nlink > 1`` refusal in ``validate_tool_path(for_write=True)`` can. Every
test drives the real guard; nothing about containment is mocked.
"""

import os

import pytest

import nltk.parse.malt as malt_module
import nltk.pathsec as pathsec

REFUSED = (PermissionError, ValueError)


def _hardlink_in_root_to_outside(root, outside, in_root_name):
    """A regular file OUTSIDE the roots, hardlinked to a name INSIDE a root.

    The returned in-root path passes every name-based containment check, so only
    the ``st_nlink`` refusal stands between the writer and the outside inode.
    """
    secret = outside / "secret_marker"
    secret.write_text("OUTSIDE_MARKER", encoding="utf-8")
    link = root / in_root_name
    os.link(str(secret), str(link))
    return link, secret


# nltk.tbl.demo._demo_plot: matplotlib writes learning_curve_output

_STATS = {"initialerrors": 10, "rulescores": [3, 2], "tokencount": 100}


@pytest.fixture
def demo_plot():
    """``_demo_plot`` with a headless matplotlib, or skip when it is absent."""
    try:
        import matplotlib
    except Exception:
        pytest.skip("matplotlib is not installed")
    matplotlib.use("Agg", force=True)
    from nltk.tbl.demo import _demo_plot

    return _demo_plot


class TestTblDemoPlotOutsideRootIsRefused:
    def test_absolute_outside_path(self, demo_plot, pathsec_sandbox):
        root, outside = pathsec_sandbox
        with pytest.raises(REFUSED):
            demo_plot(str(outside / "curve.png"), _STATS, _STATS)

    def test_traversal_out_of_root(self, demo_plot, pathsec_sandbox):
        root, outside = pathsec_sandbox
        with pytest.raises(REFUSED):
            demo_plot("../" * 6 + "tmp/curve.png", _STATS, _STATS)

    def test_symlink_in_root_pointing_out(self, demo_plot, pathsec_sandbox):
        root, outside = pathsec_sandbox
        (outside / "real").mkdir()
        link = root / "curve.png"
        os.symlink(str(outside / "real" / "curve.png"), str(link))
        with pytest.raises(REFUSED):
            demo_plot(str(link), _STATS, _STATS)

    def test_hardlink_in_root_to_outside_file(self, demo_plot, pathsec_sandbox):
        """The confirmed exploit: an in-root hardlink to an outside file. The
        write must be refused and the outside file must be byte-for-byte intact."""
        root, outside = pathsec_sandbox
        link, secret = _hardlink_in_root_to_outside(root, outside, "curve.png")
        with pytest.raises(REFUSED):
            demo_plot(str(link), _STATS, _STATS)
        assert secret.read_text(encoding="utf-8") == "OUTSIDE_MARKER"

    def test_benign_write_under_clean_root(self, demo_plot, pathsec_sandbox):
        root, outside = pathsec_sandbox
        out = root / "curve.png"
        demo_plot(str(out), _STATS, _STATS)
        assert out.exists() and out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"

    def test_removing_the_guard_lets_the_outside_file_be_written(
        self, demo_plot, pathsec_sandbox, monkeypatch
    ):
        """Teeth: neutering the guard makes the hardlinked write reach the outside
        inode, proving the refusal above is the guard and not an accident."""
        import nltk.tbl.demo as tbl_demo

        root, outside = pathsec_sandbox
        link, secret = _hardlink_in_root_to_outside(root, outside, "curve.png")
        monkeypatch.setattr(tbl_demo, "validate_tool_path", lambda v, *a, **k: v)
        demo_plot(str(link), _STATS, _STATS)
        assert secret.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


# nltk.parse.malt.MaltParser.generate_malt_command: the JVM writes the .mco


def _malt_with_model(model_path, working_dir):
    """A MaltParser whose ``generate_malt_command`` can run without the real tool
    (construction would need the jar); only ``model`` and ``working_dir`` matter."""
    mp = malt_module.MaltParser.__new__(malt_module.MaltParser)
    mp.model = model_path
    mp._working_dir = working_dir
    return mp


def _learn(mp, input_file):
    return mp.generate_malt_command(input_file, mode="learn")


class TestMaltLearnModeModelOutsideRootIsRefused:
    @pytest.fixture
    def in_root_input(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        src = root / "train.conll"
        src.write_text("1\tJohn\t_\tNNP\t_\t_\t2\tSUBJ\t_\t_\n", encoding="utf-8")
        return str(src)

    def test_absolute_outside_model(self, pathsec_sandbox, in_root_input):
        root, outside = pathsec_sandbox
        mp = _malt_with_model(str(outside / "evil.mco"), str(root))
        with pytest.raises(REFUSED):
            _learn(mp, in_root_input)

    def test_traversal_model(self, pathsec_sandbox, in_root_input):
        root, outside = pathsec_sandbox
        mp = _malt_with_model(os.path.join(str(root), "..", "evil.mco"), str(root))
        with pytest.raises(REFUSED):
            _learn(mp, in_root_input)

    def test_symlink_model_pointing_out(self, pathsec_sandbox, in_root_input):
        root, outside = pathsec_sandbox
        (outside / "real.mco").write_text("x", encoding="utf-8")
        link = root / "m.mco"
        os.symlink(str(outside / "real.mco"), str(link))
        mp = _malt_with_model(str(link), str(root))
        with pytest.raises(REFUSED):
            _learn(mp, in_root_input)

    def test_hardlink_model_to_outside_file(self, pathsec_sandbox, in_root_input):
        """The confirmed exploit: the JVM would write the .mco through an in-root
        hardlink onto an outside file. The command build must refuse it first."""
        root, outside = pathsec_sandbox
        link, secret = _hardlink_in_root_to_outside(root, outside, "m.mco")
        mp = _malt_with_model(str(link), str(root))
        with pytest.raises(REFUSED):
            _learn(mp, in_root_input)
        assert secret.read_text(encoding="utf-8") == "OUTSIDE_MARKER"

    def test_benign_model_under_clean_root_builds_command(
        self, pathsec_sandbox, in_root_input
    ):
        """A model name under the root (not yet written) must build the command
        with -w/-c/-i, so a legitimate train is unaffected."""
        root, outside = pathsec_sandbox
        mp = _malt_with_model(os.path.join(str(root), "model.mco"), str(root))
        cmd = _learn(mp, in_root_input)
        assert cmd[0] == "org.maltparser.Malt"
        assert "-w" in cmd and "-c" in cmd and "-i" in cmd

    def test_removing_the_guard_lets_the_hostile_model_build(
        self, pathsec_sandbox, in_root_input, monkeypatch
    ):
        """Teeth: with the guard neutered the hardlinked model builds into the
        command the JVM would then write through."""
        root, outside = pathsec_sandbox
        link, secret = _hardlink_in_root_to_outside(root, outside, "m.mco")
        mp = _malt_with_model(str(link), str(root))
        monkeypatch.setattr(malt_module, "validate_tool_path", lambda v, *a, **k: v)
        cmd = _learn(mp, in_root_input)
        assert "-c" in cmd and os.path.basename(str(link)) in cmd

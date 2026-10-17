"""Regression tests for running the downloader as a module."""

import os
import subprocess
import sys
import textwrap

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


def _run(args):
    env = os.environ.copy()
    env["PYTHONPATH"] = _REPO + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, *args],
        cwd=_REPO,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_module_cli_does_not_warn_that_downloader_is_already_imported():
    # Importing nltk.downloader while the package loads makes runpy warn
    # (#2162). Help exits before any download.
    completed = _run(["-W", "always", "-m", "nltk.downloader", "-h"])
    assert completed.returncode == 0, completed.stderr
    assert "found in sys.modules" not in completed.stderr
    assert "Usage:" in completed.stdout


def test_package_import_leaves_downloader_unloaded_until_used():
    script = textwrap.dedent(
        """
        import importlib.util
        import sys

        import nltk

        assert "nltk.downloader" not in sys.modules
        assert callable(nltk.download)
        assert callable(nltk.download_shell)
        if importlib.util.find_spec("tkinter"):
            assert callable(nltk.download_gui)
        assert "nltk.downloader" not in sys.modules

        from nltk import downloader

        assert "nltk.downloader" in sys.modules

        def fake(*args, **kwargs):
            fake.args = args
            fake.kwargs = kwargs
            return "ok"

        downloader.download = fake
        assert nltk.download("tiny", quiet=True, extract=False) == "ok"
        assert fake.args == ("tiny",)
        assert fake.kwargs["quiet"] is True
        assert fake.kwargs["extract"] is False
        """
    )
    completed = _run(["-c", script])
    assert completed.returncode == 0, completed.stderr

"""GHSA-59f9-gqg8-mqpj [high] : Path traversal in save_maxent_params /
load_maxent_params (CWE-22), the GitHub transfer of Huntr CVE-2026-15367.

Both functions once built paths from a caller-controlled ``tab_dir`` and opened
them with the builtin ``open``, outside the pathsec sandbox. The save side now
validates ``tab_dir`` and writes every parameter file through ``pathsec.open``
(2a92b7182, PR #3759); the load side reads through ``open_datafile`` on a
``PathPointer`` whose ``open`` is ``pathsec.open`` (f2556f9e1). The probe runs
the advisory's attack against a directory under ``$HOME``: never a temp dir,
because the private per-user temp root is a trusted pathsec root on macOS.
"""

import os
import pathlib
import shutil
import tempfile

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-59f9-gqg8-mqpj")
def _maxent_params_outside_root():
    import numpy

    import nltk.pathsec as pathsec
    from nltk.classify.maxent import load_maxent_params, save_maxent_params
    from nltk.data import FileSystemPathPointer

    outside = tempfile.mkdtemp(prefix=".nltk_59f9_", dir=pathlib.Path.home())
    planted = os.path.join(outside, "planted")
    os.mkdir(planted)
    for name, body in (
        ("weights.txt", "0.1\n0.2\n"),
        ("mapping.tab", "a\tb\tc\t0\n"),
        ("labels.txt", "x\ny\n"),
        ("alwayson.tab", ""),
    ):
        pathlib.Path(planted, name).write_text(body, encoding="utf-8")
    saved_to = os.path.join(outside, "saved")
    enforce = pathsec.ENFORCE
    pathsec.ENFORCE = True
    try:
        leaks = []
        try:
            save_maxent_params(
                numpy.array([0.1, 0.2]),
                {("a", "b", "c"): 0},
                ["x"],
                {},
                tab_dir=saved_to,
            )
            leaks.append("save wrote " + repr(sorted(os.listdir(saved_to))))
        except PermissionError:
            pass
        for label, target in (
            ("pointer", FileSystemPathPointer(planted)),
            ("str", planted),
            ("Path", pathlib.Path(planted)),
        ):
            try:
                weights = load_maxent_params(target)[0]
                leaks.append(f"load({label}) read {weights!r}")
            except PermissionError:
                pass
            except (AttributeError, TypeError) as exc:
                # nothing was read, but the refusal must be pathsec's, not a crash
                leaks.append(f"load({label}) crashed instead of refusing: {exc!r:.80}")
        if leaks:
            return VULNERABLE, "; ".join(leaks)
        return FIXED, "save and load outside every data root refused by pathsec"
    finally:
        pathsec.ENFORCE = enforce
        shutil.rmtree(outside, ignore_errors=True)

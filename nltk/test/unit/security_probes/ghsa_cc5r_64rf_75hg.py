"""GHSA-cc5r-64rf-75hg [high] -- Untrusted search path in prover9/mace4 config allows local code execution via relative binary_location (CWE-426, CWE-427)"""

import os
import shutil
import stat
import tempfile

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-cc5r-64rf-75hg")
def _prover9_relative_binary_location():
    """Plant ``./prover9`` and ``./sub/prover9`` in the CWD, then configure the
    prover with relative locations.

    ``config_prover9`` forwarded ``binary_location`` straight to ``find_binary``,
    which honors an explicit relative path, so a planted CWD binary would be run
    by ``_call``'s ``Popen`` (an untrusted search path). It now resolves through
    ``find_binary_absolute`` and accepts only an absolute location, like
    Boxer/Malt/REPP; every relative form must be refused. Mace4 inherits the
    same ``config_prover9``.
    """
    from nltk.inference.prover9 import Prover9

    box = tempfile.mkdtemp()
    for rel in ("prover9", "sub/prover9"):
        target = os.path.join(box, rel)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho PWNED\n")
        os.chmod(target, os.stat(target).st_mode | stat.S_IEXEC)
    old = os.getcwd()
    try:
        os.chdir(box)
        for loc in (".", "./prover9", "sub/prover9"):
            try:
                Prover9().config_prover9(loc)
            except LookupError:
                continue
            return VULNERABLE, "config_prover9(%r) took a CWD-relative binary" % loc
        return FIXED, "every relative binary_location refused (absolute-only)"
    finally:
        os.chdir(old)
        shutil.rmtree(box, ignore_errors=True)

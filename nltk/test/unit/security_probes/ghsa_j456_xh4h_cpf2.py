"""GHSA-j456-xh4h-cpf2 [high] -- WekaClassifier passes an unvalidated model path to the weka JVM"""

import contextlib
import io
import os

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe
from .ghsa_8mgp_746c_j5xp import _outside_dir

FEATS = [({"a": 1}, "pos"), ({"a": 0}, "neg")]


@probe("GHSA-j456-xh4h-cpf2")
def _weka_model_path():
    """The weka ``-l`` read and ``-d`` write model paths must be pathsec-bounded.

    ``WekaClassifier`` was the one ``java()`` wrapper that skipped the
    model-artifact containment every sibling (CRFTagger, MaltParser, Stanford*)
    applies, giving an out-of-root file write (``-d``) and read oracle (``-l``).
    The probe drives the real APIs with a path OUTSIDE every allowed root:

    * read side: ``WekaClassifier(formatter, outside)`` stores the path for a
      later ``-l`` open. Bounded => it is refused at construction; unbounded =>
      it stores the escaping path silently (VULNERABLE) -- observable without
      weka installed.
    * write side: ``WekaClassifier.train(outside, ...)`` must refuse before any
      weka lookup; a security refusal is the fix, a non-security failure only
      means weka is absent so it is not scored against the read verdict.

    A refusal counts only when it is security-marked, so an incidental
    LookupError (weka not installed) is never mistaken for a defence.
    """
    from nltk.classify.weka import WekaClassifier

    with _outside_dir() as outside:
        if outside is None:
            return STATIC, "$HOME is inside an allowed root here; no escape target"
        read_target = os.path.join(str(outside), "secret.model")
        write_target = os.path.join(str(outside), "evil.model")

        # read side (-l): the clean signal, needs no weka.
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                WekaClassifier(None, read_target)
        except Exception as exc:
            if not is_security_rejection(exc):
                return STATIC, f"construction raised non-security {type(exc).__name__}"
        else:
            return VULNERABLE, "WekaClassifier stored an out-of-root -l model path"

        # write side (-d): must also be refused, before config_weka().
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                WekaClassifier.train(write_target, FEATS)
        except Exception as exc:
            if is_security_rejection(exc):
                return FIXED, "WekaClassifier -l and -d refuse out-of-root model paths"
            return (
                FIXED,
                f"-l bounded; -d failed pre-weka ({type(exc).__name__}), path unreached",
            )
        return VULNERABLE, "train() accepted an out-of-root -d model path"

"""GHSA-fg9w-wfp5-j933 [medium]: BllipParser hands caller model paths to the
bllipparser C extension without a pathsec check (CWE-22 / CWE-73 / CWE-400)."""

import os
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, is_security_rejection, probe


class _SpyExtension:
    """Records the paths the bllipparser C extension would open natively."""

    last = None

    def __init__(self):
        type(self).last = self
        self.parser_model = None
        self.reranker = None

    def load_parser_model(self, model_dir, **kw):
        self.parser_model = model_dir

    def load_reranker_model(self, features_filename, weights_filename, **kw):
        self.reranker = (features_filename, weights_filename)


def _unified_shim(model_dir):
    parser = os.path.join(model_dir, "parser")
    return (parser if os.path.exists(parser) else model_dir, None, None)


def _malt_learn_mode_model():
    """Second-pass sibling sink: ``MaltParser.generate_malt_command`` in ``learn``
    mode builds the ``-c`` the JVM WRITES the ``.mco`` to. An outside-root model
    must be refused while the command is built, before any JVM runs. No tool is
    needed: the command builder is a pure function driven on a fabricated
    instance, so this is deterministic on every platform."""
    import nltk.parse.malt as malt

    outside = tempfile.mkdtemp(prefix=".nltk_fg9w_malt_", dir=os.path.expanduser("~"))
    try:
        mp = malt.MaltParser.__new__(malt.MaltParser)
        mp.model = os.path.join(outside, "evil.mco")
        mp._working_dir = outside
        try:
            cmd = mp.generate_malt_command(
                os.path.join(outside, "train.conll"), mode="learn"
            )
        except Exception as exc:
            if is_security_rejection(exc):
                return FIXED, "outside-root learn-mode model refused before the JVM"
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if any(mp.model in str(tok) or "evil.mco" in str(tok) for tok in cmd):
            return VULNERABLE, f"learn-mode command built with outside model {cmd!r}"
        return FIXED, "no outside-root model reached the command"
    finally:
        import shutil

        shutil.rmtree(outside, ignore_errors=True)


@probe("GHSA-fg9w-wfp5-j933")
def _bllip_model_paths():
    """``BllipParser(parser_model=<outside-root>)`` must be refused before the
    extension opens the file; the sibling MaltParser learn-mode model sink
    (second pass) must be refused before its JVM writes the ``.mco``.

    The real extension rarely builds, so a spy stands in for it and records what
    ``load_parser_model`` would have opened: the guard being present means an
    outside-root model is security-refused and the spy never sees it (FIXED);
    with the guard removed the spy records the escaping path (VULNERABLE). An
    out-of-root *directory* is the attack target because ``parser_model`` names a
    model directory; the advisory's ``/etc/passwd`` file form is refused the same
    way (not a directory AND outside the roots). The verdict is the combined
    worst case over both sinks.
    """
    import nltk.parse.bllip as bllip

    outside = tempfile.mkdtemp(
        prefix=".nltk_fg9w_outside_", dir=os.path.expanduser("~")
    )
    model = os.path.join(outside, "parser")
    os.makedirs(model, exist_ok=True)
    with open(os.path.join(model, "pSgT.txt"), "wb") as handle:
        handle.write(b"model data")

    _ABSENT = object()
    saved = {
        name: getattr(bllip, name, _ABSENT)
        for name in (
            "RerankingParser",
            "get_unified_model_parameters",
            "_ensure_bllip_import_or_error",
        )
    }
    _SpyExtension.last = None
    bllip.RerankingParser = _SpyExtension
    bllip.get_unified_model_parameters = _unified_shim
    bllip._ensure_bllip_import_or_error = lambda: None
    try:
        try:
            bllip.BllipParser(parser_model=model)
        except Exception as exc:
            if is_security_rejection(exc):
                if _SpyExtension.last is not None and _SpyExtension.last.parser_model:
                    bllip_result = (
                        VULNERABLE,
                        "refused but the extension got the path",
                    )
                else:
                    bllip_result = (
                        FIXED,
                        "outside-root parser_model refused before the extension",
                    )
            else:
                bllip_result = (STATIC, f"non-security failure {type(exc).__name__}")
        else:
            if (
                _SpyExtension.last is not None
                and _SpyExtension.last.parser_model == model
            ):
                bllip_result = (VULNERABLE, f"extension opened out-of-root {model!r}")
            else:
                bllip_result = (FIXED, "no outside-root path reached the extension")
    finally:
        for name, value in saved.items():
            if value is _ABSENT:
                if hasattr(bllip, name):
                    delattr(bllip, name)
            else:
                setattr(bllip, name, value)
        import shutil

        shutil.rmtree(outside, ignore_errors=True)

    malt_result = _malt_learn_mode_model()
    results = [bllip_result, malt_result]
    for status, detail in results:
        if status == VULNERABLE:
            return VULNERABLE, detail
    if all(status == STATIC for status, _ in results):
        return STATIC, bllip_result[1]
    detail = "; ".join(f"{s.lower()}: {d}" for s, d in results)
    return FIXED, detail

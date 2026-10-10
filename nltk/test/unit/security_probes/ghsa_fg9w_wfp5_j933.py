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


@probe("GHSA-fg9w-wfp5-j933")
def _bllip_model_paths():
    """``BllipParser(parser_model=<outside-root>)`` must be refused before the
    extension opens the file.

    The real extension rarely builds, so a spy stands in for it and records what
    ``load_parser_model`` would have opened: the guard being present means an
    outside-root model is security-refused and the spy never sees it (FIXED);
    with the guard removed the spy records the escaping path (VULNERABLE). An
    out-of-root *directory* is the attack target because ``parser_model`` names a
    model directory; the advisory's ``/etc/passwd`` file form is refused the same
    way (not a directory AND outside the roots).
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
                    return VULNERABLE, "refused but the extension still got the path"
                return FIXED, "outside-root parser_model refused before the extension"
            return STATIC, f"non-security failure {type(exc).__name__}: {exc}"
        if _SpyExtension.last is not None and _SpyExtension.last.parser_model == model:
            return VULNERABLE, f"extension opened out-of-root model {model!r}"
        return FIXED, "no outside-root path reached the extension"
    finally:
        for name, value in saved.items():
            if value is _ABSENT:
                if hasattr(bllip, name):
                    delattr(bllip, name)
            else:
                setattr(bllip, name, value)
        import shutil

        shutil.rmtree(outside, ignore_errors=True)

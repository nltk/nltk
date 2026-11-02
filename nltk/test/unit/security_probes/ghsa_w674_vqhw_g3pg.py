"""GHSA-w674-vqhw-g3pg [draft] : Symlink-following stat (CWE-59/22) in
StreamBackedCorpusView. The constructor stat'ed a plain string fileid before
any containment check, so it leaked whether an out-of-root file existed and
how big it was.

The fix validates the fileid first, and a refused fileid never gets stat'ed.
"""

import os

from ._base import (
    FIXED,
    OUTSIDE_TARGET,
    STATIC,
    VULNERABLE,
    Sandbox,
    is_security_rejection,
    probe,
    register_data_root,
)

_MISSING_NAME: str = "nltk_probe_w674_absent"


def _construct(fileid: str) -> tuple[str, object]:
    """Build a view over ``fileid`` and return ``(outcome, view or None)``.

    ``outcome`` is ``"constructed"``, ``"refused"`` for a security rejection,
    or the exception's type name for anything else.
    """
    from nltk.corpus.reader.util import StreamBackedCorpusView, read_whitespace_block

    try:
        view = StreamBackedCorpusView(fileid=fileid, block_reader=read_whitespace_block)
    except Exception as exc:
        if is_security_rejection(exc=exc):
            return "refused", None
        return type(exc).__name__, None
    return "constructed", view


@probe("GHSA-w674-vqhw-g3pg")
def _corpus_view_stat_before_containment() -> tuple[str, str]:
    """Build corpus views over an outside file and check what they leak.

    VULNERABLE if a view sizes or reads the outside file, or if construction
    goes differently for a missing outside path than for a present one, which
    is an existence oracle. FIXED needs a security refusal for each outside
    fileid, at construction or on the first read.
    """
    if not OUTSIDE_TARGET:
        return STATIC, "no readable outside-root target on this platform"
    missing: str = os.path.join(os.path.dirname(OUTSIDE_TARGET), _MISSING_NAME)
    if os.path.lexists(missing):
        return STATIC, "%s exists, so there is no missing-path control" % missing
    box = Sandbox()
    undo = register_data_root(root=box.root)
    try:
        fileids: dict[str, str] = {"absolute": OUTSIDE_TARGET}
        if box.link:
            fileids["symlink"] = box.link
        outcomes: dict[str, str] = {}
        notes: list[str] = []
        for label, fileid in fileids.items():
            outcome, view = _construct(fileid=fileid)
            outcomes[label] = outcome
            if outcome == "refused":
                notes.append("%s=refused at construction" % label)
                continue
            if view is None:
                return STATIC, f"{label} failed non-securely ({outcome})"
            if view._eofpos is not None:
                return VULNERABLE, "constructor sized the %s fileid (%d bytes)" % (
                    label,
                    view._eofpos,
                )
            try:
                text: str = str(list(view))
            except Exception as exc:
                if not is_security_rejection(exc=exc):
                    return STATIC, "{} read failed non-securely ({})".format(
                        label, type(exc).__name__
                    )
                notes.append("%s=refused at read" % label)
                continue
            if box.leaked(text):
                return VULNERABLE, f"{label} fileid read {OUTSIDE_TARGET}"
            return STATIC, "%s was read but returned no canary" % label
        absent, _ = _construct(fileid=missing)
        if absent != outcomes["absolute"]:
            return (
                VULNERABLE,
                "existence oracle: present path {}, missing path {}".format(
                    outcomes["absolute"], absent
                ),
            )
        return FIXED, "; ".join(notes)
    finally:
        undo()
        box.cleanup()

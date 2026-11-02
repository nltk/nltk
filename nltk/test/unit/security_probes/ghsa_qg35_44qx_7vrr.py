"""GHSA-qg35-44qx-7vrr [high]: Symlink escape in YCOECorpusReader lets a psd/pos directory symlink read files outside the corpus root within the data sandbox"""

import os
import shutil
import tempfile
from collections.abc import Iterable

from ._base import (
    FIXED,
    STATIC,
    VULNERABLE,
    is_security_rejection,
    makedirs_private,
    probe,
    register_data_root,
    write_private,
)

CANARY: str = "qgsiblingcanary"
#: subdir -> document template, ``%s`` is the verb
_TEMPLATES: dict[str, str] = {
    "psd": "( (IP-MAT (NP-NOM (PRO^N Ic)) (VBP %s) (. .)) (ID cotest,1.1))\n",
    "pos": "Ic_PRO^N %s_VBP ._. cotest,1.1_ID\n",
}

#: (linked subdir, YCOECorpusReader method that reads from it)
_LINKS: tuple[tuple[str, str], ...] = (("pos", "tagged_words"), ("psd", "parsed_sents"))


def _write_ycoe(root: str, token: str, subs: Iterable[str]) -> str:
    """Write one YCOE document under ``root`` in each of ``subs``."""
    for sub in subs:
        makedirs_private(path=os.path.join(root, sub))
        write_private(
            path=os.path.join(root, sub, f"cotest.{sub}"),
            data=_TEMPLATES[sub] % token,
        )
    return root


def _linked_corpora(box: str) -> list[tuple[str, str, str]] | None:
    """Build a YCOE corpus per ``_LINKS`` entry with its subdir linked to a sibling.

    Returns ``(sub, corpus root, accessor)`` triples, or None if the platform
    can't make a directory symlink.
    """
    sibling: str = _write_ycoe(
        root=os.path.join(box, "other"), token=CANARY, subs=_TEMPLATES.keys()
    )
    corpora: list[tuple[str, str, str]] = []
    for sub, accessor in _LINKS:
        corpus: str = _write_ycoe(
            root=os.path.join(box, f"ycoe_{sub}"),
            token="wat",
            subs=[kept for kept in _TEMPLATES if kept != sub],
        )
        try:
            os.symlink(
                src=os.path.join(sibling, sub),
                dst=os.path.join(corpus, sub),
                target_is_directory=True,
            )
        except OSError:
            return None
        corpora.append((sub, corpus, accessor))
    return corpora


@probe("GHSA-qg35-44qx-7vrr")
def _ycoe_subdir_symlink_escape() -> tuple[str, str]:
    """Read a sibling corpus through a psd/ or pos/ symlink in a YCOE corpus.

    The sibling is in the same registered data root, so the global sandbox lets
    the link through and the check scoped to the YCOE root has to refuse it.
    VULNERABLE if the sibling's canary comes back. FIXED needs a security
    refusal on each link.
    """
    from nltk.corpus.reader.ycoe import YCOECorpusReader

    box: str = tempfile.mkdtemp()
    undo = register_data_root(root=box)
    try:
        corpora: list[tuple[str, str, str]] | None = _linked_corpora(box=box)
        if corpora is None:
            return STATIC, "cannot plant a directory symlink on this platform"
        notes: list[str] = []
        for sub, corpus, accessor in corpora:
            try:
                reader = YCOECorpusReader(root=corpus)
                text: str = str(list(getattr(reader, accessor)()))
            except Exception as exc:
                if not is_security_rejection(exc=exc):
                    return STATIC, "{} link failed non-securely ({})".format(
                        sub, type(exc).__name__
                    )
                notes.append("%s=blocked" % sub)
                continue
            if CANARY in text:
                return VULNERABLE, "%s link read the sibling corpus" % sub
            return STATIC, "%s link was read but returned no canary" % sub
        return FIXED, "; ".join(notes)
    finally:
        undo()
        shutil.rmtree(box, ignore_errors=True)

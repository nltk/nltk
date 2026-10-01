"""GHSA-xmfg-f9cm-w86q [medium]: Symlink escape in chat80.sql_query bypasses the pathsec data-root sandbox to read out-of-root SQLite databases (CWE-22, CWE-59)"""

import contextlib
import io
import os
import shutil
import tempfile

from ._base import (
    FIXED,
    STATIC,
    VULNERABLE,
    is_security_rejection,
    probe,
    register_data_root,
)
from .ghsa_8mgp_746c_j5xp import _outside_dir
from .ghsa_xv54_447f_mj22 import CANARY, _canary_store

RESOURCE = "corpora/city_database/city.db"


@probe("GHSA-xmfg-f9cm-w86q")
def _chat80_sql_query_city_db_symlink():
    """The advisory's own vector: an in-root symlink at the expected resource.

    A throwaway data root holds ``corpora/city_database/city.db`` as a symlink
    to a sqlite store outside every root, the root is registered first on
    ``nltk.data.path``, and the real ``sql_query`` (then ``sql_demo``, which the
    advisory names as the other entry point) is called for the in-root resource
    name. ``nltk.data.find`` bounds only the name, so before the fix sqlite
    followed the link and returned the outside rows. VULNERABLE when the
    canary comes back through either entry point, FIXED only when both are
    security-refused.
    """
    import nltk.sem.chat80 as chat80

    if os.name != "posix":
        return STATIC, "symlink planting is POSIX-only"
    with _outside_dir() as outside:
        if outside is None:
            return STATIC, "$HOME is inside an allowed root here; no escape target"
        secret = _canary_store(outside)
        box = tempfile.mkdtemp()
        planted = os.path.join(box, *RESOURCE.split("/"))
        os.makedirs(os.path.dirname(planted))
        os.symlink(secret, planted)
        undo = register_data_root(box)
        try:
            notes = []
            try:
                rows = list(chat80.sql_query(RESOURCE, "SELECT * FROM t"))
            except Exception as exc:
                if not is_security_rejection(exc):
                    return (
                        STATIC,
                        "sql_query failed non-securely (%s)" % type(exc).__name__,
                    )
                notes.append("sql_query=blocked")
            else:
                if any(CANARY in str(row) for row in rows):
                    return (
                        VULNERABLE,
                        "sql_query read the outside store through the link",
                    )
                return STATIC, "sql_query opened the link but returned no canary"

            printed = io.StringIO()
            try:
                with contextlib.redirect_stdout(printed):
                    chat80.sql_demo()
            except Exception as exc:
                if not is_security_rejection(exc):
                    return (
                        STATIC,
                        "sql_demo failed non-securely (%s)" % type(exc).__name__,
                    )
                notes.append("sql_demo=blocked")
            else:
                if CANARY in printed.getvalue():
                    return (
                        VULNERABLE,
                        "sql_demo printed the outside store through the link",
                    )
                return STATIC, "sql_demo ran but printed no canary"
            return FIXED, "; ".join(notes)
        finally:
            undo()
            shutil.rmtree(box, ignore_errors=True)

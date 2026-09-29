"""GHSA-xv54-447f-mj22 [low]: Symlink-follow sandbox bypass in chat80.sql_query allows out-of-root SQLite file read (CWE-59, CWE-73)"""

import os
import shutil
import sqlite3
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

CANARY = "XV54_OUTSIDE_CANARY"


def _canary_store(directory, name="secret.db"):
    """Write a real sqlite store holding CANARY in ``directory``; return its path."""
    path = os.path.join(str(directory), name)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE t (v)")
        connection.execute("INSERT INTO t VALUES (?)", (CANARY,))
        connection.commit()
    finally:
        connection.close()
    return path


def _plant_hardlink(secret, planted, extra_dirs):
    """Alias ``secret`` at ``planted``; fall back to a canary store on the store's
    own filesystem when the kernel refuses a cross-device or protected link."""
    try:
        os.link(secret, planted)
        return True
    except OSError:
        alt = tempfile.mkdtemp()
        extra_dirs.append(alt)
        try:
            os.link(_canary_store(alt), planted)
            return True
        except OSError:
            return False


def _attempts(box, outside, extra_dirs):
    """(label, resource name, query, outside path the query would create)."""
    secret = _canary_store(outside)
    os.makedirs(os.path.join(box, "xv54"))
    attempts = []

    os.symlink(secret, os.path.join(box, "xv54", "link.db"))
    attempts.append(("symlink", "xv54/link.db", "SELECT v FROM t", None))

    if _plant_hardlink(secret, os.path.join(box, "xv54", "hard.db"), extra_dirs):
        attempts.append(("hardlink", "xv54/hard.db", "SELECT v FROM t", None))

    # a symlinked DIRECTORY inside the root whose entries live outside it
    os.symlink(
        str(outside), os.path.join(box, "xv54", "dirlink"), target_is_directory=True
    )
    attempts.append(("dirlink", "xv54/dirlink/secret.db", "SELECT v FROM t", None))

    # a benign in-root store whose QUERY text names an outside file itself
    _canary_store(os.path.join(box, "xv54"), "good.db")
    attached = os.path.join(str(outside), "attached.db")
    attempts.append(
        ("attach", "xv54/good.db", "ATTACH DATABASE '%s' AS o" % attached, attached)
    )
    vacuumed = os.path.join(str(outside), "vacuumed.db")
    attempts.append(
        ("vacuum-into", "xv54/good.db", "VACUUM INTO '%s'" % vacuumed, vacuumed)
    )
    return attempts


@probe("GHSA-xv54-447f-mj22")
def _chat80_sql_query_store_escape():
    """Reach an outside sqlite file through ``sql_query`` and read its canary.

    ``sql_query`` resolves ``dbname`` with ``nltk.data.find``, which bounds the
    resource NAME to a data root but not the file behind it, then hands that
    path to ``sqlite3.connect``, which follows a symlink (or a hardlink alias,
    or a symlinked parent directory) planted inside the root. The query text
    can also name an outside file by itself (``ATTACH``, ``VACUUM INTO``). Each
    attack is staged in a registered data root and driven through the real
    ``sql_query``: VULNERABLE when the outside canary comes back or an outside
    file is created, FIXED only when every link attack is security-refused and
    no query created a file. On develop every link case returns the canary.
    """
    import nltk.sem.chat80 as chat80

    if os.name != "posix":
        return STATIC, "link planting is POSIX-only"
    with _outside_dir() as outside:
        if outside is None:
            return STATIC, "$HOME is inside an allowed root here; no escape target"
        box = tempfile.mkdtemp()
        undo = register_data_root(box)
        extra_dirs = []
        try:
            notes = []
            for label, name, query, creates in _attempts(box, outside, extra_dirs):
                try:
                    rows = list(chat80.sql_query(name, query))
                except Exception as exc:
                    if creates is not None:
                        if os.path.exists(creates):
                            return VULNERABLE, "%s created an outside file" % label
                        notes.append("%s=blocked" % label)
                        continue
                    if is_security_rejection(exc):
                        notes.append("%s=blocked" % label)
                        continue
                    return STATIC, "{} failed non-securely ({})".format(
                        label, type(exc).__name__
                    )
                if creates is not None:
                    if os.path.exists(creates):
                        return VULNERABLE, "%s created an outside file" % label
                    notes.append("%s=ran without creating a file" % label)
                    continue
                if any(CANARY in str(row) for row in rows):
                    return VULNERABLE, "%s store read the outside canary" % label
                return STATIC, "%s opened but returned no canary" % label
            return FIXED, "; ".join(notes)
        finally:
            undo()
            shutil.rmtree(box, ignore_errors=True)
            for directory in extra_dirs:
                shutil.rmtree(directory, ignore_errors=True)

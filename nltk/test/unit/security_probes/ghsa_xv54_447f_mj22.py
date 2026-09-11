"""GHSA-xv54-447f-mj22 [low] -- Symlink-follow sandbox bypass in chat80.sql_query allows out-of-root SQLite file read (CWE-59, CWE-73)"""

from ._base import guard_rejects, probe


@probe("GHSA-xv54-447f-mj22")
def _chat80_sql_query_symlink():
    """Drive ``chat80.sql_query`` with a ``dbname`` that resolves outside the
    data roots (a symlink, an absolute path, a traversal).

    ``sql_query`` opened ``dbname`` with ``sqlite3`` without any containment
    check, so a symlink or traversal could read a SQLite file outside the roots.
    It now calls ``validate_path(dbname)`` first (like ``cities2table`` /
    ``val_dump`` / ``val_load``), so each escape is security-rejected before the
    connection is opened.
    """
    from nltk.sem.chat80 import sql_query

    def guard(path, root):
        sql_query(path, "SELECT 1")

    return guard_rejects(guard)

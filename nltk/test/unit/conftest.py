"""Shared pytest configuration for NLTK unit tests.

Many corpus/security tests stage a small fixture corpus under pytest's temporary
directory and then construct a reader on it. Under the ``nltk.pathsec`` sandbox
(``ENFORCE`` is on for these tests), a reader root must resolve inside an allowed
NLTK data root. pathsec trusts a *private* per-user temp directory (macOS
``$TMPDIR``, Windows ``%TEMP%``) but deliberately does NOT trust a *shared,
world-writable* one (Linux ``/tmp``, mode ``1777``) -- a local attacker could
plant files there (CWE-377/CWE-378).

On Linux, that means pytest's fixtures under ``/tmp`` would be refused. pytest's
own session base ``<tmp>/pytest-of-<user>/...`` is, however, created private to
the user, so registering that *specific* base on ``nltk.data.path`` for the test
session authorizes exactly the fixture tree -- never all of ``/tmp`` -- and keeps
the suite green on every platform. This affects only the test process; it changes
no production behavior. Tests that assert blocking scope their own roots
(``required_root=`` or a patched ``_get_allowed_roots``) and are unaffected.
"""

import os

import pytest


@pytest.fixture(scope="session", autouse=True)
def _authorize_pytest_basetemp(tmp_path_factory):
    """Register pytest's private session temp base on nltk.data.path for the whole
    session. Session scope is required so this runs *before* module- and
    session-scoped fixtures (e.g. corpus-reader fixtures built with
    ``tmp_path_factory``) -- a function-scoped fixture would register too late for
    those. The append is left in place for the session (not monkeypatched, which
    is function-scoped); it authorizes only the pytest base, never all of /tmp,
    and changes no production behavior.
    """
    import nltk.data as _nltk_data
    from nltk import pathsec

    base = os.path.realpath(str(tmp_path_factory.getbasetemp()))
    known = [os.path.realpath(str(p)) for p in _nltk_data.path if isinstance(p, str)]
    if base not in known:
        _nltk_data.path.append(base)
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
    yield

import os
import sys

import pytest

from nltk.corpus.reader import CorpusReader


@pytest.fixture(scope="session", autouse=True)
def _authorize_pytest_basetemp(tmp_path_factory):
    """Authorize pytest's private session temp base for the whole test tree.

    Under the pathsec sandbox a data/corpus root must resolve inside an allowed
    NLTK data root. pathsec trusts a *private* per-user temp dir (macOS ``$TMPDIR``,
    Windows ``%TEMP%``) but not a *shared, world-writable* one (Linux ``/tmp``,
    mode ``1777``) -- a local attacker could plant files there (CWE-377/378).
    pytest's own session base ``<tmp>/pytest-of-<user>/...`` is private, so
    authorizing exactly that base keeps the suite green everywhere without
    trusting all of ``/tmp``.

    This lives in ``nltk/test/conftest.py`` (not only ``unit/``) so it also covers
    tests directly under ``nltk/test/`` and the ``--doctest-modules`` run. It is
    session-scoped so it runs before module-/session-scoped fixtures, and exports
    the base via ``NLTK_DATA`` as well so ``multiprocessing`` *spawn* children
    (used by several ReDoS / "does not hang" tests) -- which inherit ``os.environ``
    but not ``nltk.data.path`` edits -- trust the same base. Test-only; no
    production behavior changes.
    """
    import nltk.data as _nltk_data
    from nltk import pathsec

    base = os.path.realpath(str(tmp_path_factory.getbasetemp()))
    known = [os.path.realpath(str(p)) for p in _nltk_data.path if isinstance(p, str)]
    if base not in known:
        _nltk_data.path.append(base)
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None

    env_parts = [p for p in os.environ.get("NLTK_DATA", "").split(os.pathsep) if p]
    if base not in env_parts:
        os.environ["NLTK_DATA"] = os.pathsep.join([*env_parts, base])
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
    yield


@pytest.fixture(autouse=True)
def mock_plot(mocker):
    """Disable matplotlib plotting in test code"""

    try:
        import matplotlib.pyplot as plt

        mocker.patch.object(plt, "gca")
        mocker.patch.object(plt, "show")
    except ImportError:
        pass


@pytest.fixture(scope="module", autouse=True)
def teardown_loaded_corpora():
    """
    After each test session ends (either doctest or unit test),
    unload any loaded corpora
    """

    yield  # first, wait for the test to end

    import nltk.corpus

    for name in dir(nltk.corpus):
        obj = getattr(nltk.corpus, name, None)
        if isinstance(obj, CorpusReader) and hasattr(obj, "_unload"):
            obj._unload()

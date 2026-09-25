import os
import sys

import pytest

from nltk.corpus.reader import CorpusReader

# Test files whose tests start child processes (JVMs, or subprocesses running
# attack payloads), measured by child-process CPU. CI runs them as a separate
# serial stage on macOS so neither stage has more processes than cores.
SERIAL_STAGE_FILES = frozenset(
    [
        "unit/test_alpino.py",
        "unit/test_attack_allowlist_callers_expanded.py",
        "unit/test_attack_allowlist_payload.py",
        "unit/test_attack_dos_expanded.py",
        "unit/test_attack_json_loaders_expanded.py",
        "unit/test_attack_redos_candidates_expanded.py",
        "unit/test_ccg_lexicon_security.py",
        "unit/test_chart_parser.py",
        "unit/test_chunk_redos_security.py",
        "unit/test_cistem.py",
        "unit/test_confusionmatrix.py",
        "unit/test_corenlp_options_security.py",
        "unit/test_distance.py",
        "unit/test_downloader_atomic.py",
        "unit/test_everygrams_alloc.py",
        "unit/test_featstruct_redos.py",
        "unit/test_file_io_guard_coverage.py",
        "unit/test_generate.py",
        "unit/test_inference_security.py",
        "unit/test_logic.py",
        "unit/test_malt_stanford_pathsec.py",
        "unit/test_markdown.py",
        "unit/test_pathsec_sweep_wrappers.py",
        "unit/test_picklesec_allowlist_consolidation.py",
        "unit/test_redos_caller_patterns.py",
        "unit/test_redos_compile_dos.py",
        "unit/test_reviews_security.py",
        "unit/test_segmentation.py",
        "unit/test_sem_evaluate.py",
        "unit/test_senseval_security.py",
        "unit/test_staging_tempdir_security.py",
        "unit/test_stem_regexp_redos.py",
        "unit/test_text.py",
        "unit/test_texttiling_security.py",
        "unit/test_tokenize.py",
        "unit/test_tree_deep_walks.py",
        "unit/test_treetransforms.py",
        "unit/test_valuation_redos.py",
        "unit/test_weka_integration.py",
        "unit/test_weka_model_path_security.py",
        "unit/test_xmldocs_security.py",
        "unit/test_zipbomb_security.py",
        "unit/translate/test_alignment.py",
        "unit/translate/test_gdfa.py",
        "unit/translate/test_lepor.py",
        "unit/translate/test_meteor.py",
        "unit/translate/test_phrase_based_security.py",
    ]
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "serial: starts child processes; runs in the serial CI stage"
    )


def pytest_collection_modifyitems(config, items):
    here = os.path.dirname(os.path.abspath(__file__))
    missing = [
        f for f in SERIAL_STAGE_FILES if not os.path.exists(os.path.join(here, f))
    ]
    if missing:
        raise pytest.UsageError(f"SERIAL_STAGE_FILES lists missing files: {missing}")
    for item in items:
        rel = os.path.relpath(str(item.path), here).replace(os.sep, "/")
        if rel in SERIAL_STAGE_FILES:
            item.add_marker(pytest.mark.serial)


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

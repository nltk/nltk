# Natural Language Toolkit: negative controls for the chat80 store probes
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Teeth for the chat80 store-class advisory probes (GHSA-xv54-447f-mj22,
GHSA-xmfg-f9cm-w86q, GHSA-7j4p-88wx-5jrc).

Each control removes exactly one guard in-process and asserts that the probe
flips to VULNERABLE, proving the probe reaches the sqlite / shelve sink and that
the named guard is what holds the line; the guard is restored and the probe must
report FIXED again. Kept in its own module so the block appended to
``test_advisory_probes.py`` by sibling pull requests is never touched.
"""

import sqlite3

import pytest

from nltk.test.unit import security_probes as probes


def _fixed_or_skip(ghsa):
    """The probe for ``ghsa``, or a skip where its link planting cannot run."""
    probe = probes.PROBES[ghsa]
    status, detail = probe()
    if status == probes.STATIC:
        pytest.skip("probe is STATIC on this platform: " + detail)
    assert status == probes.FIXED, detail
    return probe


def _all_three_fixed_after(probe):
    """Every store probe must still be FIXED once the guards are restored."""
    for ghsa in ("GHSA-xv54-447f-mj22", "GHSA-xmfg-f9cm-w86q", "GHSA-7j4p-88wx-5jrc"):
        status, detail = probes.PROBES[ghsa]()
        assert status in (probes.FIXED, probes.STATIC), (ghsa, detail)
    assert probe()[0] == probes.FIXED


def test_xv54_sql_query_store_probe_has_teeth():
    """Restore the pre-fix sink: no containment on the file behind the resource
    name and no link check at the store; sqlite then follows the planted symlink
    to the outside store and the probe must flip VULNERABLE."""
    import nltk.sem.chat80 as chat80

    probe = _fixed_or_skip("GHSA-xv54-447f-mj22")
    validate, refuse = chat80.validate_path, chat80._refuse_symlinked_store
    try:
        chat80.validate_path = lambda *args, **kwargs: None
        chat80._refuse_symlinked_store = lambda *args, **kwargs: None
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        assert "symlink" in detail
    finally:
        chat80.validate_path, chat80._refuse_symlinked_store = validate, refuse
    _all_three_fixed_after(probe)


def test_xv54_hardlink_is_held_by_the_store_link_check_alone():
    """validate_path resolves symlinks but cannot see a hardlink alias; with only
    the store link check removed the hardlink attack must get through, proving
    that check is what holds that line (not a neighbour)."""
    import nltk.sem.chat80 as chat80

    probe = _fixed_or_skip("GHSA-xv54-447f-mj22")
    real = chat80._refuse_symlinked_store
    try:
        chat80._refuse_symlinked_store = lambda *args, **kwargs: None
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        assert "hardlink" in detail
    finally:
        chat80._refuse_symlinked_store = real
    _all_three_fixed_after(probe)


def test_xv54_query_text_escape_is_held_by_the_authorizer():
    """Let every sqlite action through; ATTACH then creates the outside file the
    query names and the probe must flip VULNERABLE on that file, not on a link."""
    import nltk.sem.chat80 as chat80

    probe = _fixed_or_skip("GHSA-xv54-447f-mj22")
    real = chat80._sql_query_authorizer
    try:
        chat80._sql_query_authorizer = lambda *args: sqlite3.SQLITE_OK
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        assert "created an outside file" in detail
    finally:
        chat80._sql_query_authorizer = real
    _all_three_fixed_after(probe)


def test_xmfg_city_db_symlink_probe_has_teeth():
    """The advisory's exact vector (an in-root corpora/city_database/city.db link)
    must leak through both sql_query and sql_demo once the file-behind-the-name
    guards are gone, and be refused again once they are back."""
    import nltk.sem.chat80 as chat80

    probe = _fixed_or_skip("GHSA-xmfg-f9cm-w86q")
    validate, refuse = chat80.validate_path, chat80._refuse_symlinked_store
    try:
        chat80.validate_path = lambda *args, **kwargs: None
        chat80._refuse_symlinked_store = lambda *args, **kwargs: None
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        assert "sql_query read the outside store" in detail
    finally:
        chat80.validate_path, chat80._refuse_symlinked_store = validate, refuse
    _all_three_fixed_after(probe)


def test_7j4p_chat80_store_link_probe_has_teeth():
    """Disable the derived-name store guard; the planted symlink is followed past
    it and the probe must flip VULNERABLE."""
    import nltk.sem.chat80 as chat80

    probe = _fixed_or_skip("GHSA-7j4p-88wx-5jrc")
    real = chat80._refuse_symlinked_store
    try:
        chat80._refuse_symlinked_store = lambda *args, **kwargs: None
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
    finally:
        chat80._refuse_symlinked_store = real
    _all_three_fixed_after(probe)


def test_7j4p_store_guard_is_the_pathsec_hardened_open():
    """The store guard opens each backing name through pathsec.open; swap the
    hardened opener for a bare open and the planted link is followed, so the
    guard's strength is exactly the opener's (O_NOFOLLOW, st_nlink, realpath)."""
    import builtins

    import nltk.pathsec as pathsec

    probe = _fixed_or_skip("GHSA-7j4p-88wx-5jrc")
    real = pathsec._hardened_open
    try:
        pathsec._hardened_open = (
            lambda raw, mode, context, required_root, **kw: builtins.open(
                raw, mode, **kw
            )
        )
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
    finally:
        pathsec._hardened_open = real
    _all_three_fixed_after(probe)


def test_j456_weka_model_path_probe_stays_fixed():
    """GHSA-j456-xh4h-cpf2 is fixed on develop (PR #3863, probe from #3905); the
    store branch must not regress it. Its own teeth live with the weka tests."""
    status, detail = probes.PROBES["GHSA-j456-xh4h-cpf2"]()
    assert status in (probes.FIXED, probes.STATIC), detail

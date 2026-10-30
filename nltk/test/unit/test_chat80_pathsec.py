# Natural Language Toolkit: pathsec sweep attack tests (chat80)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path-traversal attack tests for the caller-controlled file sinks hardened in
``nltk.sem.chat80`` (GHSA-8mgp-746c-j5xp).

Each patched API must refuse to read from / write to a path outside the NLTK
data sandbox and must leave nothing behind.
"""

import os

import pytest

import nltk.pathsec as pathsec

# The ``sandbox`` fixture is provided by nltk/test/unit/conftest.py.


def test_negative_control_open_outside_raises(sandbox):
    """The sandbox is wired correctly: a plain pathsec.open() of the outside
    target must be refused and write nothing."""
    target = sandbox / "neg_control.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


def test_chat80_val_dump_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_valuation"
    with pytest.raises(PermissionError):
        chat80.val_dump([], str(target))
    # shelve may append backend suffixes (.db/.dir/.dat/.bak); none may appear.
    assert not list(sandbox.glob("evil_valuation*"))


def test_chat80_val_load_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_db"
    with pytest.raises(PermissionError):
        chat80.val_load(str(target))


def test_chat80_cities2table_refuses_outside(sandbox):
    from nltk.sem import chat80

    target = sandbox / "evil_city.db"
    with pytest.raises(PermissionError):
        chat80.cities2table("cities.pl", "city", str(target))
    assert not target.exists()


def test_chat80_label_indivs_refuses_outside_cwd(sandbox):
    from nltk.sem import chat80
    from nltk.sem.evaluate import Valuation

    # label_indivs writes the fixed name "chat_pnames.cfg" relative to CWD; make
    # CWD the outside dir so the write would land outside the sandbox.
    os.chdir(sandbox)
    with pytest.raises(PermissionError):
        chat80.label_indivs(Valuation([]), lexicon=True)
    assert not (sandbox / "chat_pnames.cfg").exists()


@pytest.mark.parametrize(
    "target",
    ["<outside>/evil", "/etc/nltk_pwned", "<outside>/e\x00vil"],
    ids=["outside", "etc", "nul"],
)
def test_shelve_backed_valuation_paths_refuse_escape(pathsec_sandbox, target):
    """val_dump/val_load hand a caller path straight to shelve.open, which
    creates its own backing files, so pathsec.open cannot wrap it. The path is
    validated first instead, before any corpus work happens."""
    from nltk.sem import chat80

    root, outside = pathsec_sandbox
    resolved = target.replace("<outside>", str(outside))
    with pytest.raises((PermissionError, ValueError)):
        chat80.val_dump({}, resolved)
    with pytest.raises((PermissionError, ValueError)):
        chat80.val_load(resolved)


def test_shelve_valuation_path_inside_the_root_is_allowed(pathsec_sandbox):
    """Over-block control: an in-root destination passes validation."""
    from nltk.sem import chat80

    root, _outside = pathsec_sandbox
    try:
        chat80.val_dump({}, str(root / "ok"))
    except (PermissionError, ValueError) as exc:
        pytest.fail(f"in-root shelve destination was refused: {exc}")
    except Exception:
        pass  # past validation; whatever shelve/corpus does next is not our concern

# Natural Language Toolkit: package-init import smoke test
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Import-time smoke test for the hardened VERSION read in ``nltk/__init__``.

The package initializer now reads its ``VERSION`` file through
``nltk.pathsec.open_package_resource`` instead of a bare ``open``. That read runs
at import time, so a wrong root or a too-strict guard would either raise or
silently turn ``__version__`` into an error string, breaking the whole package.
"""

import nltk


def test_import_nltk_and_version_is_clean():
    """``import nltk`` must succeed and populate a real version string."""
    assert nltk.__version__
    assert "Security Violation" not in nltk.__version__
    assert "unknown" not in nltk.__version__
    assert nltk.__version__[0].isdigit()


def test_pathsec_open_package_resource_is_reachable():
    """The initializer depends on this symbol; it must import cleanly."""
    from nltk.pathsec import open_package_resource

    assert callable(open_package_resource)

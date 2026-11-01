# Natural Language Toolkit: WordNet browser static page tests
#
# Copyright (C) 2001-2026 NLTK Project
#
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Static-page dispatch tests for ``nltk.app.wordnet_app``.

``get_static_page_by_path`` is the single dispatcher behind the WordNet
browser's static pages.  Every documented path must either render a page or
raise :exc:`FileNotFoundError`, which the request handler turns into a plain
"unknown path" response.  A path must never raise :exc:`NameError` by
dispatching to a helper that no longer exists.
"""

import pytest

import nltk.app.wordnet_app as wa


def test_web_help_page_renders():
    page = wa.get_static_page_by_path("web_help.html")
    assert "NLTK Wordnet Browser Help" in page


def test_wx_help_page_is_not_a_nameerror():
    # Regression test: the "wx_help.html" branch used to call
    # get_static_wx_help_page(), a helper that no longer exists,
    # crashing the request with NameError instead of being handled
    # as an unknown static page.
    with pytest.raises(FileNotFoundError):
        wa.get_static_page_by_path("wx_help.html")

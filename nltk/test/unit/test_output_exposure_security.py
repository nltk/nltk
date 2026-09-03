# Natural Language Toolkit: XSS + secret-exposure regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Two file-local weaknesses closed on this branch: the WordNet browser served
corpus-derived synset text as HTML without escaping (CWE-79), and the Twitter
creds validator pretty-printed the whole credentials dict (secret values and
all) into a ValueError that reaches stderr/logs (CWE-532 / CWE-200). These tests
drive the real code paths."""

import html

import pytest


class TestWordnetAppXss:
    def test_make_lookup_link_escapes_label_and_href(self):
        from nltk.app.wordnet_app import make_lookup_link

        class Ref:
            def encode(self):
                return 'a"onmouseover=alert(1)'

        out = make_lookup_link(Ref(), html.escape("<script>x</script>"))
        assert "<script>" not in out  # element-content payload neutralised
        assert '"onmouseover=alert(1)"' not in out  # attribute breakout neutralised
        assert "&lt;script&gt;" in out and "&quot;" in out


class TestTwitterCredsNoLeak:
    def test_invalid_creds_error_omits_secret_values(self):
        pytest.importorskip("twython", reason="twython not installed")
        from nltk.twitter.util import Authenticate

        auth = Authenticate()
        auth.creds_file = "credentials.txt"
        auth.oauth = {"app_key": "PUBLIC", "app_secret": "TOP_SECRET_VALUE"}
        with pytest.raises(ValueError) as exc:
            auth._validate_creds_file()
        msg = str(exc.value)
        assert "TOP_SECRET_VALUE" not in msg  # no secret value leaked
        assert "app_secret" in msg  # key name is fine

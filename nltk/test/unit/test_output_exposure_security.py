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

    # Each dict is missing at least one required OAuth key, so validation must
    # raise; the secret VALUES must never appear in the error while the key
    # NAMES may (they help an operator fix the file). CWE-532 / CWE-200 / CWE-209.
    @pytest.mark.parametrize(
        "oauth",
        [
            {"app_key": "PUBLIC", "app_secret": "SEKRIT_APP_SECRET"},
            {"app_key": "PUBLIC", "app_secret": "S", "oauth_token": "SEKRIT_OAUTH_TOK"},
            {"app_key": "PUBLIC", "access_token": "SEKRIT_ACCESS_TOK"},
            {"app_secret": "SEKRIT_ONLY", "oauth_token_secret": "SEKRIT_TS_ONLY"},
            {},  # nothing at all
        ],
    )
    def test_invalid_creds_never_leak_any_value(self, oauth):
        pytest.importorskip("twython", reason="twython not installed")
        from nltk.twitter.util import Authenticate

        auth = Authenticate()
        auth.creds_file = "credentials.txt"
        auth.oauth = dict(oauth)
        with pytest.raises(ValueError) as exc:
            auth._validate_creds_file()
        msg = str(exc.value)
        for key, value in oauth.items():
            assert key in msg, f"key name {key!r} should be reported for debugging"
            assert value not in msg, f"secret value for {key!r} leaked into error"

    @pytest.mark.parametrize(
        "oauth",
        [
            {
                "app_key": "K",
                "app_secret": "S",
                "oauth_token": "T",
                "oauth_token_secret": "TS",
            },  # complete OAuth 1
            {"app_key": "K", "app_secret": "S", "access_token": "AT"},  # OAuth 2
        ],
    )
    def test_valid_creds_pass_without_error(self, oauth):
        pytest.importorskip("twython", reason="twython not installed")
        from nltk.twitter.util import Authenticate

        auth = Authenticate()
        auth.creds_file = "credentials.txt"
        auth.oauth = dict(oauth)
        # A complete key set must validate silently (no ValueError).
        auth._validate_creds_file()

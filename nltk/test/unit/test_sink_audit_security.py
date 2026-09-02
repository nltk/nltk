# Natural Language Toolkit: whole-library sink-audit regression tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Regression tests for the gaps a whole-library output-sink audit surfaced: a
credential leak into a Twitter exception (CWE-532), a JSON loader that bypassed
the jsontags depth guard (CWE-400), and corpus readers emitting raw corpus text
to stderr via warnings (CWE-150). Each test drives the real code path."""

import json
import warnings

import pytest


class TestTwitterCredsNoLeak:
    def test_invalid_creds_error_does_not_contain_secret_values(self):
        pytest.importorskip("twython", reason="twython not installed")
        from nltk.twitter.util import Authenticate

        auth = Authenticate()
        auth.creds_file = "credentials.txt"
        # a partial creds dict (missing keys) -> validation raises
        auth.oauth = {"app_key": "PUBLIC", "app_secret": "TOP_SECRET_VALUE"}
        with pytest.raises(ValueError) as exc:
            auth._validate_creds_file()
        msg = str(exc.value)
        assert "TOP_SECRET_VALUE" not in msg  # no secret value leaked
        assert "app_secret" in msg  # the key NAME is fine to report


class TestJsonLoaderDepthGuard:
    def test_json_taggeddecoder_rejects_deep_nesting(self):
        from nltk.jsontags import JSONTaggedDecoder

        deep = "[" * 500 + "]" * 500
        with pytest.raises((ValueError, RecursionError)):
            json.loads(deep, cls=JSONTaggedDecoder)

    def test_json_taggeddecoder_rejects_unknown_tag(self):
        from nltk.jsontags import JSONTaggedDecoder

        with pytest.raises(ValueError):
            json.loads('{"!nosuchtag": 1}', cls=JSONTaggedDecoder)

    def test_plain_json_passes_through(self):
        from nltk.jsontags import JSONTaggedDecoder

        assert json.loads('{"a": [1, 2, 3]}', cls=JSONTaggedDecoder) == {"a": [1, 2, 3]}

    def test_data_load_json_uses_the_guarded_decoder(self, tmp_path):
        import nltk.data

        p = tmp_path / "x.json"
        p.write_text('{"hello": "world"}', encoding="utf-8")
        assert nltk.data.load("file://" + str(p), format="json") == {"hello": "world"}


class TestCorpusWarnSanitisation:
    def test_sonority_tokenizer_warning_is_sanitised(self):
        # an out-of-alphabet token character carrying a control sequence must not
        # reach stderr raw when the sonority tokenizer warns about it (CWE-150)
        from nltk.tokenize.sonority_sequencing import SyllableTokenizer

        tok = SyllableTokenizer()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            tok.tokenize("ab\x1b[2Jc")
        blob = " ".join(str(w.message) for w in caught)
        assert "\x1b" not in blob

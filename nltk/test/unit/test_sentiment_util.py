import json
import unittest
from functools import partial

import pytest

import nltk.sentiment.util as sentiment_util
from nltk.sentiment.util import extract_bigram_feats, extract_unigram_feats


class ExtractFeatsTest(unittest.TestCase):
    document = "the film was not good , not good at all".split()

    def test_unigram_feats(self):
        self.assertEqual(
            extract_unigram_feats(self.document, ["good", "bad", "film"]),
            {"contains(good)": True, "contains(bad)": False, "contains(film)": True},
        )

    def test_unigram_feats_with_negation(self):
        feats = extract_unigram_feats(
            self.document, ["good", "good_NEG"], handle_negation=True
        )
        self.assertEqual(feats, {"contains(good)": False, "contains(good_NEG)": True})

    def test_bigram_feats(self):
        bigrams = [("not", "good"), ("good", "not"), ("good", "at"), ("film", "not")]
        self.assertEqual(
            extract_bigram_feats(self.document, bigrams),
            {
                "contains(not - good)": True,
                "contains(good - not)": False,
                "contains(good - at)": True,
                "contains(film - not)": False,
            },
        )


@pytest.mark.parametrize(
    "text",
    ["caf\u00e9", "\u041d\u043e\u0432\u044b\u0439 \u0444\u0438\u043b\u044c\u043c"],
)
def test_tweet_csv_utf8_roundtrip(tmp_path, monkeypatch, enforce_off, text):
    source = tmp_path / "tweets.json"
    target = tmp_path / "tweets.csv"
    source.write_text(json.dumps({"id": 1, "text": text}) + "\n", encoding="utf-8")
    # Emulate the default text encoding on a Western Windows installation.
    monkeypatch.setattr(
        sentiment_util,
        "pathsec_open",
        partial(sentiment_util.pathsec_open, encoding="cp1252"),
    )
    sentiment_util.json2csv_preprocess(
        str(source), str(target), ["id", "text"], strip_off_emoticons=False
    )
    result = sentiment_util.parse_tweets_set(
        str(target), "positive", sent_tokenizer=object()
    )
    assert result == [(text, "positive")]

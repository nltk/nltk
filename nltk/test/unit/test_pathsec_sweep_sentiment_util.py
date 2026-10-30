"""GHSA-8mgp-746c-j5xp sweep: nltk.sentiment.util file I/O stays in the sandbox.

output_markdown / json2csv_preprocess / parse_tweets_set used codecs.open on a
caller-supplied path, bypassing pathsec. They now go through pathsec_open.
"""

import pytest

import nltk.pathsec as pathsec

# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off /
# pathsec_sandbox) are provided by nltk/test/unit/conftest.py.


def test_negative_control(sandbox):
    target = str(sandbox / "x.txt")
    with pytest.raises(PermissionError):
        with pathsec.open(target, "w"):
            pass


def test_output_markdown_refuses_outside_path(sandbox):
    from nltk.sentiment.util import output_markdown

    target = sandbox / "report.md"
    with pytest.raises(PermissionError):
        output_markdown(str(target), model="x", accuracy=1.0)
    assert not target.exists(), "refused write must not have created the file"


def test_parse_tweets_set_refuses_outside_path(sandbox):
    from nltk.sentiment.util import parse_tweets_set

    outside = sandbox / "tweets.csv"
    outside.write_text("1,hello\n", encoding="utf-8")  # a real file, so the
    # refusal is the sandbox check, not FileNotFound.
    # Pass tokenizers so the function reaches the file open without needing punkt
    # data (unavailable in the sandboxed data path); the open raises first.
    with pytest.raises(PermissionError):
        parse_tweets_set(
            str(outside),
            label="pos",
            word_tokenizer=object(),
            sent_tokenizer=object(),
        )


def test_json2csv_preprocess_refuses_outside_outfile(pathsec_sandbox):
    """json2csv_preprocess reads a legitimate in-sandbox input but must refuse an
    out-of-sandbox ``outfile`` (its CSV/GZIP output is a caller-supplied path)."""
    from nltk.sentiment.util import json2csv_preprocess

    src = pathsec_sandbox.root / "in.json"  # in-sandbox input, allowed to read
    src.write_text('{"id": 1, "text": "hi"}\n', encoding="utf-8")
    outfile = pathsec_sandbox.outside / "evil.csv"  # out-of-sandbox output
    with pytest.raises(PermissionError):
        json2csv_preprocess(str(src), str(outfile), fields=["id", "text"])
    assert not outfile.exists(), "refused write must not have created the file"

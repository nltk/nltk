"""GHSA-8mgp-746c-j5xp sweep: nltk.sentiment.util file I/O stays in the sandbox.

output_markdown / json2csv_preprocess / parse_tweets_set used codecs.open on a
caller-supplied path, bypassing pathsec. They now go through pathsec_open.
"""

import os
import pathlib
import shutil
import tempfile

import pytest

import nltk
import nltk.pathsec as pathsec


@pytest.fixture
def sandbox():
    saved_paths = nltk.data.path[:]
    saved_enforce = pathsec.ENFORCE
    pathsec.ENFORCE = True
    nltk.data.path[:] = [tempfile.mkdtemp()]
    pathsec._ALLOWED_ROOTS_CACHE = None
    pathsec._LAST_DATA_PATHS = None
    # A genuinely-outside target: a fresh $HOME dir, never a temp dir (the
    # private system temp is an allowed pathsec root on macOS).
    outside_dir = pathlib.Path.home() / (".nltk_sweep_sentutil_%d" % os.getpid())
    shutil.rmtree(outside_dir, ignore_errors=True)
    outside_dir.mkdir(exist_ok=True)
    try:
        yield outside_dir
    finally:
        nltk.data.path[:] = saved_paths
        pathsec.ENFORCE = saved_enforce
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        shutil.rmtree(outside_dir, ignore_errors=True)


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

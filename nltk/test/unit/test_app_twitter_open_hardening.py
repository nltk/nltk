"""Adversarial coverage for the app / draw / twitter opens routed through
pathsec.open.

The paths these modules open are operator-chosen (a Tk Save/Open dialog, the
``$TWITTER`` credentials dir, a tweet-output dir), so pathsec.open does not bound
them to the data roots. It still hardens them, and these tests pin that on the
actual wrappers: a symlink or hardlink planted at the destination is refused at
open time (O_NOFOLLOW / st_nlink, CWE-59), a NUL byte or a URL in the path is
refused (CWE-22), and a freshly written file is created 0600 so a saved chart or
credentials file is never left group/world readable (CWE-377/378). Legitimate
operator paths keep working. POSIX only (symlink / hardlink / permission model).
"""

import os
import stat

import pytest

from nltk.pathsec import open as pathsec_open

posix_only = pytest.mark.skipif(
    os.name != "posix", reason="symlink / hardlink / permission model is POSIX"
)


@pytest.fixture
def sensitive(tmp_path):
    """A file an attacker would try to redirect a write onto / a read out of."""
    target = tmp_path / "sensitive"
    target.write_text("SECRET")
    return target


# --- the shared chokepoint every app/draw/twitter open now goes through --------


@posix_only
@pytest.mark.parametrize("mode", ["w", "wb", "a", "r", "rb"])
def test_symlink_at_the_path_is_refused(tmp_path, sensitive, mode):
    link = tmp_path / "dest"
    link.symlink_to(sensitive)
    with pytest.raises(PermissionError):
        pathsec_open(str(link), mode, context="test")
    assert sensitive.read_text() == "SECRET"  # neither read out nor clobbered


@posix_only
@pytest.mark.parametrize("mode", ["w", "wb", "a"])
def test_hardlink_at_the_destination_is_refused(tmp_path, sensitive, mode):
    hard = tmp_path / "hard"
    os.link(sensitive, hard)
    with pytest.raises(PermissionError):
        pathsec_open(str(hard), mode, context="test")
    assert sensitive.read_text() == "SECRET"


@pytest.mark.parametrize("mode", ["w", "wb", "a", "r"])
def test_nul_byte_in_path_is_refused(tmp_path, mode):
    with pytest.raises((PermissionError, ValueError, OSError)):
        pathsec_open(str(tmp_path / "a\x00b"), mode, context="test")


@pytest.mark.parametrize("url", ["http://evil.example/x", "file:///etc/passwd"])
def test_url_as_path_is_refused(url):
    with pytest.raises((PermissionError, ValueError)):
        pathsec_open(url, "w", context="test")


@posix_only
def test_new_file_is_not_group_or_world_readable(tmp_path):
    path = tmp_path / "out.txt"
    with pathsec_open(str(path), "w", context="test") as handle:
        handle.write("x")
    assert stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


@posix_only
def test_legit_operator_path_roundtrips(tmp_path):
    path = tmp_path / "operator" / "chosen.txt"
    path.parent.mkdir()
    with pathsec_open(str(path), "w", context="test") as handle:
        handle.write("hello")
    with pathsec_open(str(path), "r", context="test") as handle:
        assert handle.read() == "hello"


# --- per-wrapper attacks on the actual functions -------------------------------


@posix_only
def test_twitter_outf_writer_refuses_symlinked_destination(tmp_path, sensitive):
    from nltk.twitter.common import _outf_writer

    link = tmp_path / "out.csv"
    link.symlink_to(sensitive)
    with pytest.raises(PermissionError):
        _outf_writer(str(link), "utf-8", "strict", gzip_compress=False)
    assert sensitive.read_text() == "SECRET"


def test_twitter_outf_writer_legit_path_works(tmp_path):
    from nltk.twitter.common import _outf_writer

    path = tmp_path / "out.csv"
    writer, handle = _outf_writer(str(path), "utf-8", "strict", gzip_compress=False)
    writer.writerow(["a", "b"])
    handle.close()
    assert path.read_text().strip() == "a,b"


@posix_only
def test_tweetwriter_refuses_symlinked_output(tmp_path, sensitive):
    pytest.importorskip("twython", reason="twython not installed")
    from nltk.twitter.twitterclient import TweetWriter

    link = tmp_path / "tweets.json"
    link.symlink_to(sensitive)
    writer = object.__new__(TweetWriter)
    writer.startingup = True
    writer.gzip_compress = False
    writer.fname = str(link)
    with pytest.raises(PermissionError):
        writer.handle({"id": 1})
    assert sensitive.read_text() == "SECRET"


@posix_only
def test_chartcomparer_load_refuses_symlinked_source(tmp_path, sensitive):
    from nltk.app.chartparser_app import ChartComparer

    link = tmp_path / "chart.pickle"
    link.symlink_to(sensitive)
    comparer = object.__new__(ChartComparer)
    with pytest.raises(PermissionError):
        comparer.load_chart(str(link))


@posix_only
def test_chartparserapp_save_refuses_symlinked_destination(
    tmp_path, sensitive, monkeypatch
):
    import nltk.app.chartparser_app as cpa

    link = tmp_path / "chart.pickle"
    link.symlink_to(sensitive)
    monkeypatch.setattr(cpa, "asksaveasfilename", lambda *a, **k: str(link))
    app = object.__new__(cpa.ChartParserApp)
    app._chart = "unused: the open is refused before pickling"
    with pytest.raises(PermissionError):
        app.save_chart()
    assert sensitive.read_text() == "SECRET"


# --- functional: a real chart pickle still saves and loads through pathsec -----


def test_real_chart_pickle_roundtrips_through_pathsec(tmp_path):
    import nltk.app.chartparser_app as cpa
    from nltk import CFG
    from nltk.parse.chart import ChartParser
    from nltk.picklesec import pickle_dump

    chart = ChartParser(CFG.fromstring("S -> 'a'")).chart_parse(["a"])
    path = tmp_path / "chart.pickle"
    with pathsec_open(str(path), "wb", context="test") as handle:
        pickle_dump(chart, handle)
    with pathsec_open(str(path), "rb", context="test") as handle:
        loaded = cpa._load_chart_pickle(handle)  # pathsec + allowlist unpickler
    assert loaded.num_edges() == chart.num_edges()

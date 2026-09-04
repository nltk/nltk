"""Operator-chosen file opens must not be confined to the NLTK data roots.

The Tk Save/Open dialogs, the ``$TWITTER`` credentials/output paths, and the
wordnet browser log are chosen by the operator and legitimately live OUTSIDE the
data roots (a chart saved to ``~/mychart.pickle``, tweets collected to
``./twitter-files/``). #3861 briefly routed these through ``pathsec.open``, which
confines to the data roots and so rejected every such path with
``PermissionError: Unauthorized path``. They are now plain builtin opens
annotated for the no-unsandboxed-open guard.

These paths are operator-controlled, not attacker input, so the annotated bare
open is not an exploit point: the GUI dialogs return an operator-picked path, the
twitter paths come from operator config, and the only HTTP-facing case (the
wordnet browser) is proven traversal-safe below. The functional tests pin that an
outside-roots operator path works, so re-confining these would fail immediately.
"""

import os

import pytest

# --- wordnet HTTP surface: no arbitrary-file read (attack) --------------------


@pytest.mark.parametrize(
    "evil",
    [
        "../../../../etc/passwd",
        "/etc/passwd",
        "..%2f..%2fetc%2fpasswd",
        "....//....//etc/passwd",
        "\\..\\..\\windows\\win.ini",
        "index.rdf/../../../etc/passwd",
        "arbitrary.html",
    ],
)
def test_wordnet_static_page_dispatch_never_reads_arbitrary_files(evil):
    """The wordnet browser serves static pages by dispatching a fixed set of known
    paths; an unknown or traversal path raises FileNotFoundError and opens nothing,
    so the HTTP-facing route cannot be turned into an arbitrary file read (CWE-22).
    """
    from nltk.app.wordnet_app import get_static_page_by_path

    with pytest.raises(FileNotFoundError):
        get_static_page_by_path(evil)


def test_wordnet_dbinfo_open_is_exact_string_gated():
    """The one file the request handler opens is gated by exact equality to a fixed
    name, so a crafted request path can never reach that open."""
    import inspect

    from nltk.app import wordnet_app

    src = inspect.getsource(wordnet_app.MyServerHandler.do_GET)
    assert '== "NLTK Wordnet Browser Database Info.html"' in src


# --- functional: operator opens work OUTSIDE the data roots -------------------


@pytest.fixture
def outside_roots(monkeypatch, tmp_path):
    """An operator directory confirmed OUTSIDE every allowed data root, so a
    confining open rejects it. Skips where the platform authorizes the temp base
    (there the confinement regression cannot be observed)."""
    import nltk.data as _data
    from nltk import pathsec
    from nltk.pathsec import open as pathsec_open

    data_root = tmp_path / "dataroot"
    data_root.mkdir()
    operator = tmp_path / "operator_home"
    operator.mkdir()
    monkeypatch.setattr(_data, "path", [str(data_root)])
    monkeypatch.setenv("NLTK_DATA", str(data_root))
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        with pathsec_open(str(operator / ".probe"), "w"):
            pass
        pytest.skip("temp base is authorized here; confinement is not observable")
    except PermissionError:
        pass
    return operator


def _open_not_confined(fn):
    """Run an operator open; fail ONLY if it was confined to the data roots.

    The open is what this pins; any later error from an incompletely initialised
    Tk widget / tweet handler is downstream of the open and irrelevant here.
    """
    try:
        fn()
    except PermissionError as exc:
        if "Unauthorized" in str(exc):
            pytest.fail(f"operator open was confined to the data roots: {exc}")
        raise  # a genuine OS permission error is a real failure
    except Exception:
        pass  # post-open handler/widget state, not the open


def test_twitter_outf_writer_works_outside_data_roots(outside_roots):
    from nltk.twitter.common import _outf_writer

    path = str(outside_roots / "tweets.csv")
    writer, handle = _outf_writer(path, "utf-8", "strict", gzip_compress=False)
    writer.writerow(["a", "b"])
    handle.close()
    assert os.path.exists(path)


def test_tweetwriter_output_works_outside_data_roots(outside_roots):
    from nltk.twitter.twitterclient import TweetWriter

    writer = object.__new__(TweetWriter)
    writer.startingup = True
    writer.gzip_compress = False
    writer.fname = str(outside_roots / "tweets.json")
    _open_not_confined(lambda: writer.handle({"id": 1}))
    assert os.path.exists(writer.fname)  # the open + first write happened


def test_chart_load_works_outside_data_roots(outside_roots):
    import nltk.app.chartparser_app as cpa
    from nltk import CFG
    from nltk.parse.chart import ChartParser
    from nltk.picklesec import pickle_dump

    chart = ChartParser(CFG.fromstring("S -> 'a'")).chart_parse(["a"])
    path = str(outside_roots / "chart.pickle")
    with open(path, "wb") as handle:  # test writer; nltk/test is not guarded
        pickle_dump(chart, handle)
    comparer = object.__new__(cpa.ChartComparer)
    comparer._charts = {}
    _open_not_confined(lambda: comparer.load_chart(path))  # operator Open


def test_twitter_creds_read_outside_data_roots(outside_roots):
    """Authenticate reads the operator's credentials file from a path outside the
    data roots (the regression that failed CI)."""
    from nltk.twitter.util import Authenticate

    creds = outside_roots / "credentials.txt"
    creds.write_text("app_key=a\napp_secret=b\noauth_token=c\noauth_token_secret=d\n")
    auth = Authenticate()
    result = auth.load_creds(creds_file="credentials.txt", subdir=str(outside_roots))
    assert result.get("app_key") == "a"

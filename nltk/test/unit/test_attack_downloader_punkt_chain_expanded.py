# Natural Language Toolkit: the punkt to punkt_tab download chain, attacked
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Asking for a package this NLTK no longer reads (``punkt``, whose pickles
were retired for ``punkt_tab``) also installs its successor (#3394). That
second download is driven by network data, the index, so it is attacked
here against a REAL local HTTP server (http.server on an ephemeral loopback
port) serving real indexes and real archives.

What is established, each case judged by what reached the disk, the
terminal, the server and the loaders, never by whether something raised:

* every way of asking reaches the successor (a string, a list, a tuple, a
  Package, a collection such as ``popular`` or ``book``, nested
  collections, ``nltk.download``, the command line, the text shell, the
  GUI's ``incr_download``, ``update()``), and what it installs really loads
  through ``nltk.data`` and tokenizes;
* the chain never weakens a request: a mirror without ``punkt_tab`` still
  installs ``punkt``; a failing index is fetched once; the caller's list is
  not changed; the successor is fetched once whatever the request holds;
  ``quiet``, ``force``, ``halt_on_error``, ``raise_on_error`` and
  ``print_error_to`` keep their meaning;
* a hostile ``punkt_tab`` archive or index entry reached through the chain
  is refused exactly as when ``punkt_tab`` is asked for directly: the same
  sandbox root, size bounds, deadlines, member checks and sanitised output;
* no spoofed name gets through: a lookalike, case or suffix alias of
  ``punkt_tab`` in the index is never chained, an index whose packages
  would install into one another's place is refused, a request spelled
  like ``punkt`` is not ``punkt``, and an archive member whose name a
  filesystem or terminal would not keep as written is refused;
* the chain is one way and the pickles stay unreachable: asking for
  ``punkt_tab`` never brings ``punkt``, and a hostile ``punkt`` pickle is
  never unpickled however its pickle-era name is loaded.

The only thing loosened is the SSRF filter, for exactly 127.0.0.1, so the
local server is reachable. Endless routes stop at a hard 128 MiB cap.
Interactive prompts are answered by feeding ``input()``; the code under test
is never replaced. Control, bidi and lookalike characters are built with chr().
"""

import builtins
import contextlib
import inspect
import io
import json
import os
import runpy
import stat
import sys
import unicodedata
import warnings
import zipfile

import pytest

import nltk
import nltk.data
from nltk import downloader
from nltk.test.unit import timing
from nltk.test.unit.test_attack_allowlist_callers_expanded import _pkg_env
from nltk.test.unit.test_attack_downloader_zip_expanded import (  # noqa: F401  (box is a fixture)
    BEL,
    CSI8,
    ESC,
    NEL,
    OSC8,
    RLO,
    ST8,
    ZWSP,
    assert_lines_clean,
    box,
    make_index,
    make_zip,
    needs_dir_fd,
    needs_symlink,
    package_attrs,
    patch_declared_size,
    run_download,
    tree,
)
from nltk.tokenize import (
    _get_punkt_tokenizer,
    punkt_model_available,
    sent_tokenize,
    word_tokenize,
)

HARD_STOP = 128 * 1024 * 1024
NBSP = chr(0xA0)
CYRILLIC_ER = chr(0x0440)  # looks like a Latin "p"
FULLWIDTH_LOW_LINE = chr(0xFF3F)  # NFKC folds it to "_"
CAFE = "caf" + chr(0xE9)

ABBREV = "zzq"
SAMPLE = "I met zzq. Smith today. Then we left."
#: How the served punkt_tab splits SAMPLE: "zzq" is one of its abbreviations,
#: so no real model (and no fallback) could produce this split.
SERVED_SPLIT = ["I met zzq. Smith today.", "Then we left."]

TAB_BASE = (
    ("punkt_tab/", b""),
    ("punkt_tab/english/", b""),
    ("punkt_tab/english/collocations.tab", b""),
    ("punkt_tab/english/sent_starters.txt", b""),
    ("punkt_tab/english/abbrev_types.txt", (ABBREV + "\n").encode()),
    ("punkt_tab/english/ortho_context.tab", b""),
)
PUNKT_README = b"pickle-era Punkt models, never read by this NLTK\n"


def punkt_tab_zip(*extra):
    return make_zip(list(TAB_BASE) + list(extra))


def unpickling_marker(marker):
    """Protocol-0 pickle bytes that create *marker* if anything unpickles
    them (builtins.open(marker, "w")); inert as bytes on disk."""
    return b"cbuiltins\nopen\n(V" + str(marker).encode() + b"\nVw\ntR."


def punkt_zip(payload=b"not a pickle"):
    return make_zip(
        [
            ("punkt/", b""),
            ("punkt/README", PUNKT_README),
            ("punkt/english.pickle", payload),
            ("punkt/PY3/", b""),
            ("punkt/PY3/english.pickle", payload),
        ]
    )


def tiny_zip(pid):
    return make_zip([(f"{pid}/", b""), (f"{pid}/words.txt", b"alpha\n")])


def serve_chain(
    server,
    *,
    tab=None,
    tab_extra=None,
    punkt=None,
    punkt_extra=None,
    with_tab=True,
    others=(),
    collections=(),
):
    """Serve punkt (pickle era), punkt_tab and *others*; return the index URL."""
    packages = [
        (
            "punkt",
            punkt if punkt is not None else punkt_zip(),
            {"subdir": "tokenizers", **(punkt_extra or {})},
        )
    ]
    if with_tab:
        packages.append(
            (
                "punkt_tab",
                tab if tab is not None else punkt_tab_zip(),
                {"subdir": "tokenizers", **(tab_extra or {})},
            )
        )
    packages.extend(others)
    attrs = []
    for pid, blob, extra in packages:
        extra = dict(extra)
        url = extra.pop("url", None)
        path = f"/pkgs/{pid}.zip"
        server.body(path, blob)
        entry = package_attrs(pid, blob, server.url(path), **extra)
        if url is not None:
            entry["url"] = url
        attrs.append(entry)
    server.body("/index.xml", make_index(attrs, collections))
    return server.url("/index.xml")


def hits(server, pid):
    return server.hits.count(f"/pkgs/{pid}.zip")


def toks(dl):
    return tree(str(dl / "tokenizers"))


def tab_installed(dl):
    return (dl / "tokenizers" / "punkt_tab" / "english" / "abbrev_types.txt").is_file()


def punkt_installed(dl):
    readme = dl / "tokenizers" / "punkt" / "README"
    return readme.is_file() and readme.read_bytes() == PUNKT_README


def served_split():
    """Split SAMPLE with the installed punkt_tab, found through nltk.data."""
    from nltk.tokenize import PunktTokenizer

    return PunktTokenizer("english").tokenize(SAMPLE)


def assert_contained(root, outside, dl):
    """Nothing outside the box, and nothing in the data root outside dl."""
    assert list(outside.iterdir()) == []
    stray = [p.name for p in root.iterdir() if p.name != "dl"]
    assert stray == [], stray


def feed_input(monkeypatch, answers):
    """Answer the downloader's prompts with *answers*; an extra prompt fails."""
    asked = []
    queue = list(answers)

    def answer(*_prompt):
        asked.append(_prompt)
        if not queue:
            raise AssertionError("an unexpected interactive prompt")
        return queue.pop(0)

    monkeypatch.setattr(builtins, "input", answer)
    return asked


def run_cli(monkeypatch, *argv):
    """``python -m nltk.downloader *argv``, executed in this process (so the
    loopback allowance holds) through runpy, the way the interpreter runs it."""
    monkeypatch.setattr(sys, "argv", ["nltk.downloader", *argv])
    out, err = io.StringIO(), io.StringIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # already imported
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            runpy.run_module("nltk.downloader", run_name="__main__", alter_sys=False)
    return out.getvalue() + err.getvalue()


#: Every attribute of the module-level Downloader that a download changes.
_DOWNLOADER_STATE = (
    "_url",
    "_download_dir",
    "_index",
    "_index_timestamp",
    "_index_url",
    "_packages",
    "_collections",
    "_status_cache",
    "_errors",
)
_MISSING = object()


@contextlib.contextmanager
def module_downloader(index_url, dl):
    """Point nltk.download's own Downloader at *index_url*, then restore it."""
    d = downloader._downloader
    saved = {}
    for name in _DOWNLOADER_STATE:
        value = getattr(d, name, _MISSING)
        saved[name] = dict(value) if isinstance(value, dict) else value
    try:
        d._url = index_url
        d._index = None
        d._index_timestamp = None
        d._packages, d._collections, d._status_cache = {}, {}, {}
        d._download_dir = str(dl)
        yield d
    finally:
        for name, value in saved.items():
            if value is _MISSING:
                if hasattr(d, name):
                    delattr(d, name)
            else:
                setattr(d, name, value)


# ===========================================================================
# 1. Every way of asking for punkt reaches a working punkt_tab
# ===========================================================================
REQUEST_SHAPES = {
    "string": lambda d: "punkt",
    "list": lambda d: ["punkt"],
    "tuple": lambda d: ("punkt",),
    "package-object": lambda d: d.info("punkt"),
    "popular-like-collection": lambda d: "popularish",
    "book-like-nested-collection": lambda d: "bookish",
    "list-with-collection": lambda d: ["popularish", "tinyb"],
}
SHAPE_COLLECTIONS = [
    ("popularish", ["tinya", "punkt", "tinyb"]),
    ("bookish", ["popularish", "tinyc"]),
]
SHAPE_OTHERS = [
    ("tinya", tiny_zip("tinya"), {}),
    ("tinyb", tiny_zip("tinyb"), {}),
    ("tinyc", tiny_zip("tinyc"), {}),
]


class TestEveryEntryPointReachesTheSuccessor:
    @pytest.mark.parametrize("shape", sorted(REQUEST_SHAPES))
    def test_the_request_installs_a_punkt_tab_that_tokenizes(self, box, shape):
        root, outside, dl, server = box
        index_url = serve_chain(
            server, others=SHAPE_OTHERS, collections=SHAPE_COLLECTIONS
        )
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        request = REQUEST_SHAPES[shape](d)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            result = d.download(request, download_dir=str(dl), print_error_to=err)
        output = out.getvalue() + err.getvalue()
        assert result is True, output
        assert punkt_installed(dl) and tab_installed(dl), toks(dl)
        assert served_split() == SERVED_SPLIT
        assert hits(server, "punkt_tab") == 1
        assert d.status("punkt_tab", str(dl)) == d.INSTALLED
        assert_lines_clean(output)
        assert_contained(root, outside, dl)

    def test_nltk_download_itself(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        out, err = io.StringIO(), io.StringIO()
        with module_downloader(index_url, dl), contextlib.redirect_stdout(out):
            result = nltk.download("punkt", download_dir=str(dl), print_error_to=err)
        assert result is True, out.getvalue() + err.getvalue()
        assert punkt_installed(dl) and tab_installed(dl)
        assert served_split() == SERVED_SPLIT

    def test_the_command_line(self, box, monkeypatch):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        output = run_cli(monkeypatch, "-d", str(dl), "-u", index_url, "punkt")
        assert punkt_installed(dl) and tab_installed(dl), output
        assert "punkt_tab" in output
        assert_lines_clean(output)
        assert served_split() == SERVED_SPLIT

    def test_the_command_line_quiet_and_forced(self, box, monkeypatch):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        run_cli(monkeypatch, "-d", str(dl), "-u", index_url, "punkt")
        output = run_cli(
            monkeypatch, "-q", "-f", "-d", str(dl), "-u", index_url, "punkt"
        )
        assert output.strip() == ""
        assert hits(server, "punkt") == 2 and hits(server, "punkt_tab") == 2
        assert tab_installed(dl)

    def test_the_text_shell(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            downloader.DownloaderShell(d)._simple_interactive_download(["punkt"])
        assert punkt_installed(dl) and tab_installed(dl)
        assert_lines_clean(out.getvalue() + err.getvalue())

    def test_the_gui_call_incr_download_with_a_marked_list(self, box):
        # DownloaderGUI._download calls self._ds.incr_download(marked, dir)
        root, outside, dl, server = box
        index_url = serve_chain(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        messages = list(d.incr_download(["punkt"], str(dl)))
        started = [
            m.package.id
            for m in messages
            if isinstance(m, downloader.StartPackageMessage)
        ]
        assert started == ["punkt", "punkt_tab"]
        assert not any(isinstance(m, downloader.ErrorMessage) for m in messages)
        assert tab_installed(dl)

    def test_update_reinstalls_a_stale_punkt_with_its_successor(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        (dl / "tokenizers").mkdir()
        (dl / "tokenizers" / "punkt.zip").write_bytes(b"truncated")
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt") == d.STALE
        with contextlib.redirect_stdout(io.StringIO()):
            d.update(quiet=True)
        assert punkt_installed(dl) and tab_installed(dl)
        assert d.status("punkt") == d.INSTALLED
        assert d.status("punkt_tab") == d.INSTALLED

    def test_the_callers_list_is_left_as_given(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        request = ["punkt"]
        result, output = run_download(index_url, dl, request)
        assert result is True, output
        assert request == ["punkt"]
        assert tab_installed(dl)


# ===========================================================================
# 2. The chain never weakens a request
# ===========================================================================
class TestBookkeeping:
    def test_an_installed_successor_is_reported_up_to_date_not_refetched(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt_tab")[0] is True
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert hits(server, "punkt_tab") == 1
        assert "punkt_tab is already up-to-date" in output

    def test_a_stale_successor_is_refetched_once(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt")[0] is True
        (dl / "tokenizers" / "punkt_tab" / "english" / "abbrev_types.txt").write_bytes(
            b"tampered-and-longer\n"
        )
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert hits(server, "punkt_tab") == 2
        assert served_split() == SERVED_SPLIT

    def test_force_refetches_each_package_once(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt")[0] is True
        result, output = run_download(index_url, dl, "punkt", force=True)
        assert result is True, output
        assert hits(server, "punkt") == 2 and hits(server, "punkt_tab") == 2

    @pytest.mark.parametrize(
        "request_",
        [
            ["punkt", "punkt_tab"],
            ["punkt_tab", "punkt"],
            ["punkt", "punkt"],
            ["punkt", "punkt_tab", "punkt"],
            "allish",
            ["popularish", "allish"],
        ],
        ids=lambda r: "+".join(r) if isinstance(r, list) else r,
    )
    @pytest.mark.parametrize("force", [False, True], ids=["plain", "forced"])
    def test_the_successor_is_fetched_once_whatever_the_request_holds(
        self, box, request_, force
    ):
        root, outside, dl, server = box
        index_url = serve_chain(
            server,
            collections=[
                ("allish", ["punkt", "punkt_tab"]),
                ("popularish", ["punkt"]),
            ],
        )
        result, output = run_download(index_url, dl, request_, force=force)
        assert result is True, output
        assert hits(server, "punkt_tab") == 1
        assert tab_installed(dl)

    def test_asking_for_the_successor_never_brings_the_pickles(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        result, output = run_download(index_url, dl, "punkt_tab")
        assert result is True, output
        assert hits(server, "punkt") == 0
        assert not (dl / "tokenizers" / "punkt").exists()
        assert served_split() == SERVED_SPLIT

    def test_the_successor_map_is_one_way_and_has_no_chains(self):
        table = downloader._SUCCESSORS
        assert set(table) & set(table.values()) == set()
        assert len(set(table.values())) == len(table)
        assert all(isinstance(k, str) and isinstance(v, str) for k, v in table.items())
        assert table["punkt"] == "punkt_tab"

    def test_a_package_object_with_no_index_loaded_fetches_no_index(self, box):
        root, outside, dl, server = box
        blob = punkt_zip()
        index_url = serve_chain(server, punkt=blob)
        package = downloader.Package(
            **package_attrs(
                "punkt", blob, server.url("/pkgs/punkt.zip"), subdir="tokenizers"
            )
        )
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            result = d.download(package, download_dir=str(dl), print_error_to=err)
        assert result is True, out.getvalue() + err.getvalue()
        assert server.hits.count("/index.xml") == 0
        assert hits(server, "punkt_tab") == 0
        assert punkt_installed(dl)

    @pytest.mark.parametrize("shape", ["string", "list", "collection"])
    def test_a_mirror_without_the_successor_still_installs_what_was_asked(
        self, box, shape
    ):
        root, outside, dl, server = box
        index_url = serve_chain(
            server, with_tab=False, collections=[("popularish", ["punkt"])]
        )
        request_ = {"string": "punkt", "list": ["punkt"], "collection": "popularish"}
        result, output = run_download(index_url, dl, request_[shape])
        assert result is True, output
        assert punkt_installed(dl)
        assert "Error" not in output
        assert hits(server, "punkt_tab") == 0

    def test_a_mirror_without_the_successor_asks_nothing_interactively(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        index_url = serve_chain(server, with_tab=False)
        asked = feed_input(monkeypatch, ["y", "y", "n"])
        result, output = run_download(index_url, dl, "punkt", halt_on_error=False)
        assert result is True, output
        assert asked == []
        assert punkt_installed(dl)

    def test_a_mirror_without_the_successor_through_the_command_line(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        index_url = serve_chain(server, with_tab=False)
        asked = feed_input(monkeypatch, ["n"])
        output = run_cli(monkeypatch, "-d", str(dl), "-u", index_url, "punkt")
        assert punkt_installed(dl), output
        assert asked == [] and "Error" not in output

    def test_quiet_prints_nothing_and_loud_names_the_successor(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        result, output = run_download(index_url, dl, "punkt", quiet=True)
        assert result is True and output == ""
        result, output = run_download(index_url, dl, "punkt", force=True)
        assert result is True
        assert "Downloading package punkt_tab" in output.replace("\n[nltk_data]  ", "")
        assert_lines_clean(output)

    @pytest.mark.parametrize("failure", ["status-500", "refused-entry"])
    @pytest.mark.parametrize("request_", ["punkt", ["punkt"]], ids=["str", "list"])
    def test_a_failing_index_is_fetched_once(self, box, failure, request_):
        root, outside, dl, server = box
        if failure == "status-500":
            server.body("/index.xml", b"no", status=500)
        else:
            attrs = package_attrs(
                "punkt", punkt_zip(), server.url("/pkgs/punkt.zip"), subdir="../up"
            )
            server.body("/index.xml", make_index([attrs]))
        result, output = run_download(server.url("/index.xml"), dl, request_)
        assert result is False
        assert server.hits.count("/index.xml") == 1
        assert_lines_clean(output)
        assert toks(dl) == {}

    def test_a_working_index_is_fetched_once_for_the_whole_chain(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server, collections=[("popularish", ["punkt"])])
        assert run_download(index_url, dl, "popularish")[0] is True
        assert server.hits.count("/index.xml") == 1

    def test_the_default_directory_is_chosen_once_and_used_for_both(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        messages = list(d.incr_download("punkt"))
        chosen = [
            m.download_dir
            for m in messages
            if isinstance(m, downloader.SelectDownloadDirMessage)
        ]
        assert chosen == [str(dl)]
        assert tab_installed(dl) and punkt_installed(dl)

    def test_an_explicit_directory_is_used_for_the_successor_too(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        other = root / "default_dir"
        other.mkdir()
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(other))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out):
            assert d.download("punkt", download_dir=str(dl), print_error_to=err)
        assert tab_installed(dl) and punkt_installed(dl)
        assert list(other.iterdir()) == []
        assert list(outside.iterdir()) == []

    def test_the_search_path_gains_only_the_download_directory(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        before = list(nltk.data.path)
        assert run_download(index_url, dl, "punkt")[0] is True
        added = [p for p in nltk.data.path if p not in before]
        assert added == [os.path.realpath(str(dl))]


# ===========================================================================
# 3. Failure semantics of the second download
# ===========================================================================
class TestWhenTheSuccessorFails:
    def _failing(self, server):
        index_url = serve_chain(server)
        reason = "Gone" + ESC + "]52;c;aGk=" + BEL + ESC + "[2J"
        server.body("/pkgs/punkt_tab.zip", b"", status=404, reason=reason)
        return index_url

    def test_the_default_halts_with_false_and_keeps_what_installed(self, box):
        root, outside, dl, server = box
        result, output = run_download(self._failing(server), dl, "punkt")
        assert result is False
        assert punkt_installed(dl)
        assert not os.path.exists(dl / "tokenizers" / "punkt_tab.zip")
        assert not os.path.exists(dl / "tokenizers" / "punkt_tab.zip.tmp")
        assert not os.path.exists(dl / "tokenizers" / "punkt_tab.zip.lock")
        assert "punkt_tab" in output
        assert_lines_clean(output)

    def test_raise_on_error_names_the_successor_in_a_clean_message(self, box):
        root, outside, dl, server = box
        index_url = self._failing(server)
        with pytest.raises(ValueError) as caught:
            run_download(index_url, dl, "punkt", raise_on_error=True)
        assert "punkt_tab" in str(caught.value)
        assert_lines_clean(str(caught.value))

    def test_the_error_goes_to_print_error_to_only(self, box, capsys):
        root, outside, dl, server = box
        index_url = self._failing(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        err = io.StringIO()
        assert d.download("punkt", download_dir=str(dl), print_error_to=err) is False
        captured = capsys.readouterr()
        assert "punkt_tab" in err.getvalue()
        assert "punkt_tab" not in captured.err
        assert_lines_clean(err.getvalue())

    def test_no_halt_and_quiet_returns_true_with_errors_flagged(self, box):
        root, outside, dl, server = box
        index_url = self._failing(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()):
            result = d.download(
                "punkt",
                download_dir=str(dl),
                quiet=True,
                halt_on_error=False,
                print_error_to=err,
            )
        assert result is True and d._errors is True
        assert punkt_installed(dl)

    def test_a_retry_is_bounded_by_the_answers(self, box, monkeypatch):
        root, outside, dl, server = box
        index_url = self._failing(server)
        asked = feed_input(monkeypatch, ["y", "n"])
        result, output = run_download(index_url, dl, "punkt", halt_on_error=False)
        assert len(asked) == 2
        assert hits(server, "punkt_tab") == 2
        assert hits(server, "punkt") == 1
        assert_lines_clean(output)

    def test_a_failed_predecessor_without_halting_still_gets_its_successor(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        server.body("/pkgs/punkt.zip", b"", status=404)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        with contextlib.redirect_stdout(io.StringIO()):
            result = d.download(
                "punkt",
                download_dir=str(dl),
                quiet=True,
                halt_on_error=False,
                print_error_to=io.StringIO(),
            )
        assert result is True and d._errors is True
        assert tab_installed(dl)
        assert served_split() == SERVED_SPLIT

    def test_a_failed_predecessor_halting_stops_before_the_successor(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        server.body("/pkgs/punkt.zip", b"", status=404)
        result, output = run_download(index_url, dl, "punkt")
        assert result is False
        assert hits(server, "punkt_tab") == 0


# ===========================================================================
# 4. A hostile punkt_tab archive: the chain refuses it as a direct request does
# ===========================================================================
PLANTED_PICKLE_BYTES = b"cos\nsystem\n(Vplanted\ntR."
HOSTILE_MEMBERS = {
    "parent-traversal": ("punkt_tab/../../evil.txt", b"EVIL"),
    "deep-traversal": ("punkt_tab/english/../../../evil.txt", b"EVIL"),
    "root-traversal": ("../evil.txt", b"EVIL"),
    "absolute": ("/evil.txt", b"EVIL"),
    "backslash-traversal": ("punkt_tab\\..\\..\\evil.txt", b"EVIL"),
    "drive-letter": ("C:/evil.txt", b"EVIL"),
    "unc": ("\\\\server\\share\\evil.txt", b"EVIL"),
    "into-the-punkt-pickles": ("punkt/PY3/english.pickle", PLANTED_PICKLE_BYTES),
    "sibling-root": ("punkt_tab_evil/x.txt", b"EVIL"),
    "case-variant-root": ("Punkt_tab/english/abbrev_types.txt", b"EVIL"),
    "fullwidth-root": ("punkt" + FULLWIDTH_LOW_LINE + "tab/english/x.txt", b"EVIL"),
    "duplicate": ("punkt_tab/english/abbrev_types.txt", b"EVIL"),
    "case-collision": ("punkt_tab/english/Abbrev_types.txt", b"EVIL"),
    "nfd-collision": [
        ("punkt_tab/english/" + unicodedata.normalize("NFC", CAFE) + ".txt", b"ok"),
        ("punkt_tab/english/" + unicodedata.normalize("NFD", CAFE) + ".txt", b"EVIL"),
    ],
    "trailing-dot-collision": ("punkt_tab/english/abbrev_types.txt.", b"EVIL"),
    "trailing-space-collision": ("punkt_tab/english/abbrev_types.txt ", b"EVIL"),
    "trailing-space-dir": ("punkt_tab/english /abbrev_types.txt", b"EVIL"),
    "trailing-dot-dir": ("punkt_tab/english./abbrev_types.txt", b"EVIL"),
    "escape-sequence": ("punkt_tab/english/a" + ESC + "[2Jb.txt", b"EVIL"),
    "osc52-clipboard": ("punkt_tab/english/" + ESC + "]52;c;aGk=" + BEL, b"EVIL"),
    "line-feed": ("punkt_tab/english/a\nb.txt", b"EVIL"),
    "carriage-return": ("punkt_tab/english/a\rb.txt", b"EVIL"),
    "next-line": ("punkt_tab/english/a" + NEL + "b.txt", b"EVIL"),
    "rlo-extension-spoof": ("punkt_tab/english/" + RLO + "txt.exe", b"EVIL"),
    "zero-width": ("punkt_tab/english/abbrev" + ZWSP + "_types.txt", b"EVIL"),
    "nfd-name": (
        "punkt_tab/english/" + unicodedata.normalize("NFD", "x" + CAFE),
        b"EVIL",
    ),
}
if os.name != "posix":
    HOSTILE_MEMBERS["device-name"] = ("punkt_tab/english/CON.txt", b"EVIL")
# zipfile writes each of these as "_" when it extracts on Windows, so the twin
# lands on abbrev_types.txt there: refused everywhere, as a case twin is
WINDOWS_UNWRITABLE = {
    "colon": ":",
    "less-than": "<",
    "greater-than": ">",
    "pipe": "|",
    "quote": '"',
    "question": "?",
    "star": "*",
}
for _label, _char in WINDOWS_UNWRITABLE.items():
    HOSTILE_MEMBERS[f"windows-{_label}-collision"] = (
        "punkt_tab/english/abbrev" + _char + "types.txt",
        b"EVIL",
    )
HOSTILE_MEMBERS["file-and-directory"] = ("punkt_tab/english", b"FILE")
HOSTILE_MEMBERS["nul-cut-name"] = (
    "punkt_tab/english/abbrev_types.txt" + chr(0) + ".x",
    b"EVIL",
)


def patch_member(blob, name, *, flag=0, method=None, local_name=None):
    """Rewrite *name*'s zip headers: OR *flag* into its general purpose bits,
    set its compression *method*, or give its local header *local_name* (of
    the same length) while the central directory keeps *name*."""
    data = bytearray(blob)
    encoded = name.encode()
    for signature, length_at, flag_at, method_at, name_at in (
        (b"PK\x03\x04", 26, 6, 8, 30),
        (b"PK\x01\x02", 28, 8, 10, 46),
    ):
        start = data.find(signature)
        while start >= 0:
            size = int.from_bytes(
                data[start + length_at : start + length_at + 2], "little"
            )
            if data[start + name_at : start + name_at + size] == encoded:
                data[start + flag_at] |= flag
                if method is not None:
                    data[start + method_at : start + method_at + 2] = method.to_bytes(
                        2, "little"
                    )
                if local_name is not None and signature == b"PK\x03\x04":
                    data[start + name_at : start + name_at + size] = local_name.encode()
            start = data.find(signature, start + 4)
    return bytes(data)


def _hostile_archive(label, server):
    """(tab blob, tab index extras) for an archive-level attack."""
    if label in HOSTILE_MEMBERS:
        members = HOSTILE_MEMBERS[label]
        if isinstance(members, tuple):
            members = [members]
        return punkt_tab_zip(*members), {}
    if label == "expands-past-its-declared-size":
        blob = punkt_tab_zip(("punkt_tab/english/liar.bin", b"A" * 200_000))
        return patch_declared_size(blob, "punkt_tab/english/liar.bin", 1000), {}
    if label == "more-than-the-index-declares":
        blob = punkt_tab_zip(("punkt_tab/english/pad.bin", b"\0" * (3 * 1024 * 1024)))
        return blob, {"unzipped_size": "1000"}
    if label == "ratio-bomb":
        return punkt_tab_zip(("punkt_tab/english/bomb.bin", bytes(64 << 20))), {}
    if label == "member-count-bomb":
        count = nltk.data.MAX_UNZIP_MEMBERS + 1
        return (
            punkt_tab_zip(*[(f"punkt_tab/english/f{i}", b"") for i in range(count)]),
            {},
        )
    # Each fails only when opened: before the phase 1 check the members ahead of
    # it were already on disk. The local header name differs in case only.
    blob = punkt_tab_zip(("punkt_tab/english/zz.txt", b"zzz"))
    if label == "encrypted-member":
        return patch_member(blob, "punkt_tab/english/zz.txt", flag=1), {}
    if label == "unknown-compression-method":
        return patch_member(blob, "punkt_tab/english/zz.txt", method=99), {}
    if label == "local-header-names-another-file":
        local = "punkt_tab/english/ZZ.txt"
        return patch_member(blob, "punkt_tab/english/zz.txt", local_name=local), {}
    raise KeyError(label)


ARCHIVE_ATTACKS = sorted(HOSTILE_MEMBERS) + [
    "expands-past-its-declared-size",
    "more-than-the-index-declares",
    "ratio-bomb",
    "member-count-bomb",
    "encrypted-member",
    "unknown-compression-method",
    "local-header-names-another-file",
]


class TestHostileSuccessorArchive:
    @pytest.mark.parametrize("route", ["chain", "direct"])
    @pytest.mark.parametrize("label", ARCHIVE_ATTACKS)
    def test_a_hostile_archive_is_refused_with_nothing_kept(self, box, label, route):
        root, outside, dl, server = box
        if label == "expands-past-its-declared-size" and not (
            os.name == "posix" and os.open in os.supports_dir_fd
        ):
            pytest.skip("the hardened extractor needs dir_fd")
        blob, extra = _hostile_archive(label, server)
        index_url = serve_chain(server, tab=blob, tab_extra=extra)
        target = "punkt" if route == "chain" else "punkt_tab"
        result, output = run_download(index_url, dl, target)
        assert result is False, (label, output)
        assert hits(server, "punkt_tab") == 1
        written = toks(dl)
        if label == "expands-past-its-declared-size":
            # caught while writing: the liar leaves nothing, members before it
            # may stay (a direct request keeps the same), the install is stale
            liar = os.path.join("punkt_tab", "english", "liar.bin")
            assert liar not in written, written
            d = downloader.Downloader(server_index_url=index_url)
            assert d.status("punkt_tab", str(dl)) != d.INSTALLED
        else:
            assert not any(name.startswith("punkt_tab" + os.sep) for name in written), (
                label,
                written,
            )
        assert not any("evil" in name.lower() for name in written), written
        assert not (dl / "evil.txt").exists() and not (root / "evil.txt").exists()
        if route == "chain":
            assert punkt_installed(dl)
            planted = dl / "tokenizers" / "punkt" / "PY3" / "english.pickle"
            assert planted.read_bytes() == b"not a pickle"
        assert_lines_clean(output)
        assert_contained(root, outside, dl)

    @needs_symlink
    @pytest.mark.parametrize("route", ["chain", "direct"])
    def test_a_symlink_member_is_written_as_a_plain_file(self, box, route):
        root, outside, dl, server = box
        link = zipfile.ZipInfo("punkt_tab/english/link")
        link.create_system = 3
        link.external_attr = (0o120777) << 16
        target = os.path.relpath(str(outside), str(dl / "tokenizers" / "punkt_tab"))
        blob = punkt_tab_zip((link, target.encode()))
        index_url = serve_chain(server, tab=blob)
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is True, output
        placed = dl / "tokenizers" / "punkt_tab" / "english" / "link"
        assert not placed.is_symlink() and placed.read_bytes() == target.encode()
        assert list(outside.iterdir()) == []
        assert served_split() == SERVED_SPLIT

    @pytest.mark.parametrize("route", ["chain", "direct"])
    @pytest.mark.parametrize(
        "body",
        ["checksum-mismatch", "cut-short", "endless", "declared-past-the-ceiling"],
    )
    def test_a_hostile_body_is_refused_within_its_bounds(self, box, body, route):
        root, outside, dl, server = box
        blob = punkt_tab_zip()
        extra = {}
        if body == "declared-past-the-ceiling":
            extra = {"size": str(downloader.MAX_PACKAGE_BYTES + 1)}
        index_url = serve_chain(server, tab=blob, tab_extra=extra)
        if body == "checksum-mismatch":
            server.body("/pkgs/punkt_tab.zip", blob[:-1] + bytes([blob[-1] ^ 1]))
        elif body == "cut-short":
            server.truncated("/pkgs/punkt_tab.zip", blob, len(blob) // 2)
        elif body in ("endless", "declared-past-the-ceiling"):
            server.stream("/pkgs/punkt_tab.zip", b"Z" * 65536, cap=HARD_STOP)
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is False, output
        assert server.sent.get("/pkgs/punkt_tab.zip", 0) < HARD_STOP
        assert not tab_installed(dl)
        for leftover in ("punkt_tab.zip", "punkt_tab.zip.tmp", "punkt_tab.zip.lock"):
            assert not (dl / "tokenizers" / leftover).exists(), leftover
        if body == "declared-past-the-ceiling":
            assert hits(server, "punkt_tab") == 0
        assert_lines_clean(output)

    def test_a_drip_fed_successor_meets_the_package_deadline(self, box, monkeypatch):
        root, outside, dl, server = box
        monkeypatch.setattr(downloader, "PACKAGE_DEADLINE_FLOOR", 1.0)
        blob = punkt_tab_zip()
        index_url = serve_chain(server, tab=blob)
        server.drip("/pkgs/punkt_tab.zip", blob, delay=0.05)
        with timing.budget(12, "the successor's drip, which needs its deadline"):
            result, output = run_download(index_url, dl, "punkt")
        assert result is False, output
        assert "time budget" in output
        assert not (dl / "tokenizers" / "punkt_tab.zip").exists()
        assert punkt_installed(dl)

    @needs_symlink
    def test_a_planted_link_for_the_successor_directory_is_not_followed(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        (dl / "tokenizers").mkdir()
        os.symlink(str(outside), str(dl / "tokenizers" / "punkt_tab"))
        result, output = run_download(index_url, dl, "punkt")
        assert list(outside.iterdir()) == []
        if result:
            assert not (dl / "tokenizers" / "punkt_tab").is_symlink()
            assert served_split() == SERVED_SPLIT

    @needs_symlink
    def test_a_planted_link_for_the_tokenizers_directory_is_refused(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        os.symlink(str(outside), str(dl / "tokenizers"))
        result, output = run_download(index_url, dl, "punkt")
        assert result is False
        assert list(outside.iterdir()) == []
        assert_lines_clean(output)


# ===========================================================================
# 5. A hostile index entry for the successor, aliases and spoofed names
# ===========================================================================
LOOKALIKE_IDS = {
    "cyrillic-er": CYRILLIC_ER + "unkt_tab",
    "fullwidth-low-line": "punkt" + FULLWIDTH_LOW_LINE + "tab",
    "nbsp-suffix": "punkt_tab" + NBSP,
    "hyphen": "punkt-tab",
    "upper-case": "PUNKT_TAB",
    "title-case": "Punkt_tab",
    "zip-suffix": "punkt_tab.zip",
    "plural": "punkt_tabs",
}
INVISIBLE_IDS = {
    "zero-width": "punkt" + ZWSP + "_tab",
    "rlo": "punkt_tab" + RLO,
    "trailing-space": "punkt_tab ",
    "trailing-dot": "punkt_tab.",
    "nfd": unicodedata.normalize("NFD", "punkt_tab" + CAFE),
    "c1-csi": "punkt_tab" + CSI8 + "2J",
    "c1-osc": "punkt_tab" + OSC8 + "0;pwned" + ST8,
    "next-line": "punkt_tab" + NEL,
}


class TestHostileIndexEntry:
    def test_a_successor_listed_only_as_a_collection_is_not_followed(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(
            server,
            with_tab=False,
            others=[("tinya", tiny_zip("tinya"), {})],
            collections=[
                ("punkt_tab", ["punkt", "loop", "tinya"]),
                ("loop", ["punkt_tab", "punkt"]),
            ],
        )
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert hits(server, "tinya") == 0
        assert hits(server, "punkt") == 1
        assert "collection" not in output

    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/punkt_tab.zip",
            "http://[::1]:1/punkt_tab.zip",
            "http://10.0.0.1/punkt_tab.zip",
            "file:///etc/passwd.zip",
            "ftp://127.0.0.1/punkt_tab.zip",
        ],
        ids=["metadata", "ipv6-loopback-port", "private", "file-scheme", "ftp"],
    )
    @pytest.mark.parametrize("route", ["chain", "direct"])
    def test_a_successor_url_to_a_forbidden_place_is_refused(self, box, url, route):
        root, outside, dl, server = box
        index_url = serve_chain(server, tab_extra={"url": url})
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is False, output
        assert not tab_installed(dl)
        assert_lines_clean(output)
        assert_contained(root, outside, dl)

    @pytest.mark.parametrize("route", ["chain", "direct"])
    def test_a_successor_redirected_to_the_metadata_address_is_refused(
        self, box, route
    ):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        server.redirect(
            "/pkgs/punkt_tab.zip",
            "http://169.254.169.254/latest/meta-data/punkt_tab.zip",
        )
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is False, output
        assert not tab_installed(dl)

    def test_a_successor_in_another_subdir_stays_in_the_download_directory(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server, tab_extra={"subdir": "corpora"})
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert (dl / "corpora" / "punkt_tab" / "english").is_dir()
        assert_contained(root, outside, dl)

    @pytest.mark.parametrize(
        "subdir", ["tokenizers/punkt", "tokenizers/punkt.zip", "tokenizers/PUNKT"]
    )
    @pytest.mark.parametrize("order", ["chain", "punkt-then-punkt_tab"])
    def test_a_successor_placed_inside_another_package_is_an_alias(
        self, box, subdir, order
    ):
        # Without the refusal, "tokenizers/punkt.zip" makes download() raise a
        # raw FileExistsError (its subdir runs through punkt's archive file)
        # and "tokenizers/punkt" extracts into punkt's own directory.
        root, outside, dl, server = box
        index_url = serve_chain(server, tab_extra={"subdir": subdir})
        targets = ["punkt"] if order == "chain" else ["punkt", "punkt_tab"]
        for target in targets:
            result, output = run_download(index_url, dl, target)
            assert result is False, output
            assert "install path" in output
            assert_lines_clean(output)
        assert toks(dl) == {}
        assert set(server.hits) == {"/index.xml"}

    @pytest.mark.parametrize("label", sorted(LOOKALIKE_IDS))
    def test_a_lookalike_beside_the_successor_is_never_chained(self, box, label):
        root, outside, dl, server = box
        alias = LOOKALIKE_IDS[label]
        evil = make_zip([(f"{alias}/", b""), (f"{alias}/x.txt", b"EVIL")])
        index_url = serve_chain(
            server, others=[(alias, evil, {"subdir": "tokenizers"})]
        )
        result, output = run_download(index_url, dl, "punkt")
        folds_onto_punkt_tab = alias.rstrip(" .").casefold() == "punkt_tab" or (
            unicodedata.normalize("NFKC", alias).casefold() == "punkt_tab"
        )
        claims_the_archive_name = alias == "punkt_tab.zip"
        if folds_onto_punkt_tab or claims_the_archive_name:
            # one install path on a case-folding or normalising filesystem
            assert result is False, output
            assert "install path" in output
            assert toks(dl) == {}
        else:
            assert result is True, output
            assert served_split() == SERVED_SPLIT
        assert server.hits.count(f"/pkgs/{alias}.zip") == 0
        if not folds_onto_punkt_tab:
            assert not (dl / "tokenizers" / alias).exists()

    @pytest.mark.parametrize("label", sorted(LOOKALIKE_IDS))
    def test_a_lookalike_alone_is_never_taken_for_the_successor(self, box, label):
        root, outside, dl, server = box
        alias = LOOKALIKE_IDS[label]
        evil = make_zip([(f"{alias}/", b""), (f"{alias}/x.txt", b"EVIL")])
        index_url = serve_chain(
            server, with_tab=False, others=[(alias, evil, {"subdir": "tokenizers"})]
        )
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert punkt_installed(dl)
        assert server.hits.count(f"/pkgs/{alias}.zip") == 0
        assert not tab_installed(dl)

    @pytest.mark.parametrize("label", sorted(INVISIBLE_IDS))
    def test_an_id_a_filesystem_or_terminal_would_change_refuses_the_index(
        self, box, label
    ):
        root, outside, dl, server = box
        alias = INVISIBLE_IDS[label]
        evil = make_zip([("x/", b""), ("x/x.txt", b"EVIL")])
        attrs = [
            package_attrs(
                "punkt", punkt_zip(), server.url("/pkgs/punkt.zip"), subdir="tokenizers"
            ),
            package_attrs(alias, evil, server.url("/pkgs/x.zip"), subdir="tokenizers"),
        ]
        server.body("/index.xml", make_index(attrs))
        result, output = run_download(server.url("/index.xml"), dl, "punkt")
        assert result is False, output
        assert "Invalid package" in output  # refused for its name, nothing else
        assert server.hits == ["/index.xml"]
        assert toks(dl) == {}
        assert_lines_clean(output)

    @pytest.mark.parametrize(
        "spoof",
        [
            "punkt ",
            " punkt",
            "PUNKT",
            "Punkt",
            "tokenizers/punkt",
            "punkt.zip",
            "punkt\x00",
            "punkt" + ZWSP,
            CYRILLIC_ER + "unkt",
            "punkt" + RLO,
            "./punkt",
        ],
        ids=lambda s: s.encode("unicode_escape").decode("ascii"),
    )
    def test_a_request_spelled_like_punkt_is_not_punkt(self, box, spoof):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        result, output = run_download(index_url, dl, spoof)
        assert result is False
        assert hits(server, "punkt") == 0 and hits(server, "punkt_tab") == 0
        assert toks(dl) == {}
        assert_lines_clean(output)

    @pytest.mark.parametrize("route", ["chain", "direct"])
    def test_a_hostile_successor_name_is_displayed_inert(self, box, route):
        root, outside, dl, server = box
        # XML 1.0 refuses ESC and BEL outright; their C1 forms, a bidi
        # override and an entity-form line break all parse
        name = "Punkt" + OSC8 + "0;pwned" + ST8 + RLO + "\nFORGED" + CSI8 + "2J" + NEL
        index_url = serve_chain(
            server, tab_extra={"name": name}, punkt_extra={"name": name}
        )
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is True, output
        assert_lines_clean(output)
        out = io.StringIO()
        d = downloader.Downloader(server_index_url=index_url)
        with contextlib.redirect_stdout(out):
            d.list(download_dir=str(dl))
        assert_lines_clean(out.getvalue())
        assert not any(line.startswith("FORGED") for line in out.getvalue().split("\n"))

    def test_a_duplicate_successor_entry_resolves_as_a_direct_request_does(self, box):
        root, outside, dl, server = box
        first, second = punkt_tab_zip(), punkt_tab_zip(("punkt_tab/second.txt", b"2"))
        server.body("/pkgs/punkt.zip", punkt_zip())
        server.body("/pkgs/first.zip", first)
        server.body("/pkgs/second.zip", second)
        attrs = [
            package_attrs(
                "punkt", punkt_zip(), server.url("/pkgs/punkt.zip"), subdir="tokenizers"
            ),
            package_attrs(
                "punkt_tab", first, server.url("/pkgs/first.zip"), subdir="tokenizers"
            ),
            package_attrs(
                "punkt_tab", second, server.url("/pkgs/second.zip"), subdir="tokenizers"
            ),
        ]
        server.body("/index.xml", make_index(attrs))
        chained = root / "chained"
        direct = root / "direct"
        chained.mkdir()
        direct.mkdir()
        assert run_download(server.url("/index.xml"), chained, "punkt")[0] is True
        assert run_download(server.url("/index.xml"), direct, "punkt_tab")[0] is True
        assert tree(str(chained / "tokenizers" / "punkt_tab")) == tree(
            str(direct / "tokenizers" / "punkt_tab")
        )
        assert server.hits.count("/pkgs/first.zip") == 0


# ===========================================================================
# 6. The pickles stay unreachable
# ===========================================================================
class TestPicklesStayUnreachable:
    def test_a_hostile_punkt_pickle_is_never_unpickled(self, box):
        root, outside, dl, server = box
        marker = outside / "UNPICKLED"
        index_url = serve_chain(server, punkt=punkt_zip(unpickling_marker(marker)))
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        # the pickle-era names are served by punkt_tab, never by the pickles
        for name in (
            "tokenizers/punkt/english.pickle",
            "tokenizers/punkt/PY3/english.pickle",
            "nltk:tokenizers/punkt/english.pickle",
        ):
            tokenizer = nltk.data.load(name, cache=False)
            assert tokenizer.tokenize(SAMPLE) == SERVED_SPLIT, name
            assert not marker.exists(), name
        # loading the pickle file itself, by its path, is refused
        pickle_path = dl / "tokenizers" / "punkt" / "PY3" / "english.pickle"
        for url in ("file:" + str(pickle_path),):
            with pytest.raises(Exception) as caught:
                nltk.data.load(url, format="pickle", cache=False)
            assert not isinstance(caught.value, AssertionError)
            assert not marker.exists(), url
        assert not marker.exists()

    def test_a_pickle_inside_punkt_tab_is_never_read_by_the_tokenizer(self, box):
        root, outside, dl, server = box
        marker = outside / "UNPICKLED"
        blob = punkt_tab_zip(
            ("punkt_tab/english/english.pickle", unpickling_marker(marker))
        )
        index_url = serve_chain(server, tab=blob)
        assert run_download(index_url, dl, "punkt")[0] is True
        assert served_split() == SERVED_SPLIT
        assert not marker.exists()


# ===========================================================================
# 7. Composition with #3929 (extract=), when that change is present
# ===========================================================================
@pytest.mark.skipif(
    "extract" not in inspect.signature(downloader.Downloader.download).parameters,
    reason="needs the extract= option of #3929",
)
def test_the_successor_is_extracted_as_the_request_asks(box):
    root, outside, dl, server = box
    index_url = serve_chain(
        server, tab_extra={"unzip": "0"}, punkt_extra={"unzip": "0"}
    )
    result, output = run_download(index_url, dl, "punkt", extract=True)
    assert result is True, output
    assert (dl / "tokenizers" / "punkt_tab" / "english").is_dir()
    assert (dl / "tokenizers" / "punkt").is_dir()
    other = root / "plain"
    other.mkdir()
    result, output = run_download(index_url, other, "punkt", extract=False)
    assert result is True, output
    assert not (other / "tokenizers" / "punkt_tab").exists()
    assert (other / "tokenizers" / "punkt_tab.zip").is_file()


# ===========================================================================
# 8. Device names: refused where they open a device, kept as written elsewhere
# ===========================================================================
DEVICE_MEMBERS = {
    "conin": "CONIN$",
    "conout": "CONOUT$",
    "com-superscript-one": "COM" + chr(0xB9) + ".txt",
    "lpt-superscript-three": "LPT" + chr(0xB3),
    "con-space-stem": "CON .txt",
    "nul-lower": "nul.tab",
}


@pytest.mark.parametrize("label", sorted(DEVICE_MEMBERS))
def test_a_device_name_member_is_refused_only_where_it_names_a_device(box, label):
    root, outside, dl, server = box
    name = DEVICE_MEMBERS[label]
    blob = punkt_tab_zip(("punkt_tab/english/" + name, b"DEVICE?"))
    result, output = run_download(serve_chain(server, tab=blob), dl, "punkt")
    if os.name != "posix":
        assert result is False, output
        assert "character device name" in output
        assert not tab_installed(dl), toks(dl)
    else:
        assert result is True, output
        placed = dl / "tokenizers" / "punkt_tab" / "english" / name
        assert placed.read_bytes() == b"DEVICE?"
        assert served_split() == SERVED_SPLIT
    assert_lines_clean(output)
    assert_contained(root, outside, dl)


# ===========================================================================
# 9. A hostile index entry for the successor: other archives under its name
# ===========================================================================
class TestTheSuccessorEntryLies:
    @pytest.mark.parametrize("route", ["chain", "direct"])
    def test_the_successor_entry_serving_the_pickle_archive_is_refused(
        self, box, route
    ):
        root, outside, dl, server = box
        pickles = punkt_zip(b"HOSTILE")
        index_url = serve_chain(server, tab=pickles)
        if route == "direct":
            assert run_download(index_url, dl, "punkt")[0] is False
        result, output = run_download(
            index_url, dl, "punkt" if route == "chain" else "punkt_tab"
        )
        assert result is False, output
        assert "Cross-package overwrite blocked" in output
        planted = dl / "tokenizers" / "punkt" / "PY3" / "english.pickle"
        assert planted.read_bytes() == b"not a pickle"
        assert not tab_installed(dl)
        assert_contained(root, outside, dl)

    @pytest.mark.parametrize(
        "top",
        [
            "punkt_tab2",
            "PUNKT_TAB",
            "tokenizers/punkt_tab",
            "punkt",
            "averaged_perceptron_tagger_eng",
        ],
    )
    def test_a_successor_archive_under_another_top_directory_is_refused(self, box, top):
        root, outside, dl, server = box
        blob = make_zip(
            [(top + name[len("punkt_tab") :], data) for name, data in TAB_BASE]
        )
        result, output = run_download(serve_chain(server, tab=blob), dl, "punkt")
        assert result is False, output
        assert "Cross-package overwrite blocked" in output
        assert sorted(os.listdir(dl / "tokenizers")) == [
            "punkt",
            "punkt.zip",
            "punkt_tab.zip",
        ]
        assert not (dl / top).exists()
        assert_contained(root, outside, dl)

    def test_a_successor_served_as_a_bare_pickle_is_never_unpickled(self, box):
        root, outside, dl, server = box
        marker = outside / "UNPICKLED"
        payload = unpickling_marker(marker)
        server.body("/pkgs/punkt_tab.pickle", payload)
        index_url = serve_chain(
            server,
            tab=payload,
            tab_extra={"url": server.url("/pkgs/punkt_tab.pickle"), "unzip": "0"},
        )
        result, output = run_download(index_url, dl, "punkt")
        assert result is True, output
        assert (dl / "tokenizers" / "punkt_tab.pickle").read_bytes() == payload
        with pytest.raises(LookupError):
            nltk.data.load("tokenizers/punkt_tab.pickle", cache=False)
        _get_punkt_tokenizer.cache_clear()
        assert punkt_model_available("english") is False
        assert not marker.exists()

    def test_a_successor_kept_zipped_still_serves_the_tokenizer(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server, tab_extra={"unzip": "0"})
        params = inspect.signature(downloader.Downloader.download).parameters
        keep = {"extract": False} if "extract" in params else {}
        assert run_download(index_url, dl, "punkt", **keep)[0] is True
        assert not (dl / "tokenizers" / "punkt_tab").exists()
        _get_punkt_tokenizer.cache_clear()
        assert punkt_model_available("english") is True
        assert sent_tokenize(SAMPLE, language="english") == SERVED_SPLIT
        _get_punkt_tokenizer.cache_clear()

    def test_punkt_listed_as_a_collection_holding_itself_installs_once(self, box):
        root, outside, dl, server = box
        blob = punkt_tab_zip()
        server.body("/pkgs/punkt_tab.zip", blob)
        attrs = package_attrs(
            "punkt_tab", blob, server.url("/pkgs/punkt_tab.zip"), subdir="tokenizers"
        )
        server.body(
            "/index.xml", make_index([attrs], [("punkt", ["punkt_tab", "punkt"])])
        )
        result, output = run_download(server.url("/index.xml"), dl, "punkt")
        assert result is True, output
        assert hits(server, "punkt_tab") == 1
        assert served_split() == SERVED_SPLIT

    def test_a_successor_nested_in_its_own_directory_is_not_a_model(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server, tab_extra={"subdir": "tokenizers/punkt_tab"})
        assert run_download(index_url, dl, "punkt")[0] is True
        nested = dl / "tokenizers" / "punkt_tab" / "punkt_tab" / "english"
        assert (nested / "abbrev_types.txt").is_file()
        _get_punkt_tokenizer.cache_clear()
        assert punkt_model_available("english") is False
        with pytest.raises(LookupError):
            sent_tokenize(SAMPLE, language="english")
        assert_contained(root, outside, dl)


# ===========================================================================
# 10. A punkt_tab whose file names are right and whose contents are hostile
# ===========================================================================
def _tab_with(file_name, content):
    target = "punkt_tab/english/" + file_name
    return make_zip([(n, content if n == target else d) for n, d in TAB_BASE])


TERMINAL_LINES = (
    ESC
    + "]52;c;aGk="
    + BEL
    + "\n"
    + CSI8
    + "2J\n"
    + RLO
    + "txt.exe\n"
    + NEL
    + "\nzzq\n"
).encode("utf-8")
#: (file, content, outcome): "loads" splits SAMPLE, "refused" is a ValueError
#: (UnicodeDecodeError included) from the tokenizer and the availability check alike.
TAB_CONTENT_ATTACKS = {
    "abbrev-pickle-opcodes": ("abbrev_types.txt", "pickle", "loads"),
    "collocations-pickle-opcodes": ("collocations.tab", "pickle", "loads"),
    "starters-pickle-opcodes": ("sent_starters.txt", "pickle", "loads"),
    "ortho-pickle-opcodes": ("ortho_context.tab", "pickle", "refused"),
    "abbrev-terminal-controls": ("abbrev_types.txt", TERMINAL_LINES, "loads"),
    "starters-terminal-controls": ("sent_starters.txt", TERMINAL_LINES, "loads"),
    "ortho-not-an-integer": ("ortho_context.tab", b"zzq\tx\n", "refused"),
    "ortho-integer-past-the-digit-limit": (
        "ortho_context.tab",
        b"zzq\t" + b"9" * 5000 + b"\n",
        "refused",
    ),
    "ortho-three-columns": ("ortho_context.tab", b"zzq\t1\t2\n", "refused"),
    "ortho-no-tab": ("ortho_context.tab", b"zzq\n", "refused"),
    "abbrev-invalid-utf8": ("abbrev_types.txt", b"zzq\n\xff\xfe\n", "refused"),
    "abbrev-nul-bytes": ("abbrev_types.txt", b"a\x00b\nzzq\n", "loads"),
    "abbrev-one-mebibyte-line": (
        "abbrev_types.txt",
        b"a" * (1 << 20) + b"\nzzq\n",
        "loads",
    ),
    "abbrev-many-lines": ("abbrev_types.txt", b"x\n" * 200_000 + b"zzq\n", "loads"),
    "collocations-wide-rows": ("collocations.tab", b"a\tb\tc\td\n" * 1000, "loads"),
}


@pytest.mark.parametrize("label", sorted(TAB_CONTENT_ATTACKS))
def test_hostile_model_contents_load_inert_or_are_refused(box, capsys, label):
    root, outside, dl, server = box
    marker = outside / "UNPICKLED"
    file_name, content, outcome = TAB_CONTENT_ATTACKS[label]
    if content == "pickle":
        content = unpickling_marker(marker) + b"\nzzq\n"
    index_url = serve_chain(server, tab=_tab_with(file_name, content))
    assert run_download(index_url, dl, "punkt", quiet=True)[0] is True
    capsys.readouterr()
    _get_punkt_tokenizer.cache_clear()
    with timing.budget(20, "a hostile punkt_tab model loads in bounded time"):
        if outcome == "loads":
            assert punkt_model_available("english") is True
            assert sent_tokenize(SAMPLE, language="english") == SERVED_SPLIT
        else:
            with pytest.raises(ValueError):
                punkt_model_available("english")
            with pytest.raises(ValueError):
                sent_tokenize(SAMPLE, language="english")
    _get_punkt_tokenizer.cache_clear()
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""
    assert not marker.exists()
    assert_contained(root, outside, dl)


# ===========================================================================
# 11. The downloader and the tokenizer agree on what an installed model is
# ===========================================================================
class TestInstalledMeansTheSameToBoth:
    def _available(self):
        _get_punkt_tokenizer.cache_clear()
        try:
            return punkt_model_available("english")
        finally:
            _get_punkt_tokenizer.cache_clear()

    def test_the_chain_turns_an_absent_model_into_an_installed_one(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt_tab", str(dl)) == d.NOT_INSTALLED
        assert self._available() is False
        assert run_download(index_url, dl, "punkt")[0] is True
        d.clear_status_cache()
        assert d.status("punkt_tab", str(dl)) == d.INSTALLED
        assert self._available() is True

    @pytest.mark.parametrize(
        "missing", sorted(n.split("/")[-1] for n, _ in TAB_BASE[2:])
    )
    def test_a_model_file_removed_is_stale_unavailable_and_refetched(
        self, box, missing
    ):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt")[0] is True
        (dl / "tokenizers" / "punkt_tab" / "english" / missing).unlink()
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt_tab", str(dl)) == d.STALE
        assert self._available() is False
        with pytest.raises(LookupError, match="punkt_tab"):
            sent_tokenize(SAMPLE, language="english")
        _get_punkt_tokenizer.cache_clear()
        assert run_download(index_url, dl, "punkt")[0] is True
        assert hits(server, "punkt_tab") == 2
        assert self._available() is True

    def test_a_directory_in_an_empty_files_place_is_stale_and_repaired(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt")[0] is True
        empty = dl / "tokenizers" / "punkt_tab" / "english" / "collocations.tab"
        empty.unlink()
        empty.mkdir()
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt_tab", str(dl)) == d.STALE
        _get_punkt_tokenizer.cache_clear()
        with pytest.raises(PermissionError) as refused:
            punkt_model_available("english")
        if os.name == "posix":  # Windows refuses to open a directory itself (EACCES)
            assert "Security Violation" in str(refused.value)
        assert run_download(index_url, dl, "punkt")[0] is True
        assert empty.is_file() and self._available() is True

    def test_files_resized_to_the_same_total_are_stale(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        assert run_download(index_url, dl, "punkt")[0] is True
        model = dl / "tokenizers" / "punkt_tab" / "english"
        (model / "abbrev_types.txt").write_bytes(b"zz\n")
        (model / "collocations.tab").write_bytes(b"q")
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt_tab", str(dl)) == d.STALE
        assert run_download(index_url, dl, "punkt")[0] is True
        assert served_split() == SERVED_SPLIT

    def test_an_empty_model_directory_is_neither_installed_nor_available(self, box):
        root, outside, dl, server = box
        index_url = serve_chain(server)
        (dl / "tokenizers" / "punkt_tab" / "english").mkdir(parents=True)
        d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
        assert d.status("punkt_tab", str(dl)) == d.NOT_INSTALLED
        assert self._available() is False
        assert run_download(index_url, dl, "punkt")[0] is True
        assert self._available() is True


# ===========================================================================
# 12. Real archives: every retired package brings a successor that works
# ===========================================================================
def _ambient_archive(relative):
    """The bytes of an installed real archive, from the data roots this test
    run started with, or None when it is not installed."""
    for root in _AMBIENT_ROOTS:
        candidate = os.path.join(root, relative)
        if os.path.isfile(candidate):
            with open(candidate, "rb") as handle:
                return handle.read()
    return None


_AMBIENT_ROOTS = [p for p in nltk.data.path if isinstance(p, str) and os.path.isdir(p)]
#: retired id: (its pickle-era members, its successor's archive, subdir)
RETIRED = {
    "punkt": (
        ["punkt/english.pickle", "punkt/PY3/english.pickle"],
        "punkt_tab",
        "tokenizers",
    ),
    "averaged_perceptron_tagger": (
        ["averaged_perceptron_tagger/averaged_perceptron_tagger.pickle"],
        "averaged_perceptron_tagger_eng",
        "taggers",
    ),
    "averaged_perceptron_tagger_ru": (
        ["averaged_perceptron_tagger_ru/averaged_perceptron_tagger_ru.pickle"],
        "averaged_perceptron_tagger_rus",
        "taggers",
    ),
    "maxent_ne_chunker": (
        [
            "maxent_ne_chunker/english_ace_multiclass.pickle",
            "maxent_ne_chunker/PY3/english_ace_binary.pickle",
        ],
        "maxent_ne_chunker_tab",
        "chunkers",
    ),
    "maxent_treebank_pos_tagger": (
        ["maxent_treebank_pos_tagger/PY3/english.pickle"],
        "maxent_treebank_pos_tagger_tab",
        "taggers",
    ),
}
SAMPLES = {
    "english": "Mr. Smith arrived at 5 p.m. on Jan. 3. He left early, e.g. before lunch.",
    "german": "Herr Dr. M"
    + chr(0xFC)
    + "ller kam am 3. Jan. um 5 Uhr. Er ging z. B. vor dem Essen.",
    "portuguese": "O Sr. Silva chegou "
    + chr(0xE0)
    + "s 5 horas. Ele saiu cedo, i.e. antes do almo"
    + chr(0xE7)
    + "o.",
}
#: What the real punkt_tab makes of SAMPLES (the released archive, sha256 e57f6418...).
REAL_SPLITS = {
    "english": [
        "Mr. Smith arrived at 5 p.m. on Jan. 3.",
        "He left early, e.g.",
        "before lunch.",
    ],
    "german": [
        "Herr Dr. M" + chr(0xFC) + "ller kam am 3.",
        "Jan.",
        "um 5 Uhr.",
        "Er ging z.",
        "B. vor dem Essen.",
    ],
    "portuguese": [
        "O Sr. Silva chegou " + chr(0xE0) + "s 5 horas.",
        "Ele saiu cedo, i.e.",
        "antes do almo" + chr(0xE7) + "o.",
    ],
}
_FUNCTIONAL_CHILD = r"""
import json, sys
import nltk, nltk.data
nltk.data.path[:] = sys.argv[1].split("\n")
from nltk import ne_chunk, pos_tag
from nltk.tokenize import punkt_model_available, sent_tokenize, word_tokenize
samples, pickle_names = json.loads(sys.argv[2])
out = {"available": {l: punkt_model_available(l) for l in [*samples, "klingon"]}}
out["sent"] = {l: sent_tokenize(t, language=l) for l, t in samples.items()}
out["word"] = {l: word_tokenize(t, language=l) for l, t in samples.items()}
words = word_tokenize("Mark Pedersen works at Google in London.")
out["pos"] = pos_tag(words)
out["pos_ru"] = pos_tag(["\u041c\u0430\u043c\u0430", "\u043c\u044b\u043b\u0430"], lang="rus")
out["ne"] = str(ne_chunk(pos_tag(words)))
loaded = {}
for name in pickle_names:
    model = nltk.data.load(name, cache=False)
    if hasattr(model, "tokenize"):
        loaded[name] = model.tokenize(samples["english"])
    elif hasattr(model, "tag"):
        loaded[name] = model.tag(words)
    else:
        loaded[name] = str(model.parse(pos_tag(words)))
out["pickle_era_names"] = loaded
print(json.dumps(out, sort_keys=True))
"""


def _run_functional_child(roots, pickle_names):
    """Run _FUNCTIONAL_CHILD in a fresh interpreter (no model cached from this
    one) on *roots*, and return what it reports."""
    request = json.dumps([SAMPLES, pickle_names])
    done, run = timing.run_subprocess(
        [sys.executable, "-c", _FUNCTIONAL_CHILD, "\n".join(roots), request],
        budget=120,
        capture_output=True,
        env=_pkg_env(),
    )
    assert done is not None and done.returncode == 0, done and done.stderr
    return json.loads(done.stdout.decode("utf-8").strip().splitlines()[-1])


def test_every_retired_package_brings_its_real_successor_in_a_fresh_process(box):
    root, outside, dl, server = box
    archives = {}
    for old, (members, new, subdir) in RETIRED.items():
        archives[new] = _ambient_archive(f"{subdir}/{new}.zip")
    archives["words"] = _ambient_archive("corpora/words.zip")
    missing = sorted(k for k, v in archives.items() if v is None)
    if missing:
        pytest.skip(f"the real archives are not installed here: {missing}")
    marker = outside / "UNPICKLED"
    payload = unpickling_marker(marker)
    packages, pickle_names = [], []
    for old, (members, new, subdir) in RETIRED.items():
        dirs = sorted({m.rsplit("/", 1)[0] + "/" for m in members})
        hostile = make_zip([(d, b"") for d in dirs] + [(m, payload) for m in members])
        packages.append((old, hostile, subdir))
        packages.append((new, archives[new], subdir))
        pickle_names += [f"{subdir}/{m}" for m in members]
    packages.append(("words", archives["words"], "corpora"))
    attrs = []
    for pid, blob, subdir in packages:
        server.body(f"/pkgs/{pid}.zip", blob)
        attrs.append(
            package_attrs(pid, blob, server.url(f"/pkgs/{pid}.zip"), subdir=subdir)
        )
    collection = [("popularish", [*RETIRED, "words"])]
    server.body("/index.xml", make_index(attrs, collection))
    result, output = run_download(
        server.url("/index.xml"), dl, "popularish", quiet=True
    )
    assert result is True, output
    for old, (members, new, subdir) in RETIRED.items():
        assert hits(server, new) == 1, new
    chained = _run_functional_child([str(dl)], pickle_names)
    released = _run_functional_child(_AMBIENT_ROOTS, pickle_names)
    assert chained == released
    assert chained["available"] == {
        "english": True,
        "german": True,
        "portuguese": True,
        "klingon": False,
    }
    assert chained["sent"] == REAL_SPLITS
    assert not marker.exists()
    assert_contained(root, outside, dl)


def test_the_real_punkt_tab_flips_availability_for_every_language_it_holds(box):
    root, outside, dl, server = box
    blob = _ambient_archive("tokenizers/punkt_tab.zip")
    if blob is None:
        pytest.skip("the real punkt_tab archive is not installed here")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        languages = sorted(
            {
                n.split("/")[1]
                for n in zf.namelist()
                if n.count("/") >= 2 and n.endswith(".tab")
            }
        )
    assert len(languages) >= 18 and {"english", "german", "portuguese"} <= set(
        languages
    )
    index_url = serve_chain(server, tab=blob)
    _get_punkt_tokenizer.cache_clear()
    assert not any(punkt_model_available(lang) for lang in languages)
    with pytest.raises(LookupError, match="punkt_tab"):
        sent_tokenize(SAMPLES["english"], language="english")
    assert run_download(index_url, dl, "punkt", quiet=True)[0] is True
    try:
        assert all(punkt_model_available(lang) for lang in languages)
        for lang in languages:
            assert sent_tokenize("A b. C d.", language=lang)
        for lang, text in SAMPLES.items():
            assert sent_tokenize(text, language=lang) == REAL_SPLITS[lang]
            assert word_tokenize(text, language=lang)
    finally:
        _get_punkt_tokenizer.cache_clear()


# ===========================================================================
# 13. The live index (needs the network; CI runs it)
# ===========================================================================
def test_the_live_index_installs_a_punkt_tab_the_tokenizers_use(tmp_path, monkeypatch):
    monkeypatch.setenv("NLTK_ALLOW_PROXIED_URLOPEN", "1")
    target = tmp_path / "nltk_data"
    d = downloader.Downloader(download_dir=str(target))
    with contextlib.redirect_stdout(io.StringIO()):
        assert d.download("punkt", download_dir=str(target), quiet=True) is True
    assert d.status("punkt", str(target)) == d.INSTALLED
    assert d.status("punkt_tab", str(target)) == d.INSTALLED
    monkeypatch.setattr(nltk.data, "path", [str(target)])
    _get_punkt_tokenizer.cache_clear()
    try:
        for lang, text in SAMPLES.items():
            assert punkt_model_available(lang) is True
            assert sent_tokenize(text, language=lang) == REAL_SPLITS[lang]
            assert word_tokenize(text, language=lang)
        assert punkt_model_available("klingon") is False
    finally:
        _get_punkt_tokenizer.cache_clear()


# ===========================================================================
# 14. One index per request, and #3929's extraction, through the chain
# ===========================================================================
def test_the_successor_comes_from_the_index_the_request_used(box):
    root, outside, dl, server = box
    first = serve_chain(server)
    second_punkt = punkt_zip(b"second")
    second_tab = punkt_tab_zip(("punkt_tab/second.txt", b"2"))
    server.body("/second/punkt.zip", second_punkt)
    server.body("/second/punkt_tab.zip", second_tab)
    attrs = [
        package_attrs(pid, blob, server.url(f"/second/{pid}.zip"), subdir="tokenizers")
        for pid, blob in (("punkt", second_punkt), ("punkt_tab", second_tab))
    ]
    server.body("/second.xml", make_index(attrs))
    d = downloader.Downloader(server_index_url=first, download_dir=str(dl))
    with contextlib.redirect_stdout(io.StringIO()):
        assert d.download("punkt_tab", download_dir=str(dl), quiet=True)
        # pointed at another index the way nltk.download's own object is
        d._url = server.url("/second.xml")
        other = root / "other"
        other.mkdir()
        assert d.download("punkt", download_dir=str(other), quiet=True)
    used_second = "/second/punkt.zip" in server.hits
    assert ("/second/punkt_tab.zip" in server.hits) == used_second
    if "_index_url" in vars(downloader.Downloader()):
        assert used_second  # #3929: an index fetched from another URL is refetched
    second_file = other / "tokenizers" / "punkt_tab" / "second.txt"
    assert second_file.exists() == used_second


@pytest.mark.skipif(
    "extract" not in inspect.signature(downloader.Downloader.download).parameters,
    reason="needs the extract= option of #3929",
)
def test_extracting_an_installed_zipped_request_extracts_its_successor(box):
    root, outside, dl, server = box
    index_url = serve_chain(
        server, tab_extra={"unzip": "0"}, punkt_extra={"unzip": "0"}
    )
    assert run_download(index_url, dl, "punkt", extract=False)[0] is True
    assert not (dl / "tokenizers" / "punkt_tab").exists()
    result, output = run_download(index_url, dl, "punkt", extract=True)
    assert result is True, output
    assert (dl / "tokenizers" / "punkt_tab" / "english").is_dir()
    assert (dl / "tokenizers" / "punkt").is_dir()
    assert served_split() == SERVED_SPLIT
    assert_contained(root, outside, dl)


# ===========================================================================
# 15. The collision fold itself, for every pathsec.ZipFile caller
# ===========================================================================
FOLDED_PAIRS = {
    "trailing-dot": ("d/ok.txt", "d/ok.txt."),
    "trailing-space": ("d/ok.txt", "d/ok.txt "),
    "trailing-dot-directory": ("d/x/ok.txt", "d/x./ok.txt"),
    "case": ("d/ok.txt", "d/OK.TXT"),
    "fullwidth": ("d/ok.txt", "d/" + chr(0xFF4F) + chr(0xFF4B) + ".txt"),
    "decomposed": (
        "d/" + CAFE + ".txt",
        "d/" + unicodedata.normalize("NFD", CAFE) + ".txt",
    ),
    "file-and-folded-directory": ("d/x.", "d/x/ok.txt"),
    **{
        f"windows-{label}": ("d/a_b.txt", "d/a" + char + "b.txt")
        for label, char in WINDOWS_UNWRITABLE.items()
    },
}
DISTINCT_PAIRS = {
    "different-names": ("d/a.txt", "d/b.txt"),
    "a-dot-inside": ("d/x", "d/x.y"),
    "two-underscores": ("d/a_b.txt", "d/a__b.txt"),
    "dots-only-name": ("d/...", "d/x"),
}


@pytest.mark.parametrize("label", sorted(FOLDED_PAIRS))
def test_names_one_filesystem_stores_as_one_file_are_refused(label, pathsec_sandbox):
    from nltk import pathsec

    root, outside = pathsec_sandbox
    first, second = FOLDED_PAIRS[label]
    with pytest.raises(ValueError, match="resource poisoning"):
        pathsec._reject_colliding_members([first, second])
    archive = root / "pair.zip"
    archive.write_bytes(make_zip([(first, b"ok"), (second, b"EVIL")]))
    with pathsec.ZipFile(str(archive)) as zf:
        with pytest.raises((ValueError, PermissionError)):
            zf.extractall(str(root / "out"))
    assert not any(
        kind == stat.S_IFREG for kind, _size in tree(str(root / "out")).values()
    ), tree(str(root / "out"))


@pytest.mark.parametrize("label", sorted(DISTINCT_PAIRS))
def test_names_no_filesystem_folds_together_are_kept(label, pathsec_sandbox):
    from nltk import pathsec

    first, second = DISTINCT_PAIRS[label]
    assert pathsec._reject_colliding_members([first, second]) is None


# ===========================================================================
# 16. Index names longer than a filesystem can append to
# ===========================================================================
@pytest.mark.parametrize(
    "field, value, refused",
    [
        ("id", "p" * downloader.MAX_NAME_BYTES, False),
        ("id", "p" * (downloader.MAX_NAME_BYTES + 1), True),
        ("id", chr(0xE9) * (downloader.MAX_NAME_BYTES // 2 + 1), True),
        ("subdir", "tokenizers/" + "s" * (downloader.MAX_NAME_BYTES + 1), True),
    ],
    ids=["id-at-the-bound", "id-past-it", "id-past-it-in-bytes", "subdir-past-it"],
)
def test_an_index_name_past_the_byte_bound_refuses_the_index(
    box, field, value, refused
):
    # ".zip.lock" and ".zip.tmp" are appended to a name; the bound keeps every
    # such file under the 255 bytes a component may have
    root, outside, dl, server = box
    pid = value if field == "id" else "longsub"
    blob = make_zip([(f"{pid}/", b""), (f"{pid}/words.txt", b"alpha\n")])
    server.body("/pkgs/long.zip", blob)
    attrs = package_attrs(pid, blob, server.url("/pkgs/long.zip"), subdir="corpora")
    attrs[field] = value
    server.body("/index.xml", make_index([attrs]))
    result, output = run_download(server.url("/index.xml"), dl, pid)
    if refused:
        assert result is False, output
        assert "longer than" in output and server.hits == ["/index.xml"]
        assert tree(str(dl)) == {}
    else:
        assert result is True, output
        assert (dl / "corpora" / pid / "words.txt").read_bytes() == b"alpha\n"
    assert_lines_clean(output)

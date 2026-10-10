# Natural Language Toolkit: file names handed to gzip and sqlite openers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack and benign tests for the gzip name forms and the PanLex Lite database.

Given a file NAME, ``gzip.GzipFile`` opens it with the builtin ``open()``, and
``sqlite3.connect`` opens it by name in C; neither sees ``nltk.pathsec``.
``nltk.data.gzip_open_unicode`` and the deprecated ``BufferedGzipFile`` handed
GzipFile the name, so a name outside every data root, or an in-root symlink or
hardlink to an outside file, was read or written. They now open the name
through ``nltk.pathsec.open`` and hand GzipFile the handle; the PanLex Lite
reader opens its database and sidecars through pathsec before sqlite does.

Every attack is planted inside a real throwaway data root (pathsec enforced)
and judged by what the filesystem shows afterwards; each has teeth: the stdlib
opener the code used before is run on the same planted name and reaches the
outside file. A runtime spy then drives every entry point on benign names and
proves no name reaches a stdlib opener without a pathsec frame. Benign round
trips use real .gz files and the real TADM event writer. Nothing is mocked.
"""

import builtins
import gzip
import os
import sqlite3
import sys
import traceback
import warnings

import pytest

import nltk.data
from nltk import pathsec
from nltk.classify.maxent import TadmEventMaxentFeatureEncoding, TadmMaxentClassifier
from nltk.classify.tadm import write_tadm_file
from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader
from nltk.data import BufferedGzipFile, gzip_open_unicode

CANARY = "OUTSIDE-CANARY\n"
REFUSED = (PermissionError, ValueError)
posix_only = pytest.mark.skipif(os.name != "posix", reason="POSIX link and FIFO model")


def _buffered(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return BufferedGzipFile(*args, **kwargs)


def _read_text(handle):
    with handle as fh:
        data = fh.read()
    return data.decode("utf-8") if isinstance(data, bytes) else data


#: name -> read the gzip file at a name through the NLTK entry point
READERS = {
    "gzip_open_unicode": lambda p: _read_text(gzip_open_unicode(p)),
    "gzip_open_unicode rb": lambda p: _read_text(gzip_open_unicode(p, "rb")),
    "BufferedGzipFile": lambda p: _read_text(_buffered(p)),
    "BufferedGzipFile rb": lambda p: _read_text(_buffered(p, "rb")),
}


def _write(handle, text):
    with handle as fh:
        fh.write(text if not isinstance(fh, gzip.GzipFile) else text.encode())


#: name -> write "PWNED" as gzip to a name through the NLTK entry point
WRITERS = {
    "gzip_open_unicode w": lambda p: _write(gzip_open_unicode(p, "w"), "PWNED"),
    "gzip_open_unicode a": lambda p: _write(gzip_open_unicode(p, "a"), "PWNED"),
    "BufferedGzipFile wb": lambda p: _write(_buffered(p, "wb"), "PWNED"),
    "BufferedGzipFile ab": lambda p: _write(_buffered(p, "ab"), "PWNED"),
}


def _plant_gz(path, text=CANARY):
    # newline="" writes the text byte for byte (no \r\n on Windows)
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write(text)
    return str(path)


def _gz_text(path):
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return fh.read()


def _assert_refused(func, path):
    with pytest.raises(REFUSED) as caught:
        func(path)
    assert "Security Violation" in str(caught.value), caught.value


@pytest.fixture
def planted(pathsec_sandbox):
    """A data root and, outside it, a gzip file holding the canary."""
    root, outside = pathsec_sandbox
    secret = _plant_gz(outside / "secret.gz")
    return str(root), str(outside), secret


def _symlink_or_skip(target, link):
    try:
        os.symlink(target, link)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"cannot create a symlink here: {exc}")
    return link


def _traversal_or_skip(root, target):
    """``root/../..`` spelling of *target*: a name that starts in the root."""
    try:
        return os.path.join(root, os.path.relpath(target, root))
    except ValueError as exc:  # another drive on Windows
        pytest.skip(f"no relative path from the root to the target: {exc}")


def _hardlink_or_skip(target, link):
    try:
        os.link(target, link)
    except OSError as exc:
        pytest.skip(f"cannot hardlink across these directories: {exc}")
    return link


# =========================================================================
# Reads: a name outside every root, or an in-root link, is refused
# =========================================================================
@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_of_an_outside_name_is_refused(planted, entry):
    root, outside, secret = planted
    _assert_refused(READERS[entry], secret)
    # teeth: the GzipFile name form used before reads the outside file
    assert _read_text(gzip.GzipFile(secret)) == CANARY


@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_through_a_traversal_name_is_refused(planted, entry):
    root, outside, secret = planted
    name = _traversal_or_skip(root, secret)
    assert os.pardir in name.split(os.sep)
    _assert_refused(READERS[entry], name)
    assert _read_text(gzip.GzipFile(name)) == CANARY


@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_through_an_in_root_symlink_to_outside_is_refused(planted, entry):
    root, outside, secret = planted
    link = _symlink_or_skip(secret, os.path.join(root, "link.gz"))
    _assert_refused(READERS[entry], link)
    assert _read_text(gzip.GzipFile(link)) == CANARY


@posix_only
@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_through_an_in_root_symlink_to_an_in_root_file_is_refused(planted, entry):
    root, outside, secret = planted
    inside = _plant_gz(os.path.join(root, "inside.gz"), "inside\n")
    link = _symlink_or_skip(inside, os.path.join(root, "link.gz"))
    _assert_refused(READERS[entry], link)
    assert _read_text(gzip.GzipFile(link)) == "inside\n"


@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_through_an_in_root_hardlink_to_outside_is_refused(planted, entry):
    root, outside, secret = planted
    hard = _hardlink_or_skip(secret, os.path.join(root, "hard.gz"))
    _assert_refused(READERS[entry], hard)
    assert _read_text(gzip.GzipFile(hard)) == CANARY


@posix_only
@pytest.mark.parametrize("entry", sorted(READERS))
def test_read_of_a_fifo_is_refused_without_blocking(planted, entry):
    root, outside, secret = planted
    fifo = os.path.join(root, "fifo.gz")
    os.mkfifo(fifo)
    _assert_refused(READERS[entry], fifo)


# =========================================================================
# Writes: nothing is created or changed outside the root
# =========================================================================
@pytest.mark.parametrize("entry", sorted(WRITERS))
def test_write_to_an_outside_name_is_refused(planted, entry):
    root, outside, secret = planted
    target = os.path.join(outside, "new.gz")
    _assert_refused(WRITERS[entry], target)
    assert sorted(os.listdir(outside)) == ["secret.gz"]
    # teeth: the GzipFile name form used before creates the outside file
    _write(gzip.GzipFile(target, "wb"), "PWNED")
    assert _gz_text(target) == "PWNED"


@pytest.mark.parametrize("entry", sorted(WRITERS))
def test_write_through_an_in_root_symlink_to_outside_is_refused(planted, entry):
    root, outside, secret = planted
    link = _symlink_or_skip(secret, os.path.join(root, "link.gz"))
    _assert_refused(WRITERS[entry], link)
    assert _gz_text(secret) == CANARY
    _write(gzip.GzipFile(link, "wb"), "PWNED")
    assert _gz_text(secret) == "PWNED"


@pytest.mark.parametrize("entry", sorted(WRITERS))
def test_write_through_an_in_root_hardlink_to_outside_is_refused(planted, entry):
    root, outside, secret = planted
    hard = _hardlink_or_skip(secret, os.path.join(root, "hard.gz"))
    _assert_refused(WRITERS[entry], hard)
    assert _gz_text(secret) == CANARY
    _write(gzip.GzipFile(hard, "wb"), "PWNED")
    assert _gz_text(secret) == "PWNED"


@pytest.mark.parametrize("entry", sorted(WRITERS))
def test_write_through_a_traversal_name_is_refused(planted, entry):
    root, outside, secret = planted
    name = _traversal_or_skip(root, os.path.join(outside, "new.gz"))
    _assert_refused(WRITERS[entry], name)
    assert sorted(os.listdir(outside)) == ["secret.gz"]
    _write(gzip.GzipFile(name, "wb"), "PWNED")
    assert _gz_text(os.path.join(outside, "new.gz")) == "PWNED"


@pytest.mark.parametrize("entry", sorted(READERS) + sorted(WRITERS))
def test_a_nul_or_url_name_is_refused(planted, entry):
    func = {**READERS, **WRITERS}[entry]
    root = planted[0]
    for name in (os.path.join(root, "a\x00b.gz"), "file:///etc/passwd"):
        with pytest.raises((*REFUSED, OSError)):
            func(name)


# =========================================================================
# Benign: real gzip files under a data root still round trip
# =========================================================================
def test_gzip_open_unicode_round_trips_text_under_a_root(restricted_sandbox):
    text = "Tökén ünïcödé, 中文, עברית\n" * 500
    name = os.path.join(restricted_sandbox, "text.gz")
    with gzip_open_unicode(name, "w") as fh:
        fh.write(text)
    assert _read_text(gzip_open_unicode(name)) == text
    assert _gz_text(name) == text
    with gzip_open_unicode(name, "a") as fh:
        fh.write("tail\n")
    assert _gz_text(name) == text + "tail\n"


def test_buffered_gzip_file_round_trips_the_howto_payload(restricted_sandbox):
    # the data howto's example: 10000 numbers written and read back
    name = os.path.join(restricted_sandbox, "testbuf.gz")
    ans = [str(i).encode("ascii") for i in range(10000)]
    test = _buffered(name, "wb", size=2**10)
    for chunk in ans:
        test.write(chunk)
    test.close()
    assert _read_text(_buffered(name, "rb")) == b"".join(ans).decode()
    assert gzip.decompress(open(name, "rb").read()) == b"".join(ans)


def test_a_stdlib_gzip_file_reads_identically(restricted_sandbox):
    payload = "".join(f"line {i}\n" for i in range(3000))
    name = _plant_gz(os.path.join(restricted_sandbox, "std.gz"), payload)
    assert _read_text(gzip_open_unicode(name)) == payload
    assert _read_text(_buffered(name)) == payload
    with nltk.data.GzipFileSystemPathPointer(name).open() as fh:
        assert fh.read().decode() == payload


def test_the_file_object_form_is_unchanged(restricted_sandbox):
    name = os.path.join(restricted_sandbox, "fo.gz")
    with pathsec.open(name, "wb") as raw:
        gz = _buffered(fileobj=raw, mode="wb")
        gz.write(b"abc")
        gz.close()
        assert not raw.closed
    with pathsec.open(name, "rb") as raw:
        assert _read_text(gzip_open_unicode(None, fileobj=_buffered(fileobj=raw))) == (
            "abc"
        )


@pytest.mark.parametrize("mode", ["rt", "wt", "rU"])
def test_a_text_mode_is_still_refused_by_gzip_rules(restricted_sandbox, mode):
    name = os.path.join(restricted_sandbox, "never.gz")
    with pytest.raises(ValueError, match="Invalid mode"):
        gzip_open_unicode(name, mode)
    with pytest.raises(ValueError, match="Invalid mode"):
        _buffered(name, mode)
    assert not os.path.exists(name)


def test_a_missing_name_is_still_file_not_found(restricted_sandbox):
    with pytest.raises(FileNotFoundError):
        gzip_open_unicode(os.path.join(restricted_sandbox, "absent.gz"))


@posix_only
def test_the_reader_owns_and_closes_its_handle(restricted_sandbox):
    name = _plant_gz(os.path.join(restricted_sandbox, "fd.gz"), "x\n")
    fds = lambda: len(os.listdir("/dev/fd"))  # noqa: E731
    before = fds()
    for _ in range(200):
        _read_text(gzip_open_unicode(name))
        _read_text(_buffered(name))
        with gzip_open_unicode(os.path.join(restricted_sandbox, "w.gz"), "w") as fh:
            fh.write("y")
    assert fds() <= before + 2


def test_real_tadm_event_file_round_trips_through_gzip_open_unicode():
    """TADM training writes its events with gzip_open_unicode into a staging
    directory under a data root; the file must read back exactly."""
    from nltk.corpus import names

    try:
        toks = [({"last": n[-1]}, "male") for n in names.words("male.txt")[:300]]
        toks += [({"last": n[-1]}, "female") for n in names.words("female.txt")[:300]]
    except LookupError:
        pytest.skip("the names corpus is not installed")
    encoding = TadmEventMaxentFeatureEncoding.train(toks)
    stage = nltk.data.make_staging_dir(prefix="nltk_tadm_test_", cleanup=True)
    name = os.path.join(stage, "events.gz")
    with gzip_open_unicode(name, "w") as stream:
        write_tadm_file(toks, encoding, stream)
    text = _gz_text(name)
    labels = encoding.labels()
    assert text.count("\n") == len(toks) * (1 + len(labels))
    assert text.splitlines()[0] == str(len(labels))
    assert _read_text(gzip_open_unicode(name)) == text


def test_real_tadm_training_when_the_binary_is_installed():
    from nltk.classify.tadm import config_tadm

    try:
        config_tadm()
    except LookupError:
        pytest.skip("the tadm binary is not installed")
    toks = [({"a": 1}, "x"), ({"b": 1}, "y")] * 20
    classifier = TadmMaxentClassifier.train(toks, trace=0)
    assert classifier.classify({"a": 1}) == "x"


# =========================================================================
# PanLex Lite: sqlite opens the database by name; links there are refused
# =========================================================================
def _panlex_db(path):
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE lv (lv INTEGER, uid TEXT, lc TEXT, tt TEXT);
        CREATE TABLE ex (ex INTEGER, lv INTEGER, tt TEXT);
        CREATE TABLE dnx (mn INTEGER, ex INTEGER, uq INTEGER, ap INTEGER, ui INTEGER);
        INSERT INTO lv VALUES (1, 'eng-000', 'eng', 'English'), (2, 'fra-000', 'fra', 'français');
        INSERT INTO ex VALUES (10, 1, 'dog'), (20, 2, 'chien');
        INSERT INTO dnx VALUES (100, 10, 9, 5, 7), (100, 20, 9, 5, 7);
        """
    )
    con.commit()
    con.close()
    return path


def test_panlex_reader_reads_a_database_under_its_root(restricted_sandbox):
    root = os.path.join(restricted_sandbox, "panlex_lite")
    os.mkdir(root)
    _panlex_db(os.path.join(root, "db.sqlite"))
    reader = PanLexLiteCorpusReader(root)
    assert reader.language_varieties("fra") == [("fra-000", "français")]
    assert reader.translations("eng-000", "dog", "fra-000") == [("chien", 9)]
    [meaning] = reader.meanings("eng-000", "dog")
    assert meaning.expressions() == {"eng-000": ["dog"], "fra-000": ["chien"]}


@pytest.mark.parametrize("name", ["db.sqlite", "db.sqlite-journal", "db.sqlite-wal"])
def test_panlex_hardlinked_database_or_sidecar_is_refused(pathsec_sandbox, name):
    root, outside = pathsec_sandbox
    corpus = os.path.join(str(root), "panlex_lite")
    os.mkdir(corpus)
    secret = _panlex_db(os.path.join(str(outside), "secret.sqlite"))
    if name != "db.sqlite":
        _panlex_db(os.path.join(corpus, "db.sqlite"))
    hard = _hardlink_or_skip(secret, os.path.join(corpus, name))
    with pytest.raises(REFUSED, match="Security Violation"):
        PanLexLiteCorpusReader(corpus)
    if name == "db.sqlite":
        # teeth: sqlite opens the hardlink by name and reads the outside rows
        rows = sqlite3.connect(hard).execute("SELECT uid FROM lv").fetchall()
        assert ("eng-000",) in rows


@pytest.mark.parametrize("name", ["db.sqlite", "db.sqlite-wal"])
def test_panlex_symlinked_database_or_sidecar_is_refused(pathsec_sandbox, name):
    root, outside = pathsec_sandbox
    corpus = os.path.join(str(root), "panlex_lite")
    os.mkdir(corpus)
    secret = _panlex_db(os.path.join(str(outside), "secret.sqlite"))
    if name != "db.sqlite":
        _panlex_db(os.path.join(corpus, "db.sqlite"))
    _symlink_or_skip(secret, os.path.join(corpus, name))
    with pytest.raises(REFUSED, match="Security Violation"):
        PanLexLiteCorpusReader(corpus)


# =========================================================================
# Runtime spy: no NAME reaches a stdlib opener without a pathsec frame
# =========================================================================
_NLTK_DIR = os.path.dirname(os.path.abspath(nltk.__file__))
_PATHSEC_FILE = os.path.abspath(pathsec.__file__)


@pytest.fixture
def name_spy(monkeypatch):
    """Record (sink, library caller) for every name opened outside pathsec."""
    seen = []

    def _record(sink, arg):
        if not isinstance(arg, (str, bytes, os.PathLike)):
            return
        frames = traceback.extract_stack()[:-2]
        if any(os.path.abspath(f.filename) == _PATHSEC_FILE for f in frames):
            return
        for f in reversed(frames):
            path = os.path.abspath(f.filename)
            in_lib = path.startswith(_NLTK_DIR + os.sep)
            if in_lib and os.sep + "test" + os.sep not in path[len(_NLTK_DIR) :]:
                seen.append((sink, f"{os.path.basename(path)}:{f.lineno}"))
                return

    def spy(owner, attr, sink, pick):
        orig = getattr(owner, attr)

        def wrapper(*args, **kwargs):
            _record(sink, pick(args, kwargs))
            return orig(*args, **kwargs)

        monkeypatch.setattr(owner, attr, wrapper)

    def gz_name(args, kwargs):
        fileobj = args[4] if len(args) > 4 else kwargs.get("fileobj")
        return None if fileobj is not None else (args[1] if len(args) > 1 else None)

    spy(builtins, "open", "builtins.open", lambda a, k: a[0] if a else k.get("file"))
    spy(gzip.GzipFile, "__init__", "GzipFile", gz_name)
    spy(sqlite3, "connect", "sqlite3.connect", lambda a, k: a[0] if a else None)
    return seen


def test_no_gzip_entry_point_hands_a_name_to_a_stdlib_opener(
    restricted_sandbox, name_spy
):
    name = os.path.join(restricted_sandbox, "spy.gz")
    _write(gzip_open_unicode(name, "w"), "a")
    _read_text(gzip_open_unicode(name))
    _write(_buffered(name, "wb"), "b")
    _read_text(_buffered(name))
    assert name_spy == []


def test_spy_teeth_it_sees_a_library_name_handed_to_sqlite(
    restricted_sandbox, name_spy
):
    # sqlite3.connect has no file object form: the reader checks first, then
    # passes the name, which the spy must see (so an empty record above means it).
    root = os.path.join(restricted_sandbox, "panlex_lite")
    os.mkdir(root)
    _panlex_db(os.path.join(root, "db.sqlite"))
    del name_spy[:]
    PanLexLiteCorpusReader(root)
    assert ("sqlite3.connect", "panlex_lite.py") in {
        (sink, where.split(":")[0]) for sink, where in name_spy
    }

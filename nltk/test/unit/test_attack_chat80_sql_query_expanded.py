# Natural Language Toolkit: store-path attack tests (chat80.sql_query)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Attack tests for the sqlite store opened by ``nltk.sem.chat80.sql_query``
(GHSA-xv54-447f-mj22, CWE-59 / CWE-73).

``sql_query`` takes a *resource name* that ``nltk.data.find`` resolves inside a
data root, then hands the file it found to ``sqlite3.connect``. Two things can
go wrong after the name has been bounded: the file behind the name can be a
link or special file that the by-path open follows somewhere else, and the SQL
text itself can name a file (``ATTACH``, ``VACUUM INTO``, directory pragmas).
Every attack here is staged inside a registered data root the way a real corpus
lives and driven through the real ``sql_query``; the verdict is taken from what
was actually opened, created or returned, never from the exception alone. The
benign cases at the end prove the documented usage still works.
"""

import os
import socket
import sqlite3
import stat
import threading

import pytest

import nltk.data
from nltk.sem import chat80

CANARY = "SQLQUERY_OUTSIDE_CANARY"
SECURITY = (PermissionError, ValueError)


def _store(path, canary=CANARY):
    """Write a real sqlite store holding ``canary``; return ``path``."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    connection = sqlite3.connect(path)
    try:
        connection.execute("CREATE TABLE t (v)")
        connection.execute("INSERT INTO t VALUES (?)", (canary,))
        connection.commit()
    finally:
        connection.close()
    return path


def _assert_security_refused(name, query="SELECT v FROM t"):
    """The call must raise a security-marked refusal and return no row."""
    with pytest.raises(SECURITY, match="Security Violation|Unsafe resource path"):
        chat80.sql_query(name, query)


@pytest.fixture
def staged(pathsec_sandbox):
    """A registered data root holding a benign store at ``att/good.db`` and an
    outside dir holding a canary store; yields ``(root, outside, secret)``."""
    root, outside = pathsec_sandbox
    _store(str(root / "att" / "good.db"), canary="in_root")
    secret = _store(str(outside / "secret.db"))
    return root, outside, secret


# ---------------------------------------------------------------------------
# The name itself: absolute, traversal, URL, UNC, ~, NUL, control characters
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "name",
    [
        "/etc/passwd",
        "/etc/hosts",
        "../" * 8 + "etc/passwd",
        "att/../../../../../../etc/passwd",
        "att/..",
        "..\\..\\..\\etc\\passwd",
        "att\\..\\..\\secret.db",
        "file:///etc/passwd",
        "file:/etc/passwd",
        "http://evil.example/x.db",
        "nltk:/etc/passwd",
        "//server/share/x.db",
        "\\\\server\\share\\x.db",
        "att/good.db|evil",
        "C:/Windows/win.ini",
    ],
)
def test_name_shapes_that_escape_are_refused_by_find(staged, name):
    """These never reach sqlite: nltk.data.find refuses the name shape."""
    _assert_security_refused(name)


def test_absolute_path_into_the_secret_store_is_refused(staged):
    root, outside, secret = staged
    _assert_security_refused(secret)
    # even an absolute path INTO the root is not a resource name
    _assert_security_refused(str(root / "att" / "good.db"))


@pytest.mark.parametrize(
    "name",
    [
        "att/good.db" + chr(0) + "evil",
        "att/good.db\n",
        "att/goo\rd.db",
        "\tatt/good.db",
        "att/good.db\x0b",
        "~/secret.db",
        "~root/secret.db",
        "att/~/good.db",
    ],
)
def test_nul_control_and_tilde_names_open_nothing(staged, name):
    """NUL, control characters and ``~`` are never expanded into a different
    file: the lookup fails (nothing found) or is refused, and no row comes back."""
    root, outside, secret = staged
    with pytest.raises((LookupError,) + SECURITY):
        chat80.sql_query(name, "SELECT v FROM t")
    assert not os.path.exists(os.path.expanduser("~/secret.db"))


@pytest.mark.parametrize("name", ["CON", "att/NUL", "COM1.db", "att/aux.db", "LPT1"])
def test_windows_device_names_are_not_opened(staged, name):
    """On POSIX these are ordinary missing names (LookupError); on Windows a
    device is not a regular file and the store check refuses it."""
    with pytest.raises((LookupError,) + SECURITY):
        chat80.sql_query(name, "SELECT 1")


# ---------------------------------------------------------------------------
# The file behind an in-root name: links, special files, parent-dir links
# ---------------------------------------------------------------------------
def test_symlink_at_store_to_outside_is_refused(staged):
    root, outside, secret = staged
    os.symlink(secret, str(root / "att" / "link.db"))
    _assert_security_refused("att/link.db")


def test_symlink_at_store_to_an_in_root_file_is_refused_too(staged):
    """Any symlink at the store is refused (fail closed, like pathsec.open),
    even one whose target is inside the root."""
    root, outside, secret = staged
    os.symlink(str(root / "att" / "good.db"), str(root / "att" / "alias.db"))
    _assert_security_refused("att/alias.db")


def test_symlinked_parent_directory_is_refused(staged):
    root, outside, secret = staged
    os.symlink(str(outside), str(root / "dirlink"))
    _assert_security_refused("dirlink/secret.db")


def test_hardlink_at_store_to_outside_is_refused(staged):
    root, outside, secret = staged
    planted = str(root / "att" / "hard.db")
    try:
        os.link(secret, planted)
    except OSError:
        # cross-device: alias an in-root file instead; st_nlink > 1 still refuses
        os.link(str(root / "att" / "good.db"), planted)
    _assert_security_refused("att/hard.db")


@pytest.mark.parametrize("suffix", ["-journal", "-wal", "-shm", ".db", ".bak"])
def test_symlink_at_a_sidecar_name_is_refused_and_target_untouched(staged, suffix):
    """sqlite reopens ``<store>-journal`` / ``-wal`` / ``-shm`` by path; a symlink
    planted there next to a benign store must refuse the whole open and leave the
    outside target byte-identical."""
    root, outside, secret = staged
    target = str(outside / ("side" + suffix))
    with open(target, "wb") as f:
        f.write(b"OUTSIDE SIDECAR BYTES")
    os.symlink(target, str(root / "att" / ("good.db" + suffix)))
    before = os.stat(target)
    _assert_security_refused("att/good.db")
    with open(target, "rb") as f:
        assert f.read() == b"OUTSIDE SIDECAR BYTES"
    assert os.stat(target).st_mtime_ns == before.st_mtime_ns


def test_hardlink_at_a_sidecar_name_is_refused(staged):
    root, outside, secret = staged
    aliased = str(root / "att" / "elsewhere.bin")
    with open(aliased, "wb") as f:
        f.write(b"x")
    os.link(aliased, str(root / "att" / "good.db-wal"))
    _assert_security_refused("att/good.db")


def _finishes_within(seconds, fn):
    """Run ``fn`` on a thread; True if it returned or raised within ``seconds``."""
    done = threading.Event()
    outcome = {}

    def run():
        try:
            fn()
        except BaseException as exc:  # recorded, re-raised by the caller
            outcome["exc"] = exc
        finally:
            done.set()

    threading.Thread(target=run, daemon=True).start()
    finished = done.wait(seconds)
    return finished, outcome.get("exc")


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs on this platform")
@pytest.mark.parametrize("suffix", ["", "-wal", "-journal"])
def test_fifo_at_store_or_sidecar_is_refused_without_blocking(staged, suffix):
    """A FIFO planted at the store or a sidecar would block any reader that
    opens it; the check must refuse it by inspection, promptly."""
    root, outside, secret = staged
    if suffix:
        os.mkfifo(str(root / "att" / ("good.db" + suffix)))
        name = "att/good.db"
    else:
        os.mkfifo(str(root / "att" / "pipe.db"))
        name = "att/pipe.db"
    finished, exc = _finishes_within(
        10, lambda: chat80.sql_query(name, "SELECT v FROM t")
    )
    assert finished, "sql_query blocked on the planted FIFO"
    assert isinstance(exc, SECURITY) and "Security Violation" in str(exc)


@pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="no unix sockets")
def test_unix_socket_at_store_is_refused(staged):
    root, outside, secret = staged
    path = str(root / "att" / "sock.db")
    if len(path) > 100:
        pytest.skip("socket path too long for AF_UNIX on this platform")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(path)
        assert stat.S_ISSOCK(os.lstat(path).st_mode)
        _assert_security_refused("att/sock.db")
    finally:
        sock.close()


def test_directory_at_store_name_is_refused(staged):
    root, outside, secret = staged
    with pytest.raises(SECURITY):
        chat80.sql_query("att", "SELECT 1")


# ---------------------------------------------------------------------------
# Names that are not plain strings
# ---------------------------------------------------------------------------
class _LyingName(str):
    """A str subclass whose every Python-level method hides the traversal."""

    def __new__(cls, real, shown):
        obj = str.__new__(cls, real)
        obj._shown = shown
        return obj

    def __str__(self):
        return self._shown

    def __repr__(self):
        return repr(self._shown)

    def __eq__(self, other):
        return self._shown == other

    def __hash__(self):
        return hash(self._shown)

    def __contains__(self, item):
        return item in self._shown

    def startswith(self, *args, **kwargs):
        return self._shown.startswith(*args, **kwargs)

    def replace(self, *args, **kwargs):
        return self._shown.replace(*args, **kwargs)

    def split(self, *args, **kwargs):
        return self._shown.split(*args, **kwargs)

    def lower(self):
        return self._shown.lower()


@pytest.mark.parametrize(
    "real",
    ["../" * 8 + "etc/passwd", "/etc/passwd", "att/link.db"],
)
def test_lying_str_subclass_is_judged_on_its_real_characters(staged, real):
    root, outside, secret = staged
    os.symlink(secret, str(root / "att" / "link.db"))
    _assert_security_refused(_LyingName(real, "att/good.db"))


class _ShiftingPath:
    """An os.PathLike whose __fspath__ answers differently on each call."""

    def __init__(self, answers):
        self._answers = list(answers)

    def __fspath__(self):
        return self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]


def test_path_like_with_shifting_fspath_opens_nothing(staged):
    """``sql_query`` takes a resource NAME, so a PathLike is not a str and is
    rejected before any lookup; nothing is resolved twice."""
    root, outside, secret = staged
    shifting = _ShiftingPath(["att/good.db", secret])
    with pytest.raises((TypeError,) + SECURITY):
        chat80.sql_query(shifting, "SELECT v FROM t")
    assert shifting._answers == ["att/good.db", secret], "__fspath__ was consulted"


def test_bytes_name_is_not_a_resource_name(staged):
    with pytest.raises((TypeError,) + SECURITY):
        chat80.sql_query(b"att/good.db", "SELECT v FROM t")


# ---------------------------------------------------------------------------
# The query text naming a file of its own
# ---------------------------------------------------------------------------
def test_attach_of_an_existing_outside_store_is_denied(staged):
    root, outside, secret = staged
    with pytest.raises(sqlite3.DatabaseError, match="not authorized"):
        chat80.sql_query("att/good.db", "ATTACH DATABASE '%s' AS o" % secret)


def test_attach_cannot_create_an_outside_file(staged):
    root, outside, secret = staged
    created = str(outside / "created_by_attach.db")
    with pytest.raises(sqlite3.DatabaseError):
        chat80.sql_query("att/good.db", "ATTACH DATABASE '%s' AS o" % created)
    assert not os.path.exists(created)


def test_vacuum_into_cannot_write_an_outside_file(staged):
    root, outside, secret = staged
    target = str(outside / "vacuumed.db")
    with pytest.raises(sqlite3.DatabaseError, match="authorization denied"):
        chat80.sql_query("att/good.db", "VACUUM INTO '%s'" % target)
    assert not os.path.exists(target)


def test_detach_is_denied(staged):
    with pytest.raises(sqlite3.DatabaseError):
        chat80.sql_query("att/good.db", "DETACH DATABASE main")


@pytest.mark.parametrize("pragma", ["temp_store_directory", "data_store_directory"])
def test_directory_pragmas_are_denied(staged, pragma):
    root, outside, secret = staged
    with pytest.raises(sqlite3.DatabaseError):
        chat80.sql_query("att/good.db", f"PRAGMA {pragma} = '{outside}'")


@pytest.mark.parametrize(
    "query",
    [
        "SELECT load_extension('/nonexistent/evil.so')",
        "SELECT readfile('/etc/passwd')",
        "SELECT writefile('%s', 'x')",
        "SELECT fsdir('/')",
    ],
)
def test_file_functions_are_unavailable_or_denied(staged, query):
    """load_extension is disabled by default and the fileio functions are not
    compiled into the stdlib module; none may read or write a file."""
    root, outside, secret = staged
    target = str(outside / "written_by_sql.txt")
    with pytest.raises(sqlite3.Error):
        chat80.sql_query("att/good.db", query % target if "%s" in query else query)
    assert not os.path.exists(target)


# ---------------------------------------------------------------------------
# Other pointer kinds nltk.data.find can hand back
# ---------------------------------------------------------------------------
def test_zipped_store_is_not_handed_to_sqlite(staged):
    """A store found only inside a .zip is a ZipFilePathPointer; sqlite would
    take its string form as a fresh path. It is refused with the documented
    'uncompressed' warning, and nothing is created at that path."""
    import zipfile

    root, outside, secret = staged
    os.makedirs(str(root / "corpora"))
    archive = str(root / "corpora" / "zipped.zip")
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(str(root / "att" / "good.db"), "zipped/city.db")
    with pytest.warns(UserWarning, match="uncompressed"):
        with pytest.raises(ValueError, match="uncompressed database file"):
            chat80.sql_query("corpora/zipped/city.db", "SELECT v FROM t")
    assert not os.path.exists(os.path.join(archive, "zipped", "city.db"))


def test_gzip_store_is_opened_in_root_but_is_not_a_database(staged):
    """A ``.gz`` name resolves to a GzipFileSystemPathPointer (a real in-root
    file), which sqlite rejects as not a database; no escape is involved."""
    import gzip

    root, outside, secret = staged
    with gzip.open(str(root / "att" / "packed.db.gz"), "wb") as f:
        f.write(b"not a database")
    with pytest.raises(sqlite3.DatabaseError):
        chat80.sql_query("att/packed.db.gz", "SELECT 1")


# ---------------------------------------------------------------------------
# BENIGN: the documented usage still works end to end
# ---------------------------------------------------------------------------
def test_benign_in_root_store_answers(staged):
    rows = chat80.sql_query("att/good.db", "SELECT v FROM t").fetchall()
    assert rows == [("in_root",)]


def test_benign_non_directory_pragma_and_builtin_functions_still_work(staged):
    columns = chat80.sql_query("att/good.db", "PRAGMA table_info(t)").fetchall()
    assert [c[1] for c in columns] == ["v"]
    version = chat80.sql_query("att/good.db", "SELECT sqlite_version()").fetchone()
    assert version[0] == sqlite3.sqlite_version


def test_benign_query_leaves_no_sidecar_behind(staged):
    root, outside, secret = staged
    chat80.sql_query("att/good.db", "SELECT v FROM t").fetchall()
    assert sorted(os.listdir(str(root / "att"))) == ["good.db"]


def test_benign_installed_city_database_if_present():
    try:
        nltk.data.find("corpora/city_database/city.db")
    except LookupError:
        pytest.skip("city_database corpus not installed")
    rows = chat80.sql_query(
        "corpora/city_database/city.db",
        "SELECT Country FROM city_table WHERE City = 'athens'",
    ).fetchall()
    assert rows == [("greece",)]

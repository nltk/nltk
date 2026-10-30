"""The file operations modules used to roll themselves now route through pathsec.

Two pathsec additions are tested on their own (``remove_tree`` with the
descriptor-based fast path and ``ignore_errors``, and ``ensure_private_dir``),
then each routed site is exercised: the downloader's privacy predicate is
pathsec's, the transition parser stages its scratch file inside a data root,
PanLex binds its sqlite open to the checked inode, and the tool wrappers
remove their scratch files by name through pathsec.
"""

import os
import sqlite3
import stat
import sys

import pytest

from nltk import pathsec

POSIX = os.name == "posix"


# =========================================================================== #
# pathsec.remove_tree                                                          #
# =========================================================================== #


def _tree(root):
    """A small tree with a file at every level."""
    (root / "a" / "b").mkdir(parents=True)
    (root / "top.txt").write_text("top")
    (root / "a" / "mid.txt").write_text("mid")
    (root / "a" / "b" / "leaf.txt").write_text("leaf")
    return root


def test_remove_tree_removes_a_tree_inside_the_root(pathsec_sandbox):
    root, outside = pathsec_sandbox
    target = _tree(root / "tree")
    pathsec.remove_tree(str(target), context="test")
    assert not target.exists()


def test_remove_tree_refuses_a_tree_outside_the_root(pathsec_sandbox):
    root, outside = pathsec_sandbox
    target = _tree(outside / "tree")
    with pytest.raises(PermissionError, match="Security Violation"):
        pathsec.remove_tree(str(target), context="test")
    assert (target / "a" / "b" / "leaf.txt").exists()


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_remove_tree_never_follows_a_link_inside_the_tree(pathsec_sandbox):
    """A link planted inside the tree, pointing outside, is removed as a link;
    the target it points at keeps every file."""
    root, outside = pathsec_sandbox
    victim = _tree(outside / "victim")
    target = _tree(root / "tree")
    os.symlink(str(victim), str(target / "a" / "escape"))
    pathsec.remove_tree(str(target), context="test")
    assert not target.exists()
    assert (victim / "a" / "b" / "leaf.txt").read_text() == "leaf"


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_remove_tree_refuses_a_link_standing_as_the_tree(pathsec_sandbox):
    """The root itself being a link is refused outright, whatever
    ``ignore_errors`` says: the security refusals are never swallowed."""
    root, outside = pathsec_sandbox
    victim = _tree(outside / "victim")
    link = root / "tree"
    os.symlink(str(victim), str(link))
    for ignore in (False, True):
        with pytest.raises(PermissionError, match="Security Violation"):
            pathsec.remove_tree(str(link), context="test", ignore_errors=ignore)
    assert os.path.islink(link) and (victim / "top.txt").exists()
    # a link to a directory INSIDE the root passes containment and is refused
    # by the not-a-link check itself
    inside = _tree(root / "inside")
    link2 = root / "tree2"
    os.symlink(str(inside), str(link2))
    for ignore in (False, True):
        with pytest.raises(PermissionError, match="not a directory to remove"):
            pathsec.remove_tree(str(link2), context="test", ignore_errors=ignore)
    assert os.path.islink(link2) and (inside / "top.txt").exists()


def test_remove_tree_refuses_a_plain_file(pathsec_sandbox):
    root, outside = pathsec_sandbox
    target = root / "file.txt"
    target.write_text("x")
    with pytest.raises(PermissionError, match="not a directory to remove"):
        pathsec.remove_tree(str(target), context="test")
    assert target.exists()


@pytest.mark.skipif(
    not POSIX or os.geteuid() == 0, reason="a mode bit stops nothing for root"
)
def test_remove_tree_ignore_errors_swallows_only_the_removal_failure(pathsec_sandbox):
    """A directory whose entries cannot be unlinked (no write bit on it) makes
    the plain call raise and the ignore_errors call return; what could not be
    removed is still there either way, nothing else is touched."""
    root, outside = pathsec_sandbox
    target = _tree(root / "tree")
    locked = target / "a" / "b"
    os.chmod(locked, 0o500)
    try:
        with pytest.raises(OSError):
            pathsec.remove_tree(str(target), context="test")
        assert (locked / "leaf.txt").exists()
        pathsec.remove_tree(str(target), context="test", ignore_errors=True)
        assert (locked / "leaf.txt").exists()
    finally:
        os.chmod(locked, 0o700)
    pathsec.remove_tree(str(target), context="test")
    assert not target.exists()


# =========================================================================== #
# pathsec.ensure_private_dir                                                   #
# =========================================================================== #


def test_ensure_private_dir_creates_a_missing_dir_privately(pathsec_sandbox):
    root, outside = pathsec_sandbox
    target = root / "out"
    old_umask = os.umask(0o000)
    try:
        made = pathsec.ensure_private_dir(str(target), context="test")
    finally:
        os.umask(old_umask)
    assert os.path.isdir(made) and os.path.samefile(made, target)
    if POSIX:
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o700


def test_ensure_private_dir_accepts_an_existing_private_dir(pathsec_sandbox):
    root, outside = pathsec_sandbox
    target = root / "out"
    target.mkdir(mode=0o700)
    (target / "keep.txt").write_text("kept")
    pathsec.ensure_private_dir(str(target), context="test")
    assert (target / "keep.txt").read_text() == "kept"


def test_ensure_private_dir_refuses_a_dir_outside_the_root(pathsec_sandbox):
    root, outside = pathsec_sandbox
    with pytest.raises(PermissionError, match="Security Violation"):
        pathsec.ensure_private_dir(str(outside / "out"), context="test")
    assert not (outside / "out").exists()


@pytest.mark.skipif(not POSIX or os.geteuid() == 0, reason="root owns every mode")
@pytest.mark.parametrize("mode", [0o777, 0o775, 0o757])
def test_ensure_private_dir_refuses_a_dir_another_account_can_write(
    pathsec_sandbox, mode
):
    root, outside = pathsec_sandbox
    target = root / "shared"
    target.mkdir()
    os.chmod(target, mode)
    try:
        with pytest.raises(PermissionError, match="writable by another account"):
            pathsec.ensure_private_dir(str(target), context="test")
    finally:
        os.chmod(target, 0o700)


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_ensure_private_dir_refuses_a_link_to_outside(pathsec_sandbox):
    root, outside = pathsec_sandbox
    (outside / "real").mkdir()
    link = root / "out"
    os.symlink(str(outside / "real"), str(link))
    with pytest.raises(PermissionError, match="Security Violation"):
        pathsec.ensure_private_dir(str(link), context="test")


# =========================================================================== #
# the routed sites                                                             #
# =========================================================================== #


@pytest.mark.skipif(not POSIX, reason="the predicate is POSIX only")
def test_downloader_not_ours_is_pathsec_private_stat():
    """The downloader's install-tree predicate is pathsec's privacy predicate,
    not a second copy: for every owner and mode the two must agree."""
    from nltk.downloader import _not_ours

    me = os.geteuid()
    for uid in (me, 0, me + 1):
        for mode in (0o600, 0o644, 0o664, 0o666, 0o700, 0o755, 0o775, 0o777):
            st = os.stat_result((stat.S_IFREG | mode, 1, 1, 1, uid, 0, 0, 0, 0, 0))
            assert _not_ours(st) == (not pathsec._private_stat(st)), (uid, oct(mode))


def test_downloader_cleanup_goes_through_pathsec(pathsec_sandbox, monkeypatch):
    """``_safe_rmtree`` and ``_safe_remove`` call pathsec.remove_tree and
    pathsec.unlink: the module holds no removal of its own."""
    import inspect

    from nltk import downloader

    src = "\n".join(
        line
        for line in inspect.getsource(
            downloader.Downloader._download_package
        ).splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "pathsec.remove_tree(" in src and "pathsec.unlink(" in src
    assert "shutil.rmtree(" not in src and "os.remove(" not in src
    assert "pathsec.replace(" in src and "os.replace(" not in src


def test_transition_parser_stages_its_scratch_file_inside_a_data_root(
    pathsec_sandbox, monkeypatch
):
    """The training scratch file lands in a private staging dir under the
    allowed root, never in the shared system temp dir, and is gone after."""
    pytest.importorskip("sklearn")
    pytest.importorskip("scipy")
    import tempfile

    import nltk.data
    from nltk.parse import transitionparser
    from nltk.parse.dependencygraph import DependencyGraph

    root, outside = pathsec_sandbox
    staged = []
    real = nltk.data.make_staging_dir

    def spy(*args, **kwargs):
        path = real(*args, **kwargs)
        staged.append(path)
        return path

    monkeypatch.setattr(transitionparser, "make_staging_dir", spy)
    scratch_before = {
        name
        for name in os.listdir(tempfile.gettempdir())
        if name.startswith("transition_parse.train")
    }
    gold = DependencyGraph("the\tDT\t2\tdet\ndog\tNN\t3\tnsubj\nbarks\tVBZ\t0\troot\n")
    parser = transitionparser.TransitionParser("arc-standard")
    model = str(root / "model.pickle")
    parser.train([gold] * 4, model, verbose=False)
    assert os.path.exists(model)
    assert len(staged) == 1, staged
    assert os.path.realpath(staged[0]).startswith(os.path.realpath(str(root)))
    assert not os.path.exists(staged[0]), "the staging dir is removed after"
    scratch_after = {
        name
        for name in os.listdir(tempfile.gettempdir())
        if name.startswith("transition_parse.train")
    }
    assert scratch_after == scratch_before, "nothing landed in the shared temp dir"


def _panlex_db(path):
    connection = sqlite3.connect(str(path))
    connection.execute("CREATE TABLE lv (uid text, lv int)")
    connection.execute("INSERT INTO lv VALUES ('eng-000', 187)")
    connection.commit()
    connection.close()


def test_panlex_reader_binds_sqlite_to_the_checked_inode(pathsec_sandbox, monkeypatch):
    from nltk.corpus.reader import panlex_lite

    root, outside = pathsec_sandbox
    corpus = root / "panlex"
    corpus.mkdir()
    _panlex_db(corpus / "db.sqlite")
    seen = {}
    real = pathsec.connect_sqlite_read_only

    def spy(path, names=None, context=None, *, required_root=None):
        seen.update(path=path, names=names, context=context, root=required_root)
        return real(path, names=names, context=context, required_root=required_root)

    monkeypatch.setattr(pathsec, "connect_sqlite_read_only", spy)
    reader = panlex_lite.PanLexLiteCorpusReader(str(corpus))
    assert reader._uid_lv == {"eng-000": 187}
    assert os.path.samefile(seen["path"], corpus / "db.sqlite")
    # the sidecar names are pathsec's own now, pinned by default
    assert seen["names"] is None
    assert pathsec.sqlite_names(seen["path"]) == [
        seen["path"] + suffix for suffix in ("", "-journal", "-wal", "-shm")
    ]
    assert seen["context"] == "PanLexLiteCorpusReader"
    assert os.path.samefile(seen["root"], corpus)


def test_panlex_reader_connection_is_read_only(pathsec_sandbox):
    from nltk.corpus.reader import panlex_lite

    root, outside = pathsec_sandbox
    corpus = root / "panlex"
    corpus.mkdir()
    _panlex_db(corpus / "db.sqlite")
    reader = panlex_lite.PanLexLiteCorpusReader(str(corpus))
    with pytest.raises(sqlite3.OperationalError):
        reader._c.execute("INSERT INTO lv VALUES ('xxx-000', 1)")


def test_sqlite_by_name_fallback_is_read_only_too(pathsec_sandbox, monkeypatch):
    """Where the descriptor-bound open is unavailable (Windows), the database
    is opened by name as a read-only file URI: a write must still be refused
    and a read must still work, with a space and a '#' in the path."""
    root, outside = pathsec_sandbox
    corpus = root / "pan lex#1"
    corpus.mkdir()
    db = corpus / "db.sqlite"
    _panlex_db(db)
    real_isdir = os.path.isdir
    monkeypatch.setattr(
        pathsec.os.path, "isdir", lambda p: False if p == "/dev/fd" else real_isdir(p)
    )
    connection = pathsec.connect_sqlite_read_only(str(db), context="test")
    assert connection.execute("SELECT uid, lv FROM lv").fetchall() == [("eng-000", 187)]
    with pytest.raises(sqlite3.OperationalError):
        connection.execute("INSERT INTO lv VALUES ('xxx-000', 1)")
    connection.close()


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_panlex_reader_refuses_a_linked_database(pathsec_sandbox):
    """A link standing as db.sqlite, pointing outside the corpus root, is
    refused before sqlite reopens it by name."""
    from nltk.corpus.reader import panlex_lite

    root, outside = pathsec_sandbox
    corpus = root / "panlex"
    corpus.mkdir()
    _panlex_db(outside / "victim.sqlite")
    os.symlink(str(outside / "victim.sqlite"), str(corpus / "db.sqlite"))
    with pytest.raises((PermissionError, ValueError)):
        panlex_lite.PanLexLiteCorpusReader(str(corpus))


@pytest.mark.parametrize(
    "module, function",
    [
        ("nltk.classify.maxent", "train_maxent_classifier_with_megam"),
        ("nltk.classify.maxent", "TadmMaxentClassifier.train"),
        ("nltk.classify.weka", "WekaClassifier._classify_many"),
        ("nltk.classify.weka", "WekaClassifier.train"),
        ("nltk.parse.malt", "MaltParser.parse_tagged_sents"),
        ("nltk.parse.malt", "MaltParser.train"),
        ("nltk.parse.stanford", "GenericStanfordParser._execute"),
        ("nltk.tag.stanford", "StanfordTagger.tag_sents"),
        ("nltk.tokenize.stanford", "StanfordTokenizer._execute"),
        ("nltk.tokenize.stanford_segmenter", "StanfordSegmenter.segment_sents"),
        ("nltk.sem.boxer", "Boxer._call_boxer"),
        ("nltk.tokenize.repp", "ReppTokenizer.tokenize_sents"),
        ("nltk.corpus.reader.nkjp", "XML_Tool.remove_preprocessed_file"),
    ],
)
def test_tool_wrappers_remove_scratch_through_pathsec(module, function):
    """Every tool wrapper removes its scratch file or staging dir through
    pathsec.unlink / pathsec.remove_tree; none keeps a bare removal."""
    import importlib
    import inspect

    mod = importlib.import_module(module)
    obj = mod
    for part in function.split("."):
        obj = getattr(obj, part)
    src = inspect.getsource(obj)
    assert "pathsec.unlink(" in src or "pathsec.remove_tree(" in src, function
    for bare in ("os.remove(", "os.unlink(", "shutil.rmtree(", "os.rmdir("):
        assert bare not in src, (function, bare)


# =========================================================================== #
# the helpers refuse exactly what pathsec.open refuses, and no more            #
# =========================================================================== #


def test_helpers_refuse_what_the_tool_path_guard_refuses(pathsec_sandbox):
    """The contained operations apply the same syntax guard as the tool-path
    checks: a name ending in a dot (which Windows silently strips, so it is
    checked as one name and opened as another) is refused by every one of
    them on every platform, so the guard is not relaxed for NLTK's own
    operations."""
    root, outside = pathsec_sandbox
    inside = root / "dir"
    inside.mkdir()
    (inside / "f.txt").write_text("x")
    stripped = str(root / "name.")
    for call in (
        lambda: pathsec.unlink(stripped, context="test"),
        lambda: pathsec.remove_tree(stripped, context="test"),
        lambda: pathsec.ensure_private_dir(stripped, context="test"),
        lambda: pathsec.validate_private_dir(stripped, context="test"),
        lambda: pathsec.replace(str(inside / "f.txt"), stripped, context="test"),
        lambda: pathsec.replace(stripped, str(inside / "g.txt"), context="test"),
    ):
        with pytest.raises(PermissionError, match="ends with a dot or space"):
            call()
    assert (inside / "f.txt").read_text() == "x" and not os.path.lexists(stripped)


def test_downloader_derives_its_names_from_the_canonical_download_dir(tmp_path):
    """The install lock and .tmp names are derived from the resolved download
    dir (a symlink here, an 8.3 alias such as RUNNER~1 on a Windows runner),
    so the syntax guard in pathsec.unlink accepts what the downloader made."""
    import hashlib
    import unittest.mock

    from nltk.downloader import Downloader, _canonical_dir

    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    os.symlink(str(real), str(alias))
    assert _canonical_dir(str(alias)) == os.path.realpath(str(real))
    missing = str(alias / "not" / "yet")
    assert _canonical_dir(missing) == os.path.join(
        os.path.realpath(str(real)), "not", "yet"
    )

    class DummyInfo:
        id = "dummy"
        url = "https://example.com/dummy.txt"
        size = 1
        filename = os.path.join("corpora", "dummy.txt")
        subdir = "corpora"
        unzip = False
        sha256_checksum = hashlib.sha256(b"x").hexdigest()
        checksum = hashlib.md5(b"x").hexdigest()

    canonical = os.path.realpath(str(real))
    with unittest.mock.patch(
        "nltk.downloader.urlopen"
    ) as urlopen_mock, unittest.mock.patch(
        "nltk.downloader.pathsec_open"
    ) as pathsec_open_mock, unittest.mock.patch(
        "nltk.downloader.sha256_hexdigest", return_value=DummyInfo.sha256_checksum
    ), unittest.mock.patch(
        "nltk.downloader.md5_hexdigest", return_value=DummyInfo.checksum
    ), unittest.mock.patch(
        "nltk.downloader.os.path.getsize", return_value=1
    ), unittest.mock.patch(
        "nltk.downloader.pathsec.replace"
    ) as replace_mock, unittest.mock.patch.object(
        Downloader, "status", return_value=Downloader.NOT_INSTALLED
    ):
        infile = unittest.mock.Mock()
        infile.read.side_effect = [b"x", b""]
        urlopen_mock.return_value = infile
        outfile = unittest.mock.Mock()
        pathsec_open_mock.return_value.__enter__.return_value = outfile
        pathsec_open_mock.return_value.__exit__.return_value = False
        list(
            Downloader(download_dir=str(alias))._download_package(
                DummyInfo(), str(alias), force=True
            )
        )
    tmp_file = os.path.join(canonical, "corpora", "dummy.txt.tmp")
    final_file = os.path.join(canonical, "corpora", "dummy.txt")
    pathsec_open_mock.assert_called_once_with(
        tmp_file, "wb", context="Downloader._download_package", required_root=canonical
    )
    replace_mock.assert_called_once_with(
        tmp_file, final_file, context="Downloader._download_package"
    )
    assert not os.path.lexists(os.path.join(canonical, "corpora", "dummy.txt.lock"))


def test_downloader_reports_a_stale_lock_it_cannot_remove(tmp_path, monkeypatch):
    """A lock older than the zombie limit that pathsec.unlink refuses to
    remove is reported once and the download returns; it was retried forever
    with no sleep (the Windows cells hung for hours on a RUNNER~1 temp path)."""
    import threading
    import time

    from nltk import downloader as dl

    download_dir = str(tmp_path / "download")
    os.makedirs(os.path.join(download_dir, "corpora"))
    lock = os.path.join(download_dir, "corpora", "dummy.txt.lock")
    with open(lock, "w") as handle:
        handle.write("")
    stale = time.time() - 10 * 60
    os.utime(lock, (stale, stale))

    def refuse(path, context="x"):
        raise PermissionError("Security Violation [test]: refused")

    monkeypatch.setattr(pathsec, "unlink", refuse)

    class DummyInfo:
        id = "dummy"
        url = "https://example.com/dummy.txt"
        size = 1
        filename = os.path.join("corpora", "dummy.txt")
        subdir = "corpora"
        unzip = False

    messages = []

    def run():
        messages.extend(
            dl.Downloader(download_dir=download_dir)._download_package(
                DummyInfo(), download_dir, force=True
            )
        )

    worker = threading.Thread(target=run, daemon=True)
    worker.start()
    worker.join(timeout=20)
    assert not worker.is_alive(), "the download spun on the stale lock"
    assert any(
        isinstance(m, dl.ErrorMessage) and "stale install lock" in m.message
        for m in messages
    ), messages
    assert os.path.exists(lock), "the lock was not removable, so it is still there"

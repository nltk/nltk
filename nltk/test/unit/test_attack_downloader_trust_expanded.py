# Natural Language Toolkit: the trust decision of #3928, attacked
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The trust decision of #3928 (another account's install is served through
its extracted files while the archive stays private), attacked with real
files, real archives, the real extractor and a real local HTTP server. No
guard is replaced; the attacker's step is done to the disk as another
account would do it, with the one thing this account cannot forge, another
owner, stood in by the mode bits the same checks read.

What is trusted, and on what evidence (from ``nltk/data.py`` and
``nltk/downloader.py``):

* D1, a data root: ``find()`` reads from a search-path directory only when
  ``pathsec.is_private_dir`` holds for it: ``os.stat`` (links followed)
  reports a directory owned by this account or root with no group or world
  write bit; a sticky world-writable directory is refused too. POSIX, under
  enforcement.
* D2, the way down: every directory from the root to the one holding the
  resource passes the same test, and so does a resource that is itself a
  directory, the corpus root the readers open files under (section 1).
* D3, the resource: a file or an archive is read only when this account or
  root owns it and no group or world write bit is set, judged by ``find()``
  by name and again on the opened descriptor at every read through a
  pointer (section 1), so a swap after the check changes nothing.
* D4, the read: ``pathsec.open`` opens with ``O_NOFOLLOW``, refuses a
  multiply-linked file, a device, a FIFO, a socket or a directory, and
  re-validates the opened descriptor's real path against the allowed roots.
* D5, archive versus tree: the extracted files are found before the archive
  beside them; an archive this account cannot read is reported as found but
  unreadable, with extraction as the remedy, never as absent.
* D6, the installed verdict: the archive's size and checksum when readable;
  when it is another account's (0600), the extracted directory alone, by
  ``lstat``: the directory itself (section 2) and every entry a real
  directory or regular file, no link, junction, special entry or second
  name, each owned by this account or root with no group or world write
  bit, the regular sizes summing to the index's ``unzipped_size``. Anything
  else is STALE: the next download removes the entry (never following a
  link) and extracts afresh.
* D7, the name: an index id and subdir are relative, without separators,
  parent references, control, bidi or invisible characters, or components
  over 200 bytes; a member name is contained in the owning package and free
  of parent references, NUL, control, bidi and invisible characters;
  NFC/NFD, case and file/directory collisions are refused; a symlink entry
  is written as a plain file.
* D8, extraction policy: a download made as root or outside this account's
  home is extracted without being asked; the archive stays 0600.
* D9, content: what passes the above is bytes until a loader accepts it:
  picklesec, jsontags, xmlsec, the decompression ceilings and ``nltk.redos``
  judge the content, whatever its name.

Found while writing this harness, and fixed on this branch: a corpus root
another account could write to was served to the readers because only the
directories on the way to it were judged (D2); a file another account could
write to was read through a directory pointer because the verdict ``find()``
gives a file was not carried to the read (D3); a link or a writable directory
standing as the package directory read as installed because only the entries
under it were judged (D6); a member name with a line break or an escape
sequence was written to disk (D7); an id over the filesystem's name length
escaped ``download()`` as a raw ``OSError`` (D7); the documented remedy,
re-running the download with extraction over an existing archive-only
install, was answered with up-to-date and extracted nothing (D5, D8); a
plain file standing where the package directory belongs was left in place
by the stale cleanup, so the repair failed on ENOTDIR every time (D6).
"""

import gzip
import os
import pickle
import shutil
import stat
import unicodedata
import zipfile

import pytest

import nltk
import nltk.data
from nltk import downloader, pathsec
from nltk.corpus.reader import WordListCorpusReader, XMLCorpusReader
from nltk.test.unit import timing
from nltk.test.unit.test_attack_downloader_zip_expanded import (  # noqa: F401  (the fixture: a private root, an outside dir, a server)
    POSIX_NON_ROOT,
    WORDS,
    _links_under,
    _mode,
    _symlink_member,
    _umask,
    box,
    make_index,
    make_zip,
    package_attrs,
    run_download,
    serve_packages,
    tiny_package,
    tree,
)
from nltk.test.unit.test_data import BILLION_LAUGHS, _Callable

INSTALLED = downloader.Downloader.INSTALLED
STALE = downloader.Downloader.STALE
NOT_INSTALLED = downloader.Downloader.NOT_INSTALLED

#: Every attribute of the module-level Downloader that an index fetch or a
#: download changes; a test that points it at a local index restores all of
#: them, or the next test's nltk.download("stopwords") reads the test index.
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


def _snapshot(d):
    """Every state attribute, dict containers copied so a later in-place
    change (a status cached, a package list rebuilt) cannot alter it."""
    state = {}
    for name in _DOWNLOADER_STATE:
        value = getattr(d, name, _MISSING)
        state[name] = dict(value) if isinstance(value, dict) else value
    return state


def _restore(d, state):
    for name, value in state.items():
        if value is _MISSING:
            if hasattr(d, name):
                delattr(d, name)
        else:
            setattr(d, name, value)


@pytest.fixture
def default_downloader():
    """The module-level Downloader behind nltk.download, with every piece of
    its state put back at teardown (containers copied, so in-place changes
    are undone too)."""
    d = nltk.downloader._downloader
    state = _snapshot(d)
    try:
        yield d
    finally:
        _restore(d, state)


needs_posix = pytest.mark.skipif(os.name != "posix", reason="POSIX links and modes")
CYRILLIC_I = chr(0x456)
RLO = chr(0x202E)
NUL = chr(0)


def install_extracted(box, pid="tiny", members=None, **extra):
    """Serve and install *pid* with extraction; return (index, unpacked dir,
    archive). The index leaves it zipped, as wordnet is."""
    root, outside, dl, server = box
    blob = tiny_package(pid) if members is None else make_zip(members)
    index = serve_packages(server, [(pid, blob, {"unzip": "0", **extra})])
    with _umask(0o022):
        result, text = run_download(index, dl, pid, quiet=True, extract=True)
    assert result is True, text
    return index, dl / "corpora" / pid, dl / "corpora" / (pid + ".zip")


def fresh_status(index, dl, pid="tiny"):
    """A fresh Downloader each time: the verdict, not a cached one."""
    d = downloader.Downloader(server_index_url=index, download_dir=str(dl))
    return d.status(pid)


def refused_by_find(name):
    """The tree is refused and nothing else serves: a LookupError naming the
    refusal (and, for the account that cannot read the archive, that too)."""
    with pytest.warns(RuntimeWarning, match="writable by, or owned by"):
        with pytest.raises(LookupError) as exc:
            nltk.data.find(name)
    assert "Refused, writable by other accounts" in str(exc.value)
    return str(exc.value)


def archive_serves_instead(name, archive):
    """The tree is refused and the installer's own private archive beside it,
    which passed the same ownership test, serves the genuine bytes through
    the zip-name retry (what find() does for the installing account)."""
    with pytest.warns(RuntimeWarning, match="writable by, or owned by"):
        found = nltk.data.find(name)
    assert isinstance(found, nltk.data.ZipFilePathPointer), (name, found)
    assert os.path.samefile(found.zipfile.filename, archive)
    return found


# ===========================================================================
# 1. D2 and D3: a corpus root, and a file read through it
# ===========================================================================
@POSIX_NON_ROOT
class TestCorpusRootAndFilesThroughIt:
    def test_a_corpus_root_other_accounts_can_write_is_refused(self, box, monkeypatch):
        """The LazyCorpusLoader form, find('corpora/tiny'), judged only the
        directories above the corpus root; the readers then opened files under
        a directory another account could rename, replace or add to."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        corpus = nltk.data.find("corpora/tiny")
        assert isinstance(corpus, nltk.data.FileSystemPathPointer)
        assert WordListCorpusReader(corpus, ["words.txt"]).words() == [
            "alpha",
            "beta",
            "gamma",
        ]
        for mode in (0o777, 0o775, 0o1777, 0o757):
            os.chmod(unpacked, mode)
            # the directory form has no archive fallback: refused outright
            text = refused_by_find("corpora/tiny")
            assert f"- {str(unpacked)!r}" in text
            assert f"chmod go-w {str(unpacked)!r}" in text
            # the forms with a zip-name retry fall back to the installer's own
            # archive, never to the refused tree
            assert (
                archive_serves_instead("corpora/tiny/", archive)
                .join("words.txt")
                .open()
                .read()
                == WORDS
            )
            assert (
                archive_serves_instead("corpora/tiny/words.txt", archive).open().read()
                == WORDS
            )
            with pytest.warns(RuntimeWarning, match="writable by, or owned by"):
                loaded = nltk.corpus.util.LazyCorpusLoader(
                    "tiny", WordListCorpusReader, ["words.txt"]
                )
                assert loaded.words() == ["alpha", "beta", "gamma"]
                assert isinstance(loaded.root, nltk.data.ZipFilePathPointer)
            assert fresh_status(index, dl) == STALE
            # the account that cannot read the archive is served nothing
            os.chmod(archive, 0)
            try:
                for name in ("corpora/tiny", "corpora/tiny/", "corpora/tiny/words.txt"):
                    text = refused_by_find(name)
                    assert f"- {str(unpacked)!r}" in text
                assert "Found but could not read" in text
                assert fresh_status(index, dl) == STALE
            finally:
                os.chmod(archive, 0o600)
        os.chmod(unpacked, 0o755)
        assert nltk.data.find("corpora/tiny").join("words.txt").open().read() == WORDS
        assert fresh_status(index, dl) == INSTALLED
        # the next download, as the installer, puts a private directory back
        os.chmod(unpacked, 0o777)
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert _mode(unpacked) == 0o755 and fresh_status(index, dl) == INSTALLED
        assert nltk.data.find("corpora/tiny").join("words.txt").open().read() == WORDS

    def test_a_file_other_accounts_can_write_is_refused_at_the_read(
        self, box, monkeypatch
    ):
        """find('corpora/tiny/words.txt') refused such a file; the same file
        reached through the corpus root, as every reader reaches it, was read.
        The verdict is now given on the opened descriptor, so a rewrite window
        between the check and the read is closed too."""
        root, outside, dl, server = box
        packed = gzip.compress(WORDS)
        index, unpacked, archive = install_extracted(
            box,
            members=[
                ("tiny/", b""),
                ("tiny/words.txt", WORDS),
                ("tiny/words.gz", packed),
            ],
        )
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        corpus = nltk.data.find("corpora/tiny")
        assert corpus.join("words.txt").open().read() == WORDS
        assert nltk.data.find("corpora/tiny/words.gz").open().read() == WORDS
        plain, zipped = unpacked / "words.txt", unpacked / "words.gz"
        for mode in (0o666, 0o664, 0o646):
            os.chmod(plain, mode)
            os.chmod(zipped, mode)
            with pytest.raises(PermissionError, match="writable by, or owned by"):
                corpus.join("words.txt").open()
            with pytest.raises(PermissionError, match="writable by, or owned by"):
                WordListCorpusReader(corpus, ["words.txt"]).words()
            with pytest.raises(PermissionError, match="writable by, or owned by"):
                nltk.data.GzipFileSystemPathPointer(str(zipped)).open()
            # asked for by name, the writable file is refused and the
            # installer's own archive serves the genuine bytes instead
            assert (
                archive_serves_instead("corpora/tiny/words.txt", archive).open().read()
                == WORDS
            )
            assert (
                archive_serves_instead("corpora/tiny/words.gz", archive).open().read()
                == WORDS
            )
            with pytest.warns(RuntimeWarning, match="writable by, or owned by"):
                assert (
                    nltk.data.load("corpora/tiny/words.txt", format="raw", cache=False)
                    == WORDS
                )
            assert fresh_status(index, dl) == STALE
            os.chmod(archive, 0)
            try:
                refused_by_find("corpora/tiny/words.txt")
                with pytest.warns(RuntimeWarning):
                    with pytest.raises(LookupError, match="Found but could not read"):
                        nltk.data.load(
                            "corpora/tiny/words.txt", format="raw", cache=False
                        )
            finally:
                os.chmod(archive, 0o600)
        os.chmod(plain, 0o644)
        os.chmod(zipped, 0o644)
        # the window: a pointer taken while the file was private, the file
        # made writable before the read
        pointer = corpus.join("words.txt")
        os.chmod(plain, 0o666)
        with pytest.raises(PermissionError, match="writable by, or owned by"):
            pointer.open()
        os.chmod(plain, 0o644)
        assert pointer.open().read() == WORDS
        assert fresh_status(index, dl) == INSTALLED
        # a download as the installer restores a planted writable file
        plain.write_bytes(b"PLANTED!!!!!!!!!!")  # same size as WORDS
        os.chmod(plain, 0o666)
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert plain.read_bytes() == WORDS and _mode(plain) == 0o644

    def test_the_extracted_tree_of_a_private_archive_is_judged_the_same_way(
        self, box, monkeypatch
    ):
        """As the account that did not install it: the archive is closed, the
        tree serves, and a writable directory or file in the tree is refused
        and reported as not installed-and-usable rather than served."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        os.chmod(archive, 0)
        try:
            assert fresh_status(index, dl) == INSTALLED
            assert (
                nltk.data.find("corpora/tiny").join("words.txt").open().read() == WORDS
            )
            os.chmod(unpacked, 0o777)
            assert fresh_status(index, dl) == STALE
            for name in ("corpora/tiny", "corpora/tiny/", "corpora/tiny/words.txt"):
                text = refused_by_find(name)
                assert "Found but could not read" in text
            os.chmod(unpacked, 0o755)
            os.chmod(unpacked / "words.txt", 0o666)
            assert fresh_status(index, dl) == STALE
            with pytest.raises(PermissionError, match="writable by, or owned by"):
                nltk.data.find("corpora/tiny").join("words.txt").open()
            text = refused_by_find("corpora/tiny/words.txt")
            assert "Found but could not read" in text
            # this account cannot repair another account's install (its
            # directory is not writable to it) and is told so, never served
            os.chmod(dl / "corpora", 0o555)
            try:
                result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
                assert result is False, text
                assert (unpacked / "words.txt").exists() and _mode(
                    unpacked / "words.txt"
                ) == 0o666
            finally:
                os.chmod(dl / "corpora", 0o755)
            os.chmod(unpacked / "words.txt", 0o644)
            assert fresh_status(index, dl) == INSTALLED
        finally:
            os.chmod(archive, 0o600)


# ===========================================================================
# 2. D6: the package directory itself, and type confusion at its names
# ===========================================================================
@needs_posix
class TestThePackageDirectoryItself:
    def test_a_symlink_standing_as_the_package_directory_is_stale_never_followed(
        self, box, monkeypatch
    ):
        """A link to a tree holding the same bytes passed the walk (regular
        files, right sizes, this account's) because the top entry was never
        looked at. It is stale, the read through it is refused by containment,
        and the next download removes the link, not its target."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        fake = outside / "fake"
        fake.mkdir()
        (fake / "words.txt").write_bytes(WORDS)
        shutil.rmtree(unpacked)
        os.symlink(str(fake), str(unpacked))
        assert fresh_status(index, dl) == STALE
        os.chmod(archive, 0)
        try:
            assert fresh_status(index, dl) == STALE  # the other account's view too
        finally:
            os.chmod(archive, 0o600)
        with pytest.raises(PermissionError):
            nltk.data.find("corpora/tiny").join("words.txt").open()
        with pytest.raises((PermissionError, LookupError)):
            nltk.data.find("corpora/tiny/words.txt").open()
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert unpacked.is_dir() and not unpacked.is_symlink()
        assert (unpacked / "words.txt").read_bytes() == WORDS
        assert sorted(os.listdir(fake)) == ["words.txt"]
        assert (fake / "words.txt").read_bytes() == WORDS
        assert not _links_under(str(dl))
        assert fresh_status(index, dl) == INSTALLED

    def test_a_file_standing_as_the_package_directory_is_stale_and_replaced(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        shutil.rmtree(unpacked)
        unpacked.write_bytes(b"x" * len(WORDS))  # the size sum still matches
        assert fresh_status(index, dl) == STALE
        # the installer's own archive serves through the zip-name retry; the
        # file standing as the directory serves nothing
        found = nltk.data.find("corpora/tiny/words.txt")
        assert isinstance(found, nltk.data.ZipFilePathPointer)
        assert found.open().read() == WORDS
        with pytest.raises(OSError):
            nltk.data.find("corpora/tiny").join("words.txt")
        os.chmod(archive, 0)
        try:
            with pytest.raises(LookupError, match="Found but could not read"):
                nltk.data.find("corpora/tiny/words.txt")
        finally:
            os.chmod(archive, 0o600)
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert unpacked.is_dir() and (unpacked / "words.txt").read_bytes() == WORDS
        assert fresh_status(index, dl) == INSTALLED

    def test_a_directory_standing_as_a_package_file_is_stale_and_replaced(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        """A directory holding a file of the right size where the package file
        belongs keeps the size sum intact, so the status cannot see it without
        the member list (the archive is unreadable to another account); the
        read is refused at the open, and a forced download, the owner's own
        repair, puts the file back or refuses, never writes through."""
        target = unpacked / "words.txt"
        target.unlink()
        target.mkdir()
        (target / "inner.txt").write_bytes(WORDS)  # the size sum still matches
        verdict = fresh_status(index, dl)
        with pytest.raises(PermissionError):
            nltk.data.find("corpora/tiny/words.txt").open()
        with pytest.raises(PermissionError):
            nltk.data.find("corpora/tiny").join("words.txt").open()
        with _umask(0o022):
            result, text = run_download(
                index, dl, "tiny", quiet=True, extract=True, force=True
            )
        if result:
            assert target.is_file() and target.read_bytes() == WORDS
            assert fresh_status(index, dl) == INSTALLED
        else:
            assert target.is_dir() and (target / "inner.txt").read_bytes() == WORDS
        assert not _links_under(str(dl))
        assert verdict in (INSTALLED, STALE)


# ===========================================================================
# 3. D4 and D6: a link or a special file standing as a package file
# ===========================================================================
@needs_posix
class TestLinksStandingAsPackageFiles:
    @pytest.mark.parametrize(
        "kind",
        ["device", "fifo-link", "fifo", "directory", "outside-file", "hardlink"],
    )
    def test_a_link_or_special_entry_is_refused_at_every_layer_and_repaired(
        self, box, monkeypatch, kind
    ):
        """Status says stale, find and the read refuse (a FIFO must not hang
        the reader), and the next download replaces the entry with the package
        file, leaving the link's target untouched."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        target = unpacked / "words.txt"
        target.unlink()
        victim = outside / "victim.txt"
        victim.write_bytes(b"VICTIM")
        if kind == "device":
            os.symlink("/dev/zero", str(target))
        elif kind == "fifo-link":
            os.mkfifo(str(outside / "fifo"))
            os.symlink(str(outside / "fifo"), str(target))
        elif kind == "fifo":
            os.mkfifo(str(target))
        elif kind == "directory":
            os.symlink(str(outside), str(target))
        elif kind == "outside-file":
            os.symlink(str(victim), str(target))
        else:
            try:
                os.link(str(victim), str(target))
            except OSError:
                pytest.skip("cross-directory hardlinks not permitted here")
        before = sorted(os.listdir(outside))
        assert fresh_status(index, dl) == STALE

        def read_direct():
            return nltk.data.find("corpora/tiny/words.txt").open().read(4)

        def read_through_root():
            return nltk.data.find("corpora/tiny").join("words.txt").open().read(4)

        for attempt in (read_direct, read_through_root):
            finished, exc, charged = timing.finishes_within(
                10, attempt, hard_deadline=30, cpu_bound=False
            )
            assert finished, (kind, "the read hung")
            assert isinstance(exc, (PermissionError, LookupError)), (kind, exc)
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, (kind, text)
        assert target.is_file() and not target.is_symlink()
        assert target.read_bytes() == WORDS and os.stat(target).st_nlink == 1
        assert victim.read_bytes() == b"VICTIM"
        assert sorted(os.listdir(outside)) == before
        assert not _links_under(str(dl))
        assert fresh_status(index, dl) == INSTALLED
        assert nltk.data.find("corpora/tiny/words.txt").open().read() == WORDS


# ===========================================================================
# 4. D7: a resource name that is not the installed name
# ===========================================================================
SPOOFED_NAMES = {
    "nul": "corpora/tiny/words.txt" + NUL,
    "nul-inside": "corpora/ti" + NUL + "ny/words.txt",
    "lf": "corpora/tiny/words.txt\n",
    "cr": "corpora/tiny\r/words.txt",
    "trailing-dot": "corpora/tiny./words.txt",
    "trailing-space": "corpora/tiny /words.txt",
    "upper-case": "corpora/TINY/WORDS.TXT",
    "cyrillic-i": "corpora/t" + CYRILLIC_I + "ny/words.txt",
    "bidi-override": "corpora/tiny/" + RLO + "txt.sdrow",
    "overlong": "corpora/tiny/" + "a" * 300,
    "double-slash": "corpora//tiny//words.txt",
    "dot-segment": "corpora/./tiny/words.txt",
    "dotdot-inside": "corpora/x/../tiny/words.txt",
    "dotdot-leading": "../corpora/tiny/words.txt",
    "absolute": "/corpora/tiny/words.txt",
    "tilde": "~/corpora/tiny/words.txt",
    "backslash": "corpora\\tiny\\words.txt",
    "archive-form": "corpora/tiny.zip/tiny/words.txt",
    "percent-dotdot": "corpora/%2e%2e/tiny/words.txt",
}


class TestSpoofedResourceNames:
    @pytest.mark.parametrize("shape", sorted(SPOOFED_NAMES), ids=str)
    def test_find_serves_the_genuine_file_or_nothing(self, box, monkeypatch, shape):
        """Whatever the filesystem does with the spelling (a case-insensitive
        or normalisation-insensitive one folds it), the only thing find() may
        hand back is the installed file or archive, never anything else."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        genuine = unpacked / "words.txt"
        name = SPOOFED_NAMES[shape]
        try:
            found = nltk.data.find(name)
        except (LookupError, ValueError):
            return
        if isinstance(found, nltk.data.ZipFilePathPointer):
            assert os.path.samefile(found.zipfile.filename, archive), shape
            assert found.open().read() == WORDS
        else:
            assert isinstance(found, nltk.data.FileSystemPathPointer), shape
            assert os.path.samefile(found.path, genuine), (shape, found.path)
            assert found.open().read() == WORDS

    @pytest.mark.parametrize("shape", sorted(SPOOFED_NAMES), ids=str)
    def test_download_of_a_spoofed_id_installs_nothing(self, box, shape):
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        before = tree(str(dl))
        pid = (
            SPOOFED_NAMES[shape].split("/")[-2]
            if "/" in SPOOFED_NAMES[shape]
            else SPOOFED_NAMES[shape]
        )
        result, text = run_download(index, dl, pid, quiet=True, extract=True)
        if pid == "tiny":
            assert (
                result is True
            ), text  # "corpora/tiny/words.txt" forms resolve to tiny
        else:
            assert result is False, (shape, text)
        assert tree(str(dl)) == before

    def test_a_normalisation_variant_of_an_installed_name(self, box, monkeypatch):
        """A package whose name has a composed character, asked for with the
        decomposed spelling: either the filesystem folds the two to the same
        entry (the genuine file is served) or they differ (not found)."""
        root, outside, dl, server = box
        nfc = "caf" + chr(0xE9)
        nfd = unicodedata.normalize("NFD", nfc)
        blob = tiny_package(nfc)
        server.body(
            "/pkgs/cafe.zip", blob
        )  # the URL stays ASCII, as the real index's are
        attrs = package_attrs(nfc, blob, server.url("/pkgs/cafe.zip"), unzip="0")
        server.body("/index.xml", make_index([attrs]))
        index = server.url("/index.xml")
        with _umask(0o022):
            result, text = run_download(index, dl, nfc, quiet=True, extract=True)
        assert result is True, text
        unpacked = dl / "corpora" / nfc
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        assert nltk.data.find(f"corpora/{nfc}/words.txt").open().read() == WORDS
        try:
            found = nltk.data.find(f"corpora/{nfd}/words.txt")
        except LookupError:
            return
        assert os.path.samefile(found.path, unpacked / "words.txt")
        assert found.open().read() == WORDS


# ===========================================================================
# 5. D7: an index that names the package with a spoofed id or subdir
# ===========================================================================
SPOOFED_INDEX = {
    "subdir-parent": ("subdir", "../../x"),
    "subdir-absolute": ("subdir", "/tmp"),
    "subdir-parent-inside": ("subdir", "corpora/../.."),
    "subdir-backslash-parent": ("subdir", "corpora\\..\\.."),
    "subdir-overlong": ("subdir", "a" * 300),
    "id-parent": ("id", "../x"),
    "id-parent-inside": ("id", "tiny/../../x"),
    "id-trailing-dot": ("id", "tiny."),
    "id-trailing-space": ("id", "tiny "),
    "id-cyrillic-i": ("id", "t" + CYRILLIC_I + "ny"),
    "id-overlong": ("id", "a" * 300),
    "id-lf": ("id", "tiny\n"),
    "id-nul": ("id", "ti" + NUL + "ny"),
    "id-bidi": ("id", "ti" + RLO + "ny"),
}


class TestSpoofedIndexNames:
    @pytest.mark.parametrize("shape", sorted(SPOOFED_INDEX), ids=str)
    def test_the_spoofed_entry_installs_nothing_the_genuine_name_serves(
        self, box, monkeypatch, shape
    ):
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        field, value = SPOOFED_INDEX[shape]
        blob = tiny_package()
        server.body("/pkgs/spoof.zip", blob)
        attrs = package_attrs("tiny", blob, server.url("/pkgs/spoof.zip"), unzip="0")
        attrs[field] = value
        server.body("/spoof.xml", make_index([attrs]))
        pid = value if field == "id" else "tiny"
        outside_before = sorted(os.listdir(outside)) + sorted(os.listdir(root))
        try:
            result, text = run_download(
                server.url("/spoof.xml"), dl, pid, quiet=True, extract=True
            )
        except Exception as exc:  # a malformed index is refused by its parser
            result, text = False, repr(exc)
        assert result is False, (shape, text)
        # nothing extracted anywhere but, at most, an archive at the spoofed
        # name, which serves nothing; the genuine install is untouched
        assert sorted(os.listdir(outside)) + sorted(os.listdir(root)) == outside_before
        for name in os.listdir(dl / "corpora"):
            full = dl / "corpora" / name
            assert name in ("tiny", "tiny.zip") or full.is_file(), (shape, name)
        assert nltk.data.find("corpora/tiny/words.txt").open().read() == WORDS
        if field == "id" and value not in ("tiny", "TINY"):
            with pytest.raises((LookupError, ValueError)):
                nltk.data.find(f"corpora/{value}/words.txt")


# ===========================================================================
# 6. D7: member names that resolve to, or near, the expected name
# ===========================================================================
def _patch_member_name(blob, name, new):
    """Rewrite *name* to *new* (same length) in both zip headers, bypassing
    zipfile's own refusal to write such a name."""
    assert len(name.encode()) == len(new.encode())
    return blob.replace(name.encode(), new.encode())


MEMBER_SHAPES = {
    # refused outright: nothing written
    "dotdot-inside": ([("h/", b""), ("h/../h/ok.txt", b"ok")], None),
    "dot-prefix": ([("h/", b""), ("./h/ok.txt", b"ok")], None),
    "backslash-escape": ([("h/", b""), ("h\\..\\..\\esc.txt", b"ok")], None),
    "lf-in-name": ([("h/", b""), ("h/ok\n.txt", b"ok")], None),
    "cr-in-name": ([("h/", b""), ("h/ok\r.txt", b"ok")], None),
    "esc-in-name": ([("h/", b""), ("h/ok" + chr(0x1B) + ".txt", b"ok")], None),
    "bidi-in-name": ([("h/", b""), ("h/ok" + RLO + "txt.exe", b"ok")], None),
    "overlong-name": ([("h/", b""), ("h/" + "a" * 300 + ".txt", b"ok")], None),
    "nfc-nfd-pair": (
        [
            ("h/", b""),
            ("h/caf" + chr(0xE9) + ".txt", b"1"),
            ("h/" + unicodedata.normalize("NFD", "caf" + chr(0xE9)) + ".txt", b"2"),
        ],
        None,
    ),
    "case-pair": ([("h/", b""), ("h/A.txt", b"1"), ("h/a.txt", b"2")], None),
    "file-then-dir": (
        [("h/", b""), ("h/x", b"f"), ("h/x/", b""), ("h/x/y", b"y")],
        None,
    ),
    "symlink-dir-then-file": (
        [("h/", b""), _symlink_member("h/d", ".."), ("h/d/esc.txt", b"x")],
        None,
    ),
    "empty-name": ([("h/", b""), ("", b"x")], None),
    "only-the-dirname": ([("h/", b""), ("h", b"x")], None),
    # normalised inside the package: exactly these files, nothing else
    "double-slash": ([("h/", b""), ("h//ok.txt", b"ok")], {"ok.txt": b"ok"}),
    "backslash-inside": ([("h/", b""), ("h\\ok.txt", b"ok")], {"ok.txt": b"ok"}),
    "trailing-dot": ([("h/", b""), ("h/ok.txt.", b"ok")], {"ok.txt.": b"ok"}),
    "trailing-space": ([("h/", b""), ("h/ok.txt ", b"ok")], {"ok.txt ": b"ok"}),
    "unicode": (
        [("h/", b""), ("h/caf" + chr(0xE9) + ".txt", b"ok")],
        {"caf" + chr(0xE9) + ".txt": b"ok"},
    ),
}


class TestMemberNames:
    @pytest.mark.parametrize("shape", sorted(MEMBER_SHAPES), ids=str)
    def test_a_member_name_is_refused_or_lands_exactly_where_it_says(
        self, box, monkeypatch, shape
    ):
        root, outside, dl, server = box
        entries, expected = MEMBER_SHAPES[shape]
        before = sorted(os.listdir(outside)) + sorted(os.listdir(root))
        index = serve_packages(server, [("h", make_zip(entries), {"unzip": "0"})])
        result, text = run_download(index, dl, "h", quiet=True, extract=True)
        assert sorted(os.listdir(outside)) + sorted(os.listdir(root)) == before
        assert not _links_under(str(dl))
        unpacked = dl / "corpora" / "h"
        if expected is None:
            assert result is False, (shape, text)
            assert not any(
                kind == stat.S_IFREG for kind, size in tree(str(unpacked)).values()
            ), (shape, tree(str(unpacked)))
        else:
            assert result is True, (shape, text)
            assert {
                name: (unpacked / name).read_bytes() for name in os.listdir(unpacked)
            } == expected, shape
            monkeypatch.setattr(nltk.data, "path", [str(dl)])
            assert fresh_status(index, dl, "h") == INSTALLED

    def test_a_nul_in_a_member_name_cannot_hide_a_second_member(self, box):
        """zipfile cuts a name at NUL (writing and reading), so a name the
        archive spells 'h/ok.txt' with a NUL in it is seen as its prefix: one
        such member lands under the prefix it is read as, and two members that
        collapse to one name collide and are refused."""
        root, outside, dl, server = box
        blob = make_zip([("h/", b""), ("h/okAtxt", b"first")])
        blob = _patch_member_name(blob, "h/okAtxt", "h/ok" + NUL + "txt")
        index = serve_packages(server, [("h", blob, {"unzip": "0"})])
        result, text = run_download(index, dl, "h", quiet=True, extract=True)
        unpacked = dl / "corpora" / "h"
        if result:
            assert sorted(os.listdir(unpacked)) == ["ok"], os.listdir(unpacked)
        else:
            assert not tree(str(unpacked))
        shutil.rmtree(dl / "corpora", ignore_errors=True)
        blob = make_zip([("h/", b""), ("h/okAtxt", b"first"), ("h/okBtxt", b"second")])
        blob = _patch_member_name(blob, "h/okAtxt", "h/ok" + NUL + "txt")
        blob = _patch_member_name(blob, "h/okBtxt", "h/ok" + NUL + "tx2")
        index = serve_packages(server, [("h", blob, {"unzip": "0"})])
        result, text = run_download(index, dl, "h", quiet=True, extract=True)
        assert result is False, text
        assert not any(
            kind == stat.S_IFREG for kind, size in tree(str(unpacked)).values()
        )


# ===========================================================================
# 7. TOCTOU: the archive and the directory swapped around the checks
# ===========================================================================
@needs_posix
class TestSwapsAroundTheChecks:
    def test_an_archive_swapped_after_the_status_check_is_never_the_source(
        self, box, monkeypatch
    ):
        """An extracted package is served from its files; the archive beside
        them, whatever it holds now, is not read. A package left zipped is read
        from the archive, and a hostile archive swapped in is refused by the
        loaders as any hostile archive is."""
        root, outside, dl, server = box
        index, unpacked, archive = install_extracted(box)
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        assert fresh_status(index, dl) == INSTALLED
        bomb = make_zip(
            [("tiny/", b""), ("tiny/words.txt", b"\0" * (64 * 1024 * 1024))]
        )
        archive.write_bytes(bomb)
        assert nltk.data.find("corpora/tiny/words.txt").open().read() == WORDS
        assert nltk.data.find("corpora/tiny").join("words.txt").open().read() == WORDS
        assert fresh_status(index, dl) == STALE  # the checksum no longer matches
        shutil.rmtree(unpacked)
        with pytest.raises(ValueError, match="zip bomb"):
            nltk.data.find("corpora/tiny/words.txt").open().read()

    def test_the_package_directory_swapped_for_a_link_during_extraction(
        self, box, monkeypatch
    ):
        """The attacker's step runs inside the archive validation the extractor
        performs, right before members are written: the link is met as an
        entry, never followed, and nothing lands at its target."""
        root, outside, dl, server = box
        index = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        unpacked = dl / "corpora" / "tiny"
        real_validate = pathsec.validate_zip_archive
        fired = []

        def attacker_window(*args, **kw):
            outcome = real_validate(*args, **kw)
            if not fired:
                fired.append(True)
                if unpacked.is_dir():
                    shutil.rmtree(unpacked)
                os.symlink(str(outside), str(unpacked))
            return outcome

        monkeypatch.setattr(pathsec, "validate_zip_archive", attacker_window)
        before = sorted(os.listdir(outside))
        result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert fired
        assert sorted(os.listdir(outside)) == before
        assert not (outside / "words.txt").exists()
        if result:
            assert unpacked.is_dir() and not unpacked.is_symlink()
            assert (unpacked / "words.txt").read_bytes() == WORDS
        monkeypatch.setattr(pathsec, "validate_zip_archive", real_validate)
        result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert (unpacked / "words.txt").read_bytes() == WORDS
        assert not _links_under(str(dl))


# ===========================================================================
# 8. D7 and D9: an index that lies about the package
# ===========================================================================
class TestTamperedIndex:
    def test_an_unzipped_size_that_lies_never_reads_as_installed(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        blob = tiny_package()
        real = sum(
            i.file_size
            for i in zipfile.ZipFile(__import__("io").BytesIO(blob)).infolist()
        )
        index = serve_packages(
            server, [("tiny", blob, {"unzip": "0", "unzipped_size": str(real * 2)})]
        )
        result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        unpacked = dl / "corpora" / "tiny"
        assert (unpacked / "words.txt").read_bytes() == WORDS  # ours, intact
        assert fresh_status(index, dl) != INSTALLED
        index = serve_packages(
            server, [("tiny", blob, {"unzip": "0", "unzipped_size": str(real - 1)})]
        )
        shutil.rmtree(dl / "corpora")
        result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is False, text
        assert (
            fresh_status(index, dl) != INSTALLED
        )  # what landed is stale, never served as installed

    @pytest.mark.parametrize(
        "url",
        ["file:///etc/passwd", "file://localhost/etc/hosts", "ftp://127.0.0.1/x.zip"],
    )
    def test_a_package_url_off_the_web_is_refused(self, box, url):
        root, outside, dl, server = box
        attrs = package_attrs("tiny", tiny_package(), url, unzip="0")
        server.body("/index.xml", make_index([attrs]))
        result, text = run_download(server.url("/index.xml"), dl, "tiny", quiet=True)
        assert result is False, text
        assert not any(kind == stat.S_IFREG for kind, size in tree(str(dl)).values())

    def test_an_entry_pointing_the_trusted_name_at_another_package_is_refused(
        self, box, monkeypatch
    ):
        """The index says 'tiny' is at other.zip whose members live under
        'other/': the ownership rule refuses them, nothing lands under tiny/."""
        root, outside, dl, server = box
        other = make_zip([("other/", b""), ("other/words.txt", b"OTHER!")])
        server.body("/pkgs/other.zip", other)
        attrs = package_attrs("tiny", other, server.url("/pkgs/other.zip"), unzip="0")
        server.body("/index.xml", make_index([attrs]))
        result, text = run_download(
            server.url("/index.xml"), dl, "tiny", quiet=True, extract=True
        )
        assert result is False, text
        assert not (dl / "corpora" / "tiny").exists()
        assert not (dl / "corpora" / "other").exists()


# ===========================================================================
# 9. D9: hostile content at a trusted name, through both routes
# ===========================================================================
HOSTILE_MEMBERS = [
    ("h/", b""),
    ("h/evil.pickle", pickle.dumps(_Callable(), protocol=4)),
    ("h/evil.json", b'{"!h.Trojan": {"cmd": "x"}}'),
    ("h/deep.json", ("[" * 200000 + "]" * 200000).encode()),
    ("h/evil.xml", BILLION_LAUGHS.encode()),
    ("h/evil.yaml", b"!!python/object/apply:os.getcwd []\n"),
    ("h/pattern.txt", b"(a+)+$"),
    ("h/words.txt", WORDS),
]


class TestHostileContentAtATrustedName:
    @pytest.mark.parametrize("route", ["extracted", "archive", "other-accounts-tree"])
    def test_every_loader_still_refuses(self, box, monkeypatch, route):
        root, outside, dl, server = box
        index = serve_packages(
            server, [("h", make_zip(HOSTILE_MEMBERS), {"unzip": "0"})]
        )
        with _umask(0o022):
            result, text = run_download(
                index, dl, "h", quiet=True, extract=(route != "archive")
            )
        assert result is True, text
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        archive = dl / "corpora" / "h.zip"
        if route == "other-accounts-tree":
            os.chmod(archive, 0)
        try:
            found = nltk.data.find("corpora/h/words.txt")
            expected = (
                nltk.data.ZipFilePathPointer
                if route == "archive"
                else nltk.data.FileSystemPathPointer
            )
            assert isinstance(found, expected)
            assert found.open().read() == WORDS
            with pytest.raises(pickle.UnpicklingError, match="forbidden"):
                nltk.data.load("corpora/h/evil.pickle")
            with pytest.raises(ValueError, match="json tag"):
                nltk.data.load("corpora/h/evil.json")
            with pytest.raises(ValueError, match="nesting"):
                nltk.data.load("corpora/h/deep.json")
            yaml = pytest.importorskip("yaml")
            with pytest.raises(yaml.constructor.ConstructorError):
                nltk.data.load("corpora/h/evil.yaml")
            reader_root = nltk.data.find(
                "corpora/h.zip/h/" if route == "archive" else "corpora/h"
            )
            with pytest.raises(Exception) as exc:
                XMLCorpusReader(reader_root, r"evil\.xml").xml()
            assert type(exc.value).__name__ == "EntitiesForbidden"
            pattern = nltk.data.load("corpora/h/pattern.txt", format="text").strip()
            from nltk.tokenize import RegexpTokenizer

            with timing.budget(
                5, "a catastrophic pattern at a trusted name", cpu_bound=True
            ):
                try:
                    RegexpTokenizer(pattern).tokenize("a" * 40 + "!")
                except Exception:  # the refusal is as good as a bounded run
                    pass
        finally:
            if route == "other-accounts-tree":
                os.chmod(archive, 0o600)


# ===========================================================================
# 10. D8: the cycle for real, with no window dressing
# ===========================================================================
@POSIX_NON_ROOT
class TestTheCycleForReal:
    def test_a_download_outside_the_home_is_extracted_without_being_asked(
        self, box, monkeypatch
    ):
        root, outside, dl, server = box
        if not downloader._shared_install(str(dl)):
            pytest.skip("the sandbox root is under this account's home here")
        index = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True)  # extract=None
        assert result is True, text
        unpacked, archive = dl / "corpora" / "tiny", dl / "corpora" / "tiny.zip"
        assert (unpacked / "words.txt").read_bytes() == WORDS
        assert _mode(archive) == 0o600 and _mode(unpacked) == 0o755
        assert _mode(unpacked / "words.txt") == 0o644
        monkeypatch.setattr(nltk.data, "path", [str(dl)])
        assert isinstance(
            nltk.data.find("corpora/tiny"), nltk.data.FileSystemPathPointer
        )
        assert fresh_status(index, dl) == INSTALLED
        # the same install asked not to extract keeps the index's choice
        shutil.rmtree(dl / "corpora")
        result, text = run_download(index, dl, "tiny", quiet=True, extract=False)
        assert result is True and not unpacked.exists() and archive.is_file()
        assert isinstance(
            nltk.data.find("corpora/tiny/words.txt"), nltk.data.ZipFilePathPointer
        )

    def test_the_module_level_download_forwards_extract(self, box, default_downloader):
        """nltk.download is the default Downloader's method: the keyword
        reaches _download_package, which the automatic rule then skips."""
        root, outside, dl, server = box
        index = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        default_downloader._url = index
        default_downloader._download_dir = str(dl)
        assert nltk.download("tiny", download_dir=str(dl), quiet=True, extract=False)
        assert not (dl / "corpora" / "tiny").exists()
        assert nltk.download("tiny", download_dir=str(dl), quiet=True, extract=True)
        assert (dl / "corpora" / "tiny" / "words.txt").read_bytes() == WORDS
        assert set(default_downloader._packages) == {"tiny"}

    def test_the_module_level_download_leaves_no_index_behind(self, box):
        """The leak this closes: a test that pointed nltk.download at a local
        index restored _url at teardown but left the cached index, so every
        later nltk.download("<real id>") in the process answered "not found
        in index" from the test index. The module-level path is run against
        a local index with the state swapped as the fixture swaps it, put
        back as the fixture puts it back, and the default Downloader is then
        its prior state in every attribute, _url the default URL."""
        root, outside, dl, server = box
        d = nltk.downloader._downloader
        before = _snapshot(d)
        assert before["_url"] == downloader.Downloader.DEFAULT_URL
        index = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        state = _snapshot(d)
        try:
            d._url = index
            d._download_dir = str(dl)
            assert nltk.download("tiny", download_dir=str(dl), quiet=True)
            assert set(d._packages) == {"tiny"} and d._index_url == index
            assert d._index is not None
        finally:
            _restore(d, state)
        after = _snapshot(d)
        for name in _DOWNLOADER_STATE:
            assert after[name] == before[name], (name, after[name], before[name])
        assert d._url == downloader.Downloader.DEFAULT_URL
        assert "tiny" not in d._packages
        # and even without the restore, the cache follows the URL: pointed
        # back at the default URL, a cached test index is never consulted
        assert d._index is None or d._index_url == d._url

    def test_a_cached_index_follows_the_url(self, box):
        """Two indexes on the server: a Downloader whose URL is switched reads
        the package list of the URL it has now, not the cached list of the
        URL it had, however fresh that cache is."""
        root, outside, dl, server = box
        first = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        server.body(
            "/second.xml",
            make_index(
                [
                    package_attrs(
                        "other", tiny_package("other"), server.url("/pkgs/other.zip")
                    )
                ]
            ),
        )
        server.body("/pkgs/other.zip", tiny_package("other"))
        second = server.url("/second.xml")
        d = downloader.Downloader(server_index_url=first, download_dir=str(dl))
        assert {p.id for p in d.packages()} == {"tiny"}
        assert d._index_url == first
        d._url = second  # what server_index_url set later, or _update_index(url=)
        assert {p.id for p in d.packages()} == {"other"}
        assert d._index_url == second
        assert d.info("other").id == "other"
        with pytest.raises(ValueError, match="not found"):
            d.info("tiny")
        d._update_index(url=first)
        assert {p.id for p in d.packages()} == {"tiny"}
        # the same URL again within the timeout is served from the cache
        hits = server.hits.count("/index.xml")
        assert {p.id for p in d.packages()} == {"tiny"}
        assert server.hits.count("/index.xml") == hits
        # an explicit url, even the same one, always refetches: the callers'
        # way to force a refresh (the url setter, the shells) is kept
        d._update_index(url=first)
        assert server.hits.count("/index.xml") == hits + 1
        assert {p.id for p in d.packages()} == {"tiny"}
        assert server.hits.count("/index.xml") == hits + 1

    def test_the_documented_remedy_extracts_an_archive_already_installed(
        self, box, monkeypatch
    ):
        """find() tells the account that cannot read an archive to re-run the
        download with extraction. Run by the installer over its existing
        install, that must extract: the package read as installed (archive
        present, index leaves it zipped), so the request used to be answered
        with up-to-date and nothing happened. No second download is made."""
        root, outside, dl, server = box
        index = serve_packages(server, [("tiny", tiny_package(), {"unzip": "0"})])
        result, text = run_download(index, dl, "tiny", quiet=True, extract=False)
        assert result is True, text
        unpacked, archive = dl / "corpora" / "tiny", dl / "corpora" / "tiny.zip"
        assert archive.is_file() and not unpacked.exists()
        assert fresh_status(index, dl) == INSTALLED
        fetched_before = server.hits.count("/pkgs/tiny.zip")
        with _umask(0o022):
            result, text = run_download(index, dl, "tiny", quiet=True, extract=True)
        assert result is True, text
        assert (unpacked / "words.txt").read_bytes() == WORDS
        assert _mode(unpacked) == 0o755 and _mode(archive) == 0o600
        assert server.hits.count("/pkgs/tiny.zip") == fetched_before  # no re-download
        assert fresh_status(index, dl) == INSTALLED
        # done once, it is up to date: nothing is extracted twice
        result, text = run_download(index, dl, "tiny", extract=True)
        assert result is True and "up-to-date" in text
        # the shared-install rule reaches an existing archive-only install the
        # same way (an upgrade of nltk over an older root install)
        shutil.rmtree(unpacked)
        if downloader._shared_install(str(dl)):
            result, text = run_download(index, dl, "tiny", quiet=True)
            assert result is True and (unpacked / "words.txt").read_bytes() == WORDS
        # asked not to extract, an installed archive stays as it is
        shutil.rmtree(unpacked)
        result, text = run_download(index, dl, "tiny", quiet=True, extract=False)
        assert result is True and not unpacked.exists()

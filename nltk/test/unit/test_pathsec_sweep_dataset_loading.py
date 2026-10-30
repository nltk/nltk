"""
Path-traversal / arbitrary-file-read sweep over NLTK's dataset & model loaders.

This is a *behavioural* attack matrix (not a source grep): with
``pathsec.ENFORCE = True`` and ``nltk.data.path`` pinned to a single throwaway
sandbox root, every load path below is driven against a genuine file that lives
*outside* that root and must REFUSE the read (or write) with a
``PermissionError``/``ValueError`` raised by ``nltk.pathsec``.

Covered load paths (GHSA-8mgp-746c-j5xp and the corpus-reader traversal GHSAs):

* ``nltk.data.find``              ; absolute path, ``..`` traversal, %2f-encoded traversal
* ``nltk.data.load('file://...')``; absolute outside path (read)
* ``nltk.data.retrieve``          ; symlink-at-destination write escape (CWE-59)
* ``FileSystemPathPointer.open``  ; absolute outside path + in-root symlink escape
* ``GzipFileSystemPathPointer.open``; absolute outside path
* ``StreamBackedCorpusView`` (bare string fileid, ``_open`` sink)
* ``CorpusReader.open``           ; traversal, absolute, in-root symlink escape
* ``CorpusReader.__init__``       ; out-of-sandbox root
* ``WordListCorpusReader`` / ``PlaintextCorpusReader``; in-root symlink escape
* ``XMLCorpusReader.xml`` / ``XMLCorpusView``; in-root symlink + bare outside string
* ``PanLexLiteCorpusReader``      ; in-root ``db.sqlite`` symlink escape (sqlite3 sink)

Each attack is paired with a NEGATIVE CONTROL asserting ``pathsec.open`` refuses
the same outside target, so a green "attack refused" can never be an artefact of
the target happening to sit inside an allowed root.

The sandbox root is a private temp dir (which pathsec trusts); the outside
target is placed under the user's HOME; never under a temp dir (macOS private
temp is itself an allowed root) and never assuming ``/etc/passwd`` exists.
"""

import gzip
import os
import shutil
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec
from nltk.data import (
    FileSystemPathPointer,
    GzipFileSystemPathPointer,
)

REFUSE = (PermissionError, ValueError)


def _can_symlink(root):
    """True if symlinks are creatable under *root* on this platform/filesystem."""
    probe = os.path.join(root, ".__symlink_probe__")
    try:
        os.symlink(os.path.join(root, "nonexistent"), probe)
    except (OSError, NotImplementedError, AttributeError):
        return False
    finally:
        try:
            os.unlink(probe)
        except OSError:
            pass
    return True


class _Sandbox:
    """A pinned NLTK data sandbox plus a real file that lives outside it."""

    def __init__(self, base):
        self.base = Path(base)
        self.root = self.base / "root"  # the ONE allowed data root
        self.outside_dir = self.base / "outside"  # sibling -> outside every root
        self.root.mkdir(parents=True)
        self.outside_dir.mkdir(parents=True)
        self.secret = self.outside_dir / "secret.txt"
        self.secret.write_text("TOP-SECRET-OUTSIDE-ROOT\n")
        # A benign in-root file so readers with a fileids regexp find something.
        (self.root / "inside.txt").write_text("inside-ok\n")

    def symlink_in_root(self, name, target):
        """Create ``<root>/<name>`` as a symlink to *target*; return its path."""
        link = self.root / name
        if link.exists() or link.is_symlink():
            link.unlink()
        os.symlink(str(target), str(link))
        return link


@pytest.fixture
def sandbox():
    """Pin ENFORCE + a single-root data sandbox; restore all global state after.

    The sandbox lives under HOME, *not* a temp dir: pathsec trusts a private
    system temp dir as a data root, so an "outside" target placed in temp would
    silently be *inside* an allowed root and the negative control would pass
    vacuously. Under HOME, only ``~/nltk_data`` is trusted; the sibling
    ``outside`` dir here is genuinely outside every allowed root.
    """
    prev_enforce = pathsec.ENFORCE
    prev_paths = list(nltk.data.path)
    prev_roots = pathsec._ALLOWED_ROOTS_CACHE
    prev_last = pathsec._LAST_DATA_PATHS
    base = Path.home() / f".nltk_pathsec_sweep_{os.getpid()}"
    shutil.rmtree(base, ignore_errors=True)
    box = _Sandbox(base)
    try:
        pathsec.ENFORCE = True
        nltk.data.path[:] = [str(box.root)]
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None

        # NEGATIVE CONTROL: with this configuration active, pathsec.open() itself
        # must refuse the outside target. If it did not, every "attack refused"
        # assertion below would be vacuous, so guard the whole matrix on it.
        with pytest.raises(REFUSE):
            with pathsec.open(str(box.secret), "rb"):
                pass

        yield box
    finally:
        pathsec.ENFORCE = prev_enforce
        nltk.data.path[:] = prev_paths
        pathsec._ALLOWED_ROOTS_CACHE = prev_roots
        pathsec._LAST_DATA_PATHS = prev_last
        shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------------------
# nltk.data.find
# ---------------------------------------------------------------------------
def test_find_refuses_absolute_outside(sandbox):
    with pytest.raises(REFUSE):
        nltk.data.find(str(sandbox.secret))


def test_find_refuses_traversal(sandbox):
    with pytest.raises(REFUSE):
        nltk.data.find("../outside/secret.txt")


def test_find_refuses_percent_encoded_traversal(sandbox):
    # %2f-encoded traversal must be caught by the encoded-bypass guard before
    # url2pathname() decodes it back into a real ``../`` on disk.
    with pytest.raises(REFUSE):
        nltk.data.find("..%2f..%2foutside%2fsecret.txt")


# ---------------------------------------------------------------------------
# nltk.data.load (file:// protocol -> _open fallback -> _secure_open)
# ---------------------------------------------------------------------------
def test_load_file_url_refuses_outside(sandbox):
    with pytest.raises(REFUSE):
        nltk.data.load("file://" + str(sandbox.secret), format="text")


def test_load_file_triple_slash_refuses_outside(sandbox):
    with pytest.raises(REFUSE):
        nltk.data.load(
            "file:///" + str(sandbox.secret).lstrip("/"),
            format="text",
        )


# ---------------------------------------------------------------------------
# FileSystemPathPointer.open  /  GzipFileSystemPathPointer.open
# ---------------------------------------------------------------------------
def test_filesystempathpointer_refuses_absolute_outside(sandbox):
    pointer = FileSystemPathPointer(str(sandbox.secret))
    with pytest.raises(REFUSE):
        pointer.open()


def test_filesystempathpointer_refuses_symlink_escape(sandbox):
    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    link = sandbox.symlink_in_root("leak_link.txt", sandbox.secret)
    pointer = FileSystemPathPointer(str(link))  # exists() passes: link resolves
    with pytest.raises(REFUSE):
        pointer.open()


def test_gzip_pointer_refuses_absolute_outside(sandbox):
    gz_path = sandbox.outside_dir / "secret.gz"
    with gzip.open(str(gz_path), "wb") as fh:
        fh.write(b"secret-gz-bytes")
    pointer = GzipFileSystemPathPointer(str(gz_path))
    with pytest.raises(REFUSE):
        pointer.open()


# ---------------------------------------------------------------------------
# nltk.data.retrieve; write side (symlink at destination escapes the root)
# ---------------------------------------------------------------------------
def test_retrieve_refuses_symlink_destination_escape(sandbox):
    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    src = sandbox.root / "src.txt"
    src.write_text("payload-to-write\n")
    target = sandbox.outside_dir / "written_by_retrieve.txt"  # must not pre-exist
    dest = sandbox.symlink_in_root("out_link", target)
    with pytest.raises(REFUSE):
        nltk.data.retrieve("file://" + str(src), filename=str(dest), verbose=False)
    assert not target.exists(), "retrieve() wrote through a symlink out of the root!"


# ---------------------------------------------------------------------------
# CorpusReader.open  (lexical guard + scoped required_root guard)
# ---------------------------------------------------------------------------
def test_corpusreader_open_refuses_traversal(sandbox):
    from nltk.corpus.reader.api import CorpusReader

    reader = CorpusReader(str(sandbox.root), r".*\.txt")
    with pytest.raises(REFUSE):
        reader.open("../outside/secret.txt")


def test_corpusreader_open_refuses_absolute(sandbox):
    from nltk.corpus.reader.api import CorpusReader

    reader = CorpusReader(str(sandbox.root), r".*\.txt")
    with pytest.raises(REFUSE):
        reader.open(str(sandbox.secret))


def test_corpusreader_open_refuses_symlink_escape(sandbox):
    from nltk.corpus.reader.api import CorpusReader

    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    sandbox.symlink_in_root("cr_leak.txt", sandbox.secret)
    reader = CorpusReader(str(sandbox.root), r".*\.txt")
    with pytest.raises(REFUSE):
        reader.open("cr_leak.txt")


def test_corpusreader_init_refuses_outside_root(sandbox):
    from nltk.corpus.reader.wordlist import WordListCorpusReader

    with pytest.raises(REFUSE):
        WordListCorpusReader(str(sandbox.outside_dir), r".*\.txt")


# ---------------------------------------------------------------------------
# Concrete readers driven against the sandbox root (symlink escape)
# ---------------------------------------------------------------------------
def test_wordlist_reader_refuses_symlink_escape(sandbox):
    from nltk.corpus.reader.wordlist import WordListCorpusReader

    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    sandbox.symlink_in_root("wl_leak.txt", sandbox.secret)
    reader = WordListCorpusReader(str(sandbox.root), r".*\.txt")
    with pytest.raises(REFUSE):
        reader.words("wl_leak.txt")


def test_plaintext_reader_refuses_symlink_escape(sandbox):
    from nltk.corpus.reader.plaintext import PlaintextCorpusReader

    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    sandbox.symlink_in_root("pt_leak.txt", sandbox.secret)
    reader = PlaintextCorpusReader(str(sandbox.root), r".*\.txt")
    with pytest.raises(REFUSE):
        reader.raw("pt_leak.txt")


# ---------------------------------------------------------------------------
# StreamBackedCorpusView; bare string fileid straight to the _open() sink
# ---------------------------------------------------------------------------
def test_streambacked_view_refuses_bare_outside_string(sandbox):
    from nltk.corpus.reader.util import StreamBackedCorpusView, read_line_block

    view = StreamBackedCorpusView(str(sandbox.secret), read_line_block, encoding="utf8")
    with pytest.raises(REFUSE):
        list(view)


# ---------------------------------------------------------------------------
# XML loaders (guard on defusedxml, which the XML readers import)
# ---------------------------------------------------------------------------
def test_xmlcorpusreader_refuses_symlink_escape(sandbox):
    pytest.importorskip("defusedxml")
    from nltk.corpus.reader.xmldocs import XMLCorpusReader

    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    xml_secret = sandbox.outside_dir / "secret.xml"
    xml_secret.write_text('<?xml version="1.0"?><r><leak>x</leak></r>')
    sandbox.symlink_in_root("leak.xml", xml_secret)
    reader = XMLCorpusReader(str(sandbox.root), r".*\.xml")
    with pytest.raises(REFUSE):
        reader.xml("leak.xml")


def test_xmlcorpusview_refuses_bare_outside_string(sandbox):
    pytest.importorskip("defusedxml")
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    xml_secret = sandbox.outside_dir / "view_secret.xml"
    xml_secret.write_text('<?xml version="1.0"?><r><leak>x</leak></r>')
    # Constructing the view triggers _detect_encoding(), whose bare-string branch
    # opens through pathsec; so the escape is refused before any bytes are read.
    with pytest.raises(REFUSE):
        list(XMLCorpusView(str(xml_secret), ".*/leak"))


# ---------------------------------------------------------------------------
# PanLexLiteCorpusReader; the sqlite3.connect() model/dataset sink
# ---------------------------------------------------------------------------
def test_panlex_reader_refuses_symlink_db_escape(sandbox):
    from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader

    if not _can_symlink(str(sandbox.root)):
        pytest.skip("symlinks not creatable on this filesystem")
    # A real sqlite DB outside the root, reached via an in-root db.sqlite symlink.
    outside_db = sandbox.outside_dir / "real.sqlite"
    outside_db.write_bytes(b"SQLite format 3\x00")  # header is enough; never opened
    sandbox.symlink_in_root("db.sqlite", outside_db)
    with pytest.raises(REFUSE):
        PanLexLiteCorpusReader(str(sandbox.root))

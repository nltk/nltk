"""
Regression tests for the corpus-reader symlink / path-traversal sandbox bypass
(CWE-59, GHSA-p4rw and siblings GHSA-j5pw / GHSA-mvf5 / GHSA-cr8c / GHSA-934p /
GHSA-7qj2).

Several readers derived a path from trusted corpus state and reopened it with a
raw ``open()`` / ``codecs.open()``, so a symlink placed inside a trusted corpus
root could resolve outside the root and still be parsed. Each now validates the
path through ``nltk.pathsec.validate_path`` first.
"""

import os
import tempfile

import pytest

from nltk import data as nltk_data
from nltk import pathsec


@pytest.fixture
def corpus_root(monkeypatch):
    """A trusted, allowlisted corpus root plus an out-of-root secret + symlink."""
    root = tempfile.mkdtemp(prefix="corpus_root_")
    outside = tempfile.mkdtemp(prefix="outside_")
    secret = os.path.join(outside, "secret.txt")
    with open(secret, "w") as fh:
        fh.write("TOPSECRET_OUTSIDE_ROOT")
    link = os.path.join(root, "evil.txt")
    os.symlink(secret, link)
    legit = os.path.join(root, "legit.txt")
    with open(legit, "w") as fh:
        fh.write("in-root")
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk_data, "path", [root, *nltk_data.path])
    return {"root": root, "link": link, "legit": legit}


def test_required_root_blocks_symlink_escape(corpus_root):
    """The shared guard the readers use must reject an in-root symlink that
    resolves outside the root, while allowing a genuine in-root file."""
    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_path(
            corpus_root["link"], context="test", required_root=corpus_root["root"]
        )
    # legit in-root file passes
    pathsec.validate_path(
        corpus_root["legit"], context="test", required_root=corpus_root["root"]
    )


def test_xmlcorpusview_string_fileid_does_not_crash_without_root(corpus_root):
    """XMLCorpusView carries no ``_root``; the guard must fall back to the global
    sandbox rather than raise AttributeError on a bare-string fileid."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    # A legit in-root file must construct without AttributeError.
    XMLCorpusView(corpus_root["legit"], "foo")


def test_mte_file_reader_rejects_out_of_root(corpus_root):
    """MTEFileReader validates its joined path against the corpus root."""
    from nltk.corpus.reader.mte import MTEFileReader

    with pytest.raises((PermissionError, ValueError)):
        MTEFileReader(corpus_root["link"], required_root=corpus_root["root"])


@pytest.mark.skipif(
    os.name != "posix",
    reason="the st_nlink hardlink guard in pathsec.open is POSIX-only",
)
def test_pathsec_open_blocks_hardlink_escape(corpus_root):
    """A hardlink inside the root pointing at an outside-root inode has no
    symlink to resolve, so validate_path alone allows it; the hardened
    pathsec.open must refuse it via the st_nlink guard (CWE-59, GHSA-f794 class)."""
    import os

    from nltk import pathsec

    outside = os.path.join(os.path.dirname(corpus_root["root"]), "hl_secret")
    with open(outside, "w") as fh:
        fh.write("HARDLINK_LEAK")
    hardlink = os.path.join(corpus_root["root"], "hl.txt")
    try:
        os.link(outside, hardlink)
    except OSError:
        pytest.skip("cannot create hardlink on this filesystem")
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(hardlink, required_root=corpus_root["root"]):
            pass


def test_pathsec_open_reads_legit_in_root_file(corpus_root):
    """The hardened read path must still open a genuine in-root file."""
    from nltk import pathsec

    with pathsec.open(corpus_root["legit"], required_root=corpus_root["root"]) as fh:
        assert fh.read() == "in-root"


def test_pathsec_open_final_symlink_atomic_reject(corpus_root):
    """O_NOFOLLOW makes the open atomic: a final-component symlink (in-root or
    out) is refused rather than followed, closing the validate-then-open race."""
    from nltk import pathsec

    # even a symlink that resolves in-root is refused by the atomic open
    # (corpora contain no symlinked files, so this is safe/fail-closed).
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(corpus_root["link"], required_root=corpus_root["root"]):
            pass


def test_pathsec_open_no_unsafe_fallback_on_oserror(corpus_root, monkeypatch):
    """A transient OSError from the hardened open must not fall back to a plain
    builtins.open that would follow the symlink (regression: TOCTOU leak)."""
    import os

    from nltk import pathsec

    # Point a name at an outside secret via a symlink; force the hardened open to
    # raise a non-security OSError and confirm no builtins.open retry leaks it.
    outside = os.path.join(os.path.dirname(corpus_root["root"]), "leak_secret")
    with open(outside, "w") as fh:
        fh.write("FALLBACK_LEAK")
    link = os.path.join(corpus_root["root"], "fb.txt")
    os.symlink(outside, link)
    with pytest.raises((PermissionError, ValueError, OSError)):
        with pathsec.open(link, required_root=corpus_root["root"]) as fh:
            assert "FALLBACK_LEAK" not in fh.read()


def test_pathsec_open_write_modes_still_contained(corpus_root):
    """Write/append/update modes skip the read-only hardening but must still be
    contained by validate_path (a symlink out of root is refused)."""
    from nltk import pathsec

    for mode in ("r+", "w", "a", "rb+"):
        with pytest.raises((PermissionError, ValueError, OSError)):
            with pathsec.open(
                corpus_root["link"], mode, required_root=corpus_root["root"]
            ):
                pass


# ---------------------------------------------------------------------------
# CorpusReader.__init__ reader-root validation (CWE-73, GHSA-3gq4-3j92-5w49)
# ---------------------------------------------------------------------------


@pytest.fixture
def controlled_sandbox(monkeypatch):
    """Exactly one allowed root, plus an out-of-sandbox dir and an in-root
    symlink that escapes it -- so containment is tested independent of the
    ambient tempdir that ``_get_allowed_roots`` would otherwise allow."""
    from pathlib import Path

    from nltk import pathsec

    allowed = os.path.realpath(tempfile.mkdtemp(prefix="allowed_"))
    outside = os.path.realpath(tempfile.mkdtemp(prefix="outside_"))
    os.makedirs(os.path.join(allowed, "corpus"), exist_ok=True)
    escape = os.path.join(allowed, "escape")
    os.symlink(outside, escape)  # in-root symlink -> outside
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {Path(allowed)})
    return {"allowed": allowed, "outside": outside, "escape": escape}


def test_reader_root_in_sandbox_constructs(controlled_sandbox):
    """A root inside the sandbox constructs normally."""
    from nltk.corpus.reader.api import CorpusReader

    CorpusReader(os.path.join(controlled_sandbox["allowed"], "corpus"), [])


def test_reader_root_outside_sandbox_is_refused(controlled_sandbox):
    """A string root outside the sandbox is refused at construction (CWE-73)."""
    from nltk.corpus.reader.api import CorpusReader

    with pytest.raises((PermissionError, ValueError)):
        CorpusReader(controlled_sandbox["outside"], [])


def test_reader_root_symlink_escape_is_refused(controlled_sandbox):
    """An in-sandbox symlink whose target resolves outside the sandbox is
    refused -- the check resolves symlinks (CWE-59)."""
    from nltk.corpus.reader.api import CorpusReader

    with pytest.raises((PermissionError, ValueError)):
        CorpusReader(controlled_sandbox["escape"], [])


def test_reader_root_pathpointer_outside_is_refused(controlled_sandbox):
    """FileSystemPathPointer is a str subclass, so a pointer root pointing
    outside the sandbox is validated and refused too."""
    from nltk.corpus.reader.api import CorpusReader
    from nltk.data import FileSystemPathPointer

    with pytest.raises((PermissionError, ValueError)):
        CorpusReader(FileSystemPathPointer(controlled_sandbox["outside"]), [])


def test_reader_root_check_skipped_when_enforcement_off(
    controlled_sandbox, monkeypatch
):
    """When the sandbox is disabled entirely, construction is not blocked."""
    from nltk import pathsec
    from nltk.corpus.reader.api import CorpusReader

    monkeypatch.setattr(pathsec, "ENFORCE", False)
    CorpusReader(controlled_sandbox["outside"], [])


def test_panlex_lite_outside_sandbox_db_refused(controlled_sandbox):
    """GHSA-3gq4: PanLexLiteCorpusReader must not sqlite3.connect() an
    out-of-sandbox database; the path is validated through pathsec first."""
    import sqlite3

    from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader

    db = sqlite3.connect(os.path.join(controlled_sandbox["outside"], "db.sqlite"))
    db.execute("create table lv(uid text, lv text, lc text, tt text)")
    db.commit()
    db.close()
    with pytest.raises((PermissionError, ValueError)):
        PanLexLiteCorpusReader(controlled_sandbox["outside"])


def test_panlex_lite_in_sandbox_db_loads(controlled_sandbox):
    """A PanLex Lite database inside the sandbox still loads normally."""
    import sqlite3

    from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader

    root = os.path.join(controlled_sandbox["allowed"], "panlex")
    os.makedirs(root)
    db = sqlite3.connect(os.path.join(root, "db.sqlite"))
    db.execute("create table lv(uid text, lv text, lc text, tt text)")
    db.execute("insert into lv values ('u1','lv1','en','English')")
    db.commit()
    db.close()
    reader = PanLexLiteCorpusReader(root)
    assert reader.language_varieties() == [("u1", "English")]


def test_lin_thesaurus_outside_sandbox_refused(controlled_sandbox):
    """GHSA-3gq4 second vector: LinThesaurusCorpusReader eagerly reads its data
    files at construction; an out-of-sandbox root must be refused."""
    from nltk.corpus.reader.lin import LinThesaurusCorpusReader

    with open(os.path.join(controlled_sandbox["outside"], "sim.lsp"), "w") as fh:
        fh.write('("x" (desc 1.0)\n\t"y"\t0.9\n))\n')
    with pytest.raises((PermissionError, ValueError)):
        LinThesaurusCorpusReader(controlled_sandbox["outside"])


def test_find_corpus_fileids_refuses_out_of_sandbox_walk(controlled_sandbox):
    """find_corpus_fileids() validates the root before os.walk, so a reader that
    calls it before super().__init__() cannot even enumerate an out-of-sandbox
    directory (CWE-73 defense in depth)."""
    from nltk.corpus.reader.util import find_corpus_fileids
    from nltk.data import FileSystemPathPointer

    root = FileSystemPathPointer(controlled_sandbox["outside"])
    with pytest.raises((PermissionError, ValueError)):
        find_corpus_fileids(root, r".*")


def test_ghsa_3gq4_advisory_poc_is_closed(monkeypatch, tmp_path):
    """Direct port of the GHSA-3gq4-3j92-5w49 proof-of-concept. On a vulnerable
    build the advisory reported: pathsec.open blocks a control path, yet
    LinThesaurusCorpusReader and PanLexLiteCorpusReader still read outside the
    sandbox. All three must now be blocked."""
    import sqlite3

    from nltk.corpus.reader.lin import LinThesaurusCorpusReader
    from nltk.corpus.reader.panlex_lite import PanLexLiteCorpusReader

    # Fully sealed sandbox (no allowed roots, cwd elsewhere) -- exactly the PoC.
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: set())
    monkeypatch.setattr(pathsec.os, "getcwd", lambda: "/nonexistent-cwd")

    outside = os.path.realpath(tempfile.mkdtemp(prefix="ghsa3gq4_outside_"))

    # (1) control: a direct sandboxed read of an out-of-root file is blocked.
    blocked = os.path.join(outside, "blocked.txt")
    with open(blocked, "w") as fh:
        fh.write("blocked")
    with pytest.raises((PermissionError, ValueError)):
        with pathsec.open(blocked, "rb"):
            pass

    # (2) LinThesaurusCorpusReader must not reach builtin open() outside the root.
    with open(os.path.join(outside, "sim.lsp"), "w") as fh:
        fh.write('("x" (desc 1.0)\n\t"y"\t0.9\n))\n')
    with pytest.raises((PermissionError, ValueError)):
        LinThesaurusCorpusReader(outside)

    # (3) PanLexLiteCorpusReader must not sqlite3.connect() an outside database.
    db = sqlite3.connect(os.path.join(outside, "db.sqlite"))
    db.execute("create table lv(uid text, lv text, lc text, tt text)")
    db.execute("create table dnx(ex int, mn int, uq int, ap int, ui text)")
    db.execute("create table ex(ex int, tt text, lv text, uq int)")
    db.commit()
    db.close()
    with pytest.raises((PermissionError, ValueError)):
        PanLexLiteCorpusReader(outside)


# ---------------------------------------------------------------------------
# Exhaustive sweep: NO corpus reader may reach a raw file/DB/network/enumeration
# sink on an out-of-sandbox root (CWE-73, GHSA-3gq4-3j92-5w49). This drives every
# CorpusReader subclass with a caller-supplied out-of-sandbox root (both a plain
# string and a FileSystemPathPointer) and fails if any raw sink touches a path
# under the attacker root.
# ---------------------------------------------------------------------------


def test_no_corpus_reader_leaks_out_of_sandbox(monkeypatch, tmp_path):
    import builtins
    import codecs
    import gzip
    import importlib
    import inspect
    import io
    import pkgutil
    import sqlite3
    from pathlib import Path

    import nltk.corpus.reader as reader_pkg
    from nltk.corpus.reader.api import CorpusReader
    from nltk.data import FileSystemPathPointer

    out = os.path.realpath(tempfile.mkdtemp(dir=tmp_path))  # attacker-controlled
    sandbox = os.path.realpath(tempfile.mkdtemp(dir=tmp_path))  # the only allowed root

    # Populate the attacker root with fixtures using the REAL open, BEFORE any
    # instrumentation, so reader globs (r".*") have something to match.
    for nm in (
        "a.txt",
        "cat.txt",
        "README",
        "LICENSE",
        "citation.bib",
        "f.xml",
        "1.xml",
        "sim.lsp",
        "simN.lsp",
        "a.pos",
        "a.conll",
        "a.tag",
        "a.cha",
        "cats.txt",
    ):
        with open(os.path.join(out, nm), "w") as fh:
            fh.write("x\n")
    db = sqlite3.connect(os.path.join(out, "db.sqlite"))
    db.execute("create table lv(uid text, lv text, lc text, tt text)")
    db.execute("create table dnx(ex int, mn int, uq int, ap int, ui text)")
    db.execute("create table ex(ex int, tt text, lv text, uq int)")
    db.commit()
    db.close()

    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(pathsec, "_get_allowed_roots", lambda: {Path(sandbox)})
    monkeypatch.setattr(pathsec.os, "getcwd", lambda: "/nonexistent-cwd-guard")

    leaks = []

    def _under_attacker_root(p):
        try:
            return os.path.realpath(str(p)).startswith(out)
        except Exception:
            return False

    def _instrument(module, attr, label, patharg=0):
        original = getattr(module, attr)

        def wrapper(*args, **kwargs):
            if args and _under_attacker_root(args[patharg]):
                leaks.append((label, str(args[patharg])))
            return original(*args, **kwargs)

        monkeypatch.setattr(module, attr, wrapper)

    # content sinks
    _instrument(builtins, "open", "open")
    _instrument(codecs, "open", "codecs.open")
    _instrument(io, "open", "io.open")
    _instrument(gzip, "open", "gzip.open")
    _instrument(sqlite3, "connect", "sqlite3.connect")
    _instrument(os, "open", "os.open")
    # directory-enumeration sinks (information disclosure)
    _instrument(os, "walk", "os.walk")
    _instrument(os, "listdir", "os.listdir")
    _instrument(os, "scandir", "os.scandir")

    # enumerate every concrete CorpusReader subclass
    classes = {}
    for _, modname, _ in pkgutil.iter_modules(reader_pkg.__path__):
        try:
            mod = importlib.import_module("nltk.corpus.reader." + modname)
        except Exception:
            continue
        for name, obj in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(obj, CorpusReader)
                and obj is not CorpusReader
                and obj.__module__ == mod.__name__
            ):
                classes[f"{modname}.{name}"] = obj

    outp = FileSystemPathPointer(out)
    triggers = (
        "fileids",
        "words",
        "sents",
        "paras",
        "raw",
        "tagged_words",
        "parsed_sents",
        "language_varieties",
        "entries",
        "xml",
    )
    exercised = 0
    for cls in classes.values():
        reader = None
        for args in ((out, r".*"), (outp, r".*"), (out,), (outp,)):
            try:
                reader = cls(*args)
                break
            except (PermissionError, ValueError):
                reader = None  # blocked at construction -> good
                break
            except TypeError:
                continue  # signature mismatch -> try next
            except Exception:
                reader = None
                break
        if reader is not None:
            exercised += 1
            for meth in triggers:
                fn = getattr(reader, meth, None)
                if callable(fn):
                    try:
                        res = fn()
                        if hasattr(res, "__iter__") and not isinstance(
                            res, (str, bytes)
                        ):
                            list(res)
                    except Exception:
                        pass

    assert not leaks, (
        "corpus reader(s) reached a raw sink on the out-of-sandbox attacker root "
        f"(CWE-73 leak): {leaks[:10]}"
    )
    # sanity: the sweep must actually have discovered and driven the readers,
    # otherwise a silent import/enumeration failure would make it pass vacuously.
    assert len(classes) > 40, f"only {len(classes)} readers discovered"

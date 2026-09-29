import os
import zipfile

import pytest

import nltk.data
from nltk import pathsec


def test_find_raises_exception():
    with pytest.raises(LookupError):
        nltk.data.find("no_such_resource/foo")


def test_find_raises_exception_with_full_resource_name():
    no_such_thing = "no_such_thing/bar"
    with pytest.raises(LookupError) as exc:
        nltk.data.find(no_such_thing)
    assert no_such_thing in str(exc.value)


def test_find_missing_entry_in_installed_package_demotes_download_hint():
    # Uses a well-known corpus expected to be present in CI.
    try:
        assert nltk.data.find("corpora/stopwords/english").file_size() > 0
    except LookupError:
        pytest.skip("stopwords corpus not available in this test environment")

    with pytest.raises(LookupError) as exc:
        nltk.data.find("corpora/stopwords/spanglish")

    s = str(exc.value)

    # Must reference the specific missing resource that was requested.
    assert "Attempted to load 'corpora/stopwords/spanglish'" in s

    # Error must not misleadingly claim that the entire 'stopwords' resource is missing.
    assert "Resource 'stopwords' not found" not in s

    # Downloader hint should remain present.
    assert "nltk.download('stopwords')" in s


@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="needs POSIX permission bits and an account that mode 000 stops",
)
def test_find_names_an_archive_it_cannot_read(tmp_path, monkeypatch):
    """Regression test for #3928.

    A package that is never unzipped (wordnet, omw-1.4, ...) is read straight
    from its archive. When that archive exists but is unreadable to this account
    (installed by root at image build time), ``find()`` used to fold the
    ``PermissionError`` into a plain "Resource not found" with a download hint.
    It must still raise ``LookupError`` (a later search root may hold a readable
    copy) but name the archive and say how to get a readable install: extract.
    """
    root = tmp_path / "nltk_data"
    corpora = root / "corpora"
    corpora.mkdir(parents=True)
    archive = corpora / "x.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("x/a.txt", "hello")
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)

    # Readable: resolved the way LazyCorpusLoader asks for a zipped corpus.
    assert isinstance(nltk.data.find("corpora/x/"), nltk.data.ZipFilePathPointer)
    assert isinstance(nltk.data.find("corpora/x.zip/x/"), nltk.data.ZipFilePathPointer)

    os.chmod(archive, 0)
    try:
        assert not os.access(archive, os.R_OK)
        for name in ("corpora/x", "corpora/x/", "corpora/x.zip/x/"):
            with pytest.raises(LookupError) as exc:
                nltk.data.find(name)
            s = str(exc.value)
            assert f"Attempted to load '{name}'" in s
            assert "Found but could not read (permission denied):" in s
            assert f"- {str(archive)!r}" in s
            # the archive stays private by design: the remedy is extraction
            assert f"python -m nltk.downloader --extract -d {str(root)!r} x" in s
            assert "nltk.download('x', extract=True)" in s
            assert "chmod -R a+rX" not in s
            assert f"- {str(root)!r}" in s.split("Searched in:")[1]
    finally:
        os.chmod(archive, 0o644)

    # Readable again: found, and a plain miss carries no permission text.
    assert isinstance(nltk.data.find("corpora/x/"), nltk.data.ZipFilePathPointer)
    with pytest.raises(LookupError) as exc:
        nltk.data.find("corpora/y/")
    assert "could not read" not in str(exc.value)


@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="needs POSIX permission bits and an account the mode bits stop",
)
def test_find_refuses_a_data_root_another_account_can_write_to(tmp_path, monkeypatch):
    """A directory another account can write to is not a data root, whatever the
    mode of the files in it: a planted archive or file there would be loaded as
    trusted data. ``find()`` refuses the root (or the writable directory on the
    way to the resource), warns, names it in the ``LookupError`` with the remedy,
    keeps searching later roots, and does nothing different with enforcement off.
    """
    root = tmp_path / "nltk_data"
    corpora = root / "corpora" / "x"
    corpora.mkdir(parents=True)
    (corpora / "a.txt").write_text("hello")
    archive_root = tmp_path / "zips"
    archive_root.mkdir()
    with zipfile.ZipFile(archive_root / "x.zip", "w") as zf:
        zf.writestr("x/a.txt", "hello")
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)
    assert isinstance(
        nltk.data.find("corpora/x/a.txt"), nltk.data.FileSystemPathPointer
    )

    def refused(where, name="corpora/x/a.txt"):
        with pytest.warns(RuntimeWarning, match="writable by other accounts"):
            with pytest.raises(LookupError) as exc:
                nltk.data.find(name)
        s = str(exc.value)
        assert "Refused, writable by other accounts" in s
        assert f"- {str(where)!r}" in s and f"chmod go-w {str(where)!r}" in s
        return s

    for where, mode in ((root, 0o777), (root / "corpora", 0o775), (corpora, 0o1777)):
        old = os.stat(where).st_mode & 0o7777
        os.chmod(where, mode)
        try:
            refused(where)
        finally:
            os.chmod(where, old)
    assert isinstance(
        nltk.data.find("corpora/x/a.txt"), nltk.data.FileSystemPathPointer
    )

    # a zip search-path entry inside a writable directory is refused too
    monkeypatch.setattr(nltk.data, "path", [str(archive_root / "x.zip")])
    os.chmod(archive_root, 0o777)
    try:
        refused(archive_root, "x/a.txt")
    finally:
        os.chmod(archive_root, 0o755)
    assert isinstance(nltk.data.find("x/a.txt"), nltk.data.ZipFilePathPointer)

    # a later private root still serves while the first is refused
    private = tmp_path / "private_root" / "corpora" / "x"
    private.mkdir(parents=True)
    (private / "a.txt").write_text("private")
    monkeypatch.setattr(nltk.data, "path", [str(root), str(tmp_path / "private_root")])
    os.chmod(root, 0o777)
    try:
        with pytest.warns(RuntimeWarning, match="writable by other accounts"):
            found = nltk.data.find("corpora/x/a.txt")
        assert str(found.path).startswith(str(tmp_path / "private_root"))
        # enforcement off keeps the historical behaviour
        monkeypatch.setattr(pathsec, "ENFORCE", False)
        found = nltk.data.find("corpora/x/a.txt")
        assert str(found.path).startswith(str(root))
    finally:
        os.chmod(root, 0o755)


# ===========================================================================
# Rogue files in a data root: what nltk's loaders do with them
# ===========================================================================
NUL = chr(0)
MiB = 1024 * 1024
BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
    + "".join(
        '<!ENTITY lol%d "%s">'
        % (i, "&lol%d;" % (i - 1) * 10 if i > 1 else "&lol;" * 10)
        for i in range(1, 7)
    )
    + "]><lolz>&lol6;</lolz>"
)


class _Callable:
    """A pickle whose reduce names a callable global: the shape of every
    code-executing pickle payload."""

    def __reduce__(self):
        return (dict, ([("PWNED", 1)],))


@pytest.fixture
def rogue_root(tmp_path, monkeypatch):
    import pickle

    root = tmp_path / "nltk_data"
    (root / "corpora").mkdir(parents=True)
    members = [
        ("rogue/", b""),
        ("rogue/evil.pickle", pickle.dumps(_Callable(), protocol=4)),
        ("rogue/evil.json", b'{"!rogue.Trojan": {"cmd": "x"}}'),
        ("rogue/deep.json", ("[" * 200000 + "]" * 200000).encode()),
        ("rogue/evil.xml", BILLION_LAUGHS.encode()),
        ("rogue/evil.yaml", b"!!python/object/apply:os.getcwd []\n"),
        ("../escape.txt", b"escaped"),
        ("rogue/words.txt", b"alpha\nbeta\n"),
    ]
    with zipfile.ZipFile(root / "corpora" / "rogue.zip", "w") as zf:
        for name, data in members:
            zf.writestr(name, data)
    with zipfile.ZipFile(
        root / "corpora" / "bomb.zip", "w", zipfile.ZIP_DEFLATED
    ) as zf:
        zf.writestr("bomb/", b"")
        zf.writestr("bomb/bomb.txt", b"\0" * (64 * MiB))
        zf.writestr("bomb/words.txt", b"alpha\n")
    (root / "corpora" / "loose.pickle").write_bytes(
        pickle.dumps(_Callable(), protocol=4)
    )
    monkeypatch.setattr(nltk.data, "path", [str(root)])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)
    return root


class TestRogueFilesInADataRoot:
    def test_a_callable_pickle_is_refused_inside_and_outside_an_archive(
        self, rogue_root
    ):
        import pickle

        for name in ("corpora/rogue/evil.pickle", "corpora/loose.pickle"):
            with pytest.raises(pickle.UnpicklingError, match="forbidden"):
                nltk.data.load(name)
        # raw bytes are handed over as bytes only, never unpickled
        raw = nltk.data.load("corpora/rogue/evil.pickle", format="raw")
        assert isinstance(raw, bytes) and b"PWNED" in raw

    def test_tagged_and_deep_json_are_refused(self, rogue_root):
        with pytest.raises(ValueError, match="json tag"):
            nltk.data.load("corpora/rogue/evil.json")
        with pytest.raises(ValueError, match="nesting"):
            nltk.data.load("corpora/rogue/deep.json")

    def test_a_yaml_python_tag_is_refused(self, rogue_root):
        yaml = pytest.importorskip("yaml")
        with pytest.raises(yaml.constructor.ConstructorError):
            nltk.data.load("corpora/rogue/evil.yaml")

    def test_an_xml_entity_bomb_is_refused_through_the_corpus_reader(self, rogue_root):
        from nltk.corpus.reader import XMLCorpusReader

        reader = XMLCorpusReader(
            nltk.data.find("corpora/rogue.zip/rogue/"), r"evil\.xml"
        )
        with pytest.raises(Exception) as exc:
            reader.xml()
        assert type(exc.value).__name__ == "EntitiesForbidden"

    def test_a_zip_bomb_member_makes_the_whole_archive_unusable(self, rogue_root):
        from nltk.corpus.reader import WordListCorpusReader

        with pytest.raises(ValueError, match="zip bomb"):
            nltk.data.find("corpora/bomb/bomb.txt").open().read()
        with pytest.raises(ValueError, match="zip bomb"):
            WordListCorpusReader(
                nltk.data.find("corpora/bomb.zip/bomb/"), ["words.txt"]
            ).words()
        # the archive without the bomb serves its plain member
        reader = WordListCorpusReader(
            nltk.data.find("corpora/rogue.zip/rogue/"), ["words.txt"]
        )
        assert reader.words() == ["alpha", "beta"]

    def test_escaping_member_names_stay_inside_the_archive(self, rogue_root):
        """A member named with '..' is bytes inside the archive and nothing more
        (test_pathsec_sweep_tag documents the same); find() refuses the name,
        an absolute member name is not found, and a plain member still reads."""
        archive = str(rogue_root / "corpora" / "rogue.zip")
        before = sorted(os.listdir(rogue_root)) + sorted(os.listdir(rogue_root.parent))
        pointer = nltk.data.ZipFilePathPointer(archive, "../escape.txt")
        with pointer.open() as fh:
            assert fh.read() == b"escaped"
        assert (
            sorted(os.listdir(rogue_root)) + sorted(os.listdir(rogue_root.parent))
            == before
        )
        assert not (rogue_root.parent / "escape.txt").exists()
        with pytest.raises(OSError):
            nltk.data.ZipFilePathPointer(archive, "/abs.txt")
        with pytest.raises((ValueError, LookupError)):
            nltk.data.find("corpora/rogue.zip/../escape.txt")
        assert (
            nltk.data.ZipFilePathPointer(archive, "rogue/words.txt").open().read()
            == b"alpha\nbeta\n"
        )


@pytest.mark.skipif(
    os.name != "posix" or os.geteuid() == 0,
    reason="needs POSIX permission bits, symlinks and an account the mode bits stop",
)
def test_find_judges_a_symlinked_root_by_its_target(tmp_path, monkeypatch):
    """A search-path entry that is a symlink is judged by the directory it
    resolves to: a link into a directory other accounts can write to is refused,
    a link into a private one serves. A root cannot impersonate a private
    directory through a link."""
    target = tmp_path / "real_root"
    (target / "corpora" / "x").mkdir(parents=True)
    (target / "corpora" / "x" / "a.txt").write_text("hello")
    link = tmp_path / "linked_root"
    os.symlink(str(target), str(link))
    monkeypatch.setattr(nltk.data, "path", [str(link)])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None)
    assert isinstance(
        nltk.data.find("corpora/x/a.txt"), nltk.data.FileSystemPathPointer
    )
    os.chmod(target, 0o777)
    try:
        with pytest.warns(RuntimeWarning, match="writable by other accounts"):
            with pytest.raises(LookupError) as exc:
                nltk.data.find("corpora/x/a.txt")
        assert "Refused, writable by other accounts" in str(exc.value)
    finally:
        os.chmod(target, 0o755)
    assert isinstance(
        nltk.data.find("corpora/x/a.txt"), nltk.data.FileSystemPathPointer
    )

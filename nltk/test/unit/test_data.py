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

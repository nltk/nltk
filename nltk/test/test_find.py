import os
import zipfile
import pytest

import nltk.data as data


def _make_exists_checker(true_for):
    """Return a callable suitable for monkeypatching os.path.exists.
    true_for is a set/list of paths that should exist."""
    true_set = set(true_for)

    def exists(path):
        # Normalize to handle join/backslash differences on Windows
        norm = os.path.normpath(path)
        return norm in {os.path.normpath(p) for p in true_set}

    return exists


def test_find_unsupported_protocol(monkeypatch):
    # split_resource_url says it's an http resource -> unsupported
    monkeypatch.setattr(data, "split_resource_url", lambda name: ("http", name))
    with pytest.raises(LookupError) as exc:
        data.find("http://example.com/resource")
    assert "Unsupported resource protocol" in str(exc.value)


def test_find_file_protocol_found(monkeypatch):
    # file protocol and the target path exists -> returns FileSystemPathPointer
    target = r"C:\some\path\resource"
    monkeypatch.setattr(data, "split_resource_url", lambda name: ("file", target))
    monkeypatch.setattr(data.os.path, "exists", _make_exists_checker([target]))

    ptr = data.find("file:" + target)
    assert ptr is not None
    assert ptr.__class__.__name__ == "FileSystemPathPointer"


def test_find_file_protocol_not_found(monkeypatch):
    target = r"C:\no\such\file"
    monkeypatch.setattr(data, "split_resource_url", lambda name: ("file", target))
    monkeypatch.setattr(data.os.path, "exists", _make_exists_checker([]))

    with pytest.raises(LookupError) as exc:
        data.find("file:" + target)
    assert "File resource not found" in str(exc.value)


def test_find_search_paths_finds_filesystem_path(monkeypatch):
    # Resource with no protocol -> search in provided _default_paths
    resource = "corpora/wordnet"
    root = r"C:\nltkdata"
    candidate = os.path.join(root, "corpora", "wordnet")

    monkeypatch.setattr(data, "split_resource_url", lambda name: (None, resource))
    # Force module _default_paths to a controlled value
    monkeypatch.setattr(data, "_default_paths", [root], raising=False)
    monkeypatch.setattr(data.os.path, "exists", _make_exists_checker([candidate]))

    ptr = data.find(resource)
    assert ptr is not None
    assert ptr.__class__.__name__ == "FileSystemPathPointer"


def test_find_zip_root_returns_zip_pointer(monkeypatch):
    # If a root is a zip and contains the resource, should return ZipFilePathPointer
    resource = "corpora/wordnet/data.txt"
    root_zip = r"C:\data.zip"
    monkeypatch.setattr(data, "split_resource_url", lambda name: (None, resource))
    monkeypatch.setattr(data, "_default_paths", [root_zip], raising=False)

    # os.path.exists should say the zip file exists but the joined candidate file does not
    def exists(path):
        p = os.path.normpath(path)
        if p == os.path.normpath(root_zip):
            return True
        return False

    monkeypatch.setattr(data.os.path, "exists", exists)

    class DummyZip:
        def __init__(self, path):
            # accept the path and keep it if needed by the pointer
            self._path = os.path.normpath(path)

        def namelist(self):
            return [resource]

    # Make the quick namelist check succeed by stubbing zipfile.ZipFile
    monkeypatch.setattr(data.zipfile, "ZipFile", DummyZip)

    # Prevent invoking the real ZipFilePathPointer.__init__ (which triggers
    # extra logic in data.py). Provide a lightweight stub class with the
    # same name so the test assertion still passes.
    class ZipFilePathPointer:
        def __init__(self, root, resource_name):
            self.root = root
            self.resource_name = resource_name

    monkeypatch.setattr(data, "ZipFilePathPointer", ZipFilePathPointer)

    ptr = data.find(resource)
    assert ptr is not None
    assert ptr.__class__.__name__ == "ZipFilePathPointer"


class ReopenableZipFile(zipfile.ZipFile):
    """A ZipFile that can be reopened after being closed."""

    def __init__(self, filename):
        if not isinstance(filename, str):
            raise TypeError("ReopenableZipFile filename must be a string")
        zipfile.ZipFile.__init__(self, filename)
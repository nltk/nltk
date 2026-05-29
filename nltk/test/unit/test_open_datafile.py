import os
import zipfile
from tempfile import TemporaryDirectory

import pytest

import nltk.data
from nltk.data import ZipFilePathPointer, open_datafile


def _create_test_zip(root_dir, rel_dir, file_name, contents: bytes):
    """
    Create a zip file under root_dir with a single file at rel_dir/file_name
    containing 'contents'. Return the full path to the zip file and the
    relative path inside the zip.
    """
    zip_path = os.path.join(root_dir, "testdata.zip")
    arcname = os.path.join(rel_dir, file_name).replace(os.path.sep, "/")

    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr(arcname, contents)

    return zip_path, arcname


def _create_zip_with_directory(root_dir, zip_name="pkg.zip"):
    """
    Create a zip file under root_dir containing an explicit 'pkg/' directory
    entry and a 'pkg/data.txt' file. Return the full path to the zip file.

    Some zip writers emit explicit directory entries, so this includes one.
    See https://bugs.python.org/issue34738 for examples.
    """
    zip_path = os.path.join(root_dir, zip_name)
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("pkg/", "")
        zf.writestr("pkg/data.txt", "hello")
    return zip_path


def test_open_datafile_directory_and_filename_from_zip():
    """open_datafile should open a file inside a zip when given dir + file_name."""
    with TemporaryDirectory() as tmpdir:
        rel_dir = os.path.join("corpora", "testpkg")
        file_name = "sample.txt"
        text = "Hello from zipped data\n"
        data = text.encode("utf-8")

        zip_path, arcname = _create_test_zip(tmpdir, rel_dir, file_name, data)

        # Directory entry inside the zip (must end with '/').
        dir_entry = rel_dir.replace(os.path.sep, "/") + "/"

        # PathPointer representing the *directory* inside the zip.
        path = ZipFilePathPointer(zip_path, dir_entry)

        with open_datafile(path, file_name=file_name, encoding="utf-8") as f:
            result = f.read()

        assert result == text


def test_open_datafile_file_pointer_from_zip():
    """open_datafile should open a file pointer directly when file_name is empty."""
    with TemporaryDirectory() as tmpdir:
        rel_dir = os.path.join("corpora", "testpkg")
        file_name = "sample.txt"
        text = "Direct file pointer from zipped data\n"
        data = text.encode("utf-8")

        zip_path, arcname = _create_test_zip(tmpdir, rel_dir, file_name, data)

        # Directory pointer first, then join to the file to simulate having a file pointer.
        dir_entry = rel_dir.replace(os.path.sep, "/") + "/"
        dir_pointer = ZipFilePathPointer(zip_path, dir_entry)
        file_pointer = dir_pointer.join(file_name)

        with open_datafile(file_pointer, encoding="utf-8") as f:
            result = f.read()

        assert result == text


def test_open_datafile_binary_mode_from_zip():
    """open_datafile should return a binary stream when encoding=None."""
    with TemporaryDirectory() as tmpdir:
        rel_dir = os.path.join("corpora", "testpkg")
        file_name = "binary.bin"
        binary_data = b"\x00\x01\x02\xff"

        zip_path, arcname = _create_test_zip(tmpdir, rel_dir, file_name, binary_data)

        dir_entry = rel_dir.replace(os.path.sep, "/") + "/"
        dir_pointer = ZipFilePathPointer(zip_path, dir_entry)

        with open_datafile(dir_pointer, file_name=file_name, encoding=None) as f:
            result = f.read()

        assert isinstance(result, (bytes, bytearray))
        assert result == binary_data


def test_zipfilepathpointer_accepts_bare_directory_entry():
    """ZipFilePathPointer should accept a directory entry written without a trailing slash.

    find()'s zip-rewrite fallback rewrites e.g. 'corpora/wordnet' to
    'corpora/wordnet.zip/wordnet' -- a bare directory name with no trailing
    slash. The constructor must accept it as long as the zipfile contains
    files under that prefix; otherwise find('corpora/wordnet') never resolves
    to a pre-staged corpora/wordnet.zip even when it exists on disk.
    """
    with TemporaryDirectory() as tmpdir:
        zip_path = _create_zip_with_directory(tmpdir)
        ptr = ZipFilePathPointer(zip_path, "pkg")
        assert ptr is not None


def test_zipfilepathpointer_accepts_directory_entry_with_slash():
    """Regression: trailing-slash directory entries must continue to work."""
    with TemporaryDirectory() as tmpdir:
        zip_path = _create_zip_with_directory(tmpdir)
        ptr = ZipFilePathPointer(zip_path, "pkg/")
        assert ptr is not None


def test_zipfilepathpointer_rejects_unrelated_entry():
    """A bare name that isn't a directory prefix of any zip member must still raise."""
    with TemporaryDirectory() as tmpdir:
        zip_path = _create_zip_with_directory(tmpdir)
        with pytest.raises(OSError):
            ZipFilePathPointer(zip_path, "no_such_entry")


def test_find_resolves_bare_directory_inside_zip():
    """find('corpora/pkg') should resolve to corpora/pkg.zip on the data path,
    even when 'pkg' is a directory rather than a file inside that zip. This
    mirrors the documented zip-rewrite fallback for the directory case.
    """
    with TemporaryDirectory() as tmpdir:
        corpora_dir = os.path.join(tmpdir, "corpora")
        os.makedirs(corpora_dir)
        _create_zip_with_directory(corpora_dir)

        ptr = nltk.data.find("corpora/pkg", (tmpdir,))
        assert "pkg.zip" in str(ptr)

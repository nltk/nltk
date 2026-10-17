import hashlib
import io
import os
import shutil
import unittest
import unittest.mock
import xml.etree.ElementTree as ET
from urllib.error import URLError

import pytest

from nltk import download
from nltk.downloader import Downloader, ErrorMessage, Package, build_index


class TestPackageFromXmlInjection(unittest.TestCase):
    """Security tests for XML attribute injection via Package.fromxml."""

    def test_fromxml_neutralises_injected_filename(self):
        """Malicious filename attribute in XML must be ignored."""
        mock_xml = """
        <package id="test_pkg" name="Test Package" subdir="corpora"
                 url="http://example.com/test_pkg.zip" size="100"
                 unzipped_size="100" checksum="0" unzip="0"
                 filename="../../../vulnerable_overwrite.txt" />
        """
        xml_element = ET.fromstring(mock_xml)
        pkg = Package.fromxml(xml_element)

        expected = os.path.join("corpora", "test_pkg.zip")
        self.assertEqual(pkg.filename, expected)
        self.assertNotIn("..", pkg.filename)
        self.assertFalse(os.path.isabs(pkg.filename))


def test_downloader_using_existing_parent_download_dir(tmp_path):
    """Test that download works properly when the parent folder of the download_dir exists"""
    download_dir = str(tmp_path.joinpath("another_dir"))
    with unittest.mock.patch.dict(os.environ, {"NLTK_ALLOW_PROXIED_URLOPEN": "1"}):
        download_status = download("mwa_ppdb", download_dir)
    assert download_status is True


def test_downloader_using_non_existing_parent_download_dir(tmp_path):
    """Test that download works properly when the parent folder of the download_dir does not exist"""
    download_dir = str(
        tmp_path.joinpath("non-existing-parent-folder", "another-non-existing-folder")
    )
    with unittest.mock.patch.dict(os.environ, {"NLTK_ALLOW_PROXIED_URLOPEN": "1"}):
        download_status = download("mwa_ppdb", download_dir)
    assert download_status is True


def test_downloader_redownload(tmp_path):
    """Test that a second download correctly triggers the 'already up-to-date' message"""
    first_download = 0
    second_download = 1

    download_dir = str(tmp_path.joinpath("test_repeat_download"))
    for i in range(first_download, second_download + 1):
        # the downloader routes output through the early-bound safe_print name,
        # so intercept that module attribute, not the builtins.print name
        with unittest.mock.patch("nltk.downloader.safe_print") as print_mock:
            with unittest.mock.patch.dict(
                os.environ, {"NLTK_ALLOW_PROXIED_URLOPEN": "1"}
            ):
                download_status = download("stopwords", download_dir)
            assert download_status is True
            if i == first_download:
                expected_second_call = unittest.mock.call(
                    "[nltk_data]   Unzipping %s."
                    % os.path.join("corpora", "stopwords.zip")
                )
                assert print_mock.call_args_list[1].args == expected_second_call.args
            elif i == second_download:
                expected_second_call = unittest.mock.call(
                    "[nltk_data]   Package stopwords is already up-to-date!"
                )
                assert print_mock.call_args_list[1].args == expected_second_call.args


@pytest.mark.parametrize(
    "package, error",
    [
        # #3167: a Docker build could not reach the data server
        ("punkt", OSError(99, "Cannot assign requested address")),
        # #3144: a Heroku build (nltk.txt) had its connection reset
        ("stopwords", ConnectionResetError(104, "Connection reset by peer")),
    ],
)
def test_retry_prompt_at_eof_answers_no(tmp_path, monkeypatch, package, error):
    """When nobody can answer the "Retry? [n/y/e]" prompt because stdin is at
    EOF, as in the Docker and Heroku builds of #3167 and #3144, the downloader
    takes the answer an empty line gives ("n": do not retry) instead of
    crashing with EOFError."""
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    download_dir = str(tmp_path)
    downloader = Downloader(download_dir=download_dir)
    output = io.StringIO()
    with unittest.mock.patch("nltk.downloader.urlopen", side_effect=URLError(error)):
        # halt_on_error=False is what ``python -m nltk.downloader <package>``
        # passes, and what makes the downloader ask whether to retry.
        status = downloader.download(
            package, download_dir, halt_on_error=False, print_error_to=output
        )

    assert f"Error loading {package}:" in output.getvalue()
    assert "Error installing package. Retry? [n/y/e]" in output.getvalue()
    assert status is True and downloader._errors is True


@pytest.mark.parametrize(
    "answers, status, attempts",
    [
        ("n\n", True, 1),  # do not retry, go on
        ("\n", True, 1),  # an empty line means "n"
        ("e\n", False, 1),  # stop
        ("y\nn\n", True, 2),  # retry once, then go on
    ],
)
def test_retry_prompt_typed_answers_are_unchanged(
    tmp_path, monkeypatch, answers, status, attempts
):
    """Answers typed or piped in at the "Retry? [n/y/e]" prompt still work."""
    monkeypatch.setattr("sys.stdin", io.StringIO(answers))
    package = Package(
        "test_pkg", "https://example.invalid/test_pkg.zip", size=0, unzipped_size=0
    )
    downloader = Downloader(download_dir=str(tmp_path))
    # The package itself fails (not the index), so "y" has a package to retry.
    with unittest.mock.patch.object(
        Downloader,
        "incr_download",
        side_effect=lambda *args, **kwargs: iter([ErrorMessage(package, "failed")]),
    ) as incr_download:
        result = downloader.download(
            "test_pkg", str(tmp_path), halt_on_error=False, print_error_to=io.StringIO()
        )

    assert result is status
    assert incr_download.call_count == attempts


def test_retry_prompt_without_stdin_answers_no(tmp_path, monkeypatch):
    """A process started with no stdin at all (fd 0 closed, a service without
    a console) has ``sys.stdin`` None and input() raises RuntimeError, not
    EOFError: the prompt takes "n" then too."""
    monkeypatch.setattr("sys.stdin", None)
    downloader = Downloader(download_dir=str(tmp_path))
    output = io.StringIO()
    with unittest.mock.patch(
        "nltk.downloader.urlopen", side_effect=URLError(OSError(99, "x"))
    ):
        status = downloader.download(
            "punkt", str(tmp_path), halt_on_error=False, print_error_to=output
        )

    assert "Error installing package. Retry? [n/y/e]" in output.getvalue()
    assert status is True and downloader._errors is True


@pytest.mark.parametrize("request_", ["punkt", ["punkt", "stopwords"]])
def test_retry_prompt_y_after_an_index_failure_retries_the_request(
    tmp_path, monkeypatch, request_
):
    """When the index itself cannot be loaded, as in #3167 and #3144, the
    error carries an id or nothing, not a Package. "y" retries what was asked
    for instead of crashing on ``msg.package.id``."""
    monkeypatch.setattr("sys.stdin", io.StringIO("y\nn\n"))
    downloader = Downloader(download_dir=str(tmp_path))
    output = io.StringIO()
    with unittest.mock.patch(
        "nltk.downloader.urlopen", side_effect=URLError(OSError(99, "x"))
    ) as urlopen:
        status = downloader.download(
            request_, str(tmp_path), halt_on_error=False, print_error_to=output
        )

    assert output.getvalue().count("Error installing package. Retry? [n/y/e]") == 2
    assert urlopen.call_count == 2
    assert status is True and downloader._errors is True


def test_build_index(tmp_path):
    """Test building index with both checksums."""

    test_pkg_dir = str(tmp_path.joinpath("packages"))
    test_pkg_name = "test_package"
    test_pkg_path = os.path.join(test_pkg_dir, f"{test_pkg_name}")
    os.makedirs(test_pkg_path, exist_ok=True)
    test_xml_path = os.path.join(test_pkg_path, f"{test_pkg_name}.xml")
    with open(test_xml_path, "w") as fi:
        fi.write(
            f'<package id="{test_pkg_name}" name="A Test Package" webpage="http://www.somefake.url/"'
            ' unzip="1"/>'
        )
    # Cannot mock a zip here as we are trying to validate file checksums, so just create a simple one with the XML
    zip_path = os.path.join(test_pkg_path, f"{test_pkg_name}")
    shutil.make_archive(
        base_name=zip_path,
        format="zip",
        root_dir=test_pkg_dir,
        base_dir=os.path.basename(test_pkg_path),
    )
    xml_index = build_index(
        root=os.path.dirname(test_pkg_dir), base_url="https://someurl"
    )
    package_element = xml_index[0][0]
    assert package_element.get("id") == "test_package"
    md5_checksum = package_element.get("checksum")
    assert isinstance(md5_checksum, str)
    assert len(md5_checksum) > 5
    sha256_checksum = package_element.get("sha256_checksum")
    assert isinstance(sha256_checksum, str)
    assert len(sha256_checksum) > 5


def test_download_package_uses_scoped_pathsec_open(tmp_path):
    """
    Regression test for PR #3622.

    Verify that _download_package() routes the package write through
    pathsec.open with the downloader's download_dir as required_root, and that
    the final destination is still validated before os.replace().
    """
    download_dir = str(tmp_path.joinpath("download"))
    os.makedirs(download_dir, exist_ok=True)

    downloader = Downloader(download_dir=download_dir)

    class DummyInfo:
        id = "dummy"
        url = "https://example.com/dummy.txt"
        size = 1
        filename = os.path.join("corpora", "dummy.txt")
        subdir = "corpora"
        unzip = False
        sha256_checksum = hashlib.sha256(b"x").hexdigest()
        checksum = hashlib.md5(b"x").hexdigest()

    info = DummyInfo()
    tmp_file = os.path.join(download_dir, info.filename) + ".tmp"
    final_file = os.path.join(download_dir, info.filename)

    with unittest.mock.patch(
        "nltk.downloader.urlopen"
    ) as urlopen_mock, unittest.mock.patch(
        "nltk.downloader.pathsec_open"
    ) as pathsec_open_mock, unittest.mock.patch(
        "nltk.downloader.validate_path"
    ) as validate_path_mock, unittest.mock.patch(
        "nltk.downloader.pathsec.replace"
    ) as replace_mock, unittest.mock.patch(
        "nltk.downloader.os.makedirs"
    ), unittest.mock.patch(
        "nltk.downloader.os.open", return_value=3
    ), unittest.mock.patch(
        "nltk.downloader.os.close"
    ), unittest.mock.patch(
        "nltk.downloader.os.path.exists", return_value=False
    ), unittest.mock.patch(
        "nltk.downloader.time.time", return_value=0
    ), unittest.mock.patch(
        "nltk.downloader.itertools.count", return_value=iter([0])
    ), unittest.mock.patch(
        "nltk.downloader.os.path.getsize", return_value=1
    ), unittest.mock.patch(
        "nltk.downloader.sha256_hexdigest",
        return_value=hashlib.sha256(b"x").hexdigest(),
    ), unittest.mock.patch(
        "nltk.downloader.md5_hexdigest",
        return_value=hashlib.md5(b"x").hexdigest(),
    ), unittest.mock.patch.object(
        Downloader, "status", return_value=Downloader.NOT_INSTALLED
    ):

        infile = unittest.mock.Mock()
        infile.read.side_effect = [b"x", b""]
        infile.close.return_value = None
        urlopen_mock.return_value = infile

        outfile = unittest.mock.Mock()
        pathsec_open_mock.return_value.__enter__.return_value = outfile
        pathsec_open_mock.return_value.__exit__.return_value = False

        list(downloader._download_package(info, download_dir, force=True))

        pathsec_open_mock.assert_called_once_with(
            tmp_file,
            "wb",
            context="Downloader._download_package",
            required_root=download_dir,
        )

        validate_path_mock.assert_any_call(
            final_file,
            context="Downloader._download_package",
            required_root=download_dir,
        )

        replace_mock.assert_called_once_with(
            tmp_file, final_file, context="Downloader._download_package"
        )

        # Sanity check: the PR-specific path scoping does not change builtins.open.
        assert open is __builtins__["open"]

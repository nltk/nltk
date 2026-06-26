import hashlib
import os
import shutil
import unittest
import unittest.mock
import xml.etree.ElementTree as ET

from nltk import download
from nltk.downloader import Downloader, Package, build_index


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
    download_status = download("mwa_ppdb", download_dir)
    assert download_status is True


def test_downloader_using_non_existing_parent_download_dir(tmp_path):
    """Test that download works properly when the parent folder of the download_dir does not exist"""

    download_dir = str(
        tmp_path.joinpath("non-existing-parent-folder", "another-non-existing-folder")
    )
    download_status = download("mwa_ppdb", download_dir)
    assert download_status is True


def test_downloader_redownload(tmp_path):
    """Test that a second download correctly triggers the 'already up-to-date' message"""

    first_download = 0
    second_download = 1

    download_dir = str(tmp_path.joinpath("test_repeat_download"))
    for i in range(first_download, second_download + 1):
        # capsys doesn't capture functools.partial stdout, which nltk.download.show uses, so just mock print
        with unittest.mock.patch("builtins.print") as print_mock:
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
        "nltk.downloader.os.replace"
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

        replace_mock.assert_called_once_with(tmp_file, final_file)

        # Sanity check: the PR-specific path scoping does not change builtins.open.
        assert open is __builtins__["open"]

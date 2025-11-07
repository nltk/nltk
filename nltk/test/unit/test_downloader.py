import os
import shutil
import unittest.mock

import pytest

from nltk import download
from nltk.downloader import build_index


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


@pytest.mark.iterations(1)
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

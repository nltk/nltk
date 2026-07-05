import ntpath
import os
from types import SimpleNamespace

import nltk.data
import nltk.downloader
from nltk.parse.malt import MaltParser


def test_normalize_resource_name_treats_nt_as_windows(monkeypatch):
    monkeypatch.setattr(nltk.data.os, "name", "nt")
    monkeypatch.setattr(nltk.data.os, "path", ntpath)

    assert (
        nltk.data.normalize_resource_name("C:/dir/file", False, "/") == "/C:/dir/file"
    )


def test_default_download_dir_uses_os_name_for_windows(monkeypatch):
    windows_os = SimpleNamespace(
        environ={"APPDATA": r"C:\Users\Codex\AppData\Roaming"},
        name="nt",
        path=ntpath,
    )
    monkeypatch.setattr(nltk.downloader, "os", windows_os)
    monkeypatch.setattr(nltk.data, "path", [])

    downloader = nltk.downloader.Downloader(download_dir="stub")

    assert (
        downloader.default_download_dir() == r"C:\Users\Codex\AppData\Roaming\nltk_data"
    )


def test_windows_data_paths_include_appdata(monkeypatch):
    appdata = r"C:\Users\Codex\AppData\Roaming"
    expected = ntpath.join(appdata, "nltk_data")
    monkeypatch.setattr(nltk.data.os, "path", ntpath)
    monkeypatch.setitem(nltk.data.os.environ, "APPDATA", appdata)

    assert expected in nltk.data._windows_data_paths()


def test_maltparser_command_uses_os_pathsep(monkeypatch):
    monkeypatch.setattr(os, "pathsep", ";")

    parser = MaltParser.__new__(MaltParser)
    parser.additional_java_args = []
    parser.malt_jars = ["a.jar", "b.jar"]
    parser.model = "model.mco"

    cmd = parser.generate_malt_command("input.conll", mode="learn")

    assert cmd[2] == "a.jar;b.jar"

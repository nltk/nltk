import importlib
import ntpath
import os

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
    monkeypatch.setattr(nltk.downloader.os, "name", "nt")
    monkeypatch.setenv("APPDATA", r"C:\Users\Codex\AppData\Roaming")
    monkeypatch.setattr(nltk.data, "path", [])

    downloader = nltk.downloader.Downloader(download_dir="stub")

    assert (
        downloader.default_download_dir() == r"C:\Users\Codex\AppData\Roaming\nltk_data"
    )


def test_nltk_data_path_uses_os_name_for_windows(monkeypatch):
    with monkeypatch.context() as patched:
        patched.setattr(nltk.data.os, "name", "nt")
        patched.setattr(nltk.data.sys, "platform", "cli")
        patched.setattr(nltk.data.os, "path", ntpath)
        patched.setenv("APPDATA", r"C:\Users\Codex\AppData\Roaming")
        patched.delenv("APPENGINE_RUNTIME", raising=False)
        reloaded = importlib.reload(nltk.data)
        assert r"C:\Users\Codex\AppData\Roaming\nltk_data" in reloaded.path

    importlib.reload(reloaded)


def test_maltparser_command_uses_os_pathsep(monkeypatch):
    monkeypatch.setattr(os, "pathsep", ";")

    parser = MaltParser.__new__(MaltParser)
    parser.additional_java_args = []
    parser.malt_jars = ["a.jar", "b.jar"]
    parser.model = "model.mco"

    cmd = parser.generate_malt_command("input.conll", mode="learn")

    assert cmd[2] == "a.jar;b.jar"

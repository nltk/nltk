# Natural Language Toolkit: machine-leak and distribution-hygiene guard teeth
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The ``no-machine-leaks`` pre-commit guard (``tools/check_no_machine_leaks.py``)
and the distribution guard (``tools/check_sdist_hygiene.py``) are what keep a
developer's home directory, a credential and a stale bytecode cache out of the
tree and out of a release. Every leak shape that reached, or nearly reached,
the 3.10.4 artifacts is planted here and must be FLAGGED, every documented
placeholder must still be ACCEPTED, and the live tree must pass."""

import importlib.util
import io
import os
import tarfile
import zipfile
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parents[3] / "tools"


def _load(name):
    path = _TOOLS / name
    if not path.exists():
        pytest.skip("guard not present in this checkout")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def leaks():
    return _load("check_no_machine_leaks.py")


@pytest.fixture(scope="module")
def hygiene():
    return _load("check_sdist_hygiene.py")


def _kinds(leaks, text):
    return [kind for _lineno, kind, _excerpt in leaks.check_text(text)]


# The strings are assembled at run time so the test file itself stays clean.
_MAC = "/Users/" + "alvas" + "/nltk_tools/jdk/Contents/Home"
_LINUX = "/home/" + "ewan" + "/twitter-files/"
_WIN = "C:\\Users\\" + "alvas" + "\\AppData"
_WIN_ESCAPED = "C:\\\\Users\\\\" + "alvas" + "\\\\AppData"

FLAGGED_HOMES = {
    "mac-home": 'JDK = "' + _MAC + '"',
    "linux-home": "Writing to " + _LINUX,
    "windows-home": 'r"' + _WIN + '"',
    "windows-home-escaped": '"' + _WIN_ESCAPED + '"',
    "doctest-example": ">>> ReppTokenizer('" + "/home/" + "alvas" + "/repp/')",
}

FLAGGED_TOKENS = {
    "pypi": "pypi-AgE" + "I" * 60,
    "github-classic": "ghp_" + "a" * 36,
    "github-fine": "github_pat_" + "A" * 50,
    "aws": "AKIA" + "Q" * 16,
    "huggingface": "hf_" + "b" * 34,
    "anthropic": "sk-ant-" + "c" * 50,
    "google": "AIza" + "d" * 35,
    "slack": "xoxb-" + "1" * 30,
    "pem": "-----BEGIN " + "RSA PRIVATE KEY" + "-----",
}

ACCEPTED = {
    "placeholder-user": "export MALT_PARSER='/home/user/maltparser-1.9.2/'",
    "placeholder-victim": "/home/victim/secret.model",
    "placeholder-appuser": "COPY check.py /home/appuser/check.py",
    "placeholder-runner": '"touch C:\\\\Users\\\\runner\\\\canary"',
    "placeholder-nltk": "split_resource_url('file:/home/nltk')",
    "placeholder-angle": "cd /Users/<name>/nltk_data",
    "not-a-home": "https://example.org/home/page and /homework/",
    "short-token-like": "ghp_short and sk-ant-short and AKIA123",
    "prose": "the home directory is read from HOME or USERPROFILE",
    "reviewed": _MAC + "  # machine-leak ok: a planted example",
}


@pytest.mark.parametrize("label", sorted(FLAGGED_HOMES))
def test_a_home_directory_is_flagged_by_user_name(leaks, label):
    kinds = _kinds(leaks, FLAGGED_HOMES[label])
    assert kinds and all(kind.startswith("home directory of ") for kind in kinds)
    assert not any(kind.endswith(" user") for kind in kinds)


@pytest.mark.parametrize("label", sorted(FLAGGED_TOKENS))
def test_a_credential_shape_is_flagged(leaks, label):
    kinds = _kinds(leaks, "token = '" + FLAGGED_TOKENS[label] + "'")
    assert kinds and not any(kind.startswith("home directory") for kind in kinds)


@pytest.mark.parametrize("label", sorted(ACCEPTED))
def test_a_placeholder_or_reviewed_line_is_accepted(leaks, label):
    assert _kinds(leaks, ACCEPTED[label]) == []


def test_line_numbers_point_at_the_leak(leaks):
    found = leaks.check_text("clean\nclean\n" + _MAC + "\nclean\n")
    assert [lineno for lineno, _kind, _excerpt in found] == [3]


def test_the_live_tree_is_clean(leaks, capsys):
    """The teeth: every tracked file, as the pre-commit hook and CI run it."""
    assert leaks.main([]) == 0, capsys.readouterr().out


# Distribution guard: archives are built in memory with a fake tracked tree.


def _tracked_tree(tmp_path, files):
    for rel, data in files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    return tmp_path, set(files)


def _sdist(tmp_path, members, top="nltk-9.9.9"):
    path = tmp_path / "nltk-9.9.9.tar.gz"
    with tarfile.open(path, "w:gz") as tar:
        for rel, data in members.items():
            info = tarfile.TarInfo(top + "/" + rel if top else rel)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return str(path)


def _wheel(tmp_path, members):
    path = tmp_path / "nltk-9.9.9-py3-none-any.whl"
    with zipfile.ZipFile(path, "w") as whl:
        for rel, data in members.items():
            whl.writestr(rel, data)
    return str(path)


TRACKED = {
    "nltk/__init__.py": b"VERSION = '9.9.9'\n",
    "nltk/util.py": b"def set_proxy(proxy, user=None, password=''):\n    pass\n",
    "nltk/test/unit/test_x.py": b"def test_x():\n    pass\n",
    "web/index.rst": b"NLTK\n",
    "web/api/.gitkeep": b"",
    "setup.py": b"from setuptools import setup\n",
    "setup.cfg": b"[metadata]\n",
    "tools/check_x.py": b"print('dev only')\n",
}
GENERATED = {
    "PKG-INFO": b"Metadata-Version: 2.1\nName: nltk\n",
    "setup.cfg": b"[metadata]\n\n[egg_info]\ntag_build = \n",
    "nltk.egg-info/SOURCES.txt": b"setup.py\n",
}


def _clean_sdist_members():
    members = {k: v for k, v in TRACKED.items() if not k.startswith("tools/")}
    members.update(GENERATED)
    return members


def test_a_clean_sdist_passes(tmp_path, hygiene, leaks):
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    path = _sdist(tmp_path, _clean_sdist_members())
    assert hygiene.check_sdist(path, tracked, str(root), leaks) == []


def test_a_clean_wheel_passes(tmp_path, hygiene, leaks):
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    path = _wheel(
        tmp_path,
        {
            "nltk/__init__.py": TRACKED["nltk/__init__.py"],
            "nltk/util.py": TRACKED["nltk/util.py"],
            "nltk-9.9.9.dist-info/METADATA": b"Name: nltk\n",
            "nltk-9.9.9.dist-info/RECORD": b"",
        },
    )
    assert hygiene.check_wheel(path, tracked, str(root), leaks) == []


SDIST_LEAKS = {
    "bytecode": ("nltk/__pycache__/util.cpython-39.pyc", b"\x00junk", "cache or tool"),
    "stray-pyc": ("nltk/util.pyc", b"\x00junk", "junk file *.pyc"),
    "editor-backup": ("nltk/util.py~", b"old", "junk file *~"),
    "os-file": ("nltk/.DS_Store", b"\x00", "junk file .DS_Store"),
    "hidden": ("nltk/.secret", b"x", "hidden file"),
    "credential-file": ("nltk/.pypirc", b"[pypi]\n", "junk file .pypirc"),
    "key-file": ("nltk/deploy.pem", b"x", "junk file *.pem"),
    "log": ("nltk/run.log", b"x", "junk file *.log"),
    "generated-manifest": ("MANIFEST", b"setup.py\n", "junk file MANIFEST"),
    "untracked-source": ("nltk/scratch_probe.py", b"x = 1\n", "not a git-tracked file"),
    "untracked-data": ("web/notes.txt", b"todo\n", "not a git-tracked file"),
    "modified-source": ("nltk/util.py", b"tampered\n", "bytes differ"),
    "home-directory": (
        "nltk/cfg.py",
        ('JDK = "' + _MAC + '"\n').encode(),
        "home directory of",
    ),
    "token": (
        "web/conf.py",
        ("key = '" + FLAGGED_TOKENS["pypi"] + "'\n").encode(),
        "PyPI API token",
    ),
}


@pytest.mark.parametrize("label", sorted(SDIST_LEAKS))
def test_a_leaked_sdist_member_is_flagged(tmp_path, hygiene, leaks, label):
    member, data, expected = SDIST_LEAKS[label]
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    members = _clean_sdist_members()
    members[member] = data
    findings = hygiene.check_sdist(_sdist(tmp_path, members), tracked, str(root), leaks)
    assert findings, label
    assert any(kind.startswith(expected) for _m, kind, _d in findings), findings
    assert all(found.startswith(member) for found, _k, _d in findings), findings


def test_a_missing_tracked_file_is_flagged(tmp_path, hygiene, leaks):
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    members = _clean_sdist_members()
    del members["nltk/test/unit/test_x.py"]
    findings = hygiene.check_sdist(_sdist(tmp_path, members), tracked, str(root), leaks)
    assert findings == [
        ("nltk/test/unit/test_x.py", "tracked file missing from the sdist", "")
    ]


def test_a_member_outside_the_release_directory_is_flagged(tmp_path, hygiene, leaks):
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    members = _clean_sdist_members()
    with tarfile.open(tmp_path / "x.tar.gz", "w:gz") as tar:
        for rel, data in members.items():
            info = tarfile.TarInfo("nltk-9.9.9/" + rel)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        info = tarfile.TarInfo("../escape.py")
        info.size = 1
        tar.addfile(info, io.BytesIO(b"x"))
    findings = hygiene.check_sdist(
        str(tmp_path / "x.tar.gz"), tracked, str(root), leaks
    )
    assert [f for f in findings if f[1] == "outside the release directory"], findings


WHEEL_LEAKS = {
    "bytecode": ("nltk/__pycache__/util.cpython-313.pyc", b"\x00", "cache or tool"),
    "unit-test": (
        "nltk/test/unit/test_x.py",
        TRACKED["nltk/test/unit/test_x.py"],
        "unit test shipped",
    ),
    "untracked": ("nltk/probe.py", b"x\n", "not a git-tracked file"),
    "modified": ("nltk/util.py", b"tampered\n", "bytes differ"),
    "outside": ("tools/check_x.py", TRACKED["tools/check_x.py"], "outside the package"),
    "home-directory": (
        "nltk/cfg.py",
        ("p = '" + _LINUX + "'\n").encode(),
        "home directory of",
    ),
    "token-in-metadata": (
        "nltk-9.9.9.dist-info/METADATA",
        ("x " + FLAGGED_TOKENS["aws"]).encode(),
        "AWS access key id",
    ),
}


@pytest.mark.parametrize("label", sorted(WHEEL_LEAKS))
def test_a_leaked_wheel_member_is_flagged(tmp_path, hygiene, leaks, label):
    member, data, expected = WHEEL_LEAKS[label]
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    members = {
        "nltk/__init__.py": TRACKED["nltk/__init__.py"],
        "nltk/util.py": TRACKED["nltk/util.py"],
        "nltk-9.9.9.dist-info/METADATA": b"Name: nltk\n",
    }
    members[member] = data
    findings = hygiene.check_wheel(_wheel(tmp_path, members), tracked, str(root), leaks)
    assert findings, label
    assert any(kind.startswith(expected) for _m, kind, _d in findings), findings
    assert all(found.startswith(member) for found, _k, _d in findings), findings


def test_main_reports_every_archive_and_fails_on_any_finding(
    tmp_path, hygiene, leaks, capsys, monkeypatch
):
    root, tracked = _tracked_tree(tmp_path / "tree", TRACKED)
    monkeypatch.setattr(hygiene, "ROOT", str(root))
    monkeypatch.setattr(leaks, "tracked_files", lambda _root: sorted(tracked))
    monkeypatch.setattr(hygiene, "_load_leak_guard", lambda: leaks)
    clean = _sdist(tmp_path, _clean_sdist_members())
    dirty = _wheel(
        tmp_path, {"nltk/x.pyc": b"\x00", "nltk-9.9.9.dist-info/METADATA": b""}
    )
    assert hygiene.main([clean, dirty]) == 1
    out = capsys.readouterr().out
    assert "OK " + clean in out and "FAILED " + dirty in out and "x.pyc" in out
    assert hygiene.main([clean]) == 0
    assert hygiene.main([]) == 2
    assert hygiene.main([str(tmp_path / "notes.txt")]) == 1


@pytest.mark.skipif(
    not os.environ.get("NLTK_DIST_HYGIENE"),
    reason="set NLTK_DIST_HYGIENE=dist to check built archives",
)
def test_the_built_archives_are_clean(hygiene, capsys):
    """Run against real artifacts: NLTK_DIST_HYGIENE names the dist directory."""
    folder = Path(os.environ["NLTK_DIST_HYGIENE"])
    paths = sorted(str(p) for p in folder.iterdir() if p.suffix in {".gz", ".whl"})
    assert paths, folder
    assert hygiene.main(paths) == 0, capsys.readouterr().out

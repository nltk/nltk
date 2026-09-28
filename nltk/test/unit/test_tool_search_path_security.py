# Natural Language Toolkit: tool search-path hardening tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""GHSA-cc5r-64rf-75hg (CWE-426 / CWE-427): the tool config entry points
(prover9/mace4, megam, tadm, java, hunpos) accept only an absolute binary
location without a parent-directory component.

A relative location resolves against the current working directory, and one
joined onto a trusted directory can climb back out of it through "..", so a
planted binary in the CWD would be what the tool spawns. On POSIX the trusted
spawn also refuses relative and ".." targets, but it runs any normalised
absolute file the current user owns in a private directory chain (a binary in
the user's own checkout is exactly that), and on Windows its best-effort
resolver accepts even the relative form; so the config-time refusal is the
guard, and these tests pin it, its teeth, and the benign paths it must keep
working: an absolute argument, an absolute env var, and a PATH lookup.
"""

import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from nltk import internals, pathsec
from nltk.test.unit.security_probes._base import register_data_root

TOOL_ENV = {
    "prover9": ["PROVER9"],
    "megam": ["MEGAM"],
    "tadm": ["TADM"],
    "java": ["JAVAHOME", "JAVA_HOME"],
    "hunpos-tag": ["HUNPOS_TAGGER"],
}
# the wrappers that take a directory (Senna, Boxer); the CI sets SENNA to a real
# Linux install, so the box clears these too, or a relative form would be
# rescued by the env fallback instead of being judged on its own
DIR_TOOL_ENV = ["SENNA", "CANDC"]
ALL_ENV_VARS = [var for vars_ in TOOL_ENV.values() for var in vars_] + DIR_TOOL_ENV
NUL = chr(0)


class _Spawned(Exception):
    """Raised in place of the hunpos spawn, carrying the binary it was given."""


class _LyingStr(str):
    """A location whose string methods lie. ``posixpath.isabs`` asks
    ``startswith``; ``ntpath.isabs`` slices and replaces first; a NUL check asks
    ``in``. Every one of them is answered with a lie."""

    def startswith(self, *args, **kwargs):
        return True

    def replace(self, *args, **kwargs):
        return self

    def __getitem__(self, key):
        return self

    def __contains__(self, item):
        return False


class _Flipping(os.PathLike):
    """A location whose ``__fspath__`` answers differently on each call: what a
    guard checks must be what the spawn runs, so it may be read only once."""

    def __init__(self, *answers):
        self.answers, self.calls = list(answers), 0

    def __fspath__(self):
        self.calls += 1
        return self.answers[min(self.calls, len(self.answers)) - 1]


def _bytes_whose_decode_answers(real, answer):
    """A ``bytes`` location whose ``decode()`` answers *answer* instead of its
    real bytes; ``os.fsdecode`` would have taken that answer."""
    return type("_LyingBytes", (bytes,), {"decode": lambda self, *a, **k: answer})(real)


def _exec_file(directory, name, marker="PWNED"):
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"#!/bin/sh\necho {marker}\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


def _relative_forms(name, box):
    forms = [
        ".",
        "./",
        f"./{name}",
        f"sub/{name}",
        "sub",
        "sub/",
        f"./sub/../{name}",
        f"../{os.path.basename(box)}/{name}",
    ]
    if os.name == "nt":
        forms += [
            f".\\{name}",
            f"sub\\{name}",
            f"..\\{os.path.basename(box)}\\{name}",
        ]
    return forms


def _odd_forms(name):
    """Relative locations that are not plain strings, or carry a NUL byte."""
    relative = f"./{name}"
    return [
        _LyingStr(relative),
        _LyingStr(relative + NUL),
        Path(relative),
        relative.encode(),
        relative + NUL,
        relative + "\n",
        relative + "\r",
        "./" + "a" * 5000 + "/" + name,
    ]


def _escape_form(name, box):
    """The relative form that, rebased onto a trusted directory, climbs back
    out of it into the CWD decoy."""
    return f"../{os.path.basename(box)}/{name}"


def _exe(name):
    """The file name a PATH lookup finds on this platform (PATHEXT on Windows)."""
    return name + ".exe" if os.name == "nt" else name


def _scrubbed_path(directory):
    """A PATH holding no tool at all (the finder walks PATH itself and needs no
    ``which``); ``which`` is linked in only so a test that shells out to it
    for a control comparison still can."""
    real_which = shutil.which("which")
    if os.name == "posix" and real_which:
        os.symlink(real_which, os.path.join(directory, "which"))
    return str(directory)


def _same(a, b):
    return os.path.realpath(str(a)) == os.path.realpath(str(b))


def _inside(path, directory):
    real, root = os.path.realpath(str(path)), os.path.realpath(str(directory))
    return real == root or real.startswith(root + os.sep)


def _entry_points():
    """(label, binary name, configure(location) -> resolved binary path) for the
    four entry points that resolve without side effects; java and hunpos have
    their own tests below because they keep global state or spawn."""
    from nltk.classify import megam, tadm
    from nltk.inference.mace import Mace
    from nltk.inference.prover9 import Prover9

    def prover9(location):
        tool = Prover9()
        tool.config_prover9(location)
        return tool._prover9_bin

    def mace(location):
        tool = Mace()
        tool.config_prover9(location)
        return tool._prover9_bin

    def megam_config(location):
        megam.config_megam(location)
        return megam._megam_bin

    def tadm_config(location):
        tadm.config_tadm(location)
        return tadm._tadm_bin

    return [
        ("Prover9.config_prover9", "prover9", prover9),
        ("Mace.config_prover9", "prover9", mace),
        ("config_megam", "megam", megam_config),
        ("config_tadm", "tadm", tadm_config),
    ]


ENTRY_POINTS = _entry_points()


def _hunpos(monkeypatch, model, location):
    """Construct a HunposTagger with the spawn captured: returns the binary it
    was about to run, or raises what the constructor raised before that."""
    import nltk.tag.hunpos as hunpos_module

    def _record(target, *args, **kwargs):
        raise _Spawned(target)

    monkeypatch.setattr(hunpos_module, "spawn_trusted", _record)
    try:
        hunpos_module.HunposTagger(model, path_to_bin=location)
    except _Spawned as spawned:
        return spawned.args[0]
    raise AssertionError("HunposTagger returned without spawning")


def _refused_or_install(configure, form, install_binary, box):
    """The rule for a relative form once a trusted install is configured: it is
    refused, or it resolves to that install; it never resolves into the CWD."""
    try:
        got = configure(form)
    except LookupError:
        return "refused"
    assert not _inside(got, box), (form, got)
    assert _same(got, install_binary), (form, got)
    return "install"


@pytest.fixture(autouse=True)
def _reset_tool_globals(monkeypatch):
    from nltk.classify import megam, tadm

    monkeypatch.setattr(megam, "_megam_bin", None)
    monkeypatch.setattr(tadm, "_tadm_bin", None)
    monkeypatch.setattr(internals, "_java_bin", None)


@pytest.fixture
def box(tmp_path, monkeypatch):
    """A CWD holding planted decoys for every tool, with no tool reachable through
    the environment: the tool env vars are unset and PATH holds only ``which``."""
    cwd = tmp_path / "cwd"
    empty = tmp_path / "empty"
    cwd.mkdir()
    empty.mkdir()
    scrubbed = _scrubbed_path(empty)
    for name in TOOL_ENV:
        _exec_file(cwd, name)
        _exec_file(cwd / "sub", name)
    for var in ALL_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PATH", scrubbed)
    monkeypatch.chdir(cwd)
    return cwd


@pytest.fixture
def install(box, tmp_path, monkeypatch):
    """A trusted install next to the box, configured through every tool's env
    var, so the decoys in the CWD compete with a real location."""
    trusted = tmp_path / "trusted"
    for name, vars_ in TOOL_ENV.items():
        _exec_file(trusted, name)
        for var in vars_:
            monkeypatch.setenv(var, str(trusted))
    return trusted


@pytest.fixture
def home_install(monkeypatch):
    """A trusted install under $HOME, registered as a data root: hunpos validates
    its model as private and in-sandbox, which a shared temp dir is not."""
    root = Path(tempfile.mkdtemp(prefix=".nltk_cc5r_install_", dir=Path.home()))
    for name in TOOL_ENV:
        _exec_file(root, name)
    (root / "en_wsj.model").write_text("stub\n", encoding="utf-8")
    undo = register_data_root(str(root))
    try:
        yield root
    finally:
        undo()
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def private_dir():
    """A directory under $HOME for a binary the trusted spawn must accept: a
    private chain on every CI runner, which a shared /tmp (mode 1777) is not."""
    root = Path(tempfile.mkdtemp(prefix=".nltk_cc5r_private_", dir=Path.home()))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


class TestFindBinaryAbsolute:
    def test_every_relative_form_is_refused(self, box):
        for name, vars_ in TOOL_ENV.items():
            for form in _relative_forms(name, box) + _odd_forms(name):
                with pytest.raises(LookupError):
                    internals.find_binary_absolute(
                        name, path_to_bin=form, env_vars=vars_, binary_names=[name]
                    )

    def test_raw_finder_surfaces_a_decoy_for_every_form(self, box):
        # teeth: each form really reaches a CWD decoy through the underlying
        # finder, so the absolute-only filter is what refuses it
        for name in TOOL_ENV:
            for form in _relative_forms(name, box):
                hits = list(internals.find_file_iter(form, (), (), [name]))
                assert hits, (name, form)
                assert all(not os.path.isabs(h) for h in hits), (name, form, hits)

    def test_plain_find_binary_honours_an_explicit_relative_path(self, box):
        # the pre-fix behaviour the entry points used to inherit
        for name, vars_ in TOOL_ENV.items():
            for form in (f"./{name}", f"sub/{name}"):
                got = internals.find_binary(
                    name, path_to_bin=form, env_vars=vars_, binary_names=[name]
                )
                assert not os.path.isabs(got)
                assert _inside(got, box)

    def test_missing_absolute_location_does_not_fall_back_to_a_decoy(self, box):
        # a misconfigured absolute path must fail, not silently pick the CWD decoy
        # the finder also surfaces (plain find_binary does exactly that)
        for name, vars_ in TOOL_ENV.items():
            missing = os.path.join(os.path.realpath(str(box)), "nowhere", name)
            assert not os.path.exists(missing)
            fallback = internals.find_binary(
                name, path_to_bin=missing, env_vars=vars_, binary_names=[name]
            )
            assert not os.path.isabs(fallback)  # teeth: the old path leaked the decoy
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    name, path_to_bin=missing, env_vars=vars_, binary_names=[name]
                )

    def test_parent_component_escape_from_a_trusted_directory_is_refused(
        self, box, install
    ):
        # "../cwd/<name>" joined onto the env var directory is absolute and IS the
        # CWD decoy: the raw iterator yields it (teeth), the guard refuses it
        for name, vars_ in TOOL_ENV.items():
            escape = _escape_form(name, box)
            candidates = list(
                internals.find_binary_iter(name, path_to_bin=escape, env_vars=vars_)
            )
            assert any(os.path.isabs(c) and _inside(c, box) for c in candidates), (
                name,
                candidates,
            )
            with pytest.raises(LookupError):
                internals.find_binary_absolute(name, path_to_bin=escape, env_vars=vars_)
            # with the bare name also searched, the install is found instead;
            # the decoy is never the answer
            got = internals.find_binary_absolute(
                name, path_to_bin=escape, env_vars=vars_, binary_names=[name]
            )
            assert not _inside(got, box) and _same(got, str(install / name)), name

    def test_an_absolute_argument_with_a_parent_component_is_refused(
        self, box, tmp_path
    ):
        good = _exec_file(tmp_path / "trusted", "prover9")
        dotted = os.path.join(os.path.dirname(good), "..", "trusted", "prover9")
        assert os.path.isfile(dotted)
        with pytest.raises(LookupError):
            internals.find_binary_absolute(
                "prover9", path_to_bin=dotted, binary_names=["prover9"]
            )

    def test_env_var_climbing_through_parent_into_the_cwd_is_refused(
        self, box, install, monkeypatch
    ):
        # the env var itself points through ".." at the decoy directory
        through = os.path.join(str(install), os.pardir, os.path.basename(str(box)))
        assert os.path.isfile(os.path.join(through, "prover9"))
        for name, vars_ in TOOL_ENV.items():
            for var in vars_:  # every variable of the tool, or java falls back
                monkeypatch.setenv(var, through)
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    name, env_vars=vars_, binary_names=[name]
                )
            for form in _relative_forms(name, box):
                try:
                    got = internals.find_binary_absolute(
                        name, path_to_bin=form, env_vars=vars_, binary_names=[name]
                    )
                except LookupError:
                    continue
                assert not _inside(got, box), (name, form, got)

    def test_relative_forms_never_win_once_an_install_is_configured(self, box, install):
        for name, vars_ in TOOL_ENV.items():
            outcomes = set()
            for form in _relative_forms(name, box):

                def configure(location, name=name, vars_=vars_):
                    return internals.find_binary_absolute(
                        name, path_to_bin=location, env_vars=vars_, binary_names=[name]
                    )

                outcomes.add(
                    _refused_or_install(configure, form, str(install / name), box)
                )
            # "./<name>" rebases cleanly onto the install, so it must resolve
            assert _same(configure(f"./{name}"), str(install / name)), name
            assert "install" in outcomes, name

    def test_nul_byte_is_refused_cleanly(self, box, tmp_path):
        # NUL truncates the path in native calls; a LookupError, never a
        # ValueError from the filesystem layer, and never a resolution
        good = _exec_file(tmp_path / "trusted", "prover9")
        for location in ("./prover9" + NUL, good + NUL, NUL + good):
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=location, binary_names=["prover9"]
                )

    def test_pathlike_and_bytes_locations(self, box, tmp_path):
        # a path-like or bytes location is honoured when absolute and refused
        # when relative, exactly like a str, and the result is a plain str
        good = _exec_file(tmp_path / "trusted", "prover9")
        for location in (Path(good), os.fsencode(good)):
            found = internals.find_binary_absolute(
                "prover9", path_to_bin=location, binary_names=["prover9"]
            )
            assert type(found) is str and _same(found, good), location
        for location in (Path("./prover9"), b"./prover9", Path("sub/prover9")):
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=location, binary_names=["prover9"]
                )

    def test_non_path_location_is_a_clean_refusal(self, box):
        for location in (3.14, ["./prover9"], object()):
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=location, binary_names=["prover9"]
                )

    def test_lying_str_subclass_cannot_fake_an_absolute_path(self, box, tmp_path):
        # teeth: os.path.isabs believes the object on every platform, and a
        # naive NUL check would too; the guard must consult only a plain copy
        lying = _LyingStr("./prover9")
        assert os.path.isabs(lying)
        with pytest.raises(LookupError):
            internals.find_binary_absolute(
                "prover9", path_to_bin=lying, binary_names=["prover9"]
            )
        hidden_nul = _LyingStr("./prover9" + NUL)
        assert NUL not in hidden_nul and NUL in str.__str__(hidden_nul)
        with pytest.raises(LookupError):
            internals.find_binary_absolute(
                "prover9", path_to_bin=hidden_nul, binary_names=["prover9"]
            )
        # and an honest absolute location wrapped in the subclass is honoured
        # as a plain str, so nothing downstream consults the subclass either
        good = _exec_file(tmp_path / "trusted", "prover9")
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=_LyingStr(good), binary_names=["prover9"]
        )
        assert type(found) is str and _same(found, good)

    def test_absolute_file_and_directory_locations_are_honoured(self, box, tmp_path):
        good = _exec_file(tmp_path / "trusted", "prover9")
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=good, binary_names=["prover9"]
        )
        assert _same(found, good)
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=str(tmp_path / "trusted"), binary_names=["prover9"]
        )
        assert _same(found, good)

    def test_absolute_symlink_in_the_cwd_to_the_install_resolves_to_the_install(
        self, box, install
    ):
        # an absolute link is the caller's explicit choice; the spawn layer
        # follows every hop and judges each directory on the way
        link = box / "link"
        os.symlink(str(install / "prover9"), str(link))
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=str(link), binary_names=["prover9"]
        )
        assert _same(found, str(install / "prover9"))

    def test_absolute_env_var_alone_is_honoured(self, box, install):
        for name, vars_ in TOOL_ENV.items():
            got = internals.find_binary_absolute(
                name, env_vars=vars_, binary_names=[name]
            )
            assert _same(got, str(install / name)), name

    def test_mixed_env_entries_resolve_to_the_absolute_one(
        self, box, install, monkeypatch
    ):
        for name, vars_ in TOOL_ENV.items():
            for value in (f".{os.pathsep}{install}", f"{install}{os.pathsep}."):
                monkeypatch.setenv(vars_[0], value)
                got = internals.find_binary_absolute(
                    name, env_vars=vars_, binary_names=[name]
                )
                assert _same(got, str(install / name)), (name, value)

    def test_relative_env_var_is_refused(self, box, monkeypatch):
        for name, vars_ in TOOL_ENV.items():
            for value in (".", "sub", "./sub", f"sub{os.pathsep}.", f"./{name}"):
                monkeypatch.setenv(vars_[0], value)
                with pytest.raises(LookupError):
                    internals.find_binary_absolute(
                        name, env_vars=vars_, binary_names=[name]
                    )

    def test_relative_and_escaping_searchpath_entries_are_refused(self, box, install):
        through = os.path.join(str(install), os.pardir, os.path.basename(str(box)))
        for entry in (".", "sub", "./", through):
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", searchpath=[entry], binary_names=["prover9"]
                )
        found = internals.find_binary_absolute(
            "prover9", searchpath=[".", str(install)], binary_names=["prover9"]
        )
        assert _same(found, str(install / "prover9"))

    def test_cwd_entries_on_path_are_refused(self, box, tmp_path, monkeypatch):
        # "." or an empty entry makes which() answer with a CWD-relative hit;
        # which itself stays reachable through the scrubbed entry
        scrubbed = str(tmp_path / "empty")
        for entry in (".", "", "./sub"):
            monkeypatch.setenv("PATH", f"{entry}{os.pathsep}{scrubbed}")
            for name in TOOL_ENV:
                with pytest.raises(LookupError):
                    internals.find_binary_absolute(name, binary_names=[name])

    def test_absolute_path_entry_is_the_operators_choice(
        self, box, tmp_path, monkeypatch
    ):
        # PATH is where the operator installs tools: an absolute hit is honoured
        # on every platform and the spawn layer then judges who can write it
        good = _exec_file(tmp_path / "bin", _exe("megam"))
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        found = internals.find_binary_absolute("megam", binary_names=["megam"])
        assert _same(found, good)

    def test_an_unusable_path_is_not_found_rather_than_a_crash(
        self, box, tmp_path, monkeypatch
    ):
        # a PATH holding no tool, one whose entries do not exist or are files,
        # and an empty PATH must all end in the not-found error, never an OSError
        bare = tmp_path / "bare"
        bare.mkdir()
        (tmp_path / "afile").write_text("not a directory\n", encoding="utf-8")
        for path in (
            str(bare),
            str(tmp_path / "nowhere"),
            str(tmp_path / "afile"),
            os.pathsep.join([str(bare), "", str(tmp_path / "nowhere")]),
            "",
        ):
            monkeypatch.setenv("PATH", path)
            with pytest.raises(LookupError):
                internals.find_binary_absolute("prover9", binary_names=["prover9"])
            with pytest.raises(LookupError):
                internals.find_binary("prover9", binary_names=["prover9"])
        monkeypatch.delenv("PATH")
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])

    def test_the_finder_spawns_no_process(self, box, tmp_path, monkeypatch):
        # the PATH lookup is a directory walk: with Popen made to blow up, an
        # install on PATH is still found and an absent one still reported
        good = _exec_file(tmp_path / "bin", "prover9")
        monkeypatch.setenv("PATH", str(tmp_path / "bin"))

        def _boom(*args, **kwargs):
            raise AssertionError("the finder spawned a process")

        monkeypatch.setattr(subprocess, "Popen", _boom)
        found = internals.find_binary_absolute("prover9", binary_names=["prover9"])
        assert _same(found, good)
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])

    @pytest.mark.skipif(os.name != "posix", reason="POSIX executable bit")
    def test_a_non_executable_file_on_path_is_not_a_hit(
        self, box, tmp_path, monkeypatch
    ):
        plain = tmp_path / "bin" / "prover9"
        plain.parent.mkdir()
        plain.write_text("#!/bin/sh\necho PWNED\n", encoding="utf-8")
        plain.chmod(0o644)
        monkeypatch.setenv("PATH", str(tmp_path / "bin"))
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])
        plain.chmod(0o755)
        found = internals.find_binary_absolute("prover9", binary_names=["prover9"])
        assert _same(found, plain)

    def test_a_path_entry_climbing_into_the_cwd_is_refused(
        self, box, tmp_path, monkeypatch
    ):
        # PATH=<trusted>/../cwd: the walk yields the decoy behind an absolute
        # prefix (teeth), and the absolute-only resolver refuses the '..' in it
        (tmp_path / "trusted").mkdir()
        through = os.path.join(
            str(tmp_path / "trusted"), os.pardir, os.path.basename(str(box))
        )
        monkeypatch.setenv("PATH", through)
        hits = list(internals._path_dirs_iter(["prover9"]))
        assert hits and all(_inside(h, box) for h in hits), hits
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])

    def test_parent_component_is_refused_in_either_separator_style(self, box, tmp_path):
        # pathsec's shared rule: '..' is checked after folding backslashes, so
        # a location that would climb on Windows is refused on POSIX too (a
        # directory literally named "..\\odd" is not a tool install), while a
        # component that merely starts with ".." is an ordinary name
        for form in ("/a/../b", "/a/..\\b", "C:\\a\\..\\b", "C:/a/../b", "C:\\a/..\\b"):
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=form, binary_names=["prover9"]
                )
        good = _exec_file(tmp_path / "..x", "prover9")
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=good, binary_names=["prover9"]
        )
        assert _same(found, good)


class TestToolEntryPoints:
    def test_every_relative_form_is_refused(self, box):
        for label, name, configure in ENTRY_POINTS:
            for form in _relative_forms(name, box) + _odd_forms(name):
                with pytest.raises(LookupError):
                    configure(form)

    def test_missing_absolute_location_is_refused(self, box):
        for label, name, configure in ENTRY_POINTS:
            missing = os.path.join(os.path.realpath(str(box)), "nowhere", name)
            with pytest.raises(LookupError):
                configure(missing)

    def test_relative_forms_never_win_once_an_install_is_configured(self, box, install):
        for label, name, configure in ENTRY_POINTS:
            for form in _relative_forms(name, box):
                _refused_or_install(configure, form, str(install / name), box)
            assert _same(configure(f"./{name}"), str(install / name)), label
            # the escape form lands on the install through the bare-name search,
            # never on the decoy it was aimed at
            assert _same(configure(_escape_form(name, box)), str(install / name))

    def test_absolute_argument_is_honoured(self, box, tmp_path):
        trusted = tmp_path / "trusted"
        for label, name, configure in ENTRY_POINTS:
            good = _exec_file(trusted, name)
            assert _same(configure(good), good), label
            assert _same(configure(Path(good)), good), label

    def test_no_prior_state_leaks_between_calls(self, box, tmp_path, monkeypatch):
        # a refused relative location must not leave the previous binary configured
        from nltk.classify import megam
        from nltk.inference.prover9 import Prover9

        good = _exec_file(tmp_path / "trusted", "prover9")
        tool = Prover9()
        tool.config_prover9(good)
        with pytest.raises(LookupError):
            tool.config_prover9("./prover9")
        assert _same(tool._prover9_bin, good)
        good_megam = _exec_file(tmp_path / "trusted", "megam")
        megam.config_megam(good_megam)
        with pytest.raises(LookupError):
            megam.config_megam("sub/megam")
        assert _same(megam._megam_bin, good_megam)

    def test_prover9_helper_binaries_never_come_from_the_cwd(self, box, monkeypatch):
        # prooftrans, mace4 and interpformat resolve through the same helper,
        # and a relative entry in its search path is refused like any other
        from nltk.inference.mace import Mace
        from nltk.inference.prover9 import Prover9

        for name in ("prooftrans", "mace4", "interpformat"):
            _exec_file(box, name)
        with pytest.raises(LookupError):
            Prover9()._find_binary("prooftrans")
        with pytest.raises(LookupError):
            Mace()._find_binary("mace4")
        with pytest.raises(LookupError):
            Mace()._find_binary("interpformat")
        monkeypatch.setattr(Prover9, "binary_locations", lambda self: [".", "sub"])
        with pytest.raises(LookupError):
            Prover9()._find_binary("prooftrans")

    def test_mace_helper_uses_the_configured_prover9_directory(self, box, tmp_path):
        # config_prover9 stored the rsplit list as the directory, so the mace4,
        # prooftrans and interpformat lookups crashed with a TypeError afterwards
        from nltk.inference.mace import Mace
        from nltk.inference.prover9 import Prover9

        trusted = tmp_path / "trusted"
        for name in ("prover9", "mace4", "prooftrans", "interpformat"):
            _exec_file(trusted, name)
        tool = Mace()
        tool.config_prover9(str(trusted))
        assert tool._binary_location == os.path.normpath(str(trusted))
        assert _same(tool._find_binary("mace4"), str(trusted / "mace4"))
        assert _same(tool._find_binary("interpformat"), str(trusted / "interpformat"))
        prover = Prover9()
        prover.config_prover9(str(trusted / "prover9"))
        assert _same(prover._find_binary("prooftrans"), str(trusted / "prooftrans"))

    def test_resolved_path_is_normalised(self, box, install):
        # "./prover9" joined onto the env var directory must not come back as
        # "<install>/./prover9": no "." components, no doubled separators
        for name, vars_ in TOOL_ENV.items():
            got = internals.find_binary_absolute(
                name, path_to_bin=f"./{name}", env_vars=vars_, binary_names=[name]
            )
            assert got == os.path.normpath(got), got
            assert os.curdir not in got.replace(os.altsep or os.sep, os.sep).split(
                os.sep
            ), got


class TestConfigJava:
    def test_every_relative_form_is_refused(self, box):
        for form in _relative_forms("java", box) + _odd_forms("java"):
            with pytest.raises(LookupError):
                internals.config_java(form)
            assert internals._java_bin is None

    def test_absolute_argument_and_absolute_java_home_are_honoured(
        self, box, tmp_path, monkeypatch
    ):
        good = _exec_file(tmp_path / "jdk", "java")
        internals.config_java(good)
        assert _same(internals._java_bin, good)
        internals._java_bin = None
        internals.config_java(Path(good))
        assert type(internals._java_bin) is str and _same(internals._java_bin, good)
        internals._java_bin = None
        monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk"))
        internals.config_java()
        assert _same(internals._java_bin, good)

    def test_relative_forms_never_win_once_java_home_is_set(
        self, box, tmp_path, monkeypatch
    ):
        good = _exec_file(tmp_path / "jdk", "java")
        monkeypatch.setenv("JAVA_HOME", str(tmp_path / "jdk"))

        def configure(location):
            internals._java_bin = None
            internals.config_java(location)
            return internals._java_bin

        for form in _relative_forms("java", box):
            _refused_or_install(configure, form, good, box)
        assert _same(configure("./java"), good)
        with pytest.raises(LookupError):
            configure(_escape_form("java", box))

    def test_relative_java_home_is_refused(self, box, tmp_path, monkeypatch):
        _exec_file(tmp_path / "jdk", "java")
        escape = os.path.join(str(tmp_path / "jdk"), os.pardir, "cwd")
        for var in ("JAVAHOME", "JAVA_HOME"):
            for value in (".", "sub", "./sub", "./java", escape):
                monkeypatch.setenv(var, value)
                with pytest.raises(LookupError):
                    internals.config_java()
                monkeypatch.delenv(var)


class TestHunposTagger:
    def test_every_relative_form_is_refused_before_any_spawn(
        self, box, home_install, monkeypatch
    ):
        model = str(home_install / "en_wsj.model")
        for form in _relative_forms("hunpos-tag", box) + _odd_forms("hunpos-tag"):
            with pytest.raises(LookupError):
                _hunpos(monkeypatch, model, form)

    def test_absolute_binary_reaches_the_spawn(self, box, home_install, monkeypatch):
        model = str(home_install / "en_wsj.model")
        good = str(home_install / "hunpos-tag")
        assert _same(_hunpos(monkeypatch, model, good), good)
        assert _same(_hunpos(monkeypatch, model, Path(good)), good)

    def test_relative_forms_never_win_once_the_env_var_is_set(
        self, box, home_install, monkeypatch
    ):
        model = str(home_install / "en_wsj.model")
        good = str(home_install / "hunpos-tag")
        monkeypatch.setenv("HUNPOS_TAGGER", str(home_install))

        def configure(location):
            return _hunpos(monkeypatch, model, location)

        for form in _relative_forms("hunpos-tag", box):
            _refused_or_install(configure, form, good, box)
        assert _same(configure("./hunpos-tag"), good)
        with pytest.raises(LookupError):
            configure(_escape_form("hunpos-tag", box))


def test_spawn_layer_relative_target_per_platform(monkeypatch):
    """What the spawn layer does and does not stop, on each platform, staged
    under $HOME because a shared temp directory would be refused for its
    permissions. POSIX: the trust check refuses a relative target and a ".."
    target outright but trusts a normalised absolute file we own in a private
    chain, and _call() then runs it, so the resolver must never turn a relative
    location into such a path. Windows: the best-effort resolver accepts even
    the relative target, so the config-time refusal is the only layer there.
    Either way, with an install configured no relative form reaches the spawn."""
    from nltk.inference.prover9 import Prover9

    home_box = Path(tempfile.mkdtemp(prefix=".nltk_cc5r_", dir=Path.home()))
    trusted = Path(tempfile.mkdtemp(prefix=".nltk_cc5r_trusted_", dir=Path.home()))
    try:
        planted = _exec_file(home_box, "prover9")
        _exec_file(trusted, "prover9", marker="LEGIT")
        escaped = os.path.join(str(trusted), "..", home_box.name, "prover9")
        assert os.path.isfile(escaped)
        monkeypatch.chdir(home_box)
        if os.name == "posix":
            assert pathsec.resolve_trusted_executable("./prover9") is None
            assert pathsec.resolve_trusted_executable(escaped) is None
            assert pathsec.resolve_trusted_executable(planted)
            tool = Prover9()
            tool._prover9_bin = planted  # a normalised absolute path into the CWD
            stdout, returncode = tool._call("", tool._prover9_bin)
            assert returncode == 0 and "PWNED" in stdout
        else:
            accepted = pathsec.resolve_trusted_executable("./prover9")
            assert accepted and _inside(accepted, home_box)
        monkeypatch.setenv("PROVER9", str(trusted))
        for form in ("./prover9", escaped, f"../{home_box.name}/prover9"):
            tool = Prover9()
            tool.config_prover9(form)
            assert not _inside(tool._prover9_bin, home_box), (form, tool._prover9_bin)
            assert _same(tool._prover9_bin, str(trusted / "prover9")), form
        # and with no install configured they are refused outright
        monkeypatch.delenv("PROVER9")
        (trusted / "empty").mkdir()
        monkeypatch.setenv("PATH", _scrubbed_path(trusted / "empty"))
        for form in ("./prover9", escaped, f"../{home_box.name}/prover9"):
            with pytest.raises(LookupError):
                Prover9().config_prover9(form)
    finally:
        shutil.rmtree(home_box, ignore_errors=True)
        shutil.rmtree(trusted, ignore_errors=True)


def _senna_binary_name():
    from nltk.classify.senna import Senna

    return os.path.basename(Senna.executable(None, "x"))


class TestSenna:
    """Senna / SennaTagger take a directory and spawn <dir>/senna-<platform>."""

    def _decoys(self, box):
        name = _senna_binary_name()
        _exec_file(box, name)
        _exec_file(box / "sub", name)
        return name

    def test_relative_and_odd_forms_are_refused(self, box, monkeypatch):
        from nltk.classify.senna import Senna

        name = self._decoys(box)
        forms = _relative_forms(name, box) + _odd_forms(name)
        forms += [Path("."), _LyingStr("."), _LyingStr("./"), "." + NUL]
        for form in forms:
            with pytest.raises(LookupError):
                Senna(form, ["pos"])

    def test_parent_component_escape_is_refused(self, box, tmp_path, monkeypatch):
        from nltk.classify.senna import Senna

        name = self._decoys(box)
        trusted = tmp_path / "trusted"
        _exec_file(trusted, name)
        escape = os.path.join(str(trusted), os.pardir, os.path.basename(str(box)))
        assert os.path.isfile(os.path.join(escape, name))
        with pytest.raises(LookupError):
            Senna(escape, ["pos"])
        for value in (escape, ".", "./", "sub", "./" + name):
            monkeypatch.setenv("SENNA", value)
            with pytest.raises(LookupError):
                Senna(value, ["pos"])

    def test_absolute_install_and_env_var_are_honoured(
        self, box, tmp_path, monkeypatch
    ):
        from nltk.classify.senna import Senna

        name = self._decoys(box)
        trusted = tmp_path / "trusted"
        good = _exec_file(trusted, name)
        for location in (str(trusted), Path(trusted), _LyingStr(str(trusted))):
            tagger = Senna(location, ["pos"])
            assert type(tagger._path) is str and os.path.isabs(tagger._path)
            assert _same(tagger.executable(tagger._path), good), location
        monkeypatch.setenv("SENNA", str(trusted))
        tagger = Senna("./", ["pos"])  # a relative argument yields to the env var
        assert _same(tagger.executable(tagger._path), good)
        assert not _inside(tagger._path, box)


class TestBoxer:
    def _install(self, directory):
        for name in ("candc", "boxer"):
            _exec_file(directory, name)
        return directory

    def test_relative_and_odd_forms_are_refused(self, box, monkeypatch):
        from nltk.sem.boxer import Boxer

        monkeypatch.delenv("CANDC", raising=False)
        self._install(box)
        self._install(box / "sub")
        forms = [".", "./", "sub", "sub/", "./sub/../", Path("."), b".", _LyingStr(".")]
        forms += ["." + NUL, _LyingStr("." + NUL)]
        for form in forms:
            with pytest.raises(LookupError):
                Boxer(bin_dir=form)

    def test_parent_component_escape_is_refused(self, box, tmp_path, monkeypatch):
        from nltk.sem.boxer import Boxer

        monkeypatch.delenv("CANDC", raising=False)
        self._install(box)
        trusted = self._install(tmp_path / "trusted")
        escape = os.path.join(str(trusted), os.pardir, os.path.basename(str(box)))
        with pytest.raises(LookupError):
            Boxer(bin_dir=escape)
        monkeypatch.setenv("CANDC", escape)
        with pytest.raises(LookupError):
            Boxer()
        # with a trusted install in the env var, the escape argument yields to it
        monkeypatch.setenv("CANDC", str(trusted))
        tool = Boxer(bin_dir=escape)
        assert _same(tool._candc_bin, str(trusted / "candc"))
        assert _same(tool._boxer_bin, str(trusted / "boxer"))

    def test_absolute_install_is_honoured(self, box, tmp_path, monkeypatch):
        from nltk.sem.boxer import Boxer

        monkeypatch.delenv("CANDC", raising=False)
        trusted = self._install(tmp_path / "trusted")
        for location in (str(trusted), Path(trusted)):
            tool = Boxer(bin_dir=location)
            assert _same(tool._candc_bin, str(trusted / "candc"))
            assert _same(tool._boxer_bin, str(trusted / "boxer"))


class TestRepp:
    def _install(self, directory):
        _exec_file(directory / "src", "repp")
        (directory / "erg").mkdir(parents=True, exist_ok=True)
        (directory / "erg" / "repp.set").write_text("", encoding="utf-8")
        return directory

    def test_relative_odd_and_escape_forms_are_refused(
        self, box, tmp_path, monkeypatch
    ):
        from nltk.tokenize.repp import ReppTokenizer

        monkeypatch.delenv("REPP_TOKENIZER", raising=False)
        self._install(box)
        self._install(box / "sub")
        trusted = self._install(tmp_path / "trusted")
        escape = os.path.join(str(trusted), os.pardir, os.path.basename(str(box)))
        forms = [".", "./", "sub", "sub/", escape, Path("."), b".", _LyingStr(".")]
        forms += [str(trusted) + NUL, _LyingStr(str(trusted) + NUL)]
        for form in forms:
            with pytest.raises(LookupError):
                ReppTokenizer(form)
        for value in (escape, ".", "sub"):
            monkeypatch.setenv("REPP_TOKENIZER", value)
            with pytest.raises(LookupError):
                ReppTokenizer("repp")

    def test_missing_binary_is_a_lookup_error_not_an_assertion(
        self, box, tmp_path, monkeypatch
    ):
        # the checks used to be assert statements, which python -O strips
        from nltk.tokenize.repp import ReppTokenizer

        monkeypatch.delenv("REPP_TOKENIZER", raising=False)
        empty = tmp_path / "trusted"
        empty.mkdir()
        with pytest.raises(LookupError):
            ReppTokenizer(str(empty))
        _exec_file(empty / "src", "repp")  # binary but no erg/repp.set
        with pytest.raises(LookupError):
            ReppTokenizer(str(empty))

    def test_absolute_install_and_env_var_are_honoured(
        self, box, tmp_path, monkeypatch
    ):
        from nltk.tokenize.repp import ReppTokenizer

        monkeypatch.delenv("REPP_TOKENIZER", raising=False)
        trusted = self._install(tmp_path / "trusted")
        for location in (str(trusted), Path(trusted), _LyingStr(str(trusted))):
            tokenizer = ReppTokenizer(location)
            assert type(tokenizer.repp_dir) is str and _same(
                tokenizer.repp_dir, str(trusted)
            )
        monkeypatch.setenv("REPP_TOKENIZER", str(trusted))
        assert _same(ReppTokenizer("repp").repp_dir, str(trusted))


class TestDot:
    def test_dependencygraph_dot_goes_through_the_trusted_spawn(
        self, box, tmp_path, monkeypatch
    ):
        import nltk.parse.dependencygraph as dg

        _exec_file(box, _exe("dot"))  # CWD decoy
        good = _exec_file(tmp_path / "bin", _exe("dot"))
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        seen = {}

        def _record(target, args, **kwargs):
            seen["target"], seen["args"], seen["kwargs"] = target, list(args), kwargs
            raise _Spawned(target)

        monkeypatch.setattr(dg, "spawn_trusted", _record)
        # dot2img wraps the recorder's exception; the message pins that the
        # spawn was reached, not that the binary went unfound
        with pytest.raises(Exception, match="Cannot create image representation"):
            dg.dot2img("digraph { a -> b }", "svg")
        assert _same(seen["target"], good) and not _inside(seen["target"], box)
        assert seen["args"] == ["-Tsvg"] and not seen["kwargs"].get("shell")
        # a format string with shell metacharacters stays one argv item, no shell
        hostile = "svg; touch " + str(tmp_path / "pwned")
        with pytest.raises(Exception, match="Cannot create image representation"):
            dg.dot2img("digraph { a -> b }", hostile)
        assert seen["args"] == ["-T" + hostile] and not seen["kwargs"].get("shell")
        assert not (tmp_path / "pwned").exists()

    @pytest.mark.skipif(not shutil.which("dot"), reason="needs a real Graphviz dot")
    def test_real_dot_renders_through_the_trusted_spawn(self, tmp_path):
        import nltk.parse.dependencygraph as dg

        svg = dg.dot2img("digraph { a -> b }", "svg")
        assert "<svg" in svg and "</svg>" in svg
        png = dg.dot2img("digraph { a -> b }", "png")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"


class TestSvnRevision:
    def test_a_bare_svn_is_never_taken_from_the_cwd(self, box, tmp_path, monkeypatch):
        import nltk.downloader as downloader

        _exec_file(box, "svn")
        with pytest.raises(LookupError):
            downloader._svn_revision("index.xml")

    def test_an_absolute_svn_on_path_is_spawned_trusted(
        self, box, tmp_path, monkeypatch
    ):
        import nltk.downloader as downloader
        from nltk import pathsec

        _exec_file(box, _exe("svn"))
        good = _exec_file(tmp_path / "bin", _exe("svn"))
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        seen = {}

        def _record(target, args, **kwargs):
            seen["target"], seen["args"] = target, list(args)
            raise _Spawned(target)

        monkeypatch.setattr(pathsec, "spawn_trusted", _record)
        with pytest.raises(_Spawned):
            downloader._svn_revision("index.xml")
        assert _same(seen["target"], good) and not _inside(seen["target"], box)
        assert seen["args"] == ["status", "-v", "--", "index.xml"]

    def test_a_dash_prefixed_file_name_cannot_become_an_svn_option(
        self, box, tmp_path, monkeypatch
    ):
        import nltk.downloader as downloader
        from nltk import pathsec

        _exec_file(tmp_path / "bin", _exe("svn"))
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        seen = {}

        def _record(target, args, **kwargs):
            seen["args"] = list(args)
            raise _Spawned(target)

        monkeypatch.setattr(pathsec, "spawn_trusted", _record)
        hostile = "--config-option=servers:global:http-proxy-host=evil"
        with pytest.raises(_Spawned):
            downloader._svn_revision(hostile)
        assert seen["args"].index("--") < seen["args"].index(hostile)


class TestJavaSpawn:
    def test_trusted_java_is_executed_by_its_resolved_path(
        self, trusted_java_stub, monkeypatch
    ):
        monkeypatch.setattr(internals, "_java_bin", trusted_java_stub)
        monkeypatch.setattr(internals, "_java_options", [])
        seen = {}

        class _Proc:
            returncode = 0

            def communicate(self):
                return "", ""

        def _spy(cmd, *args, **kwargs):
            seen["cmd"], seen["kwargs"] = list(cmd), kwargs
            return _Proc()

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
        internals.java(["Main"])
        assert _same(seen["cmd"][0], trusted_java_stub)
        assert seen["kwargs"]["executable"] == seen["cmd"][0]
        assert not seen["kwargs"].get("shell") and "env" in seen["kwargs"]
        assert "JAVA_TOOL_OPTIONS" not in seen["kwargs"]["env"]

    def test_untrusted_java_binary_is_refused_at_spawn(self, box, monkeypatch):
        # set directly, bypassing config_java: the spawn-time check still stands
        _exec_file(box, "java")
        monkeypatch.setattr(internals, "_java_bin", "./java")
        monkeypatch.setattr(internals, "_java_options", [])
        if os.name == "posix":
            with pytest.raises(LookupError):
                internals.java(["Main"])
        else:  # the best-effort resolver accepts it; config_java is the guard there
            seen = {}

            def _spy(cmd, *args, **kwargs):
                seen["cmd"] = list(cmd)
                raise _Spawned(cmd[0])

            monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
            with pytest.raises((LookupError, _Spawned, OSError)):
                internals.java(["Main"])

    def test_unconfigured_java_is_resolved_absolute_before_spawn(
        self, box, private_dir, monkeypatch
    ):
        # nobody called config_java(): the JVM must still be resolved through
        # the absolute-only finder, never spawned as the bare name "java"; the
        # install lives under $HOME because the spawn then really runs the check
        _exec_file(box, _exe("java"))
        jdk = private_dir / "jdk"
        good = _exec_file(jdk, _exe("java"))
        os.chmod(jdk, 0o755)
        monkeypatch.setenv("JAVA_HOME", str(jdk))
        monkeypatch.setattr(internals, "_java_bin", None)
        monkeypatch.setattr(internals, "_java_options", [])
        seen = {}

        class _Proc:
            returncode = 0

            def communicate(self):
                return "", ""

        real_popen = subprocess.Popen

        def _spy(cmd, *args, **kwargs):
            if cmd[0] == "which":  # the finder's own PATH lookup, not the JVM
                return real_popen(cmd, *args, **kwargs)
            seen["cmd"] = list(cmd)
            return _Proc()

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
        internals.java(["Main"])
        assert seen["cmd"][0] != "java" and _same(seen["cmd"][0], good)
        assert not _inside(seen["cmd"][0], box)

    def test_unconfigured_java_with_nothing_reachable_is_refused(
        self, box, monkeypatch
    ):
        _exec_file(box, _exe("java"))
        monkeypatch.setattr(internals, "_java_bin", None)
        monkeypatch.setattr(internals, "_java_options", [])
        spawned = []
        real_popen = subprocess.Popen

        def _spy(cmd, *args, **kwargs):
            if cmd[0] == "which":
                return real_popen(cmd, *args, **kwargs)
            spawned.append(list(cmd))
            raise _Spawned(cmd[0])

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
        with pytest.raises(LookupError):
            internals.java(["Main"])
        assert spawned == []

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_java_in_a_group_writable_directory_is_refused(self, monkeypatch):
        root = Path(tempfile.mkdtemp(prefix=".nltk_java_gw_", dir=Path.home()))
        try:
            stub = _exec_file(root, "java")
            os.chmod(root, 0o775)
            monkeypatch.setattr(internals, "_java_bin", stub)
            monkeypatch.setattr(internals, "_java_options", [])
            with pytest.raises(LookupError):
                internals.java(["Main"])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_java_in_a_world_writable_tree_is_refused_however_configured(
        self, box, private_dir, monkeypatch
    ):
        # the GitHub Ubuntu image's JVM: every directory and the binary itself
        # are mode 777, so any local user can swap it; config_java() accepts
        # the absolute location, the launch is what must refuse it
        jdk = private_dir / "jdk"
        stub = _exec_file(jdk / "bin", "java")
        for path in (jdk, jdk / "bin", stub):
            os.chmod(path, 0o777)
        monkeypatch.setenv("JAVA_HOME", str(jdk))
        internals.config_java()
        assert _same(internals._java_bin, stub)
        monkeypatch.setattr(internals, "_java_options", [])
        seen = {}

        class _Proc:
            returncode = 0

            def communicate(self):
                return "", ""

        def _spy(cmd, *args, **kwargs):
            seen["cmd"] = list(cmd)
            return _Proc()

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)

        def refused():
            with pytest.raises(LookupError, match="not on a trusted path"):
                internals.java(["Main"])
            assert seen == {}

        refused()
        # a private leaf below a world-writable ancestor is no better
        os.chmod(jdk / "bin", 0o755)
        os.chmod(stub, 0o755)
        refused()
        # nor a private chain ending in a group- or world-writable binary
        os.chmod(jdk, 0o755)
        for mode in (0o775, 0o757, 0o777):
            os.chmod(stub, mode)
            refused()
        # private again, the same chain is accepted: the refusals above were
        # the ownership check, not a broken configuration
        os.chmod(stub, 0o755)
        internals.java(["Main"])
        assert _same(seen["cmd"][0], stub)

    @pytest.mark.skipif(os.name != "posix", reason="POSIX symlink chain check")
    def test_java_reached_through_a_writable_directory_link_is_refused(
        self, private_dir, monkeypatch
    ):
        # a link held in a world-writable directory, and a private link out into
        # a world-writable directory: either hop lets another user swap what
        # runs, so both are refused; a private-to-private link is accepted
        real = _exec_file(private_dir / "priv", "java")
        shared = private_dir / "shared"
        shared.mkdir()
        planted = _exec_file(shared, "java")
        os.chmod(shared, 0o777)
        links = private_dir / "links"
        links.mkdir()
        os.symlink(real, shared / "java_link")
        os.symlink(planted, links / "java_out")
        os.symlink(real, links / "java_in")
        monkeypatch.setattr(internals, "_java_options", [])
        seen = {}

        def _spy(cmd, *args, **kwargs):
            seen["cmd"], seen["kwargs"] = list(cmd), kwargs
            raise _Spawned(cmd[0])

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
        for target in (shared / "java_link", links / "java_out", planted):
            monkeypatch.setattr(internals, "_java_bin", str(target))
            with pytest.raises(LookupError, match="not on a trusted path"):
                internals.java(["Main"])
            assert seen == {}, target
        monkeypatch.setattr(internals, "_java_bin", str(links / "java_in"))
        with pytest.raises(_Spawned):
            internals.java(["Main"])
        # the resolved binary is what runs, by its real path, not the link
        assert _same(seen["cmd"][0], real) and not os.path.islink(seen["cmd"][0])
        assert seen["kwargs"]["executable"] == seen["cmd"][0]


class TestTrustedJavaStubFixture:
    """The conftest ``trusted_java_stub`` fixture plants an executable under
    $HOME so the trusted spawn accepts it in place of a JVM. That must not be a
    way of getting a binary trusted: the acceptance rests on the private chain
    the fixture builds and on nothing else, the stub is reachable only through
    an explicit pointer, it runs under the sanitised launcher environment, and
    nothing of it survives the test that used it."""

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_stub_is_a_regular_file_we_own_in_a_private_directory(
        self, trusted_java_stub
    ):
        stub = Path(trusted_java_stub)
        dir_st, st = stub.parent.stat(), stub.lstat()
        assert stat.S_ISDIR(dir_st.st_mode) and stat.S_IMODE(dir_st.st_mode) == 0o700
        assert dir_st.st_uid == os.geteuid() == st.st_uid
        assert stat.S_ISREG(st.st_mode)
        assert not st.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
        assert _same(pathsec.resolve_trusted_executable(trusted_java_stub), stub)

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_every_weakening_of_the_stub_chain_is_refused(
        self, trusted_java_stub, monkeypatch
    ):
        stub = Path(trusted_java_stub)
        root = stub.parent
        monkeypatch.setattr(internals, "_java_bin", trusted_java_stub)
        monkeypatch.setattr(internals, "_java_options", [])
        spawned = []

        def _spy(cmd, *args, **kwargs):
            spawned.append(list(cmd))
            raise _Spawned(cmd[0])

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)

        def refused(what):
            assert pathsec.resolve_trusted_executable(trusted_java_stub) is None, what
            with pytest.raises(LookupError, match="not on a trusted path"):
                internals.java(["Main"])
            assert spawned == [], what

        for mode in (0o775, 0o757, 0o777):  # the stub writable by others
            os.chmod(stub, mode)
            refused(f"stub mode {mode:o}")
        os.chmod(stub, 0o755)
        for mode in (0o770, 0o707, 0o777):  # its directory writable by others
            os.chmod(root, mode)
            refused(f"directory mode {mode:o}")
        os.chmod(root, 0o700)
        # not a regular file: a directory, a FIFO, a link out into a directory
        # that another user could write
        stub.unlink()
        stub.mkdir()
        refused("a directory")
        stub.rmdir()
        os.mkfifo(stub)
        refused("a FIFO")
        stub.unlink()
        shared = root / "shared"
        shared.mkdir()
        planted = _exec_file(shared, "java")
        os.chmod(shared, 0o777)
        os.symlink(planted, stub)
        refused("a link into a world-writable directory")
        stub.unlink()
        # restored, the same stub is accepted again: the refusals above were
        # the chain checks and nothing else
        stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        stub.chmod(0o755)
        assert _same(pathsec.resolve_trusted_executable(trusted_java_stub), stub)
        with pytest.raises(_Spawned):
            internals.java(["Main"])

    def test_stub_is_unreachable_without_an_explicit_pointer(
        self, box, trusted_java_stub, monkeypatch
    ):
        # it exists under $HOME, yet with no env var or PATH entry naming it the
        # finder cannot see it: a binary gets no trust from merely being there
        assert os.path.isfile(trusted_java_stub)
        with pytest.raises(LookupError):
            internals.config_java()
        assert internals._java_bin is None
        spawned = []
        real_popen = subprocess.Popen

        def _spy(cmd, *args, **kwargs):
            if cmd[0] == "which":  # the finder's own PATH lookup, not a launch
                return real_popen(cmd, *args, **kwargs)
            spawned.append(list(cmd))
            raise _Spawned(cmd[0])

        monkeypatch.setattr("nltk.pathsec.subprocess.Popen", _spy)
        with pytest.raises(LookupError):
            internals.java(["Main"])
        assert spawned == []
        # and its own location spelled relative to the CWD is refused as well
        try:
            relative = os.path.relpath(trusted_java_stub)
        except ValueError:  # Windows: the CWD and $HOME on different drives
            relative = None
        if relative is not None:
            with pytest.raises(LookupError):
                internals.config_java(relative)
            assert internals._java_bin is None

    @pytest.mark.skipif(os.name != "posix", reason="runs the stub as a script")
    def test_stub_runs_under_the_sanitised_launcher_environment(
        self, trusted_java_stub, monkeypatch
    ):
        # executed for real: what the stub sees is what a JVM would see
        report = Path(trusted_java_stub).parent / "env.txt"
        Path(trusted_java_stub).write_text(
            "#!/bin/sh\n"
            '{ echo "LD_PRELOAD=[$LD_PRELOAD]"; echo "DYLD=[$DYLD_INSERT_LIBRARIES]"; '
            'echo "JTO=[$JAVA_TOOL_OPTIONS]"; echo "CLASSPATH=[$CLASSPATH]"; '
            'echo "LANG=[$LANG]"; echo "KEEP=[$NLTK_KEEP]"; } > "$1"\n',
            encoding="utf-8",
        )
        planted = {
            "LD_PRELOAD": "/evil.so",
            "DYLD_INSERT_LIBRARIES": "/evil.dylib",
            "JAVA_TOOL_OPTIONS": "-XX:OnError=id",
            "CLASSPATH": "/evil",
            "LANG": "C.UTF-8",
            "NLTK_KEEP": "1",
        }
        for var, value in planted.items():
            monkeypatch.setenv(var, value)
        monkeypatch.setattr(internals, "_java_bin", trusted_java_stub)
        monkeypatch.setattr(internals, "_java_options", [])
        internals.java([str(report)])
        reported = report.read_text(encoding="utf-8")
        for line in ("LD_PRELOAD=[]", "DYLD=[]", "JTO=[]", "CLASSPATH=[]"):
            assert line in reported, reported
        assert "LANG=[C.UTF-8]" in reported and "KEEP=[1]" in reported, reported

    def test_fixture_leaves_nothing_behind(self, tmp_path):
        # a fresh pytest runs one test through the fixture and records the stub
        # it was handed; afterwards neither the stub nor its directory exists,
        # so no planted executable outlives its test under $HOME
        import nltk

        marker = tmp_path / "stub_path.txt"
        (tmp_path / "test_uses_the_stub.py").write_text(
            "import os\n\n\n"
            "def test_it(trusted_java_stub):\n"
            "    assert os.path.isfile(trusted_java_stub)\n"
            f"    with open({str(marker)!r}, 'w') as fh:\n"
            "        fh.write(trusted_java_stub)\n",
            encoding="utf-8",
        )
        repo = os.path.dirname(os.path.dirname(os.path.abspath(nltk.__file__)))
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "-p",
                "nltk.test.unit.conftest",
                str(tmp_path / "test_uses_the_stub.py"),
            ],
            cwd=str(tmp_path),
            env=dict(os.environ, PYTHONPATH=repo),
            capture_output=True,
            text=True,
            timeout=600,
        )
        assert proc.returncode == 0, proc.stdout + proc.stderr
        stub = marker.read_text(encoding="utf-8").strip()
        assert _inside(stub, Path.home())
        assert not os.path.lexists(stub)
        assert not os.path.lexists(os.path.dirname(stub))


class TestPathDirsWalk:
    """The PATH lookup find_file_iter makes where it cannot shell out to
    ``which`` (Windows): every PATH directory in order, never the implicit
    current directory, and never stopping at a planted hit."""

    def test_cwd_is_not_consulted_and_every_path_hit_is_yielded(
        self, box, tmp_path, monkeypatch
    ):
        _exec_file(box, "svn.exe")  # the planted decoy in the CWD
        first, second = tmp_path / "first", tmp_path / "second"
        _exec_file(first, "svn.exe")
        _exec_file(second, "svn")
        _exec_file(second, "svn.exe")
        monkeypatch.setenv("PATHEXT", os.pathsep.join([".com", ".exe"]))
        monkeypatch.setenv(
            "PATH", os.pathsep.join([str(tmp_path / "empty"), str(first), str(second)])
        )
        got = list(internals._path_dirs_iter(["svn"]))
        assert [os.path.realpath(p) for p in got] == [
            os.path.realpath(p)
            for p in (first / "svn.exe", second / "svn", second / "svn.exe")
        ]
        assert all(os.path.isabs(p) and not _inside(p, box) for p in got)
        # a name with an extension is looked up as given, without PATHEXT
        assert list(internals._path_dirs_iter(["svn.exe"])) == [
            str(first / "svn.exe"),
            str(second / "svn.exe"),
        ]

    def test_a_relative_path_entry_is_yielded_relative_and_refused_upstream(
        self, box, tmp_path, monkeypatch
    ):
        _exec_file(box, "svn.exe")
        good = _exec_file(tmp_path / "bin", "svn.exe")
        monkeypatch.setenv("PATHEXT", ".exe")
        # a literal '.', an empty entry and a quoted entry
        monkeypatch.setenv("PATH", os.pathsep.join([".", "", f'"{tmp_path / "bin"}"']))
        assert list(internals._path_dirs_iter(["svn"])) == [
            os.path.join(os.curdir, "svn.exe"),
            str(tmp_path / "bin" / "svn.exe"),
        ]
        # the finder skips the relative hit and returns the install behind it,
        # instead of stopping at the CWD hit the way the OS search does
        found = internals.find_binary_absolute("svn", binary_names=["svn.exe"])
        assert _same(found, good) and not _inside(found, box)
        # with only the CWD hit reachable, the refusal names it
        monkeypatch.setenv("PATH", os.curdir)
        with pytest.raises(LookupError, match="only in the current working"):
            internals.find_binary_absolute("svn", binary_names=["svn.exe"])

    def test_a_name_with_a_directory_part_is_never_joined_onto_path(
        self, box, tmp_path, monkeypatch
    ):
        # "../cwd/svn.exe" joined onto a PATH entry next to the CWD would land
        # on the decoy as an absolute-looking path; a name with a directory
        # part is not a PATH lookup, so the walk yields nothing for it
        _exec_file(box, "svn.exe")
        monkeypatch.setenv("PATHEXT", ".exe")
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        escape = _escape_form("svn.exe", box)
        assert os.path.isfile(os.path.join(str(tmp_path / "empty"), escape))
        forms = [escape, os.path.join("sub", "svn.exe"), os.path.join(os.curdir, "svn")]
        assert list(internals._path_dirs_iter(forms)) == []
        # the raw finder surfaces such a form only as the relative decoy it names
        hits = list(internals.find_file_iter(escape, (), (), ["svn.exe"]))
        assert hits and all(not os.path.isabs(h) for h in hits), hits


class TestLocationSyntax:
    """Every absolute candidate the finder yields gets the name checks every
    model and tool path gets (pathsec's shared gate), and a tool directory is
    gated the same way. A location is only a search key: a hostile one never
    resolves by itself, it is refused with nothing reachable, and with an
    install configured it can only yield to that install, never to a decoy."""

    @staticmethod
    def _forms(name):
        forms = [
            f"-{name}",
            f"-/opt/{name}",
            f"http://evil.example/{name}",
            f"file:/opt/{name}",
            f"jar:/opt/{name}.jar!/x",
            f"~/{name}",
            f"sub\n/{name}",
            f"{name}\t",
            f"{os.sep}opt{os.sep}{name} ",
            f"{os.sep}opt{os.sep}{name}.",
            f"{os.sep}opt{os.sep}a\t{os.sep}{name}",
            f"{os.sep}opt{os.sep}a\n{os.sep}{name}",
            f"{os.sep}opt{os.sep}a\r{os.sep}{name}",
            f"{os.sep}opt{os.sep}a\x0b{os.sep}{name}",
            f"{os.sep}opt{os.sep}..{os.sep}{name}",
        ]
        if os.name == "posix":
            forms.append(f"//evil.example/share/{name}")
        else:
            forms += [
                f"\\\\evil.example\\share\\{name}",
                f"C:\\CON\\{name}",
                f"C:\\PROGRA~1\\{name}",
                f"C:{name}",
            ]
        return forms

    @staticmethod
    def _without(vars_):
        """Unset every one of a tool's variables (java has two; one left set
        would still resolve the install) and return an undo callable."""
        saved = {var: os.environ.pop(var, None) for var in vars_}

        def undo():
            for var, value in saved.items():
                if value is not None:
                    os.environ[var] = value

        return undo

    def test_hostile_forms_never_resolve_by_themselves(self, box, install):
        for name, vars_ in TOOL_ENV.items():
            for form in self._forms(name):
                with pytest.raises(LookupError):
                    internals.absolute_tool_dir(form, "X")
                undo = self._without(vars_)
                try:  # nothing but the CWD decoys reachable: refused
                    with pytest.raises(LookupError):
                        internals.find_binary_absolute(
                            name, path_to_bin=form, env_vars=vars_, binary_names=[name]
                        )
                finally:
                    undo()
                # the install configured: refused or the install, never a decoy
                _refused_or_install(
                    lambda location: internals.find_binary_absolute(
                        name, path_to_bin=location, env_vars=vars_, binary_names=[name]
                    ),
                    form,
                    str(install / name),
                    box,
                )

    def test_a_hostile_absolute_candidate_is_skipped_by_the_gate(
        self, box, tmp_path, monkeypatch
    ):
        # the raw finder yields the file an absolute hostile form names (teeth);
        # the gate skips it, so the search ends unresolved rather than with it
        good = _exec_file(tmp_path / "bin", "prover9")
        forms = [os.path.join(str(tmp_path), "bin", os.curdir, "..", "bin", "prover9")]
        if os.name == "posix":  # a name that really exists with a line break
            forms.append(_exec_file(tmp_path / "bad\ndir", "prover9"))
        for form in forms:
            raw = list(internals.find_file_iter(form, (), (), ["prover9"]))
            assert raw and any(os.path.isabs(r) for r in raw), (form, raw)
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=form, binary_names=["prover9"]
                )
        found = internals.find_binary_absolute(
            "prover9", path_to_bin=good, binary_names=["prover9"]
        )
        assert _same(found, good)

    def test_a_blank_location_means_not_given(self, box, install):
        for name, vars_ in TOOL_ENV.items():
            for blank in ("", "   ", _LyingStr(""), b"", Path("")):
                got = internals.find_binary_absolute(
                    name, path_to_bin=blank, env_vars=vars_, binary_names=[name]
                )
                assert _same(got, install / name) and not _inside(got, box)

    @pytest.mark.skipif(os.name != "posix", reason="a newline in a POSIX name")
    def test_a_hostile_candidate_from_the_environment_is_skipped(
        self, box, tmp_path, monkeypatch
    ):
        # a directory whose name carries a line break exists on POSIX; the raw
        # finder yields the binary in it (teeth), the gate refuses it, and a
        # clean install later in the same variable is still taken
        bad = tmp_path / "bad\ndir"
        clean = tmp_path / "clean"
        _exec_file(bad, "prover9")
        good = _exec_file(clean, "prover9")
        monkeypatch.setenv("PROVER9", str(bad))
        raw = list(internals.find_binary_iter("prover9", env_vars=["PROVER9"]))
        assert raw and any(_inside(r, bad) for r in raw), raw
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", env_vars=["PROVER9"])
        monkeypatch.setenv("PROVER9", os.pathsep.join([str(bad), str(clean)]))
        got = internals.find_binary_absolute("prover9", env_vars=["PROVER9"])
        assert _same(got, good)

    def test_non_path_locations_are_refused_not_raised(self, box):
        for name, vars_ in TOOL_ENV.items():
            for value in (7, 1.5, [name], (name,), {"p": name}, object()):
                with pytest.raises(LookupError):
                    internals.find_binary_absolute(
                        name, path_to_bin=value, env_vars=vars_, binary_names=[name]
                    )
                with pytest.raises(LookupError):
                    internals.absolute_tool_dir(value, "X")


class TestTrustedResolverInputs:
    """The spawn-time resolver answers a hostile target with a refusal, never
    with an exception another layer would not expect (a lying str hiding a
    NUL used to surface as a ValueError from lstat)."""

    def test_hostile_targets_are_refused_not_raised(self, private_dir):
        real = _exec_file(private_dir, "java")
        hostile = [
            _LyingStr(real + NUL),
            real + NUL,
            os.fsencode(real),  # bytes: the finder decodes, the spawn refuses
            None,
            7,
            [real],
            str(private_dir),  # a directory is not an executable file
        ]
        if os.name == "posix":
            hostile.append(_LyingStr("./java"))  # relative, whatever it claims
        for target in hostile:
            assert pathsec.resolve_trusted_executable(target) is None, target
            with pytest.raises(pathsec.TrustError):
                pathsec.spawn_trusted(target, [])
        # the same file spelled honestly, as a Path, or as a lying str holding
        # the real characters, resolves to its real path
        for target in (real, Path(real), _LyingStr(real)):
            assert _same(pathsec.resolve_trusted_executable(target), real), target


class TestAlignedSentDot:
    def test_repr_svg_resolves_dot_absolute_and_spawns_trusted(
        self, box, tmp_path, monkeypatch
    ):
        from nltk.translate import api as translate_api
        from nltk.translate.api import AlignedSent, Alignment

        _exec_file(box, _exe("dot"))  # CWD decoy
        good = _exec_file(tmp_path / "bin", _exe("dot"))
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        seen = {}

        def _record(target, args, **kwargs):
            seen["target"], seen["args"], seen["kwargs"] = target, list(args), kwargs
            raise _Spawned(target)

        monkeypatch.setattr(translate_api, "spawn_trusted", _record)
        sent = AlignedSent(["a"], ["b"], Alignment.fromstring("0-0"))
        with pytest.raises(_Spawned):
            sent._repr_svg_()
        assert _same(seen["target"], good) and not _inside(seen["target"], box)
        assert seen["args"] == ["-Tsvg"] and not seen["kwargs"].get("shell")
        # with only the CWD decoy reachable it is refused, never run
        monkeypatch.setenv("PATH", str(tmp_path / "empty"))
        seen.clear()
        with pytest.raises(Exception, match="Cannot find the dot binary"):
            sent._repr_svg_()
        assert seen == {}


def _resolve(location=None, env_vars=("PROVER9",)):
    return internals.find_binary_absolute(
        "prover9", location, env_vars=list(env_vars), binary_names=["prover9"]
    )


def _marker_stub(directory, name, marker):
    """A planted binary that records that it ran: it appends to *marker*, so a
    launch is visible even when the wrapper errors on its output afterwards."""
    path = Path(directory) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"#!/bin/sh\nprintf '%s\\n' {name} >> '{marker}'\necho PWNED\nexit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)


class TestAdvisoryProofOfConcept:
    """GHSA-cc5r-64rf-75hg, literally: an executable ./prover9 (and ./mace4) in
    the current directory, ``p = Prover9(); p.config_prover9(binary_location='.')``,
    then a later ``prove()`` (``build_model()`` for Mace) would Popen it from the
    CWD. The planted files record when they run. Verdict: the marker is never
    written and no spawn ever receives a CWD path; the raw finder still yields
    ``./prover9`` for ``path_to_bin='.'`` (the truthy relative path_to_bin that
    disables the bare-name guard), so the fix is the absolute-only gate, and
    with that gate neutered the advisory's state is reproduced end to end."""

    NAMES = ("prover9", "mace4", "prooftrans", "interpformat", "megam", "tadm")
    FORMS = (".", "./", "./prover9", "sub/prover9")
    # the forms the raw finder still honours as a CWD path: '.' itself has no
    # directory part, so develop's bare-name test already refuses it there
    TRUTHY = ("./", "./prover9", "sub/prover9")

    @pytest.fixture
    def poc(self, private_dir, monkeypatch):
        """The advisory's directory under $HOME (a private chain: on POSIX the
        spawn layer would run a same-user file there, so the config-time gate
        is the guard under test), nothing reachable through the environment, and
        a record of every target handed to the spawn and every Popen made."""
        from types import SimpleNamespace

        from nltk.classify import megam, tadm
        from nltk.inference import prover9 as prover9_module

        box = private_dir / "cwd"
        marker = private_dir / "ran"
        for name in self.NAMES:
            _marker_stub(box, name, marker)
            _marker_stub(box / "sub", name, marker)
        empty = private_dir / "empty"
        empty.mkdir()
        for var in ALL_ENV_VARS:
            monkeypatch.delenv(var, raising=False)
        monkeypatch.setenv("PATH", _scrubbed_path(empty))
        monkeypatch.chdir(box)
        handed, launched = [], []
        real_spawn, real_popen = pathsec.spawn_trusted, pathsec.subprocess.Popen

        def spawn_spy(target, args=(), **kwargs):
            handed.append(os.fspath(target))
            return real_spawn(target, args, **kwargs)

        def popen_spy(argv, *args, **kwargs):
            launched.append(kwargs.get("executable") or argv[0])
            return real_popen(argv, *args, **kwargs)

        for module in (prover9_module, megam, tadm):
            monkeypatch.setattr(module, "spawn_trusted", spawn_spy)
        monkeypatch.setattr(pathsec.subprocess, "Popen", popen_spy)
        return SimpleNamespace(box=box, marker=marker, handed=handed, launched=launched)

    @staticmethod
    def _judge(poc):
        """The verdict: nothing ran from the CWD and no CWD path reached the
        spawn (relative, or absolute inside the box)."""
        assert not poc.marker.exists(), poc.marker.read_text()
        for target in poc.handed + poc.launched:
            assert os.path.isabs(target) and not _inside(target, poc.box), target

    @staticmethod
    def _theorem():
        from nltk.sem import Expression

        goal = Expression.fromstring("mortal(socrates)")
        assumptions = [
            Expression.fromstring("man(socrates)"),
            Expression.fromstring("all x.(man(x) -> mortal(x))"),
        ]
        return goal, assumptions

    def test_the_truthy_relative_path_to_bin_still_disables_the_bare_name_guard(
        self, poc
    ):
        # the advisory's runtime confirmation, kept as the teeth of the fix: the
        # raw finder honours a truthy relative path_to_bin as a CWD path while
        # the bare name is refused; the absolute-only gate refuses every form
        names = ["prover9", "prover9.exe"]  # what config_prover9 passes
        for form in self.TRUTHY:
            got = internals.find_binary("prover9", path_to_bin=form, binary_names=names)
            assert not os.path.isabs(got) and _inside(got, poc.box), (form, got)
        with pytest.raises(LookupError):
            internals.find_binary("prover9", binary_names=names)
        with pytest.raises(LookupError):  # '.' is bare to the raw finder too
            internals.find_binary("prover9", path_to_bin=".", binary_names=names)
        for form in self.FORMS:
            with pytest.raises(LookupError):
                internals.find_binary_absolute(
                    "prover9", path_to_bin=form, binary_names=names
                )
        # the suggested fix criterion: only an os.path.isabs() result of the
        # raw iterator is acceptable, and with nothing configured there is none
        for form in self.TRUTHY:
            raw = list(
                internals.find_binary_iter(
                    "prover9", path_to_bin=form, binary_names=names
                )
            )
            assert raw and not any(os.path.isabs(m) for m in raw), (form, raw)
        self._judge(poc)

    def test_prover9_poc_is_refused_end_to_end(self, poc):
        from nltk.inference.prover9 import Prover9, Prover9Command

        goal, assumptions = self._theorem()
        for form in self.FORMS:
            p = Prover9()
            with pytest.raises(LookupError):
                p.config_prover9(binary_location=form)  # the advisory's line
            assert p._prover9_bin is None and p._binary_location is None
            # the "subsequent prove()": nothing to run but the decoys, refused;
            # on a host with a real install on its default search list the
            # install runs instead, which the judge below accepts
            try:
                Prover9Command(goal, assumptions, prover=p).prove()
            except LookupError:
                pass
            assert getattr(p, "_prover9_bin", None) is None or os.path.isabs(
                p._prover9_bin
            )
        self._judge(poc)

    def test_mace_poc_is_refused_end_to_end(self, poc):
        from nltk.inference.mace import Mace, MaceCommand

        goal, assumptions = self._theorem()
        for form in self.FORMS:
            m = Mace()
            with pytest.raises(LookupError):
                m.config_prover9(binary_location=form)  # inherited, the same line
            assert getattr(m, "_prover9_bin", None) is None
            assert m._binary_location is None
            try:
                MaceCommand(goal, assumptions, model_builder=m).build_model()
            except LookupError:
                pass
            assert m._mace4_bin is None or os.path.isabs(m._mace4_bin)
        self._judge(poc)

    def test_helpers_and_siblings_named_by_the_advisory_are_refused(self, poc):
        from nltk.classify import megam, tadm
        from nltk.inference.mace import Mace, MaceCommand
        from nltk.inference.prover9 import Prover9

        # prooftrans and interpformat resolve through the same helper the
        # advisory traces for mace4; with only CWD decoys they are refused
        try:
            Prover9()._call_prooftrans("x")
        except LookupError:
            pass
        try:
            MaceCommand(None, [], model_builder=Mace())._call_interpformat(
                "x", ["cooked"]
            )
        except LookupError:
            pass
        # megam and tadm: the same config entry, then the call that would run
        # the configured binary (call_* re-resolves bare when none is set)
        for form in self.FORMS:
            with pytest.raises(LookupError):
                megam.config_megam(form.replace("prover9", "megam"))
            assert megam._megam_bin is None
            with pytest.raises(LookupError):
                tadm.config_tadm(form.replace("prover9", "tadm"))
            assert tadm._tadm_bin is None
        for call in (lambda: megam.call_megam(["-h"]), lambda: tadm.call_tadm(["-h"])):
            try:
                call()
            except (LookupError, OSError):
                pass
        self._judge(poc)

    def test_with_an_install_configured_the_poc_forms_yield_only_the_install(
        self, poc, private_dir, monkeypatch
    ):
        from nltk.inference.mace import Mace
        from nltk.inference.prover9 import Prover9, Prover9Command

        install = private_dir / "install"
        legit = _marker_stub(install, "prover9", private_dir / "legit_ran")
        monkeypatch.setenv("PROVER9", str(install))
        goal, assumptions = self._theorem()
        for form in self.FORMS:
            # the suggested fix criterion: the first os.path.isabs() result of
            # the raw iterator, which is the install, is what is configured
            raw_first_abs = next(
                m
                for m in internals.find_binary_iter(
                    "prover9",
                    path_to_bin=form,
                    env_vars=["PROVER9"],
                    binary_names=["prover9", "prover9.exe"],
                )
                if os.path.isabs(m)
            )
            for tool in (Prover9(), Mace()):
                tool.config_prover9(binary_location=form)
                assert _same(tool._prover9_bin, legit), (form, tool._prover9_bin)
                assert _same(tool._prover9_bin, raw_first_abs)
                assert _same(tool._binary_location, install)
            if os.name == "posix":
                p = Prover9()
                p.config_prover9(binary_location=form)
                assert Prover9Command(goal, assumptions, prover=p).prove() is True
        self._judge(poc)
        if os.name == "posix":
            assert (private_dir / "legit_ran").read_text().split() == ["prover9"] * len(
                self.FORMS
            )

    @pytest.mark.skipif(os.name != "posix", reason="the planted binary is a script")
    def test_with_the_gate_neutered_the_advisory_state_is_reproduced(
        self, poc, monkeypatch
    ):
        # teeth: put the pre-fix resolver back behind config_prover9 and the
        # advisory's observation returns for the truthy spelling './' (develop
        # refuses the literal '.' as bare): ./prover9 is configured verbatim and
        # handed to the spawn; the POSIX spawn layer still refuses the relative
        # spelling, and the same file as a normalised absolute CWD path, which
        # is what a caller's abspath() would make of it, runs (the marker)
        from nltk.inference import prover9 as prover9_module
        from nltk.inference.mace import Mace
        from nltk.inference.prover9 import Prover9, Prover9Command

        monkeypatch.setattr(
            prover9_module, "find_binary_absolute", internals.find_binary
        )
        goal, assumptions = self._theorem()
        p = Prover9()
        p.config_prover9(binary_location="./")
        assert p._prover9_bin == os.path.join(os.curdir, "prover9")
        with pytest.raises(LookupError, match="not on a trusted path"):
            Prover9Command(goal, assumptions, prover=p).prove()
        assert poc.handed and not os.path.isabs(poc.handed[-1])  # the judge flips
        m = Mace()
        m.config_prover9(binary_location="./")
        assert m._prover9_bin == os.path.join(os.curdir, "prover9")
        assert m._binary_location == os.curdir
        assert not poc.marker.exists()
        p._prover9_bin = os.path.abspath(p._prover9_bin)
        assert Prover9Command(goal, assumptions, prover=p).prove() is True
        assert poc.marker.read_text().split() == ["prover9"]
        assert _inside(poc.launched[-1], poc.box)


class TestBeyondTheReview:
    """Attacks past the adversarial review's list, each judged by which binary
    resolved or reached the spawn: a bytes location whose decode() lies, a
    flipping __fspath__ at the spawn layer, PATHEXT shaped like a path, a
    directory named like the binary, hard links, a hostile entry ahead of the
    install in the tool's env var, a '..' hidden in a symlink target, PATH
    entry spellings, overlong and undecodable names, and Windows-shaped forms."""

    def test_a_bytes_location_is_judged_by_its_real_bytes_not_its_decode(
        self, box, tmp_path
    ):
        good = _exec_file(tmp_path / "bin", "prover9")
        # the real bytes name the CWD decoy; decode() claims the install: refused
        with pytest.raises(LookupError):
            _resolve(_bytes_whose_decode_answers(b"./prover9", good))
        with pytest.raises(LookupError):
            internals.absolute_tool_dir(
                _bytes_whose_decode_answers(b"./", str(tmp_path / "bin")), "X"
            )
        # the real bytes name the install; decode() claims the decoy: the install
        got = _resolve(_bytes_whose_decode_answers(os.fsencode(good), "./prover9"))
        assert _same(got, good) and not _inside(got, box)
        # decode() answering something that is not text is a clean refusal in
        # every guard that shares the materialisation, never a TypeError
        for guard, real, error in (
            (_resolve, b"./prover9", LookupError),
            (lambda v: internals.absolute_tool_dir(v, "X"), b"./", LookupError),
            (pathsec.validate_tool_dir, b"-prover9", PermissionError),
            (
                lambda v: pathsec.validate_tool_path(v, must_exist=False),
                b"-prover9",
                PermissionError,
            ),
            (pathsec.validate_model_resource, b"-prover9", ValueError),
        ):
            with pytest.raises(error):
                guard(_bytes_whose_decode_answers(real, 42))

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_fspath_is_read_once_at_the_spawn_layer(self, private_dir):
        trusted = _exec_file(private_dir / "trusted", "prover9", marker="LEGIT")
        world = private_dir / "world"
        planted = _exec_file(world, "prover9")
        os.chmod(world, 0o777)
        try:
            # trusted on the first read, the world-writable decoy on every
            # later one: the one read is what runs
            flip = _Flipping(trusted, planted)
            proc = pathsec.spawn_trusted(
                flip, [], stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            out = proc.communicate()[0].decode()
            assert flip.calls == 1 and _same(proc.args[0], trusted), proc.args
            assert "LEGIT" in out and "PWNED" not in out
            # the decoy on the first read is refused, whatever comes later
            flip = _Flipping(planted, trusted)
            with pytest.raises(pathsec.TrustError):
                pathsec.spawn_trusted(flip, [])
            assert flip.calls == 1
        finally:
            os.chmod(world, 0o700)

    def test_pathext_shaped_like_a_path_cannot_climb_into_the_cwd(
        self, box, tmp_path, monkeypatch
    ):
        # a PATHEXT suffix is appended to the bare name; one shaped like a path
        # climbs out of a PATH directory that holds a DIRECTORY of that name
        # (prover9's own default search list has /usr/local/bin/prover9)
        pathdir = tmp_path / "pathdir"
        (pathdir / "prover9").mkdir(parents=True)
        good = _exec_file(pathdir, "prover9.exe")
        escape = "/../../" + box.name + "/prover9"
        monkeypatch.setenv("PATH", str(pathdir))
        monkeypatch.setenv("PATHEXT", os.pathsep.join([escape, "\t", ".exe"]))
        raw = list(internals._path_dirs_iter(["prover9"]))
        assert any(_inside(r, box) for r in raw), raw  # the walk does surface it
        got = _resolve()
        assert _same(got, good) and not _inside(got, box)  # the '..' gate skips it
        monkeypatch.setenv("PATHEXT", escape)
        with pytest.raises(LookupError):
            _resolve()

    def test_a_directory_named_like_the_binary_is_never_taken(
        self, box, tmp_path, monkeypatch
    ):
        for holder in ("p9", "prover9dir"):
            _exec_file(box / holder, "prover9")
        for form in ("p9", "./p9", "p9/", "./p9/", "prover9dir", "prover9dir/"):
            with pytest.raises(LookupError):
                _resolve(form)
        # a directory named prover9 on PATH or in the env-var directory is not
        # a hit, and the binary nested inside it is not reached through it
        for holder in (tmp_path / "pathdir", tmp_path / "envdir"):
            _exec_file(holder / "prover9", "prover9", marker="NESTED")
        monkeypatch.setenv("PATH", str(tmp_path / "pathdir"))
        with pytest.raises(LookupError):
            _resolve()
        monkeypatch.setenv("PROVER9", str(tmp_path / "envdir"))
        with pytest.raises(LookupError):
            _resolve()
        # naming that directory explicitly is the caller's choice and reaches it
        got = _resolve(str(tmp_path / "envdir" / "prover9"))
        assert _same(got, tmp_path / "envdir" / "prover9" / "prover9")
        # and config_java given a directory whose "java" is itself a directory
        _exec_file(tmp_path / "jdk" / "java", "java")
        with pytest.raises(LookupError):
            internals.config_java(str(tmp_path / "jdk"))
        assert internals._java_bin is None

    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    def test_hard_links_do_not_bypass_the_spawn_trust(
        self, box, private_dir, monkeypatch
    ):
        real = _exec_file(private_dir / "trusted", "prover9", marker="LEGIT")
        scrubbed = os.environ["PATH"]
        world = private_dir / "world"
        world.mkdir()
        os.link(real, world / "prover9")
        os.chmod(world, 0o777)
        try:
            # the operator's PATH entry is taken at config time and refused at
            # the spawn: the holding directory is what another user can write
            monkeypatch.setenv("PATH", str(world))
            got = _resolve()
            assert _same(got, world / "prover9")
            assert pathsec.resolve_trusted_executable(got) is None
            with pytest.raises(pathsec.TrustError):
                pathsec.spawn_trusted(got, [])
        finally:
            os.chmod(world, 0o700)
        # a hard link planted in the CWD is a relative form like any other
        monkeypatch.setenv("PATH", scrubbed)
        home_box = private_dir / "box"
        home_box.mkdir()
        os.link(real, home_box / "hl")
        monkeypatch.chdir(home_box)
        for form in ("hl", "./hl", f"../{home_box.name}/hl"):
            with pytest.raises(LookupError):
                _resolve(form)
        # the extra links do not taint the trusted binary itself
        assert os.stat(real).st_nlink >= 3
        assert _same(pathsec.resolve_trusted_executable(real), real)

    def test_a_hostile_entry_ahead_of_the_install_in_the_env_var_is_skipped(
        self, box, install, monkeypatch
    ):
        trusted = str(install)
        hostile = [
            "./sub",
            f"{trusted}/../{box.name}",
            "",
            ".",
            f" {box}",
            f"{box}\n",
            f"~/{box.name}",
            "C:",
        ]
        for entry in hostile:
            monkeypatch.setenv("PROVER9", os.pathsep.join([entry, trusted]))
            got = _resolve()
            assert _same(got, install / "prover9") and not _inside(got, box), entry
            monkeypatch.setenv("PROVER9", entry)
            with pytest.raises(LookupError):
                _resolve()
        # the CWD's own absolute path after the install: the install still wins
        monkeypatch.setenv("PROVER9", os.pathsep.join([trusted, str(box)]))
        assert _same(_resolve(), install / "prover9")

    @pytest.mark.skipif(os.name != "posix", reason="symlinks and POSIX ownership")
    def test_a_parent_component_hidden_in_a_symlink_target_is_refused_at_spawn(
        self, box, private_dir, monkeypatch
    ):
        planted = _exec_file(private_dir / "box", "prover9")
        world = private_dir / "world"
        _exec_file(world, "prover9")
        os.chmod(world, 0o777)
        try:
            links = {
                "relative": os.path.join(os.pardir, "box", "prover9"),
                "absolute_into_writable": str(world / "prover9"),
                "two_hop": os.path.join("mid", "prover9"),
            }
            for label, target in links.items():
                holder = private_dir / label
                holder.mkdir()
                if label == "two_hop":
                    os.symlink(os.path.join(os.pardir, "box"), holder / "mid")
                os.symlink(target, holder / "prover9")
                monkeypatch.setenv("PROVER9", str(holder))
                # no lexical '..': the config gate passes the link itself
                got = _resolve()
                assert _same(got, holder / "prover9"), (label, got)
                # the spawn follows every hop and refuses the '..' or the
                # writable directory the target lives in
                assert pathsec.resolve_trusted_executable(got) is None, label
                with pytest.raises(pathsec.TrustError):
                    pathsec.spawn_trusted(got, [])
        finally:
            os.chmod(world, 0o700)
        # the honest link, to an absolute private file, resolves to that file
        honest = private_dir / "honest"
        honest.mkdir()
        os.symlink(planted, honest / "prover9")
        assert _same(pathsec.resolve_trusted_executable(honest / "prover9"), planted)

    def test_path_entry_spellings_never_reach_the_cwd(self, box, tmp_path, monkeypatch):
        good = _exec_file(tmp_path / "bin", "prover9")
        entries = [
            ".",
            "",
            '"."',
            f" {tmp_path / 'bin'}",
            "./",
            f"~/{box.name}",
            "C:",
            f"{tmp_path / 'bin'}/../{box.name}",
        ]
        for entry in entries:
            monkeypatch.setenv("PATH", entry)
            with pytest.raises(LookupError):
                _resolve()
            monkeypatch.setenv("PATH", os.pathsep.join([entry, str(tmp_path / "bin")]))
            got = _resolve()
            assert _same(got, good) and not _inside(got, box), entry

    def test_overlong_locations_are_refused_not_raised(self, box, tmp_path):
        for form in (
            str(tmp_path / ("a" * 5000) / "prover9"),
            str(tmp_path / ("b" * 300) / "prover9"),
        ):
            with pytest.raises(LookupError):
                _resolve(form)
            assert pathsec.resolve_trusted_executable(form) is None
            with pytest.raises(pathsec.TrustError):
                pathsec.spawn_trusted(form, [])
        with pytest.raises(LookupError):
            _resolve("./" + "a" * 4090 + "/prover9")

    @pytest.mark.skipif(os.name != "posix", reason="bytes paths are a POSIX spelling")
    def test_undecodable_bytes_and_surrogates_are_refused_not_raised(
        self, box, monkeypatch
    ):
        high = bytes([0xFF, 0xFE])
        for raw in (
            b"./" + high + b"/prover9",
            b"/" + high + b"/prover9",
            os.fsencode(str(box)) + b"/" + high + b"/prover9",
        ):
            with pytest.raises(LookupError):
                _resolve(raw)
            assert pathsec.resolve_trusted_executable(raw) is None
        surrogate = "/" + chr(0xDCFF) + "/prover9"
        monkeypatch.setenv("PROVER9", surrogate)
        with pytest.raises(LookupError):
            _resolve()
        monkeypatch.delenv("PROVER9")
        monkeypatch.setenv("PATH", surrogate)
        with pytest.raises(LookupError):
            _resolve()
        assert pathsec.resolve_trusted_executable(surrogate) is None

    def test_windows_shaped_and_whitespace_forms(self, box):
        decoy = str(box / "prover9")
        for form in (
            "C:prover9",
            "//" + decoy.lstrip("/"),
            f"..\\{box.name}\\prover9",
            ".\\prover9",
            decoy + ".",
            decoy + " ",
            " " + decoy,
        ):
            with pytest.raises(LookupError):
                _resolve(form)
        # an explicit absolute file the user owns, spelled with a '.' segment
        # or a doubled separator, is honoured and comes back normalised
        for form in (
            os.path.join(str(box), os.curdir, "prover9"),
            str(box) + os.sep + os.sep + "prover9",
        ):
            assert _resolve(form) == os.path.normpath(form)

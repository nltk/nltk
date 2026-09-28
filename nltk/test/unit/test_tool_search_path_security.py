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
    """A PATH holding nothing but ``which``, which find_file_iter shells out to."""
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

    def test_no_which_on_path_is_not_found_rather_than_a_crash(
        self, box, tmp_path, monkeypatch
    ):
        # a PATH without which (minimal containers), or with a which that cannot
        # run, must end in the not-found error, never an OSError for which itself
        bare = tmp_path / "bare"
        bare.mkdir()
        monkeypatch.setenv("PATH", str(bare))
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])
        with pytest.raises(LookupError):
            internals.find_binary("prover9", binary_names=["prover9"])
        broken = tmp_path / "broken"
        broken.mkdir()
        (broken / "which").write_text("not executable\n", encoding="utf-8")
        monkeypatch.setenv("PATH", str(broken))
        with pytest.raises(LookupError):
            internals.find_binary_absolute("prover9", binary_names=["prover9"])

    def test_parent_detection_uses_only_the_platform_separators(self):
        # a backslash is a file-name character on POSIX and a separator on
        # Windows; ".." must be recognised exactly where the OS would honour it
        parts = internals._path_components
        assert os.pardir in parts(os.path.join(os.sep, "a", "..", "b"))
        assert os.pardir not in parts(os.path.join(os.sep, "a", "..x", "b"))
        if os.name == "posix":
            assert os.pardir not in parts("/a/..\\b")  # one component, "..\\b"
        else:
            assert os.pardir in parts("C:\\a\\..\\b")
            assert os.pardir in parts("C:/a/../b")
            assert os.pardir in parts("C:\\a/..\\b")

    def test_posix_backslash_in_a_component_is_not_a_separator(self, box, tmp_path):
        if os.name != "posix":
            return  # a backslash cannot be part of a file name on Windows
        odd_dir = tmp_path / "..\\odd"
        good = _exec_file(odd_dir, "prover9")
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
            assert os.curdir not in internals._path_components(got), got


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
        if os.name != "nt":  # take the no-``which`` branch on POSIX too
            monkeypatch.setattr(os, "name", "nt")
        # the finder skips the relative hit and returns the install behind it,
        # instead of stopping at the CWD hit the way the OS search does
        found = internals.find_binary_absolute("svn", binary_names=["svn.exe"])
        assert _same(found, good) and not _inside(found, box)
        # with only the CWD hit reachable, the refusal names it
        monkeypatch.setenv("PATH", os.curdir)
        with pytest.raises(LookupError, match="only in the current working"):
            internals.find_binary_absolute("svn", binary_names=["svn.exe"])

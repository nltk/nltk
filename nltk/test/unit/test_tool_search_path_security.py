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
ALL_ENV_VARS = [var for vars_ in TOOL_ENV.values() for var in vars_]
NUL = chr(0)


class _Spawned(Exception):
    """Raised in place of the hunpos spawn, carrying the binary it was given."""


class _LyingStr(str):
    """A location whose string methods lie: ``os.path.isabs`` asks ``startswith``."""

    def startswith(self, *args, **kwargs):
        return True


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
    return [_LyingStr(relative), Path(relative), relative.encode(), relative + NUL]


def _escape_form(name, box):
    """The relative form that, rebased onto a trusted directory, climbs back
    out of it into the CWD decoy."""
    return f"../{os.path.basename(box)}/{name}"


def _scrubbed_path(directory):
    """A PATH holding nothing but ``which``, which find_file_iter shells out to."""
    real_which = shutil.which("which")
    if os.name == "posix" and real_which:
        os.symlink(real_which, os.path.join(directory, "which"))
    return str(directory)


def _same(a, b):
    return os.path.realpath(str(a)) == os.path.realpath(str(b))


def _inside(path, directory):
    return os.path.realpath(str(path)).startswith(
        os.path.realpath(str(directory)) + os.sep
    )


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
        # teeth: os.path.isabs believes the object; the guard must not
        lying = _LyingStr("./prover9")
        assert os.path.isabs(lying)
        with pytest.raises(LookupError):
            internals.find_binary_absolute(
                "prover9", path_to_bin=lying, binary_names=["prover9"]
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
        # PATH is where the operator installs tools: on POSIX an absolute hit is
        # honoured and the spawn layer then judges who can write it; the finder
        # has no PATH lookup on Windows, so there the CWD decoy is all it sees
        good = _exec_file(tmp_path / "bin", "megam")
        monkeypatch.setenv(
            "PATH", f"{tmp_path / 'bin'}{os.pathsep}{tmp_path / 'empty'}"
        )
        if os.name == "posix":
            found = internals.find_binary_absolute("megam", binary_names=["megam"])
            assert _same(found, good)
        else:
            with pytest.raises(LookupError):
                internals.find_binary_absolute("megam", binary_names=["megam"])

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

    def test_relative_java_home_is_refused(self, box, monkeypatch):
        for var in ("JAVAHOME", "JAVA_HOME"):
            for value in (".", "sub", "./sub", "./java"):
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

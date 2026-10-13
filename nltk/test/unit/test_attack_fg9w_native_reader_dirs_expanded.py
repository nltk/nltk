"""GHSA-fg9w-wfp5-j933, third pass: directories an external tool READS natively.

The advisory's shape is a caller path handed to a third party that opens it
itself. BllipParser's model directory was the first sink, the MaltParser
learn-mode model and the tbl demo plot the second pass. This pass covers the
directories three wrappers hand their binaries beside the binary itself:
SENNA's ``-path`` data dir, REPP's config tree (``-c erg/repp.set``) and the
C&C ``--models`` tree. Each now goes through
:func:`nltk.pathsec.validate_tool_data_dir` when the command is built: the
tree must be on a private chain like the binary, hold no symlink, junction,
special file or hardlink, and be private throughout; the checked string is
what the command carries.

Every fixture is staged under ``$HOME``, a private directory chain on every
CI runner, never the shared temp dir (world-writable ``/tmp`` on Linux),
which the trust chain refuses on its own; a refusal in these tests is
therefore due to the planted weakness alone.
"""

import os
import shutil
import stat
import tempfile
from platform import architecture, system

import pytest

from nltk import pathsec
from nltk.classify import senna as senna_mod
from nltk.sem import boxer as boxer_mod
from nltk.tokenize import repp as repp_mod

POSIX = os.name == "posix"
NOT_ROOT = POSIX and os.geteuid() != 0
REFUSED = PermissionError


@pytest.fixture
def staged(pathsec_sandbox):
    """A fresh private directory under ``$HOME`` for the tool installs, plus
    the out-of-sandbox dir, for links and hardlinks that point outside. The
    enforced sandbox root itself is a temp dir, which on a Linux runner sits
    under world-writable ``/tmp`` and so can never clear the trust chain."""
    root, outside = pathsec_sandbox
    base = tempfile.mkdtemp(prefix=".nltk_fg9w_dirs_", dir=os.path.expanduser("~"))
    try:
        yield base, str(outside)
    finally:
        shutil.rmtree(base, ignore_errors=True)


def _senna_binary_name():
    os_name = system()
    if os_name == "Linux":
        return "senna-linux64" if architecture()[0] == "64bit" else "senna-linux32"
    if os_name == "Windows":
        return "senna-win32.exe"
    if os_name == "Darwin":
        return "senna-osx"
    return "senna"


def _executable(path):
    with open(path, "wb"):
        pass
    os.chmod(path, 0o755)


def _senna_install(base):
    tool = os.path.join(base, "senna")
    os.mkdir(tool)
    _executable(os.path.join(tool, _senna_binary_name()))
    with open(os.path.join(tool, "words.lst"), "w") as handle:
        handle.write("the\n")
    return tool


def _repp_install(base):
    tool = os.path.join(base, "repp")
    os.makedirs(os.path.join(tool, "src"))
    os.makedirs(os.path.join(tool, "erg"))
    _executable(os.path.join(tool, "src", "repp"))
    with open(os.path.join(tool, "erg", "repp.set"), "w") as handle:
        handle.write("")
    return tool


def _candc_install(base):
    tool = os.path.join(base, "candc")
    os.makedirs(os.path.join(tool, "bin"))
    os.makedirs(os.path.join(tool, "models", "boxer"))
    _executable(os.path.join(tool, "bin", "candc"))
    _executable(os.path.join(tool, "bin", "boxer"))
    with open(os.path.join(tool, "models", "boxer", "super"), "w") as handle:
        handle.write("")
    return tool


def _plant(kind, tree, member, outside):
    """A weakness inside *tree* at *member*: a symlink to a file outside, a
    hardlink to one, or a world-writable member."""
    target = os.path.join(tree, member)
    if kind == "symlink":
        victim = os.path.join(outside, "victim.dat")
        with open(victim, "w") as handle:
            handle.write("outside")
        os.symlink(victim, target)
    elif kind == "hardlink":
        victim = os.path.join(outside, "victim.dat")
        with open(victim, "w") as handle:
            handle.write("outside")
        try:
            os.link(victim, target)
        except OSError as exc:
            pytest.skip(f"cannot hardlink across these directories: {exc}")
    elif kind == "world-writable":
        with open(target, "w") as handle:
            handle.write("x")
        os.chmod(target, 0o666)
    else:  # pragma: no cover
        raise ValueError(kind)


_KINDS = ["symlink", "hardlink"] + (["world-writable"] if NOT_ROOT else [])


class _Spawned(Exception):
    """Raised by the spawn stand-in once it has recorded the argv."""


@pytest.fixture
def senna_spawn(monkeypatch):
    seen = []

    def fake(executable, args, **kwargs):
        seen.append((executable, list(args)))
        raise _Spawned()

    monkeypatch.setattr(senna_mod, "spawn_trusted", fake)
    return seen


def _senna(tool):
    return senna_mod.Senna(tool, ["pos"])


# =========================================================================== #
# SENNA -path                                                                  #
# =========================================================================== #


@pytest.mark.skipif(not POSIX, reason="symlinks and modes")
@pytest.mark.parametrize("kind", _KINDS)
def test_senna_data_dir_with_a_planted_member_is_refused_before_the_spawn(
    staged, senna_spawn, kind
):
    base, outside = staged
    tool = _senna_install(base)
    _plant(kind, tool, "planted.dat", outside)
    with pytest.raises(REFUSED, match="Security Violation"):
        _senna(tool).tag_sents([["the"]])
    assert senna_spawn == []


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_senna_symlinked_data_dir_is_resolved_like_the_binary(staged, senna_spawn):
    """A link to a private install is followed, as the executable's own link
    would be, and the RESOLVED directory is what senna is handed; a link whose
    target sits behind a directory another account can write is refused."""
    base, outside = staged
    real = _senna_install(outside)
    link = os.path.join(base, "senna")
    os.symlink(real, link)
    with pytest.raises(_Spawned):
        _senna(link).tag_sents([["the"]])
    ((_, argv),) = senna_spawn
    assert argv[argv.index("-path") + 1] == os.path.realpath(real) + os.sep
    if NOT_ROOT:
        del senna_spawn[:]
        shared = os.path.join(outside, "shared")
        os.mkdir(shared)
        behind = _senna_install(shared)
        os.chmod(shared, 0o777)
        link2 = os.path.join(base, "senna2")
        os.symlink(behind, link2)
        try:
            # the binary sits behind the same shared directory and is judged
            # first, so the refusal is the binary's (LookupError) as before
            with pytest.raises(LookupError, match="not on a trusted path"):
                _senna(link2).tag_sents([["the"]])
        finally:
            os.chmod(shared, 0o700)
        assert senna_spawn == []


def test_senna_clean_data_dir_reaches_the_spawn_as_the_checked_string(
    staged, senna_spawn
):
    base, outside = staged
    tool = _senna_install(base)
    with pytest.raises(_Spawned):
        _senna(tool).tag_sents([["the"]])
    ((_, argv),) = senna_spawn
    handed = argv[argv.index("-path") + 1]
    assert os.path.realpath(handed) == os.path.realpath(tool)
    # senna appends "hash/words.lst" to the value verbatim: the separator the
    # checked string drops is put back, or the real binary cannot find its data
    assert handed == pathsec.validate_tool_data_dir(tool, context="test") + os.sep


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_removing_the_senna_guard_lets_the_planted_dir_reach_the_spawn(
    staged, senna_spawn, monkeypatch
):
    base, outside = staged
    tool = _senna_install(base)
    _plant("symlink", tool, "planted.dat", outside)
    monkeypatch.setattr(senna_mod, "validate_tool_data_dir", lambda p, context: p)
    with pytest.raises(_Spawned):
        _senna(tool).tag_sents([["the"]])
    assert senna_spawn and senna_spawn[0][1][1].rstrip(os.sep) == tool


# =========================================================================== #
# REPP -c erg/repp.set                                                         #
# =========================================================================== #


def _repp(tool):
    return repp_mod.ReppTokenizer(tool)


@pytest.mark.skipif(not POSIX, reason="symlinks and modes")
@pytest.mark.parametrize("kind", _KINDS)
def test_repp_tree_with_a_planted_member_is_refused_when_the_command_is_built(
    staged, kind
):
    base, outside = staged
    tool = _repp_install(base)
    _plant(kind, tool, os.path.join("erg", "planted.set"), outside)
    with pytest.raises(REFUSED, match="Security Violation"):
        _repp(tool).generate_repp_command(os.path.join(base, "in.txt"))


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_repp_symlinked_tree_is_resolved_like_the_binary(staged):
    """A link to a private install is followed and the command is built from
    the RESOLVED tree; a link behind a directory another account can write is
    refused."""
    base, outside = staged
    real = _repp_install(outside)
    link = os.path.join(base, "repp")
    os.symlink(real, link)
    cmd = _repp(link).generate_repp_command(os.path.join(base, "in.txt"))
    assert cmd[0] == os.path.realpath(real) + "/src/repp"
    if NOT_ROOT:
        shared = os.path.join(outside, "shared")
        os.mkdir(shared)
        behind = _repp_install(shared)
        os.chmod(shared, 0o777)
        link2 = os.path.join(base, "repp2")
        os.symlink(behind, link2)
        try:
            with pytest.raises(REFUSED, match="not on a trusted path"):
                _repp(link2).generate_repp_command(os.path.join(base, "in.txt"))
        finally:
            os.chmod(shared, 0o700)


def test_repp_clean_tree_builds_the_command_from_the_checked_string(staged):
    base, outside = staged
    tool = _repp_install(base)
    cmd = _repp(tool).generate_repp_command(os.path.join(base, "in.txt"))
    checked = pathsec.validate_tool_data_dir(tool, context="test")
    assert cmd[0] == checked + "/src/repp"
    assert cmd[cmd.index("-c") + 1] == checked + "/erg/repp.set"


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_removing_the_repp_guard_lets_the_planted_tree_build(staged, monkeypatch):
    base, outside = staged
    tool = _repp_install(base)
    _plant("symlink", tool, os.path.join("erg", "planted.set"), outside)
    monkeypatch.setattr(repp_mod, "validate_tool_data_dir", lambda p, context: p)
    cmd = _repp(tool).generate_repp_command(os.path.join(base, "in.txt"))
    assert cmd[0] == tool + "/src/repp"


# =========================================================================== #
# C&C models flag                                                               #
# =========================================================================== #


@pytest.fixture
def boxer_call(monkeypatch):
    seen = []

    def fake(self, input_str, binary, args, verbose=False):
        seen.append((binary, list(args)))
        raise _Spawned()

    monkeypatch.setattr(boxer_mod.Boxer, "_call", fake)
    return seen


def _boxer(tool, monkeypatch):
    monkeypatch.delenv("CANDC", raising=False)
    return boxer_mod.Boxer(bin_dir=os.path.join(tool, "bin"))


@pytest.mark.skipif(not POSIX, reason="symlinks and modes")
@pytest.mark.parametrize("kind", _KINDS)
def test_candc_models_with_a_planted_member_are_refused_before_the_call(
    staged, boxer_call, monkeypatch, kind
):
    base, outside = staged
    tool = _candc_install(base)
    _plant(kind, tool, os.path.join("models", "boxer", "planted"), outside)
    with pytest.raises(REFUSED, match="Security Violation"):
        _boxer(tool, monkeypatch)._call_candc(
            [["the dog barks ."]], ["1"], question=False
        )
    assert boxer_call == []


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_candc_symlinked_models_tree_is_resolved_like_the_binary(
    staged, boxer_call, monkeypatch
):
    """A models link to a private tree is followed and the RESOLVED tree is
    handed over; a link behind a directory another account can write is
    refused."""
    base, outside = staged
    tool = _candc_install(base)
    real = os.path.join(outside, "models")
    os.makedirs(os.path.join(real, "boxer"))
    os.rename(os.path.join(tool, "models"), os.path.join(base, "models.aside"))
    os.symlink(real, os.path.join(tool, "models"))
    with pytest.raises(_Spawned):
        _boxer(tool, monkeypatch)._call_candc(
            [["the dog barks ."]], ["1"], question=False
        )
    ((_, args),) = boxer_call
    assert args[args.index("--models") + 1] == os.path.realpath(
        os.path.join(real, "boxer")
    )
    if NOT_ROOT:
        del boxer_call[:]
        shared = os.path.join(outside, "shared")
        os.makedirs(os.path.join(shared, "models", "boxer"))
        os.chmod(shared, 0o777)
        os.unlink(os.path.join(tool, "models"))
        os.symlink(os.path.join(shared, "models"), os.path.join(tool, "models"))
        try:
            with pytest.raises(REFUSED, match="not on a trusted path"):
                _boxer(tool, monkeypatch)._call_candc(
                    [["the dog barks ."]], ["1"], question=False
                )
        finally:
            os.chmod(shared, 0o700)
        assert boxer_call == []


def test_candc_clean_models_tree_reaches_the_call_as_the_checked_string(
    staged, boxer_call, monkeypatch
):
    base, outside = staged
    tool = _candc_install(base)
    with pytest.raises(_Spawned):
        _boxer(tool, monkeypatch)._call_candc(
            [["the dog barks ."]], ["1"], question=False
        )
    ((_, args),) = boxer_call
    handed = args[args.index("--models") + 1]
    expected = pathsec.validate_tool_data_dir(
        os.path.join(tool, "models", "boxer"), context="test"
    )
    assert handed == expected


@pytest.mark.skipif(not POSIX, reason="symlinks")
def test_removing_the_candc_guard_lets_the_planted_tree_reach_the_call(
    staged, boxer_call, monkeypatch
):
    base, outside = staged
    tool = _candc_install(base)
    _plant("symlink", tool, os.path.join("models", "boxer", "planted"), outside)
    monkeypatch.setattr(boxer_mod, "validate_tool_data_dir", lambda p, context: p)
    with pytest.raises(_Spawned):
        _boxer(tool, monkeypatch)._call_candc(
            [["the dog barks ."]], ["1"], question=False
        )
    assert boxer_call and boxer_call[0][1][1].startswith(tool)


# =========================================================================== #
# the guard itself                                                             #
# =========================================================================== #


def test_guard_refuses_a_relative_or_missing_directory(staged):
    base, outside = staged
    with pytest.raises(REFUSED, match="not absolute"):
        pathsec.validate_tool_data_dir("relative/dir", context="test")
    with pytest.raises(REFUSED, match="does not exist|not on a trusted path"):
        pathsec.validate_tool_data_dir(os.path.join(base, "missing"), context="test")


@pytest.mark.skipif(not NOT_ROOT, reason="root owns every mode")
@pytest.mark.parametrize("mode", [0o777, 0o775])
def test_guard_refuses_a_tree_another_account_can_write(staged, mode):
    base, outside = staged
    tool = _repp_install(base)
    os.chmod(tool, mode)
    try:
        with pytest.raises(REFUSED, match="Security Violation"):
            pathsec.validate_tool_data_dir(tool, context="test")
    finally:
        os.chmod(tool, 0o755)


def test_guard_returns_the_resolved_string_for_a_clean_tree(staged):
    base, outside = staged
    tool = _repp_install(base)
    checked = pathsec.validate_tool_data_dir(tool, context="test")
    assert os.path.isabs(checked) and os.path.realpath(checked) == os.path.realpath(
        tool
    )
    assert type(checked) is str

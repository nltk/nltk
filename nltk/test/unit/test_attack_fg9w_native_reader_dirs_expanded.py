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

Every fixture is staged through ``make_staging_dir`` inside the enforced
sandbox root, which the conftest places under ``$HOME``: a private directory
chain on every CI runner, where a temp root would sit under world-writable
``/tmp`` on Linux and be refused by the trust chain on its own. A refusal in
these tests is therefore due to the planted weakness alone.
"""

import os
import pathlib
import stat
from platform import architecture, system

import pytest

import nltk.data
from nltk import pathsec
from nltk.classify import senna as senna_mod
from nltk.sem import boxer as boxer_mod
from nltk.tokenize import repp as repp_mod

POSIX = os.name == "posix"
NOT_ROOT = POSIX and os.geteuid() != 0
REFUSED = PermissionError


@pytest.fixture
def staged(pathsec_sandbox):
    """A private staging dir inside the enforced sandbox root, plus the
    out-of-sandbox dir, for links and hardlinks that point outside."""
    root, outside = pathsec_sandbox
    try:
        base = nltk.data.make_staging_dir(prefix="fg9w_dirs_", cleanup=True)
    except PermissionError as exc:  # pragma: no cover
        pytest.skip(f"no writable in-sandbox data root: {exc}")
    return base, str(outside)


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


# =========================================================================== #
# every tool, every further weakness another account could leave in the tree  #
# =========================================================================== #


def _run_senna(tool, monkeypatch):
    _senna(tool).tag_sents([["the"]])


def _run_repp(tool, monkeypatch):
    return _repp(tool).generate_repp_command(
        os.path.join(os.path.dirname(tool), "in.txt")
    )


def _run_candc(tool, monkeypatch):
    _boxer(tool, monkeypatch)._call_candc([["the dog barks ."]], ["1"], question=False)


# (tool, install it under a base, the directory inside the install the tool
# reads, the call that hands that directory over)
_SINKS = [
    ("senna", _senna_install, "", _run_senna),
    ("repp", _repp_install, "erg", _run_repp),
    ("candc", _candc_install, os.path.join("models", "boxer"), _run_candc),
]
_SINK_IDS = [name for name, *_ in _SINKS]


def _member(inside, name):
    return os.path.join(inside, name) if inside else name


def _plant_more(kind, tree, member, outside):
    """Further weaknesses at *member* inside *tree*: a symlink to a directory
    outside, a dangling one, one to a sibling inside the tree, a relative one,
    a FIFO, a group-writable member, a writable subdirectory, and the original
    weaknesses two levels down."""
    target = os.path.join(tree, member)
    if kind == "dir-symlink":
        os.symlink(outside, target)
    elif kind == "dangling-symlink":
        os.symlink(os.path.join(outside, "gone"), target)
    elif kind == "inside-symlink":
        sibling = os.path.join(os.path.dirname(target), "sibling.dat")
        with open(sibling, "w") as handle:
            handle.write("inside")
        os.symlink("sibling.dat", target)
    elif kind == "relative-symlink":
        victim = os.path.join(outside, "victim.dat")
        with open(victim, "w") as handle:
            handle.write("outside")
        os.symlink(os.path.relpath(victim, os.path.dirname(target)), target)
    elif kind == "fifo":
        os.mkfifo(target)
    elif kind == "group-writable":
        with open(target, "w") as handle:
            handle.write("x")
        os.chmod(target, 0o664)
    elif kind == "world-writable-subdir":
        os.mkdir(target)
        os.chmod(target, 0o777)
    elif kind == "group-writable-subdir":
        os.mkdir(target)
        os.chmod(target, 0o775)
    elif kind == "nested-symlink":
        deep = os.path.join(os.path.dirname(target), "deep", "deeper")
        os.makedirs(deep)
        _plant("symlink", deep, "planted", outside)
    elif kind == "nested-world-writable":
        deep = os.path.join(os.path.dirname(target), "deep", "deeper")
        os.makedirs(deep)
        _plant("world-writable", deep, "planted", outside)
    else:  # pragma: no cover
        raise ValueError(kind)


_MORE_KINDS = [
    "dir-symlink",
    "dangling-symlink",
    "inside-symlink",
    "relative-symlink",
    "fifo",
    "nested-symlink",
] + (
    [
        "group-writable",
        "world-writable-subdir",
        "group-writable-subdir",
        "nested-world-writable",
    ]
    if NOT_ROOT
    else []
)


@pytest.mark.skipif(not POSIX, reason="symlinks, FIFOs and modes")
@pytest.mark.parametrize("kind", _MORE_KINDS)
@pytest.mark.parametrize("sink", _SINKS, ids=_SINK_IDS)
def test_every_further_planted_weakness_is_refused_before_the_tool(
    staged, senna_spawn, boxer_call, monkeypatch, sink, kind
):
    base, outside = staged
    name, install, inside, run = sink
    tool = install(base)
    _plant_more(kind, tool, _member(inside, "planted"), outside)
    with pytest.raises(REFUSED, match="Security Violation"):
        run(tool, monkeypatch)
    assert senna_spawn == [] and boxer_call == []


@pytest.mark.skipif(not NOT_ROOT, reason="root owns every mode")
@pytest.mark.parametrize(
    "mode",
    [0o1777, 0o777, 0o775],
    ids=["sticky-world-writable", "world-writable", "group-writable"],
)
@pytest.mark.parametrize("sink", _SINKS, ids=_SINK_IDS)
def test_a_weak_directory_anywhere_above_the_tree_is_refused(
    staged, senna_spawn, boxer_call, monkeypatch, sink, mode
):
    """The chain is judged from the filesystem root down, as the binary's is:
    a /tmp-like sticky directory, a world-writable or a group-writable one
    anywhere above the install lets another account swap the whole tree."""
    base, outside = staged
    name, install, inside, run = sink
    shared = os.path.join(base, "shared")
    os.mkdir(shared)
    tool = install(shared)
    os.chmod(shared, mode)
    try:
        # senna judges its binary first, so its refusal is the LookupError the
        # spawn's trust check has always raised; the others refuse the tree
        with pytest.raises((REFUSED, LookupError), match="not on a trusted path"):
            run(tool, monkeypatch)
    finally:
        os.chmod(shared, 0o700)
    assert senna_spawn == [] and boxer_call == []


@pytest.mark.skipif(not NOT_ROOT, reason="root owns every mode")
def test_removing_the_guard_lets_a_tree_behind_a_sticky_directory_build(
    staged, monkeypatch
):
    base, outside = staged
    shared = os.path.join(base, "shared")
    os.mkdir(shared)
    tool = _repp_install(shared)
    os.chmod(shared, 0o1777)
    monkeypatch.setattr(repp_mod, "validate_tool_data_dir", lambda p, context: p)
    try:
        cmd = _repp(tool).generate_repp_command(os.path.join(base, "in.txt"))
    finally:
        os.chmod(shared, 0o700)
    assert cmd[0] == tool + "/src/repp"


@pytest.mark.skipif(not POSIX, reason="symlinks")
@pytest.mark.parametrize("sink", _SINKS, ids=_SINK_IDS)
def test_a_private_link_above_the_tree_is_followed_and_the_resolved_tree_handed_over(
    staged, senna_spawn, boxer_call, monkeypatch, sink
):
    """A symlink higher up the chain (an ``installs`` link to a private
    place) is followed like the binary's own, and what the tool gets is the
    resolved tree, never the spelling through the link."""
    base, outside = staged
    name, install, inside, run = sink
    real_parent = os.path.join(outside, "installs")
    os.mkdir(real_parent)
    real_tool = install(real_parent)
    link = os.path.join(base, "installs")
    os.symlink(real_parent, link)
    via_link = os.path.join(link, os.path.basename(real_tool))
    if name == "repp":
        cmd = run(via_link, monkeypatch)
        got = cmd[cmd.index("-c") + 1]
        want = os.path.realpath(real_tool) + "/erg/repp.set"
    else:
        with pytest.raises(_Spawned):
            run(via_link, monkeypatch)
        if name == "senna":
            ((_, argv),) = senna_spawn
            got = argv[argv.index("-path") + 1]
            want = os.path.realpath(real_tool) + os.sep
        else:
            ((_, args),) = boxer_call
            got = args[args.index("--models") + 1]
            want = os.path.realpath(os.path.join(real_tool, "models", "boxer"))
    assert got == want
    assert not got.startswith(link + os.sep)


def _enrich(kind, tree, inside):
    """Ordinary contents an install may well have; none of them is a
    weakness and every one must still be accepted."""
    where = os.path.join(tree, inside) if inside else tree
    if kind == "dotfile":
        with open(os.path.join(where, ".hidden"), "w") as handle:
            handle.write("x")
    elif kind == "empty-subdir":
        os.mkdir(os.path.join(where, "empty"))
    elif kind == "read-only-member":
        path = os.path.join(where, "readonly.dat")
        with open(path, "w") as handle:
            handle.write("x")
        os.chmod(path, 0o444)
    elif kind == "executable-member":
        _executable(os.path.join(where, "helper"))
    elif kind == "nested-clean-subtree":
        deep = os.path.join(where, "a", "b", "c")
        os.makedirs(deep)
        for name in ("one", "two"):
            with open(os.path.join(deep, name), "w") as handle:
                handle.write(name)
    elif kind == "many-members":
        crowd = os.path.join(where, "crowd")
        os.mkdir(crowd)
        for i in range(200):
            with open(os.path.join(crowd, f"f{i}"), "w") as handle:
                handle.write("x")
    else:  # pragma: no cover
        raise ValueError(kind)


_BENIGN = [
    "dotfile",
    "empty-subdir",
    "read-only-member",
    "executable-member",
    "nested-clean-subtree",
    "many-members",
]


@pytest.mark.parametrize("kind", _BENIGN)
@pytest.mark.parametrize("sink", _SINKS, ids=_SINK_IDS)
def test_an_ordinary_install_is_still_accepted(
    staged, senna_spawn, boxer_call, monkeypatch, sink, kind
):
    base, outside = staged
    name, install, inside, run = sink
    tool = install(base)
    _enrich(kind, tool, inside)
    if name == "repp":
        cmd = run(tool, monkeypatch)
        # repp spells its config path with "/" on every platform
        assert cmd[cmd.index("-c") + 1].endswith("/erg/repp.set")
    else:
        with pytest.raises(_Spawned):
            run(tool, monkeypatch)
        assert len(senna_spawn) + len(boxer_call) == 1


def test_the_guard_accepts_the_usual_spellings_of_the_same_directory(staged):
    base, outside = staged
    tool = _repp_install(base)
    checked = pathsec.validate_tool_data_dir(tool, context="test")
    assert pathsec.validate_tool_data_dir(tool + os.sep, context="test") == checked
    assert pathsec.validate_tool_data_dir(pathlib.Path(tool), context="test") == checked


@pytest.mark.parametrize(
    "spelling", ["dotdot", "nul", "trailing-dot", "trailing-space", "relative"]
)
def test_the_guard_refuses_unsafe_spellings_before_touching_the_disk(
    staged, spelling, monkeypatch
):
    base, outside = staged
    tool = _repp_install(base)
    if spelling == "relative":
        # the install's own name, relative to the working directory beside it
        # (a Windows runner's cwd and home sit on different drives, so no
        # relpath across them)
        monkeypatch.chdir(base)
        bad = os.path.basename(tool)
    else:
        bad = {
            "dotdot": os.path.join(tool, "..", "repp"),
            "nul": tool + "\0",
            "trailing-dot": tool + ".",
            "trailing-space": tool + " ",
        }[spelling]
    with pytest.raises(REFUSED, match="Security Violation"):
        pathsec.validate_tool_data_dir(bad, context="test")


def test_the_guard_refuses_a_tree_over_the_entry_bound(staged):
    base, outside = staged
    tool = _repp_install(base)
    crowd = os.path.join(tool, "erg", "crowd")
    os.mkdir(crowd)
    for i in range(pathsec.MAX_TOOL_DIR_ENTRIES):
        with open(os.path.join(crowd, f"f{i}"), "w"):
            pass
    with pytest.raises(REFUSED, match="too many"):
        pathsec.validate_tool_data_dir(tool, context="test")

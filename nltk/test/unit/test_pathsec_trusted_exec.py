"""Direct attack tests for the trusted-executable primitives in ``nltk.pathsec``.

These exercise ``resolve_trusted_executable`` / ``_resolve_private`` /
``is_private_dir`` / ``_private_stat`` / ``safe_env`` / ``spawn_trusted`` WITHOUT
going through the Senna wrapper, so every defensive check has its own adversarial
test: a world/group-writable directory or binary, a path under the shared
``/tmp`` (rejected even with the sticky bit), a symlink through an
attacker-writable directory, a ``..``/relative/NUL path, an owner other than us,
a FIFO/socket/directory/device in the executable slot, symlink loops, loader
variables in the environment, ``shell=True``, and a non-POSIX platform (which
fails closed). Real files with real ``chmod``/``symlink``/``mkfifo`` and real
``subprocess`` execution are used (no mocks), so a regression actually leaks
here rather than being papered over by a stub.

A benign install is staged with :func:`nltk.data.make_staging_dir`, i.e. inside a
private data root, because the strict resolver deliberately refuses ``/tmp``;
that is the only in-sandbox place a trusted binary may live on Linux.

They also lock the minimalism decisions: no ``/proc/self/fd`` fexecve dance, no
``safe_env(extra=...)`` escape hatch, no sticky-``/tmp`` traversal allowance, and
no Windows heuristic (all were attack surface without an in-scope payoff).
"""

import inspect
import os
import shutil
import socket
import stat
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

import nltk.data as nltk_data
import nltk.pathsec as ps

POSIX = pytest.mark.skipif(
    os.name != "posix", reason="POSIX ownership/permission model"
)


@pytest.fixture
def staging():
    """A private, in-sandbox base dir (never world-writable ``/tmp``). The strict
    resolver rejects ``/tmp`` even with the sticky bit, so a benign install must
    live under a private root; make_staging_dir is where NLTK stages output."""
    try:
        base = nltk_data.make_staging_dir(prefix="pathsec_test_", cleanup=True)
    except PermissionError as exc:
        pytest.skip(f"no writable in-sandbox NLTK data root to stage under: {exc}")
    return base


def _mkexec(dirpath, name="tool", mode=0o755, content="#!/bin/sh\nexit 0\n"):
    """Create an executable regular file and return its path."""
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, name)
    with open(path, "w") as handle:
        handle.write(content)
    os.chmod(path, mode)
    return path


# --------------------------------------------------------------------------- #
# is_private_dir: strict for BOTH data roots and the executable walk.           #
# --------------------------------------------------------------------------- #


def test_is_private_dir_keeps_its_documented_contract():
    """The docstring the reviewer asked to preserve must stay intact."""
    doc = ps.is_private_dir.__doc__ or ""
    assert "1777" in doc and "CWE-377" in doc and "Windows" in doc


@POSIX
def test_is_private_dir_rejects_world_and_group_writable(staging):
    d = os.path.join(staging, "d")
    os.mkdir(d)
    os.chmod(d, 0o755)
    assert ps.is_private_dir(d) is True
    os.chmod(d, 0o775)  # group-writable
    assert ps.is_private_dir(d) is False
    os.chmod(d, 0o777)  # world-writable
    assert ps.is_private_dir(d) is False


@POSIX
def test_is_private_dir_rejects_sticky_world_writable_tmp():
    """A shared sticky temp (/tmp, 1777) is refused: strict, no sticky exception."""
    if not (os.path.isdir("/tmp") and os.stat("/tmp").st_mode & stat.S_ISVTX):
        pytest.skip("/tmp is not a sticky world-writable dir here")
    assert ps.is_private_dir("/tmp") is False


@POSIX
def test_is_private_dir_rejects_non_directory_and_missing(staging):
    f = _mkexec(staging, "f")
    assert ps.is_private_dir(f) is False
    assert ps.is_private_dir(os.path.join(staging, "nope")) is False


@POSIX
def test_is_private_dir_rejects_dir_owned_by_another_user(staging, monkeypatch):
    d = os.path.join(staging, "d")
    os.mkdir(d)
    os.chmod(d, 0o755)
    other = os.geteuid() + 4242  # capture before patching to avoid recursion
    monkeypatch.setattr(ps.os, "geteuid", lambda: other)
    assert ps.is_private_dir(d) is False


# --------------------------------------------------------------------------- #
# _resolve_private: input hygiene + component-wise symlink safety, strict.       #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "bad",
    ["relative/path", "bin/sh", "", ".", "..", "a/b"],
)
def test_resolve_private_refuses_relative_input(bad):
    assert ps._resolve_private(bad) is None


@POSIX  # _resolve_private is POSIX-internal (uses os.geteuid via the dir check)
def test_resolve_private_refuses_parent_traversal_without_folding():
    """'..' is refused, never folded lexically (folding would skip a symlink)."""
    assert ps._resolve_private("/usr/../bin/sh") is None
    assert ps._resolve_private("/a/b/../../etc/passwd") is None


def test_resolve_private_refuses_nul_and_non_str():
    assert ps._resolve_private("/bin/sh\x00") is None
    assert ps._resolve_private(b"/bin/sh") is None  # os.fspath keeps bytes -> refused
    assert ps._resolve_private(1234) is None  # not a path-like -> None, not TypeError


@POSIX
def test_resolve_private_accepts_private_staging_chain(staging):
    binp = _mkexec(os.path.join(staging, "install"), "tool")
    assert ps._resolve_private(binp) == os.path.realpath(binp)


@POSIX
def test_resolve_private_refuses_world_writable_ancestor(staging):
    install = os.path.join(staging, "install")
    binp = _mkexec(install, "tool")
    os.chmod(install, 0o777)  # world-writable holding dir
    assert ps._resolve_private(binp) is None


@POSIX
def test_resolve_private_refuses_path_under_shared_tmp():
    """The whole point of going strict: a path under world-writable /tmp is
    refused, even though the leaf dir we create is a private 0700 mkdtemp."""
    if not (os.path.isdir("/tmp")):
        pytest.skip("no /tmp")
    if not (os.stat("/tmp").st_mode & (stat.S_IWGRP | stat.S_IWOTH)):
        pytest.skip("/tmp is not world-writable here")
    d = tempfile.mkdtemp(dir="/tmp")
    try:
        binp = _mkexec(d, "tool")
        assert ps._resolve_private(binp) is None
        assert ps.resolve_trusted_executable(binp) is None
    finally:
        shutil.rmtree(d, ignore_errors=True)


@POSIX
def test_resolve_private_refuses_intermediate_symlink_through_writable_dir(staging):
    """A link that passes THROUGH an attacker-writable directory is refused;
    os.path.realpath would collapse the hop and miss it (CWE-427)."""
    final = os.path.join(staging, "usr", "local", "private")
    os.makedirs(final)
    _mkexec(final, "tool")

    srv = os.path.join(staging, "srv")
    os.makedirs(os.path.join(srv, "links"))
    os.symlink(final, os.path.join(srv, "links", "bin"))  # intermediate hop
    os.chmod(srv, 0o777)  # attacker can repoint srv/links/bin

    os.makedirs(os.path.join(staging, "opt"))
    os.symlink(os.path.join(srv, "links", "bin"), os.path.join(staging, "opt", "bin"))
    target = os.path.join(staging, "opt", "bin", "tool")
    assert ps._resolve_private(target) is None


@POSIX
def test_resolve_private_follows_symlink_to_private_target(staging):
    real_dir = os.path.join(staging, "real")
    binp = _mkexec(real_dir, "tool")
    link = os.path.join(staging, "link")
    os.symlink(real_dir, link)  # link -> private dir
    assert ps._resolve_private(os.path.join(link, "tool")) == os.path.realpath(binp)


@POSIX
def test_resolve_private_bounds_symlink_loops(staging):
    a = os.path.join(staging, "a")
    b = os.path.join(staging, "b")
    os.symlink(b, a)
    os.symlink(a, b)  # a -> b -> a -> ...
    assert ps._resolve_private(os.path.join(a, "x")) is None  # terminates, not a hang


# --------------------------------------------------------------------------- #
# resolve_trusted_executable / is_trusted_executable.                          #
# --------------------------------------------------------------------------- #


@POSIX  # /bin/sh is a POSIX system binary
def test_resolve_trusted_executable_accepts_system_binary():
    real = ps.resolve_trusted_executable("/bin/sh")
    assert real and os.path.isabs(real)
    assert ps.is_trusted_executable("/bin/sh") is True


@POSIX
def test_resolve_trusted_executable_accepts_staged_install(staging):
    binp = _mkexec(os.path.join(staging, "install"), "tool")
    assert ps.resolve_trusted_executable(binp) == os.path.realpath(binp)


@POSIX
def test_resolve_trusted_executable_rejects_world_writable_binary(staging):
    binp = _mkexec(os.path.join(staging, "install"), "tool", mode=0o777)
    assert ps.resolve_trusted_executable(binp) is None
    assert ps.is_trusted_executable(binp) is False


@POSIX
def test_resolve_trusted_executable_rejects_group_writable_binary(staging):
    binp = _mkexec(os.path.join(staging, "install"), "tool", mode=0o775)
    assert ps.resolve_trusted_executable(binp) is None


@POSIX
def test_resolve_trusted_executable_rejects_directory_fifo_socket_device(staging):
    d = os.path.join(staging, "adir")
    os.mkdir(d)
    assert ps.resolve_trusted_executable(d) is None  # a directory

    fifo = os.path.join(staging, "fifo")
    os.mkfifo(fifo)
    assert ps.resolve_trusted_executable(fifo) is None  # a FIFO would block

    sockpath = os.path.join(staging, "sock")
    if len(sockpath) < 100:  # AF_UNIX paths are capped near 108 bytes
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            srv.bind(sockpath)
            assert ps.resolve_trusted_executable(sockpath) is None  # a socket
        finally:
            srv.close()

    if os.path.exists("/dev/null"):
        assert ps.resolve_trusted_executable("/dev/null") is None  # a device


@POSIX
def test_resolve_trusted_executable_rejects_symlink_to_writable_target(staging):
    target_dir = os.path.join(staging, "wt")
    tgt = _mkexec(target_dir, "real")
    os.chmod(target_dir, 0o777)  # target lives in an attacker-writable dir
    link = os.path.join(staging, "clean", "keep")
    os.makedirs(os.path.dirname(link))
    os.symlink(tgt, link)  # private holder, but link resolves into the writable one
    assert ps.resolve_trusted_executable(link) is None


@POSIX
def test_resolve_trusted_executable_rejects_binary_owned_by_other(staging, monkeypatch):
    binp = _mkexec(os.path.join(staging, "install"), "tool")
    other = os.geteuid() + 4242
    monkeypatch.setattr(ps.os, "geteuid", lambda: other)
    assert ps.resolve_trusted_executable(binp) is None


# --------------------------------------------------------------------------- #
# Non-POSIX platform fails CLOSED (no Windows heuristic to fool).               #
# --------------------------------------------------------------------------- #


def test_non_posix_platform_fails_closed(monkeypatch):
    """On a non-POSIX os.name the resolver refuses everything: POSIX mode bits do
    not answer 'who can write this path' on Windows, and NLTK does not assume
    win32security, so the safe answer is to refuse rather than guess from env."""
    monkeypatch.setattr(ps.os, "name", "nt")
    assert ps.resolve_trusted_executable("/bin/sh") is None
    assert ps.is_trusted_executable("/bin/sh") is False
    with pytest.raises(ps.TrustError):
        ps.spawn_trusted("/bin/sh", ["-c", "true"])


# --------------------------------------------------------------------------- #
# safe_env: a whitelist, with no reintroduction path.                          #
# --------------------------------------------------------------------------- #


# Every environment variable that can redirect a dynamic linker, loader,
# interpreter, charset/locale module, terminfo/message catalog, shell word split,
# or temp/config lookup. None may survive safe_env(): the whitelist drops them all
# by default. Kept deliberately broad ("benign or not") so a new attack variable
# added here fails loudly if it ever slips into _ENV_KEEP.
_DANGEROUS_ENV = [
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "LD_AUDIT",
    "LD_ORIGIN_PATH",
    "LD_PROFILE",
    "LD_DEBUG",
    "LD_ASSUME_KERNEL",
    "LD_CONFIG",
    "LD_BIND_NOW",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
    "DYLD_FRAMEWORK_PATH",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "DYLD_FALLBACK_FRAMEWORK_PATH",
    "DYLD_VERSIONED_LIBRARY_PATH",
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONEXECUTABLE",
    "PYTHONWARNINGS",
    "PERL5LIB",
    "PERLLIB",
    "PERL5OPT",
    "RUBYLIB",
    "RUBYOPT",
    "NODE_OPTIONS",
    "NODE_PATH",
    "CLASSPATH",
    "JAVA_TOOL_OPTIONS",
    "_JAVA_OPTIONS",
    "GCONV_PATH",
    "LOCPATH",
    "NLSPATH",
    "HOSTALIASES",
    "RES_OPTIONS",
    "TERMINFO",
    "TERMINFO_DIRS",
    "TERMPATH",
    "TMPDIR",
    "TMP",
    "TEMP",
    "IFS",
    "BASH_ENV",
    "ENV",
    "CDPATH",
    "GLOBIGNORE",
    "SHELLOPTS",
    "BASHOPTS",
    "PS4",
    "PROMPT_COMMAND",
    "MALLOC_CONF",
    "MANPATH",
    "XDG_CONFIG_HOME",
    "XDG_DATA_DIRS",
]


def test_safe_env_drops_all_known_dangerous_vars(monkeypatch):
    """Deny-by-default: not one of a broad set of loader/interpreter/locale/shell
    redirection variables survives, whether or not a denylist ever named it."""
    for var in _DANGEROUS_ENV:
        monkeypatch.setenv(var, "/evil")
    env = ps.safe_env()
    leaked = [var for var in _DANGEROUS_ENV if var in env]
    assert not leaked, f"safe_env leaked: {leaked}"
    # And nothing outside the whitelist (plus PATH) is kept at all.
    assert set(env) <= (set(ps._ENV_KEEP) | {"PATH"})


def test_safe_env_keeps_whitelisted_and_scrubs_path(monkeypatch):
    monkeypatch.setenv("PATH", "/attacker/bin")
    monkeypatch.setenv("LANG", "en_US.UTF-8")  # a whitelisted var is kept
    env = ps.safe_env()
    assert env.get("LANG") == "en_US.UTF-8"
    assert "/attacker/bin" not in env["PATH"].split(os.pathsep)


def test_safe_env_path_denies_resolution_and_is_never_cwd():
    """The child PATH resolves nothing (a trusted binary is run by absolute path,
    so it needs no PATH) and is never empty. An EMPTY or unset PATH is searched as
    the current directory by execvp/subprocess, so it must be a single directory
    with no executables, not '' (CWE-426)."""
    path = ps.safe_env()["PATH"]
    assert path == ps._LOCKED_PATH
    # Never empty and never an empty element (which is searched as the CWD). This
    # is the cross-platform invariant.
    assert path
    assert "" not in path.split(os.pathsep), "an empty PATH element is the CWD"
    # The sentinel is a POSIX-absolute directory with no executables. On Windows,
    # spawn_trusted fails closed, so this PATH never gates a real exec; a leading
    # slash is drive-relative there, so the absoluteness check is POSIX-only.
    if os.name == "posix":
        assert os.path.isabs(path), "a relative PATH element is CWD-relative"
        assert not os.path.isdir(path) or not os.listdir(path)  # nothing to find


def test_safe_env_has_no_extra_escape_hatch():
    """A caller must NOT be able to reintroduce a loader variable, so safe_env
    deliberately takes no parameters."""
    assert list(inspect.signature(ps.safe_env).parameters) == []


# --------------------------------------------------------------------------- #
# spawn_trusted: choke point (no shell, scrubbed env, verified path).          #
# --------------------------------------------------------------------------- #


@pytest.fixture
def _popen_spy(monkeypatch):
    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        calls.append(
            SimpleNamespace(
                argv=list(cmd),
                shell=k.get("shell", False),
                env=k.get("env"),
                executable=k.get("executable"),
                close_fds=k.get("close_fds"),
            )
        )
        return _FakeProc()

    monkeypatch.setattr(ps.subprocess, "Popen", _fake_popen)
    return calls


def test_spawn_trusted_refuses_shell():
    with pytest.raises(ValueError):
        ps.spawn_trusted("/bin/sh", ["-c", "true"], shell=True)


def test_spawn_trusted_refuses_untrusted_target(staging):
    with pytest.raises(ps.TrustError):
        ps.spawn_trusted(os.path.join(staging, "does-not-exist"))


@POSIX
def test_spawn_trusted_refuses_world_writable_target(staging):
    binp = _mkexec(os.path.join(staging, "install"), "tool", mode=0o777)
    with pytest.raises(ps.TrustError):
        ps.spawn_trusted(binp)


@POSIX  # resolves /bin/sh, which only exists on POSIX
def test_spawn_trusted_defaults_are_safe(_popen_spy):
    ps.spawn_trusted("/bin/sh", ["-c", "true"])
    assert len(_popen_spy) == 1
    call = _popen_spy[0]
    assert call.shell is False
    assert call.close_fds is True
    assert call.executable == os.path.realpath("/bin/sh")
    assert call.argv[0] == os.path.realpath("/bin/sh")  # argv[0] is the resolved path
    assert not call.executable.startswith("/proc/")  # no /proc/self/fd indirection
    assert "LD_PRELOAD" not in (call.env or {})
    # PATH is the deny-sentinel: non-empty, absolute, resolves no command.
    child_path = (call.env or {}).get("PATH", "")
    assert child_path == ps._LOCKED_PATH
    assert "" not in child_path.split(os.pathsep)  # no CWD element


@POSIX
def test_spawn_trusted_really_scrubs_child_environment(staging, monkeypatch):
    marker = os.path.join(staging, "childenv.txt")
    script = (
        "#!/bin/sh\n"
        '{ echo "LD_PRELOAD=[$LD_PRELOAD]"; echo "PYTHONPATH=[$PYTHONPATH]"; '
        'echo "DYLD=[$DYLD_INSERT_LIBRARIES]"; echo "PATH=[$PATH]"; } > "%s"\n' % marker
    )
    binp = _mkexec(os.path.join(staging, "install"), "tool", content=script)
    monkeypatch.setenv("LD_PRELOAD", "/evil.so")
    monkeypatch.setenv("PYTHONPATH", "/evil")
    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/evil.dylib")

    proc = ps.spawn_trusted(binp)
    proc.communicate()
    reported = open(marker).read()
    assert "LD_PRELOAD=[]" in reported, reported
    assert "PYTHONPATH=[]" in reported, reported
    assert "DYLD=[]" in reported, reported
    assert ("PATH=[%s]" % ps._LOCKED_PATH) in reported, reported  # deny-sentinel


@POSIX
def test_spawn_trusted_child_cannot_resolve_bare_command_from_cwd(
    staging, tmp_path, monkeypatch
):
    """Real execution: with the locked PATH a trusted child cannot resolve a
    bare-name command, and in particular cannot reach a planted ./tool in the
    current directory, so a shell-out on attacker input finds nothing (CWE-426).
    An empty PATH here WOULD run the CWD tool (verified separately), which is why
    the sentinel is used instead."""
    marker = tmp_path / "evil_ran.marker"
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    evil = cwd / "eviltool"
    evil.write_text('#!/bin/sh\n: > "%s"\n' % marker)
    os.chmod(evil, 0o755)
    monkeypatch.chdir(cwd)  # the child inherits this CWD (spawn_trusted sets no cwd)

    # A trusted stub that tries to run 'eviltool' by BARE name.
    stub = _mkexec(
        os.path.join(staging, "install"), "tool", content="#!/bin/sh\neviltool\n"
    )
    proc = ps.spawn_trusted(stub)
    proc.communicate()
    assert not marker.exists(), "child resolved a bare command from the CWD"


@POSIX
def test_spawn_trusted_runs_the_verified_binary(staging):
    binp = _mkexec(
        os.path.join(staging, "install"),
        "tool",
        content="#!/bin/sh\nprintf ran\n",
    )
    proc = ps.spawn_trusted(binp, stdout=subprocess.PIPE)
    out, _ = proc.communicate()
    assert out == b"ran"


# --------------------------------------------------------------------------- #
# Minimalism locks: strict resolver, no removed machinery.                     #
# --------------------------------------------------------------------------- #


def test_removed_attack_surface_stays_removed():
    for gone in (
        "_resolve_trusted_windows",
        "_windows_trusted_roots",
        "_WINDOWS_TRUSTED_ROOT_KEYS",
        "_dir_is_traversal_safe",
        "_traversal_dir_ok",
    ):
        assert not hasattr(ps, gone), gone

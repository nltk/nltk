"""Regression tests for the untrusted-executable hardening in the Senna wrapper.

``Senna`` builds its subprocess command from ``self.executable(self._path)``, and
``self._path`` is a plain, mutable attribute, so ``tag_sents`` re-validates it
right before spawning:

* it must be an ABSOLUTE string. A relative (or non-str) value makes
  ``executable()`` a path with a separator that ``subprocess.Popen`` runs from
  the current working directory without consulting ``$PATH`` (CWE-426/CWE-427),
  so a planted ``senna-<platform>`` file would execute.
* even an absolute path is refused if the binary, its symlink target, or any
  directory up to the root is group/world-writable or not owned by the user or
  root, since another local user could then swap the binary (CWE-426/CWE-732).
* a CR/LF in an input token is refused, since it would smuggle an extra input
  line and break senna's 1:1 sentence->output mapping (CWE-93).
"""

import os
from pathlib import Path
from platform import architecture, system
from types import SimpleNamespace

import pytest

import nltk.classify.senna as senna_mod
import nltk.data as _nltk_data
from nltk.classify.senna import Senna


def _staging(prefix="senna_test_"):
    """A private, in-sandbox base dir (never world-writable ``/tmp``). The strict
    trust check refuses ``/tmp`` even when sticky, so a benign senna install must
    live under a private data root; make_staging_dir is where NLTK stages output.
    Skips the test if no writable in-sandbox root exists."""
    try:
        return _nltk_data.make_staging_dir(prefix=prefix, cleanup=True)
    except PermissionError as exc:
        pytest.skip(f"no writable in-sandbox NLTK data root to stage under: {exc}")


# Every platform-specific binary name executable() may pick.
_SENNA_BINARIES = (
    "senna-linux64",
    "senna-linux32",
    "senna-win32.exe",
    "senna-osx",
    "senna",
)


def _this_platforms_binary():
    """The exact binary name ``Senna.executable`` selects on THIS platform, so a
    reassignment test plants the file the wrapper will actually look for."""
    os_name = system()
    if os_name == "Linux":
        return "senna-linux64" if architecture()[0] == "64bit" else "senna-linux32"
    if os_name == "Windows":
        return "senna-win32.exe"
    if os_name == "Darwin":
        return "senna-osx"
    return "senna"


def _plant_senna_binaries(directory):
    """Create an (executable) file for every candidate senna binary name."""
    os.makedirs(directory, exist_ok=True)
    for name in _SENNA_BINARIES:
        target = os.path.join(directory, name)
        with open(target, "wb"):
            pass
        os.chmod(target, 0o755)
    return directory


def test_cwd_senna_binary_is_not_picked_up(tmp_path, monkeypatch):
    """A senna-<platform> planted in the CWD must not be auto-selected."""
    _plant_senna_binaries(str(tmp_path))  # attacker-planted in the CWD
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SENNA", raising=False)

    with pytest.raises(LookupError):
        Senna(".", ["pos"])


def test_cwd_does_not_override_configured_senna(tmp_path, monkeypatch):
    """A CWD directory must not shadow an absolute SENNA environment variable."""
    cwd = tmp_path / "cwd"
    _plant_senna_binaries(str(cwd))  # attacker-planted in the CWD
    trusted = tmp_path / "trusted"
    _plant_senna_binaries(str(trusted))  # the configured (trusted) location
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("SENNA", str(trusted))

    senna = Senna(".", ["pos"])
    assert os.path.realpath(senna._path) == os.path.realpath(
        str(trusted)
    ), "CWD directory overrode the trusted SENNA location"


def test_relative_senna_env_is_rejected(tmp_path, monkeypatch):
    """A relative SENNA environment variable must not be resolved against CWD."""
    _plant_senna_binaries(str(tmp_path))  # attacker-planted in the CWD
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SENNA", ".")

    with pytest.raises(LookupError):
        Senna(".", ["pos"])


def test_absolute_path_still_accepted(tmp_path, monkeypatch):
    """An explicit absolute directory is still used as-is."""
    abs_dir = _plant_senna_binaries(str(tmp_path / "senna"))
    monkeypatch.delenv("SENNA", raising=False)

    senna = Senna(abs_dir, ["pos"])
    assert os.path.realpath(senna._path) == os.path.realpath(abs_dir)


def test_absolute_path_without_executable_raises(tmp_path, monkeypatch):
    """An absolute senna_path with no senna binary fails fast (not deferred)."""
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.delenv("SENNA", raising=False)

    with pytest.raises(LookupError):
        Senna(str(empty), ["pos"])


# --- Re-validation at invocation (path reassigned after construction) ---------
# self._path is a plain attribute; reassigning it to a relative value after
# __init__ makes executable() a CWD-relative path that Popen runs without $PATH,
# giving code execution to a planted senna-<platform> file (CWE-426/CWE-427).


@pytest.fixture
def _senna_popen_spy(monkeypatch):
    """Record the spawn without launching senna. senna now spawns through
    ``pathsec.spawn_trusted``, which does the real trust check and env scrub
    before calling ``subprocess.Popen``; patching Popen there lets an untrusted
    path still be rejected (no call recorded) while a trusted one is captured."""
    import nltk.pathsec as pathsec_mod

    real_popen = pathsec_mod.subprocess.Popen  # capture BEFORE patching
    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        argv = list(cmd)
        # On Linux, Senna.executable() runs `file` via platform.architecture()
        # through this same patched subprocess; delegate that probe to the real
        # Popen so bit-width detection works, and record only the senna spawn.
        if argv[:1] == ["file"]:
            return real_popen(cmd, *a, **k)
        calls.append(
            SimpleNamespace(
                argv=argv,
                shell=k.get("shell", False),
                env=k.get("env"),
                executable=k.get("executable"),
            )
        )
        return _FakeProc()

    monkeypatch.setattr(pathsec_mod.subprocess, "Popen", _fake_popen)
    return calls


def _make_abs_senna(tmp_path, monkeypatch):
    """Construct a Senna pointed at a valid absolute install directory, staged
    under a private data root so the strict trust check accepts it on Linux."""
    absdir = Path(_staging()) / "senna-install"
    absdir.mkdir()
    binpath = absdir / _this_platforms_binary()
    binpath.write_bytes(b"")
    os.chmod(binpath, 0o755)
    monkeypatch.delenv("SENNA", raising=False)
    return Senna(str(absdir), ["pos"]), str(absdir)


@pytest.mark.parametrize("relative_path", [".", "." + os.sep, "senna-cwd", ""])
def test_relative_path_reassigned_after_construction_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, relative_path
):
    """Reassigning ``_path`` to a relative value must be refused at ``tag_sents``,
    before any spawn, even though a matching binary sits in the CWD."""
    senna, _absdir = _make_abs_senna(tmp_path, monkeypatch)

    # Attacker plants the platform binary in the CWD and reassigns the path.
    cwd = tmp_path / "attacker_cwd"
    cwd.mkdir()
    binname = _this_platforms_binary()
    (cwd / binname).write_bytes(b"")
    os.chmod(cwd / binname, 0o755)
    monkeypatch.chdir(cwd)

    senna._path = relative_path
    with pytest.raises(LookupError):
        senna.tag_sents([["hello", "world"]])
    assert _senna_popen_spy == [], "a CWD-relative senna binary reached the spawn"


@pytest.mark.skipif(
    not hasattr(os, "getuid"),
    reason="these assertions exercise the POSIX ownership model; on Windows the "
    "exec-trust check is best-effort (a separate path), so this is POSIX-focused",
)
def test_absolute_path_still_reaches_the_spawn_after_revalidation(
    tmp_path, monkeypatch, _senna_popen_spy
):
    """Benign control: a valid absolute install still reaches the (trapped) spawn
    with an ABSOLUTE argv[0] and no shell, so the re-validation is not over-broad."""
    senna, absdir = _make_abs_senna(tmp_path, monkeypatch)
    senna.tag_sents([["hi", "there"]])
    assert len(_senna_popen_spy) == 1
    argv = _senna_popen_spy[0].argv
    assert os.path.isabs(argv[0])
    # spawn_trusted executes the fully RESOLVED path (symlinks collapsed).
    assert argv[0] == os.path.realpath(
        os.path.join(senna._path.rstrip(os.sep), _this_platforms_binary())
    )
    assert _senna_popen_spy[0].shell is False
    # The child env is scrubbed of loader/interpreter variables (no LD_*/DYLD_*).
    child_env = _senna_popen_spy[0].env or {}
    assert not any(
        k.startswith(("LD_", "DYLD_")) or k in ("PYTHONPATH", "PYTHONHOME")
        for k in child_env
    )
    # The -path argument (senna's data dir) is the absolute install directory.
    assert argv[argv.index("-path") + 1] == senna._path
    assert os.path.isabs(argv[argv.index("-path") + 1])


@pytest.mark.parametrize(
    "bad_path", [None, 123, 1.5, b"/abs/senna", ["/abs"], ("/abs",)]
)
def test_non_string_path_reassigned_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, bad_path
):
    """A non-str _path must raise LookupError (not a raw TypeError from path.join)
    and must never spawn."""
    senna, _ = _make_abs_senna(tmp_path, monkeypatch)
    senna._path = bad_path
    with pytest.raises(LookupError):
        senna.tag_sents([["hello"]])
    assert _senna_popen_spy == []


requires_posix_perms = pytest.mark.skipif(
    not hasattr(os, "getuid"), reason="POSIX ownership/permission model"
)


def _senna_install(
    tmp_path,
    *,
    dir_mode=0o755,
    bin_mode=0o755,
    symlink_target_mode=None,
    ww_ancestor=False,
):
    """Build an ABSOLUTE senna install under a private staged root exhibiting one
    permission weakness (or none, for the benign control). Staged under a data
    root (not /tmp) so any refusal is due to the injected weakness, not the
    shared-temp ancestor that the strict resolver already rejects."""
    base = Path(_staging())
    root = base / "root"
    root.mkdir()
    absdir = root / "senna"
    absdir.mkdir()
    binpath = absdir / _this_platforms_binary()
    if symlink_target_mode is not None:
        # Staged under the SAME private base, so the only weakness is the target
        # file's mode (world/group-writable), not a shared-temp ancestor.
        target = base / "symlink_target"
        target.write_bytes(b"")
        os.chmod(target, symlink_target_mode)
        os.symlink(target, binpath)
    else:
        binpath.write_bytes(b"")
        os.chmod(binpath, bin_mode)
    os.chmod(absdir, dir_mode)
    if ww_ancestor:
        os.chmod(root, 0o777)
    return str(absdir)


@requires_posix_perms
@pytest.mark.parametrize(
    "weakness",
    [
        {"dir_mode": 0o777},  # world-writable senna dir
        {"dir_mode": 0o775},  # group-writable senna dir
        {"bin_mode": 0o777},  # world-writable binary
        {"bin_mode": 0o775},  # group-writable binary
        {"symlink_target_mode": 0o777},  # symlink -> world-writable target
        {"ww_ancestor": True},  # world-writable ancestor directory
    ],
)
def test_untrusted_absolute_path_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, weakness
):
    """An ABSOLUTE path is still refused when the binary, its symlink target, or an
    ancestor is group/world-writable: another local user could swap the binary
    before Popen runs it (CWE-426/CWE-732). No spawn happens."""
    monkeypatch.delenv("SENNA", raising=False)
    senna = Senna(_senna_install(tmp_path, **weakness), ["pos"])
    with pytest.raises(LookupError):
        senna.tag_sents([["hello"]])
    assert _senna_popen_spy == []


@requires_posix_perms
def test_binary_owned_by_another_user_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy
):
    """A senna binary not owned by us (or root) is refused even with a benign mode:
    ownership is kernel truth an attacker cannot fake. getuid is patched to a
    different uid to stand in for 'owned by another local user'."""
    monkeypatch.delenv("SENNA", raising=False)
    senna = Senna(_senna_install(tmp_path), ["pos"])
    other_uid = os.geteuid() + 4242  # capture BEFORE patching to avoid recursion
    monkeypatch.setattr("nltk.pathsec.os.geteuid", lambda: other_uid)
    with pytest.raises(LookupError):
        senna.tag_sents([["hello"]])
    assert _senna_popen_spy == []


@requires_posix_perms
def test_secure_absolute_install_reaches_spawn(tmp_path, monkeypatch, _senna_popen_spy):
    """Benign control: a private, not-writable-by-others absolute install still
    reaches the (trapped) spawn with an absolute argv[0]."""
    monkeypatch.delenv("SENNA", raising=False)
    senna = Senna(_senna_install(tmp_path), ["pos"])
    senna.tag_sents([["hello", "world"]])
    assert len(_senna_popen_spy) == 1
    assert os.path.isabs(_senna_popen_spy[0].argv[0])


@pytest.mark.parametrize("bad_token", ["a\nb", "a\rb", "a\r\nb", "line1\nline2"])
def test_token_with_newline_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, bad_token
):
    """A CR/LF in a token would add an input line and break senna's 1:1
    sentence->output mapping (CWE-93); it must raise before spawning."""
    senna, _ = _make_abs_senna(tmp_path, monkeypatch)
    with pytest.raises(ValueError):
        senna.tag_sents([[bad_token, "ok"]])
    assert _senna_popen_spy == []


@pytest.mark.parametrize(
    "bad_op", ["path", "-path", "version", "../etc", "pos ner", "srl", "chk\n"]
)
def test_operation_injection_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy, bad_op
):
    """An operation outside SUPPORTED_OPERATIONS is turned into a '-<op>' senna
    argument, so an attacker-controlled value like 'path' would inject '-path' and
    redirect senna's data directory (CWE-88). It must raise before spawning."""
    senna, _ = _make_abs_senna(tmp_path, monkeypatch)
    senna.operations = ["pos", bad_op]  # a mutable attribute, like self._path
    with pytest.raises(ValueError):
        senna.tag_sents([["hello", "world"]])
    assert _senna_popen_spy == []


# --- End-to-end with a REAL, executable senna-contract binary -----------------
# These drop a REAL executable honouring SENNA's stdin/stdout contract at an
# absolute path and drive the whole real code path (real Popen/process/parsing,
# no mocks); the attacker copy touches a marker so a refusal proves it never ran.

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="the executable senna stub is a POSIX shell script",
)


def _write_real_senna(dirpath, marker=None):
    """Write a real, executable senna-contract program named for THIS platform.

    If *marker* is given, the program touches that path on execution, so a test
    can prove from its (non-)existence whether the binary actually ran.
    """
    os.makedirs(dirpath, exist_ok=True)
    lines = ["#!/bin/sh"]
    if marker is not None:
        # Quote to tolerate spaces; this fires only if the process is spawned.
        lines.append(': > "%s"' % marker)
    lines += [
        "while IFS= read -r line; do",
        '  [ -z "$line" ] && continue',
        "  for w in $line; do printf '%s\\tNNP\\n' \"$w\"; done",
        "  printf '\\n'",
        "done",
    ]
    binpath = os.path.join(dirpath, _this_platforms_binary())
    with open(binpath, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(binpath, 0o755)
    return binpath


@POSIX_ONLY
def test_real_senna_binary_tags_end_to_end(tmp_path, monkeypatch):
    """Benign, fully real: an absolute install with a runnable senna-contract
    binary tags a sentence through the real subprocess and parser."""
    from nltk.tag import SennaTagger

    absdir = os.path.join(_staging(), "senna-v3.0")
    _write_real_senna(absdir)
    monkeypatch.delenv("SENNA", raising=False)

    tagger = SennaTagger(absdir)
    tagged = tagger.tag("What is the airspeed ?".split())
    assert [w for w, _ in tagged] == ["What", "is", "the", "airspeed", "?"]
    assert all(tag == "NNP" for _, tag in tagged)  # the real binary's output


@POSIX_ONLY
def test_real_cwd_senna_binary_never_executes_when_path_reassigned(
    tmp_path, monkeypatch
):
    """Teeth with a REAL binary: a runnable senna-<platform> is planted in the CWD
    and ``_path`` is reassigned to ``.`` after construction. The planted binary is
    demonstrably executable (running it directly touches the marker), yet
    ``tag_sents`` raises before spawning, so the marker the binary would create
    never appears; the guard stops code execution, not just a missing file."""
    import subprocess

    from nltk.tag import SennaTagger

    # A valid absolute install so construction succeeds (private staged root).
    absdir = os.path.join(_staging(), "trusted")
    _write_real_senna(absdir)
    monkeypatch.delenv("SENNA", raising=False)
    tagger = SennaTagger(absdir)

    # Attacker plants a genuinely-runnable senna in the CWD that touches a marker.
    cwd = tmp_path / "attacker_cwd"
    marker = tmp_path / "senna_executed.marker"
    attacker_bin = _write_real_senna(str(cwd), marker=str(marker))
    monkeypatch.chdir(cwd)

    # Prove the planted binary really runs (would tag + create the marker).
    proof_marker = tmp_path / "proof.marker"
    proof_bin = _write_real_senna(str(tmp_path / "proof"), marker=str(proof_marker))
    subprocess.run([proof_bin], input=b"hello world\n", capture_output=True, check=True)
    assert proof_marker.exists(), "sanity: the stub is genuinely executable"

    # Now reassign to a relative path and confirm tag_sents refuses BEFORE exec.
    tagger._path = "." + os.sep
    assert os.path.isfile(attacker_bin)  # the CWD binary the guard must not run
    with pytest.raises(LookupError):
        tagger.tag_sents([["hello", "world"]])
    assert not marker.exists(), "the CWD senna binary was executed despite the guard"


@POSIX_ONLY
def test_real_world_writable_binary_never_executes(tmp_path, monkeypatch):
    """Teeth with a REAL binary: a runnable senna in a WORLD-WRITABLE install
    touches a marker when run, yet tag_sents refuses before spawning, so the
    marker never appears; the trusted-path guard stops real code execution."""
    import subprocess

    from nltk.tag import SennaTagger

    absdir = os.path.join(_staging(), "ww-install")
    marker = tmp_path / "ww_executed.marker"
    binpath = _write_real_senna(absdir, marker=str(marker))
    os.chmod(absdir, 0o777)  # world-writable: another user could swap the binary
    monkeypatch.delenv("SENNA", raising=False)
    tagger = SennaTagger(absdir)

    # Prove the binary genuinely runs on its own (creates the marker).
    subprocess.run([binpath], input=b"hi\n", capture_output=True)
    assert marker.exists(), "sanity: the stub is genuinely executable"
    marker.unlink()

    # tag_sents must refuse and never spawn the world-writable binary.
    with pytest.raises(LookupError):
        tagger.tag_sents([["hello", "world"]])
    assert not marker.exists(), "a world-writable senna binary was executed"


@POSIX_ONLY
def test_real_metacharacter_input_is_not_shell_evaluated(tmp_path, monkeypatch):
    """Real binary + real Popen: shell metacharacters in tokens are fed to senna's
    stdin, not a shell (Popen uses a list, no shell=True), so no command runs."""
    from nltk.tag import SennaTagger

    absdir = os.path.join(_staging(), "trusted")
    _write_real_senna(absdir)
    monkeypatch.delenv("SENNA", raising=False)
    tagger = SennaTagger(absdir)

    marker = tmp_path / "injected.marker"
    # Two tokens so the token count matches senna's word-split output (no
    # misalignment); joined they form "$(touch <marker>)", which must stay inert.
    payload = ["$(touch", "%s)" % marker]
    try:
        tagger.tag_sents([payload])
    except Exception:
        pass  # a misalignment on odd input is fine; we only assert no injection
    assert not marker.exists(), "shell metacharacters in input were evaluated"


@requires_posix_perms
def test_intermediate_symlink_through_writable_dir_is_refused(
    tmp_path, monkeypatch, _senna_popen_spy
):
    """The executable path passes THROUGH a symlink whose holding directory is
    world-writable. os.path.realpath would collapse the hop; the component-wise
    resolver checks every intermediate link directory and refuses (CWE-427)."""
    monkeypatch.delenv("SENNA", raising=False)
    binname = _this_platforms_binary()

    # Staged under a private base so the ONLY weakness is the world-writable
    # intermediate `srv`, not the shared-temp ancestor.
    base = Path(_staging())
    final = base / "usr" / "local" / "private"
    final.mkdir(parents=True)
    (final / binname).write_bytes(b"")
    os.chmod(final / binname, 0o755)

    srv = base / "srv"
    (srv / "links").mkdir(parents=True)
    os.symlink(final, srv / "links" / "bin")  # intermediate hop
    os.chmod(srv, 0o777)  # attacker can repoint srv/links/bin

    (base / "opt" / "tool").mkdir(parents=True)
    os.symlink(srv / "links" / "bin", base / "opt" / "tool" / "bin")
    absdir = str(base / "opt" / "tool" / "bin")

    senna = Senna(absdir, ["pos"])
    with pytest.raises(LookupError):
        senna.tag_sents([["hello"]])
    assert _senna_popen_spy == []


@POSIX_ONLY
def test_loader_environment_is_scrubbed_from_the_child(tmp_path, monkeypatch):
    """Real execution: LD_PRELOAD / DYLD_INSERT_LIBRARIES / PYTHONPATH set in the
    parent must NOT reach the senna child, since a trusted binary run with an
    untrusted loader environment is still attacker code execution."""
    from nltk.tag import SennaTagger

    absdir = os.path.join(_staging(), "trusted")
    os.makedirs(absdir)
    binpath = os.path.join(absdir, _this_platforms_binary())
    marker = tmp_path / "child_env.txt"
    script = (
        "#!/bin/sh\n"
        '{ echo "LD_PRELOAD=[$LD_PRELOAD]"; echo "DYLD=[$DYLD_INSERT_LIBRARIES]"; '
        'echo "PYTHONPATH=[$PYTHONPATH]"; } > MARKER\n'
        "while IFS= read -r l; do for w in $l; do printf 'x\\tNNP\\n'; done; echo; done\n"
    ).replace("MARKER", str(marker))
    with open(binpath, "w") as fh:
        fh.write(script)
    os.chmod(binpath, 0o755)

    monkeypatch.delenv("SENNA", raising=False)
    monkeypatch.setenv("LD_PRELOAD", "/evil.so")
    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/evil.dylib")
    monkeypatch.setenv("PYTHONPATH", "/evil")

    SennaTagger(absdir).tag(["hello"])
    reported = marker.read_text()
    assert "LD_PRELOAD=[]" in reported, reported
    assert "DYLD=[]" in reported, reported
    assert "PYTHONPATH=[]" in reported, reported

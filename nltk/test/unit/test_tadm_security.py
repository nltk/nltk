"""Trusted-exec routing for the TADM classifier wrapper (CWE-426/427/732).

``call_tadm`` spawned the tadm binary with a bare ``subprocess.Popen(cmd)``. It
now routes through ``pathsec.spawn_trusted`` (the standardized native-wrapper
chokepoint, strict trust policy like Senna): every directory from the root to the
tadm binary must be owned by us/root and not group/world-writable, no shell, and
the child gets a scrubbed environment with a locked PATH. A refusal is surfaced
as the wrapper's own OSError.
"""

import os
from types import SimpleNamespace

import pytest

import nltk.classify.tadm as tadm
import nltk.pathsec as ps

requires_posix_perms = pytest.mark.skipif(
    not hasattr(os, "getuid"), reason="POSIX ownership/permission model"
)


def _staging(prefix="tadm_test_"):
    import nltk.data as nltk_data

    try:
        return nltk_data.make_staging_dir(prefix=prefix, cleanup=True)
    except PermissionError as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"no writable in-sandbox NLTK data root: {exc}")


def _mkbin(dirpath, name="tadm", mode=0o755):
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, name)
    with open(path, "w") as handle:
        handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(path, mode)
    return path


@requires_posix_perms
def test_call_tadm_refuses_untrusted_binary(tmp_path, monkeypatch):
    """Strict trust: a tadm binary in a world-writable directory is refused before
    running, since another local user could swap it (CWE-426/732)."""
    install = tmp_path / "inst"
    binp = _mkbin(str(install))
    os.chmod(install, 0o777)  # world-writable: attacker can swap the binary
    monkeypatch.setattr(tadm, "_tadm_bin", binp)
    with pytest.raises(OSError):
        tadm.call_tadm(["-x", "/dev/null"])


def test_call_tadm_reaches_spawn_for_a_trusted_binary(monkeypatch):
    """Benign control: a tadm binary under a private staged root reaches the
    (trapped) spawn with an absolute, resolved argv[0] and no shell."""
    binp = _mkbin(os.path.join(_staging(), "inst"))
    monkeypatch.setattr(tadm, "_tadm_bin", binp)

    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        calls.append(SimpleNamespace(argv=list(cmd), shell=k.get("shell", False)))
        return _FakeProc()

    monkeypatch.setattr(ps.subprocess, "Popen", _fake_popen)
    tadm.call_tadm(["-monitor", "/dev/null"])
    assert len(calls) == 1
    assert calls[0].shell is False
    assert os.path.isabs(calls[0].argv[0])
    assert calls[0].argv[0] == os.path.realpath(binp)
    assert calls[0].argv[1:] == ["-monitor", "/dev/null"]

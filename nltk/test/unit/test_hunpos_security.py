"""Trusted-exec routing for the HunPos tagger wrapper (CWE-426/427/732).

``HunposTagger.__init__`` spawned ``hunpos-tag`` with a bare ``Popen``. It now
routes through ``pathsec.spawn_trusted`` (the standardized native-wrapper
chokepoint, strict trust policy like Senna): every directory from the root to the
binary must be owned by us/root and not group/world-writable, no shell, and the
child gets a scrubbed environment. The pre-existing ``validate_tool_path`` model
guard (bounding the model argument to the data roots) is unchanged; these tests
cover the added exec-trust and env-scrub layers.
"""

import os
from types import SimpleNamespace

import pytest

import nltk.data as nltk_data
import nltk.pathsec as ps
import nltk.tag.hunpos as hp

requires_posix_perms = pytest.mark.skipif(
    not hasattr(os, "getuid"), reason="POSIX ownership/permission model"
)


def _staging(prefix="hunpos_sec_"):
    try:
        return nltk_data.make_staging_dir(prefix=prefix, cleanup=True)
    except PermissionError as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"no writable in-sandbox NLTK data root: {exc}")


def _model_in_root(base, name="en_wsj.model"):
    """A real model file inside a data root, so validate_tool_path accepts it."""
    path = os.path.join(base, name)
    with open(path, "w") as handle:
        handle.write("stub-model\n")
    return path


@requires_posix_perms
def test_hunpos_refuses_untrusted_binary(tmp_path, monkeypatch):
    """Strict trust: a hunpos-tag binary in a world-writable directory is refused
    before running, even though the model argument is a valid in-root file."""
    model = _model_in_root(_staging())  # passes validate_tool_path
    install = tmp_path / "inst"
    install.mkdir()
    binp = install / "hunpos-tag"
    binp.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(binp, 0o755)
    os.chmod(install, 0o777)  # world-writable: another user could swap the binary

    monkeypatch.setattr(hp, "find_binary", lambda *a, **k: str(binp))
    monkeypatch.setattr(hp, "find_file", lambda p, **k: model)
    with pytest.raises(LookupError):
        hp.HunposTagger("en_wsj.model")


def test_hunpos_trusted_binary_reaches_spawn_with_scrubbed_env(monkeypatch):
    """Benign control: a hunpos-tag binary staged under a private data root reaches
    the (trapped) spawn with an absolute resolved argv, no shell, and an
    environment scrubbed of loader variables."""
    base = _staging()
    model = _model_in_root(base)
    binp = os.path.join(base, "hunpos-tag")
    with open(binp, "w") as handle:
        handle.write("#!/bin/sh\nexit 0\n")
    os.chmod(binp, 0o755)

    monkeypatch.setenv("LD_PRELOAD", "/evil.so")
    monkeypatch.setattr(hp, "find_binary", lambda *a, **k: binp)
    monkeypatch.setattr(hp, "find_file", lambda p, **k: model)

    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return b"", b""

    def _fake_popen(cmd, *a, **k):
        calls.append(
            SimpleNamespace(
                argv=list(cmd), shell=k.get("shell", False), env=k.get("env")
            )
        )
        return _FakeProc()

    monkeypatch.setattr(ps.subprocess, "Popen", _fake_popen)
    hp.HunposTagger("en_wsj.model")

    assert len(calls) == 1
    assert calls[0].shell is False
    assert calls[0].argv == [os.path.realpath(binp), model]
    assert "LD_PRELOAD" not in (calls[0].env or {})


# --- Layer-6 input guard: hunpos-tag reads one token per line (CWE-93) ---------


def _tagger_with_fake_pipe(encoding=hp._hunpos_charset):
    """A HunposTagger wired to a recording fake pipe, no real binary spawned."""
    writes = []

    class _Stdin:
        def write(self, chunk):
            writes.append(chunk)

        def flush(self):
            pass

    class _Stdout:
        def readline(self):
            return b"\n"

    tagger = object.__new__(hp.HunposTagger)
    tagger._closed = False
    tagger._encoding = encoding
    tagger._hunpos = SimpleNamespace(
        stdin=_Stdin(),
        stdout=_Stdout(),
        communicate=lambda *a, **k: (b"", b""),
    )
    return tagger, writes


def test_control_char_token_is_refused():
    """A newline/NUL/other control char in a token injects an extra line into
    hunpos-tag's line-oriented stdin (or truncates the token), desynchronising
    every following tag; the token is refused before it is written."""
    tagger, writes = _tagger_with_fake_pipe()
    for payload in ["good\nevil", "nul\x00here", "cr\rhere", "esc\x1bhere"]:
        with pytest.raises(ValueError, match="control characters"):
            tagger.tag([payload])
    assert writes == [], "a control-char token must not be written to hunpos stdin"


def test_tab_in_token_is_allowed():
    """hunpos uses tab as its own output column separator, but a tab inside an
    input token is harmless on the write side (one token per line); allow it."""
    tagger, writes = _tagger_with_fake_pipe()
    tagger.tag(["a\tb"])
    assert b"a\tb\n" in writes

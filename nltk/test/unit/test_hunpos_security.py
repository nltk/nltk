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


@pytest.mark.parametrize(
    "payload",
    [
        "good\nevil",  # LF: extra input line
        "nul\x00here",  # NUL: C-string truncation
        "cr\rhere",  # CR
        "esc\x1bhere",  # C0 control
        "vt\x0bhere",  # vertical tab
        "ff\x0chere",  # form feed
        "rs\x1ehere",  # record separator (splitlines break)
        "del\x7fhere",  # DEL (the reviewer's gap)
        "nel\x85here",  # NEL, a C1 control and a splitlines break
        "c1\x9fhere",  # C1 control
        "ls\u2028here",  # Unicode line separator
        "ps\u2029here",  # Unicode paragraph separator
        "sur\ud800here",  # lone surrogate (would crash .encode())
        "a\tb",  # TAB: splits hunpos's own tab-separated output column
    ],
)
def test_control_char_token_is_refused(payload):
    """A control character, line/paragraph separator or lone surrogate in a token
    injects/truncates a line on hunpos-tag's stdin, splits its tab-separated
    stdout, or fails to encode, desynchronising every following tag; the token is
    refused before it is written."""
    tagger, writes = _tagger_with_fake_pipe()
    with pytest.raises(ValueError, match="control characters"):
        tagger.tag([payload])
    assert writes == [], "an unsafe-char token must not be written to hunpos stdin"


def test_legitimate_multilingual_tokens_are_allowed():
    """The guard must not overblock real token content: non-ASCII letters, marks,
    symbols, non-breaking space and format characters (ZWJ/ZWNJ/bidi) all pass."""
    tagger, writes = _tagger_with_fake_pipe(encoding="utf-8")
    for token in ["café", "日本語", "नमस्ते", "العربية", "co op", "👨‍👩‍👧"]:
        tagger.tag([token])  # must not raise
        assert token.encode("utf-8") + b"\n" in writes

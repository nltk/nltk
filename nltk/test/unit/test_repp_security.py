"""Regression tests for the untrusted-search-path fix in ReppTokenizer (CWE-426).

``find_repptokenizer`` used ``os.path.exists(repp_dirname)`` to accept a directory
as-is. For a *relative* ``repp_dirname`` that resolves against the current working
directory and is checked *before* the ``REPP_TOKENIZER`` environment variable, so
an attacker who can write a ``./<name>/src/repp`` executable into the CWD could
have it run (the command path contains a separator, so ``subprocess`` executes it
directly) -- overriding a trusted ``REPP_TOKENIZER``.

Only an explicit *absolute* directory is now taken as-is; a relative name is
resolved through ``REPP_TOKENIZER``.
"""

import os
import pathlib

import pytest

from nltk.tokenize.repp import ReppTokenizer


def _make_repp_dir(path):
    (path / "src").mkdir(parents=True, exist_ok=True)
    (path / "erg").mkdir(parents=True, exist_ok=True)
    (path / "src" / "repp").write_bytes(b"")
    (path / "erg" / "repp.set").write_bytes(b"")
    return path


def test_relative_dirname_not_resolved_against_cwd(tmp_path, monkeypatch):
    """A relative repp_dirname matching a CWD directory must NOT be used."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_repp_dir(cwd / "reppdir")  # attacker-planted in the CWD
    monkeypatch.chdir(cwd)
    monkeypatch.delenv("REPP_TOKENIZER", raising=False)

    with pytest.raises(LookupError):
        ReppTokenizer("reppdir")


def test_cwd_does_not_override_configured_repp_tokenizer(tmp_path, monkeypatch):
    """A CWD directory must not shadow a configured REPP_TOKENIZER."""
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    _make_repp_dir(cwd / "reppdir")  # attacker-planted in the CWD
    trusted = _make_repp_dir(tmp_path / "trusted")  # the configured location
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("REPP_TOKENIZER", str(trusted))

    tok = ReppTokenizer("reppdir")
    assert os.path.realpath(tok.repp_dir) == os.path.realpath(
        str(trusted)
    ), "CWD directory overrode the trusted REPP_TOKENIZER"


def test_absolute_path_still_accepted(tmp_path, monkeypatch):
    """An explicit absolute directory is still used as-is, incl. as a Path."""
    abs_dir = _make_repp_dir(tmp_path / "absrepp")
    monkeypatch.delenv("REPP_TOKENIZER", raising=False)

    assert os.path.realpath(ReppTokenizer(str(abs_dir)).repp_dir) == os.path.realpath(
        str(abs_dir)
    )
    # a pathlib.Path is accepted too (normalised via os.fspath) and resolves to
    # the same directory.
    assert os.path.realpath(
        ReppTokenizer(pathlib.Path(abs_dir)).repp_dir
    ) == os.path.realpath(str(abs_dir))


def test_scratch_input_is_staged_in_a_data_root_and_cleaned_up(monkeypatch):
    """The temp input must land inside a pathsec data root, not shared /tmp
    (CWE-377, CWE-378), and be removed afterwards (CWE-459), mirroring the
    boxer/megam/tadm make_staging_dir migration."""
    import tempfile

    from nltk import pathsec

    assert not hasattr(ReppTokenizer, "working_dir")  # shared-temp attr is gone

    tok = object.__new__(ReppTokenizer)
    tok.repp_dir = "/x"
    tok.encoding = "utf8"

    captured = {}

    def fake_execute(cmd):
        path = cmd[-1]
        roots = [os.path.realpath(str(r)) for r in pathsec._get_allowed_roots()]
        captured["path"] = path
        captured["existed"] = os.path.exists(path)
        captured["in_root"] = any(os.path.realpath(path).startswith(r) for r in roots)
        captured["in_shared_tmp"] = path.startswith(tempfile.gettempdir() + os.sep)
        return b""  # empty output; we only assert on staging, not parsing

    monkeypatch.setattr(ReppTokenizer, "_execute", staticmethod(fake_execute))
    try:
        list(tok.tokenize_sents(["hello world"]))
    except ValueError:
        pass  # empty fake output yields no triples; irrelevant to staging

    assert captured["existed"] and captured["in_root"]
    assert not captured["in_shared_tmp"]
    assert not os.path.exists(captured["path"])  # cleaned up in the finally


# --- Trusted-exec routing: _execute now goes through pathsec.spawn_trusted -----
# (the standardized native-wrapper chokepoint; strict trust policy, like senna).

requires_posix_perms = pytest.mark.skipif(
    not hasattr(os, "getuid"), reason="POSIX ownership/permission model"
)


def _staging(prefix="repp_test_"):
    """A private, in-sandbox base dir (never world-writable /tmp)."""
    import nltk.data as nltk_data

    try:
        return nltk_data.make_staging_dir(prefix=prefix, cleanup=True)
    except PermissionError as exc:  # pragma: no cover - env-dependent
        pytest.skip(f"no writable in-sandbox NLTK data root: {exc}")


def _repp_cmd(reppdir):
    return [
        str(reppdir / "src" / "repp"),
        "-c",
        str(reppdir / "erg" / "repp.set"),
        "--format",
        "triple",
        "/dev/null",
    ]


@requires_posix_perms
def test_execute_refuses_untrusted_repp_binary(tmp_path):
    """Strict trust: a REPP binary whose holding directory is world-writable is
    refused before running, since another local user could swap it (CWE-426/732)."""
    reppdir = _make_repp_dir(tmp_path / "wwrepp")
    os.chmod(reppdir / "src" / "repp", 0o755)
    os.chmod(reppdir / "src", 0o777)  # world-writable: attacker can swap the binary
    with pytest.raises(LookupError):
        ReppTokenizer._execute(_repp_cmd(reppdir))


def test_execute_reaches_spawn_for_a_trusted_binary(monkeypatch):
    """Benign control: a REPP binary under a private staged root reaches the
    (trapped) spawn with an absolute, fully-resolved argv[0] and no shell."""
    from types import SimpleNamespace

    import nltk.pathsec as ps

    reppdir = _make_repp_dir(pathlib.Path(_staging()) / "repp")
    os.chmod(reppdir / "src" / "repp", 0o755)

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
                executable=k.get("executable"),
            )
        )
        return _FakeProc()

    monkeypatch.setattr(ps.subprocess, "Popen", _fake_popen)
    ReppTokenizer._execute(_repp_cmd(reppdir))
    assert len(calls) == 1
    assert calls[0].shell is False
    assert os.path.isabs(calls[0].argv[0])
    assert calls[0].argv[0] == os.path.realpath(str(reppdir / "src" / "repp"))


# --- Layer-6 input guard: REPP reads one sentence per line (CWE-93) ------------


def _detached_tokenizer():
    tok = object.__new__(ReppTokenizer)
    tok.repp_dir = "/x"
    tok.encoding = "utf8"
    return tok


def test_control_char_sentence_is_refused_before_spawn(monkeypatch):
    """A newline/NUL/other control char in a sentence would inject an extra REPP
    input line (or a NUL would truncate one), desynchronising the token stream
    from the sentence list; such input is refused before the binary is spawned."""
    tok = _detached_tokenizer()
    called = []
    monkeypatch.setattr(
        ReppTokenizer, "_execute", staticmethod(lambda cmd: called.append(cmd) or b"")
    )
    payloads = [
        "good\nevil",  # LF
        "nul\x00here",  # NUL
        "cr\rhere",  # CR
        "esc\x1bhere",  # C0 control
        "ff\x0chere",  # form feed
        "rs\x1ehere",  # record separator
        "del\x7fhere",  # DEL (the reviewer's gap)
        "nel\x85here",  # NEL / C1 control
        "c1\x9fhere",  # C1 control
        "ls\u2028here",  # Unicode line separator
        "ps\u2029here",  # Unicode paragraph separator
        "sur\ud800here",  # lone surrogate
    ]
    for payload in payloads:
        with pytest.raises(ValueError, match="control characters"):
            list(tok.tokenize_sents([payload]))
    assert not called, "REPP was spawned despite an unsafe-char sentence"


def test_legitimate_multilingual_sentence_reaches_execute(monkeypatch):
    """The guard must not overblock real text: non-ASCII letters and a literal TAB
    (REPP splits on newlines only) are ordinary sentence content and reach the
    (fake) binary rather than being refused."""
    tok = _detached_tokenizer()
    called = []
    monkeypatch.setattr(
        ReppTokenizer, "_execute", staticmethod(lambda cmd: called.append(1) or b"")
    )
    # Encodable on every platform: these must pass the guard AND reach _execute.
    # (_execute records the call before the empty fake output fails to parse, so
    # the post-spawn parse ValueError is tolerated.)
    for sent in ["hello world", "a\tb c"]:
        try:
            list(tok.tokenize_sents([sent]))
        except ValueError:
            pass
    assert len(called) == 2, "benign ASCII/tab sentences must reach _execute"
    # Multilingual / ZWJ content must not be refused by the control-char guard;
    # tolerate an unrelated platform encoding error at the tool's file write.
    for sent in ["café au lait", "日本語 の 文", "naïve\u200djoin"]:
        try:
            list(tok.tokenize_sents([sent]))
        except ValueError as exc:
            assert "control characters" not in str(exc), f"guard overblocked {sent!r}"


def test_tab_in_sentence_reaches_execute(monkeypatch):
    """A tab is legal inside a sentence (REPP splits on newlines only), so the
    guard must let it through to the (fake) binary."""
    tok = _detached_tokenizer()
    called = []
    monkeypatch.setattr(
        ReppTokenizer, "_execute", staticmethod(lambda cmd: called.append(1) or b"")
    )
    try:
        list(tok.tokenize_sents(["a\tb c"]))
    except ValueError:
        pass  # empty fake output yields no triples; irrelevant to the guard
    assert called, "a tab-containing sentence must pass the guard and reach _execute"

"""Expanded JAVA / BINARY / external-tool injection harness (GHSA-8mgp umbrella).

This file ADDS net-new external-tool attack vectors that the existing suite does
not already cover, and proves for each one that a hostile input is REFUSED and a
benign input is accepted. It deliberately avoids re-running vectors already owned
by:

* ``test_java_per_call_options_security.py`` (the ~90-vector option allowlist,
  the classpath sandbox matrix, and the child-env sanitisation, all at the
  ``internals.java()`` layer);
* ``test_java_injection_exploit.py`` (live-RCE-marker proofs, single-entry jar
  sandbox, MaltParser end-to-end);
* ``test_malt_stanford_pathsec.py`` / ``test_pathsec_sweep_wrappers.py`` (malt
  and stanford ``-model`` / ``corenlp_options`` coercion and traversal);
* ``test_pathsec_io_attack_matrix.py`` / ``test_pathsec_tool_resources.py`` (the
  guard-level path matrix and hostile PathLike / str-subclass objects);
* ``test_weka_security.py`` / ``test_malt_security.py`` (weka/malt tool-discovery
  hijacks; senna's guard and tests moved to #3858).

The genuinely-open surfaces this file targets are:

1. the generic ``internals.find_binary`` / ``find_file`` / ``find_dir``
   CWD-relative bare-name refusal, with a "teeth" proof that the raw iterator
   really does yield the untrusted CWD match the wrapper then drops (CWE-426/427);
2. the ``HunposTagger`` wrapper, which is not exercised by any file above and is
   a full binary-hijack + model-path + argv-coercion surface;
3. multi-entry classpath *shadowing* (an attacker jar prepended OR appended to a
   list of trusted jars) at the ``internals.java()`` layer;
4. tool program-flags (the Stanford ``-model`` / ``-loadClassifier`` arguments)
   fed into the JVM *option* channel, which the allowlist must reject because a
   value that IS an option is never a valid JVM flag;
5. a Stanford parser ``model_path`` that is itself an option token, refused at
   the single JVM hand-off before any process is spawned;
6. the child-env gate, asserted dynamically over the whole configured
   ``_JVM_INJECTING_ENV_VARS`` set so it self-updates.

Every hostile assertion either raises ``(PermissionError, ValueError,
UntrustedJarError, LookupError)`` OR proves the JVM/exec sentinel was never
invoked, i.e. the injected token never reached argv. No guard in ``nltk/*.py`` is
modified by this file.

Fixtures stage the trusted data root and the untrusted "outside" dir under the
real ``$HOME`` (never a shared temp dir), because a private per-user system temp
is itself a trusted pathsec root on macOS. POSIX-only vectors (symlink, mode) and
Windows-only vectors (reserved device names) are guarded with skip markers so the
file is green on Linux, macOS and Windows.
"""

import os
import pathlib
import shutil
import subprocess
import tempfile
import uuid
from types import SimpleNamespace

import pytest

import nltk.data
from nltk import internals, pathsec

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="symlink / mode / device-file vectors are POSIX-specific"
)
WINDOWS_ONLY = pytest.mark.skipif(
    os.name == "posix",
    reason="reserved device names are only special on Windows",
)


# =========================================================================== #
# Fixtures and helpers
# =========================================================================== #
@pytest.fixture
def atk_root(monkeypatch):
    """Pin ``nltk.data.path`` to ONE fresh trusted root and expose an untrusted
    ``outside`` dir, both under the real ``$HOME``.

    A private per-user system temp dir (``/var/folders/...`` on macOS) is itself
    an allowed pathsec root, so staging under ``$HOME`` (registering only
    ``root``) is the portable way to have a location that is genuinely OUTSIDE
    every trusted root on Linux/macOS/Windows alike.
    """
    home = str(pathlib.Path.home())
    root = os.path.realpath(tempfile.mkdtemp(prefix=".nltk_atk_root_", dir=home))
    outside = os.path.realpath(tempfile.mkdtemp(prefix=".nltk_atk_out_", dir=home))
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    # Invalidate the memoised allowed-roots so the new single root takes effect.
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield SimpleNamespace(root=root, outside=outside)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


@pytest.fixture
def java_spy(monkeypatch):
    """Replace ``subprocess.Popen`` with a spy that records every argv (and the
    child ``env``) and never launches a real process. A blocked exploit must
    leave the recorded call list empty, proving the injected token never reached
    the process layer."""
    calls = []

    class _FakeProc:
        returncode = 0

        def communicate(self, *a, **k):
            return "", ""

    def _fake_popen(cmd, *a, **k):
        calls.append(SimpleNamespace(argv=list(cmd), env=k.get("env")))
        return _FakeProc()

    monkeypatch.setattr(internals, "_java_bin", "java")
    monkeypatch.setattr(internals, "_java_options", [])
    monkeypatch.setattr(subprocess, "Popen", _fake_popen)
    monkeypatch.setattr(internals.subprocess, "Popen", _fake_popen)
    return calls


def _regular_file(dirpath, name, content="data"):
    """Create and return the path to a real regular file (what the tool guards
    require: not a symlink, FIFO, device, or directory)."""
    p = os.path.join(dirpath, name)
    with open(p, "w") as fh:
        fh.write(content)
    return p


class _LyingStr(str):
    """A ``str`` subclass whose inspection methods lie about the payload it holds.

    ``os.fspath`` hands a str subclass back unchanged, so a guard that reasoned
    over ``self`` would run the attacker's overridden ``startswith`` /
    ``__contains__`` / ``replace`` and be fooled. ``_as_path_text`` defeats this
    by re-extracting the real characters via ``str.__str__``."""

    def startswith(self, *a, **k):
        return False

    def __contains__(self, _item):
        return False

    def replace(self, *a, **k):
        return _LyingStr("")


class _MutatingFspath:
    """``__fspath__`` returns a benign in-root path the first time and a hostile
    one afterwards, modelling the TOCTOU where a guard validates one file and the
    tool opens another."""

    def __init__(self, first, rest):
        self._answers = [first, rest]
        self.calls = 0

    def __fspath__(self):
        answer = self._answers[min(self.calls, 1)]
        self.calls += 1
        return answer


# =========================================================================== #
# 1. Tool-discovery hijack: find_binary / find_file / find_dir (CWE-426/427)
#    Net-new: the generic discovery helpers are only reached indirectly by other
#    files (through malt/senna/repp). Here they are attacked directly, with a
#    "teeth" proof that the raw iterator really yields the CWD-relative match.
# =========================================================================== #
class TestToolDiscoveryHijack:
    def test_find_binary_bare_name_resolving_only_to_cwd_is_refused(
        self, monkeypatch, tmp_path
    ):
        """A bare tool name that exists ONLY as a CWD-relative file must not be
        run: a returned relative path is executed from the current directory, so
        an attacker who can write the CWD would choose the binary (CWE-426)."""
        monkeypatch.chdir(tmp_path)
        name = "tool_" + uuid.uuid4().hex  # guaranteed absent from PATH
        _regular_file(str(tmp_path), name)

        with pytest.raises(LookupError):
            internals.find_binary(name, env_vars=(), searchpath=())

        # Teeth: the raw iterator DOES surface the untrusted CWD-relative match,
        # so find_binary's wrapper, not a lucky miss, is what refuses it.
        raw = list(internals.find_file_iter(name, (), ()))
        assert any(not os.path.isabs(m) for m in raw), raw

    def test_find_binary_bare_path_to_bin_is_not_an_explicit_choice(
        self, monkeypatch, tmp_path
    ):
        """A bare ``path_to_bin`` (no directory component) is NOT an explicit path:
        a planted ``./<name>`` must still be refused, or ``bin='java'`` could be
        hijacked by a CWD ``./java``."""
        monkeypatch.chdir(tmp_path)
        name = "hunbin_" + uuid.uuid4().hex
        _regular_file(str(tmp_path), name)
        with pytest.raises(LookupError):
            internals.find_binary(name, path_to_bin=name, env_vars=(), searchpath=())

    def test_find_file_bare_name_resolving_only_to_cwd_is_refused(
        self, monkeypatch, tmp_path
    ):
        monkeypatch.chdir(tmp_path)
        name = "model_" + uuid.uuid4().hex
        _regular_file(str(tmp_path), name)

        with pytest.raises(LookupError):
            internals.find_file(name, env_vars=(), searchpath=())

        raw = list(internals.find_file_iter(name, (), ()))
        assert any(not os.path.isabs(m) for m in raw), raw

    def test_find_dir_bare_name_resolving_to_a_relative_env_dir_is_refused(
        self, monkeypatch, tmp_path
    ):
        """``find_dir`` yields the value of a configured env var; a relative value
        (``.``) is a CWD-relative directory and must be refused for a bare name."""
        monkeypatch.chdir(tmp_path)
        var = "NLTK_ATK_DIR_" + uuid.uuid4().hex
        monkeypatch.setenv(var, ".")  # a relative (CWD) directory
        name = "corpora_" + uuid.uuid4().hex

        with pytest.raises(LookupError):
            internals.find_dir(name, env_vars=(var,))

        raw = list(internals.find_file_iter(name, (var,), (), finding_dir=True))
        assert any(not os.path.isabs(m) for m in raw), raw

    def test_absolute_search_hit_shadows_a_planted_cwd_binary(
        self, monkeypatch, tmp_path
    ):
        """PATH-shadowing resilience: with BOTH a planted CWD-relative match and a
        trusted absolute searchpath hit, find_binary must return the absolute one,
        never the attacker's CWD copy."""
        cwd = tmp_path / "cwd"
        good = tmp_path / "trusted_bin"
        cwd.mkdir()
        good.mkdir()
        monkeypatch.chdir(cwd)
        name = "shadow_" + uuid.uuid4().hex
        planted = _regular_file(str(cwd), name)  # CWD-relative decoy
        trusted = _regular_file(str(good), name)  # absolute searchpath hit

        resolved = internals.find_binary(name, env_vars=(), searchpath=(str(good),))
        assert os.path.isabs(resolved)
        assert os.path.realpath(resolved) == os.path.realpath(trusted)
        assert os.path.realpath(resolved) != os.path.realpath(planted)

    def test_explicit_directory_component_is_honoured(self, monkeypatch, tmp_path):
        """A name WITH a directory component is the caller's explicit choice and is
        returned as given (benign control that the refusal is not over-broad)."""
        monkeypatch.chdir(tmp_path)
        sub = tmp_path / "tools"
        sub.mkdir()
        _regular_file(str(sub), "prover9")
        resolved = internals.find_file(
            os.path.join("tools", "prover9"), env_vars=(), searchpath=()
        )
        assert resolved == os.path.join("tools", "prover9")

    def test_absolute_path_to_bin_is_accepted(self, monkeypatch, tmp_path):
        """Benign control: an absolute binary is an explicit choice and honoured."""
        monkeypatch.chdir(tmp_path)
        target = _regular_file(str(tmp_path), "realbin")
        resolved = internals.find_binary(
            "realbin", path_to_bin=target, env_vars=(), searchpath=()
        )
        assert resolved == target


# =========================================================================== #
# 2. Multi-entry classpath shadowing (CWE-94). Net-new: the existing sandbox
#    matrix tests single entries; here an attacker jar is PREPENDED / APPENDED to
#    a list of otherwise-trusted jars and must poison the whole classpath.
# =========================================================================== #
class TestClasspathShadowing:
    def _jars(self, atk_root):
        a = _regular_file(atk_root.root, "trusted_a.jar")
        b = _regular_file(atk_root.root, "trusted_b.jar")
        evil = _regular_file(atk_root.outside, "evil.jar")
        return a, b, evil

    def test_attacker_jar_prepended_to_trusted_jars_is_refused(
        self, atk_root, java_spy
    ):
        a, b, evil = self._jars(atk_root)
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=[evil, a, b])
        assert java_spy == [], "untrusted jar reached the process layer"

    def test_attacker_jar_appended_to_trusted_jars_is_refused(self, atk_root, java_spy):
        a, b, evil = self._jars(atk_root)
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=[a, b, evil])
        assert java_spy == []

    def test_cwd_relative_entry_mixed_with_trusted_jars_is_refused(
        self, atk_root, java_spy
    ):
        a, _b, _evil = self._jars(atk_root)
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=[a, "." + os.sep + "evil.jar"])
        assert java_spy == []

    @POSIX_ONLY
    def test_in_root_symlink_to_outside_jar_is_refused(self, atk_root, java_spy):
        """An in-root classpath entry that is a symlink to an outside jar is
        refused: ``realpath`` sees the true (outside) inode (CWE-59)."""
        a, _b, evil = self._jars(atk_root)
        link = os.path.join(atk_root.root, "link.jar")
        os.symlink(evil, link)
        with pytest.raises(internals.UntrustedJarError):
            internals.java(["Main"], classpath=[a, link])
        assert java_spy == []

    def test_multi_entry_sandbox_is_load_bearing(self, atk_root, java_spy, monkeypatch):
        """Teeth (mentally revert the guard): with ``_verify_jar_sandbox`` neutered
        the SAME mixed list reaches the process layer with the outside jar on the
        classpath, proving it is the sandbox, not some later check, that refuses
        the shadowing list above."""
        a, _b, evil = self._jars(atk_root)
        monkeypatch.setattr(internals, "_verify_jar_sandbox", lambda entries: None)
        internals.java(["Main"], classpath=[a, evil])
        assert len(java_spy) == 1
        cp_value = java_spy[0].argv[java_spy[0].argv.index("-cp") + 1]
        assert evil in cp_value.split(os.pathsep)

    def test_trusted_multi_jar_classpath_reaches_popen_cleanly(
        self, atk_root, java_spy
    ):
        """Benign control: several in-root jars build a ``-cp`` joined with the
        platform separator, with NO empty (CWD) element, and reach the JVM."""
        a, b, _evil = self._jars(atk_root)
        internals.java(["Main"], classpath=[a, b])
        assert len(java_spy) == 1
        argv = java_spy[0].argv
        assert argv[0] == "java" and "-cp" in argv and "Main" in argv
        cp_value = argv[argv.index("-cp") + 1]
        assert cp_value == os.pathsep.join([a, b])
        assert "" not in cp_value.split(os.pathsep)


# =========================================================================== #
# 3. A value that IS an option in the JVM option channel. Net-new: the existing
#    allowlist tests feed real JVM-ish flags; here we feed the *tool's own*
#    program-flags, which must also be rejected (they are not JVM flags).
# =========================================================================== #
# Stanford/CoreNLP/malt PROGRAM arguments, never JVM launcher flags; if one
# reached the option channel it would sit before the main class.
_TOOL_FLAGS = [
    ["-model"],
    ["--outputFormat"],
    ["-loadClassifier"],
    ["-encoding"],
    ["-props"],
    ["-textFile"],
    ["-serDictionary"],
    ["-sentences", "newline"],
]


class TestToolFlagInOptionChannel:
    @pytest.mark.parametrize("opts", _TOOL_FLAGS)
    def test_tool_program_flag_is_rejected_by_the_option_allowlist(
        self, opts, java_spy
    ):
        with pytest.raises(ValueError):
            internals.java(["Main"], classpath=None, options=opts)
        assert java_spy == []

    def test_benign_allowlist_options_pass_and_reach_popen_in_order(self, java_spy):
        """Benign control: a spread of allowlisted flags validate AND reach the
        JVM in the order given, so the guard is not simply rejecting everything."""
        safe = ["-Xss8m", "-verbose:class", "--add-modules", "java.se", "-client"]
        internals._validate_java_options(safe)  # does not raise
        internals.java(["Main"], classpath=None, options=safe)
        assert len(java_spy) == 1
        argv = java_spy[0].argv
        for flag in ("-Xss8m", "-verbose:class", "--add-modules", "java.se", "-client"):
            assert flag in argv
        assert argv.index("-Xss8m") < argv.index("Main")


# =========================================================================== #
# 4. HunposTagger: an entirely uncovered external-tool wrapper.
#    hunpos uses a raw subprocess (NOT the JVM), so its defenses are the
#    find_binary CWD refusal on the executable and validate_tool_path on the
#    model; both are attacked here, with the process call trapped by a sentinel.
# =========================================================================== #
class _HunposSentinel(Exception):
    """Raised by the trapped Popen so a test can tell "argv was built and handed
    off" apart from "a guard refused first" without launching hunpos-tag."""


@pytest.fixture
def hunpos_env(monkeypatch, atk_root):
    """Wire HunposTagger so the executable resolves to a staged in-root binary and
    the real ``validate_tool_path`` model gate is the surface under test; the
    process spawn is trapped and its argv recorded."""
    from nltk.tag import hunpos as hp

    fake_bin = _regular_file(atk_root.root, "hunpos-tag")
    captured = {}

    def fake_find_binary(*a, **k):
        return fake_bin

    def fake_find_file(path_to_model, *a, **k):
        # Pass the caller's model through UNCHANGED so validate_tool_path (the
        # real guard, left un-patched) is what accepts or refuses it.
        return path_to_model

    def fake_popen(cmd, *a, **k):
        captured["argv"] = list(cmd)
        raise _HunposSentinel

    monkeypatch.setattr(hp, "find_binary", fake_find_binary)
    monkeypatch.setattr(hp, "find_file", fake_find_file)
    # HunposTagger spawns via pathsec.spawn_trusted; trap that shared sink (fake_bin
    # is a real file under the private atk_root, so the trust check accepts it).
    monkeypatch.setattr("nltk.pathsec.subprocess.Popen", fake_popen)
    return SimpleNamespace(root=atk_root, bin=fake_bin, captured=captured)


_HOSTILE_HUNPOS_MODELS = [
    "../../../etc/passwd",  # traversal out of the namespace
    "/etc/passwd",  # absolute, outside every root
    "http://evil.example/model",  # URL, not a local path
    "file:///etc/passwd",  # file URL
    "-loadClassifier",  # option-shaped (argument injection)
    "model\x00.bin",  # NUL truncates in the tool's native layer
]


class TestHunposToolInjection:
    def _make(self, model, **kw):
        from nltk.tag import HunposTagger

        return HunposTagger(model, **kw)

    @pytest.mark.parametrize("model", _HOSTILE_HUNPOS_MODELS)
    def test_hostile_model_is_refused_before_the_process_spawns(
        self, hunpos_env, model
    ):
        with pytest.raises((PermissionError, ValueError)):
            self._make(model)
        assert "argv" not in hunpos_env.captured, "process spawned with hostile model"

    def test_out_of_root_absolute_model_that_exists_is_still_refused(self, hunpos_env):
        """A model that is a REAL file but lives outside the roots is refused: the
        containment check, not mere existence, is what matters."""
        outside_model = _regular_file(hunpos_env.root.outside, "en_wsj.model")
        with pytest.raises((PermissionError, ValueError)):
            self._make(outside_model)
        assert "argv" not in hunpos_env.captured

    def test_lying_str_subclass_model_cannot_hide_its_payload(self, hunpos_env):
        payload = os.path.join(hunpos_env.root.outside, "en_wsj.model")
        _regular_file(hunpos_env.root.outside, "en_wsj.model")
        with pytest.raises((PermissionError, ValueError)):
            self._make(_LyingStr(payload))
        assert "argv" not in hunpos_env.captured

    @pytest.mark.parametrize("bogus", [None, ["/etc/passwd"], 3.14])
    def test_non_path_model_is_a_clean_security_rejection(self, hunpos_env, bogus):
        """A non-str/bytes model is a clean ``PermissionError``, not a TypeError
        that would escape a caller's ``except (PermissionError, ValueError)``."""
        with pytest.raises((PermissionError, ValueError)):
            self._make(bogus)
        assert "argv" not in hunpos_env.captured

    @WINDOWS_ONLY
    def test_reserved_windows_device_model_is_refused(self, hunpos_env):
        with pytest.raises((PermissionError, ValueError)):
            self._make("NUL")
        assert "argv" not in hunpos_env.captured

    def test_bare_cwd_relative_binary_is_refused(self, monkeypatch, tmp_path, atk_root):
        """The hunpos executable itself: a bare ``path_to_bin`` resolvable only in
        the CWD must be refused (CWE-426). find_binary is NOT stubbed here."""
        from nltk.tag import HunposTagger

        monkeypatch.chdir(tmp_path)
        bin_name = "hunbin_" + uuid.uuid4().hex  # absent from PATH
        _regular_file(str(tmp_path), bin_name)
        model = _regular_file(atk_root.root, "en_wsj.model")
        with pytest.raises(LookupError):
            HunposTagger(model, path_to_bin=bin_name)

    def test_model_guard_is_load_bearing(self, hunpos_env, monkeypatch):
        """Teeth (mentally revert the guard): with ``validate_tool_path`` neutered,
        an out-of-root model reaches the process spawn as argv[1], proving it is
        the model guard that refuses the hostile models above, not a later step."""
        from nltk.tag import hunpos as hp

        outside_model = _regular_file(hunpos_env.root.outside, "en_wsj.model")
        monkeypatch.setattr(hp, "validate_tool_path", lambda value, **k: value)
        with pytest.raises(_HunposSentinel):
            self._make(outside_model)
        assert hunpos_env.captured["argv"] == [hunpos_env.bin, outside_model]

    def test_benign_in_root_model_builds_the_expected_argv(self, hunpos_env):
        """Benign control: an in-root model and the staged binary build exactly the
        two-element ``[binary, model]`` argv and reach the (trapped) spawn."""
        model = _regular_file(hunpos_env.root.root, "en_wsj.model")
        with pytest.raises(_HunposSentinel):
            self._make(model)
        assert hunpos_env.captured["argv"] == [hunpos_env.bin, model]


# =========================================================================== #
# 4b. Argv coercion: a value-mutating ``__fspath__`` must be frozen to its first
#     answer, and callers must build argv from the RETURNED string. Net-new
#     angle: asserts the return-value contract directly and shows a re-read would
#     have opened a different (hostile) file.
# =========================================================================== #
class TestArgvCoercionFrozenFspath:
    def test_mutating_fspath_is_frozen_and_the_return_is_the_safe_value(self, atk_root):
        good = _regular_file(atk_root.root, "model.ser.gz")
        evil = os.path.join(atk_root.outside, "passwd")
        obj = _MutatingFspath(good, evil)

        returned = pathsec.validate_tool_path(obj, context="frozen-fspath")

        # The guard captured only the FIRST (safe, in-root) answer and returns it.
        assert returned == good
        # Teeth: the object now answers with the hostile path, so a caller that
        # re-read ``obj`` instead of using ``returned`` would hand the tool a file
        # the guard never saw. Building argv from ``returned`` is what stays safe.
        assert os.fspath(obj) == evil
        assert obj.calls >= 2

    def test_mutating_fspath_that_starts_hostile_is_refused(self, atk_root):
        evil_first = os.path.join(atk_root.outside, "passwd")
        good = _regular_file(atk_root.root, "model.ser.gz")
        obj = _MutatingFspath(evil_first, good)
        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_tool_path(obj, context="frozen-fspath")


# =========================================================================== #
# 5. Stanford parser: a model_path that is itself an option token is refused at
#    the single JVM hand-off, before any process is spawned. Net-new angle: the
#    existing files cover /etc/passwd + traversal for -model, not option-shaped.
# =========================================================================== #
class TestStanfordParserModelIsAnOption:
    def _stub_parser(self, monkeypatch, model_path, atk_root):
        from nltk.parse import stanford as st
        from nltk.parse.stanford import GenericStanfordParser

        p = GenericStanfordParser.__new__(GenericStanfordParser)
        p.model_path = model_path
        p._encoding = "utf8"
        p.corenlp_options = ""
        p.java_options = "-mx1g"
        p._classpath = (_regular_file(atk_root.root, "stanford.jar"),)

        reached = {}

        def fake_java(*a, **k):
            reached["hit"] = True
            return "", ""

        monkeypatch.setattr(st, "java", fake_java)
        return p, reached

    @pytest.mark.parametrize("model", ["-model", "-loadClassifier", "--outputFormat"])
    def test_option_shaped_model_path_is_refused_before_java(
        self, monkeypatch, atk_root, model
    ):
        p, reached = self._stub_parser(monkeypatch, model, atk_root)
        with pytest.raises((ValueError, PermissionError)):
            p._execute([p._MAIN_CLASS, "-model", model], "input")
        assert "hit" not in reached, "java() was reached with an option-shaped model"

    def test_out_of_root_absolute_model_path_is_refused_before_java(
        self, monkeypatch, atk_root
    ):
        outside = _regular_file(atk_root.outside, "englishPCFG.ser.gz")
        p, reached = self._stub_parser(monkeypatch, outside, atk_root)
        with pytest.raises((ValueError, PermissionError)):
            p._execute([p._MAIN_CLASS, "-model", outside], "input")
        assert "hit" not in reached

    def test_default_jar_internal_resource_still_validates(self):
        """Benign control: the documented jar-internal default resource is a bare
        resource name and is returned unchanged (not sandboxed as a path)."""
        resource = "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"
        assert pathsec.validate_model_resource(resource) == resource


# =========================================================================== #
# 6. Child-env gate: a poisoned parent env cannot inject into the child JVM.
#    Net-new angle: asserted dynamically over the WHOLE configured injecting-var
#    set so it self-updates, and proven end-to-end via the env handed to Popen.
# =========================================================================== #
class TestChildEnvGate:
    def test_every_configured_injecting_var_is_stripped_control_survives(
        self, monkeypatch
    ):
        payload = "-XX:OnOutOfMemoryError=touch /tmp/nltk_env_pwned"
        for var in internals._JVM_INJECTING_ENV_VARS:
            monkeypatch.setenv(var, payload)
        monkeypatch.setenv("NLTK_ATK_KEEP", "keepme")

        child = internals._java_child_env()

        for var in internals._JVM_INJECTING_ENV_VARS:
            assert var not in child, f"{var} leaked into the child JVM environment"
        assert payload not in child.values()
        assert child.get("NLTK_ATK_KEEP") == "keepme"
        assert "PATH" in child or os.name != "posix"

    def test_poisoned_parent_env_is_stripped_from_the_env_handed_to_popen(
        self, atk_root, java_spy, monkeypatch
    ):
        """End-to-end: with the parent env poisoned, the env dict java() hands to
        Popen carries none of the injecting vars, so the child JVM cannot read
        JAVA_TOOL_OPTIONS et al. (CWE-88)."""
        good = _regular_file(atk_root.root, "trusted.jar")
        for var in internals._JVM_INJECTING_ENV_VARS:
            monkeypatch.setenv(var, "-XX:OnError=touch /tmp/pwned")
        internals.java(["Main"], classpath=good)
        assert len(java_spy) == 1
        child_env = java_spy[0].env
        assert child_env is not None, "java() must hand Popen an explicit env"
        for var in internals._JVM_INJECTING_ENV_VARS:
            assert var not in child_env


# =========================================================================== #
# 7. Senna: a relative senna_path (incl. PathLike form) must not be resolved
#    against the CWD. Net-new form: the PathLike spelling of the CWE-426 vector.
# =========================================================================== #
class TestSennaRelativePath:
    def test_relative_pathlike_senna_dir_is_rejected(self, monkeypatch, tmp_path):
        """A relative ``Path('.')`` must fall through to the (absolute-only) SENNA
        env var rather than run a ``./senna-<platform>`` from the CWD (CWE-426)."""
        from nltk.classify import Senna

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("SENNA", raising=False)
        # Plant a decoy for every platform's expected binary name in the CWD.
        for name in (
            "senna-linux64",
            "senna-linux32",
            "senna-win32.exe",
            "senna-osx",
            "senna",
        ):
            _regular_file(str(tmp_path), name)
        with pytest.raises(LookupError):
            Senna(pathlib.Path("."), ["pos"])

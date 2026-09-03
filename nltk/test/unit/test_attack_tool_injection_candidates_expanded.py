"""Expanded external-tool / JVM invocation candidate matrix (GHSA-8mgp umbrella).

This file ADDS coverage for the external-tool wrappers that are *not* already
exercised by an existing security suite, driving each candidate through the REAL
guard and proving that a hostile input is refused BEFORE any process is spawned,
while a benign in-root input is accepted. The external binaries need not be
installed: every guard must refuse (or, for the escape-hatch APIs, keep argv
literal) before ``subprocess.Popen`` runs, so a recording spy stands in for the
process layer and a blocked exploit leaves it empty.

The surfaces targeted here, none owned by a file already in the suite, back the
ledger rows "find_binary (CWD-relative refused) + validate_tool_path", "argv lists
(never shell=True)" and the wrapper model/config-path rows:

* ``nltk.classify.megam``: ``config_megam`` binary discovery (find_binary
  CWD-relative refusal) and ``call_megam`` argv-list integrity (never shell=True;
  a metacharacter argument stays a single literal argv element, never a shell
  token). megam takes its training input as an in-root staged file and writes the
  model to stdout, so it has no NLTK-controlled model-path sink; its whole
  attack surface is the binary lookup plus the argv list.
* ``nltk.inference.prover9`` / ``nltk.inference.mace``: ``_find_binary``
  CWD-relative refusal for ``prover9`` / ``prooftrans`` / ``mace4`` /
  ``interpformat`` and ``_call`` argv-list integrity. These provers take their
  input on stdin (no file-path argument), so the binary lookup and the argv list
  are the surface.
* the ``internals.java()`` chokepoint as reached by the CoreNLP server wrapper:
  an out-of-root ``path_to_jar`` classpath entry, an ``@argfile`` smuggled through
  the free-form ``corenlp_options`` program-argument channel, and a disallowed
  ``java_options`` JVM flag.
* the generic ``internals.find_binary`` for a jar-shaped bare name and a
  ``$PATH``-injection decoy, plus the MaltParser end-to-end path where an
  out-of-root ``MALT_PARSER`` env var reaches the classpath sandbox.
* a source-level assertion that NONE of the owned wrappers ever pass
  ``shell=True``.

Trusted / untrusted dirs are
staged under the real ``$HOME`` (a private per-user system temp dir is itself a
trusted pathsec root on macOS), registering only ``root`` so ``outside`` is
genuinely outside every trusted root on Linux/macOS/Windows.
"""

import inspect
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


# =========================================================================== #
# Fixtures and helpers
# =========================================================================== #
@pytest.fixture
def atk_root(monkeypatch):
    """Pin ``nltk.data.path`` to ONE fresh trusted root and expose an untrusted
    ``outside`` dir, both under the real ``$HOME`` (see module docstring)."""
    home = str(pathlib.Path.home())
    root = os.path.realpath(tempfile.mkdtemp(prefix=".nltk_tic_root_", dir=home))
    outside = os.path.realpath(tempfile.mkdtemp(prefix=".nltk_tic_out_", dir=home))
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield SimpleNamespace(root=root, outside=outside)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


class _FakeProc:
    returncode = 0

    def communicate(self, *a, **k):
        # bytes so the wrappers' ``.decode(...)`` paths (prover9/senna) do not blow
        # up; str-returning callers accept bytes here too.
        return b"", b""

    def poll(self):
        return None


@pytest.fixture
def spy(monkeypatch):
    """Record every ``subprocess.Popen`` argv without launching a process. A
    refused exploit leaves the list empty; an escape-hatch API leaves the injected
    token as a single literal argv element (no shell splitting)."""
    calls = []

    def _fake_popen(cmd, *a, **k):
        calls.append(SimpleNamespace(argv=list(cmd), shell=k.get("shell", False)))
        return _FakeProc()

    # Every owned wrapper reaches Popen through the ``subprocess`` module object,
    # except senna which does ``from subprocess import Popen``; patch both spellings.
    monkeypatch.setattr(subprocess, "Popen", _fake_popen)
    from nltk.classify import senna as _senna

    monkeypatch.setattr(_senna, "Popen", _fake_popen)
    monkeypatch.setattr(internals, "_java_bin", "java")
    monkeypatch.setattr(internals, "_java_options", [])
    return calls


def _regular_file(dirpath, name, content=b""):
    p = os.path.join(dirpath, name)
    with open(p, "wb") as fh:
        fh.write(content)
    return p


def _exec_file(dirpath, name):
    p = _regular_file(dirpath, name)
    os.chmod(p, 0o755)
    return p


# =========================================================================== #
# 1. megam: config_megam binary discovery + call_megam argv integrity.
# =========================================================================== #
class TestMegamToolInjection:
    _BIN_NAMES = ("megam", "megam.opt", "megam_686", "megam_i686.opt")

    def test_cwd_relative_megam_binary_is_refused(self, monkeypatch, tmp_path):
        """A bare ``megam`` resolvable ONLY in the CWD must not be run: a returned
        relative path is executed from the current directory (CWE-426/427)."""
        from nltk.classify import megam

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MEGAM", raising=False)
        for n in self._BIN_NAMES:
            _exec_file(str(tmp_path), n)
        monkeypatch.setattr(megam, "_megam_bin", None)
        with pytest.raises(LookupError):
            megam.config_megam()

    def test_cwd_megam_does_not_shadow_absolute_env(self, monkeypatch, tmp_path):
        """A planted CWD megam must not shadow an absolute ``MEGAM`` env var."""
        from nltk.classify import megam

        cwd = tmp_path / "cwd"
        trusted = tmp_path / "trusted"
        cwd.mkdir()
        trusted.mkdir()
        monkeypatch.chdir(cwd)
        for n in self._BIN_NAMES:
            _exec_file(str(cwd), n)
        good = _exec_file(str(trusted), "megam")
        monkeypatch.setenv("MEGAM", str(trusted))
        monkeypatch.setattr(megam, "_megam_bin", None)
        megam.config_megam()
        assert os.path.isabs(megam._megam_bin)
        assert os.path.realpath(megam._megam_bin) == os.path.realpath(good)

    _HOSTILE_MEGAM_ARGS = [
        ["-writeModel", "/etc/cron.d/evil"],  # option-shaped file write
        ["; touch /tmp/pwned"],  # shell metacharacters
        ["$(id)"],  # command substitution
        ["multiclass", "/etc/passwd"],  # absolute read path
        ["train\n-writeModel /etc/x"],  # embedded newline
    ]

    @pytest.mark.parametrize("args", _HOSTILE_MEGAM_ARGS)
    def test_call_megam_keeps_hostile_args_literal_no_shell(
        self, monkeypatch, spy, atk_root, args
    ):
        """``call_megam`` forwards its args verbatim (it is a low-level escape
        hatch), so the security property is that they reach the process as
        LITERAL argv elements via an argv list, never interpreted by a shell:
        every hostile token appears unchanged in argv and ``shell`` is False."""
        from nltk.classify import megam

        monkeypatch.setattr(megam, "_megam_bin", _exec_file(atk_root.root, "megam"))
        megam.call_megam(list(args))
        assert len(spy) == 1
        assert spy[0].shell is False
        for tok in args:
            assert tok in spy[0].argv  # literal, not shell-split
        assert spy[0].argv[0] == megam._megam_bin

    def test_call_megam_rejects_str_args(self, monkeypatch, spy, atk_root):
        """A str (not list) is refused before any spawn: a shell would otherwise
        be the only way to interpret it, and megam never uses one."""
        from nltk.classify import megam

        monkeypatch.setattr(megam, "_megam_bin", _exec_file(atk_root.root, "megam"))
        with pytest.raises(TypeError):
            megam.call_megam("multiclass /etc/passwd")
        assert spy == []

    def test_benign_megam_call_reaches_popen(self, monkeypatch, spy, atk_root):
        """Benign control: a legit options list reaches the argv-list spawn."""
        from nltk.classify import megam

        bin_ = _exec_file(atk_root.root, "megam")
        trainfile = _regular_file(atk_root.root, "train.megam")
        monkeypatch.setattr(megam, "_megam_bin", bin_)
        megam.call_megam(["-nobias", "-explicit", "multiclass", trainfile])
        assert len(spy) == 1 and spy[0].shell is False
        assert spy[0].argv == [bin_, "-nobias", "-explicit", "multiclass", trainfile]


# =========================================================================== #
# 2. prover9 / mace: _find_binary CWD refusal + _call argv integrity.
# =========================================================================== #
class TestProver9MaceToolInjection:
    @pytest.mark.parametrize(
        "factory,binname",
        [
            ("nltk.inference.prover9:Prover9", "prover9"),
            ("nltk.inference.prover9:Prover9", "prooftrans"),
            ("nltk.inference.mace:Mace", "mace4"),
            ("nltk.inference.mace:Mace", "interpformat"),
        ],
    )
    def test_cwd_relative_binary_is_refused(
        self, monkeypatch, tmp_path, factory, binname
    ):
        """Each prover binary resolvable ONLY in the CWD must be refused
        (CWE-426/427); the search path is a list of absolute dirs, so a bare name
        never legitimately resolves relative to the CWD."""
        import importlib

        mod_name, cls_name = factory.split(":")
        cls = getattr(importlib.import_module(mod_name), cls_name)
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("PROVER9", raising=False)
        _exec_file(str(tmp_path), binname)
        obj = cls()
        obj._binary_location = None
        with pytest.raises(LookupError):
            obj._find_binary(binname)

    def test_cwd_does_not_shadow_absolute_prover9_env(self, monkeypatch, tmp_path):
        from nltk.inference.prover9 import Prover9

        cwd = tmp_path / "cwd"
        trusted = tmp_path / "trusted"
        cwd.mkdir()
        trusted.mkdir()
        monkeypatch.chdir(cwd)
        _exec_file(str(cwd), "prover9")
        good = _exec_file(str(trusted), "prover9")
        monkeypatch.setenv("PROVER9", str(trusted))
        p = Prover9()
        p._binary_location = None
        resolved = p._find_binary("prover9")
        assert os.path.isabs(resolved)
        assert os.path.realpath(resolved) == os.path.realpath(good)

    _HOSTILE_CALL_ARGS = [
        ["-f", "/etc/passwd"],
        ["; rm -rf /"],
        ["$(reboot)"],
        ["striplabels\n-load /etc/x"],
    ]

    @pytest.mark.parametrize("args", _HOSTILE_CALL_ARGS)
    def test_prover9_call_keeps_args_literal_no_shell(
        self, monkeypatch, spy, atk_root, args
    ):
        """``_call`` builds ``[binary] + args`` and never uses a shell, so a
        metacharacter/option/newline argument reaches the process as a single
        literal argv element."""
        from nltk.inference.prover9 import Prover9

        binary = _exec_file(atk_root.root, "prover9")
        Prover9()._call("clause.\n", binary, args=list(args))
        assert len(spy) == 1 and spy[0].shell is False
        assert spy[0].argv[0] == binary
        for tok in args:
            assert tok in spy[0].argv

    def test_benign_prover9_call_reaches_popen(self, monkeypatch, spy, atk_root):
        """Benign control: prover9's own fixed program args reach the spawn."""
        from nltk.inference.prover9 import Prover9

        binary = _exec_file(atk_root.root, "prooftrans")
        Prover9()._call("proof.\n", binary, args=["striplabels"])
        assert len(spy) == 1 and spy[0].shell is False
        assert spy[0].argv == [binary, "striplabels"]

    def test_mace_call_reaches_popen_via_shared_call(self, monkeypatch, spy, atk_root):
        """Mace reuses prover9's ``_call``; a benign interpformat arg reaches the
        argv-list spawn."""
        from nltk.inference.mace import Mace

        binary = _exec_file(atk_root.root, "interpformat")
        Mace()._call("model.\n", binary, args=["standard"])
        assert len(spy) == 1 and spy[0].shell is False
        assert spy[0].argv == [binary, "standard"]


# =========================================================================== #
# 3. CoreNLP server flags routed through the internals.java() chokepoint.
#    The wrapper hands corenlp_options (program args), java_options (JVM flags)
#    and the discovered jars (classpath) to java(); that single hardened entry
#    point is the guard, so it is driven directly with CoreNLP-shaped inputs.
# =========================================================================== #
_CORENLP_MAIN = "edu.stanford.nlp.pipeline.StanfordCoreNLPServer"


class TestCoreNLPChokepoint:
    def test_out_of_root_jar_is_refused_before_spawn(self, spy, atk_root):
        """An out-of-root ``path_to_jar`` reaching the classpath is refused by the
        jar sandbox before Popen (CWE-94)."""
        evil = _regular_file(atk_root.outside, "stanford-corenlp.jar")
        with pytest.raises(internals.UntrustedJarError):
            internals.java([_CORENLP_MAIN], classpath=(evil,))
        assert spy == []

    @pytest.mark.parametrize(
        "corenlp_options",
        [
            ["-preload", "tokenize", "@/tmp/argfile"],  # @argfile anywhere
            ["@/tmp/props"],
            ["-serverProperties", "x", "@/tmp/more"],
        ],
    )
    def test_argfile_in_corenlp_options_is_refused(
        self, spy, atk_root, corenlp_options
    ):
        """An ``@argfile`` smuggled through the free-form ``corenlp_options``
        program-argument channel is refused in any position: the Java launcher
        would expand it and inject arguments (CWE-88)."""
        good = _regular_file(atk_root.root, "stanford-corenlp.jar")
        with pytest.raises(ValueError):
            internals.java([_CORENLP_MAIN, *corenlp_options], classpath=(good,))
        assert spy == []

    @pytest.mark.parametrize(
        "java_options",
        [
            ["-XX:OnOutOfMemoryError=touch /tmp/pwned"],
            ["-Djava.ext.dirs=/tmp/evil"],
            ["-javaagent:/tmp/evil.jar"],
            ["-jar", "/tmp/evil.jar"],
        ],
    )
    def test_disallowed_java_option_is_refused(self, spy, atk_root, java_options):
        good = _regular_file(atk_root.root, "stanford-corenlp.jar")
        with pytest.raises(ValueError):
            internals.java([_CORENLP_MAIN], classpath=(good,), options=java_options)
        assert spy == []

    def test_in_root_symlink_jar_pointing_outside_is_refused(self, spy, atk_root):
        """POSIX symlink escape: an in-root classpath entry that is a symlink to an
        outside jar is refused, because the sandbox resolves it with realpath and
        sees the true (outside) inode before any spawn (CWE-59)."""
        real = _regular_file(atk_root.root, "code.jar")  # a genuine in-root jar
        outside_jar = _regular_file(atk_root.outside, "evil.jar")
        link = os.path.join(atk_root.root, "linked.jar")
        try:
            os.symlink(outside_jar, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this platform")
        with pytest.raises(internals.UntrustedJarError):
            internals.java([_CORENLP_MAIN], classpath=(real, link))
        assert spy == []

    def test_in_root_symlink_jar_pointing_in_root_is_accepted(self, spy, atk_root):
        """POSIX benign control: an in-root symlink whose target is ALSO in-root
        resolves inside the sandbox, so it is accepted and reaches the spawn; the
        symlink refusal above is escape-specific, not a blanket ban on symlinks."""
        real = _regular_file(atk_root.root, "code.jar")
        link = os.path.join(atk_root.root, "alias.jar")
        try:
            os.symlink(real, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable on this platform")
        internals.java([_CORENLP_MAIN], classpath=(link,))
        assert len(spy) == 1 and spy[0].shell is False
        assert _CORENLP_MAIN in spy[0].argv

    def test_benign_corenlp_launch_reaches_popen(self, spy, atk_root):
        """Benign control: in-root jars, an allowlisted ``-mx2g`` java option and a
        legitimate program-flag list build the launcher argv and reach the
        (trapped) spawn, with the program flags kept literal and NO shell."""
        code = _regular_file(atk_root.root, "stanford-corenlp.jar")
        models = _regular_file(atk_root.root, "stanford-corenlp-models.jar")
        internals.java(
            [_CORENLP_MAIN, "-preload", "tokenize,ssplit", "-port", "9000"],
            classpath=(code, models),
            options=["-mx2g"],
        )
        assert len(spy) == 1 and spy[0].shell is False
        argv = spy[0].argv
        assert argv[0] == "java" and "-cp" in argv and _CORENLP_MAIN in argv
        assert "-mx2g" in argv and argv.index("-mx2g") < argv.index(_CORENLP_MAIN)
        cp = argv[argv.index("-cp") + 1]
        assert cp == os.pathsep.join([code, models])
        assert "" not in cp.split(os.pathsep)  # no CWD element


# =========================================================================== #
# 4. Generic find_binary: jar-shaped bare name + PATH-injection + MaltParser
#    env-var-outside-root reaching the classpath sandbox end-to-end.
# =========================================================================== #
class TestBinaryResolutionCandidates:
    def test_bare_jar_name_resolvable_only_in_cwd_is_refused(
        self, monkeypatch, tmp_path
    ):
        """A bare ``<name>.jar`` (no directory component) resolvable only in the
        CWD is refused: a returned relative path would be loaded/run from the CWD
        (CWE-426/427)."""
        monkeypatch.chdir(tmp_path)
        name = "malt_" + uuid.uuid4().hex + ".jar"
        _regular_file(str(tmp_path), name)
        with pytest.raises(LookupError):
            internals.find_binary(name, env_vars=(), searchpath=())
        # Teeth: the raw iterator really surfaces the untrusted CWD-relative hit.
        raw = list(internals.find_file_iter(name, (), ()))
        assert any(not os.path.isabs(m) for m in raw), raw

    def test_absolute_searchpath_hit_wins_over_path_injection_decoy(
        self, monkeypatch, tmp_path
    ):
        """PATH-injection resilience: a planted CWD decoy plus a trusted absolute
        searchpath hit must resolve to the absolute one, never the decoy."""
        cwd = tmp_path / "cwd"
        good = tmp_path / "good"
        cwd.mkdir()
        good.mkdir()
        monkeypatch.chdir(cwd)
        name = "tool_" + uuid.uuid4().hex
        decoy = _exec_file(str(cwd), name)
        trusted = _exec_file(str(good), name)
        resolved = internals.find_binary(name, env_vars=(), searchpath=(str(good),))
        assert os.path.isabs(resolved)
        assert os.path.realpath(resolved) == os.path.realpath(trusted)
        assert os.path.realpath(resolved) != os.path.realpath(decoy)

    def test_absolute_path_to_bin_outside_root_is_the_callers_choice(
        self, monkeypatch, tmp_path
    ):
        """Benign control / by-design: an ABSOLUTE explicit ``path_to_bin`` is the
        caller's own choice and is honoured even outside any data root (find_binary
        does not sandbox an explicit executable; the jar/model sinks are what
        pathsec bounds)."""
        target = _exec_file(str(tmp_path), "realbin")
        resolved = internals.find_binary(
            "realbin", path_to_bin=target, env_vars=(), searchpath=()
        )
        assert resolved == target

    def test_malt_env_var_outside_root_jars_refused_at_classpath_sandbox(
        self, spy, atk_root, monkeypatch
    ):
        """End-to-end: a ``MALT_PARSER`` pointing at an out-of-root install is
        honoured by find_dir (an absolute env value), but the jars it yields are
        refused by java()'s classpath sandbox before any spawn (CWE-94)."""
        from nltk.parse.malt import MaltParser

        # A stub MaltParser whose jars live OUTSIDE the trusted root, with an
        # in-root working dir and in-root CoNLL input so only the jar containment
        # is what fails.
        evildir = os.path.join(atk_root.outside, "maltparser-1.9.2")
        os.makedirs(evildir)
        evil_jar = _regular_file(evildir, "maltparser-1.9.2.jar")
        conll = _regular_file(
            atk_root.root, "in.conll", b"1\tHi\t_\t_\t_\t_\t0\t_\t_\t_\n"
        )

        m = MaltParser.__new__(MaltParser)
        m.malt_jars = [evil_jar]
        m.additional_java_args = []
        m.model = "malt_temp.mco"
        m._working_dir = atk_root.root
        cmd = m.generate_malt_command(
            conll, os.path.join(atk_root.root, "o.conll"), mode="parse"
        )
        # _execute swallows OSError into a return code, but UntrustedJarError is a
        # different type and propagates, proving the sandbox refused the jar.
        with pytest.raises(internals.UntrustedJarError):
            m._execute(cmd)
        assert spy == []


# =========================================================================== #
# 5. Structural: none of the owned wrappers ever spawn with shell=True.
# =========================================================================== #
class TestNoShellTrueAnywhere:
    _OWNED_MODULES = [
        "nltk.internals",
        "nltk.classify.weka",
        "nltk.classify.megam",
        "nltk.classify.senna",
        "nltk.parse.malt",
        "nltk.parse.corenlp",
        "nltk.tag.senna",
        "nltk.inference.prover9",
        "nltk.inference.mace",
        "nltk.sem.boxer",
    ]

    @pytest.mark.parametrize("mod_name", _OWNED_MODULES)
    def test_module_source_never_sets_shell_true(self, mod_name):
        import importlib

        src = inspect.getsource(importlib.import_module(mod_name))
        normalised = src.replace(" ", "").replace("\t", "")
        assert "shell=True" not in normalised, f"{mod_name} passes shell=True"

# Natural Language Toolkit: MaltParser / StanfordParser pathsec regressions
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Path and argv hardening for the two JVM parser wrappers.

``nltk.parse.malt`` and ``nltk.parse.stanford`` take caller-supplied model,
corpus and IO paths and pass them straight into a child JVM's argv. Those are
*data* paths, so they must stay inside the NLTK data roots; a value outside the
sandbox lets the tool read (and, for MaltParser's ``-w`` in learn mode, WRITE)
anywhere on disk.

Vulnerability classes covered here:

* MaltParser ``-i`` arbitrary read / ``-o`` arbitrary write, ``-c`` model
  traversal, and the ``-w`` working directory, which used to default to the
  shared world-writable ``tempfile.gettempdir()`` and now stages a private dir
  inside a data root.
* StanfordParser ``-model`` traversal and the ``corenlp_options`` string, which
  is split into argv and could append a second ``-model`` (the JVM honours the
  last one, verified against a real ``LexicalizedParser``).
* A ``__fspath__`` time-of-check/time-of-use gap and a lying ``str`` subclass,
  both closed by the guards returning the resolved plain string the callers use.

Every guard test drives the real wrapper with only the ``java`` hand-off
replaced, so a probe cannot pass merely because the argv was assembled by the
test itself. The teeth tests neuter a guard and assert the attack reappears, so
each refusal is known to fail against the un-hardened code.
"""

import os

import pytest

from nltk import pathsec
from nltk.data import make_staging_dir
from nltk.pathsec import validate_model_resource, validate_tool_path

_DEFAULT_RESOURCE = "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"


class _ReachedJVM(Exception):
    """Raised by the trapped ``java`` so a test can tell "the argv was built and
    handed off" apart from "a guard refused first"."""


def _passthrough(value, *args, **kwargs):
    """A neutered guard: performs no checks but still returns the path, since the
    callers now use the value the guard hands back."""
    return os.fspath(value)


def _trap_java(monkeypatch, module, sink):
    """Replace ``module.java`` with a trap that records argv and stops before
    launching a JVM."""

    def fake_java(cmd, *args, **kwargs):
        sink["cmd"] = list(cmd)
        raise _ReachedJVM

    monkeypatch.setattr(module, "java", fake_java)
    return sink


class _MutatingPath:
    """A legal os.PathLike whose __fspath__ answers differently each call."""

    def __init__(self, first, rest):
        self._calls = 0
        self._first = first
        self._rest = rest

    def __fspath__(self):
        self._calls += 1
        return self._first if self._calls == 1 else self._rest

    def __str__(self):
        return self._first


def _resolve(value):
    return os.fspath(value) if hasattr(value, "__fspath__") else value


class _LyingStr(str):
    """A str subclass whose inspection methods lie.

    os.fspath() returns a str subclass unchanged, so every syntactic check would
    otherwise run on attacker-controlled methods while the value handed to the
    tool still carries the real, hostile characters.
    """

    def __str__(self):
        return "safe"

    def startswith(self, *args, **kwargs):
        return False

    def strip(self, *args, **kwargs):
        return "safe"

    def rstrip(self, *args, **kwargs):
        return self

    def replace(self, *args, **kwargs):
        return "safe/name.mco"

    def split(self, *args, **kwargs):
        return ["safe", "name.mco"]

    def lower(self):
        return "safe"

    def __contains__(self, item):
        return False


# MaltParser: the -c model and the -w working directory (WRITTEN in learn mode).


def _malt(model, trained=True):
    import nltk.parse.malt as malt

    parser = object.__new__(malt.MaltParser)
    parser.model = model
    parser._trained = trained
    parser._working_dir = None
    parser.additional_java_args = []
    return parser


def _sandbox_io(parser):
    """Valid in-sandbox -i/-o paths for a test that targets some *other* guard.
    Without these the input-file guard fires first and the test would pass for
    the wrong reason."""
    infile = os.path.join(parser.working_dir, "in.conll")
    with pathsec.open(infile, "w", encoding="utf-8") as handle:
        handle.write("")
    return infile, os.path.join(parser.working_dir, "out.conll")


def test_malt_trained_model_refuses_escape(pathsec_sandbox):
    """A .mco outside the roots would make ``-w`` an arbitrary write target."""
    root, outside = pathsec_sandbox
    evil = outside / "evil.mco"
    evil.write_text("model", encoding="utf-8")
    parser = _malt(str(evil))
    infile, _outfile = _sandbox_io(parser)
    with pytest.raises((PermissionError, ValueError)):
        parser.generate_malt_command(infile, None, mode="learn")


def test_malt_trained_model_in_sandbox_is_allowed(pathsec_sandbox):
    """Over-block control for the trained path."""
    root, _outside = pathsec_sandbox
    model = root / "engmalt.mco"
    model.write_text("model", encoding="utf-8")
    parser = _malt(str(model))
    infile, outfile = _sandbox_io(parser)
    cmd = parser.generate_malt_command(infile, outfile, mode="parse")
    assert cmd[cmd.index("-w") + 1] == str(root)
    assert cmd[cmd.index("-c") + 1] == "engmalt.mco"


def test_malt_untrained_working_dir_is_staged_inside_root(pathsec_sandbox):
    """An untrained parser used to write malt_temp.mco into the CWD; it must now
    land in a private staging dir inside a data root."""
    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    infile, _outfile = _sandbox_io(parser)
    cmd = parser.generate_malt_command(infile, None, mode="learn")
    workingdir = cmd[cmd.index("-w") + 1]
    assert os.path.realpath(workingdir).startswith(os.path.realpath(str(root)))
    assert os.path.realpath(workingdir) != os.path.realpath(os.getcwd())
    assert cmd[cmd.index("-c") + 1] == "malt_temp.mco"


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits")
def test_malt_working_dir_is_private():
    """The staging dir must not be group/world readable: it holds the CoNLL
    intermediates and the trained model."""
    staged = make_staging_dir(prefix="nltk_malt_test_")
    assert os.stat(staged).st_mode & 0o077 == 0


def test_malt_working_dir_setter_refuses_escape(pathsec_sandbox):
    """A caller may still choose the directory, but only inside the sandbox."""
    _root, outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    with pytest.raises((PermissionError, ValueError)):
        parser.working_dir = str(outside)


def test_malt_working_dir_setter_accepts_in_sandbox(pathsec_sandbox):
    """Over-block control for the setter."""
    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    parser.working_dir = str(root)
    assert parser.working_dir == str(root)


def test_malt_working_dir_is_not_shared_tempdir(pathsec_sandbox):
    """Regression: the default was ``tempfile.gettempdir()``, which is
    world-writable on Linux and gives a predictable, squattable path."""
    import tempfile as _tempfile

    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    assert os.path.realpath(parser.working_dir) != os.path.realpath(
        _tempfile.gettempdir()
    )


def test_malt_command_shape_is_unchanged(pathsec_sandbox):
    """The guard must not reorder or drop MaltParser's arguments."""
    root, _outside = pathsec_sandbox
    model = root / "engmalt.mco"
    model.write_text("model", encoding="utf-8")
    parser = _malt(str(model))
    infile, outfile = str(root / "in.conll"), str(root / "out.conll")
    with pathsec.open(infile, "w", encoding="utf-8") as handle:
        handle.write("")
    cmd = parser.generate_malt_command(infile, outfile, mode="parse")
    assert cmd[0] == "org.maltparser.Malt"
    for flag in ("-w", "-c", "-i", "-o", "-m"):
        assert flag in cmd
    assert cmd[cmd.index("-i") + 1] == infile
    assert cmd[cmd.index("-o") + 1] == outfile
    assert cmd[cmd.index("-m") + 1] == "parse"


def test_malt_working_dir_is_stable_across_calls(pathsec_sandbox):
    """The lazy property must allocate once, not a fresh dir per access, or the
    CoNLL intermediates and the model would land in different directories."""
    parser = _malt("malt_temp.mco", trained=False)
    assert parser.working_dir == parser.working_dir


def test_malt_working_dir_none_resets_to_lazy_allocation(pathsec_sandbox):
    """Regression: assigning None used to raise; it now restores the unset state
    so the property allocates again."""
    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    first = parser.working_dir
    parser.working_dir = None
    assert parser.working_dir != first or os.path.isdir(parser.working_dir)


def test_teeth_malt_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Both guards have to go before the escape reappears, which is the point:
    validate_model_resource still catches the model when validate_path is gone."""
    import nltk.parse.malt as malt

    _root, outside = pathsec_sandbox
    monkeypatch.setattr(malt, "validate_path", lambda *a, **k: None)
    monkeypatch.setattr(malt, "validate_model_resource", _passthrough)
    monkeypatch.setattr(malt, "validate_tool_path", _passthrough)
    evil = outside / "evil.mco"
    evil.write_text("model", encoding="utf-8")
    cmd = _malt(str(evil)).generate_malt_command("in.conll", "out.conll", mode="learn")
    assert cmd[cmd.index("-w") + 1] == str(outside)


def test_teeth_malt_model_resource_guard_alone_blocks(pathsec_sandbox, monkeypatch):
    """Removing only validate_path must NOT reopen the escape: the second guard
    is independently load-bearing."""
    import nltk.parse.malt as malt

    _root, outside = pathsec_sandbox
    monkeypatch.setattr(malt, "validate_path", lambda *a, **k: None)
    evil = outside / "evil.mco"
    evil.write_text("model", encoding="utf-8")
    parser = _malt(str(evil))
    infile, _outfile = _sandbox_io(parser)
    with pytest.raises((PermissionError, ValueError)):
        parser.generate_malt_command(infile, None, mode="learn")


def test_malt_working_dir_uses_the_validated_model_string(pathsec_sandbox):
    """A mutating __fspath__ must not resolve to a file the guard never saw."""
    root, outside = pathsec_sandbox
    evil = outside / "evil.mco"
    evil.write_text("x", encoding="utf-8")
    good = root / "ok.mco"
    good.write_text("m", encoding="utf-8")

    parser = _malt(_MutatingPath(str(good), str(evil)))
    infile, _outfile = _sandbox_io(parser)
    cmd = parser.generate_malt_command(infile, None, mode="learn")
    workingdir = cmd[cmd.index("-w") + 1]
    assert os.path.realpath(str(workingdir)).startswith(os.path.realpath(str(root)))


def test_malt_argv_cannot_be_injected_via_str_subclass(pathsec_sandbox):
    """The payload previously reached the JVM argv as "-c -Xmx99g"."""
    root, _outside = pathsec_sandbox
    parser = _malt(_LyingStr("-Xmx99g"))
    infile, _outfile = _sandbox_io(parser)
    with pytest.raises((PermissionError, ValueError)):
        parser.generate_malt_command(infile, None, mode="learn")


def test_malt_working_dir_is_cleaned_up(tmp_path):
    """Reclaimed malt cleanup regression: every parser that touched working_dir
    left a directory under the data root forever. The shared tempdir it replaced
    was OS-reaped, but a data root is not, so the dir is now removed at
    interpreter exit.

    Run in a real subprocess: atexit only fires when the process ends.
    """
    import subprocess
    import sys

    root = tmp_path / "nltk_data"
    root.mkdir()
    script = (
        "import nltk.data, nltk.pathsec as ps;"
        f"nltk.data.path[:] = [{str(root)!r}];"
        "ps._ALLOWED_ROOTS_CACHE = None; ps._LAST_DATA_PATHS = None;"
        "from nltk.parse.malt import MaltParser;"
        "p = MaltParser.__new__(MaltParser); p._working_dir = None;"
        "print(p.working_dir)"
    )
    env = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, env=env
    )
    assert result.returncode == 0, result.stderr
    staged = result.stdout.strip()
    assert staged.startswith(str(root))
    assert not os.path.exists(staged), f"staging dir leaked after exit: {staged}"


# StanfordParser: -model may be a filesystem path OR a jar-internal resource.


def _stanford_parser(model_path):
    import nltk.parse.stanford as st

    parser = object.__new__(st.StanfordParser)
    parser.model_path = model_path
    parser._classpath = ()
    parser.java_options = "-mx1g"
    parser._encoding = "utf8"
    parser.corenlp_options = ""
    parser._USE_STDIN = False
    return parser


def _stanford_with_options(model_path, options):
    parser = _stanford_parser(model_path)
    parser.corenlp_options = options
    return parser


@pytest.mark.parametrize(
    "model_path",
    ["/etc/passwd", "edu/stanford/../../../../etc/passwd"],
    ids=["etc-abs", "traversal"],
)
def test_stanford_parser_model_refuses_escape(pathsec_sandbox, monkeypatch, model_path):
    import nltk.parse.stanford as st

    _trap_java(monkeypatch, st, {})
    with pytest.raises((PermissionError, ValueError)):
        _stanford_parser(model_path).parse_sents([["hello", "world"]])


def test_stanford_parser_outside_model_refuses_escape(pathsec_sandbox, monkeypatch):
    import nltk.parse.stanford as st

    _root, outside = pathsec_sandbox
    _trap_java(monkeypatch, st, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("model", encoding="utf-8")
    with pytest.raises((PermissionError, ValueError)):
        _stanford_parser(str(evil)).parse_sents([["hello", "world"]])


def test_stanford_parser_default_resource_still_works(pathsec_sandbox, monkeypatch):
    """Over-block control: the shipped default is a jar-internal resource, not a
    file on disk, and must not be treated as a path."""
    import nltk.parse.stanford as st

    sink = _trap_java(monkeypatch, st, {})
    with pytest.raises(_ReachedJVM):
        _stanford_parser(_DEFAULT_RESOURCE).parse_sents([["hello", "world"]])
    assert sink["cmd"][sink["cmd"].index("-model") + 1] == _DEFAULT_RESOURCE


def test_stanford_parser_in_sandbox_model_still_works(pathsec_sandbox, monkeypatch):
    """Over-block control: a real model inside a data root must still load."""
    import nltk.parse.stanford as st

    root, _outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, st, {})
    model = root / "englishPCFG.ser.gz"
    model.write_text("model", encoding="utf-8")
    with pytest.raises(_ReachedJVM):
        _stanford_parser(str(model)).parse_sents([["hello", "world"]])
    assert sink["cmd"][sink["cmd"].index("-model") + 1] == str(model)


def test_teeth_stanford_parser_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    import nltk.parse.stanford as st

    _trap_java(monkeypatch, st, {})
    monkeypatch.setattr(st, "validate_model_resource", _passthrough)
    with pytest.raises(_ReachedJVM):
        _stanford_parser("/etc/passwd").parse_sents([["hello", "world"]])


def test_stanford_model_argv_carries_the_validated_string(pathsec_sandbox, monkeypatch):
    """The argv entry must be the exact string the guard checked, not an object
    that can resolve to something else when the child process reads it."""
    import nltk.parse.stanford as st

    root, outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, st, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("x", encoding="utf-8")
    good = root / "ok.ser.gz"
    good.write_text("m", encoding="utf-8")

    parser = _stanford_parser(_MutatingPath(str(good), str(evil)))
    with pytest.raises(_ReachedJVM):
        parser.parse_sents([["hello", "world"]])
    handed_over = sink["cmd"][sink["cmd"].index("-model") + 1]
    assert isinstance(handed_over, str)
    assert os.path.realpath(_resolve(handed_over)).startswith(
        os.path.realpath(str(root))
    )


# StanfordParser corenlp_options: split into argv, so it can append a 2nd -model.


@pytest.mark.parametrize(
    "options",
    [
        "-model /etc/passwd",
        "-model ../../../etc/passwd",
        "-loadClassifier /etc/passwd",
        "-outputFormat xml",
        "-encoding utf8",
        "-sentences newline",
    ],
    ids=[
        "second-model-abs",
        "second-model-traversal",
        "loadClassifier-abs",
        "dup-outputFormat",
        "dup-encoding",
        "dup-sentences",
    ],
)
def test_corenlp_options_cannot_override_guarded_flags(
    pathsec_sandbox, monkeypatch, options
):
    import nltk.parse.stanford as st

    root, _outside = pathsec_sandbox
    _trap_java(monkeypatch, st, {})
    model = str(root / "ok.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    with pytest.raises((PermissionError, ValueError)):
        _stanford_with_options(model, options).parse_sents([["hi", "there"]])


def test_corenlp_options_cannot_point_outside_the_roots(pathsec_sandbox, monkeypatch):
    import nltk.parse.stanford as st

    root, outside = pathsec_sandbox
    _trap_java(monkeypatch, st, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("x", encoding="utf-8")
    model = str(root / "ok.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    with pytest.raises((PermissionError, ValueError)):
        _stanford_with_options(model, f"-serializedDict {evil}").parse_sents(
            [["hi", "there"]]
        )


@pytest.mark.parametrize(
    "options",
    [
        "",
        "-maxLength 40",
        "-serializedDict edu/stanford/nlp/x.ser.gz",
        "-retainTMPSubcategories",
    ],
    ids=["empty", "new-flag", "resource-value", "bare-flag"],
)
def test_corenlp_options_passthrough_still_works(pathsec_sandbox, monkeypatch, options):
    """Over-block control: this is a general passthrough for the tool's own
    settings, so anything that is neither a duplicate nor an out-of-root path
    must still reach the JVM."""
    import nltk.parse.stanford as st

    root, _outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, st, {})
    model = str(root / "ok.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    with pytest.raises(_ReachedJVM):
        _stanford_with_options(model, options).parse_sents([["hi", "there"]])
    assert sink["cmd"][sink["cmd"].index("-model") + 1] == model
    for token in options.split():
        assert token in sink["cmd"]


def test_teeth_corenlp_options_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Restore the raw split and the injected -model reaches the JVM again."""
    import nltk.parse.stanford as st

    root, outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, st, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("x", encoding="utf-8")
    model = str(root / "ok.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    monkeypatch.setattr(
        st.StanfordParser,
        "_validated_extra_options",
        lambda self, cmd: self.corenlp_options.split(),
    )
    with pytest.raises(_ReachedJVM):
        _stanford_with_options(model, f"-model {evil}").parse_sents([["hi", "there"]])
    models = [sink["cmd"][i + 1] for i, x in enumerate(sink["cmd"]) if x == "-model"]
    assert str(evil) in models


# Functional: the patched wrappers must still import with no new import cycle.


def test_wrapper_modules_still_import():
    """Both wrappers touched by this change import cleanly, with no import cycle
    introduced by the new pathsec dependency."""
    import importlib

    for name in ("nltk.parse.malt", "nltk.parse.stanford"):
        assert importlib.import_module(name) is not None


# Real end-to-end runs. These launch an actual JVM against a real MaltParser /
# Stanford parser install; they skip when the external tool is genuinely absent.


def _has_java():
    """True only if a JVM actually *runs*.

    Merely finding a ``java`` on PATH is not enough: macOS ships a
    ``/usr/bin/java`` stub that resolves fine and then fails at exec time with
    "Unable to locate a Java Runtime", which would turn these into hard failures
    on a machine with no JDK instead of skips.
    """
    import subprocess

    from nltk.internals import find_binary

    try:
        binary = find_binary(
            "java", env_vars=("JAVAHOME", "JAVA_HOME"), verbose=False, binary_names=None
        )
    except LookupError:
        return False
    try:
        return (
            subprocess.run(
                [binary, "-version"], capture_output=True, timeout=60
            ).returncode
            == 0
        )
    except (OSError, subprocess.SubprocessError):
        return False


def _find_tool_dir(*names):
    """Absolute path of an external tool directory inside a data root, or None."""
    import nltk.data

    for root in nltk.data.path:
        for name in names:
            candidate = os.path.join(root, name)
            if os.path.isdir(candidate):
                return candidate
    return None


requires_java = pytest.mark.skipif(not _has_java(), reason="no JVM on this machine")


@requires_java
def test_real_malt_train_writes_model_inside_sandbox(tmp_path):
    """End-to-end: a real MaltParser JVM must write malt_temp.mco into the private
    staging dir, and must NOT pollute the current working directory as it did when
    ``-w`` defaulted to ``os.getcwd()``."""
    import nltk.data
    from nltk.parse.dependencygraph import DependencyGraph
    from nltk.parse.malt import MaltParser

    malt_dir = _find_tool_dir("maltparser-1.9.2", "maltparser-1.9.1")
    if malt_dir is None:
        pytest.skip("maltparser is not installed under nltk.data.path")

    parser = MaltParser(parser_dirname=malt_dir)
    assert os.stat(parser.working_dir).st_mode & 0o077 == 0
    assert any(
        os.path.realpath(parser.working_dir).startswith(os.path.realpath(root))
        for root in nltk.data.path
    )

    rows = "1\tJohn\t_\tNNP\t_\t_\t2\tSUBJ\t_\t_\n2\tsees\t_\tVB\t_\t_\t0\tROOT\t_\t_\n"
    parser.train([DependencyGraph(rows), DependencyGraph(rows)], verbose=False)

    model = os.path.join(parser.working_dir, "malt_temp.mco")
    assert os.path.exists(model) and os.path.getsize(model) > 0
    assert not os.path.exists(os.path.join(os.getcwd(), "malt_temp.mco"))


@requires_java
def test_real_stanford_parser_default_resource_parses(monkeypatch):
    """End-to-end: the shipped jar-internal default model must still parse. If the
    guard treated it as a filesystem path this raises instead."""
    from nltk.parse.stanford import StanfordParser

    parser_dir = _find_tool_dir("stanford-parser-full-2020-11-17")
    if parser_dir is None:
        pytest.skip("stanford-parser is not installed under nltk.data.path")
    monkeypatch.setenv("STANFORD_PARSER", parser_dir)
    monkeypatch.setenv("STANFORD_MODELS", parser_dir)

    trees = list(StanfordParser().raw_parse("John sees a dog."))
    assert trees and trees[0].label() == "ROOT"


@requires_java
@pytest.mark.parametrize(
    "model_path",
    [
        "/etc/passwd" if os.name == "posix" else "C:\\Windows\\win.ini",
        "edu/stanford/../../../../etc/passwd",
    ],
    ids=["system-file-abs", "traversal"],
)
def test_real_stanford_parser_refuses_escape_with_jvm_present(monkeypatch, model_path):
    """End-to-end negative: with a working JVM and real jars, a hostile -model is
    refused before launch, so the block is the guard and not a missing JVM."""
    from nltk.parse.stanford import StanfordParser

    parser_dir = _find_tool_dir("stanford-parser-full-2020-11-17")
    if parser_dir is None:
        pytest.skip("stanford-parser is not installed under nltk.data.path")
    monkeypatch.setenv("STANFORD_PARSER", parser_dir)
    monkeypatch.setenv("STANFORD_MODELS", parser_dir)

    parser = StanfordParser()
    parser.model_path = model_path
    with pytest.raises((PermissionError, ValueError)):
        list(parser.raw_parse("John sees a dog."))

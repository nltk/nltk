# Natural Language Toolkit: pathsec sweep over the external-tool wrappers
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Escape matrix for the model/data paths handed to external tools.

The JVM wrappers take caller-supplied model and corpus paths and pass them
straight into the child process's argv. Those are *data* paths, so they must be
bounded to the NLTK data roots; a path outside the sandbox means the wrapper will
read (and, for MaltParser's ``-w`` in learn mode, WRITE) anywhere on disk.

Two classes of path are deliberately treated differently:

* **model / corpus paths** (this file) are bounded with ``pathsec.validate_path``
  or ``pathsec.validate_model_resource``.
* **install / binary directories** (``candc``/``boxer``'s ``bin_dir``, REPP's
  tokenizer dir) are NOT: ``validate_path`` permits only NLTK *data* roots, so
  bounding them would break every real installation. They get an absolute-path
  (CWE-426) check instead, and the tests at the end of this file pin that
  distinction so a later refactor cannot quietly collapse the two.

Every test drives the real code path with only the ``java`` hand-off replaced, so
a probe cannot pass merely because the argv was assembled by the test itself.
"""

import hashlib
import os

import pytest

from nltk import pathsec
from nltk.data import make_staging_dir
from nltk.pathsec import validate_model_resource, validate_tool_path


class _ReachedJVM(Exception):
    """Raised by the trapped ``java`` so a test can tell "the argv was built and
    handed off" apart from "a guard refused first"."""


def _passthrough(value, *args, **kwargs):
    """A neutered guard: performs no checks but still returns the path, since
    the callers now use the value the guard hands back."""
    return os.fspath(value)


def _trap_java(monkeypatch, module, sink):
    """Replace ``module.java`` with a trap that records argv and stops before
    launching a JVM."""

    def fake_java(cmd, *args, **kwargs):
        sink["cmd"] = list(cmd)
        raise _ReachedJVM

    monkeypatch.setattr(module, "java", fake_java)
    return sink


# ---------------------------------------------------------------------------
# StanfordSegmenter: -loadClassifier / -serDictionary / -sighanCorporaDict /
# -textFile all reach the JVM argv.
# ---------------------------------------------------------------------------


def _segmenter(monkeypatch, root, model=None, dictionary=None, sihan=None):
    """A StanfordSegmenter whose jar passes the sha256 allowlist, so the test
    reaches the model-path handling rather than stopping at the jar check."""
    import nltk.tokenize.stanford_segmenter as seg

    jar = os.path.join(root, "seg.jar")
    with pathsec.open(jar, "wb") as handle:
        handle.write(b"PK\x05\x06" + b"\0" * 18)
    with pathsec.open(jar, "rb") as handle:
        digest = hashlib.sha256(handle.read()).hexdigest()
    monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)

    tool = object.__new__(seg.StanfordSegmenter)
    tool._stanford_jar = jar
    tool._encoding = "utf8"
    tool.java_options = "-mx1g"
    tool._jar_sha256_cache = {}
    tool._java_class = "edu.stanford.nlp.ie.crf.CRFClassifier"
    tool._model = model
    tool._dict = dictionary
    tool._sihan_corpora_dict = sihan
    tool._sihan_post_processing = "true"
    tool._keep_whitespaces = "false"
    tool._options_cmd = ""
    return tool


# ---------------------------------------------------------------------------
# MaltParser: -c model and the -w working directory (WRITTEN to in learn mode).
# ---------------------------------------------------------------------------


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
    with pathsec.open(infile, "w") as handle:
        handle.write("")
    return infile, os.path.join(parser.working_dir, "out.conll")


# ---------------------------------------------------------------------------
# StanfordParser: -model may be a filesystem path OR a jar-internal resource.
# ---------------------------------------------------------------------------

_DEFAULT_RESOURCE = "edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz"


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


# ---------------------------------------------------------------------------
# validate_model_resource itself.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "edu/stanford/../nlp/x.ser.gz",
        "../x.ser.gz",
        "a/b/../../../etc/passwd",
        "edu\\stanford\\..\\x.ser.gz",
    ],
)
def test_validate_model_resource_rejects_traversal(value):
    """``..`` is refused whether or not the value looks like a real path, so a
    resource name cannot escape the jar namespace."""
    with pytest.raises(ValueError):
        validate_model_resource(value, context="test")


@pytest.mark.parametrize(
    "value",
    [_DEFAULT_RESOURCE, "edu/stanford/nlp/models/pos-tagger/english-left3words.tagger"],
)
def test_validate_model_resource_allows_resource_names(value):
    """A bare classpath resource is not a filesystem path and is left alone."""
    validate_model_resource(value, context="test")


def test_validate_model_resource_bounds_real_paths(pathsec_sandbox):
    root, outside = pathsec_sandbox
    inside = root / "m.ser.gz"
    inside.write_text("m")
    validate_model_resource(str(inside), context="test")
    with pytest.raises((PermissionError, ValueError)):
        validate_model_resource(str(outside / "m.ser.gz"), context="test")


def test_validate_model_resource_accepts_pathlike(pathsec_sandbox):
    """os.PathLike must not blow up on ``.replace``."""
    root, _outside = pathsec_sandbox
    inside = root / "m.ser.gz"
    inside.write_text("m")
    validate_model_resource(inside, context="test")


def test_validate_model_resource_is_exported():
    assert "validate_model_resource" in pathsec.__all__


# ---------------------------------------------------------------------------
# Teeth: neuter each guard and assert the attack becomes reachable again. A
# probe that passes with the guard removed is not testing the guard.
# ---------------------------------------------------------------------------


def test_teeth_segmenter_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    _trap_java(monkeypatch, seg, {})
    monkeypatch.setattr(seg, "validate_path", _passthrough)
    monkeypatch.setattr(seg, "validate_tool_path", _passthrough)
    tool = _segmenter(monkeypatch, str(root))
    with pytest.raises(_ReachedJVM):
        tool.segment_file("/etc/passwd")


# ---------------------------------------------------------------------------
# Install-directory wrappers: pinned as a DIFFERENT class. These must keep the
# CWE-426 absolute-path check and must NOT gain validate_path, which permits
# only NLTK data roots and would break every real installation.
# ---------------------------------------------------------------------------


def test_boxer_bin_dir_rejects_relative_and_cwd(pathsec_sandbox):
    """A relative or CWD bin_dir is a binary-planting vector (CWE-426)."""
    import nltk.sem.boxer as boxer

    _root, outside = pathsec_sandbox
    bindir = outside / "candcbin"
    bindir.mkdir()
    for name in ("candc", "boxer"):
        target = bindir / name
        target.write_text("#!/bin/sh\n")
        target.chmod(0o755)
    os.chdir(str(outside))

    tool = object.__new__(boxer.Boxer)
    for bad in ("candcbin", "."):
        with pytest.raises(LookupError):
            tool.set_bin_dir(bad)


def test_boxer_models_path_is_derived_not_caller_supplied(pathsec_sandbox):
    """``--models`` has no independent input: it is derived from the absolute
    candc binary, so bounding bin_dir bounds the models dir too."""
    import nltk.sem.boxer as boxer

    _root, outside = pathsec_sandbox
    bindir = outside / "candcbin"
    bindir.mkdir()
    for name in ("candc", "boxer"):
        target = bindir / name
        target.write_text("#!/bin/sh\n")
        target.chmod(0o755)

    tool = object.__new__(boxer.Boxer)
    tool.set_bin_dir(str(bindir))
    assert tool._candc_models_path == os.path.normpath(str(outside / "models"))


def test_repp_dir_must_resolve_absolute(pathsec_sandbox):
    """REPP executes ``<dir>/src/repp``; a CWD-relative dir would let an
    attacker plant that binary."""
    import nltk.tokenize.repp as repp

    _root, outside = pathsec_sandbox
    tree = outside / "evil_repp"
    (tree / "src").mkdir(parents=True)
    (tree / "erg").mkdir()
    (tree / "src" / "repp").write_text("#!/bin/sh\n")
    (tree / "erg" / "repp.set").write_text("")
    os.environ.pop("REPP_TOKENIZER", None)
    os.chdir(str(outside))

    tokenizer = object.__new__(repp.ReppTokenizer)
    with pytest.raises(LookupError):
        tokenizer.find_repptokenizer("evil_repp")


# ---------------------------------------------------------------------------
# Functional: the patched modules must still import and behave. These exercise
# the real objects rather than asserting on mocks.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Real end-to-end runs. These launch an actual JVM against a real MaltParser /
# Stanford parser install, so they prove the guards neither break the feature
# nor "pass" merely because no JVM was reachable. They skip when the external
# tool is genuinely absent (CI has no JVM or model jars); every other test in
# this file runs unconditionally.
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Expanded vector matrix. Every entry below was run against the live sinks; the
# ones that leaked drove the hardening in validate_model_resource. Benign and
# merely-suspicious candidates are kept so a regression shows up as a new leak.
# ---------------------------------------------------------------------------


def _hostile_vectors(root, outside):
    """(id, value) pairs that must never reach an external tool."""
    secret = outside / "secret.mco"
    secret.write_text("SECRET")

    system_file = "/etc/passwd" if os.name == "posix" else "C:\\Windows\\win.ini"
    vectors = [
        ("outside-abs", str(secret)),
        ("system-file-abs", system_file),
        ("traversal-from-root", os.path.join(str(root), "..", "..", "etc", "passwd")),
        ("nul-byte", system_file[:5] + "\x00" + system_file[5:]),
        ("leading-dash", "-Xmx99g"),
        ("newline-injection", system_file + "\n-serDictionary " + system_file),
        ("backslash-traversal", "..\\..\\..\\etc\\passwd"),
        ("file-url", "file:///etc/passwd"),
        ("http-url", "http://evil.example/model.gz"),
        ("empty", ""),
        ("whitespace-only", "   "),
        ("dir-not-file", str(outside)),
    ]

    symlink = root / "sym.mco"
    os.symlink(str(secret), symlink)
    vectors.append(("symlink-to-outside", str(symlink)))

    symlink_etc = root / "symetc"
    os.symlink("/etc/passwd", symlink_etc)
    vectors.append(("symlink-to-etc", str(symlink_etc)))

    symlinked_dir = root / "symdir"
    os.symlink(str(outside), symlinked_dir)
    vectors.append(("via-symlinked-dir", str(symlinked_dir / "secret.mco")))

    # Hardlinks are deliberately NOT in this matrix: they are refused only for
    # paths the tool writes. See the dedicated tests below.
    return vectors


def _vector_ids(vectors):
    return [name for name, _ in vectors]


def test_validate_model_resource_refuses_every_hostile_vector(pathsec_sandbox):
    """The whole matrix at once, so a new leak names itself in the failure."""
    root, outside = pathsec_sandbox
    leaked = []
    for name, value in _hostile_vectors(root, outside):
        try:
            validate_model_resource(value, context="sweep")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"validate_model_resource let these through: {leaked}"


def test_malt_model_refuses_every_hostile_vector(pathsec_sandbox):
    root, outside = pathsec_sandbox
    leaked = []
    for name, value in _hostile_vectors(root, outside):
        try:
            parser = _malt(value)
            infile, _outfile = _sandbox_io(parser)
            parser.generate_malt_command(infile, None, mode="learn")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"MaltParser passed these to the JVM: {leaked}"


def test_malt_working_dir_setter_refuses_every_hostile_vector(pathsec_sandbox):
    root, outside = pathsec_sandbox
    leaked = []
    for name, value in _hostile_vectors(root, outside):
        parser = _malt("malt_temp.mco", trained=False)
        try:
            parser.working_dir = value
        except (PermissionError, ValueError, OSError):
            continue
        # An in-root staging dir is the only acceptable outcome.
        if not os.path.realpath(parser.working_dir).startswith(
            os.path.realpath(str(root))
        ):
            leaked.append(name)
    assert leaked == [], f"working_dir accepted these: {leaked}"


def _hardlink_into(root, outside):
    secret = outside / "secret.mco"
    secret.write_text("SECRET")
    alias = root / "alias.mco"
    try:
        os.link(str(secret), alias)
    except OSError:  # pragma: no cover - cross-device or unsupported
        pytest.skip("hard links unavailable between these directories")
    return str(alias)


def test_hardlinked_write_target_is_refused(pathsec_sandbox):
    """realpath() cannot see a hardlink, so an in-root alias of an outside file
    passes every path check and the tool would overwrite the original."""
    root, outside = pathsec_sandbox
    alias = _hardlink_into(root, outside)
    with pytest.raises(PermissionError):
        validate_tool_path(alias, context="sweep", for_write=True)


@pytest.mark.skipif(os.name != "posix", reason="st_nlink hardlink guard is POSIX-only")
def test_hardlinked_read_target_is_refused_by_the_tool_guard(pathsec_sandbox):
    """validate_tool_path refuses a multiply-linked file for READS as well.

    The two branches merged here disagreed. The wrapper work allowed it, on the
    grounds that creating the link already needs write access to the data root
    and that refusing st_nlink > 1 also refuses ordinary deduplicated trees
    (cp -l, rsync --link-dest) and the ORIGINAL file, since both names share the
    count. The tagger work refused it, because a hardlink names an inode that may
    live outside the sandbox and no path resolution can see that (CWE-59).

    The stricter reading wins for the sinks that open a file directly. The
    trade-off is recorded here rather than dropped: a user whose models live in a
    hardlink-deduplicated tree will need a plain copy.
    """
    root, outside = pathsec_sandbox
    alias = _hardlink_into(root, outside)
    with pytest.raises(PermissionError):
        validate_tool_path(alias, context="sweep")
    # validate_model_resource keeps the laxer rule: it also serves values that
    # are classpath resources rather than files the guard is about to open.
    validate_model_resource(alias, context="sweep")


def test_single_linked_model_is_allowed(pathsec_sandbox):
    """Over-block control for the hardlink guard: an ordinary file has one link."""
    root, _outside = pathsec_sandbox
    model = root / "plain.mco"
    model.write_text("m")
    validate_model_resource(str(model), context="sweep")
    validate_tool_path(str(model), context="sweep", for_write=True)


def test_directory_model_is_not_hardlink_rejected(pathsec_sandbox):
    """Directories always have st_nlink >= 2, so the guard must apply to regular
    files only or every corpus directory would be refused."""
    root, _outside = pathsec_sandbox
    corpus = root / "sihan"
    corpus.mkdir()
    validate_model_resource(str(corpus), context="sweep")


@pytest.mark.parametrize(
    "value",
    [
        "malt_temp.mco",
        _DEFAULT_RESOURCE,
        "edu/stanford/nlp/models/pos-tagger/english-left3words.tagger",
    ],
)
def test_benign_resource_names_still_pass(value):
    """The values NLTK itself uses must survive every check added above."""
    validate_model_resource(value, context="sweep")


# ---------------------------------------------------------------------------
# Exotic vectors: NUL truncation, '~', NTFS streams, UNC shares and blocking
# device nodes. Each of these leaked when first run and drove a guard.
# ---------------------------------------------------------------------------


def _exotic_vectors(root):
    vectors = [
        ("tilde-expansion", "~/.ssh/id_rsa"),
        *([] if os.name == "posix" else [("ads-stream", "model.mco:evil")]),
        ("unc-backslash", "\\\\server\\share\\evil.mco"),
        ("unc-slash", "//server/share/evil.mco"),
        ("nul-in-middle", "model\x00.mco"),
        ("jar-url", "jar:file:///etc/passwd!/x"),
        ("double-slash", "//etc//passwd"),
        ("dotdot-alone", ".."),
    ]
    if os.name == "posix":
        # Character devices and procfs exist only here; on Windows these are
        # ordinary non-existent relative names and prove nothing.
        vectors += [
            ("dev-stdin", "/dev/stdin"),
            ("dev-null", "/dev/null"),
            ("proc-environ", "/proc/self/environ"),
            ("case-folded-etc", "/ETC/PASSWD"),
            ("overlong-name", "/" + ("A" * 300) + "/evil.mco"),
            ("root-only", "/"),
        ]
    else:
        vectors += [
            ("windows-device", "NUL"),
            ("windows-system-file", "C:\\Windows\\System32\\config\\SAM"),
            ("drive-relative", "C:evil.mco"),
        ]

    fifo = root / "fifo.mco"
    try:
        os.mkfifo(fifo)
    except (AttributeError, OSError):  # pragma: no cover - not on Windows
        pass
    else:
        vectors.append(("fifo-in-root", str(fifo)))
    return vectors


def test_validate_model_resource_refuses_exotic_vectors(pathsec_sandbox):
    root, _outside = pathsec_sandbox
    leaked = []
    for name, value in _exotic_vectors(root):
        try:
            validate_model_resource(value, context="sweep")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"validate_model_resource let these through: {leaked}"


@pytest.mark.skipif(not hasattr(__import__("socket"), "AF_UNIX"), reason="no AF_UNIX")
def test_unix_socket_model_is_refused(pathsec_sandbox):
    """A socket planted in a data root is not a model; reading it would block."""
    import socket

    root, _outside = pathsec_sandbox
    path = str(root / "s.sock")
    sock = socket.socket(socket.AF_UNIX)
    try:
        sock.bind(path)
        with pytest.raises(PermissionError):
            validate_model_resource(path, context="sweep")
    finally:
        sock.close()


@pytest.mark.parametrize(
    "value",
    [
        "$EVIL_HOME/passwd",
        "..\uff0f..\uff0fetc\uff0fpasswd",
        "%2e%2e/%2e%2e/etc/passwd",
    ],
    ids=["env-var", "fullwidth-solidus", "percent-encoded"],
)
def test_benign_lookalikes_stay_literal(pathsec_sandbox, value):
    """These are permitted because nothing downstream expands or decodes them:
    they stay literal filenames. The test pins that assumption, so if a sink ever
    starts expanding them this fails instead of silently reading /etc.
    """
    validate_model_resource(value, context="sweep")
    assert not os.path.exists(value)
    assert not os.path.realpath(os.path.expandvars(value)).startswith("/etc/")


def test_java_inner_class_resource_is_allowed():
    """Over-block control: '$' is legal in a JVM resource name, so the option and
    stream checks must not reject it."""
    validate_model_resource("edu/stanford/Foo$Bar.ser.gz", context="sweep")


def test_windows_drive_path_is_not_stream_rejected():
    """Over-block control: 'C:\\...' is a drive prefix, not an NTFS stream."""
    import re as _re

    from nltk.pathsec import validate_model_resource as _vmr

    try:
        _vmr("C:\\models\\english.ser.gz", context="sweep")
    except ValueError as exc:
        assert "alternate data stream" not in str(exc), exc
    except PermissionError:
        # On Windows this IS an absolute path, so it is (correctly) refused for
        # being outside the data roots. That is not the stream rejection.
        pass
    assert _re.match(r"^[A-Za-z]:[\\/]", "C:\\models\\english.ser.gz")


# ---------------------------------------------------------------------------
# Regressions found while building this PR. Each one shipped a bug that the
# mocked tests missed, so they are pinned here permanently.
# ---------------------------------------------------------------------------


def test_regression_generate_malt_command_needs_no_trained_attribute(pathsec_sandbox):
    """Regression: generate_malt_command briefly branched on a private ``_trained``
    attribute, which broke every caller that built a parser without it."""
    import nltk.parse.malt as malt

    parser = object.__new__(malt.MaltParser)
    parser.model = "malt_temp.mco"
    parser._working_dir = None
    parser.additional_java_args = []
    infile = os.path.join(parser.working_dir, "in.conll")
    with pathsec.open(infile, "w") as handle:
        handle.write("")
    cmd = parser.generate_malt_command(infile, None, mode="learn")
    assert cmd[cmd.index("-c") + 1] == "malt_temp.mco"


def test_regression_trained_bare_model_resolves_to_working_dir(pathsec_sandbox):
    """Regression: after train(), ``self.model`` is still the bare name
    ``malt_temp.mco`` while ``_trained`` is True. Resolving that against the CWD
    made every post-training parse fail with a security violation."""
    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=True)
    infile = os.path.join(parser.working_dir, "in.conll")
    outfile = os.path.join(parser.working_dir, "out.conll")
    with pathsec.open(infile, "w") as handle:
        handle.write("")
    cmd = parser.generate_malt_command(infile, outfile, mode="parse")
    workingdir = cmd[cmd.index("-w") + 1]
    assert os.path.realpath(workingdir).startswith(os.path.realpath(str(root)))
    assert os.path.realpath(workingdir) != os.path.realpath(os.getcwd())


def test_regression_working_dir_setter_rejects_empty(pathsec_sandbox):
    """Regression: an empty working_dir passed validate_path and reached
    MaltParser as ``-w ""``, i.e. the current working directory."""
    parser = _malt("malt_temp.mco", trained=False)
    for value in ("", "   "):
        with pytest.raises(ValueError):
            parser.working_dir = value


def test_regression_has_java_probe_actually_executes():
    """Regression: the JVM probe used to accept any ``java`` on PATH. macOS ships
    a /usr/bin/java stub that resolves fine and then fails at exec, which turned
    the end-to-end tests into hard failures instead of skips."""
    import subprocess

    result = _has_java()
    assert isinstance(result, bool)
    if result:
        from nltk.internals import find_binary

        binary = find_binary(
            "java", env_vars=("JAVAHOME", "JAVA_HOME"), verbose=False, binary_names=None
        )
        assert subprocess.run([binary, "-version"], capture_output=True).returncode == 0


# ---------------------------------------------------------------------------
# MaltParser -i / -o. Both are public: generate_malt_command() takes them
# directly and train_from_file() is the public route to -i. -i is READ by the
# JVM and -o is WRITTEN by it, so an unbounded value is an arbitrary file read
# and an arbitrary file write.
# ---------------------------------------------------------------------------


def _malt_in_sandbox(root):
    parser = _malt("malt_temp.mco", trained=False)
    parser.malt_jars = []
    infile = os.path.join(parser.working_dir, "in.conll")
    with pathsec.open(infile, "w") as handle:
        handle.write("")
    return parser, infile


def test_malt_input_file_refuses_every_hostile_vector(pathsec_sandbox):
    """-i is an arbitrary-file-read primitive without a guard."""
    root, outside = pathsec_sandbox
    parser, _infile = _malt_in_sandbox(root)
    leaked = []
    for name, value in _hostile_vectors(root, outside):
        try:
            parser.generate_malt_command(value, None, mode="learn")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"MaltParser -i accepted: {leaked}"


def test_malt_output_file_refuses_every_hostile_vector(pathsec_sandbox):
    """-o is an arbitrary-file-WRITE primitive without a guard."""
    root, outside = pathsec_sandbox
    parser, infile = _malt_in_sandbox(root)
    leaked = []
    for name, value in _hostile_vectors(root, outside):
        try:
            parser.generate_malt_command(infile, value, mode="parse")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"MaltParser -o accepted: {leaked}"


def test_malt_train_from_file_refuses_outside_corpus(pathsec_sandbox):
    """train_from_file is the public route to -i."""
    root, outside = pathsec_sandbox
    parser, _infile = _malt_in_sandbox(root)
    corpus = outside / "steal.conll"
    corpus.write_text("1\ta\t_\tNN\t_\t_\t0\tROOT\t_\t_\n")
    for target in ("/etc/passwd", str(corpus)):
        with pytest.raises((PermissionError, ValueError)):
            parser.train_from_file(target)


def test_malt_in_sandbox_input_and_output_are_allowed(pathsec_sandbox):
    """Over-block control: the internal callers pass temp files inside
    working_dir, which must keep working."""
    root, _outside = pathsec_sandbox
    parser, infile = _malt_in_sandbox(root)
    outfile = os.path.join(parser.working_dir, "out.conll")
    cmd = parser.generate_malt_command(infile, outfile, mode="parse")
    assert cmd[cmd.index("-i") + 1] == infile
    assert cmd[cmd.index("-o") + 1] == outfile


def test_teeth_malt_io_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Neuter the guard and -o reaches the JVM again."""
    import nltk.parse.malt as malt

    root, outside = pathsec_sandbox
    parser, infile = _malt_in_sandbox(root)
    monkeypatch.setattr(malt, "validate_tool_path", _passthrough)
    target = str(outside / "pwned.conll")
    cmd = parser.generate_malt_command(infile, target, mode="parse")
    assert cmd[cmd.index("-o") + 1] == target


def test_malt_revalidates_on_every_call(pathsec_sandbox):
    """No cached verdict: a model swapped after a successful call is re-checked,
    so an attacker cannot 'warm up' the parser with a benign value first."""
    root, outside = pathsec_sandbox
    parser, infile = _malt_in_sandbox(root)
    parser.generate_malt_command(infile, None, mode="learn")
    evil = outside / "evil.mco"
    evil.write_text("x")
    parser.model = str(evil)
    with pytest.raises((PermissionError, ValueError)):
        parser.generate_malt_command(infile, None, mode="learn")


def test_edited_wrappers_never_widen_the_sandbox(pathsec_sandbox):
    """Regression guard for the worst bug class in this audit: a loader that
    appends its target to nltk.data.path and clears the pathsec root cache
    disarms validate_path process-wide. None of the modules touched here may do
    that, whatever else they change.
    """
    import nltk.data

    before = list(nltk.data.path)
    root, outside = pathsec_sandbox
    parser, infile = _malt_in_sandbox(root)
    for target in ("/etc/passwd", str(outside / "evil.mco")):
        for call in (
            lambda t=target: parser.generate_malt_command(t, None, mode="learn"),
            lambda t=target: setattr(parser, "working_dir", t),
            lambda t=target: validate_model_resource(t, context="widen"),
        ):
            try:
                call()
            except (PermissionError, ValueError, OSError):
                pass
    assert list(nltk.data.path) == before
    with pytest.raises(PermissionError):
        pathsec.validate_path("/etc/passwd", context="widen-check")


# ---------------------------------------------------------------------------
# validate_tool_path. Contract differs from validate_model_resource: this one
# never accepts a bare resource name, because the tool opens the value directly.
# ---------------------------------------------------------------------------


def test_validate_tool_path_refuses_every_hostile_vector(pathsec_sandbox):
    root, outside = pathsec_sandbox
    leaked = []
    for name, value in _hostile_vectors(root, outside) + _exotic_vectors(root):
        try:
            validate_tool_path(value, context="sweep")
        except (PermissionError, ValueError, OSError):
            continue
        leaked.append(name)
    assert leaked == [], f"validate_tool_path let these through: {leaked}"


def test_validate_tool_path_rejects_bare_resource_names(pathsec_sandbox):
    """Unlike a model argument, an -i/-o value is never a classpath resource: a
    bare name would resolve against the current working directory."""
    for value in ("in.conll", "malt_temp.mco", _DEFAULT_RESOURCE):
        with pytest.raises((PermissionError, ValueError)):
            validate_tool_path(value, context="sweep")


def test_validate_tool_path_allows_in_sandbox_paths(pathsec_sandbox):
    """Over-block control, including a not-yet-created output file."""
    root, _outside = pathsec_sandbox
    existing = root / "in.conll"
    existing.write_text("")
    validate_tool_path(str(existing), context="sweep")
    # A destination the tool will create does not exist yet.
    validate_tool_path(str(root / "out.conll"), context="sweep", must_exist=False)


def test_malt_output_file_refuses_hardlink(pathsec_sandbox):
    """-o is written by the JVM, so a hardlinked target would clobber the file
    it aliases outside the roots."""
    root, outside = pathsec_sandbox
    alias = _hardlink_into(root, outside)
    parser, infile = _malt_in_sandbox(root)
    with pytest.raises(PermissionError):
        parser.generate_malt_command(infile, alias, mode="parse")


def test_validate_tool_path_refuses_fifo(pathsec_sandbox):
    """An output path that is a FIFO would block the JVM forever."""
    root, _outside = pathsec_sandbox
    fifo = root / "out.fifo"
    try:
        os.mkfifo(fifo)
    except (AttributeError, OSError):  # pragma: no cover - not on Windows
        pytest.skip("mkfifo unavailable")
    with pytest.raises(PermissionError):
        validate_tool_path(str(fifo), context="sweep")


def test_validate_tool_path_is_exported():
    assert "validate_tool_path" in pathsec.__all__


def test_regression_bare_model_name_is_not_probed_against_cwd(pathsec_sandbox):
    """Regression: validate_model_resource decided "is this a real path?" with
    os.path.exists(), which resolves relative to the CWD. A stray malt_temp.mco
    in the user's directory therefore made the DEFAULT MaltParser() flow die with
    a security violation. Older NLTK wrote exactly that file into the CWD, so an
    upgrade would have tripped it.
    """
    root, _outside = pathsec_sandbox
    os.chdir(str(root.parent))
    decoy = root.parent / "malt_temp.mco"
    decoy.write_text("decoy")
    try:
        validate_model_resource("malt_temp.mco", context="sweep")
        parser, infile = _malt_in_sandbox(root)
        parser.model = "malt_temp.mco"
        cmd = parser.generate_malt_command(infile, None, mode="learn")
        assert cmd[cmd.index("-c") + 1] == "malt_temp.mco"
    finally:
        decoy.unlink()


def test_regression_staging_dirs_are_cleaned_up(tmp_path):
    """Regression: every parser that touched working_dir left a directory under
    the data root forever. The shared tempdir it replaced was OS-reaped, but a
    data root is not, so the dir is now removed at interpreter exit.

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


def test_working_dir_none_resets_to_lazy_allocation(pathsec_sandbox):
    """Regression: assigning None used to raise; it now restores the unset state
    so the property allocates again."""
    root, _outside = pathsec_sandbox
    parser = _malt("malt_temp.mco", trained=False)
    first = parser.working_dir
    parser.working_dir = None
    assert parser.working_dir != first or os.path.isdir(parser.working_dir)


@pytest.mark.parametrize(
    "value",
    ["NUL", "CON", "COM1", "LPT1", "nul.ser.gz", "models/COM9.mco", "AUX"],
)
@pytest.mark.skipif(os.name == "posix", reason="POSIX: these are ordinary names")
def test_reserved_windows_device_names_are_refused(value):
    """On Windows these resolve to a device (a serial port, the null device) no
    matter which directory they appear in. On POSIX they are ordinary filenames,
    so the check is deliberately platform-conditional: refusing them there would
    break legitimate files."""
    with pytest.raises(ValueError):
        validate_model_resource(value, context="sweep")


@pytest.mark.parametrize("value", ["CONTEXT.mco", "console.ser.gz", "nulls.mco"])
def test_names_merely_starting_like_a_device_are_allowed(value):
    """Over-block control: the check is on the whole stem, not a prefix."""
    validate_model_resource(value, context="sweep")


@pytest.mark.parametrize("value", ["C:evil.mco", "C:models\\evil.mco", "D:x.ser.gz"])
@pytest.mark.skipif(os.name == "posix", reason="POSIX: ':' is an ordinary char")
def test_drive_relative_paths_are_refused(value):
    """Windows CI found this: "C:name" is drive-RELATIVE, meaning "name in the
    current directory of drive C", so it escapes the location that was validated.
    It is not the same as the absolute "C:\\name"."""
    with pytest.raises(ValueError):
        validate_model_resource(value, context="sweep")
    with pytest.raises(PermissionError):
        validate_tool_path(value, context="sweep")


def test_both_guards_share_one_syntax_gate(pathsec_sandbox):
    """Windows CI found that validate_tool_path skipped the name checks that
    validate_model_resource applied, so a value refused by one was accepted by
    the other. They must stay in agreement on syntax."""
    root, outside = pathsec_sandbox
    disagreements = []
    for name, value in _hostile_vectors(root, outside) + _exotic_vectors(root):
        verdicts = []
        for guard in (validate_model_resource, validate_tool_path):
            try:
                guard(value, context="sweep")
                verdicts.append("allowed")
            except (PermissionError, ValueError, OSError):
                verdicts.append("refused")
        # validate_tool_path is strictly stricter: it may refuse where the model
        # guard allows a bare resource name, but never the reverse.
        if verdicts[0] == "refused" and verdicts[1] == "allowed":
            disagreements.append(name)
    assert disagreements == [], f"tool_path weaker than model_resource: {disagreements}"


# ---------------------------------------------------------------------------
# Time-of-check/time-of-use at the API boundary. __fspath__ is allowed to
# return a different answer on every call, so a guard that resolves the path
# separately from the code that uses it validates one file while the tool opens
# another. Both parsers leaked this way until the guards started returning the
# resolved string for the caller to use.
# ---------------------------------------------------------------------------


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


def test_mutating_path_that_starts_hostile_is_refused(pathsec_sandbox):
    """The other ordering: hostile on the guard's call. Must still be refused."""
    root, outside = pathsec_sandbox
    evil = outside / "evil.mco"
    evil.write_text("x")
    good = root / "ok.mco"
    good.write_text("m")
    with pytest.raises((PermissionError, ValueError)):
        validate_model_resource(_MutatingPath(str(evil), str(good)), context="sweep")


def test_guards_return_the_resolved_string(pathsec_sandbox):
    """The contract callers rely on: use the return value, never the original."""
    root, _outside = pathsec_sandbox
    model = root / "m.mco"
    model.write_text("m")
    assert validate_model_resource(model, context="sweep") == str(model)
    assert validate_tool_path(model, context="sweep") == str(model)
    assert validate_model_resource(_DEFAULT_RESOURCE, context="sweep") == (
        _DEFAULT_RESOURCE
    )


@pytest.mark.parametrize("value", [None, ["/etc/passwd"], object()])
def test_non_path_inputs_are_a_clean_security_rejection(value):
    """A TypeError would escape a caller's except (ValueError, PermissionError)
    and surface as a crash rather than a refusal.

    bytes are NOT here: a bytes path is a legal spelling on POSIX, so it is
    decoded and checked rather than refused.

    Integers are deliberately absent: throughout pathsec an int is a file
    descriptor, not a path, and validate_path short-circuits on one. Treating it
    as a bad path here would contradict that convention.

    The exception type follows each guard's own convention: a malformed value is
    a ValueError from validate_model_resource, and a PermissionError from the
    tool-path guards, which report every refusal that way.
    """
    with pytest.raises(ValueError):
        validate_model_resource(value, context="sweep")
    with pytest.raises(PermissionError):
        validate_tool_path(value, context="sweep")


@pytest.mark.parametrize(
    "name", ["evil.mco.", "evil.mco ", "evil.mco...", "evil.mco. "]
)
def test_trailing_dot_or_space_is_refused(name):
    """Windows silently strips these, so the name that is checked is not the name
    that is opened."""
    with pytest.raises(ValueError):
        validate_model_resource(name, context="sweep")


class _DotPathObject:
    """validate_path reads a ``.path`` attribute in preference to __fspath__
    (it supports NLTK's PathPointer objects). An object whose ``.path`` is
    benign and whose __fspath__ is hostile therefore passes the check and is
    resolved to the hostile value by whoever consumes it."""

    def __init__(self, benign, hostile):
        self.path = benign
        self._hostile = hostile

    def __fspath__(self):
        return self._hostile

    def __str__(self):
        return self.path


@pytest.mark.parametrize("slot", ["model", "input"])
def test_segmenter_refuses_dot_path_objects(pathsec_sandbox, monkeypatch, slot):
    """Both the model and the input file leaked this way: the guard read .path
    and the JVM would have resolved __fspath__."""
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    _trap_java(monkeypatch, seg, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("x")
    good = str(root / "ok.ser.gz")
    with pathsec.open(good, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")

    if slot == "model":
        tool = _segmenter(monkeypatch, str(root), model=_DotPathObject(good, str(evil)))
        target = inside
    else:
        tool = _segmenter(monkeypatch, str(root), model=good)
        target = _DotPathObject(inside, "/etc/passwd")
    with pytest.raises((PermissionError, ValueError)):
        tool.segment_file(target)


def test_segmenter_argv_carries_validated_strings(pathsec_sandbox, monkeypatch):
    """Over-block control plus the positive invariant: what reaches the JVM is
    the exact string the guard returned, as a str."""
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, seg, {})
    model = str(root / "ok.ser.gz")
    with pathsec.open(model, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")

    tool = _segmenter(monkeypatch, str(root), model=model)
    with pytest.raises(_ReachedJVM):
        tool.segment_file(inside)
    for flag in ("-loadClassifier", "-textFile"):
        value = sink["cmd"][sink["cmd"].index(flag) + 1]
        assert isinstance(value, str)
        assert os.path.realpath(value).startswith(os.path.realpath(str(root)))


def test_dot_path_object_is_refused_by_both_guards(pathsec_sandbox):
    root, outside = pathsec_sandbox
    evil = outside / "evil.mco"
    evil.write_text("x")
    good = root / "ok.mco"
    good.write_text("m")
    sneaky = _DotPathObject(str(good), str(evil))
    for guard in (validate_model_resource, validate_tool_path):
        with pytest.raises((PermissionError, ValueError)):
            guard(sneaky, context="sweep")


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


class _LyingFsPath:
    def __fspath__(self):
        return _LyingStr("-Xmx99g")


@pytest.mark.parametrize(
    "payload",
    ["-Xmx99g", "../../../etc/passwd", "file:///etc/passwd", "model\x00.mco"]
    + ([] if os.name == "posix" else ["NUL", "evil.mco.", "name:stream"]),
)
def test_lying_str_subclass_is_refused(payload):
    """Every check must see the real characters, not what the subclass claims."""
    for guard in (validate_model_resource, validate_tool_path):
        with pytest.raises((PermissionError, ValueError)):
            guard(_LyingStr(payload), context="sweep")


def test_lying_subclass_returned_by_fspath_is_refused():
    for guard in (validate_model_resource, validate_tool_path):
        with pytest.raises((PermissionError, ValueError)):
            guard(_LyingFsPath(), context="sweep")


def test_guards_always_return_an_exact_str(pathsec_sandbox):
    """The value callers put into argv must be a plain str, so that nothing can
    re-resolve or re-inspect it differently later."""
    root, _outside = pathsec_sandbox
    model = root / "ok.mco"
    model.write_text("m")

    class _BenignSubclass(str):
        pass

    for value in (str(model), _BenignSubclass(str(model)), model, _DEFAULT_RESOURCE):
        assert type(validate_model_resource(value, context="sweep")) is str
    assert type(validate_tool_path(model, context="sweep")) is str


def test_benign_str_subclass_still_works(pathsec_sandbox):
    """Over-block control: subclassing str is legal, lying about it is not."""
    root, _outside = pathsec_sandbox
    model = root / "ok.mco"
    model.write_text("m")

    class _BenignSubclass(str):
        pass

    assert validate_model_resource(_BenignSubclass(str(model)), context="sweep") == str(
        model
    )


# ---------------------------------------------------------------------------
# corenlp_options is SPLIT into separate argv elements, so it can append a
# second -model. Verified directly against the JVM that Stanford's
# LexicalizedParser honours the LAST occurrence, so an injected option replaced
# the model the guard had just checked and the parser deserialized that file.
# ---------------------------------------------------------------------------


def _stanford_with_options(model_path, options):
    parser = _stanford_parser(model_path)
    parser.corenlp_options = options
    return parser


@pytest.mark.parametrize(
    "name",
    [".\n./TARGET", ".\t./TARGET", ".\r./TARGET", ".\x0b./TARGET", "model\x0c.mco"],
    ids=["lf", "tab", "cr", "vtab", "formfeed"],
)
def test_control_characters_are_refused(name):
    """Python 3.14's url2pathname follows the WHATWG rules and STRIPS tab, LF and
    CR, so a name containing them passes a '..' check here and then BECOMES a
    traversal downstream. Verified against a real 3.14.4 interpreter:

        url2pathname('.\\n./TARGET') -> '../TARGET'

    A legitimate model or corpus filename never contains a control character, so
    they are refused outright rather than normalised.
    """
    for guard in (validate_model_resource, validate_tool_path):
        with pytest.raises((PermissionError, ValueError)):
            guard(name, context="sweep")


def test_control_character_guard_does_not_block_ordinary_names(pathsec_sandbox):
    """Over-block control: spaces are legal in a filename, control characters
    are not."""
    root, _outside = pathsec_sandbox
    spaced = root / "my model.ser.gz"
    spaced.write_text("m")
    validate_model_resource(str(spaced), context="sweep")
    validate_model_resource(_DEFAULT_RESOURCE, context="sweep")


# ---------------------------------------------------------------------------
# StanfordSegmenter's options dict is joined into ONE comma-separated -options
# argv element, so a key containing ',' or '=' injects extra option pairs. Same
# class as the parser's corenlp_options, in the sibling wrapper.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "key",
    ["normalize=true,serDictionary", "a,b", "a=b", "a b", "a\nb", "a\tb", "", "   "],
    ids=[
        "comma-and-equals",
        "comma",
        "equals",
        "space",
        "newline",
        "tab",
        "empty",
        "whitespace",
    ],
)
def test_segmenter_option_keys_cannot_inject_pairs(key):
    from nltk.tokenize.stanford_segmenter import _validated_options

    with pytest.raises(ValueError):
        _validated_options({key: "1"})


def test_segmenter_option_values_are_bounded(pathsec_sandbox):
    """A value that names a file must stay inside the data roots."""
    from nltk.tokenize.stanford_segmenter import _validated_options

    root, outside = pathsec_sandbox
    evil = outside / "evil.gz"
    evil.write_text("x")
    for value in ("/etc/passwd", str(evil)):
        with pytest.raises((PermissionError, ValueError)):
            _validated_options({"serDictionary": value})


def test_segmenter_benign_options_still_work(pathsec_sandbox):
    """Over-block control: ordinary settings, numbers and in-root paths pass."""
    from nltk.tokenize.stanford_segmenter import _validated_options

    root, _outside = pathsec_sandbox
    good = root / "ok.gz"
    good.write_text("m")
    assert _validated_options({"normalize": "true", "keepAll": "false"}) == {
        "normalize": "true",
        "keepAll": "false",
    }
    assert _validated_options({"maxLen": 40}) == {"maxLen": 40}
    assert _validated_options({"serDictionary": str(good)}) == {
        "serDictionary": str(good)
    }
    assert _validated_options({}) == {}


def test_teeth_segmenter_options_guard_is_load_bearing():
    """Without the guard the injected pair lands in the built option string."""
    import json as _json

    options = {"normalize=true,serDictionary": "/etc/passwd"}
    unguarded = ",".join(f"{k}={_json.dumps(v)}" for k, v in options.items())
    assert "serDictionary" in unguarded.split(",")[1]


def test_segmenter_out_of_root_jar_is_refused_despite_approved_checksum(
    pathsec_sandbox, monkeypatch
):
    """The checksum allowlist is not a location check. A jar outside the roots
    must still be refused, even when its sha256 has been approved."""
    import hashlib as _hashlib

    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    evil_jar = outside / "evil.jar"
    evil_jar.write_bytes(b"PK\x05\x06" + b"\0" * 18)
    digest = _hashlib.sha256(evil_jar.read_bytes()).hexdigest()
    monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)

    tool = object.__new__(seg.StanfordSegmenter)
    tool._stanford_jar = str(evil_jar)
    tool._jar_sha256_cache = {}
    with pytest.raises((PermissionError, ValueError)):
        tool._validate_classpath()


# ---------------------------------------------------------------------------
# Surfaces probed and found CLEAN. Pinned so a later change cannot open them
# without a test noticing. Each was verified by execution, not by reading.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "java_class",
    ["-jar", "-Xmx99g", "-javaagent:/tmp/evil.jar", "@/tmp/argfile"],
)
def test_segmenter_java_class_cannot_be_an_option(
    pathsec_sandbox, monkeypatch, java_class
):
    """java_class is caller-supplied and lands in the JVM's MAIN CLASS slot, so
    an option-shaped value would be read as a JVM option instead. internals.java
    already refuses it; this pins that it keeps doing so."""
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")
    tool = _segmenter(monkeypatch, str(root))
    tool._java_class = java_class
    with pytest.raises((ValueError, PermissionError)):
        tool.segment_file(inside)


@pytest.mark.parametrize(
    "option",
    [
        "-XX:OnOutOfMemoryError=touch /tmp/pwned",
        "-javaagent:/tmp/evil.jar",
        "@/tmp/argfile",
        "-jar /tmp/evil.jar",
    ],
)
def test_wrapper_java_options_hit_the_allowlist(pathsec_sandbox, monkeypatch, option):
    """The JVM option allowlist lives in internals.java. This confirms it is
    actually reached through THIS wrapper rather than assumed."""
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")
    tool = _segmenter(monkeypatch, str(root))
    tool.java_options = option
    with pytest.raises((ValueError, PermissionError)):
        tool.segment_file(inside)


@pytest.mark.skipif(
    os.name != "posix",
    reason="POSIX-shaped traversal and resolve() fallback; hardening, not a fixed vuln",
)
def test_unresolvable_path_with_traversal_or_nul_is_refused(pathsec_sandbox):
    """validate_path falls back to validating only the prefix up to ".zip" when
    resolve() fails, and resolve() also fails on a NUL. Refusing an unresolvable
    path that still contains a traversal or a NUL keeps that fallback from
    approving a value on a harmless prefix.

    No usable escape was found through this (a NUL path cannot be opened by
    Python and truncates in a subprocess), so this is hardening rather than a
    fixed vulnerability.
    """
    import zipfile as _zipfile

    root, _outside = pathsec_sandbox
    archive = str(root / "corpus.zip")
    with _zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("member.txt", "hello")
    for suspect in (
        f"{archive}/\x00../../../etc/passwd",
        f"{archive}/../../../../etc/passwd",
    ):
        with pytest.raises((PermissionError, ValueError)):
            pathsec.validate_path(suspect, context="sweep")


def test_zip_member_paths_still_validate(pathsec_sandbox):
    """Over-block control for the change above: virtual zip member paths are the
    reason that fallback exists and must keep working."""
    import zipfile as _zipfile

    from nltk.data import ZipFilePathPointer

    root, _outside = pathsec_sandbox
    archive = str(root / "corpus.zip")
    with _zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("member.txt", "hello")
    for good in (archive, f"{archive}/member.txt", f"{archive}/sub/dir/member.txt"):
        pathsec.validate_path(good, context="sweep")
    assert ZipFilePathPointer(archive, "member.txt").open().read() == b"hello"


# ---------------------------------------------------------------------------
# Entry-point matrix. The recurring real bug in this PR was a guard placed on
# ONE method while a sibling built its argv before validating. segment_file was
# fixed first and segment_sents/segment still leaked. This drives the attack
# through EVERY public entry point so a new method cannot reopen it quietly.
# ---------------------------------------------------------------------------


def _segmenter_entry_points():
    return {
        "segment_file": lambda tool, path: tool.segment_file(path),
        "segment_sents": lambda tool, _path: tool.segment_sents([["中", "文"]]),
        "segment": lambda tool, _path: tool.segment(["中", "文"]),
    }


@pytest.mark.parametrize("entry", sorted(_segmenter_entry_points()))
@pytest.mark.parametrize("hostile", ["mutating", "dot-path", "plain-outside"])
def test_every_segmenter_entry_point_refuses_hostile_models(
    pathsec_sandbox, monkeypatch, entry, hostile
):
    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, seg, {})
    evil = str(outside / "evil.ser.gz")
    (outside / "evil.ser.gz").write_text("x")
    good = str(root / "ok.ser.gz")
    with pathsec.open(good, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")

    model = {
        "mutating": _MutatingPath(good, evil),
        "dot-path": _DotPathObject(good, evil),
        "plain-outside": evil,
    }[hostile]
    tool = _segmenter(monkeypatch, str(root), model=model)

    try:
        _segmenter_entry_points()[entry](tool, inside)
    except (PermissionError, ValueError):
        return
    except _ReachedJVM:
        pass
    # If it reached the JVM at all, the argv must hold the validated string.
    handed = sink["cmd"][sink["cmd"].index("-loadClassifier") + 1]
    resolved = _resolve(handed)
    assert isinstance(handed, str), f"{entry} put a {type(handed).__name__} in argv"
    assert os.path.realpath(str(resolved)).startswith(
        os.path.realpath(str(root))
    ), f"{entry} handed the JVM a path outside the roots: {resolved}"


@pytest.mark.parametrize("entry", sorted(_segmenter_entry_points()))
def test_every_segmenter_entry_point_still_works(pathsec_sandbox, monkeypatch, entry):
    """Over-block control for the matrix above."""
    import nltk.tokenize.stanford_segmenter as seg

    root, _outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, seg, {})
    good = str(root / "ok.ser.gz")
    with pathsec.open(good, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")

    tool = _segmenter(monkeypatch, str(root), model=good)
    with pytest.raises(_ReachedJVM):
        _segmenter_entry_points()[entry](tool, inside)
    assert sink["cmd"][sink["cmd"].index("-loadClassifier") + 1] == good


@pytest.mark.parametrize(
    "entry",
    [
        "parse_sents",
        "raw_parse_sents",
        "tagged_parse_sents",
        "raw_parse",
        "tagged_parse",
    ],
)
def test_every_parser_entry_point_refuses_a_mutating_model(
    pathsec_sandbox, monkeypatch, entry
):
    """All five public parser methods funnel through _execute, which replaces the
    -model argv entry with the validated string. This proves it for each."""
    import nltk.parse.stanford as st

    root, outside = pathsec_sandbox
    sink = _trap_java(monkeypatch, st, {})
    evil = outside / "evil.ser.gz"
    evil.write_text("x")
    good = root / "ok.ser.gz"
    good.write_text("m")

    parser = _stanford_parser(_MutatingPath(str(good), str(evil)))
    calls = {
        "parse_sents": lambda p: p.parse_sents([["hi", "there"]]),
        "raw_parse_sents": lambda p: p.raw_parse_sents(["hi there"]),
        "tagged_parse_sents": lambda p: p.tagged_parse_sents([[("hi", "UH")]]),
        "raw_parse": lambda p: p.raw_parse("hi there"),
        "tagged_parse": lambda p: p.tagged_parse([("hi", "UH")]),
    }
    try:
        calls[entry](parser)
    except (PermissionError, ValueError):
        return
    except _ReachedJVM:
        pass
    handed = sink["cmd"][sink["cmd"].index("-model") + 1]
    assert isinstance(handed, str), f"{entry} put a {type(handed).__name__} in argv"
    assert os.path.realpath(_resolve(handed)).startswith(os.path.realpath(str(root)))


def test_validate_model_paths_returns_the_validated_strings(
    pathsec_sandbox, monkeypatch
):
    """The contract the segmenter's argv builders rely on: the guard hands back
    what it checked, so nothing has to re-read shared mutable state."""
    root, _outside = pathsec_sandbox
    model = str(root / "m.ser.gz")
    dictionary = str(root / "d.ser.gz")
    sihan = str(root / "sihan")
    for path in (model, dictionary):
        with pathsec.open(path, "w", encoding="utf-8") as handle:
            handle.write("x")
    os.mkdir(sihan)

    tool = _segmenter(monkeypatch, str(root), model=model)
    tool._dict = dictionary
    tool._sihan_corpora_dict = sihan
    assert tool._validate_model_paths() == (model, dictionary, sihan)

    unset = _segmenter(monkeypatch, str(root))
    assert unset._validate_model_paths() == (None, None, None)


def test_segmenter_argv_survives_a_concurrent_model_swap(pathsec_sandbox, monkeypatch):
    """A background thread rewriting self._model must never land an out-of-root
    path in the argv. The builders take the guard's return value rather than
    re-reading the attribute, so the checked value and the used value are the
    same object.

    No leak was observed here before the change either, so this documents the
    property rather than reproducing a past failure.
    """
    import threading

    import nltk.tokenize.stanford_segmenter as seg

    root, outside = pathsec_sandbox
    evil = str(outside / "evil.ser.gz")
    (outside / "evil.ser.gz").write_text("x")
    good = str(root / "ok.ser.gz")
    with pathsec.open(good, "w", encoding="utf-8") as handle:
        handle.write("m")
    inside = str(root / "in.txt")
    with pathsec.open(inside, "w", encoding="utf-8") as handle:
        handle.write("x")

    handed = []

    def fake_java(cmd, *args, **kwargs):
        handed.append(cmd[cmd.index("-loadClassifier") + 1])
        raise _ReachedJVM

    monkeypatch.setattr(seg, "java", fake_java)
    tool = _segmenter(monkeypatch, str(root), model=good)

    stop = threading.Event()

    def flipper():
        while not stop.is_set():
            tool._model = evil
            tool._model = good

    thread = threading.Thread(target=flipper, daemon=True)
    thread.start()
    try:
        for _ in range(200):
            for call in (
                lambda: tool.segment_file(inside),
                lambda: tool.segment_sents([["中", "文"]]),
            ):
                try:
                    call()
                except (_ReachedJVM, PermissionError, ValueError):
                    pass
    finally:
        stop.set()
        thread.join(timeout=5)

    escaped = [
        value
        for value in handed
        if not os.path.realpath(str(value)).startswith(os.path.realpath(str(root)))
    ]
    assert escaped == [], f"a concurrent write reached the JVM argv: {escaped[:3]}"


def test_file_descriptors_pass_through_both_guards():
    """An int is a file descriptor everywhere in pathsec, never a path."""
    assert validate_tool_path(0, context="sweep") == 0


def test_validate_tool_dir_returns_the_checked_string(pathsec_sandbox):
    """Directories go through validate_tool_dir, which must hand back the checked
    string for the same reason validate_tool_path does."""
    from nltk.pathsec import validate_tool_dir

    root, outside = pathsec_sandbox
    corpus = root / "sihan"
    corpus.mkdir()
    assert validate_tool_dir(str(corpus), context="sweep") == str(corpus)
    with pytest.raises((PermissionError, ValueError)):
        validate_tool_dir(str(outside / "elsewhere"), context="sweep")

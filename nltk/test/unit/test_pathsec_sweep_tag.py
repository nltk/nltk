# Natural Language Toolkit: pathsec sweep tests (nltk.tag sinks)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Attack tests for the caller-controlled model-path sinks hardened under
GHSA-8mgp-746c-j5xp in :mod:`nltk.tag`.

The taggers here hand a model path to a native extension or an external
process that ``pathsec.open`` cannot wrap:

* ``CRFTagger.set_model_file`` / ``CRFTagger.train`` -> pycrfsuite C-extension
  (``Tagger.open`` / ``Trainer.train``).
* ``StanfordTagger.tag_sents`` -> a Java subprocess (``-model`` /
  ``-loadClassifier``).
* ``HunposTagger.__init__`` -> the ``hunpos-tag`` subprocess argv.

Each patched API now calls ``pathsec.validate_path`` immediately before the
hand-off, so a model path *outside* the NLTK data sandbox is refused. The
outside target is a fresh directory under the real home directory; never a
temp dir, because the system temp dir can itself be an allowed root (and on
Linux ``tempfile.mkdtemp()`` lives under the shared ``/tmp``).
"""

import builtins
import importlib
import inspect
import io
import os
import pkgutil
import random
import re
import shutil
import socket
import string
import tempfile
import time
from pathlib import Path

import pytest

import nltk.data
import nltk.pathsec as pathsec

# The pathsec sandbox fixtures (sandbox / restricted_sandbox / enforce_off)
# are provided by nltk/test/unit/conftest.py.


def test_negative_control_pathsec_open_refuses_outside(sandbox):
    """Baseline: pathsec.open() itself refuses a write outside the sandbox."""
    target = sandbox / "pwned.txt"
    with pytest.raises(PermissionError):
        pathsec.open(str(target), "w")
    assert not target.exists()


def test_crf_set_model_file_refuses_outside_path(sandbox):
    """CRFTagger.set_model_file() must refuse an outside model path before the
    pycrfsuite native loader touches it.

    Reached without pycrfsuite installed: ``validate_path`` runs before
    ``self._tagger.open``, so ``object.__new__`` (no ``__init__``, which needs
    pycrfsuite) suffices to drive the sink.
    """
    from nltk.tag.crf import CRFTagger

    target = sandbox / "model.crf.tagger"
    ct = object.__new__(CRFTagger)
    with pytest.raises(PermissionError):
        ct.set_model_file(str(target))


def test_crf_train_refuses_outside_path(sandbox):
    """CRFTagger.train() must refuse an outside destination before the pycrfsuite
    Trainer writes the model."""
    pytest.importorskip("pycrfsuite")
    from nltk.tag.crf import CRFTagger

    target = sandbox / "trained.crf.tagger"
    ct = CRFTagger()
    with pytest.raises(PermissionError):
        ct.train([[("dog", "Noun"), ("runs", "Verb")]], str(target))
    assert not target.exists()


def test_stanford_tag_sents_refuses_outside_model(sandbox):
    """StanfordTagger.tag_sents() must refuse an outside model path before the
    JVM subprocess is spawned.

    Driven via ``object.__new__`` so no Stanford jar / JVM is required:
    ``validate_path`` raises before the ``java()`` hand-off.
    """
    from nltk.tag.stanford import StanfordPOSTagger

    target = sandbox / "english-bidirectional-distsim.tagger"
    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = str(target)
    tagger._stanford_jar = "unused.jar"
    tagger._encoding = "utf8"
    tagger.java_options = "-mx1000m"

    with pytest.raises(PermissionError):
        tagger.tag_sents([["What", "is", "the", "airspeed"]])


def test_hunpos_init_refuses_outside_model(sandbox):
    """HunposTagger.__init__() must refuse an outside model path before the
    hunpos-tag subprocess is spawned.

    ``find_file`` returns the outside model only if it exists on disk, so the
    model file is created under ``~``; a dummy binary satisfies ``find_binary``
    without being executed (validation raises before ``Popen``).
    """
    from nltk.tag.hunpos import HunposTagger

    dummy_bin = sandbox / "hunpos-tag"
    dummy_bin.write_text("#!/bin/sh\n")
    model = sandbox / "en_wsj.model"
    model.write_text("stub")

    with pytest.raises(PermissionError):
        HunposTagger(str(model), path_to_bin=str(dummy_bin))


def test_tagger_sources_route_through_pathsec():
    """Grep-style guard: the patched sinks must reference the pathsec sentinel,
    so a future refactor that drops the check is caught here."""
    from nltk.chunk import named_entity
    from nltk.tag import crf, hunpos, perceptron, stanford

    crf_set_src = inspect.getsource(crf.CRFTagger.set_model_file)
    assert (
        'validate_tool_path(model_file, context="CRFTagger.set_model_file")'
        in crf_set_src
    )

    crf_train_src = inspect.getsource(crf.CRFTagger.train)
    assert 'validate_tool_path(model_file, context="CRFTagger.train"' in crf_train_src

    stanford_src = inspect.getsource(stanford.StanfordTagger.tag_sents)
    assert "validate_tool_path(" in stanford_src
    assert "self._stanford_model" in stanford_src

    stanford_init_src = inspect.getsource(stanford.StanfordTagger.__init__)
    assert "validate_tool_path(self._stanford_model" in stanford_init_src

    hunpos_src = inspect.getsource(hunpos.HunposTagger.__init__)
    assert "validate_tool_path(self._hunpos_model" in hunpos_src

    save_src = inspect.getsource(perceptron.PerceptronTagger.save_to_json)
    assert "validate_tool_dir(loc" in save_src
    assert "_validate_name_component(lang" in save_src

    ne_src = inspect.getsource(named_entity.Maxent_NE_Chunker.save_params)
    assert "validate_tool_dir(tab_dir" in ne_src


def test_perceptron_module_has_no_bare_open():
    """The only ``open(`` in perceptron.py is the fd-pinned model write.

    That one deliberately bypasses ``pathsec.open``: it writes a name relative to
    an already-verified O_NOFOLLOW directory descriptor, which is strictly
    stronger than re-validating a string. Every other file access must go
    through the sentinel.
    """
    import nltk.tag.perceptron as perceptron

    source = inspect.getsource(perceptron)
    bare = [
        line.strip()
        for line in source.splitlines()
        if re.search(r"(?<![\w.])open\(", line)
        and "pathsec_open" not in line
        and "os.open" not in line
        and not line.strip().startswith("#")
    ]
    assert bare == [
        'with open(target, "w", opener=_no_follow_opener) as fout:'
    ], f"unexpected bare open(): {bare}"


# --- the full escape matrix, fired at every guarded model-path sink -----------
_POSIX = os.name == "posix"

# Vectors every guarded sink must refuse. Platform-specific ones are skipped
# (not silently passed) where the filesystem cannot represent them.
_ESCAPES = [
    "plain-outside",
    "outside-nested",
    "etc-passwd",
    "traversal-dotdot",
    "traversal-many",
    "backslash-traversal-outside",
    "double-slash-outside",
    "trailing-slash-outside",
    "case-folded-etc",
    "cwd-relative",
    "dot-dot",
    "symlink-final",
    "symlink-to-etc",
    "symlink-chained",
    "symlink-intermediate-dir",
    "hardlink-to-outside",
    "fifo-in-root",
    "socket-in-root",
    "directory-in-root",
    "nul-trailing",
    "nul-middle-inside-root",
    "nul-only",
    "leading-dash",
    "leading-double-dash",
    "blank",
    "tab-only",
    "newline-only",
    "file-url",
    "file-url-query",
    "jar-url",
    "http-url",
    "https-url",
    "ftp-url",
    "tilde",
    "tilde-root",
    "unc-backslash",
    "unc-slash",
    "dev-stdin",
    "dev-fd-0",
    "dev-null",
    "dev-zero",
    "proc-self-environ",
    "bytes-outside",
    "pathlib-outside",
]

# Contained-but-odd paths. These are NOT attacks: they name a real file inside
# the sandbox. They are pinned so that a future change which starts expanding,
# splitting or decoding a path shows up here as a new leak.
_BENIGN = [
    "plain-in-root",
    "dot-segments",
    "dash-basename-absolute",
    "space-in-name",
    "unicode-name",
    "newline-in-name",
    "backslash-in-name",
    "colon-ads-in-name",
    "percent-encoded-name",
    "long-name",
    "dollar-var-name",
    "glob-chars-name",
]

_NEEDS_SYMLINK = {
    "symlink-final",
    "symlink-to-etc",
    "symlink-chained",
    "symlink-intermediate-dir",
}
_POSIX_ONLY = _NEEDS_SYMLINK | {
    "hardlink-to-outside",
    "fifo-in-root",
    "socket-in-root",
    "newline-in-name",
    "backslash-in-name",
    "colon-ads-in-name",
    "backslash-traversal-outside",
    "dev-stdin",
    "dev-fd-0",
    "dev-null",
    "dev-zero",
    "proc-self-environ",
    "glob-chars-name",
}


def _vector(name, root, outside, registry):
    """Materialise vector *name* inside the sandbox and return its path value.

    *registry* is a per-test list the caller closes over so sockets/FIFOs are
    cleaned up. Calls ``pytest.skip`` when the platform cannot represent the
    vector, so a platform gap is visible rather than a silent pass.
    """
    if name in _POSIX_ONLY and not _POSIX:
        pytest.skip(f"{name} is a POSIX-only filesystem shape")

    secret = outside / "secret"
    if not secret.exists():
        secret.write_text("SECRET", encoding="utf-8")

    def _reg(path, kind):
        registry.append((str(path), kind))
        return str(path)

    if name == "plain-outside":
        return str(outside / "m.model")
    if name == "outside-nested":
        return str(outside / "deep" / "er" / "m.model")
    if name == "etc-passwd":
        return "/etc/passwd"
    if name == "traversal-dotdot":
        return os.path.join(str(root), "..", "..", "..", "etc", "passwd")
    if name == "traversal-many":
        return str(root) + "/" + "../" * 40 + "etc/passwd"
    if name == "backslash-traversal-outside":
        return str(outside) + "\\..\\..\\etc\\passwd"
    if name == "double-slash-outside":
        return "/" + str(outside / "m.model")
    if name == "trailing-slash-outside":
        return str(outside) + os.sep
    if name == "case-folded-etc":
        return "/ETC/PASSWD"
    if name == "cwd-relative":
        return "sneaky.model"
    if name == "dot-dot":
        return ".."
    if name == "symlink-final":
        link = root / "link.model"
        if not link.is_symlink():
            os.symlink(str(secret), str(link))
        return str(link)
    if name == "symlink-to-etc":
        link = root / "etclink.model"
        if not link.is_symlink():
            os.symlink("/etc/passwd", str(link))
        return str(link)
    if name == "symlink-chained":
        first = root / "link.model"
        if not first.is_symlink():
            os.symlink(str(secret), str(first))
        chain = root / "chain.model"
        if not chain.is_symlink():
            os.symlink(str(first), str(chain))
        return str(chain)
    if name == "symlink-intermediate-dir":
        linkdir = root / "linkdir"
        if not linkdir.is_symlink():
            os.symlink(str(outside), str(linkdir))
        return str(linkdir / "secret")
    if name == "hardlink-to-outside":
        hard = root / "hard.model"
        if not hard.exists():
            try:
                os.link(str(secret), str(hard))
            except OSError:
                pytest.skip("hardlinks unavailable here")
        return str(hard)
    if name == "fifo-in-root":
        fifo = root / "fifo.model"
        if not fifo.exists():
            os.mkfifo(str(fifo))
        return str(fifo)
    if name == "socket-in-root":
        sockpath = root / "sock.model"
        if not sockpath.exists():
            sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sk.bind(str(sockpath))
            registry.append(sk)
        return str(sockpath)
    if name == "directory-in-root":
        adir = root / "a_directory"
        adir.mkdir(exist_ok=True)
        return str(adir)
    if name == "nul-trailing":
        return "/etc/passwd\x00.model"
    if name == "nul-middle-inside-root":
        return str(root) + "/x\x00/../../../../etc/passwd"
    if name == "nul-only":
        return "\x00"
    if name == "leading-dash":
        return "-mx4g"
    if name == "leading-double-dash":
        return "--loadClassifier=etc-passwd"
    if name == "blank":
        return "   "
    if name == "tab-only":
        return "\t"
    if name == "newline-only":
        return "\n"
    if name == "file-url":
        return "file:///etc/passwd"
    if name == "file-url-query":
        return "file:///etc/passwd?x=1"
    if name == "jar-url":
        return "jar:file:///etc/evil.jar!/x"
    if name == "http-url":
        return "http://evil.example/m.model"
    if name == "https-url":
        return "https://evil.example/m.model"
    if name == "ftp-url":
        return "ftp://evil.example/m.model"
    if name == "tilde":
        return "~/.ssh/id_rsa"
    if name == "tilde-root":
        return "~"
    if name == "unc-backslash":
        return "\\\\evil\\share\\m.model"
    if name == "unc-slash":
        return "//evil/share/m.model"
    if name == "dev-stdin":
        return "/dev/stdin"
    if name == "dev-fd-0":
        return "/dev/fd/0"
    if name == "dev-null":
        return "/dev/null"
    if name == "dev-zero":
        return "/dev/zero"
    if name == "proc-self-environ":
        return "/proc/self/environ"
    if name == "bytes-outside":
        return str(outside / "m.model").encode()
    if name == "pathlib-outside":
        return Path(str(outside / "m.model"))

    # --- benign, contained vectors: a real file inside the allowed root ------
    benign_names = {
        "plain-in-root": "legit.model",
        "dash-basename-absolute": "-loadClassifier",
        "space-in-name": "my model.json",
        "unicode-name": "modelé_模型.json",
        "newline-in-name": "a\nb.model",
        "backslash-in-name": "a\\b.model",
        "colon-ads-in-name": "legit.model:evil",
        "percent-encoded-name": "%2e%2e%2fpasswd",
        "long-name": "L" * 180 + ".model",
        "dollar-var-name": "$HOME.model",
        "glob-chars-name": "m[0-9]*?.model",
    }
    if name == "dot-segments":
        leaf = root / "legit.model"
        leaf.write_text("{}", encoding="utf-8")
        return str(root) + "/./" + "./legit.model"
    if name in benign_names:
        leaf = root / benign_names[name]
        leaf.write_text("{}", encoding="utf-8")
        return _reg(leaf, "file")

    raise AssertionError(f"unknown vector {name!r}")


def _cleanup(registry):
    for item in registry:
        if isinstance(item, socket.socket):
            item.close()


# --- drivers: one per public entry point that reaches a model-path sink ------
def _drive_crf_set(path):
    from nltk.tag.crf import CRFTagger

    object.__new__(CRFTagger).set_model_file(path)


def _drive_crf_train(path):
    pytest.importorskip("pycrfsuite")
    from nltk.tag.crf import CRFTagger

    CRFTagger().train([[("dog", "N"), ("runs", "V")]], path)


def _stanford_tagger(path):
    from nltk.tag.stanford import StanfordPOSTagger

    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = path
    tagger._stanford_jar = "unused.jar"
    tagger._encoding = "utf8"
    tagger.java_options = "-mx1000m"
    return tagger


def _no_jvm(fn):
    """Run *fn* with nltk.tag.stanford.java replaced by a sentinel raiser.

    The guard runs strictly before the hand-off, so this never weakens an attack
    test; it makes the *benign* case assert what the JVM would have been handed
    without paying for a real JVM start.
    """
    import nltk.tag.stanford as stanford_module

    saved = stanford_module.java

    def _boom(cmd, *args, **kwargs):
        raise _ReachedSink(list(cmd))

    stanford_module.java = _boom
    try:
        return fn()
    finally:
        stanford_module.java = saved


def _drive_stanford_tag_sents(path):
    tagger = _stanford_tagger(path)
    _no_jvm(lambda: tagger.tag_sents([["What", "is", "the", "airspeed"]]))


def _drive_stanford_tag(path):
    tagger = _stanford_tagger(path)
    _no_jvm(lambda: tagger.tag(["What", "is"]))


def _drive_hunpos_init(path):
    """Drive HunposTagger.__init__ with find_file/find_binary stubbed out.

    The real ``find_file`` refuses anything that does not already exist, which
    would mask the guard for most vectors; stubbing it means the guard is the
    only thing standing between the caller's string and the subprocess argv.
    ``Popen`` is replaced so nothing is ever spawned.
    """
    import nltk.tag.hunpos as hunpos_module

    def _boom(cmd, *args, **kwargs):
        raise _ReachedSink(list(cmd))

    saved = (hunpos_module.find_file, hunpos_module.find_binary, hunpos_module.Popen)
    hunpos_module.find_file = lambda p, **kw: p
    hunpos_module.find_binary = lambda *a, **kw: "hunpos-tag"
    hunpos_module.Popen = _boom
    try:
        hunpos_module.HunposTagger(path)
    finally:
        (
            hunpos_module.find_file,
            hunpos_module.find_binary,
            hunpos_module.Popen,
        ) = saved


class _ReachedSink(Exception):
    """Raised in place of the real sink so a test can see what it was handed."""


def _drive_perceptron_save(path):
    from nltk.tag.perceptron import AveragedPerceptron

    AveragedPerceptron().save(path)


def _drive_perceptron_load(path):
    from nltk.tag.perceptron import AveragedPerceptron

    AveragedPerceptron().load(path)


def _drive_save_to_json(path):
    from nltk.tag.perceptron import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {"the": "DT"}
    tagger.classes = {"NN", "DT"}
    tagger.save_to_json(lang="eng", loc=path)


def _drive_train_save_loc(path):
    from nltk.tag.perceptron import PerceptronTagger

    PerceptronTagger(load=False).train(
        [[("today", "NN"), ("is", "VBZ")]], save_loc=path, nr_iter=1
    )


def _drive_load_from_json(path):
    from nltk.tag.perceptron import PerceptronTagger

    PerceptronTagger(load=False).load_from_json("eng", path)


def _drive_perceptron_init(path):
    from nltk.tag.perceptron import PerceptronTagger

    PerceptronTagger(load=True, lang="eng", loc=path)


def _drive_ne_save_params(path):
    from nltk.chunk.named_entity import Maxent_NE_Chunker

    chunker = object.__new__(Maxent_NE_Chunker)
    chunker._save_dir = None
    Maxent_NE_Chunker.save_params(chunker, path)


# Sinks that take a *file* path handed straight to a native loader or argv.
_FILE_SINKS = {
    "CRFTagger.set_model_file": _drive_crf_set,
    "CRFTagger.train": _drive_crf_train,
    "StanfordTagger.tag_sents": _drive_stanford_tag_sents,
    "StanfordTagger.tag": _drive_stanford_tag,
    "HunposTagger.__init__": _drive_hunpos_init,
    "AveragedPerceptron.save": _drive_perceptron_save,
    "AveragedPerceptron.load": _drive_perceptron_load,
}

# Sinks that take a *directory* to write model artifacts into.
_DIR_SINKS = {
    "PerceptronTagger.save_to_json": _drive_save_to_json,
    "PerceptronTagger.train(save_loc)": _drive_train_save_loc,
    "PerceptronTagger.load_from_json": _drive_load_from_json,
    "PerceptronTagger(load=True, loc=)": _drive_perceptron_init,
    "Maxent_NE_Chunker.save_params": _drive_ne_save_params,
}

_ALL_SINKS = dict(_FILE_SINKS, **_DIR_SINKS)


def _refusal(sink, path):
    """Run *sink* on *path*; return None if it refused, else the exception (or
    None-as-success) that proves it got past the guard."""
    try:
        _ALL_SINKS[sink](path)
    except (PermissionError, ValueError):
        return None
    except _ReachedSink as exc:
        return exc
    except Exception as exc:  # noqa: BLE001 - any other failure is "past the guard"
        return exc
    return "no-exception"


@pytest.mark.parametrize("sink", sorted(_FILE_SINKS))
@pytest.mark.parametrize("vector", _ESCAPES)
def test_file_sinks_refuse_every_escape_vector(pathsec_sandbox, sink, vector):
    """No model-*file* sink may accept any escape form."""
    root, outside = pathsec_sandbox
    registry = []
    try:
        path = _vector(vector, root, outside, registry)
        with pytest.raises((PermissionError, ValueError)):
            _FILE_SINKS[sink](path)
    finally:
        _cleanup(registry)


# A directory destination legitimately need not exist yet, so the file-shaped
# vectors (FIFO/socket/hardlink/regular-file checks) do not apply to it.
_DIR_ESCAPES = [
    v
    for v in _ESCAPES
    if v
    not in {
        "hardlink-to-outside",
        "fifo-in-root",
        "socket-in-root",
        "directory-in-root",
    }
]


@pytest.mark.parametrize("sink", sorted(_DIR_SINKS))
@pytest.mark.parametrize("vector", _DIR_ESCAPES)
def test_dir_sinks_refuse_every_escape_vector(pathsec_sandbox, sink, vector):
    """No model-*directory* sink may accept any escape form."""
    root, outside = pathsec_sandbox
    registry = []
    try:
        path = _vector(vector, root, outside, registry)
        with pytest.raises((PermissionError, ValueError, LookupError)):
            _DIR_SINKS[sink](path)
    finally:
        _cleanup(registry)


@pytest.mark.parametrize("sink", sorted(_FILE_SINKS))
@pytest.mark.parametrize("vector", _BENIGN)
def test_file_sinks_do_not_over_block_contained_paths(pathsec_sandbox, sink, vector):
    """A contained path, however odd its name, must not be refused.

    These are the false-positive controls: a guard that refuses everything would
    pass every attack test above and still be useless. Each sink is allowed to
    fail for its own unrelated reason (no native tagger, stub jar, bad json);
    what must NOT happen is a containment refusal.
    """
    root, outside = pathsec_sandbox
    registry = []
    try:
        path = _vector(vector, root, outside, registry)
        outcome = _refusal(sink, path)
        assert outcome is not None, f"{sink} unexpectedly refused {vector}"
    finally:
        _cleanup(registry)


def test_benign_vectors_are_not_expanded_or_decoded(pathsec_sandbox):
    """Nothing downstream may expand ``$HOME``/``~``, decode ``%2e%2e`` or glob.

    The path handed to the subprocess must be the exact string NLTK validated,
    byte for byte; any expansion would mean the validated path and the opened
    path can differ.
    """
    root, outside = pathsec_sandbox
    registry = []
    try:
        for vector in (
            "percent-encoded-name",
            "dollar-var-name",
            "glob-chars-name",
            "newline-in-name",
            "space-in-name",
            "unicode-name",
            "dash-basename-absolute",
        ):
            if vector in _POSIX_ONLY and not _POSIX:
                continue
            path = _vector(vector, root, outside, registry)
            try:
                _drive_hunpos_init(path)
            except _ReachedSink as exc:
                argv = exc.args[0]
                assert len(argv) == 2, f"{vector} split into {len(argv)} argv entries"
                assert argv[1] == path, f"{vector} was rewritten to {argv[1]!r}"
                assert not argv[1].startswith(
                    "-"
                ), f"{vector} reached argv as an option"
            else:  # pragma: no cover - the driver always reaches the sink
                pytest.fail(f"{vector} never reached the subprocess argv")
    finally:
        _cleanup(registry)


def test_absolute_path_with_dash_basename_is_not_an_option(pathsec_sandbox):
    """``<root>/-loadClassifier`` is a filename, not a switch: the argv element
    starts with the root's leading separator, so the callee cannot parse it as an
    option. It must therefore be permitted (over-blocking control) while a bare
    ``-loadClassifier`` is refused (the escape matrix covers that)."""
    root, outside = pathsec_sandbox
    registry = []
    try:
        path = _vector("dash-basename-absolute", root, outside, registry)
        assert not path.startswith("-")
        pathsec.validate_tool_path(path, context="probe")
    finally:
        _cleanup(registry)


def _assert_teeth(action, evidence, *, what):
    """Run *action* with a guard already neutered and report what happened.

    On POSIX ``save_to_json`` writes through a pinned directory descriptor, so
    removing the containment guard really lets the write land and *evidence*
    must show it. On Windows there is no directory descriptor: that branch
    writes through ``pathsec.open``, which independently refuses an outside
    path, so the correct assertion there is that the write is STILL blocked.
    Either way the probe is not inert; it just proves a different thing.
    """
    try:
        action()
        landed = True
    except (PermissionError, ValueError, OSError):
        landed = False
    if _POSIX:
        assert (
            landed and evidence()
        ), f"{what}: guard removed but nothing escaped; the probe is inert"
    else:
        assert (
            not landed and not evidence()
        ), f"{what}: pathsec.open should still refuse this on this platform"


# --- the guards must be load-bearing, not incidental --------------------------
# (test id, module, guard attribute, driver). The id is spelled out because a
# function repr carries its address, which differs per xdist worker.
_TEETH = [
    ("crf.set_model_file", "nltk.tag.crf", "validate_tool_path", _drive_crf_set),
    (
        "stanford.tag_sents",
        "nltk.tag.stanford",
        "validate_tool_path",
        _drive_stanford_tag_sents,
    ),
    ("hunpos.__init__", "nltk.tag.hunpos", "validate_tool_path", _drive_hunpos_init),
    (
        "perceptron.save_to_json",
        "nltk.tag.perceptron",
        "validate_tool_dir",
        _drive_save_to_json,
    ),
]


@pytest.mark.parametrize(
    "modname,attr,driver",
    [entry[1:] for entry in _TEETH],
    ids=[entry[0] for entry in _TEETH],
)
def test_each_guard_is_load_bearing(
    pathsec_sandbox, monkeypatch, modname, attr, driver
):
    """Negative control: with the guard neutered the outside path must become
    reachable again. A probe that still 'passes' with the guard removed is
    testing nothing."""
    import importlib

    root, outside = pathsec_sandbox
    target = str(outside / "m.model")

    with pytest.raises((PermissionError, ValueError)):
        driver(target)

    module = importlib.import_module(modname)
    monkeypatch.setattr(module, attr, lambda *a, **k: None)
    outcome = _refusal_for(driver, target)
    if not _POSIX and attr == "validate_tool_dir":
        # The Windows save branch writes through pathsec.open, which refuses an
        # outside path on its own, so the write stays blocked there.
        assert outcome == "refused"
        return
    assert (
        outcome != "refused"
    ), f"{modname}.{attr} removed but the exploit is still blocked; the test proves nothing"


def _refusal_for(driver, path):
    try:
        driver(path)
    except (PermissionError, ValueError):
        return "refused"
    except Exception:
        return "past-guard"
    return "landed"


def test_averaged_perceptron_io_is_guarded_twice(pathsec_sandbox, monkeypatch):
    """AveragedPerceptron.save/load are behind TWO independent layers.

    ``validate_tool_path`` refuses the file *shapes* a path check cannot see
    (FIFO, hardlink, non-regular), and ``pathsec.open`` independently refuses an
    out-of-sandbox path at open time. Neutering either one alone must leave the
    escape blocked; only removing both opens it. That is what makes this
    defence-in-depth rather than two names for one check.
    """
    import nltk.tag.perceptron as perceptron

    root, outside = pathsec_sandbox
    planted = outside / "planted.json"
    planted.write_text('{"f": {"NN": 1.0}}', encoding="utf-8")

    with pytest.raises(PermissionError):
        _drive_perceptron_load(str(planted))

    monkeypatch.setattr(perceptron, "validate_tool_path", lambda *a, **k: None)
    with pytest.raises(PermissionError):
        _drive_perceptron_load(str(planted))

    # Deliberately the raw builtin (this is the "no guards at all" control, and
    # the target is outside the sandbox on purpose).
    monkeypatch.setattr(
        perceptron, "pathsec_open", lambda path, *a, **kw: builtins.open(path)
    )
    from nltk.tag.perceptron import AveragedPerceptron

    ap = AveragedPerceptron()
    ap.load(str(planted))
    assert ap.weights == {"f": {"NN": 1.0}}, (
        "both guards removed but the outside model was still not read; "
        "the probe is inert"
    )


def test_perceptron_save_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """With validate_tool_dir neutered, save_to_json writes a real model outside
    the sandbox, which is precisely the leak the guard closes."""
    import nltk.tag.perceptron as perceptron

    root, outside = pathsec_sandbox
    victim = outside / "planted_model_dir"

    with pytest.raises(PermissionError):
        _drive_save_to_json(str(victim))
    assert not victim.exists()

    monkeypatch.setattr(perceptron, "validate_tool_dir", lambda *a, **k: None)
    _assert_teeth(
        lambda: _drive_save_to_json(str(victim)),
        lambda: victim.exists()
        and any(p.name.endswith(".weights.json") for p in victim.iterdir()),
        what="save_to_json containment",
    )


# --- pathsec.validate_tool_path unit-level behaviour --------------------------
def test_validate_tool_path_rejects_option_shaped_paths(restricted_sandbox):
    """A path that begins with '-' becomes an option, not a filename (CWE-88)."""
    for bad in ("-mx4g", "--loadClassifier", "-"):
        with pytest.raises(PermissionError):
            pathsec.validate_tool_path(bad, context="probe")


def test_validate_tool_path_rejects_blank_and_nul(restricted_sandbox):
    for bad in ("", "   ", "\t", "\n", "a\x00b", "\x00"):
        with pytest.raises(PermissionError):
            pathsec.validate_tool_path(bad, context="probe")


def test_validate_tool_path_write_destination_may_not_exist(restricted_sandbox):
    """must_exist=False is for a file the tool will create, so a missing path is
    fine, but it still has to be inside the sandbox."""
    inside = os.path.join(restricted_sandbox, "not_yet.model")
    pathsec.validate_tool_path(inside, context="probe", must_exist=False)
    with pytest.raises(FileNotFoundError):
        pathsec.validate_tool_path(inside, context="probe")
    # and an existing regular file is accepted either way
    with pathsec.open(inside, "w", context="probe") as handle:
        handle.write("{}")
    pathsec.validate_tool_path(inside, context="probe")


@pytest.mark.skipif(not _POSIX, reason="POSIX file types")
def test_validate_tool_path_rejects_non_regular_files(restricted_sandbox):
    """A FIFO/socket/directory inside the root passes containment but would hang
    or confuse a native loader, so the file-type check refuses it."""
    root = Path(restricted_sandbox)
    fifo = root / "f.model"
    os.mkfifo(str(fifo))
    sockpath = root / "s.model"
    sk = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sk.bind(str(sockpath))
    adir = root / "d.model"
    adir.mkdir()
    try:
        for bad in (fifo, sockpath, adir):
            # containment alone says yes; the tool-path guard says no
            pathsec.validate_path(str(bad), context="probe")
            with pytest.raises(PermissionError):
                pathsec.validate_tool_path(str(bad), context="probe")
    finally:
        sk.close()


@pytest.mark.skipif(not _POSIX, reason="POSIX hardlinks")
def test_validate_tool_path_rejects_in_root_hardlink(restricted_sandbox):
    """A hardlink is a second name for an inode with no symlink to resolve, so
    path resolution cannot see that the data lives outside the sandbox."""
    root = Path(restricted_sandbox)
    outside = _outside_dir()
    try:
        secret = outside / "secret"
        secret.write_text("SECRET", encoding="utf-8")
        hard = root / "hard.model"
        try:
            os.link(str(secret), str(hard))
        except OSError:
            pytest.skip("hardlinks unavailable here")
        pathsec.validate_path(str(hard), context="probe")
        with pytest.raises(PermissionError):
            pathsec.validate_tool_path(str(hard), context="probe")
    finally:
        shutil.rmtree(outside, ignore_errors=True)


def _outside_dir():
    return Path(
        tempfile.mkdtemp(prefix=".nltk_tagsweep_outside_", dir=str(Path.home()))
    )


def test_validate_path_no_longer_waves_through_a_blank_path(restricted_sandbox):
    """Regression: ``validate_path`` used to return early for any all-whitespace
    string, so ``"   "`` silently became a directory/file in the CWD, escaping
    the sandbox at every call site that trusts validate_path alone."""
    for blank in ("   ", "\t", "\n", " \t "):
        with pytest.raises(PermissionError):
            pathsec.validate_path(blank, context="probe")
    # the genuinely empty path stays a no-op: nothing can open it
    pathsec.validate_path("", context="probe")
    pathsec.validate_path(None, context="probe")


# --- sandbox-widening: the escape that would defeat every guard above --------
@pytest.mark.parametrize("victim", ["/etc", "/usr/bin", "~"])
def test_model_dir_authorization_does_not_widen_the_sandbox(victim, monkeypatch):
    """A caller-supplied model directory must never be added to nltk.data.path.

    NLTK used to widen the sandbox so a model saved under the private system-temp
    dir could be read back. ``pathsec.is_private_dir`` accepts
    any directory owned by the current user *or root* that is not group/world
    writable, which includes /etc, /usr/bin and $HOME. Authorizing one of those
    disarms ``validate_path`` AND ``internals._verify_jar_sandbox`` for the whole
    process, defeating every model-path guard in this module at once.
    """
    import nltk.data
    from nltk.internals import UntrustedJarError, _verify_jar_sandbox
    from nltk.tag.perceptron import PerceptronTagger

    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", list(nltk.data.path))
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)

    target = os.path.expanduser(victim)
    try:
        PerceptronTagger(load=True, lang="eng", loc=target)
    except Exception:
        pass  # the load itself fails; only its side effect matters here

    real = os.path.realpath(target)
    authorized = [
        os.path.realpath(str(p)) for p in nltk.data.path if isinstance(p, str)
    ]
    assert real not in authorized, f"{victim} was added to nltk.data.path"

    # and the guards it would have disarmed are still armed
    with pytest.raises(PermissionError):
        pathsec.validate_path(os.path.join(real, "anything"), context="probe")
    with pytest.raises(UntrustedJarError):
        _verify_jar_sandbox([os.path.join(real, "evil.jar")])


def test_trained_model_dir_is_allocated_inside_a_data_root():
    """NLTK's own trained-model dir must be allocated by pathsec inside a data
    root, so saving and loading need no sandbox widening at all.

    This is what replaced the old guessable ``<tempdir>/<tagger>_<lang>`` plus an
    authorize step: an unpredictable 0700 directory under an allowed root.
    """
    import nltk.data
    from nltk.tag.perceptron import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    save_dir = tagger.save_dir
    try:
        roots = [
            os.path.realpath(os.path.expanduser(str(p)))
            for p in nltk.data.path
            if isinstance(p, str)
        ]
        real = os.path.realpath(save_dir)
        assert any(
            real == r or real.startswith(r + os.sep) for r in roots
        ), f"{save_dir} is not inside an allowed data root"
        # already inside the sandbox: pathsec permits it without any widening
        pathsec.validate_path(save_dir, context="probe")
        if os.name == "posix":
            assert (os.stat(real).st_mode & 0o077) == 0, "staging dir is not private"
    finally:
        shutil.rmtree(save_dir, ignore_errors=True)


def test_sandbox_widening_primitive_is_gone():
    """The helper that appended a caller directory to nltk.data.path must not come
    back: it let one public call disarm validate_path and the jar sandbox."""
    import nltk.tag.perceptron as perceptron

    assert not hasattr(perceptron, "_authorize_private_dir")
    source = inspect.getsource(perceptron)
    assert "nltk.data.path.append" not in source
    assert "_ALLOWED_ROOTS_CACHE" not in source


# --- algorithmic DoS reachable through the same model-path entry point --------
@pytest.mark.parametrize(
    "resource_name", ["\n", "\r\n", "a\nb", "\n\n\n", "x\ny\nz\n", "corpora/a\nb/c"]
)
def test_find_terminates_on_a_newline_resource_name(restricted_sandbox, resource_name):
    """``nltk.data.find`` must not blow up on a resource name containing a newline.

    ``find`` decides whether a name is a zip with ``(.*?\\.zip)/?(.*)$``. Without
    ``re.DOTALL`` that never matches a name containing a newline, so the
    ".zip/" retry kept re-entering ``find`` with an ever-longer name: a
    caller-supplied ``PerceptronTagger(loc=...)`` of one newline burned 76s and
    2.7 GB before raising (CWE-407). Guarded by absolute time, not a ratio.
    """
    started = time.monotonic()
    with pytest.raises((LookupError, ValueError)):
        nltk.data.find(resource_name, paths=[restricted_sandbox])
    elapsed = time.monotonic() - started
    assert elapsed < 5.0, f"find({resource_name!r}) took {elapsed:.1f}s (DoS)"


def test_perceptron_loc_with_newline_terminates(pathsec_sandbox):
    """The same DoS through the tagger entry point that surfaced it."""
    from nltk.tag.perceptron import PerceptronTagger

    started = time.monotonic()
    with pytest.raises((LookupError, PermissionError, ValueError)):
        PerceptronTagger(load=True, lang="eng", loc="\n")
    assert time.monotonic() - started < 5.0


def test_find_still_resolves_ordinary_zip_style_names(restricted_sandbox):
    """Over-block control for the DOTALL fix: ordinary names behave unchanged."""
    root = Path(restricted_sandbox)
    (root / "corpora").mkdir()
    (root / "corpora" / "demo").mkdir()
    (root / "corpora" / "demo" / "f.txt").write_text("hi", encoding="utf-8")
    found = nltk.data.find("corpora/demo/f.txt", paths=[restricted_sandbox])
    assert str(found).endswith(os.path.join("corpora", "demo", "f.txt"))
    with pytest.raises(LookupError):
        nltk.data.find("corpora/demo/missing.txt", paths=[restricted_sandbox])


# --- documented negative results ---------------------------------------------
def test_setting_model_file_attribute_directly_reaches_no_loader():
    """Assigning ``_model_file`` bypasses the guard but reaches nothing.

    The only native ``open()`` is inside the guarded setter, so a raw attribute
    write leaves an inert string rather than loading a model.
    """
    import nltk.tag.crf as crf_module

    source = inspect.getsource(crf_module)
    opens = [ln.strip() for ln in source.splitlines() if "_tagger.open(" in ln]
    assert opens, "expected a native open() call in crf.py"
    for line in opens:
        assert "self._model_file" in line
    setter = inspect.getsource(crf_module.CRFTagger.set_model_file)
    assert "validate_tool_path" in setter
    assert setter.index("validate_tool_path") < setter.index("_tagger.open")


def test_hunpos_binary_is_caller_trusted_but_never_cwd_relative(sandbox):
    """Documented trust boundary: ``path_to_bin`` names an *executable*, which
    legitimately lives outside nltk_data (``/usr/local/bin`` etc.), so it is not
    sandbox-bound. What must stay refused is the CWD-relative discovery path,
    where a planted ``hunpos-tag`` in the working directory would be executed.
    """
    from nltk.internals import find_binary

    saved_cwd = os.getcwd()
    planted = sandbox / "cwd"
    planted.mkdir()
    (planted / "hunpos-tag").write_text("#!/bin/sh\n", encoding="utf-8")
    os.chmod(planted / "hunpos-tag", 0o700)
    try:
        os.chdir(planted)
        with pytest.raises(LookupError):
            find_binary("hunpos-tag", searchpath=[])
    finally:
        os.chdir(saved_cwd)


# --- the OTHER caller-controlled component: lang becomes a filename -----------
_LANG_ESCAPES = [
    "sub/../../../../../../../../etc",
    "..",
    ".",
    "",
    "   ",
    "\t",
    "a/b",
    "a\\b",
    "/etc/passwd",
    "x\x00",
]


@pytest.mark.parametrize("lang", _LANG_ESCAPES)
def test_save_to_json_refuses_a_path_shaped_lang(pathsec_sandbox, lang):
    """``lang`` is interpolated into the model filename, which is opened relative
    to a pinned directory fd. The fd anchors the base but NOT a ``..`` inside the
    name, so a path-shaped lang wrote outside the sandbox entirely (CWE-22)."""
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    loc = root / "mdir"
    loc.mkdir(mode=0o700)
    (loc / "averaged_perceptron_tagger_sub").mkdir(mode=0o700)

    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    with pytest.raises((ValueError, PermissionError)):
        tagger.save_to_json(lang=lang, loc=str(loc))
    assert not list(outside.iterdir()), "a path-shaped lang escaped the sandbox"


def test_lang_traversal_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Negative control: without the filename guard the traversal really lands
    outside the pinned directory, so the guard is what stops it."""
    import nltk.tag.perceptron as perceptron

    root, outside = pathsec_sandbox
    loc = root / "mdir"
    loc.mkdir(mode=0o700)
    sub = loc / "averaged_perceptron_tagger_sub"
    sub.mkdir(mode=0o700)
    rel = os.path.relpath(os.path.realpath(str(outside)), os.path.realpath(str(sub)))
    lang = "sub/" + rel + "/TRAVERSED"

    tagger = perceptron.PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}

    with pytest.raises(ValueError):
        tagger.save_to_json(lang=lang, loc=str(loc))
    assert not list(outside.iterdir())

    monkeypatch.setattr(
        perceptron, "_validate_name_component", lambda value, kind="": str(value)
    )
    _assert_teeth(
        lambda: tagger.save_to_json(lang=lang, loc=str(loc)),
        lambda: any(p.name.startswith("TRAVERSED") for p in outside.iterdir()),
        what="lang traversal",
    )


@pytest.mark.parametrize("lang", ["eng", "xxx", "sv", "rus", "en-GB", "zh_TW", "a.b"])
def test_ordinary_language_codes_still_work(pathsec_sandbox, lang):
    """Over-block control: a real language code is a plain filename component."""
    from nltk.tag.perceptron import PerceptronTagger

    root, _ = pathsec_sandbox
    loc = root / "mdir"
    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    tagger.save_to_json(lang=lang, loc=str(loc))
    written = sorted(p.name for p in loc.iterdir())
    assert written == [
        f"averaged_perceptron_tagger_{lang}.classes.json",
        f"averaged_perceptron_tagger_{lang}.tagdict.json",
        f"averaged_perceptron_tagger_{lang}.weights.json",
    ]

    reloaded = PerceptronTagger(load=False)
    reloaded.load_from_json(lang, str(loc))
    assert reloaded.classes == {"NN"}


def test_param_files_is_the_lang_chokepoint():
    """Both the save and the load side build filenames here, so the check lives
    in one place rather than being duplicated (and forgotten) at each caller."""
    from nltk.tag.perceptron import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    with pytest.raises(ValueError):
        list(tagger.param_files("../evil"))
    assert list(tagger.param_files("eng")) == [
        "averaged_perceptron_tagger_eng.weights.json",
        "averaged_perceptron_tagger_eng.tagdict.json",
        "averaged_perceptron_tagger_eng.classes.json",
    ]


def test_hunpos_newline_token_check_survives_optimised_mode():
    """The newline check must not be a bare ``assert``: ``python -O`` strips
    those, and a newline in a token injects an extra line into the tagger's
    line-oriented stdin, desynchronising every tag after it."""
    from nltk.tag.hunpos import HunposTagger

    source = inspect.getsource(HunposTagger.tag)
    statements = [ln.strip() for ln in source.splitlines()]
    assert not any(ln.startswith("assert ") for ln in statements)
    assert "raise ValueError" in source


@pytest.mark.parametrize("lang", ["..%2f..%2fetc", "%2e%2e", "a%00b"])
def test_percent_encoded_lang_is_written_verbatim(pathsec_sandbox, lang):
    """Benign pin: a percent-encoded lang is NOT decoded anywhere downstream, so
    it stays an ordinary (ugly) filename inside the sandbox. If a future change
    starts decoding it, this test turns into a traversal report."""
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    loc = root / "mdir"
    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    tagger.save_to_json(lang=lang, loc=str(loc))
    written = sorted(p.name for p in loc.iterdir())
    assert written == [
        f"averaged_perceptron_tagger_{lang}.classes.json",
        f"averaged_perceptron_tagger_{lang}.tagdict.json",
        f"averaged_perceptron_tagger_{lang}.weights.json",
    ], "a percent-encoded lang was decoded somewhere downstream"
    assert not list(outside.iterdir())


# --- the environment as an attack channel ------------------------------------
def test_hunpos_env_var_model_outside_the_sandbox_is_refused(
    pathsec_sandbox, monkeypatch
):
    """``find_file`` consults ``$HUNPOS_TAGGER``, so the environment can aim the
    model path outside the sandbox without the caller passing anything."""
    import nltk.tag.hunpos as hunpos_module

    root, outside = pathsec_sandbox
    model = outside / "en_wsj.model"
    model.write_text("stub", encoding="utf-8")
    stub = root / "hunpos-tag"
    stub.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    os.chmod(stub, 0o700)

    def _boom(cmd, *args, **kwargs):
        raise _ReachedSink(list(cmd))

    monkeypatch.setenv("HUNPOS_TAGGER", str(model))
    monkeypatch.setattr(hunpos_module, "Popen", _boom)
    with pytest.raises(PermissionError):
        hunpos_module.HunposTagger("en_wsj.model", path_to_bin=str(stub))


def test_stanford_models_env_var_outside_the_sandbox_is_refused(
    pathsec_sandbox, monkeypatch
):
    """Same channel for the Stanford taggers: ``$STANFORD_MODELS`` feeds
    ``find_file``, whose result becomes a JVM argument."""
    from nltk.internals import find_file

    root, outside = pathsec_sandbox
    (outside / "english.tagger").write_text("stub", encoding="utf-8")
    monkeypatch.setenv("STANFORD_MODELS", str(outside))
    resolved = find_file("english.tagger", env_vars=("STANFORD_MODELS",))
    with pytest.raises(PermissionError):
        pathsec.validate_tool_path(resolved, context="probe")


def test_no_tag_or_chunk_module_widens_the_sandbox():
    """The sandbox-widening primitive must not come back anywhere in the tagger
    or chunker packages, not just in the one module it used to live in."""
    import importlib
    import pkgutil

    import nltk.chunk
    import nltk.tag

    banned = ("data.path.append", "_ALLOWED_ROOTS_CACHE", "_LAST_DATA_PATHS")
    scanned = 0
    for package in (nltk.tag, nltk.chunk):
        names = [package.__name__] + [
            info.name
            for info in pkgutil.iter_modules(package.__path__, package.__name__ + ".")
        ]
        for name in names:
            try:
                module = importlib.import_module(name)
                # inspect, not file I/O: nltk's own source lives outside the
                # data sandbox, so reading it as a file would be refused.
                text = inspect.getsource(module)
            except (ImportError, OSError, TypeError):
                continue
            scanned += 1
            for needle in banned:
                assert needle not in text, f"{name} re-introduces {needle}"
    assert scanned > 10, f"only {scanned} modules scanned; the sweep found nothing"


@pytest.mark.parametrize(
    "shape", ["plain", "double-slash", "dot-segment", "pathpointer", "bytes"]
)
def test_validate_tool_path_accepts_equivalent_spellings(restricted_sandbox, shape):
    """Over-block control: several spellings of the same in-root file are all the
    same file, and all must be accepted."""
    from nltk.data import FileSystemPathPointer

    root = Path(restricted_sandbox)
    legit = root / "legit.model"
    legit.write_text("{}", encoding="utf-8")
    value = {
        "plain": str(legit),
        "double-slash": str(root) + "//legit.model",
        "dot-segment": str(root) + "/./legit.model",
        "pathpointer": FileSystemPathPointer(str(legit)),
        "bytes": str(legit).encode(),
    }[shape]
    pathsec.validate_tool_path(value, context="probe")


# --- the staging-dir allocator: a prefix is concatenated, never resolved ------
_PREFIX_ESCAPES = ["../../evil_", "sub/../../evil_", "a\x00b", "a\\b", "/abs_", "a/b_"]


@pytest.mark.parametrize("prefix", _PREFIX_ESCAPES)
def test_make_staging_dir_refuses_a_path_shaped_prefix(restricted_sandbox, prefix):
    """``tempfile.mkdtemp`` concatenates *prefix* onto *dir*, so a ``..`` inside
    it places the staging directory outside the validated data root. Callers
    build the prefix from a tagger language / chunker fmt, both caller supplied
    (CWE-22)."""
    with pytest.raises(ValueError):
        nltk.data.make_staging_dir(prefix=prefix)


def test_make_staging_dir_still_stages_inside_the_root(restricted_sandbox):
    """Over-block control: an ordinary prefix still allocates inside the root,
    private and unpredictably named."""
    staged = nltk.data.make_staging_dir(prefix="nltk_probe_")
    real = os.path.realpath(staged)
    assert real.startswith(os.path.realpath(restricted_sandbox) + os.sep)
    assert os.path.basename(real).startswith("nltk_probe_")
    if _POSIX:
        assert (os.stat(real).st_mode & 0o077) == 0


def test_tagger_save_dir_refuses_a_path_shaped_lang(pathsec_sandbox):
    """The tagger reaches the allocator through ``save_dir``; with a real first
    component present the traversal used to create a directory under $HOME."""
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    seed = root / "nltk_averaged_perceptron_tagger_x"
    seed.mkdir()
    rel = os.path.relpath(os.path.realpath(str(outside)), os.path.realpath(str(seed)))
    with pytest.raises(ValueError):
        PerceptronTagger(load=False, lang="x/" + rel + "/evil").save_dir
    assert not list(outside.iterdir()), "save_dir staged output outside the sandbox"


def test_punkt_and_chunker_share_the_staging_guard(restricted_sandbox):
    """The same allocator backs punkt and the NE chunker, so the fix is one
    chokepoint rather than a per-caller check that the next caller forgets."""
    from nltk.tokenize.punkt import PunktTokenizer

    tokenizer = object.__new__(PunktTokenizer)
    tokenizer._lang = "../../evil"
    tokenizer._save_dir = None
    with pytest.raises(ValueError):
        tokenizer.save_dir


# --- PathPointer objects: the branch that assumes the caller already resolved --
def test_zip_pointer_to_an_outside_archive_is_refused(pathsec_sandbox):
    """``load_from_json`` accepts a ready-made PathPointer, so a caller could
    hand it a ZipFilePathPointer aimed at an archive outside the sandbox."""
    import zipfile

    from nltk.data import ZipFilePathPointer
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    archive = outside / "evil.zip"
    # builtins.zipfile on purpose: this stages the attack OUTSIDE the sandbox,
    # which pathsec.ZipFile would (correctly) refuse to create.
    with zipfile.ZipFile(str(archive), "w") as handle:
        for attr, payload in (
            ("weights", '{"z": {"NN": 1.0}}'),
            ("tagdict", '{"z": "NN"}'),
            ("classes", '["NN"]'),
        ):
            handle.writestr(f"m/averaged_perceptron_tagger_eng.{attr}.json", payload)

    tagger = PerceptronTagger(load=False)
    with pytest.raises((PermissionError, ValueError, OSError)):
        tagger.load_from_json("eng", ZipFilePathPointer(str(archive), "m/"))
    assert tagger.tagdict == {}


def test_filesystem_pointer_to_an_outside_dir_is_refused(pathsec_sandbox):
    """A FileSystemPathPointer is a str subclass, so it takes the absolute-path
    branch and must meet the same guard as a plain string."""
    import json

    from nltk.data import FileSystemPathPointer
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    planted = outside / "plantdir"
    planted.mkdir()
    for attr, payload in (
        ("weights", {"f": {"NN": 1.0}}),
        ("tagdict", {"f": "NN"}),
        ("classes", ["NN"]),
    ):
        (planted / f"averaged_perceptron_tagger_eng.{attr}.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

    tagger = PerceptronTagger(load=False)
    with pytest.raises(PermissionError):
        tagger.load_from_json("eng", FileSystemPathPointer(str(planted)))
    assert tagger.tagdict == {}


def test_duck_typed_pointer_is_a_documented_non_finding(pathsec_sandbox):
    """Negative result, kept so it is not rediscovered as a bug.

    An object that merely *looks* like a PathPointer supplies its own ``open``,
    so it can return any stream it likes. That is not a sandbox escape: a caller
    able to construct it already has the file access it would grant. NLTK's own
    pointer types are the ones that must be bounded, and they are (above).
    """
    from nltk.tag.perceptron import PerceptronTagger

    class _FakePointer:
        path = "/etc"

        def join(self, name):
            return self

        def open(self, encoding=None):
            return io.StringIO("not-json")

    with pytest.raises(Exception):
        PerceptronTagger(load=False).load_from_json("eng", _FakePointer())


@pytest.mark.parametrize("pieces", [5, 20, 80, 160])
def test_find_scales_linearly_in_the_number_of_path_pieces(restricted_sandbox, pieces):
    """The ".zip/" retry recurses once per piece; each retry must terminate
    immediately because the retried name now contains ".zip". Before the DOTALL
    fix a newline made that condition unreachable and the retries compounded."""
    name = "/".join(f"p{i}\n" for i in range(pieces))
    started = time.monotonic()
    with pytest.raises((LookupError, ValueError)):
        nltk.data.find(name, paths=[restricted_sandbox])
    assert time.monotonic() - started < 5.0


# --- platform-shaped vectors --------------------------------------------------
@pytest.mark.parametrize(
    "device", ["NUL", "CON", "COM1", "LPT1", "nul.model", "Con.txt"]
)
def test_windows_device_names_are_refused_as_model_paths(restricted_sandbox, device):
    """On Windows these are character devices wherever they appear, so
    ``<root>\\NUL`` is the null device rather than a file inside the root: a model
    write silently vanishes and a read returns nothing. Refused on Windows; on
    POSIX they are ordinary filenames and this asserts they stay usable."""
    target = os.path.join(restricted_sandbox, device)
    if os.name == "posix":
        with pathsec.open(target, "w", context="probe") as handle:
            handle.write("{}")
        pathsec.validate_tool_path(target, context="probe")
    else:
        with pytest.raises(PermissionError):
            pathsec.validate_tool_path(target, context="probe")


@pytest.mark.skipif(not _POSIX, reason="POSIX symlinks")
def test_in_root_symlink_is_refused_by_design(restricted_sandbox):
    """Deliberate, not an oversight: a final-component symlink is refused even
    when its target is inside the root, matching what ``pathsec.open`` already
    does for descriptors it owns. Data files are never symlinks, so refusing
    them outright removes the swap race rather than trying to win it."""
    root = Path(restricted_sandbox)
    real = root / "real.model"
    real.write_text("{}", encoding="utf-8")
    link = root / "link.model"
    os.symlink(str(real), str(link))

    pathsec.validate_tool_path(str(real), context="probe")
    pathsec.validate_path(str(link), context="probe")
    with pytest.raises(PermissionError):
        pathsec.validate_tool_path(str(link), context="probe")


def test_tool_path_string_checks_apply_even_with_enforce_off(
    restricted_sandbox, monkeypatch
):
    """``ENFORCE = False`` relaxes *sandbox policy*, which is a deployment
    choice. It does not make ``-mx4g`` or a NUL byte a valid model filename, so
    those checks stay on."""
    monkeypatch.setattr(pathsec, "ENFORCE", False)
    for bad in ("-mx4g", "a\x00b", "   "):
        with pytest.raises(PermissionError):
            pathsec.validate_tool_path(bad, context="probe")


# --- the other caller-supplied StanfordTagger arguments ----------------------
@pytest.mark.parametrize(
    "option",
    [
        "-Xshare:off",
        "-cp /etc",
        "@/etc/passwd",
        "-agentlib:jdwp=transport=dt_socket",
        "-Djava.security.policy=/etc/evil",
        "--add-opens=java.base/java.lang=ALL-UNNAMED",
        "-XX:OnOutOfMemoryError=touch /tmp/pwn",
    ],
)
def test_stanford_java_options_stay_on_the_allowlist(pathsec_sandbox, option):
    """``java_options`` is a constructor argument that reaches the JVM launcher.
    The model-path guard does not cover it; the ``java()`` option allowlist does,
    and this pins that the tagger really goes through that chokepoint."""
    from nltk.tag.stanford import StanfordPOSTagger

    root, _ = pathsec_sandbox
    model = root / "m.tagger"
    model.write_text("stub", encoding="utf-8")
    jar = root / "stanford-postagger.jar"
    jar.write_text("PK\x03\x04", encoding="utf-8")

    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = str(model)
    tagger._stanford_jar = str(jar)
    tagger._encoding = "utf8"
    tagger.java_options = option
    with pytest.raises((ValueError, PermissionError)):
        tagger.tag_sents([["a"]])


@pytest.mark.parametrize("encoding", ["-model", "utf8 -x", "-encoding"])
def test_stanford_encoding_never_reaches_the_jvm_as_an_option(
    pathsec_sandbox, encoding
):
    """Documented benign result: ``encoding`` also becomes an argv value, but the
    input is encoded with it first, so a non-codec string raises LookupError long
    before ``java()``. Pinned so a refactor that stops encoding first (and starts
    passing the raw string through) shows up here."""
    from nltk.tag.stanford import StanfordPOSTagger

    root, _ = pathsec_sandbox
    model = root / "m.tagger"
    model.write_text("stub", encoding="utf-8")

    tagger = object.__new__(StanfordPOSTagger)
    tagger._stanford_model = str(model)
    tagger._stanford_jar = str(root / "stanford-postagger.jar")
    tagger._encoding = encoding
    tagger.java_options = "-mx1000m"
    with pytest.raises(LookupError):
        _no_jvm(lambda: tagger.tag_sents([["a"]]))


# --- model *content* shapes, and the descriptor pass-through ------------------
def test_deeply_nested_model_json_raises_rather_than_crashing(restricted_sandbox):
    """A model file inside the sandbox is still parsed, so its shape matters:
    deep nesting must surface as RecursionError, not a crash or a hang."""
    from nltk.tag.perceptron import AveragedPerceptron

    deep = os.path.join(restricted_sandbox, "deep.json")
    with pathsec.open(deep, "w", context="probe") as handle:
        handle.write("[" * 200000 + "]" * 200000)
    started = time.monotonic()
    with pytest.raises((RecursionError, ValueError)):
        AveragedPerceptron().load(deep)
    assert time.monotonic() - started < 10.0


def test_large_flat_model_is_not_size_capped(restricted_sandbox):
    """Over-block control and a deliberate non-finding: real tagger models are
    tens of MB of weights, so there is no size cap on an in-sandbox model file.
    Containment, not size, is what bounds this sink."""
    import json

    from nltk.tag.perceptron import AveragedPerceptron

    big = os.path.join(restricted_sandbox, "big.json")
    weights = {f"f{i}": {"NN": 1.0} for i in range(50000)}
    with pathsec.open(big, "w", context="probe") as handle:
        json.dump(weights, handle)
    model = AveragedPerceptron()
    model.load(big)
    assert len(model.weights) == 50000


def test_integer_descriptor_is_a_documented_pass_through(pathsec_sandbox):
    """Negative result, recorded so it is not refiled as a bug.

    ``pathsec.open`` passes an ``int`` straight to ``builtins.open``: to hand
    NLTK a descriptor the caller must already have opened the file, so this
    grants no access they did not have. It is pinned because a future change
    that starts *deriving* a path from caller data and passing a descriptor
    would need a different guard.
    """
    from nltk.tag.perceptron import AveragedPerceptron

    root, outside = pathsec_sandbox
    secret = outside / "secret.json"
    secret.write_text('{"s": {"NN": 1.0}}', encoding="utf-8")
    fd = os.open(str(secret), os.O_RDONLY)
    try:
        model = AveragedPerceptron()
        model.load(fd)
        assert model.weights == {"s": {"NN": 1.0}}
    except OSError:
        os.close(fd)
        raise


# --- structural audit: no public entry point reaches a sink unguarded --------
_GUARD_NAMES = (
    "validate_tool_path",
    "validate_tool_dir",
    "validate_path",
    "pathsec_open",
    "_validate_lang",
    "make_staging_dir",
    "open_datafile",
    "find(",
)

# Methods that take a path-ish argument but delegate it to a guarded sibling
# rather than guarding it themselves. Listed explicitly so a future method that
# stops delegating (and starts opening the path itself) fails this audit.
_DELEGATING = {
    ("PerceptronTagger", "__init__"): "load_from_json",
    ("PerceptronTagger", "train"): "save_to_json",
}

_PATHY_TOKENS = ("path", "loc", "file", "dir", "model", "jar", "save")


def _touched_classes():
    from nltk.chunk.named_entity import Maxent_NE_Chunker
    from nltk.tag.crf import CRFTagger
    from nltk.tag.hunpos import HunposTagger
    from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger
    from nltk.tag.stanford import (
        StanfordNERTagger,
        StanfordPOSTagger,
        StanfordTagger,
    )

    return [
        AveragedPerceptron,
        PerceptronTagger,
        CRFTagger,
        HunposTagger,
        StanfordTagger,
        StanfordPOSTagger,
        StanfordNERTagger,
        Maxent_NE_Chunker,
    ]


def test_every_public_path_taking_method_is_guarded_or_delegates():
    """The #1 real bypass is a guard on one method while a sibling walks past it,
    so enumerate every public method on every touched class and require each one
    that accepts a path-ish argument to either hold a guard itself or delegate to
    a named sibling that does."""
    audited = 0
    for cls in _touched_classes():
        for name, member in sorted(vars(cls).items()):
            if name.startswith("__") and name != "__init__":
                continue
            func = member.fget if isinstance(member, property) else member
            func = getattr(func, "__func__", func)
            if not callable(func):
                continue
            try:
                source = inspect.getsource(func)
                signature = str(inspect.signature(func)).lower()
            except (OSError, TypeError, ValueError):
                continue
            if not any(token in signature for token in _PATHY_TOKENS):
                continue
            audited += 1
            if any(guard in source for guard in _GUARD_NAMES):
                continue
            delegate = _DELEGATING.get((cls.__name__, name))
            assert delegate, f"{cls.__name__}.{name} takes a path with no guard"
            assert delegate in source, (
                f"{cls.__name__}.{name} no longer delegates to {delegate}; "
                "it needs its own guard now"
            )
    assert audited >= 10, f"only {audited} path-taking methods audited"


@pytest.mark.parametrize(
    "tagger_name", ["seed/../../evil", "../../evil", "a\\b", "x\x00"]
)
def test_tagger_name_is_guarded_like_lang(pathsec_sandbox, tagger_name):
    """``TAGGER_NAME`` is the other half of the model filename and traverses the
    same way. Guarding only ``lang`` left this half open, which is why the check
    now runs on the composed filename rather than on one ingredient."""
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    loc = root / "mdir"
    loc.mkdir(mode=0o700)
    (loc / "seed").mkdir(mode=0o700)

    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    tagger.TAGGER_NAME = tagger_name
    with pytest.raises(ValueError):
        tagger.save_to_json(lang="eng", loc=str(loc))
    assert not list(outside.iterdir())


def test_tagger_name_traversal_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Negative control for the TAGGER_NAME half of the filename."""
    import nltk.tag.perceptron as perceptron

    root, outside = pathsec_sandbox
    loc = root / "mdir"
    loc.mkdir(mode=0o700)
    seed = loc / "seed"
    seed.mkdir(mode=0o700)
    rel = os.path.relpath(os.path.realpath(str(outside)), os.path.realpath(str(seed)))

    tagger = perceptron.PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    tagger.TAGGER_NAME = "seed/" + rel + "/EVIL"

    with pytest.raises(ValueError):
        tagger.save_to_json(lang="eng", loc=str(loc))
    assert not list(outside.iterdir())

    monkeypatch.setattr(
        perceptron, "_validate_name_component", lambda value, kind="": str(value)
    )
    _assert_teeth(
        lambda: tagger.save_to_json(lang="eng", loc=str(loc)),
        lambda: any(p.name.startswith("EVIL_") for p in outside.iterdir()),
        what="TAGGER_NAME traversal",
    )


def test_param_files_validates_the_composed_filename(pathsec_sandbox):
    """The chokepoint checks the whole name, so any future interpolation into it
    is covered without adding another per-ingredient check."""
    from nltk.tag.perceptron import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    tagger.TAGGER_NAME = "../evil"
    with pytest.raises(ValueError):
        tagger.param_files("eng")
    tagger.TAGGER_NAME = "averaged_perceptron_tagger"
    assert tagger.param_files("eng")[0].endswith("_eng.weights.json")


@pytest.mark.parametrize("tagger_name", ["..", "   ", ".", "-x"])
def test_odd_but_harmless_tagger_names_compose_to_safe_filenames(
    pathsec_sandbox, tagger_name
):
    """Benign pin: the check is on the *composed* filename, and ``..`` composes
    to ``.._eng.weights.json``, which is an ordinary file inside the pinned
    directory rather than a traversal. Permitting these is correct; pinned so a
    change that starts treating the composed name as a path is caught."""
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    loc = root / "mdir"

    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    tagger.TAGGER_NAME = tagger_name
    tagger.save_to_json(lang="eng", loc=str(loc))
    written = sorted(p.name for p in loc.iterdir())
    assert written == [
        f"{tagger_name}_eng.classes.json",
        f"{tagger_name}_eng.tagdict.json",
        f"{tagger_name}_eng.weights.json",
    ]
    assert not list(outside.iterdir())


@pytest.mark.parametrize("lang", ["../../etc", "a/b", "\n", "x\x00", "..", "   "])
def test_load_from_json_rejects_a_path_shaped_lang(pathsec_sandbox, lang):
    """The load side interpolates lang too: into a ``find()`` resource name and
    into the model filenames. Rejecting it up front makes the failure name the
    cause instead of surfacing as a resource-not-found much later."""
    from nltk.data import FileSystemPathPointer
    from nltk.tag.perceptron import PerceptronTagger

    root, _ = pathsec_sandbox
    with pytest.raises(ValueError):
        PerceptronTagger(load=False).load_from_json(
            lang, FileSystemPathPointer(str(root))
        )


@pytest.mark.skipif(not _POSIX, reason="/dev/fd accounting is POSIX")
def test_validate_tool_path_does_not_leak_descriptors(restricted_sandbox):
    """The guard opens the candidate to inspect it, so every refusal path must
    close that descriptor; otherwise a caller that retries a refused model in a
    loop exhausts the fd table (DoS)."""
    root = Path(restricted_sandbox)
    legit = root / "legit.model"
    legit.write_text("{}", encoding="utf-8")
    outside = _outside_dir()
    try:
        link = root / "l.model"
        os.symlink(str(outside / "x"), str(link))
        fifo = root / "f.model"
        os.mkfifo(str(fifo))
        before = len(os.listdir("/dev/fd"))
        for _ in range(200):
            pathsec.validate_tool_path(str(legit), context="probe")
            for bad in (str(link), str(fifo), str(outside / "nope")):
                with pytest.raises((PermissionError, OSError)):
                    pathsec.validate_tool_path(bad, context="probe")
        after = len(os.listdir("/dev/fd"))
        assert after <= before + 2, f"fd leak: {before} -> {after}"
    finally:
        shutil.rmtree(outside, ignore_errors=True)


# --- URL-shaped model paths: validated as one thing, opened as another --------
_URL_SHAPES = [
    "file://pwned",
    "FILE://Pwned",
    "file://evil/x",
    "file:",
    "file:///etc/passwd",
    "http://evil.example/m.model",
    "https://evil.example/m.model",
    "ftp://evil.example/m.model",
]


@pytest.mark.parametrize("url", _URL_SHAPES)
def test_url_shaped_model_paths_are_refused(pathsec_sandbox, url):
    """A ``file:`` URL is rewritten to its path component before the check, but
    the caller (and the tool) still holds the original string.

    ``urlparse("file://evil")`` puts ``evil`` in *netloc* and leaves the path
    EMPTY, so validate_path used to find nothing to validate and return, while
    ``save_to_json(loc="file://evil")`` went on to create ``./file:/evil`` in the
    working directory and write the model there. Found by fuzzing.
    """
    from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger

    root, outside = pathsec_sandbox
    workdir = outside / "cwd"
    workdir.mkdir()
    os.chdir(workdir)

    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_path(url, context="probe")
    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_tool_dir(url, context="probe")
    with pytest.raises((PermissionError, ValueError)):
        pathsec.validate_tool_path(url, context="probe")

    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    with pytest.raises((PermissionError, ValueError)):
        tagger.save_to_json(lang="eng", loc=url)
    with pytest.raises((PermissionError, ValueError)):
        AveragedPerceptron().load(url)

    assert not list(workdir.iterdir()), f"{url} wrote into the working directory"


def test_empty_path_file_url_guard_is_load_bearing(pathsec_sandbox, monkeypatch):
    """Negative control: with the URL rejection removed, the write really lands
    in the working directory as ./file:/pwned."""
    import nltk.tag.perceptron as perceptron

    root, outside = pathsec_sandbox
    workdir = outside / "cwd"
    workdir.mkdir()
    os.chdir(workdir)

    tagger = perceptron.PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}

    with pytest.raises((PermissionError, ValueError)):
        tagger.save_to_json(lang="eng", loc="file://pwned")
    assert not list(workdir.iterdir())

    monkeypatch.setattr(perceptron, "validate_tool_dir", lambda *a, **k: None)
    # "file:" is not a legal directory name on Windows, so the escape is not
    # even representable there; _assert_teeth checks the right thing per platform.
    _assert_teeth(
        lambda: tagger.save_to_json(lang="eng", loc="file://pwned"),
        lambda: [p.name for p in workdir.iterdir()] == ["file:"],
        what="empty-path file URL",
    )


def test_ordinary_paths_that_merely_look_url_ish_still_work(restricted_sandbox):
    """Over-block control: only a real scheme prefix is a URL. A filename that
    happens to contain "://" or start with "file" is an ordinary path."""
    root = Path(restricted_sandbox)
    for name in ("filesystem.model", "file_backup.json", "a-file:name.model"):
        leaf = root / name
        leaf.write_text("{}", encoding="utf-8")
        pathsec.validate_tool_path(str(leaf), context="probe")
        pathsec.validate_tool_dir(str(root / "outdir"), context="probe")


# --- seeded fuzz: the hand-written matrix is not the whole shape space --------
_FUZZ_ALPHABET = list(string.printable) + [
    "\x00",
    "\n",
    "\\",
    "/",
    "..",
    "~",
    "%2e",
    ":",
    "\t",
    "-",
    "file:",
    "\r",
    "#",
    "?",
]

_FUZZ_PREFIXES = [
    "",
    "./",
    "../",
    "-",
    "file://",
    "file:///",
    "http://",
    "https://",
    "ftp://",
    "\\\\",
    "//",
    "~/",
    "/dev/",
    "/proc/",
    "/etc/",
]


@pytest.mark.parametrize("seed", [7, 20260826])
def test_fuzzed_paths_never_resolve_outside_the_root(restricted_sandbox, seed):
    """Randomised sweep over the guards.

    The hand-written vectors above encode shapes someone thought of; this covers
    the ones nobody did. It is how the empty-path ``file:`` URL escape was found:
    the guard returned success for a string that resolved outside the root. Two
    fixed seeds keep it deterministic and fast while still sampling widely.
    """
    root_real = os.path.realpath(restricted_sandbox)
    rng = random.Random(seed)
    expected = (PermissionError, ValueError, OSError, TypeError)

    def resolves_inside(candidate):
        try:
            real = os.path.realpath(candidate)
        except (OSError, ValueError):
            return False
        return real == root_real or real.startswith(root_real + os.sep)

    guards = (
        lambda v: pathsec.validate_tool_path(v, context="fuzz"),
        lambda v: pathsec.validate_tool_path(v, context="fuzz", must_exist=False),
        lambda v: pathsec.validate_tool_dir(v, context="fuzz"),
    )

    leaked = []
    for _ in range(1500):
        body = "".join(rng.choice(_FUZZ_ALPHABET) for _ in range(rng.randint(1, 14)))
        candidate = rng.choice(_FUZZ_PREFIXES + [restricted_sandbox + os.sep]) + body
        for guard in guards:
            try:
                guard(candidate)
            except expected:
                continue
            except Exception as exc:  # noqa: BLE001 - an unexpected type is a finding
                leaked.append((candidate, f"{type(exc).__name__}: {exc}"))
                continue
            if not resolves_inside(candidate):
                leaked.append((candidate, "permitted but resolves outside the root"))
    assert not leaked, f"fuzz found {len(leaked)} escapes, e.g. {leaked[:3]}"


def test_fuzzed_sink_arguments_never_write_outside_the_root(pathsec_sandbox):
    """The same idea one level up: fuzz the *sink* arguments together.

    ``lang``, ``TAGGER_NAME`` and ``loc`` are composed into one filesystem
    operation, so a combination can be dangerous when no single part is. This
    drives the real write path and then asserts that nothing appeared outside
    the root or in the working directory.
    """
    from nltk.tag.perceptron import PerceptronTagger

    root, outside = pathsec_sandbox
    workdir = outside / "cwd"
    workdir.mkdir()
    os.chdir(workdir)

    rng = random.Random(99)
    locations = [
        str(root / "d"),
        str(outside / "d"),
        "d",
        "/etc/d",
        "file://x",
        "~/d",
        "-d",
        "",
        "   ",
    ]
    tagger = PerceptronTagger(load=False)
    tagger.model.weights = {"f": {"NN": 1.0}}
    tagger.tagdict = {}
    tagger.classes = {"NN"}

    surprises = []
    for _ in range(200):
        lang = "".join(rng.choice(_FUZZ_ALPHABET) for _ in range(rng.randint(1, 8)))
        tagger.TAGGER_NAME = "".join(
            rng.choice(_FUZZ_ALPHABET) for _ in range(rng.randint(1, 8))
        )
        try:
            tagger.save_to_json(lang=lang, loc=rng.choice(locations))
        except (PermissionError, ValueError, OSError, TypeError):
            continue
        except Exception as exc:  # noqa: BLE001 - an unexpected type is a finding
            surprises.append((lang, tagger.TAGGER_NAME, f"{type(exc).__name__}: {exc}"))

    assert not surprises, f"unexpected failures: {surprises[:3]}"
    stray = [p.name for p in outside.iterdir() if p.name != "cwd"]
    assert not stray, f"fuzzed save_to_json wrote outside the root: {stray}"
    assert not list(workdir.iterdir()), "fuzzed save_to_json wrote into the CWD"


def test_zip_internal_traversal_stays_inside_the_archive(restricted_sandbox):
    """Documented benign result: the packaged tagger model is a zip, so a member
    name like ``../escape.json`` is worth checking.

    Reading it yields bytes from that same archive; nothing is extracted and no
    path outside the zip is touched, so an in-root archive stays in-root however
    its members are named. The extraction-side zip-slip guard lives in
    ``pathsec.validate_zip_archive`` and is exercised by the zipbomb suite.
    """
    import json
    import zipfile

    from nltk.data import ZipFilePathPointer
    from nltk.tag.perceptron import PerceptronTagger

    root = Path(restricted_sandbox)
    archive = root / "taggers.zip"
    with pathsec.ZipFile(str(archive), "w") as handle:
        for attr, payload in (
            ("weights", {"in": {"NN": 1.0}}),
            ("tagdict", {"in": "NN"}),
            ("classes", ["NN"]),
        ):
            handle.writestr(
                f"m/averaged_perceptron_tagger_eng.{attr}.json", json.dumps(payload)
            )
        handle.writestr("../escape.json", "ESCAPED")

    pointer = ZipFilePathPointer(str(archive), "../escape.json")
    with pointer.open() as stream:
        assert stream.read().strip() in (b"ESCAPED", "ESCAPED")
    # nothing was created outside the archive
    assert sorted(p.name for p in root.iterdir()) == ["taggers.zip"]

    # and the legitimate in-root zip model still loads
    tagger = PerceptronTagger(load=False)
    tagger.load_from_json("eng", ZipFilePathPointer(str(archive), "m/"))
    assert tagger.tagdict == {"in": "NN"}
    assert isinstance(zipfile.ZipFile(str(archive)).namelist(), list)


# --- the stdlib normalising a name AFTER it was validated (CWE-22) -----------
_NORMALIZED_BYPASS_NAMES = [
    ".\n./TARGET",
    ".\t./TARGET",
    ".\r./TARGET",
    "..\n/TARGET",
    "corpora/.\n./.\n./TARGET",
    "a#b",
    "a?b",
    "\n",
    "a\nb",
]


@pytest.mark.parametrize("resource_name", _NORMALIZED_BYPASS_NAMES)
def test_find_refuses_names_the_stdlib_would_rewrite(restricted_sandbox, resource_name):
    """``find`` validates the raw name and then joins ``url2pathname(name)``.

    Python 3.14 made ``url2pathname`` follow the WHATWG URL rules: it strips
    ASCII tab / LF / CR and truncates at ``#`` or ``?``. Stripping *creates* a
    traversal the raw-form check never saw, so ``find(".\\n./TARGET")`` contained
    no ``../`` when it was validated and became ``../TARGET`` when it was used,
    escaping the data root on 3.14 (CWE-22). Refusing the characters keeps the
    validated and the used name identical on every version.
    """
    with pytest.raises(ValueError):
        nltk.data.find(resource_name, paths=[restricted_sandbox])


def test_normalized_bypass_would_escape_without_the_guard(restricted_sandbox):
    """Negative control, and the proof this is version-specific.

    Runs the conversion the way ``find`` does and asserts that on an
    interpreter which rewrites the name the result really would leave the root,
    so the guard above is not defending against nothing.
    """
    from urllib.request import url2pathname

    converted = url2pathname(".\n./TARGET")
    joined = os.path.realpath(os.path.join(restricted_sandbox, converted))
    root_real = os.path.realpath(restricted_sandbox)
    escapes = not (joined == root_real or joined.startswith(root_real + os.sep))
    if converted == ".\n./TARGET":
        # This interpreter does not rewrite; nothing to escape with.
        assert not escapes
    else:
        assert converted == os.path.join("..", "TARGET") or ".." in converted
        assert escapes, "the rewritten name should have left the root"


def test_ordinary_resource_names_are_unaffected(restricted_sandbox):
    """Over-block control for the rejection: real resource names are plain."""
    root = Path(restricted_sandbox)
    (root / "corpora").mkdir()
    (root / "corpora" / "demo").mkdir()
    (root / "corpora" / "demo" / "f.txt").write_text("hi", encoding="utf-8")
    assert str(nltk.data.find("corpora/demo/f.txt", paths=[restricted_sandbox]))
    for name in ("corpora/demo", "corpora/demo/", "taggers/x_eng.json", "a b/c-d.e"):
        try:
            nltk.data.find(name, paths=[restricted_sandbox])
        except Exception as exc:  # noqa: BLE001 - only the reason matters here
            assert "Unsafe resource path" not in str(
                exc
            ), f"{name!r} was wrongly rejected as unsafe"


@pytest.mark.parametrize("seed", [3141])
def test_fuzzed_resource_names_never_resolve_outside_the_root(restricted_sandbox, seed):
    """Fuzz ``find`` itself, not just the path guards.

    ``find`` is where a resource name becomes a filesystem path, and it is the
    step the standard library rewrites underneath us: this is the shape that
    escaped on Python 3.14. A candidate is a finding if ``find`` returns a
    pointer whose realpath is outside the data root.
    """
    root_real = os.path.realpath(restricted_sandbox)
    rng = random.Random(seed)
    expected = (LookupError, ValueError, OSError, TypeError)

    escapes = []
    for _ in range(1200):
        name = "".join(rng.choice(_FUZZ_ALPHABET) for _ in range(rng.randint(1, 14)))
        try:
            found = nltk.data.find(name, paths=[restricted_sandbox])
        except expected:
            continue
        except Exception as exc:  # noqa: BLE001 - an unexpected type is a finding
            escapes.append((name, f"{type(exc).__name__}: {exc}"))
            continue
        real = os.path.realpath(str(found))
        if not (real == root_real or real.startswith(root_real + os.sep)):
            escapes.append((name, real))
    assert not escapes, f"find() escaped the root: {escapes[:3]}"

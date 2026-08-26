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
import inspect
import os
import re
import shutil
import socket
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


# --- the guards must be load-bearing, not incidental --------------------------
_TEETH = [
    ("nltk.tag.crf", "validate_tool_path", _drive_crf_set),
    ("nltk.tag.stanford", "validate_tool_path", _drive_stanford_tag_sents),
    ("nltk.tag.hunpos", "validate_tool_path", _drive_hunpos_init),
    ("nltk.tag.perceptron", "validate_tool_dir", _drive_save_to_json),
]


@pytest.mark.parametrize("modname,attr,driver", _TEETH, ids=lambda v: str(v)[:40])
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
    _drive_save_to_json(str(victim))
    written = sorted(p.name for p in victim.iterdir())
    assert written, "guard removed but nothing was written; the probe is inert"
    assert any(name.endswith(".weights.json") for name in written)


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
    with pytest.raises(LookupError):
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
    """Negative control: without _validate_lang the traversal really lands
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

    monkeypatch.setattr(perceptron, "_validate_lang", lambda value: str(value))
    tagger.save_to_json(lang=lang, loc=str(loc))
    escaped = sorted(p.name for p in outside.iterdir())
    assert escaped, "guard removed but nothing escaped; the probe is inert"
    assert any(name.startswith("TRAVERSED") for name in escaped)


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
def test_hunpos_env_var_model_outside_the_sandbox_is_refused(pathsec_sandbox, monkeypatch):
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
    import nltk.chunk
    import nltk.tag

    import importlib
    import pkgutil

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

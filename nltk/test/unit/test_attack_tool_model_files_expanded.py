# Natural Language Toolkit: expanded attack harness for tool model files
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded attack harness for the MODEL FILES handed to external tools.

Sinks: ``CRFTagger.set_model_file`` / ``train`` (pycrfsuite, a C loader and
writer), ``StanfordTagger`` (JVM ``-model`` / ``-loadClassifier``) and
``StanfordSegmenter`` (JVM ``-loadClassifier`` / ``-serDictionary`` /
``-sighanCorporaDict`` plus a path-valued ``options=`` entry). Each is bounded
by ``validate_tool_path`` with ``max_bytes`` and ``require_private`` (the Sihan
corpora dir by ``validate_tool_dir(require_private=True)``), and each wrapper
must use the STRING the guard returns rather than the caller's object.

Every vector runs against the real wrapper code. The CRF sink is the real
pycrfsuite loader, nothing mocked. The JVM wrappers run their real discovery
and guard code with ONLY the final ``java`` hand-off replaced by a trap that
records argv: a hostile path reaching that argv is the leak evidence, and a
benign path must reach it, so an over-block is caught too. A test that needs a
real JVM and a real tool install inside a data root runs when both exist and
skips otherwise.

Vectors per sink: an absolute system file, ``..`` traversal, a symlink into and
out of the root, a symlinked intermediate directory, a hardlink, FIFO / socket /
device / directory, NUL and control characters, URL / UNC / ``~`` forms, Windows
device names and NTFS stream names, a trailing dot or space, blank and
option-shaped strings, non-path objects, a sparse file over the REAL
``MAX_TOOL_MODEL_BYTES`` ceiling (no monkeypatched cap), group- and
world-writable modes, a PathLike whose ``__fspath__`` changes between calls, a
lying ``str`` subclass, and bytes.

Teeth: each guard has a negative control that neuters it in-process and asserts
the harness then observes the leak, so a vector cannot pass by never reaching
the sink.

Documented residuals, not exploits under the threat model: a gzip-compressed JVM
model is bounded by its on-disk size, not its inflated size (a same-UID planter
who can put a private file in a data root already controls the process); a
swap between the check and the tool's own open remains a race for any
path-taking sink; a bare (separator-free) ``options=`` value is a resource name
the JVM resolves itself, like ``validate_model_resource`` allows.
"""

import glob
import hashlib
import inspect
import os
import pathlib
import shutil
import socket
import tempfile
from types import SimpleNamespace

import pytest

import nltk.data
from nltk import internals, pathsec
from nltk.pathsec import MAX_TOOL_MODEL_BYTES

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="symlink / hardlink / FIFO / mode semantics are POSIX"
)

NUL = chr(0)
ESC = chr(0x1B)
DEL = chr(0x7F)
VT = chr(0x0B)
FF = chr(0x0C)
PASSWD = "/etc/passwd"
ZH = "".join(chr(c) for c in (0x4E2D, 0x6587))  # two CJK characters


# =========================================================================== #
# Fixtures and helpers
# =========================================================================== #
class _ReachedJVM(Exception):
    """Raised by the trapped ``java`` once the argv is fully built."""

    def __init__(self, argv):
        super().__init__("reached the JVM hand-off")
        self.argv = list(argv)


class _MutatingPath:
    """``__fspath__`` answers ``first`` once and ``rest`` on every later call."""

    def __init__(self, first, rest):
        self.calls, self._first, self._rest = 0, first, rest

    def __fspath__(self):
        self.calls += 1
        return self._first if self.calls == 1 else self._rest


class _LyingStr(str):
    """A ``str`` whose inspection methods deny what it holds."""

    def startswith(self, *a, **k):
        return False

    def __contains__(self, _item):
        return False

    def replace(self, *a, **k):
        return _LyingStr("")


@pytest.fixture
def atk(monkeypatch):
    """One fresh trusted root and one dir OUTSIDE every root, both under $HOME
    (a private system temp dir is itself a root on macOS/Windows)."""
    home = str(pathlib.Path.home())
    root = os.path.realpath(tempfile.mkdtemp(prefix=".nltk_atk_model_root_", dir=home))
    outside = os.path.realpath(
        tempfile.mkdtemp(prefix=".nltk_atk_model_out_", dir=home)
    )
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    monkeypatch.setattr(nltk.data, "_STAGING_TEMPDIR", None, raising=False)
    monkeypatch.delenv("STANFORD_MODELS", raising=False)
    monkeypatch.delenv("STANFORD_SEGMENTER", raising=False)
    try:
        yield SimpleNamespace(root=root, outside=outside, monkeypatch=monkeypatch)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(outside, ignore_errors=True)


def _trap_java(monkeypatch, module):
    sink = {}

    def fake_java(cmd, *args, **kwargs):
        sink["cmd"] = list(cmd)
        raise _ReachedJVM(cmd)

    monkeypatch.setattr(module, "java", fake_java)
    return sink


def _reg(path, content=b"model", mode=None):
    """A real regular file; the attacker's plant, so the stdlib writer."""
    with open(path, "wb") as fh:
        fh.write(content)
    if mode is not None:
        os.chmod(path, mode)
    return path


def _sparse(path, size):
    """A sparse file of exactly ``size`` bytes: st_size is real, disk use is not."""
    with open(path, "wb") as fh:
        fh.truncate(size)
    return path


def _private_dir(path):
    os.makedirs(path, exist_ok=True)
    os.chmod(path, 0o755)
    return path


def _is_security(exc):
    return "security violation" in str(exc).lower()


def _argv_value(argv, flag):
    return argv[argv.index(flag) + 1]


def _fspath(value):
    try:
        return os.fspath(value)
    except TypeError:
        return str(value)


# =========================================================================== #
# 1. CRFTagger.set_model_file: the real pycrfsuite loader
# =========================================================================== #
_TRAIN = [
    [("the", "DT"), ("cat", "NN"), ("sat", "VBD")],
    [("a", "DT"), ("dog", "NN"), ("ran", "VBD")],
]
_SENT = ["the", "cat", "sat"]
_TAGS = {"DT", "NN", "VBD"}


@pytest.fixture
def crf(atk):
    pytest.importorskip("pycrfsuite")
    from nltk.tag.crf import CRFTagger

    good = os.path.join(atk.root, "good.crf")
    CRFTagger().train(_TRAIN, good)
    planted = os.path.join(atk.outside, "planted.crf")
    shutil.copyfile(good, planted)  # a VALID model outside every root
    atk.good, atk.planted, atk.cls, atk.keep = good, planted, CRFTagger, []
    return atk


def _copy_with_mode(c, name, mode):
    path = os.path.join(c.root, name)
    shutil.copyfile(c.good, path)
    os.chmod(path, mode)
    return path


def _symlink(c, name, target):
    path = os.path.join(c.root, name)
    os.symlink(target, path)
    return path


def _hardlink(c, name, target):
    path = os.path.join(c.root, name)
    os.link(target, path)
    return path


def _fifo(c, name):
    path = os.path.join(c.root, name)
    os.mkfifo(path)
    return path


def _unix_socket(c, name):
    path = os.path.join(c.root, name)
    sock = socket.socket(socket.AF_UNIX)
    sock.bind(path)
    c.keep.append(sock)
    return path


def _traversal(c, leaf):
    return os.path.join(c.root, "..", os.path.basename(c.outside), leaf)


def _through_symlinked_dir(c, leaf):
    os.symlink(c.outside, os.path.join(c.root, "dirlink"))
    return os.path.join(c.root, "dirlink", leaf)


_CRF_SECURITY_REFUSED = [
    pytest.param(lambda c: PASSWD, id="absolute-system-file"),
    pytest.param(lambda c: c.planted, id="valid-model-outside-root"),
    pytest.param(lambda c: _traversal(c, "planted.crf"), id="dotdot-traversal"),
    pytest.param(
        lambda c: _symlink(c, "link_out.crf", c.planted),
        id="symlink-in-root-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _symlink(c, "link_in.crf", c.good),
        id="symlink-in-root-to-in-root",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _through_symlinked_dir(c, "planted.crf"),
        id="symlinked-intermediate-dir",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _hardlink(c, "hard_out.crf", c.planted),
        id="hardlink-in-root-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _hardlink(c, "hard_in.crf", c.good),
        id="hardlink-in-root-to-in-root",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda c: _fifo(c, "fifo.crf"), id="fifo", marks=POSIX_ONLY),
    pytest.param(
        lambda c: _unix_socket(c, "s.crf"), id="unix-socket", marks=POSIX_ONLY
    ),
    pytest.param(lambda c: "/dev/null", id="device-null", marks=POSIX_ONLY),
    pytest.param(lambda c: "/dev/zero", id="device-zero", marks=POSIX_ONLY),
    pytest.param(lambda c: "/dev/stdin", id="device-stdin", marks=POSIX_ONLY),
    pytest.param(lambda c: "/dev/fd/0", id="device-fd0", marks=POSIX_ONLY),
    pytest.param(lambda c: c.root, id="directory"),
    pytest.param(lambda c: c.good + NUL, id="nul-suffix"),
    pytest.param(lambda c: c.good + NUL + PASSWD, id="nul-splice"),
    pytest.param(lambda c: os.path.join(c.root, "g\n.crf"), id="lf-in-name"),
    pytest.param(lambda c: os.path.join(c.root, "g\r.crf"), id="cr-in-name"),
    pytest.param(lambda c: os.path.join(c.root, "g\t.crf"), id="tab-in-name"),
    pytest.param(lambda c: os.path.join(c.root, "g" + VT + ".crf"), id="vt-in-name"),
    pytest.param(lambda c: os.path.join(c.root, "g" + FF + ".crf"), id="ff-in-name"),
    pytest.param(lambda c: "file://" + PASSWD, id="url-file-outside"),
    pytest.param(lambda c: "file://" + c.good, id="url-file-in-root"),
    pytest.param(lambda c: "http://evil/m.crf", id="url-http"),
    pytest.param(lambda c: "jar:file:///x!/m", id="url-jar"),
    pytest.param(lambda c: "nltk:" + c.good, id="url-nltk-scheme"),
    pytest.param(lambda c: "FILE:///etc/passwd", id="url-file-uppercase"),
    pytest.param(lambda c: "\\\\srv\\share\\m.crf", id="unc-backslash"),
    pytest.param(lambda c: "//srv/share/m.crf", id="unc-slash"),
    pytest.param(lambda c: "~/good.crf", id="tilde-home"),
    pytest.param(lambda c: "~root/x.crf", id="tilde-user"),
    pytest.param(lambda c: c.good + ".", id="trailing-dot"),
    pytest.param(lambda c: c.good + " ", id="trailing-space"),
    pytest.param(lambda c: "", id="empty"),
    pytest.param(lambda c: "   ", id="whitespace-only"),
    pytest.param(lambda c: "-model", id="option-shaped"),
    pytest.param(lambda c: "-model=" + PASSWD, id="option-shaped-with-value"),
    pytest.param(lambda c: "good.crf", id="relative-bare-name-cwd-not-a-root"),
    pytest.param(lambda c: None, id="none"),
    pytest.param(lambda c: [c.good], id="list"),
    pytest.param(
        lambda c: _sparse(os.path.join(c.root, "big.crf"), MAX_TOOL_MODEL_BYTES + 1),
        id="oversize-real-ceiling-plus-one",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "ww.crf", 0o666),
        id="world-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "gw.crf", 0o664),
        id="group-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "ow.crf", 0o646),
        id="other-writable-only",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda c: _LyingStr(c.planted), id="lying-str-outside"),
    pytest.param(lambda c: c.planted.encode(), id="bytes-outside"),
    pytest.param(
        lambda c: _MutatingPath(c.planted, c.good), id="mutating-fspath-hostile-first"
    ),
]


@pytest.mark.parametrize("vector", _CRF_SECURITY_REFUSED)
def test_crf_hostile_model_is_security_refused_before_the_loader(crf, vector):
    tagger = crf.cls()
    with pytest.raises((PermissionError, ValueError)) as info:
        tagger.set_model_file(vector(crf))
    assert _is_security(info.value), info.value
    assert tagger._model_file == "", "the loader was reached"


_CRF_OS_REFUSED = [
    pytest.param(lambda c: os.path.join(c.root, "x.zip", "m.crf"), id="zip-component"),
    pytest.param(lambda c: os.path.join(c.root, "PROGRA~1", "m.crf"), id="short-name"),
    pytest.param(lambda c: os.path.join(c.root, "a" * 300 + ".crf"), id="over-long"),
    pytest.param(lambda c: c.good + "/", id="trailing-slash-on-a-file"),
    pytest.param(
        lambda c: _copy_with_mode(c, "m0.crf", 0o000), id="unreadable", marks=POSIX_ONLY
    ),
]


@pytest.mark.parametrize("vector", _CRF_OS_REFUSED)
def test_crf_unopenable_model_never_loads(crf, vector):
    """Refused by the OS rather than a security decision, but still no load."""
    tagger = crf.cls()
    with pytest.raises(OSError):
        tagger.set_model_file(vector(crf))
    assert tagger._model_file == ""


_CRF_BENIGN = [
    pytest.param(lambda c: c.good, id="plain-str"),
    pytest.param(lambda c: pathlib.Path(c.good), id="pathlib-path"),
    pytest.param(lambda c: c.good.encode(), id="bytes"),
    pytest.param(lambda c: _LyingStr(c.good), id="lying-str-in-root"),
    pytest.param(lambda c: os.path.join(c.root, ".", "good.crf"), id="dot-component"),
    pytest.param(lambda c: c.root + "//good.crf", id="double-separator"),
    pytest.param(
        lambda c: _copy_with_mode(c, "p600.crf", 0o600),
        id="mode-0600",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "p444.crf", 0o444),
        id="mode-0444",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "p2644.crf", 0o2644),
        id="setgid-no-write",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "p1644.crf", 0o1644),
        id="sticky-no-write",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "g" + ESC + "[31m.crf", 0o644),
        id="esc-in-name",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "g" + DEL + ".crf", 0o644),
        id="del-in-name",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "NUL", 0o644),
        id="windows-device-name-is-a-plain-posix-file",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "COM1.crf", 0o644),
        id="windows-com-name-is-a-plain-posix-file",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda c: _copy_with_mode(c, "good.crf:stream", 0o644),
        id="ntfs-stream-name-is-a-plain-posix-file",
        marks=POSIX_ONLY,
    ),
]


@pytest.mark.parametrize("vector", _CRF_BENIGN)
def test_crf_benign_model_loads_and_tags(crf, vector):
    """Over-block control on the real loader: a legitimate in-root model in any
    spelling still loads, and the wrapper keeps the guard's plain str."""
    tagger = crf.cls()
    tagger.set_model_file(vector(crf))
    tagged = tagger.tag(_SENT)
    assert [word for word, _ in tagged] == _SENT
    assert all(tag in _TAGS for _, tag in tagged)
    assert type(tagger._model_file) is str


@pytest.mark.parametrize("size", [MAX_TOOL_MODEL_BYTES, MAX_TOOL_MODEL_BYTES - 1])
@POSIX_ONLY
def test_crf_model_at_the_real_ceiling_passes_the_guard(crf, size):
    """Boundary: exactly the cap is not over it. The sparse zeros then fail
    pycrfsuite's own magic check, which proves the guard let the loader run."""
    edge = _sparse(os.path.join(crf.root, "edge.crf"), size)
    with pytest.raises(ValueError) as info:
        crf.cls().set_model_file(edge)
    assert not _is_security(info.value)
    assert "Invalid model file" in str(info.value)


def _truncated_header_plant(c):
    """A file pycrfsuite reports DISTINCTLY: valid magic but a short header.
    Opening it is therefore observable without touching the sink."""
    return _reg(os.path.join(c.outside, "truncated.crf"), b"lCRF" + b"\0" * 10)


def test_crf_mutating_fspath_is_frozen_at_the_real_sink(crf):
    """pycrfsuite calls ``__fspath__`` again inside ``Tagger.open`` (its magic
    check does a builtin open), so a PathLike that answers an in-root path to
    the guard and an outside path afterwards opened the outside file. The
    wrapper must hand the loader the checked str, resolving the object ONCE."""
    plant = _truncated_header_plant(crf)
    obj = _MutatingPath(crf.good, plant)
    tagger = crf.cls()
    tagger.set_model_file(obj)
    assert obj.calls == 1
    assert tagger._model_file == crf.good and type(tagger._model_file) is str
    assert [word for word, _ in tagger.tag(["the", "cat"])] == ["the", "cat"]


def test_crf_mutating_fspath_to_system_file_is_frozen(crf):
    obj = _MutatingPath(crf.good, PASSWD)
    tagger = crf.cls()
    tagger.set_model_file(obj)
    assert obj.calls == 1 and tagger._model_file == crf.good


def test_crf_unfrozen_loader_would_open_the_outside_file(crf, monkeypatch):
    """Negative control: hand the loader the ORIGINAL object (the pre-fix shape)
    and pycrfsuite opens the outside plant, reported by its distinct header
    error. This is the leak the frozen-string test above stands guard over."""
    import nltk.tag.crf as crf_mod

    def unfrozen(self, model_file):
        crf_mod.validate_tool_path(
            model_file,
            context="neutered",
            max_bytes=crf_mod.MAX_TOOL_MODEL_BYTES,
            require_private=True,
        )
        self._model_file = model_file
        self._tagger.open(model_file)

    monkeypatch.setattr(crf.cls, "set_model_file", unfrozen)
    plant = _truncated_header_plant(crf)
    with pytest.raises(ValueError, match="complete header"):
        crf.cls().set_model_file(_MutatingPath(crf.good, plant))


def test_crf_guard_removed_lets_the_outside_model_load(crf, monkeypatch):
    """Negative control: with the guard a pass-through, the outside plant loads
    and tags, so the refusal matrix above is the guard's doing."""
    import nltk.tag.crf as crf_mod

    monkeypatch.setattr(crf_mod, "validate_tool_path", lambda path, *a, **k: path)
    tagger = crf.cls()
    tagger.set_model_file(crf.planted)
    assert tagger._model_file == crf.planted
    assert [word for word, _ in tagger.tag(_SENT)] == _SENT


# --- CRFTagger.train: the native WRITE sink --------------------------------------


def test_crf_train_outside_destination_is_refused_and_not_created(crf):
    target = os.path.join(crf.outside, "new.crf")
    with pytest.raises(PermissionError) as info:
        crf.cls().train(_TRAIN, target)
    assert _is_security(info.value)
    assert not os.path.exists(target)


@pytest.mark.parametrize(
    "vector",
    [
        pytest.param(lambda c: _traversal(c, "t.crf"), id="dotdot-traversal"),
        pytest.param(lambda c: os.path.join(c.root, "n" + NUL + ".crf"), id="nul"),
        pytest.param(lambda c: "-o", id="option-shaped"),
        pytest.param(lambda c: "   ", id="whitespace-only"),
        pytest.param(lambda c: "file://" + os.path.join(c.root, "u.crf"), id="url"),
        pytest.param(lambda c: c.root, id="directory"),
        pytest.param(lambda c: _fifo(c, "fifo.crf"), id="fifo", marks=POSIX_ONLY),
    ],
)
def test_crf_train_hostile_destination_is_refused(crf, vector):
    with pytest.raises((PermissionError, ValueError)) as info:
        crf.cls().train(_TRAIN, vector(crf))
    assert _is_security(info.value)


@POSIX_ONLY
def test_crf_train_refuses_a_hardlinked_victim_and_leaves_it_intact(crf):
    victim = _reg(os.path.join(crf.outside, "victim.crf"), b"untouched")
    link = _hardlink(crf, "hard_victim.crf", victim)
    with pytest.raises(PermissionError) as info:
        crf.cls().train(_TRAIN, link)
    assert _is_security(info.value)
    assert pathlib.Path(victim).read_bytes() == b"untouched"


@POSIX_ONLY
def test_crf_train_refuses_a_symlinked_victim_and_leaves_it_intact(crf):
    victim = _reg(os.path.join(crf.outside, "victim.crf"), b"untouched")
    link = _symlink(crf, "link_victim.crf", victim)
    with pytest.raises(PermissionError) as info:
        crf.cls().train(_TRAIN, link)
    assert _is_security(info.value)
    assert pathlib.Path(victim).read_bytes() == b"untouched"


def test_crf_train_mutating_destination_writes_only_the_checked_path(crf):
    """The trainer gets the checked str: the object is resolved once and the
    outside spelling it answers afterwards is never written."""
    inside = os.path.join(crf.root, "mm.crf")
    outside = os.path.join(crf.outside, "mm.crf")
    obj = _MutatingPath(inside, outside)
    crf.cls().train(_TRAIN, obj)
    assert obj.calls == 1
    assert os.path.isfile(inside) and not os.path.exists(outside)


def test_crf_train_marks_the_destination_as_a_write():
    """``for_write`` is what refuses a hardlinked target on Windows, where the
    O_NOFOLLOW/fstat path is unavailable, so its presence is pinned in source."""
    pytest.importorskip("pycrfsuite")
    from nltk.tag.crf import CRFTagger

    source = inspect.getsource(CRFTagger.train)
    assert "for_write=True" in source
    assert "model_file = validate_tool_path(" in source


# =========================================================================== #
# 2. StanfordTagger: real find_file and guards, java trapped
# =========================================================================== #
@pytest.fixture
def stanford(atk):
    import nltk.tag.stanford as st

    atk.mod = st
    atk.sink = _trap_java(atk.monkeypatch, st)
    atk.jar = _reg(
        os.path.join(atk.root, "stanford-postagger.jar"), b"PK\x05\x06" + bytes(18)
    )
    atk.model = _reg(os.path.join(atk.root, "english.tagger"), b"model", 0o644)
    atk.planted = _reg(os.path.join(atk.outside, "planted.tagger"), b"model", 0o644)
    atk.keep = []
    return atk


def _tag(s, model, env=None):
    if env is not None:
        s.monkeypatch.setenv("STANFORD_MODELS", env)
    tagger = s.mod.StanfordPOSTagger(model, path_to_jar=s.jar)
    return tagger.tag(["hello"])


_STANFORD_SECURITY_REFUSED = [
    pytest.param(lambda s: PASSWD, id="absolute-system-file"),
    pytest.param(lambda s: s.planted, id="planted-outside-root"),
    pytest.param(lambda s: _traversal(s, "planted.tagger"), id="dotdot-traversal"),
    pytest.param(
        lambda s: _symlink(s, "l_out.tagger", s.planted),
        id="symlink-in-root-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _symlink(s, "l_in.tagger", s.model),
        id="symlink-in-root-to-in-root",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _through_symlinked_dir(s, "planted.tagger"),
        id="symlinked-intermediate-dir",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _hardlink(s, "h_out.tagger", s.planted),
        id="hardlink-in-root-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "t\t.tagger")),
        id="tab-in-existing-name",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "x.tagger.")),
        id="trailing-dot-existing-file",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _sparse(os.path.join(s.root, "big.tagger"), MAX_TOOL_MODEL_BYTES + 1),
        id="oversize-real-ceiling-plus-one",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "ww.tagger"), mode=0o666),
        id="world-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "gw.tagger"), mode=0o664),
        id="group-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda s: _LyingStr(s.planted), id="lying-str-outside"),
    pytest.param(
        lambda s: s.monkeypatch.setenv("STANFORD_MODELS", "/etc") or "passwd",
        id="env-search-path-outside-root-bare-name",
    ),
    pytest.param(
        lambda s: s.monkeypatch.setenv("STANFORD_MODELS", s.outside)
        or "planted.tagger",
        id="env-search-path-outside-root-planted",
    ),
]


@pytest.mark.parametrize("vector", _STANFORD_SECURITY_REFUSED)
def test_stanford_hostile_model_is_security_refused_before_the_jvm(stanford, vector):
    with pytest.raises((PermissionError, ValueError)) as info:
        _tag(stanford, vector(stanford))
    assert _is_security(info.value), info.value
    assert "cmd" not in stanford.sink


_STANFORD_NEVER_FOUND = [
    pytest.param(lambda s: _fifo(s, "fifo.tagger"), id="fifo", marks=POSIX_ONLY),
    pytest.param(lambda s: _unix_socket(s, "s.tagger"), id="socket", marks=POSIX_ONLY),
    pytest.param(lambda s: s.root, id="directory"),
    pytest.param(lambda s: "/dev/null", id="device", marks=POSIX_ONLY),
    pytest.param(lambda s: s.model + NUL, id="nul"),
    pytest.param(lambda s: "file://" + PASSWD, id="url"),
    pytest.param(lambda s: "//srv/share/m.tagger", id="unc"),
    pytest.param(lambda s: "~/x.tagger", id="tilde"),
    pytest.param(lambda s: "", id="empty"),
    pytest.param(lambda s: "-model", id="option-shaped"),
    pytest.param(lambda s: None, id="none"),
    pytest.param(lambda s: s.model.encode(), id="bytes"),
    pytest.param(lambda s: _MutatingPath(s.model, s.planted), id="mutating-pathlike"),
]


@pytest.mark.parametrize("vector", _STANFORD_NEVER_FOUND)
def test_stanford_unresolvable_model_never_reaches_the_jvm(stanford, vector):
    """``find_file`` only yields an existing regular file it was given as a str;
    everything else fails discovery, and nothing is handed to the JVM."""
    with pytest.raises(Exception) as info:
        _tag(stanford, vector(stanford))
    assert not isinstance(info.value, _ReachedJVM)
    assert "cmd" not in stanford.sink


_STANFORD_BENIGN = [
    pytest.param(lambda s: s.model, id="plain-str"),
    pytest.param(lambda s: _LyingStr(s.model), id="lying-str-in-root"),
    pytest.param(
        lambda s: s.monkeypatch.setenv("STANFORD_MODELS", s.root) or "english.tagger",
        id="env-search-path-in-root",
    ),
    pytest.param(
        lambda s: _sparse(os.path.join(s.root, "edge.tagger"), MAX_TOOL_MODEL_BYTES),
        id="exactly-the-ceiling",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "p600.tagger"), mode=0o600),
        id="mode-0600",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _reg(os.path.join(s.root, "e" + ESC + ".tagger"), mode=0o644),
        id="esc-in-name",
        marks=POSIX_ONLY,
    ),
]


@pytest.mark.parametrize("vector", _STANFORD_BENIGN)
def test_stanford_benign_model_reaches_the_jvm_as_the_checked_str(stanford, vector):
    model = vector(stanford)
    with pytest.raises(_ReachedJVM):
        _tag(stanford, model)
    handed = _argv_value(stanford.sink["cmd"], "-model")
    assert type(handed) is str
    assert os.path.realpath(handed).startswith(stanford.root + os.sep)
    if isinstance(model, str):
        assert handed == str.__str__(model) or handed.endswith(model)


@POSIX_ONLY
def test_stanford_model_made_tamperable_after_init_is_refused_at_tag_time(stanford):
    tagger = stanford.mod.StanfordPOSTagger(stanford.model, path_to_jar=stanford.jar)
    os.chmod(stanford.model, 0o666)
    with pytest.raises(PermissionError) as info:
        tagger.tag(["x"])
    assert _is_security(info.value)
    assert "cmd" not in stanford.sink


def test_stanford_model_attribute_swapped_after_init_is_refused_at_tag_time(stanford):
    tagger = stanford.mod.StanfordPOSTagger(stanford.model, path_to_jar=stanford.jar)
    tagger._stanford_model = stanford.planted
    with pytest.raises(PermissionError) as info:
        tagger.tag(["x"])
    assert _is_security(info.value)
    assert "cmd" not in stanford.sink


def test_stanford_model_attribute_pathlike_is_frozen_before_cmd_is_built(stanford):
    """``tag_sents`` re-validates and stores the checked str BEFORE ``_cmd``
    reads the attribute, so a re-resolving object never reaches the argv."""
    tagger = stanford.mod.StanfordPOSTagger(stanford.model, path_to_jar=stanford.jar)
    obj = _MutatingPath(stanford.model, stanford.planted)
    tagger._stanford_model = obj
    with pytest.raises(_ReachedJVM):
        tagger.tag(["x"])
    handed = _argv_value(stanford.sink["cmd"], "-model")
    assert handed == stanford.model and type(handed) is str
    assert obj.calls == 1
    assert tagger._stanford_model == stanford.model


def test_stanford_guard_removed_lets_the_swap_reach_the_jvm(stanford):
    """Negative control: a pass-through guard and the outside model reaches
    argv, so the tag-time refusal above is the guard's doing."""
    tagger = stanford.mod.StanfordPOSTagger(stanford.model, path_to_jar=stanford.jar)
    stanford.monkeypatch.setattr(
        stanford.mod, "validate_tool_path", lambda path, *a, **k: path
    )
    tagger._stanford_model = stanford.planted
    with pytest.raises(_ReachedJVM):
        tagger.tag(["x"])
    assert _argv_value(stanford.sink["cmd"], "-model") == stanford.planted


def test_stanford_unfrozen_guard_lets_the_object_reach_the_jvm(stanford):
    """Negative control for the freeze: a guard that validates but returns the
    caller's object puts a re-resolving PathLike in argv, and the child would
    open the outside path. The frozen-str test above stands guard over this."""
    real = stanford.mod.validate_tool_path
    tagger = stanford.mod.StanfordPOSTagger(stanford.model, path_to_jar=stanford.jar)

    def validating_but_unfrozen(path, *a, **k):
        real(path, *a, **k)
        return path

    stanford.monkeypatch.setattr(
        stanford.mod, "validate_tool_path", validating_but_unfrozen
    )
    tagger._stanford_model = _MutatingPath(stanford.model, stanford.planted)
    with pytest.raises(_ReachedJVM):
        tagger.tag(["x"])
    handed = _argv_value(stanford.sink["cmd"], "-model")
    assert type(handed) is not str
    assert os.fspath(handed) == stanford.planted


def test_stanford_freeze_is_pinned_in_source():
    from nltk.tag.stanford import StanfordTagger

    init_src = inspect.getsource(StanfordTagger.__init__)
    tag_src = inspect.getsource(StanfordTagger.tag_sents)
    for src in (init_src, tag_src):
        assert "self._stanford_model = validate_tool_path(" in src
    assert tag_src.index("validate_tool_path(") < tag_src.index("list(self._cmd)")


# =========================================================================== #
# 3. StanfordSegmenter: real __init__ and guards, java trapped
# =========================================================================== #
@pytest.fixture
def segmenter(atk):
    import nltk.tokenize.stanford_segmenter as seg

    atk.mod = seg
    atk.sink = _trap_java(atk.monkeypatch, seg)
    atk.jar = _reg(
        os.path.join(atk.root, "stanford-segmenter.jar"), b"PK\x05\x06" + bytes(18)
    )
    digest = hashlib.sha256(pathlib.Path(atk.jar).read_bytes()).hexdigest()
    atk.monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)
    atk.model = _reg(os.path.join(atk.root, "pku.gz"), b"\x1f\x8bm", 0o644)
    atk.dictionary = _reg(os.path.join(atk.root, "dict.ser.gz"), b"\x1f\x8bd", 0o644)
    atk.sihan = _private_dir(os.path.join(atk.root, "data"))
    _reg(os.path.join(atk.sihan, "norm.simp.utf8"), b"n", 0o644)
    _private_dir(os.path.join(atk.sihan, "dict"))
    _reg(os.path.join(atk.sihan, "dict", "character_list"), b"c", 0o644)
    atk.infile = _reg(os.path.join(atk.root, "in.txt"), ZH.encode("utf-8"), 0o644)
    atk.planted = _reg(os.path.join(atk.outside, "planted.gz"), b"\x1f\x8bp", 0o644)
    atk.keep = []
    return atk


_UNSET = object()
_CRF_CLASSIFIER = "edu.stanford.nlp.ie.crf.CRFClassifier"


def _segment(s, model=_UNSET, dictionary=None, sihan=None, options=None):
    tool = s.mod.StanfordSegmenter(
        path_to_jar=s.jar,
        java_class=_CRF_CLASSIFIER,
        path_to_model=s.model if model is _UNSET else model,
        path_to_dict=dictionary,
        path_to_sihan_corpora_dict=sihan,
        options=options,
    )
    return tool.segment_file(s.infile)


_SEG_FILE_VECTORS = [
    pytest.param(lambda s, n: s.planted, id="planted-outside-root"),
    pytest.param(lambda s, n: PASSWD, id="absolute-system-file"),
    pytest.param(lambda s, n: _traversal(s, "planted.gz"), id="dotdot-traversal"),
    pytest.param(
        lambda s, n: _symlink(s, f"l_out_{n}.gz", s.planted),
        id="symlink-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s, n: _symlink(s, f"l_in_{n}.gz", s.model),
        id="symlink-to-in-root",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s, n: _hardlink(s, f"h_out_{n}.gz", s.planted),
        id="hardlink-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda s, n: _fifo(s, f"fifo_{n}.gz"), id="fifo", marks=POSIX_ONLY),
    pytest.param(lambda s, n: s.root, id="directory"),
    pytest.param(lambda s, n: s.model + NUL, id="nul"),
    pytest.param(lambda s, n: os.path.join(s.root, "t\t.gz"), id="tab-in-name"),
    pytest.param(lambda s, n: "file://" + PASSWD, id="url"),
    pytest.param(lambda s, n: "//srv/share/m.gz", id="unc"),
    pytest.param(lambda s, n: "~/pku.gz", id="tilde"),
    pytest.param(lambda s, n: "-loadClassifier", id="option-shaped"),
    pytest.param(lambda s, n: s.model + ".", id="trailing-dot"),
    pytest.param(
        lambda s, n: _sparse(
            os.path.join(s.root, f"big_{n}.gz"), MAX_TOOL_MODEL_BYTES + 1
        ),
        id="oversize-real-ceiling-plus-one",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s, n: _reg(os.path.join(s.root, f"ww_{n}.gz"), mode=0o666),
        id="world-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s, n: _reg(os.path.join(s.root, f"gw_{n}.gz"), mode=0o664),
        id="group-writable",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda s, n: _LyingStr(s.planted), id="lying-str-outside"),
    pytest.param(lambda s, n: s.planted.encode(), id="bytes-outside"),
    pytest.param(
        lambda s, n: _MutatingPath(s.planted, s.model), id="mutating-hostile-first"
    ),
]


@pytest.mark.parametrize("slot", ["model", "dictionary"])
@pytest.mark.parametrize("vector", _SEG_FILE_VECTORS)
def test_segmenter_hostile_file_is_security_refused_before_the_jvm(
    segmenter, slot, vector
):
    with pytest.raises((PermissionError, ValueError)) as info:
        _segment(segmenter, **{slot: vector(segmenter, slot)})
    assert _is_security(info.value), info.value
    assert "cmd" not in segmenter.sink


def test_segmenter_benign_model_dict_and_sihan_reach_the_jvm(segmenter):
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=segmenter.sihan)
    argv = segmenter.sink["cmd"]
    assert _argv_value(argv, "-loadClassifier") == segmenter.model
    assert _argv_value(argv, "-serDictionary") == segmenter.dictionary
    assert _argv_value(argv, "-sighanCorporaDict") == segmenter.sihan
    assert _argv_value(argv, "-textFile") == segmenter.infile


@pytest.mark.parametrize(
    "vector",
    [
        pytest.param(lambda s: s.model.encode(), id="bytes-in-root"),
        pytest.param(lambda s: pathlib.Path(s.model), id="pathlib-path"),
        pytest.param(lambda s: _LyingStr(s.model), id="lying-str-in-root"),
        pytest.param(
            lambda s: _sparse(os.path.join(s.root, "edge.gz"), MAX_TOOL_MODEL_BYTES),
            id="exactly-the-ceiling",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda s: _reg(os.path.join(s.root, "p600.gz"), mode=0o600),
            id="mode-0600",
            marks=POSIX_ONLY,
        ),
    ],
)
def test_segmenter_benign_model_spelling_reaches_the_jvm_as_str(segmenter, vector):
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, model=vector(segmenter))
    handed = _argv_value(segmenter.sink["cmd"], "-loadClassifier")
    assert type(handed) is str
    assert os.path.realpath(handed).startswith(segmenter.root + os.sep)


@pytest.mark.parametrize("slot", ["model", "dictionary"])
def test_segmenter_mutating_pathlike_file_is_frozen(segmenter, slot):
    obj = _MutatingPath(segmenter.dictionary, segmenter.planted)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, **{slot: obj})
    flag = "-loadClassifier" if slot == "model" else "-serDictionary"
    if slot == "dictionary":
        # the dictionary is only emitted alongside a sihan dir
        assert flag not in segmenter.sink["cmd"]
    else:
        assert _argv_value(segmenter.sink["cmd"], flag) == segmenter.dictionary
    assert obj.calls == 1
    assert segmenter.planted not in [_fspath(a) for a in segmenter.sink["cmd"]]


# --- the Sihan corpora dict: a DIRECTORY the JVM reads files from ----------------


def _ww_dir(s, name, mode=0o777):
    path = os.path.join(s.root, name)
    os.mkdir(path)
    os.chmod(path, mode)
    return path


def _dir_with(s, name, plant):
    path = _private_dir(os.path.join(s.root, name))
    plant(path)
    return path


_SIHAN_REFUSED = [
    pytest.param(lambda s: s.outside, id="outside-dir"),
    pytest.param(lambda s: "/etc", id="system-dir"),
    pytest.param(
        lambda s: os.path.join(s.root, "..", os.path.basename(s.outside)),
        id="dotdot-traversal",
    ),
    pytest.param(
        lambda s: _symlink(s, "dirlink_out", s.outside),
        id="symlink-dir-to-outside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _symlink(s, "dirlink_in", s.sihan),
        id="symlink-leaf-to-in-root-dir",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _ww_dir(s, "ww_data", 0o777),
        id="world-writable-dir",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _ww_dir(s, "gw_data", 0o775),
        id="group-writable-dir",
        marks=POSIX_ONLY,
    ),
    pytest.param(lambda s: s.model, id="regular-file-not-a-dir"),
    pytest.param(lambda s: _fifo(s, "fifo_dir"), id="fifo-not-a-dir", marks=POSIX_ONLY),
    pytest.param(lambda s: os.path.join(s.root, "missing"), id="nonexistent"),
    pytest.param(lambda s: s.sihan + NUL, id="nul"),
    pytest.param(lambda s: "-sighanCorporaDict", id="option-shaped"),
    pytest.param(lambda s: "file://" + s.sihan, id="url"),
    pytest.param(
        lambda s: _dir_with(
            s, "d_wwfile", lambda d: _reg(os.path.join(d, "f"), mode=0o666)
        ),
        id="world-writable-file-inside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _dir_with(
            s, "d_gwfile", lambda d: _reg(os.path.join(d, "f"), mode=0o664)
        ),
        id="group-writable-file-inside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _dir_with(
            s, "d_link", lambda d: os.symlink(PASSWD, os.path.join(d, "f"))
        ),
        id="symlink-inside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _dir_with(s, "d_fifo", lambda d: os.mkfifo(os.path.join(d, "f"))),
        id="fifo-inside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _dir_with(s, "d_wwsub", lambda d: _ww_dir(s, "d_wwsub/sub", 0o777)),
        id="world-writable-subdir-inside",
        marks=POSIX_ONLY,
    ),
    pytest.param(
        lambda s: _dir_with(
            s,
            "d_deep",
            lambda d: (
                _private_dir(os.path.join(d, "a", "b")),
                _reg(os.path.join(d, "a", "b", "f"), mode=0o666),
            ),
        ),
        id="world-writable-file-two-levels-down",
        marks=POSIX_ONLY,
    ),
]


@pytest.mark.parametrize("vector", _SIHAN_REFUSED)
def test_segmenter_hostile_sihan_dir_is_security_refused_before_the_jvm(
    segmenter, vector
):
    with pytest.raises((PermissionError, ValueError)) as info:
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=vector(segmenter))
    assert _is_security(info.value), info.value
    assert "cmd" not in segmenter.sink


@pytest.mark.parametrize(
    "vector",
    [
        pytest.param(lambda s: s.sihan, id="private-dir"),
        pytest.param(lambda s: s.sihan + os.sep, id="trailing-separator"),
        pytest.param(
            lambda s: os.path.join(s.root, ".", "data") + os.sep,
            id="default-config-shape",
        ),
        pytest.param(lambda s: pathlib.Path(s.sihan), id="pathlib-path"),
        pytest.param(
            lambda s: _private_dir(os.path.join(s.root, "empty")),
            id="empty-private-dir",
        ),
        pytest.param(
            lambda s: _dir_with(
                s, "d_ro", lambda d: _reg(os.path.join(d, "f"), mode=0o444)
            ),
            id="read-only-file-inside",
            marks=POSIX_ONLY,
        ),
    ],
)
def test_segmenter_benign_sihan_dir_reaches_the_jvm(segmenter, vector):
    sihan = vector(segmenter)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=sihan)
    handed = _argv_value(segmenter.sink["cmd"], "-sighanCorporaDict")
    assert type(handed) is str
    assert os.path.realpath(handed) == os.path.realpath(
        segmenter.root + os.sep + os.path.relpath(os.fspath(sihan), segmenter.root)
    )


def test_segmenter_mutating_pathlike_sihan_is_frozen(segmenter):
    obj = _MutatingPath(segmenter.sihan, segmenter.outside)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=obj)
    assert _argv_value(segmenter.sink["cmd"], "-sighanCorporaDict") == segmenter.sihan
    assert obj.calls == 1


@POSIX_ONLY
def test_segmenter_sihan_dir_over_the_entry_cap_is_refused(segmenter):
    """The private-tree audit is bounded: past the cap the dir is refused rather
    than walked without limit (a tiny monkeypatched cap stands in for 10000)."""
    big = _private_dir(os.path.join(segmenter.root, "big_data"))
    for i in range(6):
        _reg(os.path.join(big, f"f{i}"), mode=0o644)
    segmenter.monkeypatch.setattr(pathsec, "MAX_TOOL_DIR_ENTRIES", 5)
    with pytest.raises(PermissionError, match="too many"):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=big)
    segmenter.monkeypatch.setattr(pathsec, "MAX_TOOL_DIR_ENTRIES", 6)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=big)


@POSIX_ONLY
def test_segmenter_sihan_private_check_removed_lets_the_tamperable_dir_through(
    segmenter,
):
    """Negative control: drop ``require_private`` from the directory guard and
    a world-writable Sihan dir reaches the JVM, so the refusal is that check."""
    real = segmenter.mod.validate_tool_dir
    segmenter.monkeypatch.setattr(
        segmenter.mod,
        "validate_tool_dir",
        lambda path, context="NLTK tool", **k: real(path, context=context),
    )
    tamperable = _ww_dir(segmenter, "ww_data", 0o777)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, dictionary=segmenter.dictionary, sihan=tamperable)
    assert _argv_value(segmenter.sink["cmd"], "-sighanCorporaDict") == tamperable


# --- options=: one comma-joined argv element with path-valued entries -----------


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(lambda s: s.planted, id="plain-str-outside"),
        pytest.param(lambda s: _LyingStr(s.planted), id="lying-str-outside"),
        pytest.param(lambda s: pathlib.Path(s.planted), id="pathlib-outside"),
        pytest.param(lambda s: s.planted.encode(), id="bytes-outside"),
        pytest.param(lambda s: PASSWD, id="absolute-system-file"),
        pytest.param(lambda s: _traversal(s, "planted.gz"), id="dotdot-traversal"),
        pytest.param(lambda s: "file://" + PASSWD, id="url"),
        pytest.param(lambda s: "~/x.gz", id="tilde"),
        pytest.param(
            lambda s: _MutatingPath(s.planted, s.dictionary),
            id="mutating-hostile-first",
        ),
        pytest.param(
            lambda s: _symlink(s, "opt_link.gz", s.planted),
            id="symlink-to-outside",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda s: _reg(os.path.join(s.root, "opt_ww.gz"), mode=0o666),
            id="world-writable",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda s: _sparse(
                os.path.join(s.root, "opt_big.gz"), MAX_TOOL_MODEL_BYTES + 1
            ),
            id="oversize-real-ceiling-plus-one",
            marks=POSIX_ONLY,
        ),
        pytest.param(lambda s: _fifo(s, "opt_fifo.gz"), id="fifo", marks=POSIX_ONLY),
        pytest.param(lambda s: s.root, id="directory"),
    ],
)
def test_segmenter_hostile_option_value_is_security_refused_end_to_end(
    segmenter, value
):
    """Through the real ``__init__``: the value is materialised to its real
    characters before the path-shape test, so a lying str subclass, a PathLike
    or bytes naming an outside file is refused like a plain str."""
    with pytest.raises((PermissionError, ValueError)) as info:
        _segment(segmenter, options={"serDictionary": value(segmenter)})
    assert _is_security(info.value), info.value
    assert "cmd" not in segmenter.sink


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(lambda s: s.dictionary, id="plain-str-in-root"),
        pytest.param(lambda s: pathlib.Path(s.dictionary), id="pathlib-in-root"),
        pytest.param(lambda s: s.dictionary.encode(), id="bytes-in-root"),
        pytest.param(lambda s: _LyingStr(s.dictionary), id="lying-str-in-root"),
        pytest.param(
            lambda s: _MutatingPath(s.dictionary, s.planted), id="mutating-benign-first"
        ),
    ],
)
def test_segmenter_benign_option_path_reaches_the_jvm_as_the_checked_str(
    segmenter, value
):
    obj = value(segmenter)
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, options={"serDictionary": obj})
    options = _argv_value(segmenter.sink["cmd"], "-options")
    assert options == f'serDictionary="{segmenter.dictionary}"'
    if isinstance(obj, _MutatingPath):
        assert obj.calls == 1


def test_segmenter_bare_option_values_pass_through_as_resource_names(segmenter):
    """Documented residual: a separator-free value is a name the JVM resolves
    itself, exactly the allowance ``validate_model_resource`` makes."""
    with pytest.raises(_ReachedJVM):
        _segment(
            segmenter,
            options={"serDictionary": "dict-chris6.ser.gz", "normalizeSpace": True},
        )
    options = _argv_value(segmenter.sink["cmd"], "-options")
    assert options == 'serDictionary="dict-chris6.ser.gz",normalizeSpace=true'


def test_segmenter_option_guard_removed_lets_the_lying_str_reach_the_jvm(segmenter):
    """Negative control: with a pass-through path guard the lying str's outside
    path lands in ``-options``, the leak the materialisation now prevents."""
    segmenter.monkeypatch.setattr(
        segmenter.mod, "validate_tool_path", lambda path, *a, **k: path
    )
    with pytest.raises(_ReachedJVM):
        _segment(segmenter, options={"serDictionary": _LyingStr(segmenter.planted)})
    assert segmenter.planted in _argv_value(segmenter.sink["cmd"], "-options")


def test_segmenter_option_materialisation_is_pinned_in_source():
    from nltk.tokenize.stanford_segmenter import _validated_options

    source = inspect.getsource(_validated_options)
    assert "str.__str__(os.fsdecode(value))" in source
    assert source.index("os.fsdecode") < source.index("validate_tool_path(")


# =========================================================================== #
# 4. validate_tool_dir(require_private=True) at the guard level
# =========================================================================== #
@pytest.fixture
def tool_dir(atk):
    atk.good = _private_dir(os.path.join(atk.root, "corpora"))
    _reg(os.path.join(atk.good, "a.txt"), mode=0o644)
    _private_dir(os.path.join(atk.good, "sub"))
    _reg(os.path.join(atk.good, "sub", "b.txt"), mode=0o600)
    return atk


def test_tool_dir_private_tree_passes_and_returns_the_str(tool_dir):
    out = pathsec.validate_tool_dir(
        pathlib.Path(tool_dir.good), context="t", require_private=True
    )
    assert out == tool_dir.good and type(out) is str


def test_tool_dir_without_require_private_keeps_the_old_contract(tool_dir):
    """The write-destination callers (perceptron, named_entity) are unchanged:
    a missing directory is still accepted without the flag."""
    missing = os.path.join(tool_dir.root, "to_be_created")
    assert pathsec.validate_tool_dir(missing, context="t") == missing
    with pytest.raises(PermissionError, match="does not exist"):
        pathsec.validate_tool_dir(missing, context="t", require_private=True)


@pytest.mark.parametrize(
    ("plant", "why"),
    [
        pytest.param(
            lambda d: _reg(os.path.join(d.root, "f"), mode=0o644),
            "not a directory",
            id="file",
        ),
        pytest.param(
            lambda d: os.path.join(d.root, "missing"), "does not exist", id="missing"
        ),
        pytest.param(
            lambda d: (
                os.symlink(d.good, os.path.join(d.root, "lnk")),
                os.path.join(d.root, "lnk"),
            )[1],
            "is a symlink",
            id="symlink-leaf",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda d: (os.chmod(d.good, 0o777), d.good)[1],
            "group/world-writable",
            id="world-writable-dir",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda d: (os.chmod(os.path.join(d.good, "sub"), 0o775), d.good)[1],
            "group/world-writable",
            id="group-writable-subdir",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda d: (os.chmod(os.path.join(d.good, "sub", "b.txt"), 0o666), d.good)[
                1
            ],
            "group/world-writable",
            id="world-writable-nested-file",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda d: (os.symlink(PASSWD, os.path.join(d.good, "lnk")), d.good)[1],
            "symlink inside",
            id="symlink-inside",
            marks=POSIX_ONLY,
        ),
        pytest.param(
            lambda d: (os.mkfifo(os.path.join(d.good, "fifo")), d.good)[1],
            "not a regular file or directory",
            id="fifo-inside",
            marks=POSIX_ONLY,
        ),
    ],
)
def test_tool_dir_require_private_refusals(tool_dir, plant, why):
    with pytest.raises(PermissionError, match=why) as info:
        pathsec.validate_tool_dir(plant(tool_dir), context="t", require_private=True)
    assert _is_security(info.value)


@POSIX_ONLY
def test_tool_dir_private_audit_is_gated_by_enforce(tool_dir):
    """Documented negative control: like every physical check in pathsec the
    audit is an ENFORCE-mode refusal, so switching ENFORCE off lets it through."""
    os.chmod(tool_dir.good, 0o777)
    with pytest.raises(PermissionError):
        pathsec.validate_tool_dir(tool_dir.good, context="t", require_private=True)
    tool_dir.monkeypatch.setattr(pathsec, "ENFORCE", False)
    assert (
        pathsec.validate_tool_dir(tool_dir.good, context="t", require_private=True)
        == tool_dir.good
    )


def test_tool_dir_entry_cap_is_enforced(tool_dir):
    tool_dir.monkeypatch.setattr(pathsec, "MAX_TOOL_DIR_ENTRIES", 2)
    with pytest.raises(PermissionError, match="too many"):
        pathsec.validate_tool_dir(tool_dir.good, context="t", require_private=True)


# =========================================================================== #
# 5. Real tools inside a data root (skipped where absent)
# =========================================================================== #
def _find_in_roots(pattern):
    hits = []
    for root in nltk.data.path:
        if isinstance(root, str):
            hits += glob.glob(os.path.join(root, *pattern))
    return sorted(hits)


def _real_tagger_install():
    """(jar, model) of a Stanford POS tagger inside a data root, else None; the
    wrapper bounds its model to the roots, so an install elsewhere is refused
    by design and is not this test's subject."""
    for home in _find_in_roots(("stanford-postagger*",)):
        jars = [
            j
            for j in glob.glob(os.path.join(home, "stanford-postagger*.jar"))
            if not j.endswith(("-sources.jar", "-javadoc.jar"))
        ]
        model = os.path.join(home, "models", "english-left3words-distsim.tagger")
        if jars and os.path.isfile(model):
            return jars[0], model
    return None


def _real_segmenter_install():
    for home in _find_in_roots(("stanford-segmenter*",)):
        jars = [
            j
            for j in glob.glob(os.path.join(home, "stanford-segmenter*.jar"))
            if not j.endswith(("-sources.jar", "-javadoc.jar"))
        ]
        data = os.path.join(home, "data")
        if jars and os.path.isfile(os.path.join(data, "pku.gz")):
            return jars[0], data
    return None


def _configure_java(monkeypatch):
    jdk = "/Users/alvas/nltk_tools/jdk/jdk-21.0.12.1+1/Contents/Home"
    if not os.environ.get("JAVA_HOME") and os.path.isdir(jdk):
        monkeypatch.setenv("JAVA_HOME", jdk)
    monkeypatch.setattr(internals, "_java_bin", None)


def _private_staging_copy(staging, source, mode=0o600):
    target = os.path.join(staging, os.path.basename(source))
    shutil.copyfile(source, target)
    os.chmod(target, mode)
    return target


def test_real_stanford_tagger_private_copy_tags_and_tamperable_copy_is_refused(
    monkeypatch,
):
    """Executed for real: the tagging is the tool, the refusals are the guard.
    The model is staged as a private copy because a stock unzip may leave the
    distribution group-writable, which ``require_private`` refuses by design."""
    from nltk.tag.stanford import StanfordPOSTagger

    install = _real_tagger_install()
    if install is None:
        pytest.skip("no Stanford POS tagger install inside a data root")
    jar, stock = install
    _configure_java(monkeypatch)
    staging = nltk.data.make_staging_dir(prefix="nltk_modelfiles_", cleanup=True)
    model = _private_staging_copy(staging, stock)
    try:
        tagger = StanfordPOSTagger(model, jar, java_options="-mx1g")
        tagged = tagger.tag("What is the airspeed of an unladen swallow ?".split())
    except (LookupError, OSError) as exc:
        pytest.skip(f"Stanford POS tagger not usable here: {exc}")
    assert [
        word for word, _ in tagged
    ] == "What is the airspeed of an unladen swallow ?".split()
    assert ("What", "WP") in tagged and ("is", "VBZ") in tagged
    assert tagger._stanford_model == model

    if os.name == "posix":
        tamperable = _private_staging_copy(staging, stock, mode=0o666)
        with pytest.raises(PermissionError, match="Security Violation"):
            StanfordPOSTagger(tamperable, jar, java_options="-mx1g")
        oversize = _sparse(
            os.path.join(staging, "huge.tagger"), MAX_TOOL_MODEL_BYTES + 1
        )
        with pytest.raises(PermissionError, match="tool-model limit"):
            StanfordPOSTagger(oversize, jar, java_options="-mx1g")


def test_real_stanford_segmenter_segments_through_the_guards(monkeypatch):
    """Executed for real with the Chinese model, dictionary and Sihan corpora
    dir of an install inside a data root; a tamperable copy of the dictionary
    is refused on the same real JVM path."""
    from nltk.tokenize.stanford_segmenter import StanfordSegmenter

    install = _real_segmenter_install()
    if install is None:
        pytest.skip("no Stanford segmenter install inside a data root")
    jar, data = install
    _configure_java(monkeypatch)
    digest = hashlib.sha256(pathlib.Path(jar).read_bytes()).hexdigest()
    monkeypatch.setenv("NLTK_SEGMENTER_ALLOW_SHA256", digest)
    sentence = "".join(
        chr(c) for c in (0x8FD9, 0x662F, 0x65AF, 0x5766, 0x798F, 0x4E2D, 0x6587)
    )
    seg = StanfordSegmenter(
        path_to_jar=jar,
        java_class=_CRF_CLASSIFIER,
        path_to_model=os.path.join(data, "pku.gz"),
        path_to_dict=os.path.join(data, "dict-chris6.ser.gz"),
        path_to_sihan_corpora_dict=data,
        java_options="-mx2g",
    )
    try:
        out = seg.segment(sentence)
    except (LookupError, OSError, PermissionError) as exc:
        pytest.skip(f"Stanford segmenter not usable here: {exc}")
    tokens = out.split()
    assert len(tokens) >= 3 and "".join(tokens) == sentence

    if os.name == "posix":
        staging = nltk.data.make_staging_dir(prefix="nltk_modelfiles_", cleanup=True)
        tamperable = _private_staging_copy(
            staging, os.path.join(data, "dict-chris6.ser.gz"), mode=0o666
        )
        bad = StanfordSegmenter(
            path_to_jar=jar,
            java_class=_CRF_CLASSIFIER,
            path_to_model=os.path.join(data, "pku.gz"),
            path_to_dict=tamperable,
            path_to_sihan_corpora_dict=data,
            java_options="-mx2g",
        )
        with pytest.raises(PermissionError, match="Security Violation"):
            bad.segment(sentence)

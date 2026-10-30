# Natural Language Toolkit: attack tests for the model-artifact pathsec routing
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Issue #3980 ("Model-artifact APIs bypass pathsec and touch files outside
allowed roots") replayed with real calls under real enforcement, then widened.

The issue names ``TransitionParser.train`` / ``parse``,
``AveragedPerceptron.save`` / ``load``, ``PerceptronTagger.save_to_json`` and
``save_maxent_params`` as opening caller-supplied model paths with the builtin
``open``. That is true of the released 3.10.3 sdist (``transitionparser.py``
564/583, ``perceptron.py`` 178/183/351/372, ``maxent.py`` 1596-1602, whose
``tab_dir`` defaulted to ``/tmp``). On develop every one of the six already
routes through ``nltk.pathsec`` (GHSA-8mgp-746c-j5xp, #3969) and refuses an
out-of-root path with ``PermissionError`` before any byte moves; the three
negative controls the reporter names (``pathsec.open``, ``load_from_json``,
``load_maxent_params``) refuse the same paths. The first classes here pin that
disposition with real training on real data, so the six claims cannot reopen.

Widening the probe found two residual holes, both in the POSIX branch of
``PerceptronTagger.save_to_json``, which writes each parameter file relative to
a pinned directory descriptor and so could not use ``pathsec.open``:

* a hardlink planted at a parameter-file name inside an in-root ``loc`` was
  opened with ``O_TRUNC`` and the outside inode it names was truncated and
  overwritten with model weights (CWE-59), the exact escape ``pathsec.open``
  defers ``O_TRUNC`` and refuses ``st_nlink > 1`` to prevent;
* a FIFO planted at that name blocked the call forever (CWE-400), since the
  open carried no ``O_NONBLOCK`` and nothing checked the inode type.

A symlink there was refused only as a bare ``OSError(ELOOP)``. The writer now
creates each file the way ``pathsec.ZipFile._write_leaf`` does
(``O_CREAT | O_EXCL | O_NOFOLLOW``, an existing entry judged with ``lstat`` and
replaced only when it is a regular single-linked file), and the no-dir_fd
fallback goes through ``pathsec.open``. The remaining classes pin every other
vector probed (sibling-prefix roots, ``..`` through the root, relative paths
against an outside working directory, in-root FIFOs and hardlinks for the other
sinks, backslash spellings, a group-writable model dir, the parser's staging
dir) as already closed, keep the legitimate in-root flows working, and put the
old opener back to prove the new tests reach the sink.

Run::

    python -m pytest nltk/test/unit/test_attack_model_artifact_pathsec.py -q
"""

import contextlib
import json
import os
import pathlib
import shutil
import signal
import stat

import pytest

import nltk.data
from nltk import pathsec
from nltk.tag import perceptron
from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX-only path form")
DIR_FD_ROUTE_ONLY = pytest.mark.skipif(
    os.name != "posix" or not perceptron._dir_fd_write_supported(),
    reason="save_to_json writes by name through pathsec.open here, not via dir_fd",
)
CONTEXT = "PerceptronTagger.save_to_json"
LANG = "xxx"
SECRET = b"OUTSIDE-SECRET-MUST-SURVIVE\n"
TINY_TAGGED = [[("the", "DT"), ("cat", "NN"), ("sat", "VBD")]]


def _is_guard_refusal(exc):
    return str(exc).startswith("Security Violation [")


def _refused(call, *args, **kwargs):
    """Run *call*; it must be refused by a pathsec-style guard, whose message
    starts with the ``Security Violation [`` marker. Returns the exception."""
    with pytest.raises(PermissionError) as excinfo:
        call(*args, **kwargs)
    assert _is_guard_refusal(excinfo.value), excinfo.value
    return excinfo.value


def _inside(path, root):
    real = pathlib.Path(os.path.realpath(path))
    root = pathlib.Path(os.path.realpath(root))
    return real == root or root in real.parents


@contextlib.contextmanager
def _bounded(seconds=5):
    """Fail instead of hanging when a sink blocks on a planted FIFO."""

    def _alarm(signum, frame):
        raise TimeoutError(f"blocked for more than {seconds}s")

    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def _hardlink_or_skip(src, dst):
    try:
        os.link(src, dst)
    except OSError as exc:
        pytest.skip(f"cannot hardlink here: {exc}")


def _plant_secret(outside):
    secret = outside / "secret.txt"
    secret.write_bytes(SECRET)
    return secret


# Real models, trained once per module before any sandbox narrows the roots.


@pytest.fixture(scope="module")
def depgraphs():
    """A few real dependency graphs; loaded while the installed corpora are
    still visible, since the sandbox fixtures hide them."""
    pytest.importorskip("sklearn")
    pytest.importorskip("scipy")
    from nltk.corpus import dependency_treebank

    try:
        graphs = list(dependency_treebank.parsed_sents()[:4])
    except LookupError:
        pytest.skip("dependency_treebank is not installed")
    return graphs


@pytest.fixture(scope="module")
def maxent_params():
    """Parameters of a tiny real MaxentClassifier (IIS, two iterations)."""
    pytest.importorskip("numpy")
    from nltk.classify.maxent import MaxentClassifier

    train = [({"a": 1, "b": 0}, "x"), ({"a": 0, "b": 1}, "y")] * 3
    classifier = MaxentClassifier.train(train, algorithm="iis", max_iter=2, trace=0)
    encoding = classifier._encoding
    return (
        classifier.weights(),
        encoding._mapping,
        encoding._labels,
        encoding._alwayson or {},
    )


@pytest.fixture(scope="module")
def trained_tagger():
    tagger = PerceptronTagger(load=False)
    tagger.train(TINY_TAGGED, nr_iter=1)
    return tagger


@pytest.fixture
def parser(depgraphs):
    import warnings

    from nltk.parse.transitionparser import TransitionParser

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        yield TransitionParser("arc-standard")


def _train_parser(parser, depgraphs, modelfile):
    import warnings

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        parser.train(depgraphs, modelfile, verbose=False)


def _param_file(loc, attr="weights", lang=LANG):
    return os.path.join(loc, f"averaged_perceptron_tagger_{lang}.{attr}.json")


# The six claims and the reporter's negative controls, on develop


class TestIssueClaimsAreClosedOnDevelop:
    """Each API the issue names refuses an out-of-root path and leaves it
    untouched; its in-root twin works and round-trips."""

    def test_transition_parser_train_outside_is_refused(
        self, pathsec_sandbox, parser, depgraphs
    ):
        target = pathsec_sandbox.outside / "tp.model"
        exc = _refused(_train_parser, parser, depgraphs, str(target))
        assert "[TransitionParser.train]" in str(exc)
        assert not target.exists()

    def test_transition_parser_parse_outside_is_refused(
        self, pathsec_sandbox, parser, depgraphs
    ):
        inside = pathsec_sandbox.root / "tp.model"
        _train_parser(parser, depgraphs, str(inside))
        planted = pathsec_sandbox.outside / "tp.model"
        shutil.copy(str(inside), str(planted))
        exc = _refused(parser.parse, depgraphs[:1], str(planted))
        assert "[TransitionParser.parse]" in str(exc)

    def test_transition_parser_in_root_round_trip(
        self, pathsec_sandbox, parser, depgraphs
    ):
        inside = pathsec_sandbox.root / "tp.model"
        _train_parser(parser, depgraphs, str(inside))
        assert inside.stat().st_size > 0
        parsed = parser.parse(depgraphs[:1], str(inside))
        assert len(parsed) == 1

    def test_averaged_perceptron_save_outside_is_refused(
        self, pathsec_sandbox, trained_tagger
    ):
        target = pathsec_sandbox.outside / "weights.json"
        exc = _refused(trained_tagger.model.save, str(target))
        assert "[AveragedPerceptron.save]" in str(exc)
        assert not target.exists()

    def test_averaged_perceptron_load_outside_is_refused(self, pathsec_sandbox):
        planted = pathsec_sandbox.outside / "weights.json"
        planted.write_text(json.dumps({"bias": {"NN": 1.0}}), encoding="utf-8")
        exc = _refused(AveragedPerceptron().load, str(planted))
        assert "[AveragedPerceptron.load]" in str(exc)

    def test_averaged_perceptron_in_root_round_trip(
        self, pathsec_sandbox, trained_tagger
    ):
        inside = pathsec_sandbox.root / "weights.json"
        trained_tagger.model.save(str(inside))
        reloaded = AveragedPerceptron()
        reloaded.load(str(inside))
        assert reloaded.weights == trained_tagger.model.weights

    def test_save_to_json_outside_is_refused(self, pathsec_sandbox, trained_tagger):
        loc = pathsec_sandbox.outside / "tagger"
        exc = _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert f"[{CONTEXT}]" in str(exc)
        assert not loc.exists()

    def test_save_to_json_in_root_round_trip(self, pathsec_sandbox, trained_tagger):
        loc = pathsec_sandbox.root / "tagger"
        trained_tagger.save_to_json(LANG, str(loc))
        assert sorted(os.listdir(loc)) == sorted(trained_tagger.param_files(LANG))
        reloaded = PerceptronTagger(load=False)
        reloaded.load_from_json(LANG, str(loc))
        assert reloaded.model.weights == trained_tagger.model.weights
        assert reloaded.tag(["the", "cat"]) == trained_tagger.tag(["the", "cat"])

    def test_save_maxent_params_outside_is_refused(
        self, pathsec_sandbox, maxent_params
    ):
        from nltk.classify.maxent import save_maxent_params

        tab_dir = pathsec_sandbox.outside / "maxent_tab"
        exc = _refused(save_maxent_params, *maxent_params, str(tab_dir))
        assert "[save_maxent_params]" in str(exc)
        assert not tab_dir.exists()

    def test_save_maxent_params_in_root_round_trip(
        self, pathsec_sandbox, maxent_params
    ):
        numpy = pytest.importorskip("numpy")
        from nltk.classify.maxent import load_maxent_params, save_maxent_params

        tab_dir = pathsec_sandbox.root / "maxent_tab"
        out = save_maxent_params(*maxent_params, str(tab_dir))
        assert _inside(out, pathsec_sandbox.root)
        assert sorted(os.listdir(out)) == [
            "alwayson.tab",
            "labels.txt",
            "mapping.tab",
            "weights.txt",
        ]
        wgt, mpg, lab, aon = load_maxent_params(out)
        assert numpy.allclose(wgt, maxent_params[0])
        assert mpg == maxent_params[1]
        assert lab == maxent_params[2]
        assert aon == maxent_params[3]


class TestReporterNegativeControls:
    """The three calls the reporter cites as refusing the same paths do."""

    def test_pathsec_open_outside_is_refused(self, pathsec_sandbox):
        target = pathsec_sandbox.outside / "x.txt"
        _refused(pathsec.open, str(target), "w", context="test")
        assert not target.exists()

    def test_load_from_json_outside_is_refused(self, pathsec_sandbox, trained_tagger):
        inside = pathsec_sandbox.root / "tagger"
        trained_tagger.save_to_json(LANG, str(inside))
        planted = pathsec_sandbox.outside / "tagger"
        shutil.copytree(str(inside), str(planted))
        exc = _refused(PerceptronTagger(load=False).load_from_json, LANG, str(planted))
        assert "[PerceptronTagger.load_from_json]" in str(exc)

    def test_load_maxent_params_outside_is_refused(
        self, pathsec_sandbox, maxent_params
    ):
        from nltk.classify.maxent import load_maxent_params, save_maxent_params

        inside = save_maxent_params(*maxent_params, str(pathsec_sandbox.root / "tab"))
        planted = pathsec_sandbox.outside / "tab"
        shutil.copytree(inside, str(planted))
        _refused(load_maxent_params, str(planted))


# The gap: a parameter-file name planted inside an in-root save_to_json loc


@POSIX_ONLY
class TestSaveToJsonPlantedParamFile:
    """``save_to_json`` writes relative to a pinned directory descriptor; the
    entry at each parameter-file name must never be opened as found."""

    def test_hardlink_to_an_outside_inode_is_refused_and_not_truncated(
        self, pathsec_sandbox, trained_tagger
    ):
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        _hardlink_or_skip(str(secret), _param_file(loc))
        exc = _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert "multiply-linked" in str(exc)
        assert secret.read_bytes() == SECRET

    def test_fifo_is_refused_without_blocking(self, pathsec_sandbox, trained_tagger):
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        os.mkfifo(_param_file(loc))
        with _bounded():
            _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert stat.S_ISFIFO(os.lstat(_param_file(loc)).st_mode)

    def test_symlink_is_refused_as_a_guard_refusal(
        self, pathsec_sandbox, trained_tagger
    ):
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        os.symlink(str(secret), _param_file(loc))
        _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert secret.read_bytes() == SECRET
        assert os.path.islink(_param_file(loc))

    def test_planted_directory_at_the_name_is_refused(
        self, pathsec_sandbox, trained_tagger
    ):
        """Through the pinned descriptor this is the guard refusal; on the
        by-name route ``pathsec.open`` lets the kernel refuse it (EISDIR).
        Either way nothing is written and the directory is left alone."""
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        os.mkdir(_param_file(loc))
        with pytest.raises((PermissionError, IsADirectoryError)) as excinfo:
            trained_tagger.save_to_json(LANG, str(loc))
        if perceptron._dir_fd_write_supported():
            assert _is_guard_refusal(excinfo.value), excinfo.value
        assert os.path.isdir(_param_file(loc)) and not os.listdir(_param_file(loc))

    def test_a_previous_save_is_replaced_and_round_trips(
        self, pathsec_sandbox, trained_tagger
    ):
        loc = pathsec_sandbox.root / "tagger"
        trained_tagger.save_to_json(LANG, str(loc))
        # Hold the first inode open: a filesystem may hand the same inode
        # number straight back after unlink + create, so the old inode itself
        # is the witness. Through the pinned descriptor the entry is replaced
        # (the held inode is unlinked, its bytes untouched); by name, pathsec
        # .open truncates in place only after verifying a single-linked
        # regular file, so the held inode then carries the new bytes.
        with open(_param_file(loc), "rb") as held:
            first_bytes = held.read()
            trained_tagger.save_to_json(LANG, str(loc))
            old = os.fstat(held.fileno())
            held.seek(0)
            if perceptron._dir_fd_write_supported():
                assert old.st_nlink == 0, "the old entry was truncated in place"
                assert held.read() == first_bytes
            else:
                assert old.st_nlink == 1
                assert held.read() == pathlib.Path(_param_file(loc)).read_bytes()
        second = os.stat(_param_file(loc))
        assert stat.S_ISREG(second.st_mode) and second.st_nlink == 1
        assert stat.S_IMODE(second.st_mode) == 0o600
        reloaded = PerceptronTagger(load=False)
        reloaded.load_from_json(LANG, str(loc))
        assert reloaded.model.weights == trained_tagger.model.weights

    def test_nothing_is_left_behind_after_a_refusal(
        self, pathsec_sandbox, trained_tagger
    ):
        """The first file refused, the later ones are not written either."""
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        _hardlink_or_skip(str(secret), _param_file(loc, "weights"))
        _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert os.listdir(loc) == [os.path.basename(_param_file(loc, "weights"))]

    @pytest.mark.parametrize("plant", ["hardlink", "fifo", "symlink"])
    def test_no_dir_fd_fallback_refuses_the_same_plants(
        self, plant, pathsec_sandbox, trained_tagger, monkeypatch
    ):
        """A platform without dir_fd support takes the by-name route; it must
        refuse the same inodes (pathsec.open's policy) and never block."""
        monkeypatch.setattr(os, "supports_dir_fd", set())
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        name = _param_file(loc)
        if plant == "hardlink":
            _hardlink_or_skip(str(secret), name)
        elif plant == "fifo":
            os.mkfifo(name)
        else:
            os.symlink(str(secret), name)
        with _bounded():
            _refused(trained_tagger.save_to_json, LANG, str(loc))
        assert secret.read_bytes() == SECRET

    def test_no_dir_fd_fallback_still_round_trips(
        self, pathsec_sandbox, trained_tagger, monkeypatch
    ):
        monkeypatch.setattr(os, "supports_dir_fd", set())
        loc = pathsec_sandbox.root / "tagger"
        trained_tagger.save_to_json(LANG, str(loc))
        trained_tagger.save_to_json(LANG, str(loc))
        reloaded = PerceptronTagger(load=False)
        reloaded.load_from_json(LANG, str(loc))
        assert reloaded.model.weights == trained_tagger.model.weights


class TestSaveToJsonTeeth:
    """Put the pre-fix opener back; the escape and the hang must return, so
    the tests above are known to reach the sink. Only where the pinned
    descriptor route is in use: elsewhere the by-name route is pathsec.open,
    whose own teeth live in test_model_artifact_pathsec.py."""

    @staticmethod
    def _truncating_create(name, dir_fd):
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        return os.open(name, flags, 0o600, dir_fd=dir_fd)

    @DIR_FD_ROUTE_ONLY
    def test_old_opener_overwrites_the_hardlinked_outside_inode(
        self, pathsec_sandbox, trained_tagger, monkeypatch
    ):
        monkeypatch.setattr(perceptron, "_create_model_file", self._truncating_create)
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        _hardlink_or_skip(str(secret), _param_file(loc))
        trained_tagger.save_to_json(LANG, str(loc))
        assert secret.read_bytes() != SECRET, "the old opener no longer escapes"
        assert b"bias" in secret.read_bytes()

    @DIR_FD_ROUTE_ONLY
    def test_old_opener_blocks_on_the_fifo(
        self, pathsec_sandbox, trained_tagger, monkeypatch
    ):
        monkeypatch.setattr(perceptron, "_create_model_file", self._truncating_create)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        os.mkfifo(_param_file(loc))
        with pytest.raises(TimeoutError), _bounded(seconds=2):
            trained_tagger.save_to_json(LANG, str(loc))

    def test_writer_source_creates_exclusively(self):
        """No ``O_TRUNC`` flag anywhere on the write path (prose aside)."""
        import ast
        import inspect
        import textwrap

        def flags_used(obj):
            tree = ast.parse(textwrap.dedent(inspect.getsource(obj)))
            return {
                node.attr
                for node in ast.walk(tree)
                if isinstance(node, ast.Attribute) and node.attr.startswith("O_")
            }

        create_flags = flags_used(perceptron._create_model_file)
        assert "O_EXCL" in create_flags and "O_TRUNC" not in create_flags
        assert '"O_NOFOLLOW"' in inspect.getsource(perceptron._create_model_file)
        assert "O_TRUNC" not in flags_used(PerceptronTagger.save_to_json)
        assert "_create_model_file(" in inspect.getsource(PerceptronTagger.save_to_json)


# The wider probe: vectors that were already closed on develop, pinned


def _sinks(pathsec_sandbox, parser, depgraphs, trained_tagger, maxent_params):
    """Every write sink the issue names, as ``name -> callable(path)``."""
    from nltk.classify.maxent import save_maxent_params

    return {
        "TransitionParser.train": lambda p: _train_parser(parser, depgraphs, p),
        "AveragedPerceptron.save": lambda p: trained_tagger.model.save(p),
        "PerceptronTagger.save_to_json": lambda p: trained_tagger.save_to_json(LANG, p),
        "save_maxent_params": lambda p: save_maxent_params(*maxent_params, p),
    }


SINK_NAMES = [
    "TransitionParser.train",
    "AveragedPerceptron.save",
    "PerceptronTagger.save_to_json",
    "save_maxent_params",
]


class TestWriteSinksRefuseEveryEscapeSpelling:
    @pytest.fixture
    def sinks(self, pathsec_sandbox, parser, depgraphs, trained_tagger, maxent_params):
        return _sinks(pathsec_sandbox, parser, depgraphs, trained_tagger, maxent_params)

    @pytest.mark.parametrize("sink", SINK_NAMES)
    def test_sibling_directory_sharing_the_root_prefix(
        self, sink, sinks, pathsec_sandbox
    ):
        sibling = pathlib.Path(str(pathsec_sandbox.root) + "x")
        sibling.mkdir(mode=0o700)
        try:
            target = sibling / "model"
            _refused(sinks[sink], str(target))
            assert not target.exists()
        finally:
            shutil.rmtree(sibling, ignore_errors=True)

    @pytest.mark.parametrize("sink", SINK_NAMES)
    def test_dotdot_spelled_through_the_root(self, sink, sinks, pathsec_sandbox):
        outside_name = pathsec_sandbox.outside.name
        target = pathsec_sandbox.root / "sub" / ".." / ".." / outside_name / "model"
        _refused(sinks[sink], str(target))
        assert not (pathsec_sandbox.outside / "model").exists()

    @pytest.mark.parametrize("sink", SINK_NAMES)
    def test_relative_path_against_an_outside_cwd(self, sink, sinks, pathsec_sandbox):
        saved = os.getcwd()
        os.chdir(pathsec_sandbox.outside)
        try:
            _refused(sinks[sink], "model")
        finally:
            os.chdir(saved)
        assert not (pathsec_sandbox.outside / "model").exists()

    @pytest.mark.parametrize("sink", SINK_NAMES)
    def test_relative_path_against_an_in_root_cwd_works(
        self, sink, sinks, pathsec_sandbox
    ):
        saved = os.getcwd()
        os.chdir(pathsec_sandbox.root)
        try:
            sinks[sink]("model")
        finally:
            os.chdir(saved)
        assert (pathsec_sandbox.root / "model").exists()

    @POSIX_ONLY
    @pytest.mark.parametrize(
        "sink", ["TransitionParser.train", "AveragedPerceptron.save"]
    )
    def test_in_root_hardlink_to_an_outside_inode(self, sink, sinks, pathsec_sandbox):
        secret = _plant_secret(pathsec_sandbox.outside)
        link = pathsec_sandbox.root / "model"
        _hardlink_or_skip(str(secret), str(link))
        _refused(sinks[sink], str(link))
        assert secret.read_bytes() == SECRET

    @POSIX_ONLY
    def test_maxent_in_root_hardlinked_parameter_file(self, sinks, pathsec_sandbox):
        secret = _plant_secret(pathsec_sandbox.outside)
        tab_dir = pathsec_sandbox.root / "tab"
        tab_dir.mkdir(mode=0o700)
        _hardlink_or_skip(str(secret), str(tab_dir / "weights.txt"))
        _refused(sinks["save_maxent_params"], str(tab_dir))
        assert secret.read_bytes() == SECRET

    @POSIX_ONLY
    @pytest.mark.parametrize(
        "sink", ["TransitionParser.train", "AveragedPerceptron.save"]
    )
    def test_in_root_fifo_destination_does_not_block(
        self, sink, sinks, pathsec_sandbox
    ):
        fifo = pathsec_sandbox.root / "model"
        os.mkfifo(str(fifo))
        with _bounded():
            _refused(sinks[sink], str(fifo))

    @POSIX_ONLY
    def test_maxent_in_root_fifo_parameter_file_does_not_block(
        self, sinks, pathsec_sandbox
    ):
        tab_dir = pathsec_sandbox.root / "tab"
        tab_dir.mkdir(mode=0o700)
        os.mkfifo(str(tab_dir / "weights.txt"))
        with _bounded():
            _refused(sinks["save_maxent_params"], str(tab_dir))

    @pytest.mark.parametrize(
        "sink",
        [
            "AveragedPerceptron.save",
            "PerceptronTagger.save_to_json",
            "save_maxent_params",
        ],
    )
    def test_backslash_spelled_traversal_is_refused(self, sink, sinks, pathsec_sandbox):
        """These sinks run the shared name checks, which fold ``\\`` before
        looking for ``..``, so the Windows spelling is refused everywhere."""
        target = (
            str(pathsec_sandbox.root) + "\\..\\" + pathsec_sandbox.outside.name + "\\m"
        )
        exc = _refused(sinks[sink], target)
        assert "'..'" in str(exc)

    @POSIX_ONLY
    def test_backslash_spelling_stays_an_in_root_filename_for_the_parser(
        self, sinks, pathsec_sandbox
    ):
        """``TransitionParser.train`` resolves the path instead: on POSIX a
        backslash is an ordinary character, so the spelling names one odd file
        inside the root and nothing outside it (pinned as benign)."""
        spelled = (
            str(pathsec_sandbox.root)
            + "/x\\..\\..\\"
            + pathsec_sandbox.outside.name
            + "\\m"
        )
        sinks["TransitionParser.train"](spelled)
        assert os.path.isfile(spelled) and _inside(spelled, pathsec_sandbox.root)
        assert not (pathsec_sandbox.outside / "m").exists()


class TestReadSinksRefuseInRootSpecialFiles:
    @POSIX_ONLY
    def test_parser_parse_in_root_fifo_does_not_block(
        self, pathsec_sandbox, parser, depgraphs
    ):
        fifo = pathsec_sandbox.root / "model"
        os.mkfifo(str(fifo))
        with _bounded():
            _refused(parser.parse, depgraphs[:1], str(fifo))

    @POSIX_ONLY
    def test_averaged_perceptron_load_in_root_fifo_does_not_block(
        self, pathsec_sandbox
    ):
        fifo = pathsec_sandbox.root / "model"
        os.mkfifo(str(fifo))
        with _bounded():
            _refused(AveragedPerceptron().load, str(fifo))

    @POSIX_ONLY
    def test_load_from_json_in_root_fifo_does_not_block(self, pathsec_sandbox):
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        for attr in ("weights", "tagdict", "classes"):
            os.mkfifo(_param_file(loc, attr))
        with _bounded():
            _refused(PerceptronTagger(load=False).load_from_json, LANG, str(loc))

    @POSIX_ONLY
    def test_load_maxent_params_in_root_fifo_does_not_block(self, pathsec_sandbox):
        from nltk.classify.maxent import load_maxent_params

        tab_dir = pathsec_sandbox.root / "tab"
        tab_dir.mkdir(mode=0o700)
        os.mkfifo(str(tab_dir / "weights.txt"))
        with _bounded():
            _refused(load_maxent_params, str(tab_dir))

    @pytest.mark.parametrize("mode", [0o775, 0o777, 0o707])
    @POSIX_ONLY
    def test_group_or_world_writable_model_dir_is_refused(
        self, mode, pathsec_sandbox, trained_tagger
    ):
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir()
        os.chmod(str(loc), mode)
        assert stat.S_IMODE(os.stat(str(loc)).st_mode) == mode
        # the pinned-descriptor route and pathsec.ensure_private_dir word the
        # same refusal differently
        with pytest.raises(
            PermissionError, match="non-private|writable by another account"
        ):
            trained_tagger.save_to_json(LANG, str(loc))
        assert os.listdir(loc) == []


class TestParserScratchFilesStayInside:
    def test_training_scratch_dir_is_in_root_and_removed(
        self, pathsec_sandbox, parser, depgraphs, monkeypatch
    ):
        import nltk.parse.transitionparser as module

        seen = []
        real = module.make_staging_dir

        def spy(*args, **kwargs):
            made = real(*args, **kwargs)
            seen.append(made)
            return made

        monkeypatch.setattr(module, "make_staging_dir", spy)
        _train_parser(parser, depgraphs, str(pathsec_sandbox.root / "tp.model"))
        assert seen, "training did not stage through make_staging_dir"
        for made in seen:
            assert _inside(made, pathsec_sandbox.root)
            assert not os.path.exists(made)

    def test_default_maxent_destination_is_in_root(
        self, pathsec_sandbox, maxent_params
    ):
        from nltk.classify.maxent import save_maxent_params

        out = save_maxent_params(*maxent_params)
        assert _inside(out, pathsec_sandbox.root)
        if os.name == "posix":
            assert stat.S_IMODE(os.stat(out).st_mode) == 0o700


class TestSiblingModelArtifactApis:
    """The same family outside the six names: each refuses an outside model
    path at the guard, before any tool or native library sees it."""

    def test_weka_classifier_model_outside_is_refused(self, pathsec_sandbox):
        from nltk.classify.weka import WekaClassifier

        exc = _refused(WekaClassifier, None, str(pathsec_sandbox.outside / "m.model"))
        assert "[WekaClassifier]" in str(exc)

    def test_crf_tagger_model_outside_is_refused(self, pathsec_sandbox):
        pytest.importorskip("pycrfsuite")
        from nltk.tag.crf import CRFTagger

        target = pathsec_sandbox.outside / "m.crf"
        _refused(CRFTagger().train, TINY_TAGGED, str(target))
        assert not target.exists()
        _refused(CRFTagger().set_model_file, str(target))

    def test_sentiment_analyzer_save_file_outside_is_refused(self, pathsec_sandbox):
        from nltk.sentiment.sentiment_analyzer import SentimentAnalyzer

        target = pathsec_sandbox.outside / "analyzer.pickle"
        _refused(SentimentAnalyzer().save_file, {"k": 1}, str(target))
        assert not target.exists()

    @POSIX_ONLY
    def test_sentiment_analyzer_save_file_in_root_hardlink_is_refused(
        self, pathsec_sandbox
    ):
        from nltk.sentiment.sentiment_analyzer import SentimentAnalyzer

        secret = _plant_secret(pathsec_sandbox.outside)
        link = pathsec_sandbox.root / "analyzer.pickle"
        _hardlink_or_skip(str(secret), str(link))
        _refused(SentimentAnalyzer().save_file, {"k": 1}, str(link))
        assert secret.read_bytes() == SECRET

    @POSIX_ONLY
    def test_tagger_train_save_loc_reaches_the_contained_writer(self, pathsec_sandbox):
        """``train(save_loc=)`` ends in ``save_to_json``, so the planted
        hardlink is refused there too and the outside inode survives."""
        secret = _plant_secret(pathsec_sandbox.outside)
        loc = pathsec_sandbox.root / "tagger"
        loc.mkdir(mode=0o700)
        _hardlink_or_skip(str(secret), _param_file(loc))
        tagger = PerceptronTagger(load=False)
        tagger.lang = LANG
        _refused(tagger.train, TINY_TAGGED, save_loc=str(loc), nr_iter=1)
        assert secret.read_bytes() == SECRET


@POSIX_ONLY
class TestNativeWriterPlants:
    """pycrfsuite opens the model path itself, so ``pathsec.open`` cannot wrap
    it; ``validate_tool_path(for_write=True)`` must refuse the same planted
    inodes by name before the native library sees them."""

    @pytest.fixture
    def crf(self):
        pytest.importorskip("pycrfsuite")
        from nltk.tag.crf import CRFTagger

        return CRFTagger

    def test_in_root_train_and_retrain_work(self, crf, pathsec_sandbox):
        model = pathsec_sandbox.root / "m.crf"
        crf().train(TINY_TAGGED, str(model))
        first = model.stat().st_size
        assert first > 0
        crf().train(TINY_TAGGED, str(model))
        tagger = crf()
        tagger.set_model_file(str(model))
        assert len(tagger.tag(["the", "cat"])) == 2

    @pytest.mark.parametrize(
        "plant", ["hardlink", "symlink-out", "symlink-in", "fifo", "dir"]
    )
    def test_train_refuses_a_planted_model_path(self, plant, crf, pathsec_sandbox):
        secret = _plant_secret(pathsec_sandbox.outside)
        target = pathsec_sandbox.root / "planted.crf"
        if plant == "hardlink":
            _hardlink_or_skip(str(secret), str(target))
        elif plant == "symlink-out":
            os.symlink(str(secret), str(target))
        elif plant == "symlink-in":
            real = pathsec_sandbox.root / "real.crf"
            real.write_bytes(b"")
            os.symlink(str(real), str(target))
        elif plant == "fifo":
            os.mkfifo(str(target))
        else:
            target.mkdir()
        with _bounded():
            _refused(crf().train, TINY_TAGGED, str(target))
        assert secret.read_bytes() == SECRET

    @pytest.mark.parametrize("plant", ["hardlink", "fifo"])
    def test_set_model_file_refuses_a_planted_model_path(
        self, plant, crf, pathsec_sandbox
    ):
        secret = _plant_secret(pathsec_sandbox.outside)
        target = pathsec_sandbox.root / "planted.crf"
        if plant == "hardlink":
            _hardlink_or_skip(str(secret), str(target))
        else:
            os.mkfifo(str(target))
        with _bounded():
            _refused(crf().set_model_file, str(target))

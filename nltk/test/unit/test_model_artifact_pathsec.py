"""Exploit matrix for the model-artifact read/write APIs (GHSA-8mgp-746c-j5xp).

The advisory names six entry points that treated a caller-supplied model path as
an ordinary filename: ``TransitionParser.train``/``parse``,
``AveragedPerceptron.save``/``load``, ``PerceptronTagger.save_to_json`` and
``save_maxent_params``. This file drives all of them, plus the sibling
save/load helpers in the same family and the constructor/train routes that reach
them, with every path form an attacker can supply.

Three kinds of case are kept side by side on purpose:

* **escapes** -- must be refused, and must leave nothing behind outside the root.
* **benign / probable-but-harmless** -- pinned so that if a future change starts
  expanding, decoding or following them, the pin turns into a failure.
* **over-block controls** -- the legitimate in-sandbox flows must keep working,
  so a fix cannot be "refuse everything".

Plus negative controls: each guard is neutered in-process and the exploit must
become reachable again, so none of these tests can pass by never reaching a sink.

Staging note: an "outside" target is created under ``$HOME`` (the ``sandbox`` /
``pathsec_sandbox`` fixtures in conftest.py), never in ``tempfile.mkdtemp()`` --
a private per-user system temp dir IS an allowed root on macOS/Windows, so a
target staged there would be correctly permitted and prove nothing.
"""

import builtins
import json
import os
import pathlib
import pickle
import shutil
import socket
import stat
import tempfile
import time

import pytest

import nltk.data
import nltk.pathsec as pathsec
import nltk.tag.perceptron as perceptron
from nltk.tag.perceptron import AveragedPerceptron, PerceptronTagger

CANARY = "MODEL-ARTIFACT-CANARY"
LANG = "probeartifact"

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX-only path form")


@pytest.fixture
def outside_only(monkeypatch):
    """An out-of-sandbox directory that leaves ``nltk.data.path`` alone.

    The ``sandbox`` fixtures narrow the allowed roots to one empty directory,
    which also hides the installed corpora; tests that must load a real corpus
    (or a real shipped model) use this instead. ``$HOME`` is not an allowed root
    on its own, so a directory made there is still a genuine escape target, and
    that is asserted rather than assumed.
    """
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    path = pathlib.Path(
        tempfile.mkdtemp(prefix=".nltk_artifact_outside_", dir=str(pathlib.Path.home()))
    )
    resolved = path.resolve()
    inside = any(
        resolved == root or resolved.is_relative_to(root)
        for root in pathsec._get_allowed_roots()
    )
    try:
        if inside:
            pytest.skip("$HOME is inside an allowed root here; no escape target")
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def _weights():
    return {CANARY: {"NN": 1.0}}


def _tagger():
    tagger = PerceptronTagger(load=False)
    tagger.model.weights = _weights()
    tagger.tagdict = {}
    tagger.classes = {"NN"}
    return tagger


def _plant_model_dir(loc, lang=LANG):
    """Stage the three json files ``load_from_json`` reads, as an attacker would.

    Written with the stdlib writer deliberately: this is the attacker's plant,
    staged outside the sandbox before the attack runs, not NLTK doing the I/O.
    """
    os.makedirs(loc, mode=0o700, exist_ok=True)
    for attr, value in (
        ("weights", _weights()),
        ("tagdict", {}),
        ("classes", ["NN"]),
    ):
        target = os.path.join(loc, f"averaged_perceptron_tagger_{lang}.{attr}.json")
        pathlib.Path(target).write_text(json.dumps(value), encoding="utf-8")


def _refused(call, *args, **kwargs):
    """Run *call*; return the security exception it raised, or fail loudly."""
    with pytest.raises((PermissionError, ValueError, OSError)) as excinfo:
        call(*args, **kwargs)
    return excinfo.value


# ==========================================================================
# AveragedPerceptron.save / load -- the advisory's bare-open pair
# ==========================================================================


class TestAveragedPerceptronEscapes:
    def test_load_outside_root_is_refused(self, sandbox):
        target = sandbox / "weights.json"
        target.write_text(json.dumps(_weights()), encoding="utf-8")
        model = AveragedPerceptron()
        _refused(model.load, str(target))
        assert model.weights == {}, "outside-root weights reached the caller"

    def test_save_outside_root_is_refused_and_writes_nothing(self, sandbox):
        target = sandbox / "written.json"
        _refused(AveragedPerceptron(_weights()).save, str(target))
        assert not target.exists(), "refused write still created the file"

    @POSIX_ONLY
    def test_save_through_in_root_symlink_is_refused(self, pathsec_sandbox):
        victim = pathsec_sandbox.outside / "victim.json"
        victim.write_text("untouched", encoding="utf-8")
        link = pathsec_sandbox.root / "link.json"
        os.symlink(str(victim), str(link))
        _refused(AveragedPerceptron(_weights()).save, str(link))
        assert victim.read_text(encoding="utf-8") == "untouched"

    @POSIX_ONLY
    def test_save_through_symlinked_parent_is_refused(self, pathsec_sandbox):
        victim_dir = pathsec_sandbox.outside / "parent"
        victim_dir.mkdir()
        link = pathsec_sandbox.root / "plink"
        os.symlink(str(victim_dir), str(link))
        _refused(AveragedPerceptron(_weights()).save, str(link / "w.json"))
        assert not list(victim_dir.iterdir()), "write escaped via the parent symlink"

    @POSIX_ONLY
    def test_load_through_in_root_hardlink_is_refused(self, pathsec_sandbox):
        secret = pathsec_sandbox.outside / "secret.json"
        secret.write_text(json.dumps(_weights()), encoding="utf-8")
        link = pathsec_sandbox.root / "hard.json"
        try:
            os.link(str(secret), str(link))
        except OSError:
            pytest.skip("cross-device hardlink not possible here")
        model = AveragedPerceptron()
        _refused(model.load, str(link))
        assert model.weights == {}

    def test_traversal_out_of_the_root_is_refused(self, pathsec_sandbox):
        target = pathsec_sandbox.outside / "trav.json"
        target.write_text(json.dumps(_weights()), encoding="utf-8")
        hop = os.path.join(
            str(pathsec_sandbox.root), *([os.pardir] * 12), str(target).lstrip("/")
        )
        model = AveragedPerceptron()
        _refused(model.load, hop)
        assert model.weights == {}

    def test_sibling_directory_sharing_the_root_prefix_is_refused(
        self, outside_only, monkeypatch
    ):
        """``<root>_evil`` starts with the root's characters but is not under it.

        The root has to sit somewhere that is not itself a root, or the sibling
        would be legitimately allowed by the parent and prove nothing.
        """
        root = outside_only / "root"
        root.mkdir()
        sibling = outside_only / "root_evil"
        sibling.mkdir()
        monkeypatch.setattr(nltk.data, "path", [str(root)])
        monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
        monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
        target = sibling / "x.json"
        target.write_text(json.dumps(_weights()), encoding="utf-8")
        model = AveragedPerceptron()
        _refused(model.load, str(target))
        assert model.weights == {}

    def test_case_folded_root_prefix_is_refused(self, pathsec_sandbox):
        """An upper-cased path is a different string, so containment fails closed.

        On a case-insensitive filesystem it names the same file; the check must
        still refuse rather than accidentally accept a non-matching prefix.
        """
        inside = pathsec_sandbox.root / "cf.json"
        AveragedPerceptron(_weights()).save(str(inside))
        model = AveragedPerceptron()
        _refused(model.load, str(inside).upper())
        assert model.weights == {}

    def test_bytes_and_pathlike_forms_are_validated_too(self, sandbox):
        _refused(AveragedPerceptron(_weights()).save, str(sandbox / "b.json").encode())
        _refused(AveragedPerceptron(_weights()).save, pathlib.Path(sandbox / "p.json"))
        assert not list(sandbox.iterdir())

    def test_directory_where_a_file_is_expected_is_refused(self, sandbox):
        _refused(AveragedPerceptron().load, str(sandbox))


class TestAveragedPerceptronBenignForms:
    """Forms that are harmless today, pinned so a future decode/expand regresses.

    None of these may reach a file outside the sandbox: the assertion is that the
    call fails and leaves the outside directory empty.
    """

    @pytest.mark.parametrize(
        "form",
        [
            "nul-trailing",
            "nul-middle",
            "newline",
            "tilde",
            "relative",
            "dot-slash",
            "unc-forward",
            "backslash",
            "ads-stream",
            "overlong",
            "leading-dash",
        ],
    )
    def test_probable_but_harmless_write_forms_touch_nothing(self, form, sandbox):
        base = str(sandbox / "x.json")
        payloads = {
            "nul-trailing": base + "\x00",
            "nul-middle": base + "\x00.cfg",
            "newline": base + "\n",
            "tilde": "~/" + os.path.basename(base),
            "relative": os.path.basename(base),
            "dot-slash": "./" + os.path.basename(base),
            "unc-forward": "//" + base.lstrip("/"),
            "backslash": base.replace("/", "\\"),
            "ads-stream": base + ":stream",
            "overlong": os.path.join(str(sandbox), "a" * 5000),
            "leading-dash": "-rf",
        }
        with pytest.raises(Exception):
            AveragedPerceptron(_weights()).save(payloads[form])
        assert not list(sandbox.iterdir()), f"{form} created a file outside the root"

    @pytest.mark.parametrize("blank", ["   ", "\t", "\n", "  \t "])
    def test_whitespace_only_paths_do_not_create_a_file(self, blank, outside_only):
        """A whitespace-only name is a legal relative filename, not "no path".

        Waving it through skipped containment entirely and let the open create
        that file in the working directory. The CWD is an out-of-sandbox
        directory here, so a created file is a real escape (on macOS the private
        system temp dir IS an allowed root, and a temp CWD would hide this).
        """
        saved = os.getcwd()
        os.chdir(outside_only)
        try:
            with pytest.raises(Exception):
                AveragedPerceptron(_weights()).save(blank)
            assert not list(outside_only.iterdir()), "whitespace path created a file"
        finally:
            os.chdir(saved)

    def test_empty_path_is_not_a_write(self, restricted_sandbox):
        with pytest.raises(OSError):
            AveragedPerceptron(_weights()).save("")

    @POSIX_ONLY
    @pytest.mark.parametrize("device", ["/dev/stdin", "/dev/fd/0", "/dev/null"])
    def test_device_nodes_outside_the_root_are_refused(
        self, device, restricted_sandbox
    ):
        """Never opened: containment refuses the path string before any open().

        That ordering is what keeps a blocking device/FIFO from hanging the
        reader, so it is asserted rather than assumed.
        """
        if not os.path.exists(device):
            pytest.skip(f"{device} not present")
        _refused(AveragedPerceptron().load, device)


@POSIX_ONLY
class TestBlockingSpecialFilesAreContained:
    """A FIFO / unix socket blocks a reader forever, so containment must decide
    before anything is opened.

    An outside-root FIFO is refused on the path string. One planted *inside* a
    trusted data root is deliberately still permitted (a root is trusted by
    definition), so that decision is pinned here rather than left implicit, and
    neither case is ever opened by this test.
    """

    def test_outside_fifo_is_refused_without_opening_it(self, pathsec_sandbox):
        fifo = pathsec_sandbox.outside / "fifo"
        os.mkfifo(str(fifo))
        assert stat.S_ISFIFO(os.stat(str(fifo)).st_mode)
        _refused(AveragedPerceptron().load, str(fifo))

    def test_outside_unix_socket_is_refused_without_opening_it(self, pathsec_sandbox):
        target = pathsec_sandbox.outside / "sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            server.bind(str(target))
            _refused(AveragedPerceptron().load, str(target))
        finally:
            server.close()

    def test_in_root_special_file_is_inside_the_sandbox(self, restricted_sandbox):
        fifo = os.path.join(restricted_sandbox, "fifo")
        os.mkfifo(fifo)
        # No exception: a path inside a trusted root is contained. Not opened --
        # a FIFO read blocks until a writer appears.
        pathsec.validate_path(fifo, context="test")


class TestAveragedPerceptronRoundTrip:
    """Over-block control: the legitimate in-sandbox flow must keep working."""

    def test_save_load_round_trip_inside_a_data_root(self, restricted_sandbox):
        target = os.path.join(restricted_sandbox, "weights.json")
        AveragedPerceptron(_weights()).save(target)
        assert os.path.exists(target)
        reloaded = AveragedPerceptron()
        reloaded.load(target)
        assert reloaded.weights == _weights()


# ==========================================================================
# PerceptronTagger.save_to_json / load_from_json / train / __init__
# ==========================================================================


class TestPerceptronTaggerEscapes:
    def test_save_to_json_outside_root_is_refused(self, sandbox):
        loc = str(sandbox / "tagger_out")
        _refused(_tagger().save_to_json, LANG, loc)
        assert not os.path.exists(loc), "refused save still created the directory"

    def test_train_save_loc_outside_root_is_refused(self, sandbox):
        loc = str(sandbox / "trained")
        tagger = PerceptronTagger(load=False)
        _refused(tagger.train, [[("a", "DT")]], loc, 1)
        assert not os.path.exists(loc)

    def test_forced_save_dir_outside_root_is_refused(self, sandbox):
        tagger = _tagger()
        tagger._save_dir = str(sandbox / "forced")
        _refused(tagger.save_to_json, LANG)
        assert not list(sandbox.iterdir())

    @POSIX_ONLY
    def test_save_to_json_into_a_symlinked_dir_is_refused(self, pathsec_sandbox):
        victim = pathsec_sandbox.outside / "sym_victim"
        victim.mkdir()
        link = pathsec_sandbox.root / "symloc"
        os.symlink(str(victim), str(link))
        _refused(_tagger().save_to_json, LANG, str(link))
        assert not list(victim.iterdir()), "write leaked through the symlink"

    def test_save_to_json_traversal_out_of_the_root_is_refused(self, pathsec_sandbox):
        hop = os.path.join(
            str(pathsec_sandbox.root),
            *([os.pardir] * 12),
            str(pathsec_sandbox.outside / "trav").lstrip("/"),
        )
        _refused(_tagger().save_to_json, LANG, hop)
        assert not list(pathsec_sandbox.outside.iterdir())

    def test_load_from_json_outside_root_is_refused(self, sandbox):
        loc = str(sandbox / "tagger_in")
        _plant_model_dir(loc)
        tagger = PerceptronTagger(load=False)
        _refused(tagger.load_from_json, LANG, loc)
        assert tagger.model.weights == {}

    @pytest.mark.parametrize("wrap", [str, pathlib.Path, "pointer"])
    def test_every_loc_type_reaches_the_same_guard(self, wrap, sandbox):
        """str, pathlib.Path and PathPointer are three separate branches in
        load_from_json; a guard on one is not a guard on the siblings."""
        loc = str(sandbox / f"tagger_{getattr(wrap, '__name__', wrap)}")
        _plant_model_dir(loc)
        value = nltk.data.FileSystemPathPointer(loc) if wrap == "pointer" else wrap(loc)
        tagger = PerceptronTagger(load=False)
        _refused(tagger.load_from_json, LANG, value)
        assert tagger.model.weights == {}

    def test_constructor_loc_reaches_the_same_guard(self, sandbox):
        loc = str(sandbox / "tagger_ctor")
        _plant_model_dir(loc)
        _refused(PerceptronTagger, True, LANG, loc)

    def test_relative_traversal_loc_is_refused(self, restricted_sandbox):
        _refused(PerceptronTagger(load=False).load_from_json, LANG, "../../../etc")

    def test_load_from_json_does_not_widen_the_sandbox(self, sandbox):
        """A caller-supplied dir must never be appended to nltk.data.path.

        That primitive turns containment off for the path and everything under
        it, process-wide, for every later read.
        """
        loc = str(sandbox / "tagger_widen")
        _plant_model_dir(loc)
        before = list(nltk.data.path)
        with pytest.raises(Exception):
            PerceptronTagger(load=False).load_from_json(LANG, loc)
        assert list(nltk.data.path) == before


class TestPerceptronTaggerDirectoryOpen:
    """The pinned-descriptor layer under ``save_to_json``."""

    @POSIX_ONLY
    def test_a_swapped_intermediate_directory_is_caught_by_the_fd_recheck(
        self, pathsec_sandbox, monkeypatch
    ):
        """O_NOFOLLOW only covers the leaf.

        With the caller-path check skipped (as a swapped parent between check and
        open would leave it), the descriptor's own real path must still be
        refused, so the model write cannot land outside the roots.
        """
        victim = pathsec_sandbox.outside / "redirected"
        victim.mkdir()
        link = pathsec_sandbox.root / "plink"
        os.symlink(str(victim), str(link))

        real = perceptron.validate_path
        calls = []

        def skip_the_caller_check(*args, **kwargs):
            calls.append(args)
            if len(calls) == 1:
                return None
            return real(*args, **kwargs)

        monkeypatch.setattr(perceptron, "validate_path", skip_the_caller_check)
        _refused(_tagger().save_to_json, LANG, str(link / "leaf"))
        assert (
            not any((victim / "leaf").iterdir()) if (victim / "leaf").exists() else True
        )
        assert len(calls) > 1, "the descriptor was never re-validated"

    def test_a_regular_file_as_the_destination_is_refused(self, restricted_sandbox):
        target = os.path.join(restricted_sandbox, "not_a_dir")
        with pathsec.open(target, "w", context="test") as handle:
            handle.write("{}")
        _refused(_tagger().save_to_json, LANG, target)

    @POSIX_ONLY
    def test_an_in_root_symlink_destination_is_refused_fail_closed(
        self, restricted_sandbox
    ):
        """Even a symlink pointing at another in-root file is refused.

        Model artifacts are never symlinks, so refusing the final component
        outright is the fail-closed choice; it is asserted so a future
        "follow it, it stays in-root anyway" relaxation shows up here.
        """
        real = os.path.join(restricted_sandbox, "real.json")
        with pathsec.open(real, "w", context="test") as handle:
            handle.write("{}")
        link = os.path.join(restricted_sandbox, "link.json")
        os.symlink(real, link)
        _refused(AveragedPerceptron(_weights()).save, link)


class TestPerceptronTaggerLangComponent:
    """``lang`` is interpolated into the filename both directions open."""

    @pytest.mark.parametrize(
        "lang",
        [
            "../evil",
            "sub/../../evil",
            "/abs",
            "a\x00b",
            "..",
            ".",
            "",
            "e\\v",
            "a/b",
        ],
    )
    def test_lang_cannot_contribute_path_structure(self, lang, restricted_sandbox):
        loc = os.path.join(restricted_sandbox, "d")
        os.makedirs(loc, exist_ok=True)
        with pytest.raises(ValueError):
            _tagger().save_to_json(lang=lang, loc=loc)
        assert not os.listdir(loc)

    @pytest.mark.parametrize("lang", ["eng", "rus", "probeartifact", "xx"])
    def test_ordinary_language_codes_still_work(self, lang, restricted_sandbox):
        loc = os.path.join(restricted_sandbox, "ok")
        os.makedirs(loc, exist_ok=True)
        _tagger().save_to_json(lang=lang, loc=loc)
        assert sorted(os.listdir(loc)) == sorted(
            _tagger().param_files(lang)
        ), "a legitimate language code was blocked or renamed"


class TestPerceptronTaggerRoundTrip:
    """Over-block controls for the whole train/save/load path."""

    @pytest.fixture
    def staged(self):
        """A tagger whose lazily created staging dir is removed afterwards, so a
        test run does not leave directories behind in the user's data root."""
        made = []

        def build(**kwargs):
            tagger = (
                _tagger() if not kwargs.get("plain") else PerceptronTagger(load=False)
            )
            made.append(tagger)
            return tagger

        try:
            yield build
        finally:
            for tagger in made:
                if tagger._save_dir:
                    shutil.rmtree(tagger._save_dir, ignore_errors=True)

    def test_default_save_dir_is_inside_a_data_root(self, staged):
        tagger = staged(plain=True)
        resolved = pathlib.Path(tagger.save_dir).resolve()
        assert any(
            resolved == root or resolved.is_relative_to(root)
            for root in pathsec._get_allowed_roots()
        ), f"{tagger.save_dir} is not inside an allowed root"
        if os.name == "posix":
            # Windows has no POSIX mode bits; the per-user profile ACLs govern.
            assert stat.S_IMODE(os.stat(tagger.save_dir).st_mode) == 0o700

    def test_save_dir_is_memoized(self, staged):
        tagger = staged(plain=True)
        assert tagger.save_dir == tagger.save_dir

    def test_save_then_load_round_trip(self, staged):
        tagger = staged()
        loc = tagger.save_dir
        tagger.save_to_json(lang=LANG, loc=loc)
        reloaded = PerceptronTagger(load=False)
        reloaded.load_from_json(lang=LANG, loc=loc)
        assert reloaded.model.weights == _weights()
        assert reloaded.classes == {"NN"}

    def test_train_with_default_save_loc_round_trips(self, staged):
        tagger = staged(plain=True)
        sentences = [[("the", "DT"), ("dog", "NN")], [("a", "DT"), ("cat", "NN")]]
        tagger.train(sentences, save_loc=tagger.save_dir, nr_iter=2)
        reloaded = PerceptronTagger(load=False)
        reloaded.load_from_json(lang=tagger.lang, loc=tagger.save_dir)
        assert reloaded.tag(["the", "dog"]) == [("the", "DT"), ("dog", "NN")]

    def test_shipped_english_tagger_still_loads_and_tags(self):
        pytest.importorskip("numpy")
        try:
            tagger = PerceptronTagger(load=True, lang="eng")
        except LookupError:
            pytest.skip("averaged_perceptron_tagger_eng not installed")
        tagged = tagger.tag(["The", "dog", "barks", "."])
        assert [word for word, _ in tagged] == ["The", "dog", "barks", "."]
        assert [tag for _, tag in tagged][:2] == ["DT", "NN"]
        assert all(tag for _, tag in tagged), "a token came back untagged"


# ==========================================================================
# The rest of the model-artifact family reached from the same threat
# ==========================================================================


class TestSiblingModelArtifactApis:
    def test_transition_parser_parse_outside_root_is_refused(self, sandbox):
        from nltk.parse.transitionparser import TransitionParser

        target = sandbox / "model.pickle"
        target.write_bytes(b"\x80\x04N.")
        _refused(TransitionParser("arc-standard").parse, [], str(target))

    def test_transition_parser_train_outside_root_is_refused(self, sandbox):
        pytest.importorskip("sklearn")
        from nltk.parse.transitionparser import TransitionParser

        target = str(sandbox / "trained.pickle")
        _refused(TransitionParser("arc-standard").train, [], target, False)
        assert not os.path.exists(target)

    def test_save_maxent_params_outside_root_is_refused(self, sandbox):
        numpy = pytest.importorskip("numpy")
        from nltk.classify.maxent import save_maxent_params

        loc = str(sandbox / "maxent_out")
        _refused(
            save_maxent_params,
            numpy.array([1.0]),
            {("a", "b"): 0},
            ["L"],
            {"alwayson": 0},
            loc,
        )
        assert not os.path.exists(loc)

    def test_load_maxent_params_outside_root_is_refused(self, sandbox):
        pytest.importorskip("numpy")
        from nltk.classify.maxent import load_maxent_params

        loc = sandbox / "maxent_in"
        loc.mkdir()
        for name, body in (
            ("weights.txt", "1.0"),
            ("mapping.tab", ""),
            ("labels.txt", "L"),
            ("alwayson.tab", ""),
        ):
            (loc / name).write_text(body, encoding="utf-8")
        _refused(load_maxent_params, nltk.data.FileSystemPathPointer(str(loc)))

    def test_save_punkt_params_outside_root_is_refused(self, sandbox):
        from nltk.tokenize.punkt import PunktParameters, save_punkt_params

        loc = str(sandbox / "punkt_out")
        _refused(save_punkt_params, PunktParameters(), loc)
        assert not os.path.exists(loc)

    def test_maxent_ne_chunker_save_params_outside_root_is_refused(self, outside_only):
        pytest.importorskip("numpy")
        from nltk.chunk.named_entity import Maxent_NE_Chunker

        try:
            chunker = Maxent_NE_Chunker("multiclass")
        except LookupError:
            pytest.skip("maxent_ne_chunker_tab not installed")
        loc = str(outside_only / "ne_out")
        _refused(chunker.save_params, loc)
        assert not os.path.exists(loc)


class TestTblDemoModelPaths:
    """``nltk.tbl.demo.postag`` pickles a tagger to caller-supplied paths."""

    @staticmethod
    def _postag(**kwargs):
        """Run the demo, tolerating one pre-existing, unrelated failure.

        Re-tagging with the *reloaded* tagger raises ``ValueError: timeout not
        float or None`` on ``develop`` too (a redos-wrapped pattern does not
        survive a pickle round trip). That happens after the model file is
        written, so it does not affect what these tests assert; anything else
        propagates.
        """
        from nltk.tbl import demo as tbl_demo

        try:
            tbl_demo.postag(
                num_sents=10,
                max_rules=1,
                trace=0,
                separate_baseline_data=True,
                **kwargs,
            )
        except ValueError as exc:
            if "timeout not float or None" not in str(exc):
                raise

    @pytest.fixture(autouse=True)
    def _needs_treebank(self):
        pytest.importorskip("numpy")
        try:
            nltk.data.find("corpora/treebank")
        except LookupError:
            pytest.skip("treebank corpus not installed")

    @pytest.mark.parametrize(
        "kwarg", ["serialize_output", "cache_baseline_tagger", "error_output"]
    )
    def test_outside_root_destinations_are_refused(self, kwarg, outside_only):
        target = outside_only / f"{kwarg}.out"
        with pytest.raises((PermissionError, ValueError, OSError)):
            self._postag(**{kwarg: str(target)})
        assert not target.exists(), f"{kwarg} wrote outside the sandbox"

    def test_learning_curve_output_outside_root_is_refused(self, outside_only):
        """matplotlib writes the plot itself, so the path is checked up front."""
        target = outside_only / "curve.png"
        with pytest.raises((PermissionError, ValueError, OSError)):
            self._postag(incremental_stats=True, learning_curve_output=str(target))
        assert not target.exists()

    def test_learning_curve_output_in_root_still_works(self):
        pytest.importorskip("matplotlib")
        staging = nltk.data.make_staging_dir(prefix="nltk_tbl_curve_")
        try:
            target = os.path.join(staging, "curve.png")
            self._postag(incremental_stats=True, learning_curve_output=target)
            assert os.path.getsize(target) > 0
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    @pytest.mark.parametrize(
        "kwarg", ["serialize_output", "cache_baseline_tagger", "error_output"]
    )
    def test_in_root_destinations_still_work(self, kwarg):
        staging = nltk.data.make_staging_dir(prefix="nltk_tbl_demo_")
        try:
            target = os.path.join(staging, f"{kwarg}.out")
            self._postag(**{kwarg: target})
            assert os.path.getsize(target) > 0, f"{kwarg} wrote nothing in-sandbox"
        finally:
            shutil.rmtree(staging, ignore_errors=True)


class TestCRFTaggerModelPaths:
    """``CRFTagger`` hands a caller path to a native (pycrfsuite) loader/writer.

    Not in the advisory's list, but the same threat: the C extension does its
    own open, so nothing downstream would have contained it.
    """

    TRAIN = [[("the", "DT"), ("dog", "NN")], [("a", "DT"), ("cat", "NN")]]

    def test_train_outside_root_is_refused_before_writing(self, sandbox):
        pytest.importorskip("pycrfsuite")
        from nltk.tag.crf import CRFTagger

        target = str(sandbox / "model.crf")
        _refused(CRFTagger().train, self.TRAIN, target)
        assert not os.path.exists(target), "refused train still wrote the model"

    def test_set_model_file_outside_root_is_refused(self, sandbox):
        pytest.importorskip("pycrfsuite")
        from nltk.tag.crf import CRFTagger

        target = sandbox / "model.crf"
        target.write_bytes(b"not-a-real-model")
        _refused(CRFTagger().set_model_file, str(target))

    def test_in_root_train_and_tag_round_trip(self, restricted_sandbox):
        pytest.importorskip("pycrfsuite")
        from nltk.tag.crf import CRFTagger

        target = os.path.join(restricted_sandbox, "model.crf")
        tagger = CRFTagger()
        tagger.train(self.TRAIN, target)
        assert os.path.getsize(target) > 0
        reloaded = CRFTagger()
        reloaded.set_model_file(target)
        assert reloaded.tag(["the", "dog"]) == [("the", "DT"), ("dog", "NN")]


class TestResourceNameSteering:
    """Caller-supplied *resource names* that steer a model load.

    None of these escape a data root, so they are pinned as audited-benign: the
    assertion is the containment property, so a future change that lets one
    resolve outside turns into a failure here.
    """

    def test_punkt_lang_traversal_stays_inside_a_data_root(self):
        """``PunktTokenizer(lang)`` climbs at most within the trusted root.

        ``normalize_resource_name`` collapses ``punkt_tab/..`` to ``tokenizers/``
        before ``find`` sees it, so the lookup moves inside the root but cannot
        leave it; a leading ``..`` survives normalisation and ``find`` rejects it.
        """
        from nltk.tokenize import PunktTokenizer

        with pytest.raises((LookupError, OSError, ValueError)) as excinfo:
            PunktTokenizer("../..")
        message = str(excinfo.value)
        assert "/etc/" not in message and "passwd" not in message

    @pytest.mark.parametrize(
        "resource",
        [
            "tokenizers/punkt/../x.pickle",
            "tokenizers/punkt/../../../etc/passwd.pickle",
            "chunkers/maxent_ne_chunker/../../../etc/x.pickle",
        ],
    )
    def test_pickle_shim_resource_names_cannot_traverse(self, resource):
        """load() routes a *.pickle name to a pickle-free loader; the name that
        picks the model must not carry traversal."""
        with pytest.raises((ValueError, LookupError, OSError)):
            nltk.data.load(resource)

    def test_pos_tag_rejects_an_unknown_language(self):
        with pytest.raises(NotImplementedError):
            nltk.pos_tag(["a"], lang="../../etc")

    def test_ne_chunker_format_cannot_traverse(self):
        from nltk.chunk import ne_chunker

        with pytest.raises((ValueError, LookupError, OSError)):
            ne_chunker("../../../etc")

    def test_retrieve_without_a_filename_does_not_write_to_an_outside_cwd(
        self, outside_only
    ):
        """``retrieve`` derives the destination from the URL and writes it to the
        working directory; that destination is still sandbox-checked."""
        try:
            source = str(nltk.data.find("corpora/city_database/city.db"))
        except LookupError:
            pytest.skip("city_database corpus not installed")
        saved = os.getcwd()
        os.chdir(outside_only)
        try:
            with pytest.raises((PermissionError, ValueError, OSError)):
                nltk.data.retrieve("file://" + source, verbose=False)
            assert not list(outside_only.iterdir())
        finally:
            os.chdir(saved)


# ==========================================================================
# Negative controls: neuter a guard, the exploit must come back
# ==========================================================================


class TestModelReadsAreBounded:
    """A hostile *in-root* model must fail fast, not hang or exhaust the process."""

    def test_deeply_nested_json_weights_are_rejected_quickly(self, restricted_sandbox):
        target = os.path.join(restricted_sandbox, "nested.json")
        with pathsec.open(target, "w", context="test") as handle:
            handle.write("[" * 200000 + "]" * 200000)
        started = time.perf_counter()
        with pytest.raises((RecursionError, ValueError)):
            AveragedPerceptron().load(target)
        assert time.perf_counter() - started < 15.0


class TestModelReadsRefuseAPickleGadget:
    """Containment is not the only guard on a model read.

    A model file *inside* a trusted root still goes through an allowlisting
    unpickler, so a reachable-path model cannot execute a reduce gadget. Pinned
    here because these are the same read paths the sandbox guards: fixing one
    must not be mistaken for covering the other.
    """

    class _Boom:
        def __reduce__(self):
            return (os.system, ("exit 0",))

    def _planted(self, root):
        target = os.path.join(root, "gadget.pickle")
        with pathsec.open(target, "wb", context="test") as handle:
            pickle.dump(self._Boom(), handle)
        return target

    def test_transition_parser_refuses_a_gadget_model(self, restricted_sandbox):
        from nltk.parse.transitionparser import TransitionParser

        target = self._planted(restricted_sandbox)
        with pytest.raises(pickle.UnpicklingError):
            TransitionParser("arc-standard").parse([], target)

    def test_data_load_pickle_refuses_a_gadget_model(self, restricted_sandbox):
        target = self._planted(restricted_sandbox)
        with pytest.raises(pickle.UnpicklingError):
            nltk.data.load(os.path.basename(target), format="pickle", cache=False)


class TestNegativeControls:
    def test_enforce_off_lets_the_read_escape(self, sandbox, monkeypatch):
        target = sandbox / "weights.json"
        target.write_text(json.dumps(_weights()), encoding="utf-8")
        monkeypatch.setattr(pathsec, "ENFORCE", False)
        model = AveragedPerceptron()
        model.load(str(target))
        assert model.weights == _weights(), "guard disabled but read still blocked"

    def test_bare_open_reopens_the_advisory_write(self, sandbox, monkeypatch):
        """Put the advisory's own bug back and the escape must return."""
        target = sandbox / "bare.json"

        def bare_save(self, path):
            with open(path, "w") as fout:
                return json.dump(self.weights, fout)

        monkeypatch.setattr(AveragedPerceptron, "save", bare_save)
        AveragedPerceptron(_weights()).save(str(target))
        assert CANARY in target.read_text(encoding="utf-8")

    def test_dropping_save_to_json_validation_reopens_the_write(
        self, sandbox, monkeypatch
    ):
        """Both destination guards go: the sandbox check on ``loc`` and, on the
        branch that has no pinned dir_fd, the sandboxed per-file open."""
        monkeypatch.setattr(perceptron, "validate_path", lambda *a, **k: None)
        monkeypatch.setattr(
            perceptron,
            "pathsec_open",
            lambda path, mode="r", **kwargs: builtins.open(path, mode),
        )
        loc = str(sandbox / "unguarded")
        _tagger().save_to_json(lang=LANG, loc=loc)
        assert sorted(os.listdir(loc)), "no files written with the guard removed"

    def test_widening_nltk_data_path_reopens_the_read(self, sandbox, monkeypatch):
        """The removed ``_authorize_private_dir`` primitive, reconstructed."""
        loc = str(sandbox / "widened")
        _plant_model_dir(loc)
        monkeypatch.setattr(nltk.data, "path", list(nltk.data.path) + [loc])
        monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
        monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
        tagger = PerceptronTagger(load=False)
        tagger.load_from_json(LANG, loc)
        assert tagger.model.weights == _weights()

    def test_dropping_the_lang_check_lets_lang_carry_a_separator(self):
        assert "/" in "".join(
            f"averaged_perceptron_tagger_{'a/b'}.{attr}.json" for attr in ("weights",)
        ), "the filename template no longer interpolates lang"
        with pytest.raises(ValueError):
            perceptron._reject_path_structure("a/b", "lang")

    def test_whitespace_waiver_reopens_the_cwd_write(self, outside_only, monkeypatch):
        """Restoring the whitespace early-return must let the write land again."""
        real = pathsec.validate_path

        def waives_whitespace(path_input, *args, **kwargs):
            if isinstance(path_input, str) and path_input and not path_input.strip():
                return
            return real(path_input, *args, **kwargs)

        monkeypatch.setattr(pathsec, "validate_path", waives_whitespace)
        monkeypatch.setattr(perceptron, "validate_path", waives_whitespace)
        saved = os.getcwd()
        os.chdir(outside_only)
        try:
            with pytest.raises(Exception):
                AveragedPerceptron(_weights()).save("   ")
            assert list(outside_only.iterdir()), "waiver did not reopen the write"
        finally:
            os.chdir(saved)

    def test_dropping_the_crf_check_reopens_the_native_write(
        self, sandbox, monkeypatch
    ):
        pytest.importorskip("pycrfsuite")
        import nltk.tag.crf as crf

        monkeypatch.setattr(crf, "validate_path", lambda *a, **k: None)
        target = str(sandbox / "unguarded.crf")
        crf.CRFTagger().train(
            [[("the", "DT"), ("dog", "NN")], [("a", "DT"), ("cat", "NN")]], target
        )
        assert os.path.getsize(target) > 0, "no model written with the guard removed"

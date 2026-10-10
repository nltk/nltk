# Natural Language Toolkit: BllipParser model-path attack tests (expanded)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded attack tests for the BllipParser model paths (GHSA-fg9w-wfp5-j933,
CWE-22 / CWE-73 / CWE-400).

``parser_model``, ``reranker_features`` and ``reranker_weights`` reach the
``bllipparser`` C extension, which opens and reads them natively. The guard must
bound every spelling to the NLTK data roots before the extension is called, and
let a legitimate in-root model through verbatim.

The real extension is not required (and rarely builds on modern toolchains): a
spy ``RerankingParser`` records exactly what ``load_parser_model`` /
``load_reranker_model`` would have opened, and ``get_unified_model_parameters``
is replaced by a path-only shim, so a refused path leaves the spy untouched
while a benign one reaches it. Nothing about the containment check is mocked.
"""

import os
import socket

import pytest

import nltk.parse.bllip as bllip_module
import nltk.pathsec as pathsec
from nltk.test.unit import timing

REFUSED = (PermissionError, ValueError)


class _SpyRerankingParser:
    """Stand-in for the C extension that records the paths handed to it."""

    last = None

    def __init__(self):
        type(self).last = self
        self.parser_model = None
        self.reranker = None

    def load_parser_model(self, model_dir, **kw):
        self.parser_model = model_dir

    def load_reranker_model(self, features_filename, weights_filename, **kw):
        self.reranker = (features_filename, weights_filename)


def _unified_shim(model_dir):
    """A path-only ``get_unified_model_parameters``: joins the standard
    sub-paths without reading anything, as the real third-party helper does."""
    parser = os.path.join(model_dir, "parser")
    reranker = os.path.join(model_dir, "reranker")
    feats = os.path.join(reranker, "features.gz")
    weights = os.path.join(reranker, "weights.gz")
    return (
        parser if os.path.exists(parser) else model_dir,
        feats if os.path.exists(feats) else None,
        weights if os.path.exists(weights) else None,
    )


@pytest.fixture
def bllip_spy(monkeypatch):
    """Inject the spy extension so the guard runs even without bllipparser."""
    _SpyRerankingParser.last = None
    # When bllipparser is not installed these names are absent from the module
    # (the import is optional), so raising=False lets the spy stand in anyway.
    monkeypatch.setattr(
        bllip_module, "RerankingParser", _SpyRerankingParser, raising=False
    )
    monkeypatch.setattr(
        bllip_module, "get_unified_model_parameters", _unified_shim, raising=False
    )
    monkeypatch.setattr(
        bllip_module, "_ensure_bllip_import_or_error", lambda: None, raising=False
    )
    return _SpyRerankingParser


def _real_model_dir(root):
    """A benign, private parser model DIRECTORY inside the data root."""
    model = os.path.join(str(root), "model", "parser")
    os.makedirs(model, exist_ok=True)
    with open(os.path.join(model, "pSgT.txt"), "wb") as handle:
        handle.write(b"model data")
    return os.path.join(str(root), "model", "parser")


def _assert_parser_model_refused(path, spy):
    with pytest.raises(REFUSED):
        bllip_module.BllipParser(parser_model=path)
    assert spy.last is None, f"a refused parser_model reached the extension: {path!r}"


def _assert_reranker_refused(path, root, spy):
    """A hostile reranker file with a BENIGN in-root parser_model: construction
    must reach reranker validation and refuse the file before the extension."""
    model = _real_model_dir(root)
    with pytest.raises(REFUSED):
        bllip_module.BllipParser(
            parser_model=model, reranker_features=path, reranker_weights=path
        )
    assert (
        spy.last is None or spy.last.reranker is None
    ), f"a refused reranker path reached the extension: {path!r}"


class TestParserModelOutsideRootNeverReachesTheExtension:
    def test_absolute_outside_directory(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        target = outside / "evilmodel"
        target.mkdir()
        _assert_parser_model_refused(str(target), bllip_spy)

    def test_absolute_outside_file_as_model(self, pathsec_sandbox, bllip_spy):
        """The advisory's literal PoC: a FILE outside the roots as parser_model."""
        root, outside = pathsec_sandbox
        secret = outside / "secret"
        secret.write_bytes(b"root:x:0:0:")
        _assert_parser_model_refused(str(secret), bllip_spy)

    def test_traversal_out_of_the_root(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        escape = os.path.join(str(root), "..", os.path.basename(str(outside)))
        _assert_parser_model_refused(escape, bllip_spy)
        _assert_parser_model_refused("../" * 6 + "etc", bllip_spy)

    def test_symlink_inside_root_to_outside_directory(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        target = outside / "realmodel"
        target.mkdir()
        link = root / "linkmodel"
        os.symlink(str(target), str(link), target_is_directory=True)
        _assert_parser_model_refused(str(link), bllip_spy)

    def test_model_dir_with_a_symlink_member(self, pathsec_sandbox, bllip_spy):
        """A model dir inside the root whose member is a symlink pointing out is
        refused: another local user could swap the model file the loader reads."""
        root, outside = pathsec_sandbox
        secret = outside / "secret"
        secret.write_bytes(b"x")
        model = root / "planted"
        model.mkdir()
        os.symlink(str(secret), str(model / "pSgT.txt"))
        _assert_parser_model_refused(str(model), bllip_spy)


class TestRerankerFilesOutsideRootNeverReachTheExtension:
    def test_absolute_outside_feature_file(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        secret = outside / "features.gz"
        secret.write_bytes(b"x")
        _assert_reranker_refused(str(secret), root, bllip_spy)

    def test_traversal_reranker_file(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        _assert_reranker_refused("../" * 6 + "etc/passwd", root, bllip_spy)

    def test_symlink_reranker_file_to_outside(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        secret = outside / "secret.gz"
        secret.write_bytes(b"x")
        link = root / "feat.gz"
        os.symlink(str(secret), str(link))
        _assert_reranker_refused(str(link), root, bllip_spy)

    def test_hardlink_reranker_file_to_outside(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        secret = outside / "victim.gz"
        secret.write_bytes(b"original")
        planted = root / "hard.gz"
        try:
            os.link(str(secret), str(planted))
        except OSError:
            pytest.skip("cannot hardlink across these locations")
        _assert_reranker_refused(str(planted), root, bllip_spy)


class TestFromUnifiedModelDir:
    def test_outside_unified_dir_is_refused(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        unified = outside / "unified"
        (unified / "parser").mkdir(parents=True)
        with pytest.raises(REFUSED):
            bllip_module.BllipParser.from_unified_model_dir(str(unified))
        assert bllip_spy.last is None

    def test_symlinked_unified_dir_is_refused(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        (outside / "u" / "parser").mkdir(parents=True)
        link = root / "ulink"
        os.symlink(str(outside / "u"), str(link), target_is_directory=True)
        with pytest.raises(REFUSED):
            bllip_module.BllipParser.from_unified_model_dir(str(link))
        assert bllip_spy.last is None


class _LyingPath(str):
    """A str subclass that shows a benign path but IS a hostile one."""

    def __new__(cls, real, shown):
        obj = str.__new__(cls, real)
        obj._shown = shown
        return obj

    def __str__(self):
        return self._shown

    def startswith(self, *a, **k):
        return self._shown.startswith(*a, **k)

    def replace(self, *a, **k):
        return self._shown.replace(*a, **k)

    def split(self, *a, **k):
        return self._shown.split(*a, **k)

    def __contains__(self, item):
        return item in self._shown


class _ShiftingPath:
    """A PathLike that answers one path, then another, on successive calls."""

    def __init__(self, first, then):
        self._answers = [first, then]

    def __fspath__(self):
        return self._answers.pop(0) if len(self._answers) > 1 else self._answers[0]


class TestNamesThatAreNotPlainStrings:
    def test_lying_str_subclass_is_judged_on_real_characters(
        self, pathsec_sandbox, bllip_spy
    ):
        root, outside = pathsec_sandbox
        target = outside / "evil"
        target.mkdir()
        _assert_parser_model_refused(_LyingPath(str(target), str(root)), bllip_spy)

    def test_shifting_path_like_is_resolved_once(self, pathsec_sandbox, bllip_spy):
        """validate_tool_dir reads __fspath__ once and the extension gets that
        string; a second, outside answer is never opened."""
        root, outside = pathsec_sandbox
        good = _real_model_dir(root)
        outside_dir = outside / "evil"
        outside_dir.mkdir()
        shifting = _ShiftingPath(good, str(outside_dir))
        bllip_module.BllipParser(parser_model=shifting)
        assert bllip_spy.last.parser_model == good

    def test_bytes_and_none_model_are_handled(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        # None skips validation (the extension handles an absent model), so the
        # spy sees None; a bytes path outside the root is refused.
        bllip_module.BllipParser(parser_model=None)
        assert bllip_spy.last.parser_model is None
        bllip_spy.last = None
        with pytest.raises(REFUSED):
            bllip_module.BllipParser(parser_model=str(outside).encode() + b"/evil")
        assert bllip_spy.last is None


class TestSyntacticallyHostileNames:
    @pytest.mark.parametrize("name", ["-loadModel", "--model", "-", "-d"])
    def test_option_shaped_model_is_refused(self, pathsec_sandbox, bllip_spy, name):
        _assert_parser_model_refused(name, bllip_spy)

    @pytest.mark.parametrize("bad", ["\n", "\r", "\t", "\x0b", "\x0c", chr(0)])
    def test_control_characters_are_refused(self, pathsec_sandbox, bllip_spy, bad):
        root, outside = pathsec_sandbox
        _assert_parser_model_refused(str(root / ("m" + bad)), bllip_spy)

    @pytest.mark.parametrize(
        "name",
        [
            "~/model",
            "//server/share/model",
            "\\\\server\\share\\model",
            "file:///etc",
            "file://localhost/etc/passwd",
            "jar:/x",
        ],
    )
    def test_tilde_unc_and_url_are_refused(self, pathsec_sandbox, bllip_spy, name):
        _assert_parser_model_refused(name, bllip_spy)


class TestSpecialAndOversizedRerankerFiles:
    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_fifo_reranker_file_is_refused_without_blocking(
        self, pathsec_sandbox, bllip_spy
    ):
        root, outside = pathsec_sandbox
        fifo = str(root / "pipe.gz")
        os.mkfifo(fifo)
        finished, exc, _ = timing.finishes_within(
            10, lambda: _assert_reranker_refused(fifo, root, bllip_spy)
        )
        assert finished, "the reranker-path check blocked on a FIFO"
        assert exc is None, exc

    @pytest.mark.skipif(
        os.name != "posix" or not hasattr(socket, "AF_UNIX"), reason="POSIX only"
    )
    def test_unix_socket_reranker_file_is_refused(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        path = str(root / "s.gz")
        if len(path) > 100:
            pytest.skip("socket path too long for AF_UNIX here")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(path)
            _assert_reranker_refused(path, root, bllip_spy)
        finally:
            sock.close()

    def test_oversized_reranker_file_is_refused(self, pathsec_sandbox, bllip_spy):
        """A reranker file over the tool-model byte limit is refused: the
        extension would read it whole into memory (CWE-400)."""
        root, outside = pathsec_sandbox
        big = root / "features.gz"
        with open(big, "wb") as handle:
            handle.truncate(pathsec.MAX_TOOL_MODEL_BYTES + 1)
        _assert_reranker_refused(str(big), root, bllip_spy)


class TestBenignInRootModelReachesTheExtensionVerbatim:
    def test_parser_model_in_root_is_passed_through(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        model = _real_model_dir(root)
        bllip_module.BllipParser(parser_model=model)
        assert bllip_spy.last.parser_model == model

    def test_reranker_files_in_root_are_passed_through(
        self, pathsec_sandbox, bllip_spy
    ):
        root, outside = pathsec_sandbox
        model = _real_model_dir(root)
        reranker = root / "model" / "reranker"
        reranker.mkdir(parents=True, exist_ok=True)
        feats = reranker / "features.gz"
        weights = reranker / "weights.gz"
        feats.write_bytes(b"f")
        weights.write_bytes(b"w")
        bllip_module.BllipParser(
            parser_model=model,
            reranker_features=str(feats),
            reranker_weights=str(weights),
        )
        assert bllip_spy.last.reranker == (str(feats), str(weights))

    def test_from_unified_model_dir_in_root_loads(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        base = root / "unified"
        (base / "parser").mkdir(parents=True)
        (base / "parser" / "pSgT.txt").write_bytes(b"m")
        reranker = base / "reranker"
        reranker.mkdir()
        (reranker / "features.gz").write_bytes(b"f")
        (reranker / "weights.gz").write_bytes(b"w")
        bllip_module.BllipParser.from_unified_model_dir(str(base))
        assert bllip_spy.last.parser_model == str(base / "parser")


def _assert_parser_model_blocked(path, spy):
    """Like _assert_parser_model_refused but also accepts a structural OSError
    (a zip-member spelling is NotADirectory, not a security refusal), as long as
    the extension never saw the path."""
    with pytest.raises((PermissionError, ValueError, OSError)):
        bllip_module.BllipParser(parser_model=path)
    assert spy.last is None, f"a blocked parser_model reached the extension: {path!r}"


def _case_insensitive_fs(root):
    """True when the filesystem under *root* folds case (APFS/NTFS default)."""
    probe = os.path.join(str(root), "CaseProbe")
    os.makedirs(probe, exist_ok=True)
    return os.path.isdir(os.path.join(str(root), "caseprobe"))


class TestPercentEncodedNames:
    def test_percent_encoded_outside_path_is_refused(self, pathsec_sandbox, bllip_spy):
        """Percent escapes are not decoded by the extension; an outside path spelled
        with them is still refused by containment on the resolved path."""
        root, outside = pathsec_sandbox
        target = outside / "p%75nkt"
        target.mkdir()
        _assert_parser_model_refused(str(target), bllip_spy)

    def test_percent_encoded_traversal_is_literal_and_refused(
        self, pathsec_sandbox, bllip_spy
    ):
        """%2e%2e is a literal name, not a '..'; it resolves against the CWD,
        outside the root, and is refused there."""
        _assert_parser_model_refused("%2e%2e/%2e%2e/etc", bllip_spy)
        _assert_parser_model_refused("%2f".join(["..", "..", "etc"]), bllip_spy)

    def test_literal_percent_name_in_root_loads(self, pathsec_sandbox, bllip_spy):
        """A genuine in-root directory whose name contains a percent is a real
        filename and must still load (percent is not special to the filesystem)."""
        root, outside = pathsec_sandbox
        model = root / "my%20model"
        model.mkdir()
        (model / "pSgT.txt").write_bytes(b"m")
        bllip_module.BllipParser(parser_model=str(model))
        assert bllip_spy.last.parser_model == str(model)


class TestTrailingDotAndSpace:
    @pytest.mark.parametrize("suffix", [".", " ", "..", "  "])
    def test_trailing_dot_or_space_parser_model_is_refused(
        self, pathsec_sandbox, bllip_spy, suffix
    ):
        root, outside = pathsec_sandbox
        _assert_parser_model_refused(str(root / "model") + suffix, bllip_spy)

    @pytest.mark.parametrize("suffix", [".", " "])
    def test_trailing_dot_or_space_reranker_is_refused(
        self, pathsec_sandbox, bllip_spy, suffix
    ):
        root, outside = pathsec_sandbox
        _assert_reranker_refused(str(root / "features.gz") + suffix, root, bllip_spy)


class TestCaseFoldedSpellings:
    def test_case_swapped_outside_path_is_refused(self, pathsec_sandbox, bllip_spy):
        """A case-variant spelling of an outside path is judged on the resolved
        file and refused, whether or not the filesystem folds case."""
        root, outside = pathsec_sandbox
        target = outside / "Secret"
        target.mkdir()
        _assert_parser_model_refused(str(outside / "SECRET"), bllip_spy)
        _assert_parser_model_refused(str(outside / "secret"), bllip_spy)

    def test_kelvin_sign_outside_path_is_refused(self, pathsec_sandbox, bllip_spy):
        """A Kelvin sign (U+212A) folds to 'k' on APFS/NTFS; an outside path
        spelled with it is still refused by containment."""
        root, outside = pathsec_sandbox
        _assert_parser_model_refused(str(outside / "Key"), bllip_spy)

    def test_case_variant_of_in_root_model_resolves_in_root_and_loads(
        self, pathsec_sandbox, bllip_spy
    ):
        """On a case-insensitive filesystem an uppercased spelling resolves to the
        same in-root directory, so it must load (the check judges the resolved
        file, not the spelling)."""
        root, outside = pathsec_sandbox
        if not _case_insensitive_fs(root):
            pytest.skip("case-sensitive filesystem")
        model = root / "realmodel"
        model.mkdir()
        (model / "pSgT.txt").write_bytes(b"m")
        bllip_module.BllipParser(parser_model=str(root / "REALMODEL"))
        assert bllip_spy.last is not None and bllip_spy.last.parser_model


class TestDirectoryInRerankerFilePlace:
    def test_directory_where_a_reranker_file_is_expected_is_refused(
        self, pathsec_sandbox, bllip_spy
    ):
        """reranker_features is a FILE the loader reads whole; a directory in its
        place is refused (not a regular file)."""
        root, outside = pathsec_sandbox
        a_dir = root / "features_dir"
        a_dir.mkdir()
        _assert_reranker_refused(str(a_dir), root, bllip_spy)


class TestHardlinkMemberInModelDir:
    def test_hardlinked_member_pointing_outside_is_refused(
        self, pathsec_sandbox, bllip_spy
    ):
        """A model directory inside a root whose member is a hardlink to an
        outside file is refused: the loader would read the aliased outside inode
        and realpath cannot see the alias (CWE-59)."""
        root, outside = pathsec_sandbox
        secret = outside / "secret"
        secret.write_bytes(b"outside bytes")
        model = root / "hlmodel"
        model.mkdir()
        try:
            os.link(str(secret), str(model / "pSgT.txt"))
        except OSError:
            pytest.skip("cannot hardlink across these locations")
        _assert_parser_model_refused(str(model), bllip_spy)

    def test_model_dir_of_genuine_single_link_files_loads(
        self, pathsec_sandbox, bllip_spy
    ):
        root, outside = pathsec_sandbox
        model = root / "cleanmodel"
        model.mkdir()
        (model / "pSgT.txt").write_bytes(b"m")
        bllip_module.BllipParser(parser_model=str(model))
        assert bllip_spy.last.parser_model == str(model)


class TestModelDirOwnershipAndMode:
    @pytest.mark.skipif(os.name != "posix", reason="POSIX ownership check")
    @pytest.mark.parametrize("mode", [0o777, 0o775, 0o757])
    def test_group_or_world_writable_model_dir_is_refused(
        self, pathsec_sandbox, bllip_spy, mode
    ):
        """require_private refuses a model directory another local user could
        write, so a planted or swapped model is never handed to the loader."""
        root, outside = pathsec_sandbox
        model = root / "wwmodel"
        model.mkdir()
        (model / "pSgT.txt").write_bytes(b"m")
        os.chmod(str(model), mode)
        _assert_parser_model_refused(str(model), bllip_spy)

    def test_private_0700_model_dir_loads(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        model = root / "privmodel"
        model.mkdir()
        (model / "pSgT.txt").write_bytes(b"m")
        if os.name == "posix":
            os.chmod(str(model), 0o700)
        bllip_module.BllipParser(parser_model=str(model))
        assert bllip_spy.last.parser_model == str(model)


class TestZipMemberSpelling:
    def test_zip_member_parser_model_is_refused(self, pathsec_sandbox, bllip_spy):
        """A 'model.zip/parser' spelling is refused: the bllip loader reads a
        directory tree, not a zip member, and the path is not a real directory."""
        root, outside = pathsec_sandbox
        (root / "model.zip").write_bytes(b"PK\x03\x04")
        _assert_parser_model_blocked(str(root / "model.zip" / "parser"), bllip_spy)

    def test_zip_member_reranker_is_refused(self, pathsec_sandbox, bllip_spy):
        root, outside = pathsec_sandbox
        (root / "r.zip").write_bytes(b"PK\x03\x04")
        model = _real_model_dir(root)
        with pytest.raises((PermissionError, ValueError, OSError)):
            bllip_module.BllipParser(
                parser_model=model,
                reranker_features=str(root / "r.zip" / "features.gz"),
                reranker_weights=str(root / "r.zip" / "weights.gz"),
            )
        assert bllip_spy.last is None or bllip_spy.last.reranker is None


class TestProbeHasTeeth:
    def test_probe_is_fixed_here(self):
        from nltk.test.unit import security_probes as probes

        status, detail = probes.PROBES["GHSA-fg9w-wfp5-j933"]()
        assert status in (probes.FIXED, probes.STATIC), detail

    def test_probe_flips_when_guard_removed(self, monkeypatch):
        """Neuter the tool-path guards inside bllip.py and the probe must flip to
        VULNERABLE (an out-of-root model reaches the spy extension), then FIXED."""
        from nltk.test.unit import security_probes as probes

        probe = probes.PROBES["GHSA-fg9w-wfp5-j933"]
        if probe()[0] == probes.STATIC:
            pytest.skip("no outside-root target on this platform")
        monkeypatch.setattr(bllip_module, "validate_tool_dir", lambda v, *a, **k: v)
        monkeypatch.setattr(bllip_module, "validate_tool_path", lambda v, *a, **k: v)
        status, detail = probe()
        assert status == probes.VULNERABLE, detail
        monkeypatch.undo()
        assert probe()[0] == probes.FIXED
        assert bllip_module.validate_tool_dir is pathsec.validate_tool_dir

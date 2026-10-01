# Natural Language Toolkit: expanded attack harness for the maxent parameter files
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The maxent parameter-file loader and saver (``load_maxent_params`` /
``save_maxent_params``, GHSA-59f9-gqg8-mqpj / CVE-2026-15367 and
GHSA-8mgp-746c-j5xp, CWE-22) driven with every path shape an attacker can hand
them (outside the roots, ``..``, a symlink into or out of the root, a hardlink,
a FIFO, a directory, a NUL byte, bytes, lying str subclasses and two-faced or
flipping path objects, as ``str`` and as ``os.PathLike``), with hostile file
content (non-numeric, NaN, inf, huge exponents, wrong column counts, control,
bidi and terminal-escape characters in names, invalid UTF-8, an enormous
file), with hostile names at save time (the tab and line-break separators the
tab files cannot carry), with pickled models (hostile or genuine), with
hostile binary locations and option values at the megam/tadm entry points
(a trusted stub records what the tool receives; the real tools run when they
are installed), and with a real classifier trained on the names corpus,
saved, reloaded and compared probability for probability. Nothing is mocked:
every guard is the one the library ships, and a refusal is asserted by the
exception pathsec raises plus the untouched victim.
"""

import io
import os
import pathlib
import pickle
import random
import shutil
import tempfile
import zipfile

import pytest

numpy = pytest.importorskip("numpy")

import nltk.data
from nltk import pathsec
from nltk.classify.maxent import (
    BinaryMaxentFeatureEncoding,
    MaxentClassifier,
    TadmEventMaxentFeatureEncoding,
    TadmMaxentClassifier,
    load_maxent_params,
    save_maxent_params,
)
from nltk.data import FileSystemPathPointer, ZipFilePathPointer
from nltk.tabdata import MaxentDecoder
from nltk.test.unit import timing

POSIX = pytest.mark.skipif(
    os.name != "posix", reason="POSIX inode semantics (symlink, hardlink, FIFO, sh)"
)

#: seconds a refused open has before it counts as a hang (a FIFO blocks forever)
_NO_HANG_BUDGET = 10
#: seconds a real megam/tadm run has, as the budget and as the hang deadline
_TOOL_BUDGET = 600

RLO = chr(0x202E)
ESC = chr(0x1B)
NUL = chr(0x00)

FILES = (
    ("weights.txt", "0.5\n-1.25\n"),
    ("mapping.tab", "word\tcat\tL1\t0\nshape\tup\tL2\t1\n"),
    ("labels.txt", "L1\nL2\n"),
    ("alwayson.tab", ""),
)
EXPECTED = (
    [0.5, -1.25],
    {("word", "cat", "L1"): 0, ("shape", "up", "L2"): 1},
    ["L1", "L2"],
    {},
)

TRAIN = [
    (dict(a=1, b=1, c=1), "y"),
    (dict(a=1, b=1, c=1), "x"),
    (dict(a=1, b=1, c=0), "y"),
    (dict(a=0, b=1, c=1), "x"),
    (dict(a=0, b=1, c=1), "y"),
    (dict(a=0, b=0, c=1), "y"),
    (dict(a=0, b=1, c=0), "x"),
    (dict(a=0, b=0, c=0), "x"),
    (dict(a=0, b=1, c=1), "y"),
]


def _plant(directory, files=FILES):
    directory = pathlib.Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in files:
        (directory / name).write_text(body, encoding="utf-8", newline="")
    return directory


def _assert_loaded(result, expected=EXPECTED):
    wgt, mpg, lab, aon = result
    assert wgt.tolist() == expected[0]
    assert mpg == expected[1]
    assert lab == expected[2]
    assert aon == expected[3]


def _refused(fn, *args, **kwargs):
    """Run ``fn`` and return the PermissionError pathsec raised for it."""
    with pytest.raises(PermissionError) as info:
        fn(*args, **kwargs)
    assert "Security Violation" in str(info.value)
    return info.value


def _dotdot_to(root, target):
    """``root/../../..<target>``: a traversal spelling that resolves to target."""
    rel = os.path.relpath(str(target), str(root))
    return os.path.join(str(root), rel)


class _LyingStr(str):
    """A str whose every readable face names *shown* while its buffer is real."""

    def __new__(cls, real, shown):
        self = super().__new__(cls, real)
        self._shown = shown
        return self

    def __str__(self):
        return self._shown

    def __repr__(self):
        return repr(self._shown)

    def __eq__(self, other):
        return self._shown == other

    __hash__ = str.__hash__


class _TwoFaced:
    """``.path`` says one thing, ``__fspath__`` another."""

    def __init__(self, path, fspath):
        self.path = path
        self._fspath = fspath

    def __fspath__(self):
        return self._fspath

    def __str__(self):
        return self.path


class _Flipping:
    """``__fspath__`` answers *first* once, then *then* forever (TOCTOU bait)."""

    def __init__(self, first, then):
        self.calls, self.first, self.then = 0, first, then

    def __fspath__(self):
        self.calls += 1
        return self.first if self.calls == 1 else self.then


class _Returning:
    def __init__(self, value):
        self.value = value

    def __fspath__(self):
        return self.value


# ------------------------------------------------------------------------- #
# The loader: every path shape, as str, PathLike and PathPointer
# ------------------------------------------------------------------------- #
class TestLoaderPathShapes:
    @pytest.mark.parametrize(
        "spell", ["str", "path", "pointer", "trailing_slash", "dotdot_inside"]
    )
    def test_in_root_loads_for_every_spelling(self, pathsec_sandbox, spell):
        planted = _plant(pathsec_sandbox.root / "params")
        target = {
            "str": str(planted),
            "path": planted,
            "pointer": FileSystemPathPointer(str(planted)),
            "trailing_slash": str(planted) + os.sep,
            "dotdot_inside": os.path.join(str(planted), os.pardir, "params"),
        }[spell]
        _assert_loaded(load_maxent_params(target))

    @pytest.mark.parametrize("spell", ["str", "path", "pointer", "dotdot", "bytes"])
    def test_outside_root_is_refused_for_every_spelling(self, pathsec_sandbox, spell):
        root, outside = pathsec_sandbox
        planted = _plant(outside / "params")
        if spell == "bytes":
            # bytes never reach an open: the pointer's join refuses to mix them
            with pytest.raises(TypeError):
                load_maxent_params(os.fsencode(str(planted)))
            return
        target = {
            "str": str(planted),
            "path": planted,
            "pointer": FileSystemPathPointer(str(planted)),
            "dotdot": _dotdot_to(root, planted),
        }[spell]
        _refused(load_maxent_params, target)

    @POSIX
    def test_symlinked_directory_out_of_the_root_is_refused(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        planted = _plant(outside / "params")
        link = root / "link_out"
        os.symlink(str(planted), str(link))
        for target in (str(link), link, FileSystemPathPointer(str(link))):
            _refused(load_maxent_params, target)

    @POSIX
    def test_symlinked_directory_inside_the_root_loads(self, pathsec_sandbox):
        root = pathsec_sandbox.root
        planted = _plant(root / "params")
        link = root / "link_in"
        os.symlink(str(planted), str(link))
        _assert_loaded(load_maxent_params(str(link)))
        _assert_loaded(load_maxent_params(link))

    @POSIX
    @pytest.mark.parametrize("points", ["outside", "inside"])
    def test_symlinked_parameter_file_is_refused_wherever_it_points(
        self, pathsec_sandbox, points
    ):
        """A final-component symlink is refused even inside the root: data
        files are never symlinks, and O_NOFOLLOW makes the refusal atomic."""
        root, outside = pathsec_sandbox
        real = _plant((outside if points == "outside" else root) / "real")
        planted = _plant(root / "params")
        (planted / "weights.txt").unlink()
        os.symlink(str(real / "weights.txt"), str(planted / "weights.txt"))
        _refused(load_maxent_params, str(planted))

    @POSIX
    def test_hardlinked_parameter_file_to_an_outside_inode_is_refused(
        self, pathsec_sandbox
    ):
        root, outside = pathsec_sandbox
        victim = _plant(outside / "victim")
        planted = _plant(root / "params")
        (planted / "weights.txt").unlink()
        try:
            os.link(str(victim / "weights.txt"), str(planted / "weights.txt"))
        except OSError as exc:  # pragma: no cover (cross-device temp and home)
            pytest.skip(f"cannot hardlink across these filesystems: {exc}")
        exc = _refused(load_maxent_params, str(planted))
        assert "multiply-linked" in str(exc)

    @POSIX
    def test_fifo_parameter_file_is_refused_without_blocking(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "params")
        (planted / "weights.txt").unlink()
        os.mkfifo(str(planted / "weights.txt"))
        finished, exc, _ = timing.finishes_within(
            _NO_HANG_BUDGET, lambda: load_maxent_params(str(planted))
        )
        assert finished, "the open blocked on the FIFO instead of refusing it"
        assert isinstance(exc, PermissionError) and "FIFO" in str(exc)

    @POSIX
    def test_directory_named_as_a_parameter_file_is_refused(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "params")
        (planted / "weights.txt").unlink()
        (planted / "weights.txt").mkdir()
        _refused(load_maxent_params, str(planted))

    def test_regular_file_as_tab_dir_is_a_plain_os_error(self, pathsec_sandbox):
        afile = pathsec_sandbox.root / "afile"
        afile.write_text("not a directory", encoding="utf-8")
        with pytest.raises(OSError):
            load_maxent_params(str(afile))
        with pytest.raises(OSError):
            load_maxent_params(afile)

    @pytest.mark.parametrize("kind", ["str", "path"])
    def test_nul_byte_in_the_path_is_refused_before_any_open(
        self, pathsec_sandbox, kind
    ):
        planted = _plant(pathsec_sandbox.root / "params")
        raw = str(planted) + NUL + "evil"
        target = raw if kind == "str" else pathlib.Path(raw)
        with pytest.raises((OSError, ValueError)):
            load_maxent_params(target)

    @pytest.mark.parametrize(
        "target",
        [
            42,
            None,
            ["/a"],
            _Returning(42),
            _Returning(None),
        ],
        ids=["int", "none", "list", "pathlike_int", "pathlike_none"],
    )
    def test_non_path_objects_are_refused_cleanly(self, pathsec_sandbox, target):
        with pytest.raises(TypeError):
            load_maxent_params(target)

    def test_bytes_pathlike_never_reaches_an_open(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "params")
        with pytest.raises(TypeError):
            load_maxent_params(_Returning(os.fsencode(str(planted))))

    def test_lying_str_subclass_is_judged_by_its_real_buffer(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        inside = _plant(root / "params")
        planted = _plant(outside / "params")
        _refused(load_maxent_params, _LyingStr(str(planted), str(inside)))
        # and the reverse lie cannot make an in-root directory look refused
        _assert_loaded(load_maxent_params(_LyingStr(str(inside), str(planted))))

    def test_two_faced_pathlike_is_judged_by_the_face_a_native_open_uses(
        self, pathsec_sandbox
    ):
        root, outside = pathsec_sandbox
        inside = _plant(root / "params")
        planted = _plant(outside / "params")
        _refused(load_maxent_params, _TwoFaced(str(inside), str(planted)))
        _assert_loaded(load_maxent_params(_TwoFaced(str(planted), str(inside))))

    def test_flipping_pathlike_is_read_exactly_once(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        inside = _plant(root / "params")
        planted = _plant(outside / "params")
        bait = _Flipping(str(planted), str(inside))
        _refused(load_maxent_params, bait)
        assert bait.calls == 1
        bait = _Flipping(str(inside), str(planted))
        _assert_loaded(load_maxent_params(bait))
        assert bait.calls == 1

    def test_missing_directory_and_missing_file_are_plain_os_errors(
        self, pathsec_sandbox
    ):
        root = pathsec_sandbox.root
        with pytest.raises(OSError):
            load_maxent_params(str(root / "absent"))
        planted = _plant(root / "params")
        (planted / "alwayson.tab").unlink()
        with pytest.raises(OSError):
            load_maxent_params(str(planted))

    def test_zip_pointer_path_is_unchanged(self, pathsec_sandbox):
        """The pointer branch (what ``nltk.data.find`` returns for a zipped
        resource) is untouched by the wrapping of plain paths."""
        root = pathsec_sandbox.root
        archive = root / "params.zip"
        with zipfile.ZipFile(str(archive), "w") as zf:
            for name, body in FILES:
                zf.writestr("params/" + name, body)
        _assert_loaded(load_maxent_params(ZipFilePathPointer(str(archive), "params/")))


# ------------------------------------------------------------------------- #
# The loader: hostile file content (parsed as data, never evaluated)
# ------------------------------------------------------------------------- #
def _with(name, body):
    return tuple((n, body if n == name else b) for n, b in FILES)


class TestLoaderContent:
    @pytest.mark.parametrize(
        "body",
        ["0.5\nabc\n", "0x10\n", "0.5\n1\t2\n", "0.5\n__import__('os')\n", "1,5\n"],
        ids=["word", "hex", "tab", "code", "comma"],
    )
    def test_non_numeric_weights_are_refused(self, pathsec_sandbox, body):
        planted = _plant(pathsec_sandbox.root / "p", _with("weights.txt", body))
        with pytest.raises(ValueError):
            load_maxent_params(str(planted))

    def test_nan_inf_huge_exponents_and_digit_groups_parse_as_inert_floats(
        self, pathsec_sandbox
    ):
        body = "nan\ninf\n-inf\n1e999\n1e-999\n1_000\n +2.5 \n"
        planted = _plant(pathsec_sandbox.root / "p", _with("weights.txt", body))
        wgt = load_maxent_params(str(planted))[0]
        assert numpy.isnan(wgt[0])
        assert wgt[1] == numpy.inf and wgt[2] == -numpy.inf
        assert wgt[3] == numpy.inf and wgt[4] == 0.0
        assert wgt[5] == 1000.0 and wgt[6] == 2.5

    def test_empty_weights_file_loads_an_empty_vector(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "p", _with("weights.txt", ""))
        assert load_maxent_params(str(planted))[0].tolist() == []

    @pytest.mark.parametrize("ending", ["\r\n", "\r"], ids=["crlf", "cr"])
    def test_cr_line_endings_leave_a_stray_cr_on_every_label(
        self, pathsec_sandbox, ending
    ):
        """The reader splits rows at CR too but strips only the LF, so a file
        written with CR endings reloads its labels with a trailing CR: the
        reason the saver writes LF only (pinned in test_maxent_save_security).
        Numbers survive because float() and int() strip whitespace."""
        files = tuple((n, b.replace("\n", ending)) for n, b in FILES)
        planted = _plant(pathsec_sandbox.root / "p", files)
        wgt, mpg, lab, aon = load_maxent_params(str(planted))
        assert wgt.tolist() == EXPECTED[0] and mpg == EXPECTED[1] and aon == {}
        assert lab == ["L1\r", "L2\r"]

    @pytest.mark.parametrize(
        "body",
        ["a\tb\n", "a\tb\tc\td\te\n", "a\tb\tc\tx\n", "wordlen\tabc\tc\t0\n"],
        ids=["too_few_columns", "too_many_columns", "non_int_index", "wordlen_text"],
    )
    def test_malformed_mapping_rows_are_refused(self, pathsec_sandbox, body):
        planted = _plant(pathsec_sandbox.root / "p", _with("mapping.tab", body))
        with pytest.raises(ValueError):
            load_maxent_params(str(planted))

    def test_mapping_text_is_never_evaluated(self, pathsec_sandbox):
        body = "__reduce__\tos.system\tL1\t0\n__import__('os')\trepr-None\tL2\t1\n"
        planted = _plant(pathsec_sandbox.root / "p", _with("mapping.tab", body))
        mpg = load_maxent_params(str(planted))[1]
        assert mpg == {
            ("__reduce__", "os.system", "L1"): 0,
            ("__import__('os')", None, "L2"): 1,
        }

    def test_huge_index_is_an_int_not_an_overflow(self, pathsec_sandbox):
        body = "a\tb\tL1\t99999999999999999999999\n"
        planted = _plant(pathsec_sandbox.root / "p", _with("mapping.tab", body))
        assert load_maxent_params(str(planted))[1][("a", "b", "L1")] == 10**23 - 1

    @pytest.mark.parametrize(
        "body", ["L1\tx\n", "L1\n", "L1\t1\t2\n"], ids=["non_int", "one_col", "three"]
    )
    def test_malformed_alwayson_rows_are_refused(self, pathsec_sandbox, body):
        planted = _plant(pathsec_sandbox.root / "p", _with("alwayson.tab", body))
        with pytest.raises(ValueError):
            load_maxent_params(str(planted))

    def test_control_bidi_and_escape_characters_load_as_data(self, pathsec_sandbox):
        name = "w" + RLO + "x" + ESC + "[31m" + NUL + "y"
        files = (
            FILES[0],
            ("mapping.tab", name + "\tcat\tL1\t0\nshape\tup\tL2\t1\n"),
            ("labels.txt", "L1" + NUL + "\nL2" + ESC + "c\n"),
            FILES[3],
        )
        planted = _plant(pathsec_sandbox.root / "p", files)
        _, mpg, lab, _ = load_maxent_params(str(planted))
        assert (name, "cat", "L1") in mpg
        assert lab == ["L1" + NUL, "L2" + ESC + "c"]

    def test_invalid_utf8_is_refused(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "p")
        (planted / "labels.txt").write_bytes(b"\xff\xfeL1\n")
        with pytest.raises(UnicodeDecodeError):
            load_maxent_params(str(planted))

    def test_one_enormous_row_is_refused_in_bounded_time(self, pathsec_sandbox):
        planted = _plant(pathsec_sandbox.root / "p")
        (planted / "mapping.tab").write_text("a" * 20_000_000, encoding="utf-8")

        def op():
            with pytest.raises(ValueError):
                load_maxent_params(str(planted))

        ok, seconds = timing.within_budget(op, _NO_HANG_BUDGET, cpu_bound=True)
        assert ok, f"a 20 MB row took {seconds:.1f}s"

    def test_loader_cost_is_linear_in_the_file_size(self, pathsec_sandbox):
        """No absolute size cap exists (the data root is trusted); the cost
        of a large parameter set must stay linear so a big file is slow in
        proportion, never quadratically."""
        root = pathsec_sandbox.root
        dirs = {}
        for n in (50_000, 200_000):
            weights = "".join(f"{i * 0.001:.6f}\n" for i in range(n))
            mapping = "".join(f"f{i}\tv{i}\tL{i % 2}\t{i}\n" for i in range(n))
            dirs[n] = _plant(
                root / f"n{n}",
                (
                    ("weights.txt", weights),
                    ("mapping.tab", mapping),
                    ("labels.txt", "L0\nL1\n"),
                    ("alwayson.tab", "L0\t0\nL1\t1\n"),
                ),
            )
        timing.assert_subquadratic(
            lambda n: load_maxent_params(str(dirs[n])), 50_000, 200_000, cpu_bound=True
        )


# ------------------------------------------------------------------------- #
# Display: hostile names must never reach the terminal live
# ------------------------------------------------------------------------- #
class TestDisplaySanitisation:
    def _classifier(self, root):
        name = "w" + RLO + "x" + ESC + "[31m"
        files = (
            ("weights.txt", "2.5\n-1.0\n"),
            ("mapping.tab", name + "\tcat\tL1\t0\nshape\tup\tL2\t1\n"),
            ("labels.txt", "L1\nL2\n"),
            ("alwayson.tab", ""),
        )
        wgt, mpg, lab, aon = load_maxent_params(str(_plant(root / "p", files)))
        return MaxentClassifier(BinaryMaxentFeatureEncoding(lab, mpg), wgt), name

    def test_most_informative_features_escapes_bidi_and_terminal_controls(
        self, pathsec_sandbox, capsys
    ):
        classifier, name = self._classifier(pathsec_sandbox.root)
        classifier.show_most_informative_features(2)
        out = capsys.readouterr().out
        assert RLO not in out and ESC not in out
        assert "\\u202e" in out and "\\x1b" in out
        assert "shape" in out and "2.500" in out

    def test_explain_escapes_bidi_and_terminal_controls(self, pathsec_sandbox, capsys):
        classifier, name = self._classifier(pathsec_sandbox.root)
        classifier.explain({name: "cat", "shape": "up"})
        out = capsys.readouterr().out
        assert RLO not in out and ESC not in out
        assert "\\u202e" in out and "\\x1b" in out
        assert "TOTAL:" in out and "PROBS:" in out


# ------------------------------------------------------------------------- #
# The saver: path shapes beyond the outside and symlinked-dir cases already
# pinned in test_maxent_save_security and test_model_artifact_pathsec
# ------------------------------------------------------------------------- #
WGT = numpy.array([0.5, -1.25])
MPG = {("word", "cat", "L1"): 0, ("shape", "up", "L2"): 1}
LAB = ["L1", "L2"]
AON = {}


def _save(tab_dir, mpg=MPG, lab=LAB, aon=AON, wgt=WGT):
    return save_maxent_params(wgt, mpg, lab, aon, tab_dir=tab_dir)


class TestSaverPathShapes:
    def test_dotdot_out_of_the_root_is_refused_and_writes_nothing(
        self, pathsec_sandbox
    ):
        root, outside = pathsec_sandbox
        target = _dotdot_to(root, outside / "sv")
        _refused(_save, target)
        assert not (outside / "sv").exists()

    def test_pathlike_in_root_round_trips(self, pathsec_sandbox):
        target = pathsec_sandbox.root / "sv"
        assert os.fspath(_save(target)) == os.fspath(target)
        _assert_loaded(load_maxent_params(target))
        _assert_loaded(load_maxent_params(str(target)))

    def test_nul_byte_in_tab_dir_is_refused(self, pathsec_sandbox):
        exc = _refused(_save, str(pathsec_sandbox.root / ("sv" + NUL + "x")))
        assert "NUL" in str(exc)

    def test_lying_str_subclass_is_judged_by_its_real_buffer(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        _refused(_save, _LyingStr(str(outside / "sv"), str(root / "sv")))
        assert not (outside / "sv").exists()

    def test_two_faced_pathlike_is_refused_outright(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        exc = _refused(_save, _TwoFaced(str(root / "sv"), str(outside / "sv")))
        assert "two different files" in str(exc)
        assert not (outside / "sv").exists() and not (root / "sv").exists()

    def test_existing_regular_file_as_tab_dir_is_left_intact(self, pathsec_sandbox):
        afile = pathsec_sandbox.root / "afile"
        afile.write_text("keep me", encoding="utf-8")
        with pytest.raises(FileExistsError):
            _save(str(afile))
        assert afile.read_text(encoding="utf-8") == "keep me"

    @POSIX
    def test_symlink_at_a_parameter_file_never_writes_through_it(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        victim = outside / "victim.txt"
        victim.write_text("VICTIM", encoding="utf-8")
        target = root / "sv"
        target.mkdir()
        os.symlink(str(victim), str(target / "weights.txt"))
        _refused(_save, str(target))
        assert victim.read_text(encoding="utf-8") == "VICTIM"

    @POSIX
    def test_hardlink_at_a_parameter_file_is_refused_before_truncation(
        self, pathsec_sandbox
    ):
        root, outside = pathsec_sandbox
        victim = outside / "victim.txt"
        victim.write_text("VICTIM", encoding="utf-8")
        target = root / "sv"
        target.mkdir()
        try:
            os.link(str(victim), str(target / "weights.txt"))
        except OSError as exc:  # pragma: no cover (cross-device temp and home)
            pytest.skip(f"cannot hardlink across these filesystems: {exc}")
        exc = _refused(_save, str(target))
        assert "multiply-linked" in str(exc)
        assert victim.read_text(encoding="utf-8") == "VICTIM"

    @POSIX
    def test_fifo_at_a_parameter_file_is_refused_without_blocking(
        self, pathsec_sandbox
    ):
        target = pathsec_sandbox.root / "sv"
        target.mkdir()
        os.mkfifo(str(target / "weights.txt"))
        finished, exc, _ = timing.finishes_within(
            _NO_HANG_BUDGET, lambda: _save(str(target))
        )
        assert finished, "the open blocked on the FIFO instead of refusing it"
        assert isinstance(exc, PermissionError)


# ------------------------------------------------------------------------- #
# The saver: names the tab files cannot carry (the guard this PR adds)
# ------------------------------------------------------------------------- #
#: the column separator and every row boundary the loader's reader splits by
SEPARATORS = {
    "tab": "\t",
    "lf": "\n",
    "cr": "\r",
    "vt": chr(0x0B),
    "ff": chr(0x0C),
    "fs": chr(0x1C),
    "gs": chr(0x1D),
    "rs": chr(0x1E),
    "nel": chr(0x85),
    "ls": chr(0x2028),
    "ps": chr(0x2029),
}


class TestSaverSeparatorGuard:
    def test_refused_row_boundaries_equal_the_readers_definition_over_all_code_points(
        self,
    ):
        """The loader's stream reader splits rows with ``str.splitlines``; the
        guard must refuse exactly those code points (plus the tab), checked
        over all 1,114,112 of them so neither side can drift."""
        from nltk.classify.maxent import _holds_tab_file_separator

        splitting = {
            c for c in range(0x110000) if len(("a" + chr(c) + "b").splitlines()) != 1
        }
        assert splitting == {ord(s) for k, s in SEPARATORS.items() if k != "tab"}
        refused = {c for c in range(0x110000) if _holds_tab_file_separator(chr(c))}
        assert refused == splitting | {ord("\t")}
        assert not _holds_tab_file_separator("") and not _holds_tab_file_separator("ab")

    @pytest.mark.parametrize("sep", list(SEPARATORS), ids=list(SEPARATORS))
    def test_a_row_boundary_in_a_label_would_reload_as_two_labels(
        self, pathsec_sandbox, sep
    ):
        """Why the guard exists: written raw, as the saver once did, every row
        boundary splits the label on reload and the model silently changes
        (the tab instead breaks the mapping and always-on rows)."""
        if sep == "tab":
            planted = _plant(
                pathsec_sandbox.root / "p", _with("alwayson.tab", "L\t1\t2\n")
            )
            with pytest.raises(ValueError):
                load_maxent_params(str(planted))
            return
        body = "L" + SEPARATORS[sep] + "M\n"
        planted = _plant(pathsec_sandbox.root / "p", _with("labels.txt", body))
        # the reader keeps the boundary on the first row; rm_nl strips only LF
        kept = "" if sep == "lf" else SEPARATORS[sep]
        assert load_maxent_params(str(planted))[2] == ["L" + kept, "M"]

    @pytest.mark.parametrize("sep", list(SEPARATORS), ids=list(SEPARATORS))
    @pytest.mark.parametrize(
        "where", ["feature_name", "feature_value", "mapping_label", "label", "alwayson"]
    )
    def test_separator_is_refused_before_any_file_is_written(
        self, pathsec_sandbox, sep, where
    ):
        bad = "a" + SEPARATORS[sep] + "b"
        mpg, lab, aon = dict(MPG), list(LAB), dict(AON)
        if where == "feature_name":
            mpg = {(bad, "cat", "L1"): 0, ("shape", "up", "L2"): 1}
        elif where == "feature_value":
            mpg = {("word", bad, "L1"): 0, ("shape", "up", "L2"): 1}
        elif where == "mapping_label":
            mpg = {("word", "cat", bad): 0, ("shape", "up", "L2"): 1}
        elif where == "label":
            lab = ["L1", bad]
        else:
            aon = {bad: 2}
        target = pathsec_sandbox.root / "sv"
        with pytest.raises(ValueError, match="tab or line break"):
            _save(str(target), mpg=mpg, lab=lab, aon=aon)
        assert not target.exists(), "a refused save must leave no partial model"

    def test_refusal_names_the_component_with_escapes_only(self, pathsec_sandbox):
        with pytest.raises(ValueError) as info:
            _save(str(pathsec_sandbox.root / "sv"), lab=["L1", "x" + ESC + "[2J\ny"])
        message = str(info.value)
        assert ESC not in message and "\n" not in message
        assert "\\x1b" in message and "\\n" in message

    def test_default_destination_leaves_no_directory_behind_on_refusal(
        self, restricted_sandbox
    ):
        before = set(os.listdir(restricted_sandbox))
        with pytest.raises(ValueError):
            save_maxent_params(WGT, MPG, ["L1\tL2"], AON)
        assert set(os.listdir(restricted_sandbox)) == before

    @pytest.mark.parametrize(
        "name",
        [
            "a" + NUL + "b",
            "w" + RLO + "x" + ESC + "[31m",
            "a" + chr(0x01) + "b",
            "a" + chr(0x7F) + "b",
            "caf" + chr(0xE9),
            "two words",
            chr(0x4E2D) + chr(0x6587),
            "a" + chr(0x200B) + "b",
            "",
        ],
        ids=[
            "nul",
            "bidi_escape",
            "soh",
            "del",
            "accent",
            "space",
            "cjk",
            "zwsp",
            "empty",
        ],
    )
    def test_non_structural_characters_still_round_trip_exactly(
        self, pathsec_sandbox, name
    ):
        """Characters that are not column or row separators are data to the
        tab files and must keep round-tripping exactly, however odd: the
        display path, not the artifact, is where they are neutralised."""
        mpg = {(name, name, name): 0, ("shape", "up", "L2"): 1}
        lab = [name, "L2"]
        aon = {name: 2, "L2": 3}
        out = _save(str(pathsec_sandbox.root / "sv"), mpg=mpg, lab=lab, aon=aon)
        wgt, m, l, a = load_maxent_params(out)
        assert (wgt.tolist(), m, l, a) == (WGT.tolist(), mpg, lab, aon)

    def test_typed_values_still_round_trip_exactly(self, pathsec_sandbox):
        mpg = {
            ("wordlen", 7, "L1"): 0,
            ("has(a)", True, "L1"): 1,
            ("has(b)", False, "L2"): 2,
            ("suffix", None, "L2"): 3,
        }
        out = _save(
            str(pathsec_sandbox.root / "sv"),
            mpg=mpg,
            wgt=numpy.array([0.1, 0.2, 0.3, 0.4]),
        )
        assert load_maxent_params(out)[1] == mpg

    def test_guard_cost_is_linear_in_the_model_size(self, pathsec_sandbox):
        from nltk.classify.maxent import _reject_tab_file_separators

        models = {
            n: (
                {(f"f{i}", f"v{i}", f"L{i % 2}"): i for i in range(n)},
                ["L0", "L1"],
                {"L0": n, "L1": n + 1},
            )
            for n in (200_000, 800_000)
        }
        timing.assert_subquadratic(
            lambda n: _reject_tab_file_separators(*models[n]),
            200_000,
            800_000,
            cpu_bound=True,
        )


# ------------------------------------------------------------------------- #
# Pickled models: the tab files are the only artifact nltk.data.load accepts
# ------------------------------------------------------------------------- #
class _Gadget:
    """A REDUCE that creates *marker* when the unpickler lets it run."""

    def __init__(self, marker):
        self.marker = marker

    def __reduce__(self):
        return (os.makedirs, (self.marker,))


class TestPickledModels:
    def test_hostile_reduce_under_a_classifier_name_never_runs(self, pathsec_sandbox):
        root = pathsec_sandbox.root
        marker = root / "pwned"
        planted = root / "classifiers"
        planted.mkdir()
        (planted / "evil.pickle").write_bytes(
            pickle.dumps(_Gadget(str(marker)), protocol=pickle.HIGHEST_PROTOCOL)
        )
        with pytest.raises(pickle.UnpicklingError):
            nltk.data.load("classifiers/evil.pickle")
        assert not marker.exists()

    def test_a_genuine_pickled_classifier_is_refused_too(self, pathsec_sandbox):
        from nltk.picklesec import pickle_dumps

        root = pathsec_sandbox.root
        planted = root / "classifiers"
        planted.mkdir()
        classifier = MaxentClassifier.train(TRAIN, "gis", trace=0, max_iter=3)
        (planted / "model.pickle").write_bytes(pickle_dumps(classifier))
        with pytest.raises(pickle.UnpicklingError):
            nltk.data.load("classifiers/model.pickle")

    def test_an_oversized_pickled_model_is_refused_by_the_class_rule(
        self, pathsec_sandbox
    ):
        """Size is no way in: a model pickle of any size names a class global
        for its first object, and the restricted unpickler refuses every
        global, so the megabytes behind it are never reconstructed."""
        from nltk.picklesec import pickle_dumps

        root = pathsec_sandbox.root
        planted = root / "classifiers"
        planted.mkdir()
        mapping = {(f"f{i}", f"v{i}", f"L{i % 2}"): i for i in range(100_000)}
        encoding = BinaryMaxentFeatureEncoding(["L0", "L1"], mapping)
        model = MaxentClassifier(encoding, numpy.zeros(100_000))
        payload = pickle_dumps(model)
        assert len(payload) > 2_000_000
        (planted / "big.pickle").write_bytes(payload)
        with pytest.raises(pickle.UnpicklingError, match="forbidden"):
            nltk.data.load("classifiers/big.pickle")


# ------------------------------------------------------------------------- #
# The megam / tadm entry points
# ------------------------------------------------------------------------- #
def _private_home_dir(prefix):
    """A fresh private directory under $HOME, a trusted chain on every runner
    (a shared temp dir is not), so spawn_trusted accepts a stub placed in it."""
    return pathlib.Path(tempfile.mkdtemp(prefix=prefix, dir=str(pathlib.Path.home())))


def _record_file(path):
    """The NUL-separated argv the stub recorded, or None when it never ran."""
    try:
        raw = pathlib.Path(path).read_bytes()
    except FileNotFoundError:
        return None
    return raw.decode("utf-8").split(NUL)[:-1]


@pytest.fixture
def stub_home():
    home = _private_home_dir(".nltk_maxent_stub_")
    try:
        yield home
    finally:
        shutil.rmtree(home, ignore_errors=True)


def _megam_stub(directory, record):
    stub = directory / "megam"
    stub.write_text(
        "#!/bin/sh\n"
        f"for a in \"$@\"; do printf '%s\\000' \"$a\" >> '{record}'; done\n"
        "printf '0 0.5\\n1 -0.5\\n'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def _tadm_stub(directory, record, n_weights):
    weights = "".join("0.5\\n" for _ in range(n_weights))
    stub = directory / "tadm"
    stub.write_text(
        "#!/bin/sh\n"
        "prev=''; out=''\n"
        'for a in "$@"; do\n'
        f"  printf '%s\\000' \"$a\" >> '{record}'\n"
        '  if [ "$prev" = \'-params_out\' ]; then out="$a"; fi\n'
        '  prev="$a"\n'
        "done\n"
        f'if [ -n "$out" ]; then printf \'{weights}\' > "$out"; fi\n',
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


HOSTILE_OPTION = "5; rm -rf / #"
HOSTILE_LINES = "5\n-x\r\n$(id)"


class TestTrainerEntryPoints:
    @POSIX
    def test_untrusted_megam_binary_is_refused_before_it_runs(
        self, stub_home, restricted_sandbox, monkeypatch
    ):
        import nltk.classify.megam as megam

        record = stub_home / "argv"
        swappable = stub_home / "swappable"
        swappable.mkdir()
        stub = _megam_stub(swappable, record)
        swappable.chmod(0o777)
        monkeypatch.setattr(megam, "_megam_bin", str(stub))
        with pytest.raises(OSError, match="not on a trusted path"):
            MaxentClassifier.train(TRAIN, "megam", trace=0)
        assert _record_file(record) is None, "the untrusted binary ran"

    @POSIX
    def test_untrusted_tadm_binary_is_refused_before_it_runs(
        self, stub_home, restricted_sandbox, monkeypatch
    ):
        import nltk.classify.tadm as tadm

        record = stub_home / "argv"
        swappable = stub_home / "swappable"
        swappable.mkdir()
        stub = _tadm_stub(swappable, record, 1)
        swappable.chmod(0o777)
        monkeypatch.setattr(tadm, "_tadm_bin", str(stub))
        with pytest.raises(OSError, match="not on a trusted path"):
            TadmMaxentClassifier.train(TRAIN, trace=0)
        assert _record_file(record) is None, "the untrusted binary ran"

    @POSIX
    @pytest.mark.parametrize(
        "value", [HOSTILE_OPTION, HOSTILE_LINES], ids=["shell", "lines"]
    )
    def test_trusted_megam_receives_a_hostile_option_as_one_argument(
        self, stub_home, restricted_sandbox, monkeypatch, value
    ):
        """There is no shell between the trainer and the tool: a value with
        metacharacters or line breaks arrives as exactly one argv element."""
        import nltk.classify.megam as megam

        record = stub_home / "argv"
        monkeypatch.setattr(megam, "_megam_bin", str(_megam_stub(stub_home, record)))
        classifier = MaxentClassifier.train(TRAIN, "megam", trace=0, max_iter=value)
        assert isinstance(classifier, MaxentClassifier)
        argv = _record_file(record)
        assert argv is not None
        assert argv[argv.index("-maxi") + 1] == value
        assert argv.count(value) == 1

    @POSIX
    @pytest.mark.parametrize(
        "value", [HOSTILE_OPTION, HOSTILE_LINES], ids=["shell", "lines"]
    )
    def test_trusted_tadm_receives_a_hostile_method_as_one_argument(
        self, stub_home, restricted_sandbox, monkeypatch, value
    ):
        import nltk.classify.tadm as tadm

        record = stub_home / "argv"
        n = TadmEventMaxentFeatureEncoding.train(TRAIN).length()
        monkeypatch.setattr(tadm, "_tadm_bin", str(_tadm_stub(stub_home, record, n)))
        classifier = TadmMaxentClassifier.train(TRAIN, trace=0, algorithm=value)
        assert isinstance(classifier, MaxentClassifier)
        argv = _record_file(record)
        assert argv is not None
        assert argv[argv.index("-method") + 1] == value
        assert argv.count(value) == 1

    @POSIX
    def test_the_staged_tool_files_live_inside_the_data_root_and_are_removed(
        self, stub_home, restricted_sandbox, monkeypatch
    ):
        import nltk.classify.megam as megam

        record = stub_home / "argv"
        monkeypatch.setattr(megam, "_megam_bin", str(_megam_stub(stub_home, record)))
        MaxentClassifier.train(TRAIN, "megam", trace=0)
        trainfile = _record_file(record)[-1]
        root = os.path.realpath(restricted_sandbox)
        assert os.path.commonpath([os.path.realpath(trainfile), root]) == root
        assert not os.path.exists(trainfile)
        assert not os.path.exists(os.path.dirname(trainfile))

    @pytest.mark.parametrize(
        "location",
        [
            "megam; touch pwned",
            "./megam",
            "../megam",
            "megam" + NUL + "x",
            "/bin/sh -c 'touch pwned'",
            "megam\n/bin/sh",
        ],
        ids=["metachar", "dot", "dotdot", "nul", "sh_c", "newline"],
    )
    def test_hostile_binary_locations_never_configure_a_tool(
        self, location, monkeypatch, tmp_path
    ):
        import nltk.classify.megam as megam
        import nltk.classify.tadm as tadm

        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("MEGAM", raising=False)
        monkeypatch.delenv("TADM", raising=False)
        monkeypatch.setattr(megam, "_megam_bin", None)
        monkeypatch.setattr(tadm, "_tadm_bin", None)
        with pytest.raises((LookupError, ValueError, OSError)):
            megam.config_megam(location)
        with pytest.raises((LookupError, ValueError, OSError)):
            tadm.config_tadm(location)
        assert megam._megam_bin is None and tadm._tadm_bin is None
        assert not (tmp_path / "pwned").exists()


def _real_tool_configured(configure):
    """True when the real tool is installed; False only when it is absent."""
    try:
        configure()
    except LookupError:
        return False
    return True


class TestRealTools:
    """The real megam / tadm binaries, when installed: the trainer runs them
    through the trusted spawn, the result matches the GIS/IIS reference and the
    model round-trips. Absent tools skip with the reason stated."""

    RESULTS = [(0.16, 0.84), (0.46, 0.54), (0.41, 0.59), (0.76, 0.24)]
    TEST = [
        dict(a=1, b=0, c=1),
        dict(a=1, b=0, c=0),
        dict(a=0, b=1, c=1),
        dict(a=0, b=1, c=0),
    ]

    def _check(self, train, root):
        trained = []
        finished, exc, _ = timing.finishes_within(
            _TOOL_BUDGET, lambda: trained.append(train())
        )
        assert finished, f"the real tool did not finish within {_TOOL_BUDGET}s"
        if exc is not None:
            raise exc
        classifier = trained[0]
        for (px, py), featureset in zip(self.RESULTS, self.TEST):
            pdist = classifier.prob_classify(featureset)
            assert abs(pdist.prob("x") - px) < 1e-2, (pdist.prob("x"), px)
            assert abs(pdist.prob("y") - py) < 1e-2, (pdist.prob("y"), py)
        _round_trip_exactly(classifier, root, self.TEST)

    def test_real_megam(self, restricted_sandbox):
        import nltk.classify.megam as megam

        if not _real_tool_configured(megam.config_megam):
            pytest.skip("megam binary not installed (no MEGAM, nothing on PATH)")
        self._check(
            lambda: MaxentClassifier.train(TRAIN, "megam", trace=0, max_iter=1000),
            restricted_sandbox,
        )

    def test_real_tadm(self, restricted_sandbox):
        import nltk.classify.tadm as tadm

        if not _real_tool_configured(tadm.config_tadm):
            pytest.skip("tadm binary not installed (no TADM, nothing on PATH)")
        self._check(
            lambda: MaxentClassifier.train(TRAIN, "tadm", trace=0, max_iter=1000),
            restricted_sandbox,
        )


# ------------------------------------------------------------------------- #
# A real classifier: train on the names corpus, save, reload, compare exactly
# ------------------------------------------------------------------------- #
def _round_trip_exactly(classifier, root, featuresets):
    """Save *classifier*'s parameters under *root*, rebuild it from a str and a
    PathLike, and require every label and probability to be identical.

    A GIS model carries a correction feature on top of the mapping, so it is
    rebuilt as a ``GISEncoding`` with the model's own ``C``: the tab files do
    not store it, and only without always-on features does the default
    recomputation from the mapping give it back (asserted here). Every other
    encoding is a ``BinaryMaxentFeatureEncoding``."""
    from nltk.classify.maxent import GISEncoding

    encoding = classifier._encoding
    gis = isinstance(encoding, GISEncoding)
    out = save_maxent_params(
        classifier._weights,
        encoding._mapping,
        encoding._labels,
        encoding._alwayson or {},
        tab_dir=os.path.join(str(root), "model"),
    )
    rebuilt = []
    for spelling in (out, pathlib.Path(out)):
        wgt, mpg, lab, aon = load_maxent_params(spelling)
        if gis:
            again = GISEncoding(lab, mpg, alwayson_features=aon, C=encoding.C)
            if not aon:
                assert GISEncoding(lab, mpg).C == encoding.C
        else:
            again = BinaryMaxentFeatureEncoding(lab, mpg, alwayson_features=aon)
        rebuilt.append(MaxentClassifier(again, wgt))
    for other in rebuilt:
        assert other.labels() == classifier.labels()
        assert other._encoding.length() == encoding.length()
        for featureset in featuresets:
            want = classifier.prob_classify(featureset)
            got = other.prob_classify(featureset)
            assert got.max() == want.max()
            for label in classifier.labels():
                assert got.prob(label) == want.prob(label)
    return rebuilt[0]


def _name_features(name):
    """str, bool and the ``wordlen`` int only: the tab format's value types."""
    low = name.lower()
    features = {
        "first": low[0],
        "last": low[-1],
        "last2": low[-2:],
        "wordlen": len(name),
    }
    for vowel in "aeiouy":
        features[f"has({vowel})"] = vowel in low
    return features


def _names_split():
    """600 training and 200 test names, or a skip when the corpus is absent."""
    try:
        from nltk.corpus import names

        male = list(names.words("male.txt"))
        female = list(names.words("female.txt"))
    except LookupError as exc:
        pytest.skip(f"names corpus not installed: {str(exc).splitlines()[0]}")
    labelled = [(n, "male") for n in male] + [(n, "female") for n in female]
    random.Random(20260930).shuffle(labelled)
    train = [(_name_features(n), g) for n, g in labelled[:600]]
    test = [(_name_features(n), g) for n, g in labelled[600:800]]
    return train, test


@pytest.fixture(scope="module")
def names():
    return _names_split()


class TestRealClassifierRoundTrip:
    @pytest.mark.parametrize(
        "algorithm, iterations", [("gis", 10), ("iis", 2)], ids=["gis", "iis"]
    )
    def test_trained_model_with_always_on_features_reloads_identically(
        self, names, restricted_sandbox, algorithm, iterations, capsys
    ):
        """The NE chunker's shape: an always-on encoding, trained, saved as tab
        files, rebuilt from them, and identical on every test probability."""
        from nltk.classify.maxent import GISEncoding
        from nltk.classify.util import accuracy

        train, test = names
        encoding = BinaryMaxentFeatureEncoding.train(train, alwayson_features=True)
        if algorithm == "gis":
            # GIS's default C (distinct feature names + 1) leaves no room for
            # the always-on feature, so it is given explicitly, as a user must
            names_seen = {fname for fname, _, _ in encoding._mapping}
            encoding = GISEncoding(
                encoding._labels,
                encoding._mapping,
                alwayson_features=True,
                C=len(names_seen) + 2,
            )
        classifier = MaxentClassifier.train(
            train, algorithm, trace=0, encoding=encoding, max_iter=iterations
        )
        acc = accuracy(classifier, test)
        assert acc > 0.5, f"{algorithm} learnt nothing: accuracy {acc:.3f}"
        rebuilt = _round_trip_exactly(
            classifier, restricted_sandbox, [f for f, _ in test]
        )
        assert accuracy(rebuilt, test) == acc
        rebuilt.show_most_informative_features(5)
        rebuilt.explain(test[0][0])
        out = capsys.readouterr().out
        assert "last2" in out or "first" in out or "has(" in out
        assert "PROBS:" in out

    @pytest.mark.parametrize("algorithm", ["gis", "iis"])
    def test_default_encoding_without_always_on_reloads_identically(
        self, names, restricted_sandbox, algorithm
    ):
        train, test = names
        classifier = MaxentClassifier.train(train, algorithm, trace=0, max_iter=2)
        assert classifier._encoding._alwayson is None
        _round_trip_exactly(classifier, restricted_sandbox, [f for f, _ in test])

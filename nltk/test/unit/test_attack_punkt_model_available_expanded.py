# Natural Language Toolkit: punkt_model_available and the Punkt language name, attacked
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``nltk.tokenize.punkt_model_available(language)`` (#3936) answers whether
``sent_tokenize`` can load the Punkt model for *language*. It is a try/except
around the tokenizer's own cached load, so its answer is the tokenizer's, and
the language name is checked in ``PunktTokenizer.load_lang`` before
``nltk.data.find`` sees it. Attacked here with real files in an enforced data
root, nothing replaced:

* a name that is not one model directory (traversal, absolute, drive, NUL,
  line breaks, empty, regex metacharacters, a 10 KB path, decomposed Unicode,
  a Windows device) raises ValueError from the function and from every
  tokenizer entry point alike, and ``find()`` is never called;
* a non-str raises TypeError, and a str subclass is judged on its real
  characters, whatever its methods claim;
* for every layout of the model on disk (complete, missing a file, empty, a
  FIFO, a directory or an unreadable file in a file's place, links out of the
  root and inside it, hard links, zip-only, a zip bomb, roots that shadow one
  another, case and normalisation variants) the function and the tokenizer
  give the same answer: True and a split, False and a LookupError naming the
  download, or the same refusal;
* ``find()`` stays linear in the number of components of a name, and on its
  own it would resolve a traversal name to another directory, so the name
  check is what keeps those out;
* every language of the real punkt_tab is available and tokenizes.

Control and lookalike characters are built with chr().
"""

import contextlib
import os
import stat
import sys
import unicodedata
import zipfile

import pytest

import nltk
import nltk.data
from nltk.data import find
from nltk.test.unit import timing
from nltk.test.unit.test_attack_downloader_zip_expanded import (
    assert_lines_clean,
    needs_symlink,
    patch_declared_size,
    tree,
)
from nltk.tokenize import (
    PunktTokenizer,
    _get_punkt_tokenizer,
    punkt_model_available,
    sent_tokenize,
    word_tokenize,
)

ESC, BEL, NEL, RLO, ZWSP = chr(27), chr(7), chr(0x85), chr(0x202E), chr(0x200B)
#: A four-file punkt_tab model: "zzq" is an abbreviation, so only this model
#: splits SAMPLE into SPLIT.
MODEL = {
    "abbrev_types.txt": b"zzq\n",
    "collocations.tab": b"",
    "ortho_context.tab": b"",
    "sent_starters.txt": b"",
}
SAMPLE = "I met zzq. Smith today. Then we left."
SPLIT = ["I met zzq. Smith today.", "Then we left."]
POSIX = pytest.mark.skipif(os.name != "posix", reason="POSIX file types and modes")


def write_model(directory, files=MODEL):
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in files.items():
        (directory / name).write_bytes(data)


@pytest.fixture
def punkt_root(pathsec_sandbox):
    """An enforced data root holding an english model, an outside dir, and no
    tokenizer cached before or after."""
    root, outside = pathsec_sandbox
    write_model(root / "tokenizers" / "punkt_tab" / "english")
    _get_punkt_tokenizer.cache_clear()
    yield root, outside
    _get_punkt_tokenizer.cache_clear()


@contextlib.contextmanager
def calls_to(func):
    """The resource names *func* (nltk.data.find) is called with while the
    block runs, seen through the interpreter's call events."""
    code, seen = func.__code__, []
    previous = sys.getprofile()

    def profile(frame, event, arg):
        if event == "call" and frame.f_code is code:
            seen.append(frame.f_locals.get("resource_name"))

    sys.setprofile(profile)
    try:
        yield seen
    finally:
        sys.setprofile(previous)


def answer(fn, *args, **kwargs):
    """(kind, detail): ("value", result) or (exception class name, message)."""
    _get_punkt_tokenizer.cache_clear()
    try:
        return "value", fn(*args, **kwargs)
    except Exception as exc:  # the kind of failure is what is compared
        return type(exc).__name__, str(exc)
    finally:
        _get_punkt_tokenizer.cache_clear()


def assert_parity(language):
    """The function and the tokenizer agree; return the function's answer."""
    available = answer(punkt_model_available, language)
    split = answer(sent_tokenize, SAMPLE, language=language)
    if available == ("value", True):
        assert split == ("value", SPLIT), split
    elif available == ("value", False):
        assert split[0] == "LookupError", split
        assert "nltk.download('punkt_tab')" in split[1], split
    else:
        assert split[0] == available[0], (available, split)
    return available


def assert_untouched(root, outside, before):
    assert tree(str(root)) == before
    assert list(outside.iterdir()) == []


# ===========================================================================
# 1. A name that is not one model directory never reaches find()
# ===========================================================================
REFUSED_NAMES = {
    "dot": ".",
    "dot-dot": "..",
    "up-two": "../..",
    "model-then-up": "english/..",
    "into-a-sibling": "english/../german",
    "out-of-the-root": "../../../../etc/passwd",
    "absolute": "/etc",
    "absolute-model": "/english",
    "trailing-slash": "english/",
    "backslash": "english\\german",
    "drive": "C:\\",
    "drive-relative": "C:english",
    "unc": "\\\\server\\share",
    "home": "~",
    "home-of-root": "~root",
    "percent-dots": "%2e%2e",
    "percent-slash": "%2fetc",
    "nltk-protocol": "nltk:english",
    "file-url": "file:english",
    "http-url": "http://127.0.0.1/english",
    "nul": "english" + chr(0),
    "line-feed": "english\n",
    "carriage-return": "english\r",
    "tab": "english\t",
    "next-line": "english" + NEL,
    "escape-sequence": ESC + "[2Jenglish",
    "bell": "english" + BEL,
    "rlo": RLO + "hsilgne",
    "zero-width": "eng" + ZWSP + "lish",
    "empty": "",
    "space": " ",
    "trailing-space": "english ",
    "leading-space": " english",
    "trailing-dot": "english.",
    "dotted-version": "en.v2",
    "stream-colon": "english:stream",
    "pipe": "english|x",
    "star": "english*",
    "question": "english?",
    "quote": '"english"',
    "angle": "<english>",
    "hash": "english#x",
    "regex-nested-plus": "(a+)+$",
    "regex-dot-star": ".*",
    "regex-class": "[a-z]+",
    "regex-bound": "a{1,99999}",
    "regex-escape": "\\d+",
    "decomposed": "engli" + "s" + chr(0x30C) + "h",
    "long-path": "a/" * 5000,
    "long-name-with-a-slash": "a" * 10_000 + "/",
}


@pytest.mark.parametrize("label", sorted(REFUSED_NAMES))
def test_a_name_that_is_not_one_model_directory_is_refused_before_find(
    punkt_root, label
):
    root, outside = punkt_root
    name = REFUSED_NAMES[label]
    before = tree(str(root))
    entry_points = [
        lambda: punkt_model_available(name),
        lambda: sent_tokenize(SAMPLE, language=name),
        lambda: word_tokenize(SAMPLE, language=name),
        lambda: PunktTokenizer(name),
    ]
    with calls_to(find) as finds, timing.budget(5, "a refused name costs nothing"):
        for call in entry_points:
            _get_punkt_tokenizer.cache_clear()
            with pytest.raises(
                ValueError, match="Invalid Punkt language name"
            ) as caught:
                call()
            assert_lines_clean(str(caught.value))
    assert finds == []
    assert_untouched(root, outside, before)


WINDOWS_DEVICES = ["CON", "nul", "COM1", "lpt9", "COM" + chr(0xB9), "LPT" + chr(0xB3)]


@pytest.mark.parametrize("name", WINDOWS_DEVICES, ids=ascii)
def test_a_device_name_is_refused_where_it_names_a_device(punkt_root, name):
    if os.name != "posix":
        with pytest.raises(ValueError, match="Invalid Punkt language name"):
            punkt_model_available(name)
        with pytest.raises(ValueError, match="Invalid Punkt language name"):
            sent_tokenize(SAMPLE, language=name)
    else:
        assert assert_parity(name) == ("value", False)


# ===========================================================================
# 2. A non-str, and a str subclass that lies about its characters
# ===========================================================================
@pytest.mark.parametrize(
    "value",
    [5, 5.0, None, True, b"english", bytearray(b"english"), ["english"]],
    ids=lambda v: type(v).__name__,
)
def test_a_non_str_is_a_type_error_everywhere(punkt_root, value):
    with calls_to(find) as finds:
        for call in (
            lambda: punkt_model_available(value),
            lambda: sent_tokenize(SAMPLE, language=value),
            lambda: PunktTokenizer(value),
        ):
            _get_punkt_tokenizer.cache_clear()
            with pytest.raises(TypeError):
                call()
    assert finds == []


def _lying(real, shown, *methods):
    """A str holding *real* whose *methods* all claim *shown*."""
    body = {
        "__iter__": lambda self: iter(shown),
        "__str__": lambda self: shown,
        "__format__": lambda self, spec: shown,
        "__eq__": lambda self, other: shown == other,
        "__hash__": lambda self: hash(shown),
        "__getitem__": lambda self, key: shown[key],
        "__len__": lambda self: len(shown),
    }
    return type("Lying", (str,), {m: body[m] for m in methods})(real)


LIES = {
    "iter": ("__iter__",),
    "str": ("__str__",),
    "format": ("__format__",),
    "eq-and-hash": ("__eq__", "__hash__"),
    "getitem-and-len": ("__getitem__", "__len__"),
    "all-of-them": ("__iter__", "__str__", "__format__", "__getitem__", "__len__"),
}


@pytest.mark.parametrize("lie", sorted(LIES))
def test_a_traversal_dressed_as_a_model_name_is_judged_on_its_real_characters(
    punkt_root, lie
):
    root, outside = punkt_root
    before = tree(str(root))
    name = _lying("english/../english", "english", *LIES[lie])
    with calls_to(find) as finds:
        with pytest.raises(ValueError, match=r"'english/\.\./english'"):
            punkt_model_available(name)
        _get_punkt_tokenizer.cache_clear()
        with pytest.raises(ValueError, match=r"'english/\.\./english'"):
            PunktTokenizer(name)
    assert finds == []
    assert_untouched(root, outside, before)


@pytest.mark.parametrize("lie", sorted(LIES))
def test_a_model_name_dressed_as_a_traversal_is_looked_up_as_itself(punkt_root, lie):
    name = _lying("english", "../..", *LIES[lie])
    with calls_to(find) as finds:
        assert punkt_model_available(name) is True
    assert finds and set(finds) == {"tokenizers/punkt_tab/english/"}


def test_a_name_that_equals_a_cached_model_does_not_borrow_it(punkt_root):
    # lru_cache keys a str subclass apart from a str, so a lie equal to a
    # cached "english" is still checked, on its real characters
    assert punkt_model_available("english") is True
    name = _lying("../..", "english", "__eq__", "__hash__")
    with calls_to(find) as finds:
        with pytest.raises(ValueError, match=r"'\.\./\.\.'"):
            punkt_model_available(name)
        with pytest.raises(ValueError, match=r"'\.\./\.\.'"):
            sent_tokenize(SAMPLE, language=name)
    assert finds == []


# ===========================================================================
# 3. Every layout of the model on disk: the function and the tokenizer agree
# ===========================================================================
def _model_dir(root, language="english"):
    return root / "tokenizers" / "punkt_tab" / language


def test_a_complete_model_is_available_and_splits(punkt_root):
    assert assert_parity("english") == ("value", True)
    assert assert_parity("german") == ("value", False)


@pytest.mark.parametrize("missing", sorted(MODEL))
def test_a_model_missing_one_file_is_not_available(punkt_root, missing):
    root, outside = punkt_root
    (_model_dir(root) / missing).unlink()
    assert assert_parity("english") == ("value", False)
    kind, message = answer(sent_tokenize, SAMPLE, language="english")
    assert kind == "LookupError" and missing in message


def test_an_empty_model_directory_is_not_available(punkt_root):
    root, outside = punkt_root
    _model_dir(root, "danish").mkdir()
    assert find("tokenizers/punkt_tab/danish/")
    assert assert_parity("danish") == ("value", False)


def test_a_directory_in_a_files_place_is_refused_alike(punkt_root):
    root, outside = punkt_root
    (_model_dir(root) / "collocations.tab").unlink()
    (_model_dir(root) / "collocations.tab").mkdir()
    kind, message = assert_parity("english")
    assert kind == "PermissionError" and "Security Violation" in message


@POSIX
def test_a_fifo_in_a_files_place_is_refused_alike_and_never_blocks(punkt_root):
    root, outside = punkt_root
    (_model_dir(root) / "sent_starters.txt").unlink()
    os.mkfifo(_model_dir(root) / "sent_starters.txt")
    with timing.budget(5, "a FIFO is refused, not opened and waited on"):
        kind, message = assert_parity("english")
    assert kind == "PermissionError" and "Security Violation" in message


@POSIX
def test_an_unreadable_file_is_refused_alike(punkt_root):
    if os.geteuid() == 0:
        pytest.skip("root reads a mode 000 file")
    root, outside = punkt_root
    os.chmod(_model_dir(root) / "abbrev_types.txt", 0)
    try:
        kind, message = assert_parity("english")
    finally:
        os.chmod(_model_dir(root) / "abbrev_types.txt", 0o600)
    assert kind == "PermissionError"


@POSIX
def test_a_hard_linked_file_is_refused_alike(punkt_root):
    root, outside = punkt_root
    other = root / "elsewhere.txt"
    other.write_bytes(b"zzq\n")
    (_model_dir(root) / "abbrev_types.txt").unlink()
    os.link(other, _model_dir(root) / "abbrev_types.txt")
    kind, message = assert_parity("english")
    assert kind == "PermissionError" and "multiply-linked" in message
    assert other.read_bytes() == b"zzq\n"


@needs_symlink
def test_a_model_directory_linked_out_of_the_root_is_refused_alike(punkt_root):
    root, outside = punkt_root
    write_model(outside / "english")
    before = tree(str(outside))
    os.symlink(outside / "english", _model_dir(root, "danish"))
    kind, message = assert_parity("danish")
    assert kind == "PermissionError" and "Unauthorized path" in message
    assert tree(str(outside)) == before


@needs_symlink
def test_a_model_file_linked_out_of_the_root_is_refused_alike(punkt_root):
    root, outside = punkt_root
    (outside / "abbrev_types.txt").write_bytes(b"zzq\n")
    (_model_dir(root) / "abbrev_types.txt").unlink()
    os.symlink(outside / "abbrev_types.txt", _model_dir(root) / "abbrev_types.txt")
    kind, message = assert_parity("english")
    assert kind == "PermissionError" and "Unauthorized path" in message
    assert (outside / "abbrev_types.txt").read_bytes() == b"zzq\n"


@needs_symlink
def test_a_model_directory_linked_inside_the_root_is_available(punkt_root):
    root, outside = punkt_root
    write_model(root / "models" / "danish")
    os.symlink(root / "models" / "danish", _model_dir(root, "danish"))
    assert assert_parity("danish") == ("value", True)


@needs_symlink
def test_a_data_root_reached_through_a_link_serves_its_model(punkt_root, monkeypatch):
    root, outside = punkt_root
    link = root.parent / (root.name + "_link")
    os.symlink(root, link)
    try:
        monkeypatch.setattr(nltk.data, "path", [str(link)])
        assert assert_parity("english") == ("value", True)
    finally:
        os.unlink(link)


@POSIX
def test_a_world_writable_root_is_judged_alike(punkt_root):
    # every nltk.data.path entry is a data root by develop's policy, writable
    # or not: the function says what the tokenizer does, nothing looser
    root, outside = punkt_root
    os.chmod(root, 0o777)
    try:
        assert assert_parity("english") == ("value", True)
    finally:
        os.chmod(root, 0o700)


def test_an_empty_directory_in_an_earlier_root_shadows_a_later_model(
    punkt_root, monkeypatch
):
    root, outside = punkt_root
    first = root / "first"
    _model_dir(first).mkdir(parents=True)
    monkeypatch.setattr(nltk.data, "path", [str(first), str(root)])
    assert assert_parity("english") == ("value", False)


def _zip_model(path, files=MODEL, language="english"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in files.items():
            zf.writestr(f"punkt_tab/{language}/{name}", data)


def test_a_zipped_model_is_available(punkt_root):
    root, outside = punkt_root
    _zip_model(root / "tokenizers" / "punkt_tab.zip", language="danish")
    assert assert_parity("danish") == ("value", True)


@pytest.mark.parametrize("missing", sorted(MODEL))
def test_a_zipped_model_missing_one_file_is_not_available(punkt_root, missing):
    root, outside = punkt_root
    files = {k: v for k, v in MODEL.items() if k != missing}
    _zip_model(root / "tokenizers" / "punkt_tab.zip", files, language="danish")
    assert assert_parity("danish") == ("value", False)


def test_a_zipped_model_declaring_a_bomb_is_refused_alike(punkt_root):
    root, outside = punkt_root
    path = root / "tokenizers" / "punkt_tab.zip"
    _zip_model(path, language="danish")
    member = "punkt_tab/danish/ortho_context.tab"
    path.write_bytes(patch_declared_size(path.read_bytes(), member, 0xFFFFFFFF))
    kind, message = assert_parity("danish")
    assert kind == "ValueError" and "zip bomb" in message, (kind, message)


def test_find_keeps_a_zip_traversal_inside_the_root_or_refuses_it(punkt_root):
    root, outside = punkt_root
    _zip_model(root / "tokenizers" / "punkt_tab.zip", language="danish")
    inside = find("tokenizers/punkt_tab.zip/../")
    assert os.path.realpath(str(inside)).startswith(os.path.realpath(str(root)))
    with pytest.raises(ValueError, match="Unsafe resource path"):
        find("tokenizers/punkt_tab.zip/../../../")


def test_a_case_variant_is_answered_as_the_filesystem_answers(punkt_root):
    root, outside = punkt_root
    probe = root / "Case-Probe"
    probe.write_bytes(b"")
    folds_case = (root / "case-probe").exists()
    probe.unlink()
    assert assert_parity("ENGLISH") == ("value", folds_case)


def test_a_composed_name_finds_a_decomposed_directory_only_where_they_are_one(
    punkt_root,
):
    root, outside = punkt_root
    composed = "portugu" + chr(0xEA) + "s"
    write_model(_model_dir(root, unicodedata.normalize("NFD", composed)))
    found = os.path.exists(_model_dir(root, composed))
    assert assert_parity(composed) == ("value", found)


# ===========================================================================
# 4. find() itself: linear in a name's components, and no guard of its own
# ===========================================================================
def test_find_is_linear_in_the_number_of_components(punkt_root):
    def lookup(components):
        with contextlib.suppress(LookupError):
            find("tokenizers/punkt_tab/" + "a/" * components)

    timing.assert_subquadratic(lookup, 500, 2000, cpu_bound=True)


def test_a_long_single_segment_name_is_looked_up_in_linear_time(punkt_root):
    def available(length):
        assert punkt_model_available("a" * length) is False

    timing.assert_subquadratic(available, 25_000, 100_000, cpu_bound=True)


def test_find_alone_resolves_a_traversal_name_to_another_directory(punkt_root):
    # what the name check stands in front of: without it "english/.." and
    # ".." would read the punkt_tab and tokenizers directories as a model
    root, outside = punkt_root
    punkt_tab = os.path.realpath(str(root / "tokenizers" / "punkt_tab"))
    assert os.path.realpath(str(find("tokenizers/punkt_tab/english/../"))) == punkt_tab
    tokenizers = os.path.dirname(punkt_tab)
    assert os.path.realpath(str(find("tokenizers/punkt_tab/../"))) == tokenizers


# ===========================================================================
# 5. The loaded model is kept: the answer stays the tokenizer's
# ===========================================================================
def test_a_model_removed_after_loading_is_still_served_by_both(punkt_root):
    root, outside = punkt_root
    assert punkt_model_available("english") is True
    for name in MODEL:
        (_model_dir(root) / name).unlink()
    assert punkt_model_available("english") is True
    assert sent_tokenize(SAMPLE, language="english") == SPLIT
    _get_punkt_tokenizer.cache_clear()
    assert punkt_model_available("english") is False


# ===========================================================================
# 6. The real punkt_tab: every language it holds is available and splits
# ===========================================================================
def _real_languages():
    try:
        model = find("tokenizers/punkt_tab/")
    except (LookupError, ValueError):
        return None
    if isinstance(model, nltk.data.ZipFilePathPointer):
        names = model.zipfile.namelist()
        return sorted({n.split("/")[1] for n in names if n.count("/") >= 2})
    return sorted(
        n for n in os.listdir(str(model)) if os.path.isdir(os.path.join(str(model), n))
    )


def test_every_language_of_the_real_punkt_tab_is_available_and_splits():
    languages = _real_languages()
    if not languages:
        pytest.skip("the real punkt_tab is not installed here")
    assert len(languages) >= 18 and "english" in languages
    _get_punkt_tokenizer.cache_clear()
    try:
        for language in languages:
            assert punkt_model_available(language) is True, language
            assert sent_tokenize("A b. C d.", language=language), language
        assert punkt_model_available("klingon") is False
        with pytest.raises(LookupError, match=r"nltk\.download\('punkt_tab'\)"):
            sent_tokenize("A b. C d.", language="klingon")
    finally:
        _get_punkt_tokenizer.cache_clear()

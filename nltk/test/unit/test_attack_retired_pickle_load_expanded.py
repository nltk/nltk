# Natural Language Toolkit: loading a retired pickle resource, attacked
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The pickle packages retired for CVE-2024-39705 (``punkt``,
``averaged_perceptron_tagger``, ``averaged_perceptron_tagger_ru``,
``maxent_ne_chunker`` and ``maxent_treebank_pos_tagger``) are never loaded.
``nltk.data.load()`` refuses any load that reaches for one of their pickles
with a ValueError naming the tab package that replaced it and the call that
loads that package, before the cache, the format or any file is consulted.

Each retired package is installed here, extracted and zipped, with a hostile
pickle at each of its pickle-era names: unpickled by anything but a refusing
unpickler, it creates a marker file. Every spelling of every name (another
case, a fold lookalike, ``nltk:``, a doubled slash, a trailing dot or space,
a percent escape, an archive member, a ``file:`` path, a link) in every
format is judged by what happened on the way, seen through
``sys.setprofile``: no unpickler entered and no file opened. The teeth take
the check away and show the same loads reaching the unpickler, which still
refuses the hostile pickle on its own; this change makes the retirement
explicit, it closes no unpickling hole. What replaces the pickles keeps
working and never unpickles: the tokenizers, taggers and chunker on the tab
packages, real ones where they are installed.

Control, bidi and lookalike characters are built with chr().
"""

import builtins
import contextlib
import gzip
import io
import os
import pathlib
import pickle
import sys

import pytest

import nltk
import nltk.data
from nltk import downloader, picklesec
from nltk.test.unit.test_attack_downloader_zip_expanded import (  # noqa: F401  (box is a fixture)
    ESC,
    RLO,
    ZWSP,
    assert_lines_clean,
    box,
    make_zip,
    run_download,
    serve_packages,
)

KELVIN = chr(0x212A)  # casefolds to "k"
LONG_S = chr(0x17F)  # casefolds to "s"

#: retired package: (its replacement, its pickle-era names, the call loading
#: the replacement that the refusal names for each of those names)
RETIRED = {
    "tokenizers/punkt": (
        "punkt_tab",
        {
            "tokenizers/punkt/english.pickle": "nltk.tokenize.PunktTokenizer('english')",
            "tokenizers/punkt/PY3/german.pickle": "nltk.tokenize.PunktTokenizer('german')",
        },
    ),
    "taggers/averaged_perceptron_tagger": (
        "averaged_perceptron_tagger_eng",
        {
            "taggers/averaged_perceptron_tagger/averaged_perceptron_tagger.pickle": "nltk.tag.PerceptronTagger()",
        },
    ),
    "taggers/averaged_perceptron_tagger_ru": (
        "averaged_perceptron_tagger_rus",
        {
            "taggers/averaged_perceptron_tagger_ru/averaged_perceptron_tagger_ru.pickle": "nltk.tag.PerceptronTagger(lang='rus')",
        },
    ),
    "chunkers/maxent_ne_chunker": (
        "maxent_ne_chunker_tab",
        {
            "chunkers/maxent_ne_chunker/english_ace_multiclass.pickle": "nltk.chunk.ne_chunker()",
            "chunkers/maxent_ne_chunker/PY3/english_ace_binary.pickle": "nltk.chunk.ne_chunker('binary')",
        },
    ),
    "taggers/maxent_treebank_pos_tagger": (
        "maxent_treebank_pos_tagger_tab",
        {
            "taggers/maxent_treebank_pos_tagger/PY3/english.pickle": "nltk.classify.maxent.maxent_pos_tagger()",
        },
    ),
}
NAMES = {name: package for package, (_, names) in RETIRED.items() for name in names}
FORMATS = ["auto", "pickle", "raw", "text"]

ABBREV = "zzq"
SAMPLE = "I met zzq. Smith today. Then we left."
#: "zzq" is an abbreviation only in the punkt_tab written here.
SERVED_SPLIT = ["I met zzq. Smith today.", "Then we left."]
TAB_FILES = {
    "collocations.tab": b"",
    "sent_starters.txt": b"",
    "abbrev_types.txt": (ABBREV + "\n").encode(),
    "ortho_context.tab": b"",
}


def unpickling_marker(marker):
    """Protocol-0 pickle bytes that create *marker* if anything unpickles
    them (builtins.open(marker, "w")); inert as bytes on disk."""
    return b"cbuiltins\nopen\n(V" + marker.as_posix().encode() + b"\nVw\ntR."


# ===========================================================================
# What a call does on the way
# ===========================================================================
_OPENERS = (builtins.open, os.open, io.open_code)
_PICKLESEC = os.path.normcase(os.path.abspath(picklesec.__file__))


class Watch:
    """Every unpickler a block enters and every file it opens, seen through
    ``sys.setprofile``: a C call to an unpickler's ``load`` or to
    ``pickle.load(s)``, a Python call into ``nltk.picklesec`` or into
    ``nltk.data.restricted_pickle_load``, and a C call to ``open``,
    ``os.open`` or ``io.open_code`` (importlib's own excepted). Nothing is
    replaced; every call still runs as it would."""

    def __init__(self):
        self.unpicklers = []
        self.opened = []
        self._previous = None

    def _profile(self, frame, event, arg):
        if event == "c_call":
            if any(arg is opener for opener in _OPENERS):
                code = frame.f_code
                if "importlib" not in code.co_filename:
                    self.opened.append(f"{code.co_filename}:{code.co_name}")
            elif isinstance(getattr(arg, "__self__", None), pickle.Unpickler):
                self.unpicklers.append(type(arg.__self__).__name__)
            elif arg is pickle.load or arg is pickle.loads:
                self.unpicklers.append("pickle." + arg.__name__)
        elif event == "call":
            code = frame.f_code
            if os.path.normcase(code.co_filename) == _PICKLESEC:
                self.unpicklers.append("picklesec." + code.co_name)
            elif code is nltk.data.restricted_pickle_load.__code__:
                self.unpicklers.append("restricted_pickle_load")

    def __enter__(self):
        self._previous = sys.getprofile()
        sys.setprofile(self._profile)
        return self

    def __exit__(self, *exc):
        sys.setprofile(self._previous)
        return False

    @property
    def clean(self):
        return self.unpicklers == [] and self.opened == []


@pytest.fixture
def unpickler_spy(monkeypatch):
    """The unpicklers entered while a test runs, recorded where each is
    constructed (nothing replaced): cheaper than :class:`Watch` for loading
    real models, which make millions of calls."""
    entered = []
    for cls in (
        picklesec.RestrictedUnpickler,
        picklesec.WarningUnpickler,
        picklesec.AllowlistUnpickler,
    ):

        def init(self, *args, _real=cls.__init__, _name=cls.__name__, **kwargs):
            entered.append(_name)
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(cls, "__init__", init)
    for name in ("load", "loads"):

        def entry(*args, _real=getattr(pickle, name), _name=name, **kwargs):
            entered.append("pickle." + _name)
            return _real(*args, **kwargs)

        monkeypatch.setattr(pickle, name, entry)
    return entered


def attempt(name, fmt="auto", cache=False):
    """Load *name*; return (the Watch, the exception or the value)."""
    with Watch() as watch:
        try:
            outcome = nltk.data.load(name, format=fmt, cache=cache)
        except Exception as exc:  # the outcome IS the refusal
            outcome = exc
    return watch, outcome


# ===========================================================================
# A data root holding every retired package, hostile
# ===========================================================================
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


@pytest.fixture
def retired_root(pathsec_sandbox):
    """An enforced data root with every retired package installed extracted
    and zipped, a hostile pickle at each pickle-era name (and a gzipped one
    for punkt), a README in each, and a working punkt_tab beside them."""
    from nltk.tokenize import _get_punkt_tokenizer

    root, outside = pathsec_sandbox
    marker = outside / "UNPICKLED"
    payload = unpickling_marker(marker)
    for package, (_, names) in RETIRED.items():
        subdir, pid = package.split("/")
        members = [(f"{pid}/README", b"retired pickles\n")]
        for name in names:
            members.append((name.split("/", 1)[1], payload))
        for member, data in members:
            write(root / subdir / member, data)
        write(root / subdir / f"{pid}.zip", make_zip(members))
    write(root / "tokenizers/punkt/english.pickle.gz", gzip.compress(payload))
    for name, data in TAB_FILES.items():
        write(root / "tokenizers/punkt_tab/english" / name, data)
    _get_punkt_tokenizer.cache_clear()
    yield root, marker
    _get_punkt_tokenizer.cache_clear()
    assert not marker.exists()


def fold_lookalike(word):
    """*word* with a letter swapped for one that casefolds to it."""
    if "k" in word:
        return word.replace("k", KELVIN, 1)
    return word.replace("s", LONG_S, 1)


def spellings(name, root):
    """Every way of naming one pickle-era file to nltk.data.load, by label."""
    subdir, pid, tail = name.split("/", 2)
    stem, ext = tail.rsplit(".", 1)
    absolute = (root / name).as_posix()
    return {
        "canonical": name,
        "nltk-protocol": "nltk:" + name,
        "doubled-slash": f"{subdir}//{pid}//{tail}",
        "package-upper": f"{subdir}/{pid.upper()}/{tail}",
        "subdir-upper": f"{subdir.upper()}/{pid}/{tail}",
        "title-and-ext-upper": f"{subdir.title()}/{pid.title()}/{stem}.{ext.upper()}",
        "fold-lookalike": f"{fold_lookalike(subdir)}/{pid}/{tail}",
        "trailing-dot": f"{subdir}/{pid}./{tail}",
        "trailing-space": f"{subdir}/{pid} /{tail}",
        "percent-letter": f"{subdir}/{pid[0]}%{ord(pid[1]):02X}{pid[2:]}/{tail}",
        "percent-slash": f"{subdir}%2F{pid}/{tail}",
        "percent-dot": f"{subdir}/{pid}/{stem}%2E{ext}",
        "zip-member": f"{subdir}/{pid}.zip/{pid}/{tail}",
        "outer-zip": f"{subdir}.zip/{subdir}/{pid}/{tail}",
        "file": "file:" + absolute,
        "file-triple-slash": "file://"
        + ("" if absolute.startswith("/") else "/")
        + absolute,
        "file-zip-member": "file:"
        + (root / subdir / f"{pid}.zip").as_posix()
        + f"/{pid}/{tail}",
        "file-upper": "file:" + (root / subdir / pid.upper() / tail).as_posix(),
    }


LABELS = sorted(spellings("tokenizers/punkt/english.pickle", pathlib.Path("/r")))


def assert_refused_naming_the_replacement(outcome, name, root):
    """A single clean line naming the package, the CVE, the replacement, the
    call that loads it and the installed copies that can go."""
    package = NAMES[name]
    tab, calls = RETIRED[package]
    assert isinstance(outcome, ValueError), repr(outcome)
    message = str(outcome)
    assert message.startswith("Refusing to load '"), message
    assert f"{package!r} is a retired pickle package" in message, message
    assert "CVE-2024-39705" in message, message
    assert f"Use its replacement: nltk.download({tab!r}), then {calls[name]}." in (
        message
    ), message
    for where in (
        os.path.join(str(root), *package.split("/")),
        os.path.join(str(root), *package.split("/")) + ".zip",
    ):
        assert repr(where) in message, (where, message)
    assert_lines_clean(message, expected_lines=1)


# ===========================================================================
# 1. Every spelling, every format: refused, nothing opened, nothing unpickled
# ===========================================================================
@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("label", LABELS)
def test_every_spelling_of_a_retired_pickle_is_refused_before_anything_is_read(
    retired_root, label, fmt
):
    root, marker = retired_root
    for name in NAMES:
        spelling = spellings(name, root)[label]
        watch, outcome = attempt(spelling, fmt)
        assert_refused_naming_the_replacement(outcome, name, root)
        assert watch.clean, (spelling, fmt, watch.unpicklers, watch.opened)
        assert not marker.exists(), spelling


@pytest.mark.parametrize("fmt", FORMATS)
def test_the_gzipped_pickle_is_refused_before_anything_is_read(retired_root, fmt):
    root, marker = retired_root
    for spelling in (
        "tokenizers/punkt/english.pickle.gz",
        "nltk:Tokenizers/Punkt/English.Pickle.GZ",
        "file:" + (root / "tokenizers/punkt/english.pickle.gz").as_posix(),
    ):
        watch, outcome = attempt(spelling, fmt)
        assert isinstance(outcome, ValueError), (spelling, outcome)
        assert "nltk.download('punkt_tab'), then " in str(outcome)
        assert "PunktTokenizer('english')" in str(outcome)
        assert watch.clean, (spelling, watch.unpicklers, watch.opened)


@pytest.mark.parametrize("package", sorted(RETIRED))
def test_format_pickle_on_any_file_of_a_retired_package_is_refused(
    retired_root, package
):
    root, marker = retired_root
    watch, outcome = attempt(f"{package}/README", "pickle")
    assert isinstance(outcome, ValueError), outcome
    tab = RETIRED[package][0]
    assert f"nltk.download({tab!r})" in str(outcome)
    assert watch.clean
    # a file in a retired package that is not a pickle still loads as text
    watch, outcome = attempt(f"{package}/README", "text")
    assert outcome == "retired pickles\n"
    assert watch.unpicklers == [] and watch.opened


def test_a_cached_value_under_a_retired_name_is_not_served(retired_root):
    root, marker = retired_root
    planted = type("Planted", (), {})()
    key = ("nltk:tokenizers/punkt/english.pickle", "pickle")
    nltk.data._resource_cache[key] = planted
    try:
        watch, outcome = attempt("tokenizers/punkt/english.pickle", cache=True)
    finally:
        nltk.data._resource_cache.pop(key, None)
    assert isinstance(outcome, ValueError) and outcome is not planted
    assert watch.clean


@pytest.mark.parametrize(
    "decoy",
    [
        "tokenizers/punkt/eng" + RLO + "hsil.pickle",
        "tokenizers/punkt/eng" + ZWSP + "lish.pickle",
        "file:/x/tokenizers/punkt/" + ESC + "[2J.pickle",
    ],
    ids=["bidi", "zero-width", "escape-in-file-path"],
)
def test_a_hostile_name_never_reaches_the_terminal_through_the_refusal(
    retired_root, decoy
):
    watch, outcome = attempt(decoy)
    assert isinstance(outcome, ValueError), outcome
    assert_lines_clean(str(outcome), expected_lines=1)
    assert watch.clean


# ===========================================================================
# 2. Links and short names are judged by the file they resolve to
# ===========================================================================
@pytest.mark.skipif(not hasattr(os, "symlink"), reason="needs symlinks")
@pytest.mark.parametrize("fmt", ["auto", "pickle"])
def test_a_link_to_a_retired_pickle_is_judged_by_its_target(retired_root, fmt):
    root, marker = retired_root
    alias = root / "corpora" / "alias.pickle"
    alias.parent.mkdir()
    try:
        os.symlink(root / "tokenizers/punkt/english.pickle", alias)
    except OSError:
        pytest.skip("cannot create a symlink here")
    for spelling in ("corpora/alias.pickle", "file:" + alias.as_posix()):
        watch, outcome = attempt(spelling, fmt)
        assert_refused_naming_the_replacement(
            outcome, "tokenizers/punkt/english.pickle", root
        )
        assert watch.clean, (spelling, watch.unpicklers, watch.opened)


@pytest.mark.skipif(os.name != "nt", reason="8.3 short names are a Windows alias")
def test_a_windows_short_name_is_judged_by_the_long_name_it_aliases(retired_root):
    import ctypes

    root, marker = retired_root
    buffer = ctypes.create_unicode_buffer(1024)
    if not ctypes.windll.kernel32.GetShortPathNameW(
        str(root / "tokenizers"), buffer, len(buffer)
    ):
        pytest.skip("no short name here")
    short = os.path.basename(buffer.value)
    if short.casefold() == "tokenizers":
        pytest.skip("8.3 names are not created on this volume")
    watch, outcome = attempt(f"{short}/punkt/english.pickle", "pickle")
    assert_refused_naming_the_replacement(
        outcome, "tokenizers/punkt/english.pickle", root
    )
    assert watch.clean, (watch.unpicklers, watch.opened)


def test_where_a_data_root_lives_never_refuses_its_own_pickles(
    retired_root, monkeypatch
):
    """A data root inside directories named like a retired package is judged
    by the resource names under it, not by its own location."""
    from nltk import pathsec

    root, marker = retired_root
    inner = root / "elsewhere" / "tokenizers" / "punkt_home" / "nltk_data"
    write(inner / "help" / "mine.pickle", pickle.dumps({"a": 1}, protocol=2))
    monkeypatch.setattr(nltk.data, "path", [str(inner)])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    for spelling in (
        "help/mine.pickle",
        "file:" + (inner / "help" / "mine.pickle").as_posix(),
    ):
        assert nltk.data.load(spelling, cache=False) == {"a": 1}, spelling


# ===========================================================================
# 3. Pickles beside the retired packages, and names that are not theirs
# ===========================================================================
@pytest.mark.parametrize(
    "name",
    [
        "tokenizers/punkt_tab/english/english.pickle",
        "tokenizers/punkt_tab.pickle",
        "taggers/averaged_perceptron_tagger_eng/model.pickle",
        "taggers/averaged_perceptron_tagger_rus/model.pickle",
        "chunkers/maxent_ne_chunker_tab/english_ace_multiclass/model.pickle",
        "taggers/maxent_treebank_pos_tagger_tab/english/model.pickle",
    ],
)
def test_a_pickle_in_a_tab_package_beside_them_is_refused_too(retired_root, name):
    root, marker = retired_root
    write(root / name, unpickling_marker(marker))
    watch, outcome = attempt(name)
    assert isinstance(outcome, ValueError), outcome
    message = str(outcome)
    assert "a resource tree whose pickles were retired" in message
    assert "CVE-2024-39705" in message
    assert_lines_clean(message, expected_lines=1)
    assert watch.clean


@pytest.mark.parametrize(
    "name",
    [
        "corpora/punkt/english.pickle",
        "tokenizers/other/english.pickle",
        "taggers/universal_tagset/punkt.pickle",
        "misc/tokenizers_punkt.pickle",
    ],
)
def test_other_pickles_still_reach_the_restricted_unpickler(retired_root, name):
    root, marker = retired_root
    write(root / name, unpickling_marker(marker))
    watch, outcome = attempt(name)
    assert isinstance(outcome, pickle.UnpicklingError), outcome
    assert "RestrictedUnpickler" in watch.unpicklers
    assert not marker.exists()
    benign = name.replace(".pickle", "_ok.pickle")
    write(root / benign, pickle.dumps({"a": [1, 2]}, protocol=2))
    assert nltk.data.load(benign, cache=False) == {"a": [1, 2]}


def test_the_retired_list_is_the_downloaders_successor_list():
    retired = {
        key.split("/", 1)[1]: tab for key, tab in nltk.data._RETIRED_PICKLES.items()
    }
    assert retired == downloader._SUCCESSORS
    assert retired == {p.split("/", 1)[1]: tab for p, (tab, _) in RETIRED.items()}


# ===========================================================================
# 4. What replaces the pickles works and never unpickles
# ===========================================================================
def test_the_tokenizers_read_punkt_tab_and_never_unpickle(retired_root):
    from nltk.tokenize import (
        PunktTokenizer,
        punkt_model_available,
        sent_tokenize,
        word_tokenize,
    )

    root, marker = retired_root
    with Watch() as watch:
        assert PunktTokenizer("english").tokenize(SAMPLE) == SERVED_SPLIT
        assert nltk.data.switch_punkt("english").tokenize(SAMPLE) == SERVED_SPLIT
        assert sent_tokenize(SAMPLE) == SERVED_SPLIT
        assert word_tokenize("Hello there.")[-1] == "."
        assert punkt_model_available("english") is True
    assert watch.unpicklers == []


def test_the_explicit_punkt_pickle_loader_refuses_the_hostile_pickle(retired_root):
    """``punkt_pickle_load`` reads a handle the caller opened (a model they
    trained), not a resource name, so it is kept: its allowlist refuses the
    retired file's hostile globals."""
    from nltk.tokenize.punkt import punkt_pickle_load

    root, marker = retired_root
    with open(root / "tokenizers/punkt/english.pickle", "rb") as handle:
        with Watch() as watch:
            with pytest.raises(pickle.UnpicklingError):
                punkt_pickle_load(handle)
    assert "AllowlistUnpickler" in watch.unpicklers
    assert not marker.exists()


_REAL_PACKAGES = (
    "tokenizers/punkt_tab/english/",
    "tokenizers/punkt_tab/german/",
    "taggers/averaged_perceptron_tagger_eng/",
    "taggers/averaged_perceptron_tagger_rus/",
    "chunkers/maxent_ne_chunker_tab/english_ace_multiclass/",
    "chunkers/maxent_ne_chunker_tab/english_ace_binary/",
    "taggers/maxent_treebank_pos_tagger_tab/english/",
    "corpora/words/",
)


def _missing_real_packages():
    missing = []
    for name in _REAL_PACKAGES:
        try:
            nltk.data.find(name)
        except LookupError:
            missing.append(name)
    return missing


def _run_named_call(call):
    """Run the call a refusal names, through a table of the real callables."""
    from nltk.chunk import ne_chunker
    from nltk.classify.maxent import maxent_pos_tagger
    from nltk.tag import PerceptronTagger
    from nltk.tokenize import PunktTokenizer

    table = {
        "nltk.tokenize.PunktTokenizer('english')": lambda: PunktTokenizer("english"),
        "nltk.tokenize.PunktTokenizer('german')": lambda: PunktTokenizer("german"),
        "nltk.tag.PerceptronTagger()": PerceptronTagger,
        "nltk.tag.PerceptronTagger(lang='rus')": lambda: PerceptronTagger(lang="rus"),
        "nltk.chunk.ne_chunker()": ne_chunker,
        "nltk.chunk.ne_chunker('binary')": lambda: ne_chunker("binary"),
        "nltk.classify.maxent.maxent_pos_tagger()": maxent_pos_tagger,
    }
    return table[call]()


def _works(model, words):
    """*model* (a tokenizer, a tagger or a chunker) does its job on *words*."""
    if hasattr(model, "tokenize"):
        return model.tokenize("Hello there. General Kenobi.") == [
            "Hello there.",
            "General Kenobi.",
        ]
    tagged = model.tag(words)
    return [w for w, _ in tagged] == words and all(tag for _, tag in tagged)


def test_the_real_tab_packages_work_and_never_unpickle(unpickler_spy):
    """With the real data installed: each retired name is refused, the call
    its refusal names loads a working model, and the public tokenizers,
    taggers and chunker run, all without entering an unpickler."""
    missing = _missing_real_packages()
    if missing:
        pytest.skip(f"the real tab packages are not installed here: {missing}")
    from nltk import ne_chunk, pos_tag
    from nltk.classify.maxent import maxent_pos_tagger
    from nltk.tag import PerceptronTagger, _get_tagger
    from nltk.tokenize import (
        PunktTokenizer,
        _get_punkt_tokenizer,
        sent_tokenize,
        word_tokenize,
    )

    _get_punkt_tokenizer.cache_clear()
    _get_tagger.cache_clear()
    words = word_tokenize("Mark Pedersen works at Google in London.")
    unpickler_spy.clear()
    for name, package in NAMES.items():
        call = RETIRED[package][1][name]
        with pytest.raises(ValueError) as refused:
            nltk.data.load(name, cache=False)
        assert f", then {call}." in str(refused.value), str(refused.value)
        model = _run_named_call(call)
        if hasattr(model, "parse"):
            assert model.parse(pos_tag(words)).label() == "S", call
        else:
            assert _works(model, words), call
    assert sent_tokenize("Hello there. General Kenobi.") == [
        "Hello there.",
        "General Kenobi.",
    ]
    assert word_tokenize("Hello there.") == ["Hello", "there", "."]
    assert PunktTokenizer("german").tokenize("Er kam um 5 Uhr. Dann ging er.") == [
        "Er kam um 5 Uhr.",
        "Dann ging er.",
    ]
    tagged = pos_tag(words)
    assert tagged[0] == ("Mark", "NNP") and len(tagged) == len(words)
    assert PerceptronTagger().tag(words) == tagged
    russian = ["".join(map(chr, (0x41C, 0x430, 0x43C, 0x430)))]
    assert pos_tag(russian, lang="rus")[0][0] == russian[0]
    chunked = str(ne_chunk(tagged))
    assert "(PERSON Mark/NNP)" in chunked, chunked
    assert "(GPE London/NNP)" in chunked, chunked
    assert maxent_pos_tagger().tag(["Hello", "."])[1] == (".", ".")
    assert nltk.data.switch_t_tagger().tag(["Hello", "."])[1] == (".", ".")
    assert nltk.data.switch_p_tagger("eng").tag(words) == tagged
    assert nltk.data.switch_chunker("multiclass").parse(tagged)
    assert unpickler_spy == []


# ===========================================================================
# 5. Installing them unpickles nothing
# ===========================================================================
def test_downloading_every_retired_package_unpickles_nothing(box):
    root, outside, dl, server = box
    marker = outside / "UNPICKLED"
    payload = unpickling_marker(marker)
    packages = []
    for package, (tab, names) in RETIRED.items():
        subdir, pid = package.split("/")
        members = [(f"{pid}/", b"")] + [(n.split("/", 1)[1], payload) for n in names]
        packages.append((pid, make_zip(members), {"subdir": subdir}))
        if tab == "punkt_tab":
            tab_members = [(f"{tab}/english/{f}", d) for f, d in TAB_FILES.items()]
        else:
            tab_members = [(f"{tab}/README", b"stand-in\n")]
        tab_zip = make_zip([(f"{tab}/", b"")] + tab_members)
        packages.append((tab, tab_zip, {"subdir": subdir}))
    retired = [package.split("/")[1] for package in RETIRED]
    index_url = serve_packages(server, packages, [("retiredish", retired)])
    with Watch() as watch:
        result, output = run_download(index_url, dl, "retiredish")
    assert result is True, output
    assert watch.unpicklers == []
    d = downloader.Downloader(server_index_url=index_url, download_dir=str(dl))
    for package, (tab, names) in RETIRED.items():
        subdir, pid = package.split("/")
        assert d.status(pid) == d.INSTALLED and d.status(tab) == d.INSTALLED
        for name in names:
            assert (dl / name).is_file(), name
    assert not marker.exists()


# ===========================================================================
# 6. Teeth: without the check the same loads reach the unpickler
# ===========================================================================

#: Spellings any filesystem opens as the retired file once the check is gone;
#: the others (another case, a fold lookalike, a trailing dot or space) only
#: where the filesystem folds them, which is read here rather than assumed.
ALWAYS_REACHES = {
    "canonical",
    "nltk-protocol",
    "doubled-slash",
    "percent-letter",
    "percent-slash",
    "percent-dot",
    "zip-member",
    "file",
    "file-triple-slash",
}


@pytest.mark.parametrize("label", LABELS)
def test_teeth_without_the_check_the_hostile_pickle_reaches_the_unpickler(
    retired_root, monkeypatch, label
):
    root, marker = retired_root
    payload = unpickling_marker(marker)
    monkeypatch.setattr(nltk.data, "_refuse_retired_pickle", lambda *args: None)
    for name in NAMES:
        spelling = spellings(name, root)[label]
        readable = attempt(spelling, "raw")[1] == payload
        assert readable or label not in ALWAYS_REACHES, spelling
        watch, outcome = attempt(spelling, "pickle")
        if readable:
            # the restricted unpickler is ENTERED and refuses on its own
            assert isinstance(outcome, pickle.UnpicklingError), (spelling, outcome)
            assert "RestrictedUnpickler" in watch.unpicklers, (spelling, watch)
            assert watch.opened, spelling
        else:
            assert "RestrictedUnpickler" not in watch.unpicklers, spelling
        assert not marker.exists(), spelling


@pytest.mark.parametrize("fmt", ["raw", "text"])
def test_teeth_without_the_check_raw_and_text_read_the_pickle(
    retired_root, monkeypatch, fmt
):
    root, marker = retired_root
    monkeypatch.setattr(nltk.data, "_refuse_retired_pickle", lambda *args: None)
    for name in NAMES:
        watch, outcome = attempt(name, fmt)
        assert not isinstance(outcome, Exception), (name, outcome)
        assert watch.opened and watch.unpicklers == [], name
    assert not marker.exists()


def test_teeth_the_watch_sees_an_unpickler_and_an_open():
    """The observer itself: a real unpickle and a real open are seen."""
    with Watch() as watch:
        nltk.data.restricted_pickle_load(pickle.dumps([1], protocol=2))
        with open(__file__, "rb"):
            pass
    assert "RestrictedUnpickler" in watch.unpicklers
    here = ":test_teeth_the_watch_sees_an_unpickler_and_an_open"
    assert any(where.endswith(here) for where in watch.opened), watch.opened

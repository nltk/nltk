# Natural Language Toolkit: known answers on every package of the data index
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Known answers for every package of the NLTK data index, on all of its data.

The full-data CI job (the ``full-data`` label on a pull request) downloads
every package of the index with ``nltk.downloader`` and runs this module with
``NLTK_FULL_DATA=1``; anywhere else it is skipped, since it reads all of the
data, 3.47 GiB unzipped. Each package has checks here that run the NLTK
modules that use it on the whole of it, never a sample, and compare their
output with answers that come from outside NLTK's code:

* answers shipped in the data: the Snowball and Porter test vocabularies, the
  parse count of every test sentence of the large grammars, mteval-13a's
  scores of the WMT15 sample, Moses' best translation of its sample model;
* answers published with the data or about it: the sizes in the corpora's
  READMEs, WordNet's statistics, the outputs printed in the NLTK book and in
  the README of VADER;
* for each model, inputs whose outputs NLTK documents;
* invariants every corpus reader must keep on every one of its files: the
  words of its tagged, parsed and chunked views are its words, a file is in
  each of its categories, the words of a plaintext reader are the tokens of
  its raw text.

Where NLTK departs from a shipped answer today, ``full_data_departures.json``
beside this module lists each departure, and the departures must be exactly
those: a new one fails, and so does a fixed one, until it is struck off the
list. The retired pickle packages are not read: NLTK no longer loads them, and
each has a pickle-free replacement in the index, which is checked instead.
"""

import json
import math
import os
from collections import defaultdict

import pytest

import nltk

FULL = os.environ.get("NLTK_FULL_DATA") == "1"
pytestmark = pytest.mark.skipif(
    not FULL, reason="reads all of the data: the full-data job runs it"
)

#: The pickle packages NLTK no longer loads, each with the package that replaced it.
RETIRED = {path.split("/")[1]: tab for path, tab in nltk.data._RETIRED_PICKLES.items()}
# nltk.help reads tagsets_json; the pickled tagsets are the same tables
RETIRED["tagsets"] = "tagsets_json"

#: Seconds one sentence of a shipped grammar may take to parse: the default bound
#: is for untrusted grammars, and these are NLTK's own, large and ambiguous.
TRUSTED_GRAMMAR_SECONDS = 600


def _packages(variable):
    path = os.environ.get(variable)
    if not FULL or not path:
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


#: Every package of the index, and the ones this shard checks (all of them by default).
INDEX = _packages("NLTK_FULL_DATA_INDEX")
SHARD = _packages("NLTK_FULL_DATA_PACKAGES") or INDEX

ANSWERS = defaultdict(list)


def answers(*pids):
    """Register a check of the packages ``pids``."""

    def register(check):
        for pid in pids:
            ANSWERS[pid].append(check)
        return check

    return register


def _departures():
    path = os.path.join(os.path.dirname(__file__), "full_data_departures.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


DEPARTURES = _departures()


def same_departures(kind, key, found, answer=None):
    """``found`` must be exactly the pinned departures of ``key``, or ``answer``
    (no departure at all) when none are pinned. When it is not, it is also written
    under NLTK_FULL_DATA_FOUND, one file per process, so that the CI job prints
    what each package departs in and the list can be updated."""
    default = type(found)() if answer is None else answer
    expected = DEPARTURES.get(kind, {}).get(key, default)
    folder = os.environ.get("NLTK_FULL_DATA_FOUND")
    if found != expected and folder:
        os.makedirs(folder, exist_ok=True)
        with open(
            os.path.join(folder, f"{os.getpid()}.jsonl"), "a", encoding="utf-8"
        ) as f:
            f.write(
                json.dumps(
                    {"kind": kind, "key": key, "found": found}, ensure_ascii=False
                )
                + "\n"
            )
    assert found == expected, (kind, key, len(found))


def _lines(resource):
    """The lines of a data file, its empty ones kept, without a final empty one."""
    rows = nltk.data.load(resource, format="text", cache=False).split("\n")
    return rows[:-1] if rows and rows[-1] == "" else rows


def test_every_package_has_known_answers():
    """Every package of the index is checked here, or is a retired pickle package
    whose replacement is; a package added to the index fails until it has checks."""
    ids = {p["id"] for p in INDEX}
    assert ids, "NLTK_FULL_DATA_INDEX names no packages"
    assert ids - set(ANSWERS) - set(RETIRED) == set()
    assert set(ANSWERS) - ids == set()
    assert {tab for pid, tab in RETIRED.items() if pid in ids} <= set(ANSWERS)


#: The packages this shard checks, the retired pickle packages left out.
CHECKED = sorted(p["id"] for p in SHARD if p["id"] not in RETIRED)


def _format_args():
    from nltk.sem.drt import DrtParser

    # its semantics are DRT, which nltk/test/drt.doctest reads with this parser
    return {"grammars/book_grammars/drt.fcfg": {"logic_parser": DrtParser()}}


_FORMAT_ARGS = _format_args()


def _package_files(pkg):
    """(path, form) of every file of a package NLTK can serve: as it finds it,
    and from the zip archive too where the package is also unzipped."""
    import zipfile

    pid, subdir = pkg["id"], pkg["subdir"]
    for root in nltk.data.path:
        archive = os.path.join(root, subdir, pid + ".zip")
        if os.path.isfile(archive):
            with zipfile.ZipFile(archive) as z:
                names = sorted(n for n in z.namelist() if not n.endswith("/"))
            files = [(f"{subdir}/{n}", "served") for n in names]
            if os.path.isdir(os.path.join(root, subdir, pid)):
                files += [(f"{subdir}/{pid}.zip/{n}", "zip") for n in names]
            return names, files
    return [], []


@pytest.mark.parametrize("pid", CHECKED)
def test_every_file_loads(pid):
    """Every file of the package loads in full with nltk.data.load, raw, as NLTK
    serves it and from its zip archive, and in its own format where it has one.
    Pickles are not read: NLTK no longer loads them."""
    (pkg,) = (p for p in SHARD if p["id"] == pid)
    names, files = _package_files(pkg)
    assert names, f"{pid} is not installed"
    refused = {}
    for path, form in files:
        if path.endswith(".pickle"):
            continue
        try:
            assert isinstance(nltk.data.load(path, format="raw", cache=False), bytes)
            name = path.rsplit("/", 1)[-1]
            extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if form == "served" and extension in nltk.data.AUTO_FORMATS:
                if extension not in ("txt", "text", "pickle"):
                    nltk.data.load(path, cache=False, **_FORMAT_ARGS.get(path, {}))
        except Exception as e:
            refused[path] = f"{type(e).__name__}: {e}"[:160]
    same_departures("files", pid, refused)


@pytest.mark.parametrize("pid", CHECKED)
def test_known_answers(pid):
    checks = ANSWERS.get(pid)
    assert checks, f"no known answers for {pid}"
    for check in checks:
        check()


# Stemmers: the test vocabularies shipped with them, every word.


@answers("porter_test")
def _porter_vocabulary():
    from nltk.stem import PorterStemmer

    vocabulary = _lines("stemmers/porter_test/porter_vocabulary.txt")
    for mode, name in (
        (PorterStemmer.ORIGINAL_ALGORITHM, "original"),
        (PorterStemmer.MARTIN_EXTENSIONS, "martin"),
        (PorterStemmer.NLTK_EXTENSIONS, "nltk"),
    ):
        expected = _lines(f"stemmers/porter_test/porter_{name}_output.txt")
        assert len(expected) == len(vocabulary)
        stemmer = PorterStemmer(mode)
        wrong = [
            (w, stemmer.stem(w), e)
            for w, e in zip(vocabulary, expected)
            if stemmer.stem(w) != e
        ]
        assert wrong == [], (name, wrong[:20])


#: Languages of the Snowball test data that nltk.stem.snowball has no stemmer for.
SNOWBALL_DATA_ONLY = {"german2", "kraaij_pohlmann", "lovins", "turkish"}


@answers("snowball_data")
def _snowball_vocabularies():
    from nltk.stem import SnowballStemmer

    root = nltk.data.find("stemmers/snowball_data/")
    languages = sorted(
        f.split("/")[0]
        for f in (str(p) for p in _listing(root))
        if f.endswith("/voc.txt")
    )
    assert set(languages) - set(SnowballStemmer.languages) == SNOWBALL_DATA_ONLY
    for lang in sorted(set(languages) - SNOWBALL_DATA_ONLY):
        words = _lines(f"stemmers/snowball_data/{lang}/voc.txt")
        expected = _lines(f"stemmers/snowball_data/{lang}/output.txt")
        assert len(expected) == len(words), lang
        stemmer = SnowballStemmer(lang)
        found = [
            [w, stemmer.stem(w), e]
            for w, e in zip(words, expected)
            if stemmer.stem(w) != e
        ]
        same_departures("snowball_data", lang, found)


def _listing(root):
    """The files under a data directory or zip pointer, relative to it."""
    if isinstance(root, nltk.data.ZipFilePathPointer):
        prefix = root.entry
        return [
            n[len(prefix) :]
            for n in root.zipfile.namelist()
            if n.startswith(prefix) and not n.endswith("/")
        ]
    base = root.path
    return [
        os.path.relpath(os.path.join(d, f), base).replace(os.sep, "/")
        for d, _, names in os.walk(base)
        for f in names
    ]


# Grammars: the parse count of every test sentence shipped with them.


#: The large grammars, when this shard checks their package.
LARGE_GRAMMARS = (
    ["atis", "commandtalk", "alvey"]
    if "large_grammars" in {p["id"] for p in SHARD}
    else []
)


@pytest.mark.parametrize("name", LARGE_GRAMMARS)
def test_large_grammar_parse_counts(name):
    """Each test sentence of the large grammars has the number of parses its
    file gives; a sentence given none and using a word the grammar lacks is
    refused with NLTK's coverage error, which is also no parse."""
    from nltk.parse import BottomUpLeftCornerChartParser, FeatureChartParser
    from nltk.parse.util import extract_test_sentences

    feature = name == "alvey"
    grammar = nltk.data.load(
        f"grammars/large_grammars/{name}.{'fcfg' if feature else 'cfg'}"
    )
    parser_class = FeatureChartParser if feature else BottomUpLeftCornerChartParser
    parser = parser_class(grammar, max_time=TRUSTED_GRAMMAR_SECONDS)
    sentences = extract_test_sentences(
        nltk.data.load(f"grammars/large_grammars/{name}_sentences.txt")
    )
    assert sentences
    wrong = []
    for words, expected in sentences:
        try:
            found = len(list(parser.parse(words)))
        except ValueError as e:
            if "does not cover" not in str(e):
                raise
            found = 0
        if found != expected:
            wrong.append([" ".join(words), expected, found])
    same_departures("parse counts", name, wrong)


@answers("large_grammars")
def _large_grammars_load():
    # the parse counts are test_large_grammar_parse_counts, one test per grammar
    for name, ext in (("atis", "cfg"), ("commandtalk", "cfg"), ("alvey", "fcfg")):
        assert nltk.data.load(f"grammars/large_grammars/{name}.{ext}").productions()


# Translation: mteval-13a's scores of the WMT15 sample, Moses' sample model.


def _wmt15():
    hypotheses = [line.split() for line in _lines("models/wmt15_eval/google.ru")]
    references = [[line.split()] for line in _lines("models/wmt15_eval/ref.ru")]
    lines = _lines("models/wmt15_eval/mteval-13a.output")
    return hypotheses, references, lines


@answers("wmt15_eval")
def _wmt15_mteval_scores():
    from nltk.translate.bleu_score import corpus_bleu
    from nltk.translate.nist_score import corpus_nist

    hypotheses, references, lines = _wmt15()
    assert len(hypotheses) == len(references) == 100  # its README: 100 sentences
    nist = [float(x) for x in lines[-4].split()[1:-1]]
    bleu = [float(x) for x in lines[-2].split()[1:-1]]
    assert len(nist) == len(bleu) == 9
    # the tolerances of test_bleu.py and test_nist.py
    for n in range(1, 10):
        found = corpus_bleu(references, hypotheses, weights=(1.0 / n,) * n)
        assert abs(found - bleu[n - 1]) < 0.005, (n, found, bleu[n - 1])
        found = corpus_nist(references, hypotheses, n)
        assert abs(found - nist[n - 1]) < 0.05, (n, found, nist[n - 1])


class _ArpaModel:
    """A backoff n-gram model read from an ARPA file, log probabilities in base e,
    with the interface ``StackDecoder`` asks of a language model."""

    def __init__(self, text):
        self.prob, self.backoff, self.order = {}, {}, 0
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("\\") and line.endswith("-grams:"):
                self.order = int(line[1:].split("-")[0])
            elif "\t" in line:
                fields = line.split("\t")
                words = tuple(fields[1].split(" "))
                self.prob[words] = float(fields[0]) * math.log(10)
                if len(fields) > 2:
                    self.backoff[words] = float(fields[2]) * math.log(10)

    def log_prob(self, ngram):
        if ngram in self.prob:
            return self.prob[ngram]
        if len(ngram) == 1:
            return -100.0 * math.log(10)  # KenLM's score of an unknown word
        return self.backoff.get(ngram[:-1], 0.0) + self.log_prob(ngram[1:])

    def probability_change(self, context, phrase):
        # the decoder hands over the hypothesis whose translation is the context
        words = getattr(context, "translation_so_far", lambda: context)()
        history = ["<s>"] + list(words)
        total = 0.0
        for word in phrase:
            total += self.log_prob(tuple(history[1 - self.order :]) + (word,))
            history.append(word)
        return total

    def probability(self, phrase):
        return self.probability_change((), phrase)


@answers("moses_sample")
def _moses_sample_translation():
    from nltk.translate import PhraseTable, StackDecoder

    raw = nltk.data.load("models/moses_sample/lm/europarl.srilm.gz", format="raw")
    model = _ArpaModel(raw.decode("latin-1"))
    best = _lines("models/moses_sample/phrase-model/nbest.txt")[0].split("|||")
    assert best[0].strip() == "0" and "lm: -27.0908" in best[2]
    # the model is read right: it scores Moses' 1-best as Moses' lm feature does
    words = best[1].split()
    assert round(model.probability_change((), words + ["</s>"]), 4) == -27.0908
    table = PhraseTable()
    for line in _lines("models/moses_sample/phrase-model/phrase-table"):
        source, target, score = (f.strip() for f in line.split("|||")[:3])
        table.add(tuple(source.split()), tuple(target.split()), math.log(float(score)))
    decoder = StackDecoder(table, model)
    found = [
        " ".join(decoder.translate(line.split()))
        for line in _lines("models/moses_sample/phrase-model/in")
    ]
    best = " ".join(words)
    assert len(set(found)) == 1, found
    # NLTK's translation, until StackDecoder's future cost reads the target phrase
    same_departures("moses_sample", best, found[0], answer=best)


# Models: the examples NLTK documents for the modules that load them, run on
# the downloaded model, and each model's own answers.


def _documented_examples(*modules):
    """Run the docstring examples of ``modules``; every one must pass."""
    import doctest
    import importlib

    flags = doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE
    for name in modules:
        result = doctest.testmod(
            importlib.import_module(name), optionflags=flags, report=False
        )
        assert result.attempted > 0, f"{name} documents no examples"
        assert result.failed == 0, (name, result)


@answers("averaged_perceptron_tagger_eng")
def _english_tagger():
    from nltk.tokenize import word_tokenize

    _documented_examples("nltk.tag", "nltk.tag.perceptron")
    words = word_tokenize("John's big idea isn't all that bad.")
    # nltk.pos_tag's documented outputs, in the Penn and universal tagsets
    assert nltk.pos_tag(words) == [
        ("John", "NNP"),
        ("'s", "POS"),
        ("big", "JJ"),
        ("idea", "NN"),
        ("is", "VBZ"),
        ("n't", "RB"),
        ("all", "PDT"),
        ("that", "DT"),
        ("bad", "JJ"),
        (".", "."),
    ]
    assert [t for _, t in nltk.pos_tag(words, tagset="universal")] == [
        "NOUN",
        "PRT",
        "ADJ",
        "NOUN",
        "VERB",
        "ADV",
        "DET",
        "DET",
        "ADJ",
        ".",
    ]


@answers("averaged_perceptron_tagger_rus")
def _russian_tagger():
    from nltk.tokenize import word_tokenize

    words = word_tokenize("Илья оторопел и дважды перечитал бумажку.")
    assert nltk.pos_tag(words, lang="rus") == [
        ("Илья", "S"),
        ("оторопел", "V"),
        ("и", "CONJ"),
        ("дважды", "ADV"),
        ("перечитал", "V"),
        ("бумажку", "S"),
        (".", "NONLEX"),
    ]


@answers("maxent_treebank_pos_tagger_tab", "maxent_ne_chunker_tab")
def _maxent_models():
    from nltk.corpus import treebank
    from nltk.tokenize import word_tokenize

    # nltk.data documents switch_t_tagger and switch_chunker
    _documented_examples("nltk.data", "nltk.chunk")
    assert nltk.data.switch_t_tagger().tag(word_tokenize("Hello, how are you?")) == [
        ("Hello", "NNP"),
        (",", ","),
        ("how", "WRB"),
        ("are", "VBP"),
        ("you", "PRP"),
        ("?", "."),
    ]
    tree = nltk.data.switch_chunker("multiclass").parse(
        treebank.tagged_sents()[2][8:14]
    )
    assert (
        str(tree).split()
        == (
            "(S chairman/NN of/IN (ORGANIZATION Consolidated/NNP Gold/NNP Fields/NNP) PLC/NNP)"
        ).split()
    )


@answers("punkt_tab")
def _punkt_models():
    from nltk.tokenize import PunktTokenizer

    _documented_examples("nltk.tokenize.punkt", "nltk.tokenize")
    root = nltk.data.find("tokenizers/punkt_tab/")
    languages = sorted({f.split("/")[0] for f in _listing(root) if "/" in f})
    # the languages of the README's table, each read into a working tokenizer
    assert languages == [
        "czech",
        "danish",
        "dutch",
        "english",
        "estonian",
        "finnish",
        "french",
        "german",
        "greek",
        "italian",
        "malayalam",
        "norwegian",
        "polish",
        "portuguese",
        "russian",
        "slovene",
        "spanish",
        "swedish",
        "turkish",
    ]
    text = "Dr. Smith went to Washington. He arrived on Jan. 5th."
    for lang in languages:
        assert PunktTokenizer(lang).tokenize(text), lang


@answers("perluniprops", "nonbreaking_prefixes")
def _moses_tokenizer_data():
    import unicodedata

    from nltk.corpus import nonbreaking_prefixes, perluniprops

    # the tokenizers that read them document their outputs
    _documented_examples("nltk.tokenize.nist", "nltk.tokenize.toktok")
    classes = {
        "Close_Punctuation": ("Pe",),
        "Currency_Symbol": ("Sc",),
        "IsAlnum": ("L", "N", "M"),
        "IsAlpha": ("L", "M", "Nl"),
        "IsLower": ("Ll",),
        "IsN": ("N",),
        "IsSc": ("Sc",),
        "IsSo": ("So",),
        "IsUpper": ("Lu",),
        "Line_Separator": ("Zl",),
        "Number": ("N",),
        "Open_Punctuation": ("Ps",),
        "Punctuation": ("P",),
        "Separator": ("Z",),
        "Symbol": ("S",),
    }
    assert sorted(f[:-4] for f in perluniprops.fileids()) == sorted(classes)
    # every character of a property file, against Python's Unicode database
    outside = {}
    for name, prefixes in classes.items():
        counts = defaultdict(int)
        for char in perluniprops.chars(name):
            category = unicodedata.category(char)
            if not category.startswith(prefixes):
                counts[category] += 1
        if counts:
            outside[name] = dict(sorted(counts.items()))
    same_departures("perluniprops", "outside their class", outside)
    assert len(nonbreaking_prefixes.fileids()) == 22
    assert {"Mr", "Dr", "St", "Jan"} <= set(nonbreaking_prefixes.words("en"))


@answers("rslp")
def _rslp():
    _documented_examples("nltk.stem.rslp")


@answers("universal_tagset")
def _universal_tagset():
    from nltk.corpus import brown, treebank
    from nltk.tag.mapping import _UNIVERSAL_TAGS

    _documented_examples("nltk.tag.mapping")
    # every tag of the Brown corpus and the treebank sample maps to a universal one
    for reader in (brown, treebank):
        tags = {t for _, t in reader.tagged_words(tagset="universal")}
        assert tags <= set(_UNIVERSAL_TAGS), (reader, tags - set(_UNIVERSAL_TAGS))


@answers("tagsets_json")
def _tagsets():
    import io
    from contextlib import redirect_stdout

    from nltk.corpus import treebank
    from nltk.jsontags import safe_json_load

    def table(name):
        with nltk.data.find(f"help/tagsets_json/PY3_json/{name}.json").open() as f:
            return safe_json_load(f)

    # the Penn Treebank's 36 part-of-speech and 9 punctuation tags
    sizes = {
        name: len(table(name))
        for name in ("upenn_tagset", "brown_tagset", "claws5_tagset")
    }
    assert sizes == {"upenn_tagset": 45, "brown_tagset": 226, "claws5_tagset": 62}
    for name in sizes:
        for tag, (definition, examples) in table(name).items():
            printed = io.StringIO()
            with redirect_stdout(printed):
                getattr(nltk.help, name)("^" + _escape(tag) + "$")
            assert definition in printed.getvalue(), (name, tag)
    used = {t for _, t in treebank.tagged_words()}
    same_departures(
        "tagsets_json",
        "treebank tags not in upenn_tagset",
        sorted(used - set(table("upenn_tagset"))),
    )


def _escape(tag):
    import re

    return re.escape(tag)


@answers("vader_lexicon")
def _vader():
    from nltk.sentiment import SentimentIntensityAnalyzer

    analyzer = SentimentIntensityAnalyzer()
    # VADER's README, as nltk/test/sentiment.doctest prints it
    documented = {
        "VADER is smart, handsome, and funny.": (0.8316, 0.0, 0.254, 0.746),
        "VADER is smart, handsome, and funny!": (0.8439, 0.0, 0.248, 0.752),
        "VADER is very smart, handsome, and funny.": (0.8545, 0.0, 0.299, 0.701),
        "VADER is VERY SMART, handsome, and FUNNY.": (0.9227, 0.0, 0.246, 0.754),
        "VADER is VERY SMART, handsome, and FUNNY!!!": (0.9342, 0.0, 0.233, 0.767),
        "VADER is VERY SMART, really handsome, and INCREDIBLY FUNNY!!!": (
            0.9469,
            0.0,
            0.294,
            0.706,
        ),
        "The book was good.": (0.4404, 0.0, 0.508, 0.492),
        "The book was kind of good.": (0.3832, 0.0, 0.657, 0.343),
        "The plot was good, but the characters are uncompelling and the dialog is not great.": (
            -0.7042,
            0.327,
            0.579,
            0.094,
        ),
        "A really bad, horrible book.": (-0.8211, 0.791, 0.209, 0.0),
        "At least it isn't a horrible book.": (0.431, 0.0, 0.637, 0.363),
        ":) and :D": (0.7925, 0.0, 0.124, 0.876),
        "": (0.0, 0.0, 0.0, 0.0),
        "Today sux": (-0.3612, 0.714, 0.286, 0.0),
        "Today sux!": (-0.4199, 0.736, 0.264, 0.0),
        "Today SUX!": (-0.5461, 0.779, 0.221, 0.0),
        "Today kinda sux! But I'll get by, lol": (0.5249, 0.138, 0.517, 0.344),
    }
    for sentence, scores in documented.items():
        found = analyzer.polarity_scores(sentence)
        assert (found["compound"], found["neg"], found["neu"], found["pos"]) == scores
    # every entry of the lexicon, alone, scores with the sign of its valence
    against = [
        w
        for w, valence in analyzer.lexicon.items()
        if valence * analyzer.polarity_scores(w)["compound"] <= 0 and valence
    ]
    assert len(analyzer.lexicon) == 7502
    same_departures("vader_lexicon", "against their valence", sorted(against))


@answers("word2vec_sample")
def _word2vec():
    import numpy

    # loaded as gensim's KeyedVectors does, checked against nltk/test/gensim.doctest
    lines = nltk.data.load(
        "models/word2vec_sample/pruned.word2vec.txt", format="text", cache=False
    ).split("\n")
    count, size = map(int, lines[0].split())
    words, rows = [], []
    for line in lines[1:]:
        if line.strip():
            fields = line.rstrip().split(" ")
            words.append(fields[0])
            rows.append(numpy.asarray(fields[1:], dtype=numpy.float32))
    vectors = numpy.vstack(rows)
    assert (count, size) == (43981, 300) == vectors.shape
    unit = vectors / numpy.linalg.norm(vectors, axis=1, keepdims=True)
    index = {w: i for i, w in enumerate(words)}

    def most_similar(positive, negative=(), top=1):
        mean = sum(unit[index[w]] for w in positive) - sum(
            unit[index[w]] for w in negative
        )
        similarity = unit @ (mean / numpy.linalg.norm(mean))
        given = {index[w] for w in (*positive, *negative)}
        best = [i for i in numpy.argsort(-similarity) if i not in given][:top]
        # the doctest prints five decimals and an ellipsis
        return [(words[i], math.floor(float(similarity[i]) * 1e5) / 1e5) for i in best]

    assert most_similar(["university"], top=3) == [
        ("universities", 0.70039),
        ("faculty", 0.67809),
        ("undergraduate", 0.6587),
    ]
    assert most_similar(["woman", "king"], ["man"]) == [("queen", 0.71181)]
    assert most_similar(["Paris", "Germany"], ["Berlin"]) == [("France", 0.7884)]
    meal = "breakfast cereal dinner lunch".split()
    rows = unit[[index[w] for w in meal]]
    mean = rows.mean(axis=0)
    assert meal[int(numpy.argmin(rows @ (mean / numpy.linalg.norm(mean))))] == "cereal"


# The NLTK book's printed outputs on the corpora (chapters 2, 5 and 7), all of the data.


@answers("brown")
def _brown_book():
    from nltk.corpus import brown

    assert (len(brown.words()), len(brown.sents()), len(brown.categories())) == (
        1161192,
        57340,
        15,
    )
    news = nltk.FreqDist(w.lower() for w in brown.words(categories="news"))
    modals = ["can", "could", "may", "might", "must", "will"]
    assert [news[m] for m in modals] == [94, 87, 93, 38, 53, 389]
    by_genre = nltk.ConditionalFreqDist(
        (g, w) for g in brown.categories() for w in brown.words(categories=g)
    )
    assert {
        g: [by_genre[g][m] for m in modals]
        for g in ("news", "religion", "hobbies", "science_fiction", "romance", "humor")
    } == {
        "news": [93, 86, 66, 38, 50, 389],
        "religion": [82, 59, 78, 12, 54, 71],
        "hobbies": [268, 58, 131, 22, 83, 264],
        "science_fiction": [16, 49, 4, 12, 8, 16],
        "romance": [74, 193, 11, 51, 45, 43],
        "humor": [16, 30, 8, 8, 9, 13],
    }
    tagged = brown.tagged_sents(categories="news")
    assert nltk.DefaultTagger("NN").accuracy(tagged) == 0.13089484257215028
    assert nltk.UnigramTagger(tagged).accuracy(tagged) == 0.9349006503968017
    frequent = nltk.FreqDist(brown.words(categories="news")).most_common(100)
    likely = nltk.ConditionalFreqDist(brown.tagged_words(categories="news"))
    lookup = nltk.UnigramTagger(model={w: likely[w].max() for w, _ in frequent})
    assert lookup.accuracy(tagged) == 0.45578495136941344


@answers("gutenberg")
def _gutenberg_book():
    from nltk.corpus import gutenberg

    # chapter 2, section 1.1: word length, sentence length and lexical diversity
    table = {
        "austen-emma.txt": (5, 25, 26),
        "austen-persuasion.txt": (5, 26, 17),
        "austen-sense.txt": (5, 28, 22),
        "bible-kjv.txt": (4, 34, 79),
        "blake-poems.txt": (5, 19, 5),
        "bryant-stories.txt": (4, 19, 14),
        "burgess-busterbrown.txt": (4, 18, 12),
        "carroll-alice.txt": (4, 20, 13),
        "chesterton-ball.txt": (5, 20, 12),
        "chesterton-brown.txt": (5, 23, 11),
        "chesterton-thursday.txt": (5, 18, 11),
        "edgeworth-parents.txt": (4, 21, 25),
        "melville-moby_dick.txt": (5, 26, 15),
        "milton-paradise.txt": (5, 52, 11),
        "shakespeare-caesar.txt": (4, 12, 9),
        "shakespeare-hamlet.txt": (4, 12, 8),
        "shakespeare-macbeth.txt": (4, 12, 7),
        "whitman-leaves.txt": (5, 36, 12),
    }
    found = {}
    for fid in gutenberg.fileids():
        words = gutenberg.words(fid)
        vocabulary = {w.lower() for w in words}
        found[fid] = (
            round(len(gutenberg.raw(fid)) / len(words)),
            round(len(words) / len(gutenberg.sents(fid))),
            round(len(words) / len(vocabulary)),
        )
    assert found == table
    assert len(gutenberg.words("austen-emma.txt")) == 192427


@answers("conll2000")
def _conll2000_book():
    from nltk.corpus import conll2000

    # its README: sections 15 to 18 for training, 211727 tokens, section 20 for testing, 47377
    assert len(conll2000.words("train.txt")) == 211727
    assert len(conll2000.words("test.txt")) == 47377
    test = conll2000.chunked_sents("test.txt", chunk_types=["NP"])
    # chapter 7, section 3.2, as printed
    for grammar, scores in (
        ("", ("43.4", "0.0", "0.0", "0.0")),
        (r"NP: {<[CDJNP].*>+}", ("87.7", "70.6", "67.8", "69.2")),
    ):
        printed = str(nltk.RegexpParser(grammar).accuracy(test))
        found = tuple(line.split()[-1].rstrip("%") for line in printed.splitlines()[1:])
        assert found == scores, (grammar, printed)


# WordNet and the resources read through it.


@answers("wordnet")
def _wordnet_30():
    from nltk.corpus import wordnet as wn

    _documented_examples("nltk.corpus.reader.wordnet")
    # WordNet 3.0's statistics (wnstats(7WN)): synsets of each part of speech
    counts = {pos: sum(1 for _ in wn.all_synsets(pos)) for pos in "nvar"}
    assert counts == {"n": 82115, "v": 13767, "a": 18156, "r": 3621}
    assert sum(1 for _ in wn.all_synsets()) == 117659
    # the NLTK book, chapter 2, section 5
    assert wn.synsets("motorcar") == [wn.synset("car.n.01")]
    car = wn.synset("car.n.01")
    assert car.lemma_names() == ["car", "auto", "automobile", "machine", "motorcar"]
    assert car.definition() == (
        "a motor vehicle with four wheels; usually propelled by an internal "
        "combustion engine"
    )
    right = wn.synset("right_whale.n.01")
    assert [
        right.path_similarity(wn.synset(name))
        for name in ("minke_whale.n.01", "orca.n.01", "tortoise.n.01", "novel.n.01")
    ] == [0.25, 0.16666666666666666, 0.07692307692307693, 0.043478260869565216]


@answers("wordnet_ic")
def _wordnet_ic():
    from nltk.corpus import wordnet as wn
    from nltk.corpus import wordnet_ic

    # nltk/test/wordnet.doctest: the similarities of dog and cat under the Brown IC
    ic = wordnet_ic.ic("ic-brown.dat")
    dog, cat = wn.synset("dog.n.01"), wn.synset("cat.n.01")
    assert dog.res_similarity(cat, ic) == 7.911666509036577
    assert dog.jcn_similarity(cat, ic) == 0.4497755285516739
    assert dog.lin_similarity(cat, ic) == 0.8768009843733973
    # every information content file loads, and gives the root its count
    for fid in wordnet_ic.fileids():
        content = wordnet_ic.ic(fid)
        assert set(content) == {"n", "v"} and content["n"][0] > 0, fid


@answers("sentiwordnet")
def _sentiwordnet():
    from nltk.corpus import sentiwordnet

    synsets = list(sentiwordnet.all_senti_synsets())
    # SentiWordNet 3.0 scores every synset of WordNet 3.0, each split in three parts
    assert len(synsets) == 117659
    wrong = [
        s
        for s in synsets
        if abs(s.pos_score() + s.neg_score() + s.obj_score() - 1) > 1e-9
    ]
    assert wrong == []


# Corpora: sizes their READMEs and the papers that made them give.


@answers("reuters")
def _reuters():
    from nltk.corpus import reuters

    # its README: ApteMod, 10788 documents, 7769 for training and 3019 for testing
    fileids = reuters.fileids()
    assert len(fileids) == 10788
    assert sum(f.startswith("training/") for f in fileids) == 7769
    assert sum(f.startswith("test/") for f in fileids) == 3019
    assert len(reuters.categories()) == 90


@answers("nps_chat")
def _nps_chat():
    from nltk.corpus import nps_chat

    # its README: 10,567 posts, and each file is named for its number of posts
    assert len(nps_chat.posts()) == 10567
    for fid in nps_chat.fileids():
        named = int(fid.split("_")[1].replace("posts.xml", ""))
        assert len(nps_chat.posts(fid)) == named, fid


def framenet_departures(reader):
    """Each view of a FrameNet read to its end: its size, or what it raises."""
    found = {}
    for name in (
        "frames",
        "lus",
        "docs",
        "fes",
        "semtypes",
        "frame_relations",
        "fe_relations",
        "exemplars",
        "ft_sents",
    ):
        try:
            found[name] = sum(1 for _ in getattr(reader, name)())
        except Exception as e:
            found[name] = f"{type(e).__name__}: {e}"[:200]
    return found


@answers("framenet_v17")
def _framenet_17():
    from nltk.corpus import framenet

    found = framenet_departures(framenet)
    # its README: 1,221 frame files, 13,572 lexical unit files, 107 full-text documents
    assert (found["frames"], found["lus"], found["docs"]) == (1221, 13572, 107)
    same_departures("framenet", "framenet_v17", found)


@answers("framenet_v15")
def _framenet_15():
    from nltk.corpus import framenet15

    same_departures("framenet", "framenet_v15", framenet_departures(framenet15))


@answers("timit")
def _timit():
    from nltk.corpus import timit

    # its README: 16 speakers reading 10 sentences each; every recording reads
    utterances = timit.utteranceids()
    assert len(utterances) == 160
    assert len({u.split("/")[0] for u in utterances}) == 16
    for utterance in utterances:
        assert timit.wav(utterance)[:4] == b"RIFF", utterance
        assert timit.words(utterance) and timit.phones(utterance), utterance


@answers("propbank")
def _propbank():
    from nltk.corpus import propbank

    # one proposition per line of prop.txt, every line read
    lines = nltk.data.load(
        "corpora/propbank/prop.txt", format="raw", cache=False
    ).count(b"\n")
    assert len(propbank.instances()) == lines == 112917


@answers("sinica_treebank")
def _sinica():
    from nltk.corpus import sinica_treebank

    # its README: 10,000 parsed sentences
    assert len(sinica_treebank.parsed_sents()) == 10000


@answers("ppattach")
def _ppattach():
    from nltk.corpus import ppattach

    # Ratnaparkhi, Reynar and Roukos (1994): 20801 training, 4039 development, 3097 test
    sizes = {f: len(ppattach.attachments(f)) for f in ppattach.fileids()}
    assert {k: sizes[k] for k in ("training", "devset", "test")} == {
        "training": 20801,
        "devset": 4039,
        "test": 3097,
    }


@answers("senseval")
def _senseval():
    from nltk.corpus import senseval

    # Leacock, Chodorow and Miller (1998): the instances of the four words
    sizes = {f: len(senseval.instances(f)) for f in senseval.fileids()}
    assert sizes == {
        "hard.pos": 4333,
        "interest.pos": 2368,
        "line.pos": 4146,
        "serve.pos": 4378,
    }


@answers("qc")
def _qc():
    from nltk.corpus import qc

    # Li and Roth (2002): 5452 training and 500 test questions
    assert {f: len(qc.tuples(f)) for f in qc.fileids()} == {
        "train.txt": 5452,
        "test.txt": 500,
    }


@answers("rte")
def _rte():
    import re

    from nltk.corpus import rte

    # every pair of every file is read: as many as the file has pair elements
    for fid in rte.fileids():
        raw = nltk.data.load(f"corpora/rte/{fid}", format="text", cache=False)
        assert len(rte.pairs(fid)) == len(re.findall(r"<pair\b", raw)), fid
    # the RTE challenges: 567 and 800 pairs in RTE-1, 800 each in RTE-3
    sizes = {f: len(rte.pairs(f)) for f in rte.fileids()}
    assert {
        k: sizes[k]
        for k in ("rte1_dev.xml", "rte1_test.xml", "rte3_dev.xml", "rte3_test.xml")
    } == {
        "rte1_dev.xml": 567,
        "rte1_test.xml": 800,
        "rte3_dev.xml": 800,
        "rte3_test.xml": 800,
    }


@answers("movie_reviews")
def _movie_reviews():
    from nltk.corpus import movie_reviews

    # Pang and Lee (2004), polarity dataset v2.0: 1000 positive and 1000 negative
    assert {c: len(movie_reviews.fileids(c)) for c in movie_reviews.categories()} == {
        "neg": 1000,
        "pos": 1000,
    }


@answers("sentence_polarity")
def _sentence_polarity():
    from nltk.corpus import sentence_polarity

    # its README: 5331 positive and 5331 negative snippets
    sizes = {
        c: len(sentence_polarity.sents(categories=c))
        for c in sentence_polarity.categories()
    }
    assert sizes == {"neg": 5331, "pos": 5331}


@answers("subjectivity")
def _subjectivity():
    from nltk.corpus import subjectivity

    # its README: 5000 subjective and 5000 objective sentences
    sizes = {
        c: len(subjectivity.sents(categories=c)) for c in subjectivity.categories()
    }
    assert sizes == {"obj": 5000, "subj": 5000}


@answers("twitter_samples")
def _twitter_samples():
    from nltk.corpus import twitter_samples

    # nltk/test/twitter.ipynb and the howto: 5000, 5000 and 20000 tweets
    sizes = {f: len(twitter_samples.strings(f)) for f in twitter_samples.fileids()}
    assert sizes == {
        "negative_tweets.json": 5000,
        "positive_tweets.json": 5000,
        "tweets.20150430-223406.json": 20000,
    }
    # every tweet is a JSON line that the reader parses to the same text
    for fid in twitter_samples.fileids():
        docs = twitter_samples.docs(fid)
        assert [d["text"] for d in docs] == twitter_samples.strings(fid), fid


@answers("opinion_lexicon")
def _opinion_lexicon():
    from nltk.corpus import opinion_lexicon

    # Hu and Liu (2004): 2006 positive and 4783 negative words
    assert (len(opinion_lexicon.positive()), len(opinion_lexicon.negative())) == (
        2006,
        4783,
    )


@answers("conll2002")
def _conll2002():
    from nltk.corpus import conll2002

    # Tjong Kim Sang (2002), table 1: the tokens of each file, counting the
    # -DOCSTART- lines of the Dutch files, which the reader leaves out
    tokens = {
        "esp.train": 264715,
        "esp.testa": 52923,
        "esp.testb": 51533,
        "ned.train": 202931,
        "ned.testa": 37761,
        "ned.testb": 68994,
    }
    for fid, expected in tokens.items():
        lines = nltk.data.load(
            f"corpora/conll2002/{fid}", format="raw", cache=False
        ).split(b"\n")
        starts = sum(1 for line in lines if line.startswith(b"-DOCSTART-"))
        assert len(conll2002.words(fid)) + starts == expected, fid


@answers("nombank.1.0")
def _nombank():
    from nltk.corpus import nombank

    # one proposition per line of the data file, every line read
    lines = nltk.data.load(
        "corpora/nombank.1.0/nombank.1.0", format="raw", cache=False
    ).count(b"\n")
    assert len(nombank.instances()) == lines == 114574


@answers("names")
def _names():
    from nltk.corpus import names

    # the NLTK book, chapter 2, section 4.1
    assert (len(names.words("male.txt")), len(names.words("female.txt"))) == (
        2943,
        5001,
    )


@answers("cmudict")
def _cmudict():
    from nltk.corpus import cmudict

    # the NLTK book, chapter 2, section 4.2
    entries = cmudict.entries()
    assert len(entries) == 133737
    assert cmudict.dict()["fire"] == [["F", "AY1", "ER0"], ["F", "AY1", "R"]]


@answers("swadesh")
def _swadesh():
    from nltk.corpus import swadesh

    # Swadesh's list of 207 concepts; a language may lack a word for some, and
    # every word a file holds, one to a line, is read
    assert len(swadesh.words("en")) == 207
    for fid in swadesh.fileids():
        words = [line for line in _lines(f"corpora/swadesh/{fid}") if line.strip()]
        assert len(swadesh.words(fid)) == len(words) <= 207, fid


# Grammars, the chat80 database: the book's printed outputs, and self-consistency.


@answers("book_grammars", "city_database", "chat80")
def _book_grammars():
    from nltk.parse import load_parser
    from nltk.sem import chat80

    # the NLTK book, chapter 9, section 1.2
    trees = list(
        load_parser("grammars/book_grammars/feat0.fcfg").parse(
            "Kim likes children".split()
        )
    )
    assert [str(t).split() for t in trees] == [
        (
            "(S[] (NP[NUM='sg'] (PropN[NUM='sg'] Kim)) (VP[NUM='sg', TENSE='pres'] "
            "(TV[NUM='sg', TENSE='pres'] likes) (NP[NUM='pl'] (N[NUM='pl'] children))))"
        ).split()
    ]
    # chapter 10, section 1.1: English to SQL, then the query on the city database
    trees = list(
        load_parser("grammars/book_grammars/sql0.fcfg").parse(
            "What cities are located in China".split()
        )
    )
    query = " ".join(s for s in trees[0].label()["SEM"] if s)
    assert query == 'SELECT City FROM city_table WHERE Country="china"'
    rows = chat80.sql_query("corpora/city_database/city.db", query)
    assert [r[0] for r in rows] == (
        "canton chungking dairen harbin kowloon mukden peking shanghai sian tientsin".split()
    )
    # every grammar of the package loads, the DRT ones with drt.doctest's parser
    from nltk.sem.drt import DrtParser

    for name in _listing(nltk.data.find("grammars/book_grammars/")):
        if name.endswith((".fcfg", ".fol")):
            drt = {"logic_parser": DrtParser()} if name == "drt.fcfg" else {}
            assert nltk.data.load(f"grammars/book_grammars/{name}", **drt), name


@answers("spanish_grammars", "basque_grammars", "sample_grammars")
def _small_grammars():
    from nltk.parse import ChartParser

    # no documented examples: every sentence each context-free grammar generates
    # has a parse, and every grammar of the package loads in its format
    for package in ("spanish_grammars", "basque_grammars", "sample_grammars"):
        unloadable = {}
        for name in sorted(_listing(nltk.data.find(f"grammars/{package}/"))):
            path = f"grammars/{package}/{name}"
            ext = name.rsplit(".", 1)[-1]
            if ext in ("cfg", "pcfg"):
                grammar = nltk.data.load(path)
                parser = ChartParser(grammar, max_time=TRUSTED_GRAMMAR_SECONDS)
                sentences = _language(grammar)
                assert sentences, path
                unparsed = [
                    s for s in sentences if not any(True for _ in parser.parse(s))
                ]
                assert unparsed == [], (path, unparsed[:5])
            elif ext in ("fcfg", "fol", "val"):
                try:
                    assert nltk.data.load(path), path
                except ValueError as e:
                    unloadable[path] = f"{type(e).__name__}: {e}"[:160]
            elif ext == "regexp":
                rules = nltk.data.load(path, format="text")
                assert nltk.RegexpParser(rules), path
        same_departures("grammars that do not load", package, unloadable)


def _language(grammar):
    """Every sentence of a finite grammar. A recursive one has infinitely many:
    its first 10,000 to the greatest depth NLTK's generation guard (CWE-400)
    allows and that yields any."""
    from nltk.parse.generate import generate

    def refused(e):
        # the step guard, or generate's own refusal of an unbounded left recursion
        return "Refusing to generate" in str(e) or "infinite recursion" in str(e)

    try:
        return list(generate(grammar))
    except (ValueError, RuntimeError) as e:
        if not refused(e):
            raise
    for depth in range(12, 2, -1):
        try:
            sentences = list(generate(grammar, depth=depth, n=10000))
        except (ValueError, RuntimeError) as e:
            if not refused(e):
                raise
            continue
        if sentences:
            return sentences
    raise AssertionError("no sentence generated to any depth the guard allows")


@answers("bllip_wsj_no_aux")
def _bllip_model():
    # bllipparser builds with GCC (the full-data job installs it): the model parses
    from nltk.parse.bllip import BllipParser

    parser = BllipParser.from_unified_model_dir(
        nltk.data.find("models/bllip_wsj_no_aux").path
    )
    # the outputs documented in nltk/parse/bllip.py and nltk/test/unit/test_bllip.py
    assert (
        str(parser.parse_one("British left waffles on Falklands .".split())).split()
        == (
            "(S1 (S (NP (JJ British) (NN left)) (VP (VBZ waffles) (PP (IN on) "
            "(NP (NNP Falklands)))) (. .)))"
        ).split()
    )
    parses = parser.parse_all("Time flies".split())
    assert len(parses) == 50
    assert str(parses[0]) == "(S1 (S (NP (NNP Time)) (VP (VBZ flies))))"
    assert str(next(parser.tagged_parse([("Time", "VB"), ("flies", "NNS")]))) == (
        "(S1 (NP (VB Time) (NNS flies)))"
    )
    assert str(next(parser.tagged_parse([("Time", "NN"), ("flies", None)]))) == (
        "(S1 (NP (NN Time) (VBZ flies)))"
    )
    telescope = next(parser.parse("I saw the man with the telescope".split()))
    assert (
        str(telescope).split()
        == (
            "(S1 (S (NP (PRP I)) (VP (VBD saw) (NP (DT the) (NN man)) "
            "(PP (IN with) (NP (DT the) (NN telescope))))))"
        ).split()
    )


# Every WordNet: invariants on every synset and lemma; the multilingual wordnets
# read through it, every language of each.

_INVERSES = [
    ("hypernyms", "hyponyms"),
    ("instance_hypernyms", "instance_hyponyms"),
    ("member_holonyms", "member_meronyms"),
    ("part_holonyms", "part_meronyms"),
    ("substance_holonyms", "substance_meronyms"),
]


def wordnet_departures(wn):
    """What a WordNet breaks of its invariants: each synset is found by its name
    and its offset, each lemma by its sense key, each pointer has its inverse, and
    morphy finds each lowercase one-word lemma as itself."""
    found = defaultdict(list)
    for synset in wn.all_synsets():
        name = synset.name()
        if wn.synset(name) != synset:
            found["by name"].append(name)
        if wn.synset_from_pos_and_offset(synset.pos(), synset.offset()) != synset:
            found["by offset"].append(name)
        for pointer, inverse in _INVERSES:
            for other in getattr(synset, pointer)():
                if synset not in getattr(other, inverse)():
                    found[f"{pointer} without {inverse}"].append([name, other.name()])
        pos = "a" if synset.pos() == "s" else synset.pos()
        for lemma in synset.lemmas():
            try:
                if wn.lemma_from_key(lemma.key()) != lemma:
                    found["not found by its key"].append(lemma.key())
            except nltk.corpus.reader.wordnet.WordNetError:
                found["its key raises"].append(lemma.key())
            word = lemma.name()
            if word.isalpha() and word.islower() and word not in wn._morphy(word, pos):
                found["morphy misses it"].append([word, pos])
    return {k: sorted(v) for k, v in sorted(found.items())}


def _wordnet_check(pid):
    def check():
        import importlib

        reader = getattr(importlib.import_module("nltk.corpus"), pid)
        same_departures("wordnets", pid, wordnet_departures(reader))

    return check


for _pid in ("wordnet", "wordnet31", "wordnet2021", "wordnet2022", "english_wordnet"):
    answers(_pid)(_wordnet_check(_pid))


def omw_languages(reader):
    """Language -> lemmas of it, for every language a multilingual wordnet adds;
    every lemma's synset, by its offset, is a synset of the English WordNet."""
    reader.add_omw()
    sizes = {}
    for lang in sorted(set(reader.langs()) - {"eng"}):
        lemmas = reader.all_lemma_names(lang=lang)
        sizes[lang] = sum(1 for _ in lemmas)
        for synset in reader.all_omw_synsets(lang=lang):
            assert (
                reader.synset_from_pos_and_offset(synset.pos(), synset.offset())
                == synset
            )
    return sizes


@answers("omw-2.0")
def _omw_2():
    from nltk.corpus import wordnet

    sizes = omw_languages(wordnet)
    assert sizes and all(sizes.values()), sizes
    # nltk/test/wordnet.doctest, as printed
    assert wordnet.synset("dog.n.01").lemma_names("ita") == ["cane", "Canis_familiaris"]
    assert (
        wordnet.synset("spy.n.01").lemma_names("jpn")
        == (
            "いぬ スパイ まわし者 回し者 回者 密偵 工作員 廻し者 廻者 探 探り 犬 "
            "秘密捜査員 諜報員 諜者 間者 間諜 隠密"
        ).split()
    )


def _older_omw_package(pid):
    """The older multilingual wordnets, read by WordNet as its OMW 2.0 is."""

    def check():
        from nltk.corpus.reader import CorpusReader, WordNetCorpusReader
        from nltk.corpus.util import LazyCorpusLoader

        omw = LazyCorpusLoader(
            pid, CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"
        )
        reader = WordNetCorpusReader(nltk.corpus.wordnet.root, omw)
        sizes = omw_languages(reader)
        assert sizes and all(sizes.values()), (pid, sizes)

    return check


ANSWERS["omw"] = [_older_omw_package("omw")]
ANSWERS["omw-1.4"] = [_older_omw_package("omw-1.4")]


@answers("extended_omw")
def _extended_omw():
    from nltk.corpus import wordnet

    before = set(wordnet.langs())
    wordnet.add_exomw()
    added = sorted(set(wordnet.langs()) - before)
    # every language of the extended OMW is read, each giving lemmas
    assert len(added) == 1191, len(added)
    empty = [
        lang
        for lang in added
        if not any(True for _ in wordnet.all_lemma_names(lang=lang))
    ]
    # nearly all of a script outside the Basic Multilingual Plane
    same_departures("extended_omw", "languages without lemmas", empty)


# Corpora no NLTK loader opens: what their READMEs state, and agreement between
# the files of a package.


@answers("pil")
def _pil():
    # its README: 471 patient information leaflets
    files = _listing(nltk.data.find("corpora/pil/"))
    assert sum(f.endswith(".sgml") for f in files) == 471


@answers("problem_reports")
def _problem_reports():
    # its README: the first 10,000 lines of each project's reports, or all of them
    for project in ("apache", "eclipse", "firefox", "linux", "openoffice"):
        lines = _lines(f"corpora/problem_reports/{project}")
        assert 0 < len(lines) <= 10000, project


@answers("biocreative_ppi")
def _biocreative():
    import re

    # its README: 1000 sentences in each of the two sentence files
    for name in ("bc_sentences.xml", "bc_sentences_xs.xml"):
        raw = nltk.data.load(
            f"corpora/biocreative_ppi/{name}", format="raw", cache=False
        )
        assert len(re.findall(rb"<sentence\b", raw)) == 1000, name


@answers("dolch")
def _dolch():
    # Dolch's lists: the 220 service words in six parts of speech, and 95 nouns
    counts = {
        f: len([w for w in _lines(f"corpora/dolch/{f}") if w.strip()])
        for f in (
            "adjectives",
            "adverbs",
            "conjunctions",
            "prepositions",
            "pronouns",
            "verbs",
            "nouns",
        )
    }
    assert sum(v for k, v in counts.items() if k != "nouns") == 220, counts
    assert counts["nouns"] == 95


@answers("unicode_samples")
def _unicode_samples():
    from nltk import xmlsec

    def sentence(name, encoding):
        raw = nltk.data.load(
            f"corpora/unicode_samples/{name}", format="raw", cache=False
        )
        # expat reads no multi-byte encoding but UTF-8: decode, drop the declaration
        text = raw.decode(encoding).split("?>", 1)[1]
        return [s.text.strip() for s in xmlsec.fromstring(text).iter("sent")]

    # the GB2312 and UTF-8 copies of the Sinorama sample hold the same sentence
    gb = sentence("sinorama-gb.xml", "gb2312")
    utf8 = sentence("sinorama-utf8.xml", "utf-8")
    assert gb == utf8 and gb, (gb, utf8)
    text = nltk.data.load(
        "corpora/unicode_samples/polish-lat2.txt", format="raw", cache=False
    )
    assert text.decode("iso-8859-2").startswith("Pruska Biblioteka Państwowa.")


@answers("brown_tei")
def _brown_tei():
    from nltk.corpus import brown
    from nltk.corpus.reader import XMLCorpusReader

    # the TEI edition of the Brown corpus: one text for each of Brown's 500 files
    reader = XMLCorpusReader(nltk.data.find("corpora/brown_tei/"), r"[a-r]\d\d\.xml")
    assert sorted("c" + f[:-4] for f in reader.fileids()) == sorted(brown.fileids())
    for fid in reader.fileids():
        assert reader.xml(fid) is not None, fid


@answers("pe08")
def _pe08():
    from nltk.corpus.reader import BracketParseCorpusReader

    # the parser evaluation sets: each .ptb file parses, sentence for sentence
    reader = BracketParseCorpusReader(nltk.data.find("corpora/pe08/"), r".*\.ptb")
    for fid in reader.fileids():
        trees = reader.parsed_sents(fid)
        assert len(trees) > 0 and all(t.leaves() for t in trees), fid


@answers("smultron")
def _smultron():
    from nltk import xmlsec

    def tree(name):
        raw = nltk.data.load(f"corpora/smultron/{name}", format="raw", cache=False)
        return xmlsec.fromstring(raw)

    # each alignment file holds the number of alignments it states, and every
    # node it aligns is a node of the treebank it names
    files = _listing(nltk.data.find("corpora/smultron/"))
    alignments = [f for f in files if f.startswith("alignments_")]
    assert alignments
    for name in alignments:
        root = tree(name)
        banks = {
            b.get("id"): {
                n.get("id")
                for n in tree(b.get("filename")).iter()
                if n.tag in ("t", "nt")
            }
            for b in root.iter("treebank")
        }
        aligned = list(root.iter("align"))
        assert len(aligned) == int(root.find("head/alignment-metadata/size").text), name
        missing = [
            (n.get("treebank_id"), n.get("node_id"))
            for a in aligned
            for n in a.iter("node")
            if n.get("node_id") not in banks[n.get("treebank_id")]
        ]
        assert missing == [], (name, missing[:10])


@answers("ptb")
def _ptb():
    import re

    # NLTK reads the full Penn Treebank from LDC; the package carries its file list
    lines = _lines("corpora/ptb/allcats.txt")
    assert lines and all(re.fullmatch(r"\S+\.MRG \S+", line) for line in lines)


@answers("kimmo", "paradigms", "mock_corpus")
def _xml_or_text():
    # no NLTK module reads these any more; every file is read through nltk.data,
    # and every XML file parses with NLTK's XML reader
    from nltk import xmlsec

    for pid in ("kimmo", "paradigms", "mock_corpus"):
        for name in _listing(nltk.data.find(f"corpora/{pid}/")):
            raw = nltk.data.load(f"corpora/{pid}/{name}", format="raw", cache=False)
            if name.endswith(".xml"):
                assert xmlsec.fromstring(raw) is not None, name


# Every corpus reader: the views of each file agree.


def _view(reader, name, fid):
    try:
        return list(getattr(reader, name)(fid))
    except Exception:
        # a view this reader does not offer for this file: nothing to compare
        return None


def _all_words(value):
    return isinstance(value, list) and all(isinstance(w, str) for w in value)


def _all_tagged(value):
    return isinstance(value, list) and all(
        isinstance(x, tuple) and len(x) == 2 and all(isinstance(y, str) for y in x)
        for x in value
    )


def _graph_leaves(graph):
    nodes = [graph.nodes[i] for i in sorted(graph.nodes) if i]
    return [n["word"] for n in nodes], [(n["word"], n["tag"]) for n in nodes]


def reader_departures(reader):
    """The (file, invariant) pairs a reader breaks, over every one of its files:
    the words of its tagged, parsed and chunked views are its words, its words
    are its flattened sentences (the same characters, for a plaintext reader,
    which splits sentences before words), a plaintext reader's words are the
    tokens of its raw text, and each file is in every category it is listed in."""
    from nltk.corpus.reader import (
        CategorizedPlaintextCorpusReader,
        PlaintextCorpusReader,
    )
    from nltk.parse import DependencyGraph
    from nltk.tree import Tree

    # a lazy loader becomes the reader it loads at its first use: load it first
    fileids = list(reader.fileids())
    plaintext = isinstance(reader, PlaintextCorpusReader)
    exact_plaintext = type(reader) in (
        PlaintextCorpusReader,
        CategorizedPlaintextCorpusReader,
    )
    broken = set()
    views = (
        "words",
        "sents",
        "paras",
        "tagged_words",
        "tagged_sents",
        "tagged_paras",
        "parsed_sents",
        "chunked_sents",
        "iob_sents",
    )
    for fid in fileids:
        v = {
            name: _view(reader, name, fid)
            for name in views
            if callable(getattr(reader, name, None))
        }
        words = v.get("words") if _all_words(v.get("words")) else None
        sents = (
            v.get("sents")
            if isinstance(v.get("sents"), list)
            and all(_all_words(s) for s in v["sents"])
            else None
        )
        tagged_words = (
            v.get("tagged_words") if _all_tagged(v.get("tagged_words")) else None
        )
        tagged_sents = (
            v.get("tagged_sents")
            if isinstance(v.get("tagged_sents"), list)
            and all(_all_tagged(s) for s in v["tagged_sents"])
            else None
        )

        def need(invariant, a, b):
            if a != b:
                broken.add((fid, invariant))

        if words is not None and sents is not None:
            flat = [w for s in sents for w in s]
            if plaintext:
                need(
                    "words are the characters of the sentences",
                    "".join(words),
                    "".join(flat),
                )
            else:
                need("words are the flattened sentences", words, flat)
        if sents is not None and v.get("paras") is not None:
            need(
                "sentences are the flattened paragraphs",
                sents,
                [s for p in v["paras"] for s in p],
            )
        if words is not None and tagged_words is not None:
            need(
                "words are the words of tagged_words",
                words,
                [w for w, _ in tagged_words],
            )
        if sents is not None and tagged_sents is not None:
            need(
                "sentences are the words of tagged_sents",
                sents,
                [[w for w, _ in s] for s in tagged_sents],
            )
        if tagged_words is not None and tagged_sents is not None:
            need(
                "tagged_words are the flattened tagged_sents",
                tagged_words,
                [x for s in tagged_sents for x in s],
            )
        parsed = v.get("parsed_sents")
        if parsed and all(isinstance(t, (Tree, DependencyGraph)) for t in parsed):
            leaves = [
                t.leaves() if isinstance(t, Tree) else _graph_leaves(t)[0]
                for t in parsed
            ]
            pos = [
                t.pos() if isinstance(t, Tree) else _graph_leaves(t)[1] for t in parsed
            ]
            if sents is not None:
                need("sentences are the leaves of parsed_sents", sents, leaves)
            if tagged_sents is not None:
                need("tagged_sents are the tags of parsed_sents", tagged_sents, pos)
        chunked = v.get("chunked_sents")
        if (
            chunked
            and tagged_sents is not None
            and all(isinstance(t, Tree) for t in chunked)
        ):
            need(
                "tagged_sents are the leaves of chunked_sents",
                tagged_sents,
                [t.leaves() for t in chunked],
            )
        iob = v.get("iob_sents")
        if iob and tagged_sents is not None:
            need(
                "tagged_sents are the words and tags of iob_sents",
                tagged_sents,
                [[(w, t) for w, t, _ in s] for s in iob],
            )
        if exact_plaintext and words is not None:
            need(
                "words are the tokens of the raw text",
                words,
                list(reader._word_tokenizer.tokenize(reader.raw(fid))),
            )
    if callable(getattr(reader, "categories", None)):
        try:
            categories = set(reader.categories())
            for fid in reader.fileids():
                for category in reader.categories(fid):
                    if category not in categories or fid not in reader.fileids(
                        category
                    ):
                        broken.add((fid, "a file is in each of its categories"))
            covered = (
                set().union(*(reader.fileids(c) for c in categories))
                if categories
                else set()
            )
            if categories and covered != set(reader.fileids()):
                broken.add(("*", "the categories cover every file"))
        except Exception as e:
            broken.add(("*", f"categories: {type(e).__name__}"))
    return sorted([fid, invariant] for fid, invariant in broken)


def corpus_readers(pid):
    """(label, reader) for every reader of a corpus package: its loaders in
    nltk.corpus, or the reader NLTK has for it."""
    import importlib

    readers = []
    for module_name, name in _LOADERS.get(pid, []):
        readers.append((name, getattr(importlib.import_module(module_name), name)))
    if pid in _BUILT:
        try:
            readers.append((pid, _BUILT[pid]()))
        except Exception as e:
            message = f"cannot be built: {type(e).__name__}: {e}"
            readers.append((pid, _masked(message)[:200]))
    return readers


def _masked(text):
    """``text`` with the data directories replaced, so a pin holds on any machine."""
    for root in sorted(nltk.data.path, key=len, reverse=True):
        if root and os.path.isdir(root):
            text = text.replace(root, "<data>")
    return text


def _loader_table():
    """Package id -> (module, name) of each loader, read before any is loaded:
    a loaded one is its reader, which no longer says what it loads."""
    import importlib

    from nltk.corpus.util import LazyCorpusLoader

    table = defaultdict(list)
    for module_name in ("nltk.corpus", "nltk.corpus.europarl_raw"):
        module = importlib.import_module(module_name)
        for name in sorted(dir(module)):
            loader = getattr(module, name, None)
            if isinstance(loader, LazyCorpusLoader):
                pid = vars(loader)["_LazyCorpusLoader__name"].split("/")[0]
                table[pid].append((module_name, name))
    return table


_LOADERS = _loader_table() if FULL else {}


def _build(pid):
    from nltk.corpus.reader import (
        Pl196xCorpusReader,
        VerbnetCorpusReader,
        YCOECorpusReader,
    )

    root = nltk.data.find(f"corpora/{pid}/")
    if pid == "pl196x":
        return Pl196xCorpusReader(
            root, r".*\.xml", textids="textids.txt", cat_file="cats.txt"
        )
    if pid == "ycoe":
        return YCOECorpusReader(root)
    return VerbnetCorpusReader(root, r"(?!\.).*\.xml")


#: Corpora with no loader in nltk.corpus, read with the reader NLTK has for them.
_BUILT = {pid: (lambda p=pid: _build(p)) for pid in ("pl196x", "ycoe", "verbnet3")}

#: Readers that are not of words: their files are XML of another kind, read
#: through their own checks, and the generic views do not apply.
_NOT_WORD_READERS = {
    "framenet_v15",
    "framenet_v17",
    "wordnet",
    "wordnet31",
    "wordnet2021",
    "wordnet2022",
    "english_wordnet",
    "timit",
}


def _invariants(pid):
    def check():
        found = {
            label: r if isinstance(r, str) else reader_departures(r)
            for label, r in corpus_readers(pid)
        }
        assert found, f"{pid} has no reader"
        same_departures("readers", pid, {k: v for k, v in found.items() if v})

    return check


def _register_corpora():
    for pkg in INDEX:
        if pkg["subdir"] == "corpora" and pkg["id"] not in _NOT_WORD_READERS:
            pid = pkg["id"]
            if pid in _BUILT or pid in _LOADERS:
                ANSWERS[pid].append(_invariants(pid))


if FULL:
    _register_corpora()


@answers("mwa_ppdb")
def _mwa_ppdb():
    from nltk.corpus.reader.wordlist import MWAPPDBCorpusReader
    from nltk.corpus.util import LazyCorpusLoader

    # nltk.corpus has this loader commented out; it is built as written there
    reader = LazyCorpusLoader(
        "mwa_ppdb",
        MWAPPDBCorpusReader,
        r"(?!README|\.).*",
        nltk_data_subdir="misc",
        encoding="utf8",
    )
    (fid,) = reader.fileids()
    lines = [line for line in _lines(f"misc/mwa_ppdb/{fid}") if line.strip()]
    entries = reader.entries()
    # one pair of synonyms on every line, every line read
    assert len(entries) == len(lines) == 210372
    # entries splits lines with str.splitlines, which breaks at \x1c to \x1e too
    halves = [
        [i, *pair] for i, pair in enumerate(entries) if len(pair) != 2 or not all(pair)
    ]
    same_departures("mwa_ppdb", "entries without both sides", halves)

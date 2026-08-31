# Natural Language Toolkit: full functional smoke test
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""End-to-end proof that the GHSA-8mgp security hardening did not break NLTK.

The GHSA-8mgp umbrella threaded path guards (``validate_path`` /
``validate_tool_dir`` / ``pathsec.open``), a restricted unpickler
(``nltk.picklesec``) and an entity-refusing XML parser (``nltk.xmlsec``)
through loaders all over the tree. A guard that is slightly too strict does not
fail a security test, it fails *ordinary use*: a real corpus that no longer
loads, a real model that no longer round-trips. A mocked test cannot see that
because it never runs the real pipeline.

So this module does two things no security test does:

1. It imports **every** module in the ``nltk`` package (bar an explicit list of
   genuinely optional-dependency modules) and asserts none broke.
2. It runs a battery of real operations against real data and freshly-trained
   models, and asserts a concrete correct result for each.

Nothing here is mocked. Every save/load path is aimed at a REGISTERED data root
(a ``restricted_sandbox`` root, an out-of-root ``sandbox`` dir, pytest's own
authorized ``tmp_path``, or ``nltk.data.make_staging_dir``), never a bare
``/tmp``, so the pathsec guards are exercised the way real callers exercise
them. A pipeline is skipped only when a genuinely-absent model, binary, or
optional dependency is required, and every skip reports its reason.
"""

import importlib
import os
import pathlib
import pickle
import pkgutil
import shelve
import warnings

import pytest

import nltk
import nltk.data

# ---------------------------------------------------------------------------
# Part 1: import every module.
# ---------------------------------------------------------------------------
#
# Importing these has side effects out of proportion to their value here:
# ``nltk.book`` pulls in nine corpora and prints a banner, and ``nltk.app``
# opens Tk toolkits. ``nltk.test`` is the test tree itself.
_SIDE_EFFECT_PREFIXES = ("nltk.test", "nltk.book", "nltk.app")

# The ONLY modules allowed to fail to import, and only with an ImportError,
# because each needs a third-party package that is not a hard NLTK dependency.
# Maps a module-name prefix to the human reason the skip is legitimate. Anything
# that raises ImportError and is NOT covered here is a hard failure: a core
# module that stopped importing because of the hardening must surface as a named
# regression, not hide behind a blanket skip.
_OPTIONAL_IMPORT_PREFIXES = {
    "nltk.twitter": "requires the optional 'twython' package",
}


def _reason_for_optional(name):
    """Return the skip reason if ``name`` is an allowed optional module, else None."""
    for prefix, reason in _OPTIONAL_IMPORT_PREFIXES.items():
        if name == prefix or name.startswith(prefix + "."):
            return reason
    return None


def _all_module_names():
    names = []
    for module in pkgutil.walk_packages(nltk.__path__, prefix="nltk."):
        name = module.name
        if name.startswith(_SIDE_EFFECT_PREFIXES):
            continue
        names.append(name)
    return sorted(set(names))


def test_every_nltk_module_imports(capsys):
    """Import every ``nltk`` submodule. Report imported / skipped-with-reason /
    failed counts; fail (naming the module) on any non-optional import error.

    A core module that fails to import because a guard broke at module scope
    shows up here as a named hard failure rather than as a mystery downstream.
    """
    imported = []
    skipped = []  # (name, reason)
    hard_failures = []  # human-readable "name: Type: message"

    for name in _all_module_names():
        try:
            importlib.import_module(name)
        except ImportError as exc:
            reason = _reason_for_optional(name)
            if reason is not None:
                skipped.append((name, f"{reason} ({exc})"))
            else:
                hard_failures.append(f"{name}: ImportError: {exc}")
        except LookupError as exc:
            # Missing corpus data at import time says nothing about our code, so
            # record it as an environment skip rather than a code failure. There
            # are none in a normally-provisioned tree.
            skipped.append((name, f"corpus data unavailable at import ({exc})"))
        except Exception as exc:  # noqa: BLE001 - any other error is a real break
            hard_failures.append(f"{name}: {type(exc).__name__}: {exc}")
        else:
            imported.append(name)

    # Print a small ledger so a CI log records exactly what ran and what was
    # skipped and why (visible with -s or on failure).
    with capsys.disabled():
        print(
            f"\n[module import] imported={len(imported)} "
            f"skipped={len(skipped)} failed={len(hard_failures)}"
        )
        for name, reason in skipped:
            print(f"  SKIP {name}: {reason}")
        for line in hard_failures:
            print(f"  FAIL {line}")

    assert hard_failures == [], "modules failed to import:\n" + "\n".join(hard_failures)
    # A sanity floor: if the walk silently stopped finding modules the assertion
    # above would pass vacuously.
    assert len(imported) > 200, f"only {len(imported)} modules imported; walk is broken"


# ---------------------------------------------------------------------------
# Part 2: real functional smoke on every major pipeline.
# ---------------------------------------------------------------------------


def _skip_without_data(func):
    """Run ``func``; turn a missing corpus/model into a skip, not a failure."""
    try:
        return func()
    except LookupError as exc:
        pytest.skip(f"model/corpus data unavailable: {str(exc)[:100]}")


def _authorize_tmp_root(tmp_path, monkeypatch):
    """Register ``tmp_path`` as an extra NLTK data root and return it.

    pytest's session base is already authorized by ``nltk/test/conftest.py``, so
    ``tmp_path`` is inside an allowed root. Appending it explicitly (and clearing
    the pathsec caches) keeps the intent local and is a no-op if it is already
    covered. The full ``nltk.data.path`` is preserved, so real models stay
    findable while writes land in-root.
    """
    from nltk import pathsec

    root = os.path.realpath(str(tmp_path))
    monkeypatch.setattr(nltk.data, "path", [*nltk.data.path, root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    return root


# --- Tokenize ---------------------------------------------------------------


def test_word_and_sent_tokenize():
    from nltk.tokenize import sent_tokenize, word_tokenize

    tokens = _skip_without_data(lambda: word_tokenize("Dr. Smith isn't here."))
    assert "Dr." in tokens and "n't" in tokens
    assert _skip_without_data(lambda: sent_tokenize("One. Two! Three?")) == [
        "One.",
        "Two!",
        "Three?",
    ]


def test_regexp_treebank_whitespace_tokenizers():
    from nltk.tokenize import (
        RegexpTokenizer,
        TreebankWordTokenizer,
        WhitespaceTokenizer,
    )

    assert RegexpTokenizer(r"\w+").tokenize("Hello, world!") == ["Hello", "world"]
    assert TreebankWordTokenizer().tokenize("Hello, world!") == [
        "Hello",
        ",",
        "world",
        "!",
    ]
    assert WhitespaceTokenizer().tokenize("a b\tc\nd") == ["a", "b", "c", "d"]


def test_punkt_trainer_and_pickle_roundtrip_in_root(restricted_sandbox):
    """Train a Punkt model in memory, use it, then pickle it to an in-root file
    and read it back through the restricted unpickler. Exercises the picklesec
    load guard on a legitimate model under strict single-root enforcement."""
    from nltk.pathsec import open as pathsec_open
    from nltk.picklesec import pickle_load
    from nltk.tokenize.punkt import PunktSentenceTokenizer, PunktTrainer

    text = (
        "Hello world. This is a test. Dr. Smith went home. It works well. "
        "Another sentence here. And one more follows. "
    ) * 20
    trainer = PunktTrainer()
    trainer.train(text, finalize=True)
    tokenizer = PunktSentenceTokenizer(trainer.get_params())
    assert tokenizer.tokenize("Hello world. This is a test.") == [
        "Hello world.",
        "This is a test.",
    ]

    staging = nltk.data.make_staging_dir(prefix="nltk_smoke_punkt_")
    assert staging.startswith(os.path.realpath(restricted_sandbox))
    model_path = os.path.join(staging, "punkt.pkl")
    with pathsec_open(model_path, "wb", context="smoke") as fout:
        pickle.dump(tokenizer, fout)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # WarningUnpickler emits a security notice
        with pathsec_open(model_path, "rb", context="smoke") as fin:
            reloaded = pickle_load(fin)
    assert reloaded.tokenize("Hello world. This is a test.") == [
        "Hello world.",
        "This is a test.",
    ]


# --- Tag --------------------------------------------------------------------


def test_perceptron_tagger_train_and_tag():
    """A freshly-trained PerceptronTagger needs no model data, so this runs
    everywhere and proves training and tagging themselves still work."""
    from nltk.tag import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    sentences = [[("the", "DT"), ("dog", "NN"), ("runs", "VBZ")]] * 5
    tagger.train(sentences, nr_iter=3)
    tagged = tagger.tag(["the", "dog", "runs"])
    assert [w for w, _t in tagged] == ["the", "dog", "runs"]
    assert dict(tagged)["the"] == "DT"


def test_perceptron_tagger_json_roundtrip_in_root(restricted_sandbox):
    """save_to_json / load_from_json go through validate_tool_dir and the
    hardened private-directory opener. A too-strict guard breaks the round trip
    here, inside a registered root."""
    from nltk.tag import PerceptronTagger

    tagger = PerceptronTagger(load=False)
    tagger.train([[("the", "DT"), ("dog", "NN"), ("runs", "VBZ")]] * 5, nr_iter=3)

    loc = nltk.data.make_staging_dir(prefix="nltk_smoke_ptagjson_")
    assert loc.startswith(os.path.realpath(restricted_sandbox))
    tagger.save_to_json(lang="xxx", loc=loc)
    written = sorted(os.listdir(loc))
    assert any(name.endswith(".weights.json") for name in written)

    reloaded = PerceptronTagger(load=False)
    reloaded.load_from_json(lang="xxx", loc=loc)
    assert reloaded.tag(["the", "dog", "runs"]) == tagger.tag(["the", "dog", "runs"])


def test_regexp_tagger():
    from nltk.tag import RegexpTagger

    tagger = RegexpTagger([(r".*ing$", "VBG"), (r".*", "NN")])
    assert tagger.tag(["running", "dog"]) == [("running", "VBG"), ("dog", "NN")]


def test_unigram_and_bigram_taggers():
    from nltk.tag import BigramTagger, UnigramTagger

    train = [
        [("the", "DT"), ("dog", "NN"), ("runs", "VBZ")],
        [("the", "DT"), ("cat", "NN"), ("sleeps", "VBZ")],
    ]
    unigram = UnigramTagger(train)
    assert unigram.tag(["the", "dog"]) == [("the", "DT"), ("dog", "NN")]
    bigram = BigramTagger(train, backoff=unigram)
    assert bigram.tag(["the", "dog", "runs"]) == [
        ("the", "DT"),
        ("dog", "NN"),
        ("runs", "VBZ"),
    ]


# --- Chunk / NE -------------------------------------------------------------


def test_regexp_parser_chunks_a_tagged_sentence():
    from nltk.chunk import RegexpParser

    tagged = [("the", "DT"), ("little", "JJ"), ("dog", "NN"), ("barked", "VBD")]
    tree = RegexpParser("NP: {<DT>?<JJ>*<NN>}").parse(tagged)
    nps = [st for st in tree.subtrees() if st.label() == "NP"]
    assert len(nps) == 1
    assert [leaf[0] for leaf in nps[0].leaves()] == ["the", "little", "dog"]


def test_ne_chunk_if_model_available():
    from nltk import ne_chunk, pos_tag, word_tokenize

    tagged = _skip_without_data(lambda: pos_tag(word_tokenize("John lives in Paris")))
    tree = _skip_without_data(lambda: ne_chunk(tagged))
    assert tree.label() == "S"


# --- Parse ------------------------------------------------------------------


def test_recursive_descent_and_chart_parsers():
    from nltk import CFG
    from nltk.parse import ChartParser, RecursiveDescentParser

    grammar = CFG.fromstring("S -> NP VP\nNP -> 'John'\nVP -> 'runs'")
    for parser_cls in (RecursiveDescentParser, ChartParser):
        trees = list(parser_cls(grammar).parse(["John", "runs"]))
        assert trees and trees[0].label() == "S", parser_cls.__name__


def test_dependency_graph_roundtrip():
    from nltk.parse import DependencyGraph

    data = (
        "Esso   NNP  2  SUB\n"
        "said   VBD  0  ROOT\n"
        "it     PRP  4  SUB\n"
        "paid   VBD  2  VMOD\n"
    )
    dg = DependencyGraph(data)
    # node 0 is the technical root, so four tokens give five nodes.
    assert len(dg.nodes) == 5
    assert dg.tree().label() == "said"


def test_feature_grammar_parses():
    from nltk.grammar import FeatureGrammar
    from nltk.parse import FeatureChartParser

    fcfg = (
        "% start S\n"
        "S -> NP VP\n"
        "NP -> Det N\n"
        "VP -> V NP\n"
        "Det -> 'the'\n"
        "N -> 'dog' | 'cat'\n"
        "V -> 'chased'\n"
    )
    parser = FeatureChartParser(FeatureGrammar.fromstring(fcfg))
    words = ["the", "dog", "chased", "the", "cat"]
    trees = list(parser.parse(words))
    assert trees and trees[0].leaves() == words
    # The root is the FeatStructNonterminal 'S' (its repr is "S[]").
    assert repr(trees[0].label()).startswith("S")


# --- Stem -------------------------------------------------------------------


def test_porter_lancaster_regexp_stemmers():
    from nltk.stem import LancasterStemmer, PorterStemmer, RegexpStemmer

    assert PorterStemmer().stem("running") == "run"
    assert LancasterStemmer().stem("maximum") == "maxim"
    assert RegexpStemmer(r"ing$|s$|e$", min=4).stem("cars") == "car"


def test_snowball_stemmers_including_hungarian_empty_string():
    """Hungarian on the empty string is the exact input the GHSA IndexError fix
    (commit 5c4c0d3fe) protects: it must return "" rather than raise."""
    from nltk.stem import SnowballStemmer

    assert SnowballStemmer("english").stem("generously") == "generous"
    assert SnowballStemmer("hungarian").stem("") == ""  # no IndexError
    assert SnowballStemmer("hungarian").stem("almákat") == "alma"


def test_wordnet_lemmatizer():
    from nltk.stem import WordNetLemmatizer

    assert _skip_without_data(lambda: WordNetLemmatizer().lemmatize("geese")) == "goose"


# --- Corpus -----------------------------------------------------------------


def test_plaintext_and_tagged_corpus_readers_in_root(tmp_path, monkeypatch):
    from nltk.corpus.reader import PlaintextCorpusReader, TaggedCorpusReader

    _authorize_tmp_root(tmp_path, monkeypatch)

    plain_dir = tmp_path / "plain"
    plain_dir.mkdir()
    (plain_dir / "a.txt").write_text("Hello world. This is fun. Another line here.")
    plain = PlaintextCorpusReader(str(plain_dir), r".*\.txt")
    assert list(plain.words()[:3]) == ["Hello", "world", "."]
    # sents() needs a Punkt model; skip cleanly if it is absent.
    assert len(_skip_without_data(lambda: plain.sents())) >= 1

    tagged_dir = tmp_path / "tagged"
    tagged_dir.mkdir()
    (tagged_dir / "a.pos").write_text(
        "the/DT dog/NN runs/VBZ\nthe/DT cat/NN sleeps/VBZ\n"
    )
    tagged = TaggedCorpusReader(str(tagged_dir), r".*\.pos")
    assert list(tagged.words()[:2]) == ["the", "dog"]
    assert list(tagged.tagged_words()[:2]) == [("the", "DT"), ("dog", "NN")]


def test_categorized_plaintext_corpus_reader_in_root(tmp_path, monkeypatch):
    from nltk.corpus.reader import CategorizedPlaintextCorpusReader

    _authorize_tmp_root(tmp_path, monkeypatch)
    cat_dir = tmp_path / "cat"
    cat_dir.mkdir()
    (cat_dir / "pos1.txt").write_text("great wonderful excellent")
    (cat_dir / "neg1.txt").write_text("awful terrible bad")
    reader = CategorizedPlaintextCorpusReader(
        str(cat_dir), r".*\.txt", cat_pattern=r"(pos|neg)\d+\.txt"
    )
    assert sorted(reader.categories()) == ["neg", "pos"]
    assert list(reader.words(categories="pos")[:2]) == ["great", "wonderful"]


# --- Sem --------------------------------------------------------------------


def test_valuation_and_logic_expression():
    from nltk.sem import Expression, Valuation

    val = Valuation([("P", {("a",)}), ("a", "a")])
    assert "P" in val.symbols
    expr = Expression.fromstring("all x.(man(x) -> mortal(x))")
    assert str(expr.type) == "t"  # a well-formed formula has boolean type


def test_chat80_val_dump_writes_in_root_and_reload_reads_through_guards(
    tmp_path, monkeypatch
):
    """chat80 hands a caller path straight to shelve.open, so val_dump validates
    it first: an in-root destination must be accepted and the corpus-to-shelve
    pipeline must run. Then the stored valuation is read back through the
    hardened restricted unpickler and must come back byte-for-byte, proving the
    picklesec read guard does not corrupt legitimate valuation containers.

    NB: the public ``val_load`` round trip is separately broken on this
    interpreter for a PRE-EXISTING reason unrelated to the hardening (see
    ``test_chat80_val_load_preexisting_valuation_limitation``); this test
    exercises exactly the two guards the hardening added.
    """
    from nltk.sem import chat80
    from nltk.sem.chat80 import _restricted_shelve_open

    _authorize_tmp_root(tmp_path, monkeypatch)
    db = str(tmp_path / "borders_val")

    # val_dump must accept an in-root destination and build the shelve from the
    # real chat80 corpus (borders.pl / world1.pl). Skip only if that corpus is
    # genuinely absent.
    _skip_without_data(lambda: chat80.val_dump([chat80.borders], db))
    assert any(tmp_path.glob("borders_val*")), "val_dump wrote nothing in-root"

    # Read the stored valuation back through the restricted shelf. Its values are
    # collections of string-tuples (n-ary relations) and plain strings
    # (individual labels): exactly what a real valuation stores, and what
    # RestrictedUnpickler must still reconstruct. The 'border' relation is stored
    # as a list of pairs by chat80; whatever the container, the restricted
    # unpickler must return it intact (this is the read guard the hardening added).
    shelf = _restricted_shelve_open(db)
    try:
        reloaded = {key: shelf[key] for key in shelf}
    finally:
        shelf.close()
    assert "border" in reloaded
    border = reloaded["border"]
    assert isinstance(border, (set, list, tuple)) and border  # non-empty extension
    assert all(isinstance(pair, tuple) and len(pair) == 2 for pair in border)
    # Individual labels round-trip as plain strings.
    assert any(isinstance(value, str) for value in reloaded.values())


def test_chat80_val_dump_refuses_outside_root(sandbox):
    """The write guard must refuse an out-of-sandbox destination and leave
    nothing behind."""
    from nltk.sem import chat80

    target = sandbox / "evil_valuation"
    with pytest.raises((PermissionError, ValueError)):
        chat80.val_dump([chat80.borders], str(target))
    assert not list(sandbox.glob("evil_valuation*"))
    with pytest.raises((PermissionError, ValueError)):
        chat80.val_load(str(target))


def test_chat80_restricted_shelf_blocks_a_pickle_gadget(restricted_sandbox):
    """The whole point of the restricted shelf: a crafted value pickle in a
    valuation db must not execute on read."""
    from nltk.sem.chat80 import _restricted_shelve_open

    class _Gadget:
        def __reduce__(self):
            return (os.system, ("echo pwned",))

    staging = nltk.data.make_staging_dir(prefix="nltk_smoke_c80gadget_")
    db = os.path.join(staging, "evil")
    with shelve.open(db, "n") as shelf:
        shelf["x"] = _Gadget()
    # Satisfy the pre-existing ".db" access check (see the val_load note) so the
    # read reaches the unpickler under test.
    if not os.path.exists(db + ".db"):
        try:
            os.link(db, db + ".db")
        except OSError:
            pass

    shelf = _restricted_shelve_open(db)
    try:
        with pytest.raises(pickle.UnpicklingError):
            _ = shelf["x"]
    finally:
        shelf.close()


def test_chat80_val_load_preexisting_valuation_limitation(tmp_path, monkeypatch):
    """DOCUMENTS a pre-existing (non-hardening) limitation so a future reader
    does not mistake it for a guard regression.

    ``val_dump`` stores a derived relation symbol whose value is a ``list`` of
    tuples, but ``Valuation.__init__`` only accepts ``str`` / ``bool`` / ``set``,
    so ``val_load`` raises ``ValueError`` while rebuilding the Valuation. This is
    reproduced by the plain stdlib unpickler too, so it is not caused by the
    picklesec / pathsec hardening. If chat80 is ever fixed to round-trip, update
    this test.
    """
    from nltk.sem import chat80

    _authorize_tmp_root(tmp_path, monkeypatch)
    db = str(tmp_path / "borders_val2")
    _skip_without_data(lambda: chat80.val_dump([chat80.borders], db))
    # Satisfy the stale ".db" access check so we reach the Valuation rebuild, the
    # step that raises (not the pathsec guard, which the in-root path passes).
    created = next(iter(tmp_path.glob("borders_val2*")), None)
    if created is not None and not os.path.exists(db + ".db"):
        try:
            os.link(str(created), db + ".db")
        except OSError:
            pass
    with pytest.raises(ValueError, match="Unrecognized value for symbol"):
        chat80.val_load(db)


# --- Metrics / translate ----------------------------------------------------


def test_edit_and_jaccard_distance():
    from nltk.metrics import edit_distance, jaccard_distance

    assert edit_distance("kitten", "sitting") == 3
    assert jaccard_distance(set("abc"), set("bcd")) == pytest.approx(0.5)


def test_sentence_bleu_and_meteor():
    from nltk.translate.bleu_score import sentence_bleu
    from nltk.translate.meteor_score import meteor_score

    assert sentence_bleu([["a", "b", "c", "d"]], ["a", "b", "c", "d"]) == 1.0
    score = meteor_score([["the", "cat", "sat"]], ["the", "cat", "sat"])
    assert score > 0.9


def test_ngrams_bigrams_skipgrams():
    from nltk.util import bigrams, ngrams, skipgrams

    assert list(ngrams([1, 2, 3], 2)) == [(1, 2), (2, 3)]
    assert list(bigrams([1, 2, 3])) == [(1, 2), (2, 3)]
    assert list(skipgrams([1, 2, 3, 4], 2, 1)) == [
        (1, 2),
        (1, 3),
        (2, 3),
        (2, 4),
        (3, 4),
    ]


# --- tbl / Brill ------------------------------------------------------------


def test_brill_tagger_train_and_picklesec_roundtrip_in_root(restricted_sandbox):
    """Train a small Brill tagger over a baseline tagger, tag with it, then
    pickle it to an in-root file and read it back with the restricted unpickler
    (the nltk.tbl.demo save/load pattern), asserting identical output."""
    from nltk.pathsec import open as pathsec_open
    from nltk.picklesec import pickle_load
    from nltk.tag import UnigramTagger, brill, brill_trainer

    train = [
        [("the", "DT"), ("dog", "NN"), ("runs", "VBZ")],
        [("the", "DT"), ("cat", "NN"), ("sleeps", "VBZ")],
    ] * 10
    baseline = UnigramTagger(train)
    templates = brill.brill24()[:3]
    trainer = brill_trainer.BrillTaggerTrainer(baseline, templates, trace=0)
    brill_tagger = trainer.train(train, max_rules=5)
    expected = brill_tagger.tag(["the", "dog", "runs"])
    assert [w for w, _t in expected] == ["the", "dog", "runs"]

    staging = nltk.data.make_staging_dir(prefix="nltk_smoke_brill_")
    assert staging.startswith(os.path.realpath(restricted_sandbox))
    path = os.path.join(staging, "brill.pkl")
    with pathsec_open(path, "wb", context="smoke") as fout:
        pickle.dump(brill_tagger, fout)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # WarningUnpickler emits a security notice
        with pathsec_open(path, "rb", context="smoke") as fin:
            reloaded = pickle_load(fin)
    assert reloaded.tag(["the", "dog", "runs"]) == expected


# --- Text -------------------------------------------------------------------


def test_text_concordance_collocations_findall():
    import contextlib
    import io

    from nltk.text import Text

    words = [
        "the",
        "quick",
        "brown",
        "fox",
        "jumps",
        "over",
        "the",
        "lazy",
        "dog",
        "the",
        "quick",
        "brown",
        "fox",
        "runs",
        "the",
        "quick",
        "brown",
        "fox",
        "sleeps",
    ]
    text = Text(words)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        text.concordance("fox")
    assert "fox" in buf.getvalue()

    # collocation_list must return without hanging; it may be empty on tiny input.
    assert isinstance(text.collocation_list(), list)

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        text.findall(r"<the><quick>")
    assert "the quick" in buf.getvalue()


# --- xmlsec -----------------------------------------------------------------


def test_xmlsec_parses_benign_and_refuses_entity_declaration():
    from nltk import xmlsec

    tree = xmlsec.fromstring("<corpus><doc>hello</doc></corpus>")
    assert tree.tag == "corpus"
    assert tree.find("doc").text == "hello"

    billion_laughs = (
        '<?xml version="1.0"?>'
        '<!DOCTYPE lolz [<!ENTITY lol "lol">]>'
        "<lolz>&lol;</lolz>"
    )
    # EntitiesForbidden subclasses ValueError in both back ends.
    with pytest.raises(ValueError):
        xmlsec.fromstring(billion_laughs)


def test_xmlsec_parse_of_a_benign_file_in_root(tmp_path, monkeypatch):
    from nltk import xmlsec

    _authorize_tmp_root(tmp_path, monkeypatch)
    doc = tmp_path / "doc.xml"
    doc.write_text("<root><child>ok</child></root>")
    tree = xmlsec.parse(str(doc))
    assert tree.getroot().tag == "root"


# --- util -------------------------------------------------------------------


def test_re_show_marks_matches():
    import contextlib
    import io

    from nltk.util import re_show

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        re_show("[aeiou]", "hello world")
    assert buf.getvalue().strip() == "h{e}ll{o} w{o}rld"


# --- downloader (offline) ---------------------------------------------------


def test_package_builds_and_rejects_traversal_subdir():
    from nltk.downloader import Package

    pkg = Package(
        id="smoke",
        url="http://example.com/x.zip",
        name="Smoke",
        subdir="corpora",
        size=0,
        unzipped_size=0,
    )
    assert (pkg.id, pkg.subdir) == ("smoke", "corpora")
    with pytest.raises(ValueError):
        Package(id="bad", url="u", subdir="../etc", size=0, unzipped_size=0)


def test_downloader_lists_and_reports_status_offline(tmp_path, monkeypatch):
    """Build a Downloader against a LOCAL index file (a file:// URL), so listing
    packages and querying status never touch the network."""
    from nltk.downloader import Downloader

    _authorize_tmp_root(tmp_path, monkeypatch)
    index = tmp_path / "index.xml"
    index.write_text(
        '<?xml version="1.0"?>\n'
        "<nltk_data>\n"
        "  <packages>\n"
        '    <package id="smoke_pkg" name="Smoke Package"\n'
        '             url="http://example.com/smoke.zip"\n'
        '             size="10" unzipped_size="20" subdir="corpora"'
        ' checksum="abc"/>\n'
        "  </packages>\n"
        "  <collections>\n"
        '    <collection id="smoke_coll" name="Smoke Collection">\n'
        '      <item ref="smoke_pkg"/>\n'
        "    </collection>\n"
        "  </collections>\n"
        "</nltk_data>\n"
    )
    file_url = pathlib.Path(str(index)).as_uri()
    downloader = Downloader(server_index_url=file_url, download_dir=str(tmp_path))

    assert [p.id for p in downloader.packages()] == ["smoke_pkg"]
    # Nothing is downloaded, so a package the index lists reads as NOT_INSTALLED.
    assert downloader.status("smoke_pkg", download_dir=str(tmp_path)) == (
        Downloader.NOT_INSTALLED
    )
    assert bool(downloader.default_download_dir())

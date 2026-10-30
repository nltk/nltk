# Natural Language Toolkit: import + functional smoke test
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Proof that the pathsec hardening did not break NLTK.

The security work threads ``validate_path`` / ``validate_model_resource`` through
loaders all over the tree. A guard that is slightly too strict does not fail the
security tests, it fails *ordinary use*, and mocked tests cannot see that: they
never load a real corpus or run a real model.

So this module does two things that no other test file does:

1. imports **every** module in the ``nltk`` package, and
2. runs a battery of real operations against real corpora and real models.

An ``ImportError`` is treated as a missing optional third-party dependency and a
``LookupError`` as missing corpus data, since neither says anything about our
code. Anything else is a hard failure and names the module that broke.
"""

import importlib
import pkgutil

import pytest

import nltk

# Loading these has side effects disproportionate to their value here: nltk.book
# pulls in nine corpora and prints a banner, and nltk.app opens Tk toolkits.
_SKIP_PREFIXES = ("nltk.test.", "nltk.book", "nltk.app")


def _all_module_names():
    names = []
    for module in pkgutil.walk_packages(nltk.__path__, prefix="nltk."):
        name = module.name
        if name.startswith(_SKIP_PREFIXES) or name == "nltk.test":
            continue
        names.append(name)
    return sorted(names)


def test_every_nltk_module_imports():
    """Every module must import. A guard that broke an import at module scope
    shows up here as a named hard failure rather than as a mystery elsewhere."""
    hard_failures = []
    optional = []
    imported = 0
    for name in _all_module_names():
        try:
            importlib.import_module(name)
        except ImportError as exc:
            optional.append((name, str(exc)))
        except LookupError as exc:
            optional.append((name, str(exc)))
        except Exception as exc:
            hard_failures.append(f"{name}: {type(exc).__name__}: {exc}")
        else:
            imported += 1

    assert hard_failures == [], "modules failed to import:\n" + "\n".join(hard_failures)
    # A sanity floor: if the walk silently stopped finding modules the assertion
    # above would pass vacuously.
    assert imported > 200, f"only {imported} modules imported; the walk is broken"


def _skip_without_data(func):
    """Run ``func``, turning missing corpora into a skip rather than a failure."""
    try:
        return func()
    except LookupError as exc:
        pytest.skip(f"corpus data unavailable: {str(exc)[:80]}")


# ---------------------------------------------------------------------------
# Real operations. Nothing here is mocked: each one loads real data through the
# hardened loaders and checks a real result.
# ---------------------------------------------------------------------------


def test_tokenizers_work():
    from nltk.tokenize import sent_tokenize, word_tokenize

    tokens = _skip_without_data(lambda: word_tokenize("Dr. Smith isn't here."))
    assert "Dr." in tokens and "n't" in tokens
    assert _skip_without_data(lambda: sent_tokenize("One. Two! Three?")) == [
        "One.",
        "Two!",
        "Three?",
    ]


def test_pos_tagging_and_chunking_work():
    from nltk.tokenize import word_tokenize

    tagged = _skip_without_data(
        lambda: nltk.pos_tag(word_tokenize("John lives in Paris"))
    )
    assert [word for word, _tag in tagged] == ["John", "lives", "in", "Paris"]
    tree = _skip_without_data(lambda: nltk.ne_chunk(tagged))
    assert tree.label() == "S"


def test_perceptron_tagger_loads_its_pickled_model():
    """The tagger reads a pickled model through the hardened loader, so a
    too-strict path guard breaks it here first."""
    from nltk.tag import PerceptronTagger

    tagged = _skip_without_data(lambda: PerceptronTagger().tag(["The", "dog", "runs"]))
    assert [word for word, _tag in tagged] == ["The", "dog", "runs"]


def test_stemmers_and_lemmatizer_work():
    from nltk.stem import PorterStemmer, SnowballStemmer, WordNetLemmatizer

    assert PorterStemmer().stem("running") == "run"
    assert SnowballStemmer("english").stem("generously") == "generous"
    assert _skip_without_data(lambda: WordNetLemmatizer().lemmatize("geese")) == "goose"


def test_zipped_corpora_load():
    """wordnet and stopwords are read out of zip archives, which is exactly the
    path the decompression guards sit on."""
    from nltk.corpus import stopwords, wordnet

    assert _skip_without_data(lambda: wordnet.synsets("dog")) != []
    assert "the" in _skip_without_data(lambda: stopwords.words("english"))


def test_tagged_and_parsed_corpora_load():
    from nltk.corpus import brown, gutenberg, treebank

    assert _skip_without_data(lambda: brown.tagged_words()[:3]) != []
    assert _skip_without_data(lambda: gutenberg.words("austen-emma.txt")[:5]) != []
    assert _skip_without_data(lambda: treebank.parsed_sents()[0]).label() == "S"


def test_vader_sentiment_works():
    from nltk.sentiment.vader import SentimentIntensityAnalyzer

    scores = _skip_without_data(
        lambda: SentimentIntensityAnalyzer().polarity_scores("NLTK is great!")
    )
    assert scores["compound"] > 0


def test_grammar_parsing_works():
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser

    grammar = CFG.fromstring("S -> NP VP\nNP -> 'John'\nVP -> 'runs'")
    trees = list(RecursiveDescentParser(grammar).parse(["John", "runs"]))
    assert trees and trees[0].label() == "S"


def test_classifier_training_works():
    from nltk.classify import NaiveBayesClassifier

    classifier = NaiveBayesClassifier.train([({"a": 1}, "x"), ({"a": 0}, "y")])
    assert classifier.classify({"a": 1}) == "x"


def test_metrics_and_translate_work():
    from nltk.translate.bleu_score import sentence_bleu

    assert nltk.edit_distance("kitten", "sitting") == 3
    assert sentence_bleu([["a", "b", "c", "d"]], ["a", "b", "c", "d"]) == 1.0


def test_collocations_and_freqdist_work():
    from nltk.corpus import brown

    words = _skip_without_data(lambda: list(brown.words()[:2000]))
    assert nltk.FreqDist(words).most_common(1)[0][1] > 0
    assert nltk.Text(words).collocation_list()[:1] != []

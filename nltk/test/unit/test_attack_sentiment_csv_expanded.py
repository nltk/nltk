# Natural Language Toolkit: expanded attack harness for the sentiment sinks
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The sentiment helpers that write files from untrusted tweets, driven on real
files with the widest matrix and read back the way a spreadsheet, a terminal
or nltk itself would read them: json2csv_preprocess (CWE-1236 formula cells,
CWE-150 terminal sequences, CWE-407 duplicate detection) and output_markdown
(CWE-93 report lines). Nothing is mocked."""

import csv
import gzip
import json
import os

import pytest

from nltk.sentiment.util import json2csv_preprocess, output_markdown
from nltk.test.unit import timing

ESC = chr(0x1B)
BEL = chr(0x07)
NUL = chr(0)
FORMULAS = [
    "=1+1",
    "+1+1",
    "-1+1",
    "@SUM(A1)",
    "\t=1",
    "\r=1",
    " =1",
    chr(0xA0) + "=1",
    "=cmd|' /C calc'!A0",
    '=HYPERLINK("http://evil","x")',
    "-2+3+cmd|' /C calc'!A0",
    "@" + "A" * 3000,
]
CONTROLS = [
    "x" + ESC + "]0;evil" + BEL + "y",
    "x" + ESC + "[2J" + "y",
    "x" + chr(0x9B) + "2Jy",
    "x" + NUL + "y",
    "x" + chr(0x85) + "y",
    "x" + chr(0x2028) + "y",
]
BENIGN = [
    "I love this",
    "-5",
    "+3.5",
    "1e5",
    "-0.5%",
    "@user hello",  # a mention leads with @ and is text: defused, not lost
    'it\'s "quoted", with commas',
    "multi\nline tweet",
    "tab\tinside",
    "caf" + chr(0xE9) + " \U0001f600",
]


def _write_tweets(path, texts, **extra):
    with open(path, "w", encoding="utf-8") as fh:
        for i, text in enumerate(texts):
            fh.write(json.dumps({"id": i, "text": text, "lang": "en", **extra}) + "\n")


def _read_csv(path, gz=False):
    opener = gzip.open if gz else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


class TestFormulaAndControlCells:
    @pytest.mark.parametrize("payload", FORMULAS, ids=lambda p: repr(p)[:14])
    def test_a_formula_lead_never_reaches_the_sheet(self, restricted_sandbox, payload):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        _write_tweets(src, [payload])
        json2csv_preprocess(
            src, out, ["id", "text"], remove_duplicates=False, strip_off_emoticons=False
        )
        rows = _read_csv(out)
        assert rows[0] == ["id", "text"] and len(rows) == 2, rows
        cell = rows[1][1]
        assert cell.lstrip()[0] not in "=+-@", cell
        # the industry defusal (an apostrophe) or, for a control-led payload,
        # the escaped control itself now leads the cell: text, not a formula
        assert cell.startswith("'") or cell.startswith("\\"), cell

    @pytest.mark.parametrize("payload", CONTROLS, ids=lambda p: repr(p)[:14])
    def test_a_control_sequence_is_escaped_in_the_cell(
        self, restricted_sandbox, payload
    ):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        _write_tweets(src, [payload])
        json2csv_preprocess(
            src, out, ["id", "text"], remove_duplicates=False, strip_off_emoticons=False
        )
        with open(out, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        for ch in (ESC, BEL, NUL, chr(0x9B), chr(0x85), chr(0x2028)):
            assert ch not in raw, repr(raw)
        assert "x" in _read_csv(out)[1][1]

    @pytest.mark.parametrize("payload", BENIGN, ids=lambda p: repr(p)[:14])
    def test_benign_text_survives_the_round_trip(self, restricted_sandbox, payload):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        _write_tweets(src, [payload])
        json2csv_preprocess(
            src, out, ["id", "text"], remove_duplicates=False, strip_off_emoticons=False
        )
        from nltk.csvsec import sanitize_csv_field

        rows = _read_csv(out)
        assert len(rows) == 2 and rows[1][0] == "0"
        cell = rows[1][1]
        # unchanged, or defused with a leading apostrophe and otherwise intact
        assert cell in (payload, "'" + payload), cell
        assert cell == sanitize_csv_field(payload)

    def test_a_hostile_header_field_is_defused_too(self, restricted_sandbox):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        _write_tweets(src, ["hello"], **{"=evil": "x", "text2\nrow": "y"})
        json2csv_preprocess(
            src, out, ["id", "=evil", "text2\nrow", "text"], remove_duplicates=False
        )
        rows = _read_csv(out)
        assert rows[0] == ["id", "'=evil", "text2\nrow", "text"], rows[0]
        assert len(rows) == 2

    def test_non_string_cells_keep_their_type_and_none_is_written_empty(
        self, restricted_sandbox
    ):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(
                json.dumps(
                    {
                        "id": 7,
                        "text": "hello",
                        "n": -12,
                        "f": 2.5,
                        "b": True,
                        "z": None,
                        "l": ["=a", 1],
                    }
                )
                + "\n"
            )
        json2csv_preprocess(
            src, out, ["id", "text", "n", "f", "b", "z", "l"], remove_duplicates=False
        )
        rows = _read_csv(out)
        assert rows[1] == ["7", "hello", "-12", "2.5", "True", "", "['=a', 1]"], rows[1]

    def test_gzip_output_is_sanitised_the_same_way(self, restricted_sandbox):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv.gz")
        _write_tweets(src, ["=1+1", "plain"])
        json2csv_preprocess(
            src, out, ["id", "text"], gzip_compress=True, remove_duplicates=False
        )
        rows = _read_csv(out, gz=True)
        assert rows[1][1] == "'=1+1" and rows[2][1] == "plain"


class TestInputBounds:
    def test_a_deeply_nested_json_line_is_refused_not_parsed(self, restricted_sandbox):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("[" * 200000 + "]" * 200000 + "\n")
        with pytest.raises(ValueError, match="nesting"):
            json2csv_preprocess(src, out, ["id", "text"])
        assert not os.path.exists(out) or os.path.getsize(out) < 64

    def test_the_output_path_is_confined_to_the_data_root(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        src = root / "tweets.json"
        _write_tweets(str(src), ["hello"])
        with pytest.raises((PermissionError, ValueError)):
            json2csv_preprocess(str(src), str(outside / "out.csv"), ["id", "text"])
        assert not (outside / "out.csv").exists()

    def test_duplicate_detection_is_linear(self, restricted_sandbox):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        texts = [f"tweet number {i % 100}" for i in range(40000)]
        _write_tweets(src, texts)
        with timing.budget(20, "json2csv_preprocess"):
            json2csv_preprocess(src, out, ["id", "text"])
        rows = _read_csv(out)
        assert len(rows) == 101, len(rows)  # header + one per distinct text
        assert [r[1] for r in rows[1:]] == [
            f"tweet number {i}" for i in range(100)
        ]  # first occurrence order


class TestPreprocessingStillWorks:
    def test_the_filters_and_the_limit(self, restricted_sandbox):
        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        texts = [
            "RT this is a retweet",
            "so funny :P",
            "happy :) and sad :(",
            "great day :)",
            "great   day :)",
            "fine",
            "more",
        ]
        _write_tweets(src, texts)
        json2csv_preprocess(src, out, ["id", "text"], limit=3)
        rows = _read_csv(out)
        # retweet, tongue and ambiguous tweets dropped; emoticons stripped and
        # whitespace collapsed; the collapsed duplicate dropped; limit honoured
        assert [r[1] for r in rows[1:]] == ["great day ", "fine", "more"], rows

    def test_the_csv_reads_back_into_a_tweet_set(self, restricted_sandbox):
        from nltk.sentiment.util import parse_tweets_set

        src = os.path.join(restricted_sandbox, "tweets.json")
        out = os.path.join(restricted_sandbox, "out.csv")
        _write_tweets(src, ["=1+1 is math", "I love it"])
        json2csv_preprocess(src, out, ["id", "text"], remove_duplicates=False)
        from nltk.tokenize import LineTokenizer, WhitespaceTokenizer

        tweets = parse_tweets_set(
            out,
            label="pos",
            word_tokenizer=WhitespaceTokenizer(),
            sent_tokenizer=LineTokenizer(),
        )
        assert [label for _, label in tweets] == ["pos", "pos"]
        assert tweets[0][0][0] == "'=1+1"  # the defused cell, tokenised as text


class TestOutputMarkdown:
    def test_a_line_break_or_control_in_a_value_stays_on_its_line(
        self, restricted_sandbox
    ):
        report = os.path.join(restricted_sandbox, "report.md")
        output_markdown(
            report,
            Dataset="tweets\n  - **Injected:** yes",
            Accuracy=0.75,
            Classifier="NB" + ESC + "[2J",
            Metrics={"F-measure [neg]\nfake": 0.7, "Precision": 0.8},
            Notes=["one", "two\nthree"],
        )
        with open(report, encoding="utf-8") as fh:
            lines = fh.read().split("\n")
        assert ESC not in "".join(lines)
        assert sum(1 for l in lines if l.startswith("  - **")) == 5  # one per keyword
        assert not any(l.startswith("  - **Injected") for l in lines)
        assert (
            sum(1 for l in lines if l.startswith("    - ")) == 4
        )  # two metric entries, two notes
        assert any("Accuracy:** 0.75" in l for l in lines)

    def test_a_report_appends_readably(self, restricted_sandbox):
        report = os.path.join(restricted_sandbox, "report.md")
        output_markdown(report, Dataset="movie_reviews", Accuracy=0.8)
        output_markdown(report, Dataset="subjectivity", Accuracy=0.9)
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        assert (
            text.count("*** ") == 2
            and "**Dataset:** movie_reviews" in text
            and "**Dataset:** subjectivity" in text
        )


class TestDemosOnRealData:
    """The module's own demos run on the real corpora, as the docs show."""

    def _needs(self, *resources):
        import nltk.data

        for name in resources:
            try:
                nltk.data.find(name)
            except LookupError:
                pytest.skip(f"{name} is not installed")

    def test_vader_scores_a_sentence(self, capsys):
        from nltk.sentiment.util import demo_vader_instance

        self._needs("sentiment/vader_lexicon.zip")
        demo_vader_instance("VADER is smart, handsome, and funny.")
        out = capsys.readouterr().out
        assert "compound" in out and "pos" in out

    def test_liu_hu_lexicon_classifies(self, capsys):
        from nltk.sentiment.util import demo_liu_hu_lexicon

        self._needs("corpora/opinion_lexicon")
        demo_liu_hu_lexicon("It is a wonderful, lovely day.")
        assert capsys.readouterr().out.strip().endswith("Positive")

    def test_naive_bayes_on_tweets_and_the_report(self, restricted_sandbox, capsys):
        from nltk.classify import NaiveBayesClassifier
        from nltk.sentiment.util import demo_tweets

        self._needs("corpora/twitter_samples", "corpora/stopwords")
        report = os.path.join(restricted_sandbox, "report.md")
        demo_tweets(NaiveBayesClassifier.train, n_instances=400, output=report)
        out = capsys.readouterr().out
        assert "Accuracy" in out
        with open(report, encoding="utf-8") as fh:
            text = fh.read()
        assert "**Dataset:** labeled_tweets" in text and "**Accuracy:**" in text

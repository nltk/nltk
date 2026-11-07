# Natural Language Toolkit: expanded attack harness for the twitter package
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""The twitter package's sinks for untrusted tweet data, driven on real files
with the widest matrix and read back the way a spreadsheet, a terminal or nltk
itself would read them: json2csv and json2csv_entities (CWE-1236 formula
cells, CWE-150 terminal sequences, CWE-1007 bidi spoofing, CWE-674 and CWE-400
hostile JSON), the entity walk behind json2csv_entities, TweetViewer and the
Streamer and Query prints (the terminal sink), TweetWriter (the line-delimited
JSON file sink) and the credentials reader. The live-control oracle is the one
test_termsec_attack_matrix.py derives independently of nltk.termsec, and its
ATTACKS and LEGIT tables are driven through the real CSV writer here. Nothing
is mocked and no guard is patched; the classes that need twython skip only
when twython is genuinely absent."""

import csv
import gzip
import io
import json
import os
import sys

import pytest

from nltk.jsontags import JSON_MAX_DEPTH, safe_json_loads
from nltk.test.unit import timing
from nltk.test.unit.test_termsec_attack_matrix import (
    ATTACKS,
    LEGIT,
    _dangerous_cp,
    _has_live_control,
)
from nltk.twitter.common import _get_entity_recursive, json2csv, json2csv_entities

ESC = chr(0x1B)
BEL = chr(0x07)
CR = chr(0x0D)
NUL = chr(0x00)
RLO = chr(0x202E)
LRI = chr(0x2066)
PDI = chr(0x2069)
LSEP = chr(0x2028)
NBSP = chr(0xA0)
IDEOSP = chr(0x3000)
EMSP = chr(0x2003)
SURR = chr(0xD800)
# What a spreadsheet runs as a formula when it leads a cell: the classic four,
# the two that earned the Ruby sanitiser CVE-2022-28481, and their fullwidth
# forms, which some locales normalise to ASCII on import.
FORMULA_LEADS = (
    "=",
    "+",
    "-",
    "@",
    "%",
    "|",
    chr(0xFF1D),
    chr(0xFF0B),
    chr(0xFF0D),
    chr(0xFF20),
)
POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="symlinks are POSIX")

FORMULAS = [
    "=1+1",
    "=cmd|' /C calc'!A0",
    '=cmd|"/c calc"!A1',
    "=2+5+cmd|' /C calc'!A0",
    '=HYPERLINK("http://evil","x")',
    '=WEBSERVICE("http://evil")',
    '=IMPORTXML("http://evil","//a")',
    "+cmd|' /C calc'!A0",
    "-cmd|' /C calc'!A0",
    "-2+3+cmd|' /C calc'!A0",
    "@SUM(1+1)*cmd|' /C calc'!A0",
    "%x",
    "|x",
    chr(0xFF1D) + "1+1",
    chr(0xFF0B) + "cmd",
    chr(0xFF0D) + "cmd",
    chr(0xFF20) + "SUM(1)",
    " =leading_space",
    "\t=leading_tab",
    NBSP + "=no_break_space",
    IDEOSP + "=ideographic_space",
    "  \t " + EMSP + "=mixed_spaces",
    "-inf",
    "-nan",
    "+1_0",
    "-" + "9" * 10_001,
    "@" + "A" * 5000,
]
NUMBERS = ["-42", "+3.14", "-0.0", "1e5", "-1e5", "+1.2E10", "-1,234.56", "0", "-5"]
BENIGN = [
    "RT @user: normal tweet #nlp",
    "#hashtag first",
    "http://t.co/x",
    "'=already defused",
    "a\tb\nc",
    'it\'s "quoted", with commas',
    "",
    "caf" + chr(0xE9) + " " + chr(0x2615),
    "\\x1b[31m written out as text",
    "a" + LRI + "b" + PDI + "c",
]


def _tweets_fp(tweets):
    return io.StringIO("".join(json.dumps(t) + "\n" for t in tweets))


def _lines_fp(lines):
    return io.StringIO("".join(line + "\n" for line in lines))


def _raw(path, gz=False):
    opener = gzip.open if gz else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        return fh.read()


def _rows(path, gz=False):
    opener = gzip.open if gz else open
    with opener(path, "rt", encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def _isnum(cell):
    # a spreadsheet's idea of a number: a sign is fine, inf/nan and digit
    # underscores are not, and accounting grouping (-1,234.56) is
    lowered = cell.lower()
    if "inf" in lowered or "nan" in lowered or "_" in cell:
        return False
    try:
        float(cell)
        return True
    except ValueError:
        body = cell[1:] if cell[:1] in "+-" else cell
        return bool(body) and all(ch.isdigit() or ch in ".," for ch in body)


def _assert_sheet_safe(rows):
    for row in rows:
        for cell in row:
            assert cell.lstrip()[:1] not in FORMULA_LEADS or _isnum(cell), ascii(cell)


def _assert_no_live_control(raw):
    # CR LF record terminators are the writer's own; anything else the
    # independent detector flags survived the sanitiser
    assert not _has_live_control(raw.replace(CR + "\n", "\n")), ascii(raw)[:300]


# The embeddings, isolates and direction marks real Arabic and Hebrew text
# carries: the sanitiser passes them when balanced and the full oracle flags
# them all, so the checks over real tweets use the unconditional set only.
_CONDITIONAL_BIDI = frozenset(
    {0x202A, 0x202B, 0x202C, 0x2066, 0x2067, 0x2068, 0x2069, 0x200E, 0x200F, 0x061C}
)


def _has_unconditional_control(text):
    return any(
        _dangerous_cp(cp) and cp not in _CONDITIONAL_BIDI for cp in map(ord, text)
    )


def _assert_no_unconditional_control(raw):
    assert not _has_unconditional_control(raw.replace(CR + "\n", "\n")), ascii(raw)[
        :300
    ]


def _second_line_cell(path):
    # the csv reader refuses a cell over 131072 bytes, so a megabyte cell is
    # read straight off the second record, which the writer leaves unquoted
    lines = _raw(path).split(CR + "\n")
    assert lines[1].startswith("1,") and lines[2] == "", ascii(lines[1][:40])
    return lines[1][2:]


def _visible_in_order(before, after):
    """Every character of *before* the oracle does not flag appears in *after*
    in the same order: escaping removed nothing visible."""
    if _has_unconditional_control(after):
        return False
    position = 0
    for ch in before:
        if _dangerous_cp(ord(ch)):
            continue
        position = after.find(ch, position)
        if position < 0:
            return False
        position += 1
    return True


class TestFormulaLeadDefused:
    @pytest.mark.parametrize("payload", FORMULAS, ids=lambda p: ascii(p)[:18])
    def test_a_formula_lead_in_the_text_becomes_text(self, tmp_path, payload):
        out = str(tmp_path / "out.csv")
        json2csv(_tweets_fp([{"id": 1, "text": payload}]), out, ["id", "text"])
        rows = _rows(out)
        assert rows[0] == ["id", "text"] and len(rows) == 2, rows
        # the apostrophe is the only thing prepended; the payload is intact
        assert rows[1] == ["1", "'" + payload], ascii(rows[1])
        _assert_sheet_safe(rows)

    @pytest.mark.parametrize("payload", FORMULAS[:12], ids=lambda p: ascii(p)[:18])
    def test_a_formula_lead_in_a_nested_user_field_becomes_text(
        self, tmp_path, payload
    ):
        out = str(tmp_path / "out.csv")
        tweet = {"id": "1", "text": "t", "user": {"screen_name": payload, "id": 2}}
        json2csv(_tweets_fp([tweet]), out, ["id", "user.screen_name", "user.id"])
        assert _rows(out)[1] == ["1", "'" + payload, "2"]

    def test_a_formula_led_id_string_is_defused_but_a_numeric_id_is_not(self, tmp_path):
        out = str(tmp_path / "out.csv")
        tweets = [{"id": "=1", "text": "a"}, {"id": -7, "text": "b"}]
        json2csv(_tweets_fp(tweets), out, ["id", "text"])
        assert [r[0] for r in _rows(out)[1:]] == ["'=1", "-7"]

    def test_hostile_field_names_are_defused_in_the_header(self, tmp_path):
        out = str(tmp_path / "out.csv")
        hostile = ESC + "[31mid"
        tweet = {"=cmd": "x", hostile: 1, "=user": {"x": 2}}
        json2csv(_tweets_fp([tweet]), out, ["=cmd", hostile, "=user.x"])
        rows = _rows(out)
        assert rows[0] == ["'=cmd", "\\x1b[31mid", "'=user.x"], ascii(rows[0])
        assert rows[1] == ["x", "1", "2"]
        _assert_sheet_safe(rows)
        _assert_no_live_control(_raw(out))

    def test_hostile_main_field_names_are_defused_in_the_entities_header(
        self, tmp_path
    ):
        out = str(tmp_path / "ent.csv")
        tweet = {"=id": 1, "entities": {"hashtags": [{"text": "x"}]}}
        json2csv_entities(_tweets_fp([tweet]), out, ["=id"], "hashtags", ["text"])
        rows = _rows(out)
        assert rows == [["'=id", "hashtags.text"], ["1", "x"]]


class TestGenuineValuesKept:
    @pytest.mark.parametrize("number", NUMBERS)
    def test_a_genuine_number_keeps_its_sign(self, tmp_path, number):
        out = str(tmp_path / "out.csv")
        json2csv(_tweets_fp([{"id": 1, "text": number}]), out, ["id", "text"])
        assert _rows(out)[1] == ["1", number]

    @pytest.mark.parametrize("text", BENIGN, ids=lambda p: ascii(p)[:18])
    def test_benign_text_is_unchanged(self, tmp_path, text):
        out = str(tmp_path / "out.csv")
        json2csv(_tweets_fp([{"id": 1, "text": text}]), out, ["id", "text"])
        assert _rows(out)[1] == ["1", text], ascii(_rows(out)[1])

    @pytest.mark.parametrize("name", sorted(LEGIT))
    def test_every_legitimate_script_is_unchanged(self, tmp_path, name):
        out = str(tmp_path / "out.csv")
        text = LEGIT[name]
        tweet = {"id": 1, "text": text, "user": {"name": text}}
        json2csv(_tweets_fp([tweet]), out, ["id", "text", "user.name"])
        assert _rows(out)[1] == ["1", text, text], ascii(_rows(out)[1])

    def test_exact_primitives_keep_their_rendering(self, tmp_path):
        out = str(tmp_path / "out.csv")
        tweet = {"i": -5, "f": -2.5, "b": False, "n": None, "t": True, "z": 0}
        json2csv(_tweets_fp([tweet]), out, ["i", "f", "b", "n", "t", "z"])
        assert _rows(out)[1] == ["-5", "-2.5", "False", "", "True", "0"]

    def test_a_large_integer_id_is_written_in_full(self, tmp_path):
        out = str(tmp_path / "out.csv")
        digits = "9" * 4000
        json2csv(_lines_fp(['{"id": ' + digits + "}"]), out, ["id"])
        assert _rows(out)[1] == [digits]


class TestTerminalAndBidiNeutralised:
    def test_every_termsec_attack_is_escaped_in_text_and_user_cells(self, tmp_path):
        out = str(tmp_path / "out.csv")
        names = sorted(ATTACKS)
        tweets = [
            {"id": i, "text": ATTACKS[n], "user": {"name": ATTACKS[n]}}
            for i, n in enumerate(names)
        ]
        json2csv(_tweets_fp(tweets), out, ["id", "text", "user.name"])
        raw = _raw(out)
        _assert_no_live_control(raw)
        rows = _rows(out)
        # one record per attack: no payload forged or swallowed a row
        assert [r[0] for r in rows] == ["id"] + [str(i) for i in range(len(names))]
        assert all(len(r) == 3 for r in rows)
        for row, name in zip(rows[1:], names):
            assert row[1] == row[2] and row[1], name
            assert not _has_live_control(row[1]), name
        _assert_sheet_safe(rows)

    @pytest.mark.parametrize(
        "text, expected",
        [
            (ESC + "[31mred" + ESC + "[0m", "\\x1b[31mred\\x1b[0m"),
            (chr(0x9B) + "31m", "\\x9b31m"),
            (BEL + "bel", "\\x07bel"),
            (NUL + "nul", "\\x00nul"),
            (chr(0x7F) + "del", "\\x7fdel"),
            ("a" + CR + "b", "a\\x0db"),
            (RLO + "rlo", "\\u202erlo"),
            (LRI + "unbalanced", "\\u2066unbalanced"),
            ("x" + LSEP + "y", "x\\u2028y"),
            ("a" + SURR + "b", "a\\ud800b"),
        ],
        ids=lambda p: ascii(p)[:14],
    )
    def test_the_escape_is_the_visible_form(self, tmp_path, text, expected):
        out = str(tmp_path / "out.csv")
        json2csv(_tweets_fp([{"id": 1, "text": text}]), out, ["id", "text"])
        assert _rows(out)[1] == ["1", expected]

    def test_a_lone_surrogate_is_written_visibly_even_to_ascii(self, tmp_path):
        out = str(tmp_path / "out.csv")
        tweets = [{"id": 1, "text": "a" + SURR + "b"}]
        json2csv(_tweets_fp(tweets), out, ["id", "text"], encoding="ascii")
        with open(out, "rb") as fh:
            data = fh.read()
        assert data.decode("ascii").splitlines()[1] == "1,a\\ud800b"

    def test_a_bare_cr_or_nul_cannot_forge_or_split_a_record(self, tmp_path):
        out = str(tmp_path / "out.csv")
        texts = [
            "line1" + CR + "SPOOF",
            "injected" + CR + "\n9,row",
            "soft\nbreak",
            "n" + NUL + "ul",
            'q"uote,comma',
            CR + "\n" + CR + "\n",
        ]
        tweets = [{"id": i, "text": t} for i, t in enumerate(texts)]
        json2csv(_tweets_fp(tweets), out, ["id", "text"])
        raw = _raw(out)
        assert NUL not in raw
        # the only CR LF pairs are the record terminators
        assert raw.count(CR + "\n") == len(texts) + 1
        assert raw.count(CR) == len(texts) + 1
        rows = _rows(out)
        assert [r[0] for r in rows] == ["id"] + [str(i) for i in range(len(texts))]
        assert all(len(r) == 2 for r in rows)
        assert rows[3][1] == "soft\nbreak" and rows[5][1] == 'q"uote,comma'
        assert "SPOOF" in rows[1][1] and "9,row" in rows[2][1]

    def test_an_already_escaped_literal_is_not_escaped_twice(self, tmp_path):
        out = str(tmp_path / "out.csv")
        text = "\\x1b[31m\\u202e literal backslashes"
        json2csv(_tweets_fp([{"id": 1, "text": text}]), out, ["id", "text"])
        assert _rows(out)[1][1] == text


def _hostile_tweet():
    return {
        "id": 7,
        "text": "=main" + ESC + "[2J",
        "user": {
            "id": 9,
            "screen_name": "@evil",
            "name": '=WEBSERVICE("http://evil")',
            "entities": {
                "url": {"urls": [{"url": "=u", "expanded_url": "+e"}]},
                "description": {"urls": []},
            },
        },
        "entities": {
            "hashtags": [{"text": "=danger"}, {"text": ESC + "]0;pwned" + BEL}],
            "user_mentions": [
                {"id": 1, "screen_name": "=cmd"},
                {"id": "+2", "screen_name": RLO + "x"},
            ],
            "media": [{"media_url": '=HYPERLINK("http://evil","x")', "url": "@m"}],
            "urls": [{"url": "@u", "expanded_url": "http://x" + LSEP + "y"}],
        },
        "place": {
            "id": "p1",
            "name": "-cmd",
            "country": RLO + "UK",
            "bounding_box": {"type": "Polygon", "coordinates": ["=c", -1.5, 2]},
        },
        "retweeted_status": {
            "id": 8,
            "text": "+rt" + BEL,
            "favorite_count": -3,
            "user": {"id": 3, "name": "@rt"},
        },
    }


class TestEntitiesSanitised:
    def _run(self, tmp_path, main_fields, entity_type, entity_fields, tweet=None):
        out = str(tmp_path / "ent.csv")
        tweets = [_hostile_tweet() if tweet is None else tweet]
        json2csv_entities(
            _tweets_fp(tweets), out, main_fields, entity_type, entity_fields
        )
        rows = _rows(out)
        _assert_sheet_safe(rows)
        _assert_no_live_control(_raw(out))
        return rows

    def test_hashtags(self, tmp_path):
        rows = self._run(tmp_path, ["id", "text"], "hashtags", ["text"])
        assert rows == [
            ["id", "text", "hashtags.text"],
            ["7", "'=main\\x1b[2J", "'=danger"],
            ["7", "'=main\\x1b[2J", "\\x1b]0;pwned\\x07"],
        ]

    def test_user_mentions(self, tmp_path):
        rows = self._run(tmp_path, ["id"], "user_mentions", ["id", "screen_name"])
        # "+2" is a genuine signed number, so it keeps its sign unprefixed
        assert rows[1:] == [["7", "1", "'=cmd"], ["7", "+2", "\\u202ex"]]

    def test_media(self, tmp_path):
        rows = self._run(tmp_path, ["id"], "media", ["media_url", "url"])
        assert rows[1:] == [["7", '\'=HYPERLINK("http://evil","x")', "'@m"]]

    def test_urls(self, tmp_path):
        rows = self._run(tmp_path, ["id"], "urls", ["url", "expanded_url"])
        assert rows[1:] == [["7", "'@u", "http://x\\u2028y"]]

    def test_place(self, tmp_path):
        rows = self._run(tmp_path, ["id", "text"], "place", ["name", "country"])
        assert rows[1:] == [["7", "'=main\\x1b[2J", "'-cmd", "\\u202eUK"]]

    def test_place_bounding_box_list_cells(self, tmp_path):
        rows = self._run(
            tmp_path, ["id", "name"], "place.bounding_box", ["coordinates"]
        )
        assert rows == [
            ["place.id", "place.name", "bounding_box.coordinates"],
            ["p1", "'-cmd", "'=c", "-1.5", "2"],
        ]

    def test_retweeted_status_with_composed_fields(self, tmp_path):
        rows = self._run(
            tmp_path,
            ["id"],
            "retweeted_status",
            ["text", "favorite_count", "user.name", "user.id"],
        )
        assert rows[1:] == [["7", "'+rt\\x07", "-3", "'@rt", "3"]]

    def test_user_urls_through_the_user_wrapper(self, tmp_path):
        tweet = _hostile_tweet()
        tweet["user"]["entities"] = {"urls": tweet["user"]["entities"]["url"]["urls"]}
        rows = self._run(
            tmp_path, ["id", "screen_name"], "user.urls", ["url", "expanded_url"], tweet
        )
        assert rows[1:] == [["9", "'@evil", "'=u", "'+e"]]

    def test_an_absent_entity_writes_no_row(self, tmp_path):
        tweet = {"id": 1, "text": "t", "entities": {"hashtags": []}}
        rows = self._run(tmp_path, ["id"], "media", ["media_url"], tweet)
        assert rows == [["id", "media.media_url"]]

    def test_an_entity_under_extended_entities_is_found(self, tmp_path):
        tweet = {"id": 1, "extended_entities": {"media": [{"media_url": "=x"}]}}
        rows = self._run(tmp_path, ["id"], "media", ["media_url"], tweet)
        assert rows[1:] == [["1", "'=x"]]

    def test_an_entity_under_a_non_wrapper_key_is_not_reached(self, tmp_path):
        tweet = {"id": 1, "other": {"hashtags": [{"text": "=x"}]}}
        rows = self._run(tmp_path, ["id"], "hashtags", ["text"], tweet)
        assert rows == [["id", "hashtags.text"]]


class TestHostileJsonRefused:
    def test_nesting_past_the_json_bound_is_refused_fast(self, tmp_path):
        out = str(tmp_path / "out.csv")
        deep = "[" * (JSON_MAX_DEPTH + 500) + "]" * (JSON_MAX_DEPTH + 500)
        line = '{"id": 1, "text": ' + deep + "}"
        with timing.budget(5, "depth refusal", cpu_bound=True):
            with pytest.raises(ValueError, match="nesting depth"):
                json2csv(_lines_fp([line]), out, ["id", "text"])
        with timing.budget(5, "entities depth refusal", cpu_bound=True):
            with pytest.raises(ValueError, match="nesting depth"):
                json2csv_entities(_lines_fp([line]), out, ["id"], "hashtags", ["text"])

    @pytest.mark.parametrize(
        "line",
        ['{"id": NaN}', '{"id": Infinity}', '{"id": -Infinity}', '{"id": 1e999}'],
    )
    def test_a_non_finite_number_is_refused(self, tmp_path, line):
        out = str(tmp_path / "out.csv")
        with pytest.raises(ValueError, match="non-finite"):
            json2csv(_lines_fp([line]), out, ["id"])

    def test_an_integer_past_the_digit_limit_is_refused(self, tmp_path):
        out = str(tmp_path / "out.csv")
        # past the interpreter's int-to-str limit; if that limit is disabled,
        # past the termsec render backstop (about 100,000 digits) instead
        limit = sys.get_int_max_str_digits()
        digits = limit + 1 if limit else 110_000
        line = '{"id": ' + "9" * digits + "}"
        with pytest.raises(ValueError):
            json2csv(_lines_fp([line]), out, ["id"])

    @pytest.mark.parametrize("line", ["", "not json", "{", "[1, 2]"])
    def test_a_line_that_is_not_a_tweet_object_is_an_error(self, tmp_path, line):
        out = str(tmp_path / "out.csv")
        with pytest.raises((ValueError, RuntimeError, KeyError)):
            json2csv(_lines_fp(['{"id": 1}', line]), out, ["id"])

    def test_an_empty_file_writes_only_the_header(self, tmp_path):
        out = str(tmp_path / "out.csv")
        json2csv(io.StringIO(""), out, ["id", "text"])
        assert _rows(out) == [["id", "text"]]
        ent = str(tmp_path / "ent.csv")
        json2csv_entities(io.StringIO(""), ent, ["id"], "hashtags", ["text"])
        assert _rows(ent) == [["id", "hashtags.text"]]

    def test_a_missing_field_is_a_key_error(self, tmp_path):
        out = str(tmp_path / "out.csv")
        with pytest.raises(KeyError):
            json2csv(_tweets_fp([{"id": 1}]), out, ["id", "text"])

    @pytest.mark.parametrize("user", ["str", [1], None, 5])
    def test_a_composed_field_over_a_non_object_is_a_runtime_error(
        self, tmp_path, user
    ):
        out = str(tmp_path / "out.csv")
        with pytest.raises(RuntimeError, match="Cannot find field"):
            json2csv(_tweets_fp([{"id": 1, "user": user}]), out, ["id", "user.id"])

    def test_a_benign_megabyte_cell_passes_in_full(self, tmp_path):
        out = str(tmp_path / "out.csv")
        text = "ab " * 400_000
        json2csv(_tweets_fp([{"id": 1, "text": text}]), out, ["id", "text"])
        assert _second_line_cell(out) == text


def _reference_recursive_walk(json, entity):
    """The walk as it was written before the explicit stack: the oracle the
    explicit-stack walk must match, and the version a deep nest breaks."""
    if not json:
        return None
    elif isinstance(json, dict):
        for key, value in json.items():
            if key == entity:
                return value
            if key == "entities" or key == "extended_entities":
                candidate = _reference_recursive_walk(value, entity)
                if candidate is not None:
                    return candidate
        return None
    elif isinstance(json, list):
        for item in json:
            candidate = _reference_recursive_walk(item, entity)
            if candidate is not None:
                return candidate
        return None
    else:
        return None


def _nest(leaf, depth, wrapper="entities"):
    node = leaf
    for _ in range(depth):
        node = {wrapper: node}
    return node


def _nest_lists(leaf, depth):
    node = leaf
    for _ in range(depth):
        node = [node]
    return {"entities": node}


A, B, M, N = [{"text": "a"}], [{"text": "b"}], [{"m": 1}], [{"m": 2}]
H = "hashtags"
# (json, entity, expected): the search order the recursive walk defined
WALK_CASES = {
    "wrapper-before-later-key": ({"entities": {H: A}, H: B}, H, A),
    "direct-key-before-wrapper": ({H: B, "entities": {H: A}}, H, B),
    "none-hit-reads-as-absent": ({"entities": {H: None}, H: B}, H, B),
    "top-level-none-ends-search": ({H: None, "entities": {H: A}}, H, None),
    "empty-list-is-a-hit": ({"entities": {H: []}, H: B}, H, []),
    "zero-is-a-hit": ({"entities": {H: 0}, H: B}, H, 0),
    "list-wrapper-items-in-order": ({"entities": [{"x": 1}, {H: A}], H: B}, H, A),
    "non-wrapper-key-not-descended": ({"other": {H: A}}, H, None),
    "top-level-list": ([{"entities": {H: A}}, {H: B}], H, A),
    "extended-before-plain": (
        {"extended_entities": {"media": M}, "entities": {"media": N}},
        "media",
        M,
    ),
    "plain-before-extended": (
        {"entities": {"media": N}, "extended_entities": {"media": M}},
        "media",
        N,
    ),
    "string-wrapper-skipped": ({"entities": "str", H: B}, H, B),
    "empty-wrapper-skipped": ({"entities": {}, H: B}, H, B),
    "double-wrapper": ({"entities": {"entities": {H: A}}, H: B}, H, A),
    "double-wrapper-none": ({"entities": {"entities": {H: None}}, H: B}, H, B),
    "keys-after-hit-ignored": ({H: A, "entities": {H: B}}, H, A),
    "empty-dict": ({}, H, None),
    "empty-list": ([], H, None),
    "none": (None, H, None),
    "scalar": ("s", H, None),
    "deep-but-legal": (_nest({H: A}, 500), H, A),
    "deep-lists-legal": (_nest_lists({H: A}, 500), H, A),
}


class TestEntityWalkWithoutRecursion:
    @pytest.mark.parametrize("name", sorted(WALK_CASES))
    def test_the_walk_matches_the_recursive_oracle(self, name):
        json_obj, entity, expected = WALK_CASES[name]
        got = _get_entity_recursive(json_obj, entity)
        assert got == expected and (got is None) == (expected is None), name
        oracle = _reference_recursive_walk(json_obj, entity)
        assert got == oracle and (got is None) == (oracle is None), name

    def test_a_nest_past_the_recursion_limit_breaks_the_oracle_not_the_walk(self):
        depth = sys.getrecursionlimit() + 200
        for nested in (
            _nest({"hashtags": A}, depth),
            _nest_lists({"hashtags": A}, depth),
        ):
            with pytest.raises(RecursionError):
                _reference_recursive_walk(nested, "hashtags")
            with timing.budget(5, "entity walk", cpu_bound=True):
                assert _get_entity_recursive(nested, "hashtags") == A
            assert _get_entity_recursive(nested, "media") is None

    @pytest.mark.parametrize("shape", ["wrappers", "lists"])
    def test_a_tweet_nested_to_the_json_bound_never_raises_recursion_error(
        self, tmp_path, shape
    ):
        out = str(tmp_path / "ent.csv")
        depth = JSON_MAX_DEPTH - 10
        leaf = '{"hashtags": [{"text": "=deep"}]}'
        if shape == "wrappers":
            nest = '{"entities": ' * depth + leaf + "}" * depth
        else:
            nest = "[" * depth + leaf + "]" * depth
        line = '{"id": 1, "entities": ' + nest + "}"
        # In the JSON bound but past the recursion limit: a decoder counting C
        # recursion against it (CPython 3.10, 3.11) gives jsontags' ValueError,
        # any other parses it and the walk must find the leaf; neither recurses.
        try:
            safe_json_loads(line, context="test")
        except ValueError as exc:
            assert "too deep to parse safely" in str(exc)
            with timing.budget(10, f"deep {shape} refusal", cpu_bound=True):
                with pytest.raises(ValueError, match="too deep to parse safely"):
                    json2csv_entities(
                        _lines_fp([line]), out, ["id"], "hashtags", ["text"]
                    )
            return
        with timing.budget(10, f"deep {shape}", cpu_bound=True):
            json2csv_entities(_lines_fp([line]), out, ["id"], "hashtags", ["text"])
        assert _rows(out) == [["id", "hashtags.text"], ["1", "'=deep"]]

    def test_a_nest_past_the_json_bound_never_reaches_the_walk(self, tmp_path):
        out = str(tmp_path / "ent.csv")
        depth = JSON_MAX_DEPTH + 1
        leaf = '{"hashtags": [{"text": "x"}]}'
        line = (
            '{"id": 1, "entities": '
            + '{"entities": ' * depth
            + leaf
            + "}" * depth
            + "}"
        )
        with pytest.raises(ValueError, match="nesting depth"):
            json2csv_entities(_lines_fp([line]), out, ["id"], "hashtags", ["text"])


class TestEncodingsAndCompression:
    def test_gzip_output_is_sanitised_identically(self, tmp_path):
        plain, gz = str(tmp_path / "o.csv"), str(tmp_path / "o.csv.gz")
        tweets = [{"id": 1, "text": "=x" + ESC + "[31m" + RLO}]
        json2csv(_tweets_fp(tweets), plain, ["id", "text"])
        json2csv(_tweets_fp(tweets), gz, ["id", "text"], gzip_compress=True)
        assert (
            _rows(gz, gz=True)
            == _rows(plain)
            == [["id", "text"], ["1", "'=x\\x1b[31m\\u202e"]]
        )
        _assert_no_live_control(_raw(gz, gz=True))

    def test_gzip_input_is_read_like_plain_input(self, tmp_path):
        src = tmp_path / "tweets.json.gz"
        with gzip.open(str(src), "wt", encoding="utf-8") as fh:
            fh.write(json.dumps({"id": 1, "text": "@m"}) + "\n")
        out = str(tmp_path / "o.csv")
        with gzip.open(str(src), "rt", encoding="utf-8") as fp:
            json2csv(fp, out, ["id", "text"])
        assert _rows(out)[1] == ["1", "'@m"]

    def test_a_latin1_file_round_trips_when_opened_as_such(self, tmp_path):
        src = tmp_path / "latin.json"
        text = "caf" + chr(0xE9)
        src.write_bytes(
            (json.dumps({"id": 1, "text": text}, ensure_ascii=False) + "\n").encode(
                "latin-1"
            )
        )
        out = str(tmp_path / "o.csv")
        with open(str(src), encoding="latin-1") as fp:
            json2csv(fp, out, ["id", "text"])
        assert _rows(out)[1] == ["1", text]

    def test_an_invalid_utf8_file_is_an_error_not_silently_mangled(self, tmp_path):
        src = tmp_path / "bad.json"
        src.write_bytes(b'{"id": 1, "text": "caf\xe9"}\n')
        out = str(tmp_path / "o.csv")
        with open(str(src), encoding="utf-8") as fp:
            with pytest.raises(UnicodeDecodeError):
                json2csv(fp, out, ["id", "text"])
        with open(str(src), "rb") as fp:
            with pytest.raises(ValueError):
                json2csv(fp, out, ["id", "text"])

    def test_bytes_lines_are_accepted(self, tmp_path):
        src = tmp_path / "ok.json"
        src.write_bytes((json.dumps({"id": 1, "text": "=b"}) + "\n").encode("utf-8"))
        out = str(tmp_path / "o.csv")
        with open(str(src), "rb") as fp:
            json2csv(fp, out, ["id", "text"])
        assert _rows(out)[1] == ["1", "'=b"]

    def test_output_encoding_errors_follow_the_caller(self, tmp_path):
        out = str(tmp_path / "o.csv")
        tweets = [{"id": 1, "text": "caf" + chr(0xE9)}]
        json2csv(_tweets_fp(tweets), out, ["id", "text"], encoding="ascii")
        assert _rows(out)[1] == ["1", "caf?"]
        with pytest.raises(UnicodeEncodeError):
            json2csv(
                _tweets_fp(tweets),
                out,
                ["id", "text"],
                encoding="ascii",
                errors="strict",
            )

    @POSIX_ONLY
    def test_a_symlinked_input_fixture_is_read_through_the_link(self, tmp_path):
        real = tmp_path / "real.json"
        real.write_text(json.dumps({"id": 1, "text": "=s"}) + "\n", encoding="utf-8")
        link = tmp_path / "link.json"
        link.symlink_to(real)
        out = str(tmp_path / "o.csv")
        with open(str(link), encoding="utf-8") as fp:
            json2csv(fp, out, ["id", "text"])
        assert _rows(out)[1] == ["1", "'=s"]


@pytest.fixture
def clients():
    pytest.importorskip(
        "twython",
        reason="twython is not installed, so nltk.twitter.twitterclient cannot import",
    )
    from nltk.twitter import twitterclient

    return twitterclient


CREATED = "Thu Apr 30 21:34:07 +0000 2015"


class TestTerminalSink:
    def test_viewer_escapes_controls_and_keeps_line_structure(self, clients, capsys):
        viewer = clients.TweetViewer(limit=5)
        viewer.handle(
            {"text": ESC + "[31mred" + ESC + "[0m" + BEL, "created_at": CREATED}
        )
        viewer.handle({"text": "line1\nline2\t" + RLO + "x", "created_at": CREATED})
        viewer.on_finish()
        out = capsys.readouterr().out
        assert not _has_live_control(out), ascii(out)
        assert out.splitlines() == [
            "\\x1b[31mred\\x1b[0m\\x07",
            "line1",
            "line2\t\\u202ex",
            "Written 0 Tweets",
        ]

    def test_viewer_neutralises_every_termsec_attack(self, clients, capsys):
        viewer = clients.TweetViewer(limit=len(ATTACKS))
        names = sorted(ATTACKS)
        for name in names:
            viewer.handle({"text": ATTACKS[name], "created_at": CREATED})
        out = capsys.readouterr().out
        assert not _has_live_control(out), ascii(out)[:300]
        assert len(out.splitlines()) == len(names)

    def test_viewer_prints_legitimate_scripts_unchanged(self, clients, capsys):
        viewer = clients.TweetViewer(limit=len(LEGIT))
        for name in sorted(LEGIT):
            viewer.handle({"text": LEGIT[name], "created_at": CREATED})
        out = capsys.readouterr().out
        assert out == "".join(LEGIT[name] + "\n" for name in sorted(LEGIT))

    def test_date_limit_message_and_hostile_created_at(self, clients, capsys):
        viewer = clients.TweetViewer(limit=5, upper_date_limit=(2015, 4, 1, 0, 0))
        viewer.check_date_limit({"created_at": CREATED}, verbose=True)
        assert viewer.do_stop
        out = capsys.readouterr().out
        assert out.startswith("Date limit") and "earlier" in out
        with pytest.raises(ValueError) as exc:
            viewer.handle({"text": "t", "created_at": ESC + "[31m bogus"})
        assert not _has_live_control(str(exc.value))

    def test_streamer_routes_tweets_and_errors_through_the_sanitiser(
        self, clients, capsys
    ):
        streamer = clients.Streamer("key", "secret", "token", "token_secret")
        with pytest.raises(ValueError, match="No data handler"):
            streamer.on_success({"text": "x"})
        streamer.register(clients.TweetViewer(limit=1))
        streamer.on_success({"delete": {"status": {"id": 1}}})  # no text: ignored
        streamer.on_success(
            {"text": ESC + "]0;pwned" + BEL + "hi", "created_at": CREATED}
        )
        assert streamer.handler.counter == 1 and streamer.do_continue is False
        streamer.on_success({"text": "after the limit", "created_at": CREATED})
        streamer.on_error(ESC + "[2J420", {"ignored": True})
        out = capsys.readouterr().out
        assert not _has_live_control(out), ascii(out)
        assert out.splitlines() == [
            "\\x1b]0;pwned\\x07hi",
            "Written 1 Tweets",
            "\\x1b[2J420",
        ]

    def test_query_verbose_count_is_sanitised_and_lazy(self, clients, capsys):
        query = clients.Query("key", "secret", "token", "token_secret")
        ids = io.StringIO(ESC + "[31m123\n456\n")
        chained = query.expand_tweetids(ids, verbose=True)
        out = capsys.readouterr().out
        assert out.startswith("Counted 2 Tweet IDs") and not _has_live_control(out)
        assert hasattr(chained, "__next__")  # nothing fetched until iterated


class TestFileSink:
    def _write(self, clients, subdir, tweets, **kwargs):
        writer = clients.TweetWriter(limit=len(tweets), subdir=subdir, **kwargs)
        for tweet in tweets:
            writer.handle(tweet)
            writer.counter += 1
        writer.on_finish()
        return writer.fname

    def test_hostile_text_is_json_escaped_on_disk_and_round_trips(
        self, clients, tmp_path, capsys
    ):
        tweets = [
            {"id": 1, "text": "=x" + ESC + "[31m" + RLO + SURR, "created_at": CREATED},
            {"id": 2, "text": "two", "created_at": CREATED},
        ]
        fname = self._write(clients, str(tmp_path / "twitter-files"), tweets)
        with open(fname, "rb") as fh:
            data = fh.read()
        assert ESC.encode() not in data and RLO.encode("utf-8") not in data
        assert data.count(b"\n") == 2 and data.endswith(b"\n")
        back = [safe_json_loads(line, context="test") for line in data.splitlines()]
        assert back == tweets
        out = capsys.readouterr().out
        assert out.splitlines() == [f"Writing to {fname}", "Written 2 Tweets"]
        # the written file is a valid json2csv input and the cell is defused there
        csv_out = str(tmp_path / "o.csv")
        with open(fname, encoding="utf-8") as fp:
            json2csv(fp, csv_out, ["id", "text"])
        assert _rows(csv_out)[1] == ["1", "'=x\\x1b[31m\\u202e\\ud800"]

    def test_gzip_file_round_trips(self, clients, tmp_path, capsys):
        tweets = [{"id": 1, "text": "@m" + BEL, "created_at": CREATED}]
        fname = self._write(clients, str(tmp_path / "gz"), tweets, gzip_compress=True)
        assert fname.endswith(".json.gz")
        with gzip.open(fname, "rb") as fh:
            data = fh.read()
        assert BEL.encode() not in data
        assert safe_json_loads(data.splitlines()[0], context="test") == tweets[0]

    def test_an_operator_subdir_with_a_bidi_override_prints_escaped(
        self, clients, tmp_path, capsys
    ):
        subdir = str(tmp_path / ("x" + RLO + "y"))
        self._write(clients, subdir, [{"id": 1, "text": "t", "created_at": CREATED}])
        out = capsys.readouterr().out
        assert not _has_live_control(out), ascii(out)
        assert "\\u202e" in out.splitlines()[0]

    def test_guess_path_keeps_absolute_and_homes_relative(self, clients):
        from nltk.twitter.util import guess_path

        absolute = str(os.path.abspath(os.sep))
        assert guess_path(absolute) == absolute
        relative = guess_path("twitter-files")
        assert os.path.isabs(relative) and relative.endswith("twitter-files")


class TestCredentialsFile:
    def _auth(self, clients):
        from nltk.twitter.util import Authenticate

        return Authenticate()

    def test_hostile_key_names_never_reach_the_error_live_and_no_secret_leaks(
        self, clients, tmp_path
    ):
        creds = tmp_path / "hostile.txt"
        creds.write_text(
            ESC + "[31mapp_key=K\napp_secret=SEKRIT_VALUE\n" + RLO + "oauth_token=T\n",
            encoding="utf-8",
        )
        with pytest.raises(ValueError) as exc:
            self._auth(clients).load_creds(
                creds_file="hostile.txt", subdir=str(tmp_path)
            )
        msg = str(exc.value)
        assert not _has_live_control(msg), ascii(msg)
        assert "SEKRIT_VALUE" not in msg and "app_secret" in msg

    def test_verbose_read_of_a_bidi_named_directory_prints_escaped(
        self, clients, tmp_path, capsys
    ):
        subdir = tmp_path / ("c" + RLO + "d")
        subdir.mkdir()
        (subdir / "credentials.txt").write_text(
            "app_key=K\napp_secret=S\naccess_token=A\n", encoding="utf-8"
        )
        oauth = self._auth(clients).load_creds(subdir=str(subdir), verbose=True)
        assert oauth == {"app_key": "K", "app_secret": "S", "access_token": "A"}
        out = capsys.readouterr().out
        assert not _has_live_control(out), ascii(out)
        assert out.splitlines()[0].startswith("Reading credentials file")

    def test_operator_paths_outside_the_subdir_are_operator_choices(
        self, clients, tmp_path
    ):
        outside = tmp_path / "outside"
        outside.mkdir()
        inside = tmp_path / "inside"
        inside.mkdir()
        (outside / "c.txt").write_text(
            "app_key=K\napp_secret=S\noauth_token=T\noauth_token_secret=TS\n",
            encoding="utf-8",
        )
        auth = self._auth(clients)
        oauth = auth.load_creds(
            creds_file=os.path.join("..", "outside", "c.txt"), subdir=str(inside)
        )
        assert oauth["app_key"] == "K"
        assert auth.creds_fullpath == str(outside / "c.txt")
        auth = self._auth(clients)
        assert (
            auth.load_creds(creds_file=str(outside / "c.txt"), subdir="/nonexistent")[
                "app_key"
            ]
            == "K"
        )

    @POSIX_ONLY
    def test_a_symlinked_credentials_file_is_followed(self, clients, tmp_path):
        real = tmp_path / "real.txt"
        real.write_text("app_key=K\napp_secret=S\naccess_token=A\n", encoding="utf-8")
        (tmp_path / "link.txt").symlink_to(real)
        oauth = self._auth(clients).load_creds(
            creds_file="link.txt", subdir=str(tmp_path)
        )
        assert oauth["access_token"] == "A"

    def test_empty_directory_and_undecodable_files(
        self, clients, tmp_path, monkeypatch
    ):
        (tmp_path / "empty.txt").write_text("", encoding="utf-8")
        with pytest.raises(ValueError, match=r"found keys: \[\]"):
            self._auth(clients).load_creds(creds_file="empty.txt", subdir=str(tmp_path))
        with pytest.raises(OSError, match="Cannot find file"):
            self._auth(clients).load_creds(creds_file=".", subdir=str(tmp_path))
        (tmp_path / "latin.txt").write_bytes(
            b"app_key=K\xe9\napp_secret=S\naccess_token=A\n"
        )
        with pytest.raises(UnicodeDecodeError):
            self._auth(clients).load_creds(creds_file="latin.txt", subdir=str(tmp_path))
        monkeypatch.delenv("TWITTER", raising=False)
        with pytest.raises(ValueError, match="TWITTER environment variable"):
            self._auth(clients).load_creds()


FIELD_SETS = {
    "text": ("json2csv", (["text"],)),
    "tweet": (
        "json2csv",
        (
            [
                "created_at",
                "favorite_count",
                "id",
                "in_reply_to_status_id",
                "in_reply_to_user_id",
                "retweet_count",
                "retweeted",
                "text",
                "truncated",
                "user.id",
            ],
        ),
    ),
    "user": (
        "json2csv",
        (["id", "text", "user.id", "user.followers_count", "user.friends_count"],),
    ),
    "hashtag": ("entities", (["id", "text"], "hashtags", ["text"])),
    "usermention": (
        "entities",
        (["id", "text"], "user_mentions", ["id", "screen_name"]),
    ),
    "media": ("entities", (["id"], "media", ["media_url", "url"])),
    "url": ("entities", (["id"], "urls", ["url", "expanded_url"])),
    "userurl": (
        "entities",
        (["id", "screen_name"], "user.urls", ["url", "expanded_url"]),
    ),
    "place": ("entities", (["id", "text"], "place", ["name", "country"])),
    "placeboundingbox": (
        "entities",
        (["id", "name"], "place.bounding_box", ["coordinates"]),
    ),
    "retweet": (
        "entities",
        (
            ["id"],
            "retweeted_status",
            [
                "created_at",
                "favorite_count",
                "id",
                "in_reply_to_status_id",
                "in_reply_to_user_id",
                "retweet_count",
                "text",
                "truncated",
                "user.id",
            ],
        ),
    ),
}


@pytest.fixture(scope="module")
def corpus_file():
    from nltk.corpus import twitter_samples

    try:
        return twitter_samples.abspath("tweets.20150430-223406.json")
    except LookupError as exc:
        pytest.skip(f"the twitter_samples corpus is not installed: {exc}")


def _corpus_lines(path, limit=None):
    from nltk.data import open_datafile

    with open_datafile(path) as fh:
        lines = []
        for i, line in enumerate(fh):
            if limit is not None and i >= limit:
                break
            lines.append(line)
    return lines


class TestRealCorpus:
    def test_the_whole_corpus_changes_only_by_the_apostrophe(
        self, tmp_path, corpus_file
    ):
        lines = _corpus_lines(corpus_file)
        out = str(tmp_path / "text.csv")
        json2csv(iter(lines), out, ["id", "text", "user.screen_name", "user.name"])
        rows = _rows(out)
        assert rows[0] == ["id", "text", "user.screen_name", "user.name"]
        assert len(rows) == len(lines) + 1
        _assert_sheet_safe(rows)
        _assert_no_unconditional_control(_raw(out))
        defused = escaped = 0
        for row, line in zip(rows[1:], lines):
            tweet = safe_json_loads(line, context="test")
            original = [
                str(tweet["id"]),
                tweet["text"],
                tweet["user"]["screen_name"],
                tweet["user"]["name"],
            ]
            for cell, before in zip(row, original):
                if cell == before:
                    continue
                if cell == "'" + before:
                    defused += 1
                    continue
                # the only other change: a real tweet or user name carrying a
                # CR is escaped, with every visible character kept in order
                assert _has_live_control(before), (ascii(before), ascii(cell))
                assert _visible_in_order(before, cell), (ascii(before), ascii(cell))
                escaped += 1
        # real tweets lead with an @ mention, and a few carry a control, often
        # enough for both counts to prove the writer did something
        assert defused > 100 and escaped > 0, (defused, escaped)

    @pytest.mark.parametrize("name", sorted(FIELD_SETS))
    def test_every_documented_field_set_runs_on_real_tweets(
        self, tmp_path, corpus_file, name
    ):
        kind, args = FIELD_SETS[name]
        lines = _corpus_lines(corpus_file, limit=5000)
        out = str(tmp_path / f"{name}.csv")
        if kind == "json2csv":
            json2csv(iter(lines), out, *args)
            rows = _rows(out)
            assert rows[0] == args[0] and len(rows) == len(lines) + 1
        else:
            json2csv_entities(iter(lines), out, *args)
            rows = _rows(out)
            assert len(rows[0]) == len(args[0]) + len(args[2])
        _assert_sheet_safe(rows)
        _assert_no_unconditional_control(_raw(out))

    @pytest.mark.parametrize(
        "fixture", ["positive_tweets.json", "negative_tweets.json"]
    )
    def test_the_sentiment_fixtures_round_trip(self, tmp_path, corpus_file, fixture):
        from nltk.corpus import twitter_samples

        path = twitter_samples.abspath(fixture)
        lines = _corpus_lines(path)
        out = str(tmp_path / "sent.csv")
        json2csv(iter(lines), out, ["id", "text"])
        rows = _rows(out)
        assert len(rows) == len(lines) + 1
        _assert_sheet_safe(rows)
        _assert_no_unconditional_control(_raw(out))


class TestSinkScaling:
    HOSTILE = json.dumps(
        {
            "id": 1,
            "text": "=cmd|' /C calc'!A0 "
            + ESC
            + "[31m"
            + RLO
            + " RT @u: hi caf"
            + chr(0xE9),
            "user": {"screen_name": "@evil", "id": 2},
            "entities": {"hashtags": [{"text": "=t"}, {"text": "ok"}]},
        }
    )

    def test_json2csv_is_linear_in_the_number_of_tweets(self, tmp_path):
        out = str(tmp_path / "o.csv")

        def op(n):
            json2csv(
                io.StringIO((self.HOSTILE + "\n") * n),
                out,
                ["id", "text", "user.screen_name"],
            )

        timing.assert_subquadratic(op, 2500, 10000, cpu_bound=True)

    def test_json2csv_entities_is_linear_in_the_number_of_tweets(self, tmp_path):
        out = str(tmp_path / "o.csv")

        def op(n):
            json2csv_entities(
                io.StringIO((self.HOSTILE + "\n") * n),
                out,
                ["id", "text"],
                "hashtags",
                ["text"],
            )

        timing.assert_subquadratic(op, 2000, 8000, cpu_bound=True)

    def test_a_million_digit_formula_cell_is_defused_unparsed_within_budget(
        self, tmp_path
    ):
        out = str(tmp_path / "o.csv")
        line = '{"id": 1, "text": "-' + "9" * 1_000_000 + '"}'
        with timing.budget(5, "formula cell", cpu_bound=True):
            json2csv(_lines_fp([line]), out, ["id", "text"])
        assert _second_line_cell(out) == "'-" + "9" * 1_000_000

    def test_a_control_dense_cell_stays_within_budget(self, tmp_path):
        out = str(tmp_path / "o.csv")
        text = (ESC + "[31m" + LRI) * 100_000
        with timing.budget(20, "control-dense cell", cpu_bound=True):
            json2csv(_tweets_fp([{"id": 1, "text": text}]), out, ["id", "text"])
        assert _second_line_cell(out) == "\\x1b[31m\\u2066" * 100_000

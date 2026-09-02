# Natural Language Toolkit: expanded JSON deserialization attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Expanded JSON deserialization attack matrix (GHSA-8mgp companion).

"json.load is not safe either": a malicious JSON document can crash or stall a
process even though JSON carries no code. This suite drives each hostile input
through the REAL nltk caller path (perceptron model load, ``nltk.data.load``,
``nltk.help`` tagset lookup, tweet readers) and holds every site to one hard
property:

* a hostile document is REFUSED with a bounded ``ValueError`` (or otherwise
  caught) and NEVER crashes the interpreter, even when the process recursion
  limit has been raised, and
* a benign control loads and works.

The teeth are explicit: the SAME deeply nested payload is first run through the
stock C ``json`` decoder with a raised recursion limit and shown to hard-crash
the interpreter (a fatal signal), so the guarded assertions below it are real,
not vacuous.

Vectors covered: deeply nested arrays and objects (C-stack overflow), giant
integers (int/str conversion cost), oversized documents (memory), duplicate
keys and unexpected top-level types (shape confusion), and a perceptron model
whose weight/tagdict values are hostile strings (confirming the values are inert
data, never evaluated).

Cross platform notes: subprocess fixtures are staged under ``$HOME`` (never
``/tmp``), every file is opened with an explicit encoding, subprocesses carry a
wall-clock timeout, and the fatal-signal teeth are guarded with a POSIX-only
``skipif``.
"""

import ast
import gzip
import importlib.util
import io
import json
import os
import signal
import subprocess
import sys
import textwrap

import pytest

import nltk

POSIX_ONLY = pytest.mark.skipif(os.name != "posix", reason="POSIX-only fatal signal")

# Depth that reliably overflows the C stack of the stock decoder once the
# recursion limit is lifted, while staying a tiny (~1.6 MB) payload.
DEEP = 400_000
# A recursion limit high enough that the C decoder recurses into a real C-stack
# overflow instead of raising a bounded RecursionError first.
RECLIMIT = 5_000_000
# The repo root so a "python -c" child imports THIS worktree's nltk (the parent
# directory of the nltk package, i.e. two levels up from nltk/__init__.py).
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(nltk.__file__)))

# Child-side preamble: stage a private data root under $HOME, register it, turn
# on pathsec enforcement, and expose the hostile-payload builders. Everything a
# scenario body needs is defined here so the bodies stay short.
PREAMBLE = textwrap.dedent(
    """
    import io, json, os, pathlib, shutil, sys, tempfile

    import nltk, nltk.data
    from nltk import pathsec

    DEEP = {deep}

    def stage_root():
        root = tempfile.mkdtemp(prefix="nltk_attack_root_", dir=str(pathlib.Path.home()))
        pathsec.ENFORCE = True
        nltk.data.path[:] = [root]
        pathsec._ALLOWED_ROOTS_CACHE = None
        pathsec._LAST_DATA_PATHS = None
        return root

    def deep_array():
        return "[" * DEEP + "]" * DEEP

    def deep_object():
        return '{{"a":' * DEEP + "1" + "}}" * DEEP

    def giant_int():
        return "1" + "0" * 10_000_000

    def ok(tag=""):
        print("RESULT:OK:" + str(tag))
        sys.stdout.flush()

    def rejected(exc):
        print("RESULT:REJECTED:" + type(exc).__name__ + ":" + str(exc)[:80])
        sys.stdout.flush()

    def write_text(path, text):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    """
).format(deep=DEEP)


def run_child(body, *, timeout=60, reclimit=None, memcap_bytes=None):
    """Run a child interpreter (PREAMBLE + body) with a wall-clock timeout.

    Returns the completed process. ``reclimit`` lifts the recursion limit so the
    deep-nesting vector can reach a real C-stack overflow; ``memcap_bytes`` caps
    address space where the platform supports it (belt and suspenders on top of
    the size guard). Neither is on by default.
    """
    prologue = ""
    if reclimit is not None:
        prologue += f"import sys as _s; _s.setrecursionlimit({reclimit})\n"
    if memcap_bytes is not None:
        prologue += textwrap.dedent(
            f"""
            try:
                import resource as _r
                _soft, _hard = _r.getrlimit(_r.RLIMIT_AS)
                _cap = {memcap_bytes}
                if _hard == _r.RLIM_INFINITY or _cap < _hard:
                    _r.setrlimit(_r.RLIMIT_AS, (_cap, _hard))
            except (ImportError, ValueError, OSError):
                pass
            """
        )
    src = PREAMBLE + "\n" + prologue + textwrap.dedent(body)
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", src],
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=REPO_ROOT,
        env=env,
    )


def assert_no_crash_and_rejected(proc):
    """The guarded child must exit cleanly and report a bounded rejection."""
    assert proc.returncode == 0, (
        f"guarded caller crashed (returncode={proc.returncode}); "
        f"stdout={proc.stdout!r} stderr={proc.stderr[-400:]!r}"
    )
    assert "RESULT:REJECTED:" in proc.stdout, (
        f"expected a bounded rejection; stdout={proc.stdout!r} "
        f"stderr={proc.stderr[-400:]!r}"
    )


# In-process unit checks on the shared chokepoint (safe_json_load / _loads):
# every caller funnels through these, so a bounded rejection here is inherited
# everywhere, and none of these can crash the interpreter (no subprocess).


def test_helper_parses_benign_control():
    from nltk.jsontags import safe_json_loads

    assert safe_json_loads('{"a": [1, 2, 3], "b": {"c": 4}}') == {
        "a": [1, 2, 3],
        "b": {"c": 4},
    }


def test_helper_rejects_deep_array_bounded():
    from nltk.jsontags import safe_json_loads

    payload = "[" * DEEP + "]" * DEEP
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads(payload)


def test_helper_rejects_deep_object_bounded():
    from nltk.jsontags import safe_json_loads

    payload = '{"a":' * DEEP + "1" + "}" * DEEP
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads(payload)


def test_helper_rejects_oversize_document():
    from nltk.jsontags import safe_json_loads

    # A small explicit cap keeps the test cheap while exercising the same guard
    # every caller inherits at its 200 MiB default.
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads('"' + "a" * 1000 + '"', max_bytes=100)


def test_helper_giant_integer_raises_not_hangs():
    from nltk.jsontags import safe_json_loads

    # The interpreter's int/str conversion limit bounds the parse: a bounded
    # ValueError, not a multi-second quadratic conversion.
    with pytest.raises(ValueError):
        safe_json_loads("[" + "1" + "0" * 10_000_000 + "]")


def test_helper_duplicate_keys_last_value_wins():
    from nltk.jsontags import safe_json_loads

    # Standard json semantics, preserved: no ambiguity or misbehavior.
    assert safe_json_loads('{"a": 1, "a": 2, "a": 3}') == {"a": 3}


def test_helper_unexpected_top_level_types_parse_or_bound():
    from nltk.jsontags import safe_json_loads

    # Non-object top levels are valid JSON and parse to plain data.
    assert safe_json_loads("123") == 123
    assert safe_json_loads('"hello"') == "hello"
    assert safe_json_loads("[1, 2, 3]") == [1, 2, 3]
    # A deep top-level array is still rejected by the depth guard.
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads("[" * DEEP + "]" * DEEP)


def test_helper_reads_text_and_binary_streams():
    from nltk.jsontags import safe_json_load

    assert safe_json_load(io.StringIO('{"x": 1}')) == {"x": 1}
    assert safe_json_load(io.BytesIO(b'{"x": 1}')) == {"x": 1}


def test_helper_stream_size_cap_bounds_memory():
    from nltk.jsontags import safe_json_load

    huge = io.StringIO('"' + "a" * 5000 + '"')
    with pytest.raises(ValueError, match="exceeds the"):
        safe_json_load(huge, max_bytes=100)


# JSONTaggedDecoder (NLTK model-artifact tag decoder): its ``super().decode``
# runs the recursive C accelerator, so it must bound nesting BEFORE that call,
# not only in the later Python ``decode_obj`` walk (GHSA-rf74-v2fm-23pw).


def test_tagged_decoder_deep_nesting_prescanned_not_crashed():
    from nltk.jsontags import JSONTaggedDecoder

    payload = "[" * DEEP + "]" * DEEP
    with pytest.raises(ValueError, match="nesting depth"):
        JSONTaggedDecoder().decode(payload)


def test_tagged_decoder_deep_via_json_loads_cls_refused():
    # The stdlib entry point (json.loads(..., cls=JSONTaggedDecoder)) routes
    # through the same decode(), so it is bounded too.
    from nltk.jsontags import JSONTaggedDecoder

    payload = '{"a":' * DEEP + "1" + "}" * DEEP
    with pytest.raises(ValueError, match="nesting depth"):
        json.loads(payload, cls=JSONTaggedDecoder)


def test_tagged_decoder_benign_tagged_roundtrip():
    from nltk.jsontags import JSONTaggedDecoder, JSONTaggedEncoder, register_tag

    @register_tag
    class _Point:
        json_tag = "test_attack_json._Point"

        def __init__(self, n):
            self.n = n

        def encode_json_obj(self):
            return self.n

        @classmethod
        def decode_json_obj(cls, obj):
            return cls(obj)

    encoded = json.dumps(_Point(7), cls=JSONTaggedEncoder)
    restored = JSONTaggedDecoder().decode(encoded)
    assert isinstance(restored, _Point) and restored.n == 7


def test_tagged_decoder_unknown_tag_refused():
    from nltk.jsontags import JSONTaggedDecoder

    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode('{"!nltk.not.a.real.tag": 1}')


def test_tagged_decoder_depth_at_limit_still_decodes():
    from nltk.jsontags import JSONTaggedDecoder

    # A document exactly at the decode-depth limit is legitimate and still loads.
    ok = JSONTaggedDecoder().decode("[" * 200 + "]" * 200)
    assert isinstance(ok, list)


# The structural-depth scan is the whole guarantee, so it must never UNDERCOUNT
# real nesting (which would let a deep payload slip past): brackets inside string
# literals must not count; real brackets outside them always must.


def test_scan_ignores_brackets_inside_strings():
    from nltk.jsontags import _scan_json_depth

    # An array holding one string full of brackets nests exactly one level.
    assert _scan_json_depth('["' + "[{" * 5000 + '"]', 10**9) == 1


def test_scan_honors_escaped_quotes_and_backslashes():
    from nltk.jsontags import _scan_json_depth

    # \" does not close the string (brackets after it are still in-string);
    # \\ then " does close it (the following bracket is real, depth 2).
    assert _scan_json_depth('["a\\"[[[b"]', 10**9) == 1
    assert _scan_json_depth('["a\\\\"[]', 10**9) == 2


def test_scan_does_not_undercount_deep_nesting_after_strings():
    from nltk.jsontags import _scan_json_depth

    # Real deep nesting hidden after a closed string with escape trickery is
    # still fully counted, so safe_json_loads cannot be tricked into accepting it.
    payload = '"a\\"]}[b"' + "[" * 4000 + "]" * 4000
    assert _scan_json_depth(payload, 10**9) == 4000


@pytest.mark.parametrize(
    "payload",
    [
        '["' + "[" * 500 + '"]',  # brackets buried in a string
        '"\\""' + "[{" * 300,  # escaped quote then real mixed nesting
        "{" + '"k":' * 150 + "1" + "}" * 150,  # deep via object values
        "[{" * 150 + "1" + "}]" * 150,  # deep via mixed brackets
    ],
)
def test_scan_soundness_accepted_inputs_do_not_out_nest_the_scan(payload):
    from nltk.jsontags import _scan_json_depth

    # For each adversarial input, the scan's depth must be >= the depth the real
    # parser reaches, so an accepted document can never recurse past the bound.
    scanned = _scan_json_depth(payload, 10**9)
    try:
        parsed = json.loads(payload)
    except ValueError:
        return  # malformed: no object graph, nothing to out-nest
    assert scanned >= _actual_depth(parsed)


def _actual_depth(obj):
    if isinstance(obj, dict):
        return 1 + max((_actual_depth(v) for v in obj.values()), default=0)
    if isinstance(obj, list):
        return 1 + max((_actual_depth(v) for v in obj), default=0)
    return 0


def test_giant_shallow_array_bounded_by_size_not_depth():
    from nltk.jsontags import safe_json_loads

    # A huge but shallow array is not a depth attack; the size cap bounds it.
    payload = "[" + ",".join("0" for _ in range(5000)) + "]"
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads(payload, max_bytes=100)


# Teeth: the stock decoder hard-crashes on the same payload, proving the guard
# above is non-vacuous, and the guard survives that payload with the recursion
# limit lifted.


@POSIX_ONLY
def test_teeth_raw_json_deep_array_hard_crashes():
    proc = run_child(
        """
        import json
        json.loads(deep_array())
        ok("raw parsed, no crash")
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    # Without the depth guard this payload is not safely parsable: a raised
    # recursion limit overflows the C stack into a fatal SIGSEGV pre-3.12, or a
    # RecursionError on 3.12+. The bounded loader rejects it before parsing.
    fatal = {-signal.SIGSEGV, -signal.SIGABRT, -signal.SIGBUS}
    crashed = proc.returncode in fatal
    recursion_error = proc.returncode != 0 and "RecursionError" in (proc.stderr or "")
    assert crashed or recursion_error, (
        "stock json.loads was expected to hard-crash or raise RecursionError on "
        f"deeply nested input but returncode={proc.returncode}, "
        f"stdout={proc.stdout!r}, stderr={(proc.stderr or '')[-200:]!r}"
    )
    assert "raw parsed" not in proc.stdout


def test_teeth_raw_json_giant_int_raises_not_hangs():
    # No fatal signal here: the int/str limit turns the giant integer into a
    # bounded ValueError. The value of the teeth is that it returns quickly
    # (the timeout would trip if it hung on an unbounded conversion).
    proc = run_child(
        """
        import json
        try:
            json.loads(giant_int())
            print("RESULT:OK:parsed")
        except ValueError:
            print("RESULT:REJECTED:ValueError")
        """,
        timeout=30,
    )
    assert proc.returncode == 0
    assert "RESULT:REJECTED:ValueError" in proc.stdout


@POSIX_ONLY
def test_guard_survives_deep_array_with_raised_recursion_limit():
    proc = run_child(
        """
        from nltk.jsontags import safe_json_loads
        try:
            safe_json_loads(deep_array())
            ok("parsed (unexpected)")
        except ValueError as exc:
            rejected(exc)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


# Real caller paths, each with the recursion limit lifted so a leak would
# surface as a crash. Each site: hostile -> bounded rejection, no crash; plus a
# benign control that loads and works.


@POSIX_ONLY
def test_averaged_perceptron_load_deep_weights_no_crash():
    proc = run_child(
        """
        from nltk.tag.perceptron import AveragedPerceptron
        root = stage_root()
        path = os.path.join(root, "weights.json")
        write_text(path, deep_array())
        try:
            AveragedPerceptron().load(path)
            ok("loaded (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


def test_averaged_perceptron_load_benign_control():
    proc = run_child(
        """
        from nltk.tag.perceptron import AveragedPerceptron
        root = stage_root()
        path = os.path.join(root, "weights.json")
        write_text(path, json.dumps({"bias": {"NN": 1.5, "DT": -0.25}}))
        ap = AveragedPerceptron()
        ap.load(path)
        assert ap.weights == {"bias": {"NN": 1.5, "DT": -0.25}}, ap.weights
        ok("weights round-tripped")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:weights round-tripped" in proc.stdout


@POSIX_ONLY
def test_perceptron_load_from_json_deep_model_no_crash():
    proc = run_child(
        """
        from nltk.tag.perceptron import PerceptronTagger
        root = stage_root()
        model = os.path.join(root, "model")
        os.mkdir(model)
        for attr in ("weights", "tagdict", "classes"):
            write_text(
                os.path.join(model, "averaged_perceptron_tagger_xxx.%s.json" % attr),
                deep_array(),
            )
        try:
            PerceptronTagger(load=False).load_from_json(lang="xxx", loc=model)
            ok("loaded (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


def test_perceptron_train_save_load_tag_benign_control():
    # The functionality gate: a freshly trained tagger saves its JSON, reloads
    # it through the guarded path, and tags correctly.
    proc = run_child(
        """
        from nltk.data import FileSystemPathPointer
        from nltk.tag.perceptron import PerceptronTagger
        tagger = PerceptronTagger(load=False)
        train = [
            [("today", "NN"), ("is", "VBZ"), ("good", "JJ"), ("day", "NN")],
            [("yes", "NNS"), ("it", "PRP"), ("beautiful", "JJ")],
        ]
        tagger.train(train, save_loc=tagger.save_dir)
        reloaded = PerceptronTagger(loc=FileSystemPathPointer(tagger.save_dir))
        assert reloaded.classes == tagger.classes, reloaded.classes
        tagged = reloaded.tag(["today", "is", "a", "beautiful", "day"])
        assert [t for _, t in tagged], tagged
        ok("trained/saved/loaded/tagged")
        """,
        timeout=90,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:trained/saved/loaded/tagged" in proc.stdout


def test_perceptron_model_values_are_inert_data_not_code():
    # A model whose weight and tagdict values are hostile strings must load them
    # as plain data (no eval/exec, no side effect), never as code. JSON has no
    # globals, and the caller does arithmetic on the values, never eval.
    proc = run_child(
        """
        from nltk.tag.perceptron import AveragedPerceptron
        root = stage_root()
        sentinel = os.path.join(root, "SENTINEL")
        payload = "__import__('os').system('touch %s')" % sentinel
        path = os.path.join(root, "weights.json")
        write_text(path, json.dumps({"bias": {"NN": payload}}))
        ap = AveragedPerceptron()
        ap.load(path)
        # The smuggled string is present verbatim as inert data ...
        assert ap.weights["bias"]["NN"] == payload, ap.weights
        # ... and nothing executed it.
        assert not os.path.exists(sentinel), "code execution smuggled through JSON!"
        ok("inert data, no execution")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:inert data, no execution" in proc.stdout


@POSIX_ONLY
def test_data_load_json_deep_resource_no_crash():
    proc = run_child(
        """
        import nltk.data
        root = stage_root()
        write_text(os.path.join(root, "hostile.json"), deep_array())
        try:
            nltk.data.load("hostile.json", format="json", cache=False)
            ok("loaded (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)
    # The rejection is the depth guard firing before the tag gate, not the
    # pre-existing tag error.
    assert "nesting depth" in proc.stdout


def test_data_load_json_benign_reaches_tag_gate_unchanged():
    """Guarded parse SUCCEEDS on a benign object; behavior is unchanged.

    The format="json" tag gate is pre-existing and rejects every plain object;
    the point here is that the object is fully parsed and the same tag-gate
    error is raised, not a JSON parse failure.
    """
    proc = run_child(
        """
        import nltk.data
        root = stage_root()
        write_text(os.path.join(root, "benign.json"), json.dumps({"a": 1}))
        try:
            nltk.data.load("benign.json", format="json", cache=False)
            print("RESULT:OK:returned")
        except ValueError as exc:
            print("RESULT:REJECTED:ValueError:" + str(exc)[:60])
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    # Parse succeeded; the pre-existing tag gate is what rejects it.
    assert "Unknown json tag" in proc.stdout


@POSIX_ONLY
def test_help_tagset_deep_file_no_crash():
    proc = run_child(
        """
        import nltk.help
        root = stage_root()
        d = os.path.join(root, "help", "tagsets_json", "PY3_json")
        os.makedirs(d)
        write_text(os.path.join(d, "brown_tagset.json"), deep_array())
        try:
            nltk.help.brown_tagset()
            ok("printed (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


def test_help_tagset_benign_control():
    proc = run_child(
        """
        import nltk.help
        root = stage_root()
        d = os.path.join(root, "help", "tagsets_json", "PY3_json")
        os.makedirs(d)
        write_text(
            os.path.join(d, "brown_tagset.json"),
            json.dumps({"NN": ["noun", "the dog barked"]}),
        )
        nltk.help.brown_tagset("NN")
        ok("tagset printed")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:tagset printed" in proc.stdout


@POSIX_ONLY
def test_twitter_reader_deep_tweet_line_no_crash():
    proc = run_child(
        """
        from nltk.corpus.reader.twitter import TwitterCorpusReader
        root = stage_root()
        write_text(os.path.join(root, "tweets.json"), deep_array() + "\\n")
        try:
            reader = TwitterCorpusReader(root, r".*\\.json")
            reader.strings("tweets.json")
            ok("read (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


def test_twitter_reader_benign_control():
    proc = run_child(
        """
        from nltk.corpus.reader.twitter import TwitterCorpusReader
        root = stage_root()
        line = json.dumps({"text": "hello world", "id": 1})
        write_text(os.path.join(root, "tweets.json"), line + "\\n")
        reader = TwitterCorpusReader(root, r".*\\.json")
        strings = reader.strings("tweets.json")
        assert strings == ["hello world"], strings
        ok("tweet text read")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:tweet text read" in proc.stdout


@POSIX_ONLY
def test_json2csv_deep_tweet_line_no_crash():
    proc = run_child(
        """
        import io
        from nltk.twitter.common import json2csv
        root = stage_root()
        out = os.path.join(root, "out.csv")
        fp = io.StringIO(deep_array() + "\\n")
        try:
            json2csv(fp, out, ["id"], gzip_compress=False)
            ok("wrote (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


def test_json2csv_benign_control():
    proc = run_child(
        """
        import io
        from nltk.twitter.common import json2csv
        root = stage_root()
        out = os.path.join(root, "out.csv")
        line = json.dumps({"id": 42, "text": "hi"})
        json2csv(io.StringIO(line + "\\n"), out, ["id"], gzip_compress=False)
        with open(out, "r", encoding="utf-8") as fh:
            data = fh.read()
        assert "42" in data, data
        ok("csv row written")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:csv row written" in proc.stdout


def test_sentiment_preprocess_benign_control():
    proc = run_child(
        """
        from nltk.sentiment.util import json2csv_preprocess
        root = stage_root()
        infile = os.path.join(root, "tweets.json")
        out = os.path.join(root, "out.csv")
        write_text(infile, json.dumps({"text": "a lovely day"}) + "\\n")
        json2csv_preprocess(
            infile, out, ["text"], gzip_compress=False, remove_duplicates=False
        )
        with open(out, "r", encoding="utf-8") as fh:
            data = fh.read()
        assert "lovely" in data, data
        ok("preprocess row written")
        shutil.rmtree(root, ignore_errors=True)
        """,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-400:]
    assert "RESULT:OK:preprocess row written" in proc.stdout


@POSIX_ONLY
def test_sentiment_preprocess_deep_tweet_line_no_crash():
    proc = run_child(
        """
        from nltk.sentiment.util import json2csv_preprocess
        root = stage_root()
        infile = os.path.join(root, "tweets.json")
        out = os.path.join(root, "out.csv")
        write_text(infile, deep_array() + "\\n")
        try:
            json2csv_preprocess(infile, out, ["text"], gzip_compress=False)
            ok("wrote (unexpected)")
        except ValueError as exc:
            rejected(exc)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        """,
        reclimit=RECLIMIT,
        timeout=60,
    )
    assert_no_crash_and_rejected(proc)


# Non-finite values: NaN / Infinity / -Infinity are a CPython json extension,
# not RFC 8259, and a numeric literal can also overflow an IEEE double to inf.
# safe_json_loads and JSONTaggedDecoder refuse every non-finite value so an
# attacker cannot smuggle one into a model weight or a tweet field, while finite
# values (including the largest representable double) still parse.


def test_helper_rejects_nan_infinity_constants():
    from nltk.jsontags import safe_json_loads

    for token in ("NaN", "Infinity", "-Infinity", '{"w": NaN}', "[1, 2, Infinity]"):
        with pytest.raises(ValueError, match="non-finite"):
            safe_json_loads(token)


def test_helper_rejects_numeric_overflow_to_infinity():
    from nltk.jsontags import safe_json_loads

    # Valid JSON number syntax whose value overflows a double to inf; caught by
    # parse_float rather than parse_constant.
    for token in ("1e400", "1e999999", "-1e999999", "1.8e308", '{"w": 1e400}'):
        with pytest.raises(ValueError, match="non-finite"):
            safe_json_loads(token)


def test_helper_finite_edge_floats_still_parse():
    from nltk.jsontags import safe_json_loads

    # The largest finite double parses; a tiny exponent underflows to 0.0
    # (finite); ordinary floats are unaffected.
    assert safe_json_loads("1.5e308") == 1.5e308
    assert safe_json_loads("1e-999999") == 0.0
    assert safe_json_loads('{"w": [0.5, -1.25, 1e10]}') == {"w": [0.5, -1.25, 1e10]}


def test_tagged_decoder_rejects_non_finite():
    from nltk.jsontags import JSONTaggedDecoder

    for token in ("NaN", "Infinity", '{"x": -Infinity}', "1e400", '{"x": 1e999999}'):
        with pytest.raises(ValueError, match="non-finite"):
            JSONTaggedDecoder().decode(token)
    # Finite control still decodes.
    assert JSONTaggedDecoder().decode('{"x": 1.5}') == {"x": 1.5}


def test_tagged_decoder_rejects_oversize_document():
    from nltk.jsontags import JSONTaggedDecoder

    decoder = JSONTaggedDecoder()
    decoder.MAX_DECODE_BYTES = 100  # shrink the cap so the test stays cheap
    with pytest.raises(ValueError, match="over the"):
        decoder.decode('"' + "a" * 1000 + '"')
    # A document under the cap still decodes.
    assert decoder.decode('{"a": 1}') == {"a": 1}


def test_averaged_perceptron_load_rejects_non_finite_weight(tmp_path):
    # End-to-end: a model file carrying a non-finite weight is refused by the
    # loader (which funnels through safe_json_load), so a poisoned weight never
    # reaches the tagger's scoring.
    from nltk.tag.perceptron import AveragedPerceptron

    path = tmp_path / "weights.json"
    path.write_text('{"the": {"NN": Infinity, "DT": 0.5}}', encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        AveragedPerceptron().load(str(path))


# ==========================================================================
# Advisory / CWE coverage map and net-new edge vectors on the chokepoint.
#
# jsontags is the single place all JSON deserialization funnels through, so a
# defence proven here is inherited by every caller. The cases below name the
# reported advisory or weakness class each one guards against.
# ==========================================================================


def test_ghsa_rf74_tagged_decoder_recursion_bounded():
    # GHSA-rf74-v2fm-23pw / CWE-674: unbounded recursion in decode_obj. The deep
    # document is refused with a bounded ValueError, never a RecursionError.
    from nltk.jsontags import JSONTaggedDecoder

    with pytest.raises(ValueError):
        JSONTaggedDecoder().decode("[" * 5000 + "]" * 5000)


def test_cwe400_resource_exhaustion_size_and_int_bounded():
    # CWE-400 / CWE-770 / CVE-2020-10735: a large document is refused by the byte
    # cap and a giant integer by the interpreter's int/str conversion limit.
    from nltk.jsontags import safe_json_loads

    with pytest.raises(ValueError, match="over the"):
        safe_json_loads('"' + "a" * 1000 + '"', max_bytes=100)
    with pytest.raises(ValueError):
        safe_json_loads("1" + "0" * 5000)


def test_cwe502_tag_reconstruction_only_from_allowlist():
    # CWE-502: the tag path reconstructs only pre-registered classes; an unknown
    # tag is refused, so an attacker cannot name an arbitrary class or module.
    from nltk.jsontags import JSONTaggedDecoder

    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode('{"!nltk.evil.RCE": {"cmd": "x"}}')


def test_cwe20_input_type_validation_is_a_clean_type_error():
    # CWE-20: a non str/bytes input fails at the chokepoint with a clear
    # TypeError rather than slipping into the size/scan path.
    from nltk.jsontags import safe_json_loads

    for bad in (None, 123, [1, 2], {"a": 1}, memoryview(b'{"a":1}')):
        with pytest.raises(TypeError, match="expected str or bytes"):
            safe_json_loads(bad)
    # bytes and bytearray are valid and parse.
    assert safe_json_loads(b'{"a": 1}') == {"a": 1}
    assert safe_json_loads(bytearray(b'{"a": 1}')) == {"a": 1}


def test_unicode_forms_parse_or_reject_but_never_crash():
    from nltk.jsontags import safe_json_loads

    # Standard json: lone surrogates, escaped null and bidi controls parse to a
    # str (inert data); an invalid \x escape, a \U escape and a byte-order mark
    # are rejected. None crash.
    assert isinstance(safe_json_loads(r'"\ud800"'), str)  # lone high surrogate
    assert isinstance(safe_json_loads(r'"\udc00"'), str)  # lone low surrogate
    assert safe_json_loads('"a\\u0000b"') == "a\x00b"
    assert safe_json_loads('"x\\u202ey"') == "x‮y"  # RTL override
    for bad in (r'"\x41"', r'"\U0001F600"', '﻿{"a":1}'):
        with pytest.raises(ValueError):
            safe_json_loads(bad)


def test_scanner_hidden_brackets_never_undercount_or_bypass():
    from nltk.jsontags import _scan_json_depth, safe_json_loads

    # Brackets buried in a CLOSED string are correctly counted (real brackets
    # after it are not lost), and an UNTERMINATED string that hides brackets is
    # invalid json and rejected by json.loads, so neither bypasses the guard.
    escaped = '"\\""' + "[" * 5000 + "]" * 5000
    assert _scan_json_depth(escaped, 10**9) == 5000
    with pytest.raises(ValueError):
        safe_json_loads(escaped)
    unterminated = '"' + "[" * 5000  # never closed
    assert _scan_json_depth(unterminated, 10**9) == 0
    with pytest.raises(ValueError):
        safe_json_loads(unterminated)
    # Brackets entirely inside a valid string are a depth-0 string value.
    assert safe_json_loads('"' + "[" * 500 + "]" * 500 + '"') == "[" * 500 + "]" * 500


def test_extreme_bound_parameters_fail_closed():
    from nltk.jsontags import safe_json_loads

    assert safe_json_loads("1", max_depth=0) == 1  # flat is within depth 0
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads("[1]", max_depth=0)
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads("1", max_bytes=-1)
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads("[1]", max_depth=-5)


def test_encoder_circular_reference_is_refused_not_infinite():
    # The encode side must not spin forever on a self-referential object; json's
    # circular-reference check turns it into a bounded ValueError.
    import json as _json

    from nltk.jsontags import JSONTaggedEncoder

    cyclic = {}
    cyclic["self"] = cyclic
    with pytest.raises(ValueError):
        _json.dumps(cyclic, cls=JSONTaggedEncoder)


def test_stream_partial_reads_fail_closed_not_bypass():
    # A stream that returns short partial reads truncates the document; the
    # single bounded read then hands json.loads an incomplete document, which is
    # refused. It cannot be used to smuggle more than max_bytes past the cap.
    from nltk.jsontags import safe_json_load

    class PartialStream:
        def __init__(self, data):
            self.data = data
            self.pos = 0

        def read(self, n=-1):
            chunk = self.data[self.pos : self.pos + 3]
            self.pos += 3
            return chunk

    with pytest.raises(ValueError):
        safe_json_load(PartialStream('{"abcdefgh": 1}'))


def test_leading_whitespace_flood_is_bounded_by_size():
    # A flood of insignificant whitespace is O(n) to skip and bounded by the byte
    # cap, so it neither hangs nor slips past the guard.
    from nltk.jsontags import safe_json_loads

    assert safe_json_loads(" " * 200_000 + "1") == 1
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads(" " * 200 + "1", max_bytes=100)


# ==========================================================================
# Wider-ecosystem JSON CVE/CWE classes (Python stdlib, ujson, jackson /
# fastjson / Newtonsoft polymorphic deserialization, hash-collision DoS),
# confirmed against the same chokepoint.
# ==========================================================================


def test_hash_collision_object_is_linear_not_quadratic():
    # CVE-2011-4815 class: a huge key set. Python's randomized SipHash and the
    # size cap keep insertion linear, so a many-key object is bounded, not a
    # quadratic hash-collision DoS.
    from nltk.jsontags import safe_json_loads

    payload = "{" + ",".join(f'"{i}":0' for i in range(200_000)) + "}"
    parsed = safe_json_loads(payload)
    assert len(parsed) == 200_000


def test_mixed_array_object_deep_nesting_refused():
    # CVE-2021-45958 class (ujson deep-nesting stack overflow): the scanner
    # counts both '[' and '{', so an alternating [{ tower is bounded too.
    from nltk.jsontags import JSON_MAX_DEPTH, safe_json_loads

    d = JSON_MAX_DEPTH + 50
    payload = '{"a":[' * (d // 2) + "1" + "]}" * (d // 2)
    with pytest.raises(ValueError, match="nesting depth"):
        safe_json_loads(payload)


def test_trailing_and_concatenated_data_refused():
    # Parser-differential smuggling: trailing, leading or concatenated documents
    # are rejected, so two parsers cannot disagree on the value.
    from nltk.jsontags import safe_json_loads

    for payload in ('{"a":1}garbage', '{"a":1}{"b":2}', "[1,2]  [3,4]", 'x{"a":1}'):
        with pytest.raises(ValueError):
            safe_json_loads(payload)


def test_non_rfc_number_syntax_refused():
    # RFC-8259 strictness: leading zeros, a leading '+', a bare or trailing dot,
    # hex/octal/underscore literals and a digitless exponent are all refused
    # (each is accepted by some other language's parser, a smuggling risk).
    from nltk.jsontags import safe_json_loads

    for payload in ("01", "+1", ".5", "1.", "0x1F", "0o17", "1_000", "1e", "--1"):
        with pytest.raises(ValueError):
            safe_json_loads(payload)
    # Negative zero is valid JSON and parses to 0.
    assert safe_json_loads("-0") == 0


def test_nested_tag_bomb_via_tagged_decoder_refused():
    # CWE-502 (jackson / fastjson / Newtonsoft polymorphic-deserialization
    # class): a tower of single-key '!'-tag objects is bounded by the tagged
    # decoder's depth cap, never unbounded reconstruction.
    from nltk.jsontags import JSONTaggedDecoder

    payload = '{"!x":' * 300 + "1" + "}" * 300
    with pytest.raises(ValueError):
        JSONTaggedDecoder().decode(payload)


def test_huge_single_token_is_size_bounded():
    # A single enormous string or number token is bounded by the byte cap, not
    # unbounded (CWE-400 / CWE-789).
    from nltk.jsontags import safe_json_loads

    with pytest.raises(ValueError, match="over the"):
        safe_json_loads('"' + "a" * 1000 + '"', max_bytes=200)
    # A large-but-under-cap token still parses.
    assert safe_json_loads('"' + "a" * 5000 + '"') == "a" * 5000


# ==========================================================================
# The byte cap is a BYTE cap, not a code-point cap. A non-ASCII str has more
# UTF-8 bytes than code points, so counting len() on a str would let an
# oversized multibyte payload slip past (a memory-exhaustion bypass). Every
# entry point measures the encoded byte length.
# ==========================================================================


def test_byte_cap_counts_utf8_bytes_not_code_points_loads():
    # 40 '€' code points are 120 UTF-8 bytes: under a 60-code-point count but
    # over a 60-byte cap, so it must be refused, and the reported size is bytes.
    from nltk.jsontags import safe_json_loads

    payload = '"' + "€" * 40 + '"'
    assert len(payload) < 60 < len(payload.encode("utf-8"))
    with pytest.raises(ValueError, match="122 bytes, over the 60-byte"):
        safe_json_loads(payload, max_bytes=60)
    # bytes input is already byte-measured, and a small non-ASCII doc still loads.
    assert safe_json_loads('{"c": "€"}') == {"c": "€"}
    assert safe_json_loads('{"c": "€"}'.encode()) == {"c": "€"}


def test_byte_cap_counts_utf8_bytes_not_code_points_decoder():
    # Same for JSONTaggedDecoder.decode: the argument is a str, so len() would
    # undercount a multibyte document handed to the recursive C accelerator.
    from nltk.jsontags import JSONTaggedDecoder

    decoder = JSONTaggedDecoder()
    decoder.MAX_DECODE_BYTES = 60
    payload = '"' + "€" * 40 + '"'
    with pytest.raises(ValueError, match="122 bytes, over the 60-byte"):
        decoder.decode(payload)


def test_byte_cap_counts_utf8_bytes_not_code_points_stream():
    # And for safe_json_load: a text stream's read(n) counts characters, so the
    # cap is enforced on the encoded byte length (via the binary buffer when the
    # stream exposes one). A multibyte doc over the byte cap is refused.
    from nltk.jsontags import safe_json_load

    payload = '"' + "€" * 40 + '"'
    raw = payload.encode("utf-8")
    text_stream = io.TextIOWrapper(io.BytesIO(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="exceeds the|over the"):
        safe_json_load(text_stream, max_bytes=60)
    # A binary stream is byte-measured directly, and an under-cap doc still loads.
    assert safe_json_load(io.BytesIO('{"c": "€"}'.encode())) == {"c": "€"}


def test_decompression_bomb_feeding_json_is_size_bounded():
    # CWE-409: a small gzip blob inflates to a huge JSON document. Whatever
    # decompresses it hands the inflated bytes to the chokepoint, where the byte
    # cap refuses them before the recursive parse runs. (nltk.data's gz path also
    # bounds the inflate itself; this proves the chokepoint is a second wall.)
    from nltk.jsontags import safe_json_load, safe_json_loads

    inflated = '"' + "a" * 2_000_000 + '"'
    compressed = gzip.compress(inflated.encode("utf-8"))
    assert len(compressed) < len(inflated) // 10  # genuinely a bomb
    decompressed = gzip.decompress(compressed)
    with pytest.raises(ValueError, match="over the"):
        safe_json_loads(decompressed, max_bytes=1000)
    with pytest.raises(ValueError, match="exceeds the|over the"):
        safe_json_load(io.BytesIO(decompressed), max_bytes=1000)


def test_jsonpickle_style_py_object_tag_is_inert_not_resolved():
    # CWE-502 (jsonpickle / jackson polymorphic-typing class): a document that
    # mimics another framework's type hints (``py/object``, ``py/reduce``,
    # ``__reduce__``) carries no nltk '!' tag, so the tagged decoder returns it
    # as a plain dict of inert data. No class is named, resolved or constructed.
    from nltk.jsontags import JSONTaggedDecoder

    for payload in (
        '{"py/object": "os.system", "args": ["id"]}',
        '{"py/reduce": [{"py/type": "os.system"}, ["id"]]}',
        '{"__reduce__": ["subprocess.Popen", ["sh"]]}',
    ):
        result = JSONTaggedDecoder().decode(payload)
        assert isinstance(result, dict)
    # And a single-key object whose key merely LOOKS tag-like but is unregistered
    # is refused, never resolved to an arbitrary class.
    with pytest.raises(ValueError, match="Unknown tag"):
        JSONTaggedDecoder().decode('{"!os.system": ["id"]}')


# ==========================================================================
# CI guard (tools/check_all_json_through_jsontags.py): it is the structural
# enforcement that keeps every future JSON read on the chokepoint, so its
# bypasses are part of the attack surface. Load the real guard module and drive
# its AST visitor over each import/call shape that must (or must not) be flagged.
# ==========================================================================


def _load_json_guard():
    path = os.path.join(REPO_ROOT, "tools", "check_all_json_through_jsontags.py")
    if not os.path.exists(path):
        pytest.skip("guard script is only present in a source checkout")
    spec = importlib.util.spec_from_file_location("_nltk_json_guard", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _guard_flags(guard, source):
    visitor = guard._JsonCallVisitor("<test>", set())
    visitor.visit(ast.parse(source))
    return visitor.violations


@pytest.mark.parametrize(
    "source",
    [
        "import json\njson.loads(x)",
        "import json as j\nj.load(x)",
        "from json import loads\nloads(x)",
        "from json import loads as L\nL(x)",
        # Bypasses the reviewer flagged: submodule import-from, import-as, a
        # dotted attribute chain, and a bare submodule import.
        "from json.decoder import JSONDecoder\nJSONDecoder().decode(x)",
        "from json.decoder import JSONDecoder as JD\nJD().decode(x)",
        "import json.decoder as jd\njd.JSONDecoder().decode(x)",
        "import json.decoder\njson.decoder.JSONDecoder().decode(x)",
        "from json import decoder\ndecoder.JSONDecoder().decode(x)",
        "from json import *\nloads(x)",
        # Drop-in accelerators are guarded the same way.
        "import ujson\nujson.loads(x)",
        "import simplejson as json\njson.load(x)",
    ],
)
def test_json_guard_flags_every_bare_deserialization_shape(source):
    guard = _load_json_guard()
    assert _guard_flags(guard, source), f"guard missed a bypass:\n{source}"


@pytest.mark.parametrize(
    "source",
    [
        "obj.load(x)",  # a load() method on some unrelated object
        "import pickle\npickle.load(x)",  # a different (separately guarded) module
        "import yaml\nyaml.safe_load(x)",
        "import json\njson.dumps(x)",  # serialization is not guarded
        "import json\njson.dump(x, fp)",
        "self.json.loads(x)",  # attribute named json on some object, not the module
        "from nltk.jsontags import safe_json_loads\nsafe_json_loads(x)",  # the wrapper
    ],
)
def test_json_guard_ignores_legitimate_shapes(source):
    guard = _load_json_guard()
    assert not _guard_flags(guard, source), f"guard false-positived:\n{source}"


def test_json_guard_passes_clean_on_the_shipped_tree(monkeypatch):
    # The guard must still report zero violations on the real package after being
    # strengthened, so the new bypass coverage did not introduce a false positive.
    # Run it in-process (no subprocess) with cwd at the repo root so its relative
    # GUARDED_PATHS resolve.
    guard = _load_json_guard()
    monkeypatch.chdir(REPO_ROOT)
    assert guard.main() == 0

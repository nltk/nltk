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


# ===========================================================================
# In-process unit checks on the shared chokepoint (safe_json_load / _loads).
# Every caller funnels through these, so a bounded rejection here is inherited
# everywhere. None of these can crash the interpreter, so no subprocess needed.
# ===========================================================================


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


# ===========================================================================
# Teeth: the stock decoder hard-crashes on the same payload, proving the guard
# above is non-vacuous. And the guard survives that payload with the recursion
# limit lifted.
# ===========================================================================


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
    # Without the depth guard the raw parse never completes cleanly. On Python
    # < 3.12 with a raised recursion limit the C recursion overflows into a fatal
    # SIGSEGV; on 3.12+ the new C-stack check turns the same input into a
    # RecursionError. Either way it is not safely parsable, which is exactly what
    # the bounded loader closes by rejecting it before parsing.
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


# ===========================================================================
# Real caller paths, each with the recursion limit lifted so a leak would
# surface as a crash. Each site: hostile -> bounded rejection, no crash; and a
# benign control that loads and works.
# ===========================================================================


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
    # The format="json" tag gate is pre-existing and rejects every plain object;
    # the point here is that the guarded parse SUCCEEDS (the object is fully
    # parsed) and behavior is unchanged: the same tag-gate error is raised, not
    # a JSON parse failure.
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

#!/usr/bin/env python
"""Benchmark the hot paths touched by the fork's optimizations.

Run it once per tree (``PYTHONPATH`` selects which nltk is imported) and
compare the JSON outputs with ``tools/benchmark_dashboard.py``::

    PYTHONPATH=/path/to/baseline python tools/benchmark_optimizations.py \
        --label baseline --out baseline.json
    PYTHONPATH=/path/to/fork python tools/benchmark_optimizations.py \
        --label optimized --out optimized.json

Each workload records four metrics: median wall time, throughput, peak
memory (tracemalloc) and Python function calls (cProfile), plus a sha256
fingerprint of its output so the two trees can be checked for identical
results. Corpora used: gutenberg, treebank, brown, punkt_tab,
averaged_perceptron_tagger_eng (``nltk.download``).
"""

import argparse
import cProfile
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import tracemalloc


def fingerprint(obj):
    return hashlib.sha256(repr(obj).encode("utf-8")).hexdigest()[:16]


def _text():
    from nltk.corpus import gutenberg

    return gutenberg.raw("austen-emma.txt")[:200_000]


# --- workloads -------------------------------------------------------------
# name -> (setup() -> state, run(state) -> result, unit, count(state, result))


def w_word_tokenize():
    from nltk.tokenize import word_tokenize

    text = _text()
    return (lambda: word_tokenize(text)), "tokens", lambda r: len(r)


def w_porter():
    from nltk.stem import PorterStemmer

    words = _text().split()
    st = PorterStemmer()
    return (lambda: [st.stem(w) for w in words]), "words", lambda r: len(r)


def w_snowball():
    from nltk.stem import SnowballStemmer

    words = _text().split()
    st = SnowballStemmer("english")
    return (lambda: [st.stem(w) for w in words]), "words", lambda r: len(r)


def w_pos_tag():
    from nltk import pos_tag

    toks = _text().split()[:30_000]
    return (lambda: pos_tag(toks)), "tokens", lambda r: len(r)


def w_edit_distance():
    from nltk.metrics import edit_distance

    ws = _text().split()[:400]
    pairs = [(a, b) for a in ws for b in ws[:40]]
    return (
        (lambda: [edit_distance(a, b) for a, b in pairs]),
        "pairs",
        lambda r: len(r),
    )


def w_treebank():
    from nltk.corpus import treebank

    treebank.fileids()  # resolve the corpus once, outside the timed region
    return (
        (lambda: [len(t.leaves()) for t in treebank.parsed_sents()]),
        "sentences",
        lambda r: len(r),
    )


def w_brown():
    from nltk.corpus import brown

    brown.fileids()
    return (lambda: len(brown.tagged_words())), "words", lambda r: r


WORKLOADS = {
    "word_tokenize": ("word_tokenize (control, unchanged code)", w_word_tokenize),
    "porter_stem": ("PorterStemmer.stem", w_porter),
    "snowball_stem": ("SnowballStemmer('english').stem", w_snowball),
    "pos_tag": ("pos_tag (averaged perceptron)", w_pos_tag),
    "edit_distance": ("edit_distance", w_edit_distance),
    "treebank_parsed_sents": ("treebank.parsed_sents (corpus reader)", w_treebank),
    "brown_tagged_words": ("len(brown.tagged_words()) (corpus reader)", w_brown),
}


def bench_import(repeats):
    """Import time of ``nltk`` in a fresh interpreter (median of ``repeats``)."""
    code = (
        "import sys, time; t=time.perf_counter(); import nltk; "
        "print(time.perf_counter()-t, len(sys.modules))"
    )
    times, mods = [], 0
    for _ in range(repeats):
        out = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        ).stdout.split()
        times.append(float(out[0]))
        mods = int(out[1])
    return {
        "label": "import nltk",
        "median_s": statistics.median(times),
        "min_s": min(times),
        "runs": times,
        "modules_loaded": mods,
    }


def bench(name, repeats):
    label, factory = WORKLOADS[name]
    run, unit, count = factory()
    run()  # warm caches (lazy corpus loads, file cache)
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        result = run()
        times.append(time.perf_counter() - t)
    n = count(result)
    median = statistics.median(times)

    tracemalloc.start()
    run()
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    prof = cProfile.Profile()
    prof.enable()
    run()
    prof.disable()
    calls = sum(e.callcount for e in prof.getstats())

    return {
        "label": label,
        "median_s": median,
        "min_s": min(times),
        "runs": times,
        "unit": unit,
        "count": n,
        "throughput": n / median,
        "peak_mem_mb": peak / 1e6,
        "function_calls": calls,
        "fingerprint": fingerprint(result),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--repeats", type=int, default=7)
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default="benchmark.json")
    ap.add_argument("--only", nargs="*", choices=list(WORKLOADS))
    args = ap.parse_args()

    import nltk

    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=os.path.dirname(nltk.__file__),
        capture_output=True,
        text=True,
    ).stdout.strip()

    results = {
        "label": args.label,
        "commit": commit,
        "nltk_path": os.path.dirname(nltk.__file__),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "repeats": args.repeats,
        "import": bench_import(args.repeats),
        "workloads": {},
    }
    print(f"[{args.label}] import nltk: {results['import']['median_s']*1000:.1f} ms")
    for name in args.only or WORKLOADS:
        r = bench(name, args.repeats)
        results["workloads"][name] = r
        print(
            f"[{args.label}] {name}: {r['median_s']*1000:.1f} ms, "
            f"{r['throughput']:,.0f} {r['unit']}/s, {r['peak_mem_mb']:.1f} MB peak, "
            f"{r['function_calls']:,} calls, fp={r['fingerprint']}"
        )
    with open(args.out, "w") as f:
        json.dump(results, f, indent=2)
    print("wrote", args.out)


if __name__ == "__main__":
    main()

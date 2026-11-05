"""
Parse with every feature grammar in nltk_data on two NLTK trees and compare.

A change to feature unification or to the feature chart rules must leave the
parsers' output exactly as it was. This tool parses the same sentences with a
base tree and a changed tree, and compares every edge of every chart and every
tree, in order. It also records the CPU time of each parse, so the comparison
doubles as a benchmark.

The work is the Alvey grammar's 229 test sentences under four feature
parsers (bottom-up left-corner, bottom-up, top-down and Earley), and every
other ``.fcfg`` grammar in nltk_data under all nine feature parsers, on
sentences generated from the grammar::

    python tools/check_feature_parsers.py items ITEMS.json
    python tools/check_feature_parsers.py run TREE ITEMS.json OUT.jsonl --shard 0/16
    python tools/check_feature_parsers.py compare ITEMS.json BASE CHANGE [--summary MD]

``run`` writes one JSON row per parse and skips rows already in OUT. BASE and
CHANGE are glob patterns of row files, such as ``rows/*/base.jsonl``; ``compare``
exits 1 if a parse is missing from either side or if any two rows disagree.
"""

import argparse
import glob
import hashlib
import itertools
import json
import os
import pathlib
import re
import sys
import time
import warnings
from collections import defaultdict
from multiprocessing import Pool

ALVEY = "grammars/large_grammars/alvey.fcfg"
ALVEY_SENTENCES = "grammars/large_grammars/alvey_sentences.txt"

#: The strategies run on Alvey; its top-down parses take minutes a sentence.
ALVEY_PARSERS = (
    "FeatureChartParser",
    "FeatureBottomUpChartParser",
    "FeatureTopDownChartParser",
    "FeatureEarleyChartParser",
)

#: Every feature chart parser, run on the other grammars.
ALL_PARSERS = (
    "FeatureChartParser",
    "FeatureBottomUpChartParser",
    "FeatureBottomUpLeftCornerChartParser",
    "FeatureTopDownChartParser",
    "FeatureIncrementalChartParser",
    "FeatureEarleyChartParser",
    "FeatureIncrementalTopDownChartParser",
    "FeatureIncrementalBottomUpChartParser",
    "FeatureIncrementalBottomUpLeftCornerChartParser",
)

#: Relative cost of each parser on Alvey, measured on its longest sentence.
COST = {"FeatureTopDownChartParser": 5, "FeatureEarleyChartParser": 5}

#: Sentences taken from each generated language, spread over its first GENERATED.
SAMPLE, GENERATED, DEPTH = 50, 5000, 8

#: The fields two rows of the same parse must agree on.
FIELDS = ("error", "edges", "edges_sha", "trees", "trees_sha")


def _load_kwargs(name):
    if name.endswith("/drt.fcfg"):
        from nltk.sem.drt import DrtParser

        return {"logic_parser": DrtParser()}
    return {}


def _grammars():
    """Every feature grammar in nltk_data, by its resource name."""
    import nltk

    names = set()
    for root in map(pathlib.Path, nltk.data.path):
        for path in root.glob("grammars/**/*.fcfg"):
            names.add(path.relative_to(root).as_posix())
    return sorted(names)


def _generated(grammar):
    from nltk.parse.generate import generate

    sentences = []
    try:
        for words in itertools.islice(generate(grammar, depth=DEPTH), GENERATED):
            sentences.append(words)
    except RecursionError:
        pass
    step = max(1, len(sentences) // SAMPLE)
    return sentences[::step][:SAMPLE]


def items(out):
    import nltk
    from nltk.parse.util import extract_test_sentences

    work, unloadable = [], {}
    for name in _grammars():
        try:
            grammar = nltk.data.load(name, **_load_kwargs(name))
        except Exception as e:
            unloadable[name] = f"{type(e).__name__}: {e}"[:200]
            continue
        if name == ALVEY:
            text = nltk.data.load(ALVEY_SENTENCES)
            sentences = [words for words, _ in extract_test_sentences(text)]
            parsers = ALVEY_PARSERS
        else:
            sentences, parsers = _generated(grammar), ALL_PARSERS
        for parser in parsers:
            for index, words in enumerate(sentences):
                cost = COST.get(parser, 1) * len(words) ** 3
                if name != ALVEY:
                    cost = len(words)
                work.append(
                    {
                        "id": f"{name} {parser} {index}",
                        "grammar": name,
                        "parser": parser,
                        "words": words,
                        "cost": cost,
                    }
                )
    if not any(item["grammar"] == ALVEY for item in work):
        sys.exit(f"{ALVEY} is not installed")
    # Costliest first, dealt round the shards, so each gets a like share.
    work.sort(key=lambda item: (-item["cost"], item["id"]))
    with open(out, "w") as f:
        json.dump({"items": work, "unloadable": unloadable}, f, indent=1)
    print(f"{len(work)} parses of {len({i['grammar'] for i in work})} grammars")
    for name, error in unloadable.items():
        print(f"  not loadable: {name}: {error}")


def _shard(work, shard):
    index, count = map(int, shard.split("/"))
    return [item for k, item in enumerate(work) if k % count == index]


def _sha(lines):
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf8") + b"\n")
    return digest.hexdigest()


def _init(tree):
    global _cache, _COUNTERS
    _cache = {}
    sys.path.insert(0, tree)
    warnings.simplefilter("ignore")
    import nltk
    from nltk.sem import linearlogic, logic

    found = pathlib.Path(nltk.__file__).resolve()
    if pathlib.Path(tree).resolve() not in found.parents:
        raise SystemExit(f"nltk came from {found}, not from {tree}")
    _COUNTERS = (logic._counter, linearlogic._counter)


def _parse(item):
    import nltk
    from nltk.parse import earleychart, featurechart

    name = item["grammar"]
    if name not in _cache:
        _cache[name] = nltk.data.load(name, **_load_kwargs(name))
    grammar = _cache[name]
    module = featurechart if hasattr(featurechart, item["parser"]) else earleychart
    parser = getattr(module, item["parser"])(grammar, max_time=None)
    row = {"id": item["id"]}
    # Fresh variables of logic expressions are numbered by counters that live
    # across parses; start them over, so a parse can't depend on the one before.
    for counter in _COUNTERS:
        counter._value = 0
    start = time.process_time()
    try:
        chart = parser.chart_parse(item["words"])
        trees = [str(tree) for tree in chart.parses(grammar.start())]
    except Exception as e:
        # Addresses differ from run to run; the error itself must not.
        row["error"] = re.sub(r"0x[0-9a-f]+", "0x", f"{type(e).__name__}: {e}")[:500]
        row["cpu"] = round(time.process_time() - start, 3)
        return row
    row["cpu"] = round(time.process_time() - start, 3)
    edges = sorted(str(edge) for edge in chart.edges())
    row.update(
        error=None,
        edges=len(edges),
        edges_sha=_sha(edges),
        trees=len(trees),
        trees_sha=_sha(trees),
    )
    return row


def run(tree, items_file, out, shard, jobs):
    with open(items_file) as f:
        work = _shard(json.load(f)["items"], shard)
    done = set()
    if os.path.exists(out):
        with open(out) as f:
            done = {json.loads(line)["id"] for line in f if line.strip()}
    todo = [item for item in work if item["id"] not in done]
    start = time.time()
    with Pool(jobs, initializer=_init, initargs=(tree,)) as pool, open(out, "a") as f:
        for row in pool.imap_unordered(_parse, todo):
            f.write(json.dumps(row) + "\n")
            f.flush()
    print(f"{tree}: {len(todo)} parses in {time.time() - start:.0f}s into {out}")


def _rows(pattern):
    paths = sorted(glob.glob(pattern, recursive=True))
    if not paths:
        sys.exit(f"no row files match {pattern}")
    rows = {}
    for p in paths:
        with open(p) as f:
            for line in f:
                if line.strip():
                    row = json.loads(line)
                    rows[row["id"]] = row
    return rows


def compare(items_file, base_path, change_path, shard, summary):
    with open(items_file) as f:
        work = json.load(f)["items"]
    if shard:
        work = _shard(work, shard)
    base, change = _rows(base_path), _rows(change_path)
    missing = [
        (side, item["id"])
        for item in work
        for side, rows in (("base", base), ("change", change))
        if item["id"] not in rows
    ]
    departures = [
        (item["id"], field, base[item["id"]].get(field), change[item["id"]].get(field))
        for item in work
        if item["id"] in base and item["id"] in change
        for field in FIELDS
        if base[item["id"]].get(field) != change[item["id"]].get(field)
    ]
    cpu = defaultdict(lambda: [0.0, 0.0, 0])
    for item in work:
        if item["id"] in base and item["id"] in change:
            key = (item["grammar"].rsplit("/", 1)[-1], item["parser"])
            cpu[key][0] += base[item["id"]]["cpu"]
            cpu[key][1] += change[item["id"]]["cpu"]
            cpu[key][2] += 1
    lines = [
        f"{len(work)} parses: {len(missing)} missing, {len(departures)} departures",
        "",
        "| grammar | parser | parses | base CPU s | change CPU s | speedup |",
        "|---|---|---:|---:|---:|---:|",
    ]
    total = [0.0, 0.0, 0]
    for (grammar, parser), (b, c, n) in sorted(cpu.items()):
        lines.append(
            f"| {grammar} | {parser} | {n} | {b:.1f} | {c:.1f} | {b / c if c else 0:.2f}x |"
        )
        total = [total[0] + b, total[1] + c, total[2] + n]
    b, c, n = total
    lines.append(f"| **all** | | {n} | {b:.1f} | {c:.1f} | {b / c if c else 0:.2f}x |")
    for side, item_id in missing[:50]:
        lines.append(f"- missing from {side}: {item_id}")
    for item_id, field, was, now in departures[:50]:
        lines.append(f"- departure: {item_id}: {field} {was!r} -> {now!r}")
    text = "\n".join(lines)
    print(text)
    if summary:
        with open(summary, "a") as f:
            f.write(text + "\n")
    return 1 if missing or departures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("items")
    p.add_argument("out")
    p = sub.add_parser("run")
    p.add_argument("tree")
    p.add_argument("items")
    p.add_argument("out")
    p.add_argument("--shard", default="0/1")
    p.add_argument("--jobs", type=int, default=os.cpu_count())
    p = sub.add_parser("compare")
    p.add_argument("items")
    p.add_argument("base")
    p.add_argument("change")
    p.add_argument("--shard")
    p.add_argument("--summary")
    args = ap.parse_args()
    if args.command == "items":
        _init(os.getcwd())
        items(args.out)
    elif args.command == "run":
        run(args.tree, args.items, args.out, args.shard, args.jobs)
    else:
        sys.exit(compare(args.items, args.base, args.change, args.shard, args.summary))


if __name__ == "__main__":
    main()

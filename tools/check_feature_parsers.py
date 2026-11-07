"""
Parse with every feature grammar in nltk_data and check the output.

A change to feature unification or to the feature chart rules must leave the
parsers' output exactly as it was. This tool parses the same sentences on an
NLTK tree and checks every edge of every chart and every tree, in order: against
the answers pinned in ``feature_parser_answers.json``, or against another tree.
It records the CPU time of each parse, so a comparison of two trees doubles as
a benchmark.

The work is the Alvey grammar's 229 test sentences under four feature
parsers (bottom-up left-corner, bottom-up, top-down and Earley), and every
other ``.fcfg`` grammar in nltk_data under all nine feature parsers, on
sentences generated from the grammar::

    python tools/check_feature_parsers.py items ITEMS.json [--family chart|incremental]
    python tools/check_feature_parsers.py run TREE ITEMS.json ROWS.jsonl
    python tools/check_feature_parsers.py check ITEMS.json ROWS.jsonl [--summary MD]
    python tools/check_feature_parsers.py compare ITEMS.json BASE CHANGE [--summary MD]
    python tools/check_feature_parsers.py pin ITEMS.json ROWS.jsonl

``run`` writes one JSON row per parse and skips rows already in ROWS. ``check``
exits 1 if a parse is missing, if a grammar's rows under a parser differ from
the pinned answers, or if a grammar loads or fails to load other than pinned; ``compare`` exits 1 if a parse is missing from either tree
or if any two rows disagree. ``pin`` writes the answers from rows of a tree
whose output is right. Row arguments are glob patterns, such as
``rows/*/base.jsonl``.
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

#: The parsers in two families, a CI job each: the chart parsers of
#: featurechart.py and the incremental ones of earleychart.py.
FAMILIES = {
    "chart": (
        "FeatureChartParser",
        "FeatureBottomUpChartParser",
        "FeatureBottomUpLeftCornerChartParser",
        "FeatureTopDownChartParser",
    ),
    "incremental": (
        "FeatureIncrementalChartParser",
        "FeatureEarleyChartParser",
        "FeatureIncrementalTopDownChartParser",
        "FeatureIncrementalBottomUpChartParser",
        "FeatureIncrementalBottomUpLeftCornerChartParser",
    ),
}
assert sorted(sum(FAMILIES.values(), ())) == sorted(ALL_PARSERS)

ANSWERS = pathlib.Path(__file__).with_name("feature_parser_answers.json")

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


def items(out, family=None):
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
            if family and parser not in FAMILIES[family]:
                continue
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
    # Costliest first, so the last parses to finish are short ones.
    work.sort(key=lambda item: (-item["cost"], item["id"]))
    with open(out, "w") as f:
        json.dump(
            {"items": work, "unloadable": unloadable, "family": family}, f, indent=1
        )
    print(f"{len(work)} parses of {len({i['grammar'] for i in work})} grammars")
    for name, error in unloadable.items():
        print(f"  does not load: {name}: {error}")


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


def run(tree, items_file, out, jobs):
    with open(items_file) as f:
        work = json.load(f)["items"]
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


def _report(text, summary):
    print(text)
    if summary:
        with open(summary, "a") as f:
            f.write(text + "\n")


def _groups(work):
    groups = defaultdict(list)
    for item in work:
        groups[f"{item['grammar']} {item['parser']}"].append(item["id"])
    return groups


def _digests(work, rows):
    """One digest per grammar and parser, over its rows in id order."""
    digests = {}
    for key, ids in sorted(_groups(work).items()):
        lines = [
            json.dumps([i] + [rows.get(i, {}).get(field) for field in FIELDS])
            for i in sorted(ids)
        ]
        digests[key] = {"parses": len(ids), "sha256": _sha(lines)}
    return digests


def pin(items_file, rows_path):
    with open(items_file) as f:
        listed = json.load(f)
    work = listed["items"]
    if listed.get("family"):
        sys.exit("pin from the items of every parser, not of one family")
    rows = _rows(rows_path)
    missing = [item["id"] for item in work if item["id"] not in rows]
    if missing:
        sys.exit(f"{len(missing)} parses have no row, such as {missing[0]}")
    # a grammar that does not load is pinned too, with its error, not skipped
    answers = {"groups": _digests(work, rows), "unloadable": listed["unloadable"]}
    with open(ANSWERS, "w") as f:
        json.dump(answers, f, indent=1, sort_keys=True)
        f.write("\n")
    print(f"pinned {len(work)} parses and {len(listed['unloadable'])} failed loads")


def check(items_file, rows_path, summary):
    with open(items_file) as f:
        listed = json.load(f)
    work, unloadable = listed["items"], listed["unloadable"]
    rows = _rows(rows_path)
    with open(ANSWERS) as f:
        answers = json.load(f)
    pinned, pinned_unloadable = answers["groups"], answers["unloadable"]
    family = listed.get("family")
    if family:
        # each job checks every pinned group of its own family's parsers
        pinned = {
            k: v for k, v in pinned.items() if k.rsplit(" ", 1)[1] in FAMILIES[family]
        }
    found = _digests(work, rows)
    missing = [item["id"] for item in work if item["id"] not in rows]
    departures = sorted(
        key for key in set(pinned) | set(found) if pinned.get(key) != found.get(key)
    )
    load_departures = sorted(
        name
        for name in set(pinned_unloadable) | set(unloadable)
        if pinned_unloadable.get(name) != unloadable.get(name)
    )
    lines = [
        f"{len(work)} parses: {len(missing)} missing, "
        f"{len(departures)} of {len(pinned)} pinned groups depart; "
        f"{len(unloadable)} grammars do not load, "
        f"{len(load_departures)} of them other than pinned",
        "",
        "| grammar | parser | parses | CPU s |",
        "|---|---|---:|---:|",
    ]
    for key, ids in sorted(_groups(work).items()):
        grammar, parser = key.rsplit("/", 1)[-1].split(" ")
        cpu = sum(rows[i]["cpu"] for i in ids if i in rows)
        lines.append(f"| {grammar} | {parser} | {len(ids)} | {cpu:.1f} |")
    lines += [f"- missing: {item_id}" for item_id in missing[:50]]
    lines += [f"- departs: {key}" for key in departures]
    for name in load_departures:
        was, now = pinned_unloadable.get(name), unloadable.get(name)
        lines.append(f"- loads other than pinned: {name}: {was!r} -> {now!r}")
    _report("\n".join(lines), summary)
    return 1 if missing or departures or load_departures else 0


def compare(items_file, base_path, change_path, summary):
    with open(items_file) as f:
        work = json.load(f)["items"]
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
    _report("\n".join(lines), summary)
    return 1 if missing or departures else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("items")
    p.add_argument("out")
    p.add_argument("--family", choices=sorted(FAMILIES))
    p = sub.add_parser("run")
    p.add_argument("tree")
    p.add_argument("items")
    p.add_argument("out")
    p.add_argument("--jobs", type=int, default=os.cpu_count())
    p = sub.add_parser("check")
    p.add_argument("items")
    p.add_argument("rows")
    p.add_argument("--summary")
    p = sub.add_parser("compare")
    p.add_argument("items")
    p.add_argument("base")
    p.add_argument("change")
    p.add_argument("--summary")
    p = sub.add_parser("pin")
    p.add_argument("items")
    p.add_argument("rows")
    args = ap.parse_args()
    if args.command == "items":
        _init(os.getcwd())
        items(args.out, args.family)
    elif args.command == "run":
        run(args.tree, args.items, args.out, args.jobs)
    elif args.command == "check":
        sys.exit(check(args.items, args.rows, args.summary))
    elif args.command == "compare":
        sys.exit(compare(args.items, args.base, args.change, args.summary))
    else:
        pin(args.items, args.rows)


if __name__ == "__main__":
    main()

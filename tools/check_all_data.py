#!/usr/bin/env python3
# Natural Language Toolkit: every data package and module, base against change
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Read every NLTK data package and import every module, on two trees, and compare.

A unit test opens the few files it was written for, so a change to a shared
loader, reader or bound (a size cap, a depth scan, a sandbox check) can still
break a package that no test reads. This check runs NLTK's own code over the
whole data index, with nothing mocked, once on the base commit and once on the
change, and compares the two runs call by call:

* every file of a package whose format ``nltk.data.load`` recognises (pickle,
  JSON, YAML, grammars, valuations, logic) is loaded in that format, the first
  dozen files are also read raw, and every ``.json`` file is parsed with
  :func:`~nltk.jsontags.safe_json_load`;
* every corpus loader in ``nltk.corpus`` is read: each public method that needs
  no argument, on the whole corpus and on its first three files, plus the
  entry points that need one (WordNet synsets, information content, ...);
* corpora with no loader are read with the reader NLTK has for them, and the
  taggers, tokenizers, chunker, tagsets, VADER, stemmers and chat80 run their
  real pipelines;
* every module under ``nltk`` is imported, and its public names and signatures
  are recorded.

Each call records a digest of a bounded sample of its result and of what it
printed, or the exception it raised. ``compare`` fails when a call that worked
on the base fails, returns something else or is gone on the change, or when a
module that imported no longer does; an intended change of output fails too,
so that it is reviewed. A call that failed on both trees is listed, never
failed on, so a fix shows in the summary.

Usage::

    python tools/check_all_data.py packages TREE OUT.json
    PYTHONHASHSEED=0 python -P -s tools/check_all_data.py run TREE PACKAGES.json OUT.json
    python tools/check_all_data.py compare BASE.json HEAD.json

``run`` refuses to start without a fixed ``PYTHONHASHSEED``: the order of a
set, and of anything a reader builds from one, otherwise changes per process.
"""

import contextlib
import hashlib
import importlib
import inspect
import io
import itertools
import json
import os
import pkgutil
import random
import re
import signal
import sys
import time
import warnings
import xml.etree.ElementTree as ElementTree
import zipfile

#: Seconds one call may take before it is recorded as a timeout.
CALL_SECONDS = 300
#: How many items of a result are hashed, and how many characters of a string.
SAMPLE_ITEMS = 200
SAMPLE_CHARS = 20000
#: How many files of a package are read raw, and of a corpus per method.
RAW_FILES = 12
CORPUS_FILES = 3
SAMPLE_TEXT = (
    "NLTK is a leading platform for building Python programs. "
    "Dr. Smith went to Washington on Jan. 5th."
)

# Reader methods that return file handles, paths or settings, not the corpus.
SKIP_METHODS = {"open", "abspath", "abspaths", "ensure_loaded", "encoding"}
# Read per file only: on the whole corpus it would hash gigabytes.
PER_FILE_ONLY = {"raw"}
_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _canonical(value, tree):
    """A process-independent form of ``value``: sets sorted, addresses dropped."""
    kind = type(value)
    if kind in (str, bytes):
        return value[:SAMPLE_CHARS]
    if value is None or kind in (bool, int, float):
        return value
    if kind in (list, tuple):
        return [_canonical(v, tree) for v in value]
    if kind in (set, frozenset):
        return sorted((_canonical(v, tree) for v in value), key=repr)
    if kind is dict:
        items = ((_canonical(k, tree), _canonical(v, tree)) for k, v in value.items())
        return sorted(items, key=repr)
    if isinstance(value, ElementTree.Element):
        return ElementTree.tostring(value)
    return _ADDRESS.sub("", repr(value)).replace(tree, "<tree>")


def _sample(value):
    """The part of a result that is hashed: a bounded prefix of a sequence."""
    if isinstance(value, (str, bytes, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        keys = itertools.islice(sorted(value, key=repr), SAMPLE_ITEMS)
        return [(k, value[k]) for k in keys]
    try:
        return list(itertools.islice(iter(value), SAMPLE_ITEMS))
    except TypeError:
        return value


def _digest(value, tree):
    text = repr(_canonical(value, tree)).replace(tree, "<tree>")
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()[:16]


class _Run:
    """The calls of one package, recorded as label -> [status, detail, printed, seconds]."""

    def __init__(self, tree):
        self.tree = tree
        self.calls = {}

    def call(self, label, fn):
        while label in self.calls:
            label += "'"
        signal.alarm(CALL_SECONDS)
        start = time.perf_counter()
        try:
            with warnings.catch_warnings(), contextlib.redirect_stdout(
                io.StringIO()
            ) as printed:
                warnings.simplefilter("ignore")
                value = _sample(fn())
            entry = [
                "ok",
                _digest(value, self.tree),
                _digest(printed.getvalue(), self.tree),
            ]
        except _Timeout:
            entry = ["timeout", "", ""]
        except Exception as e:
            message = str(e)[:200].replace(self.tree, "<tree>")
            entry = [type(e).__name__, message, ""]
        finally:
            signal.alarm(0)
        self.calls[label] = entry + [round(time.perf_counter() - start, 2)]
        return entry[0] == "ok"

    def note(self, label, status, detail=""):
        self.calls[label] = [status, detail, "", 0]


def _import_tree(tree):
    sys.path.insert(0, tree)
    import nltk

    where = os.path.realpath(nltk.__file__)
    if not where.startswith(os.path.realpath(tree) + os.sep):
        sys.exit(f"nltk was imported from {where}, not from {tree}")
    return nltk


def _data_roots(nltk):
    return [p for p in nltk.data.path if os.path.isdir(p)]


def _package_files(nltk, subdir, pid):
    """The files of a package, relative to its subdirectory, as NLTK finds them."""
    for root in _data_roots(nltk):
        unzipped = os.path.join(root, subdir, pid)
        archive = unzipped + ".zip"
        if os.path.isdir(unzipped):
            base = os.path.join(root, subdir)
            return sorted(
                os.path.relpath(os.path.join(d, f), base)
                for d, _, files in os.walk(unzipped)
                for f in files
            )
        if os.path.isfile(archive):
            with zipfile.ZipFile(archive) as z:
                return sorted(n for n in z.namelist() if not n.endswith("/"))
    return []


def _corpus_loaders():
    """Package id -> [(name, loader)] for every lazy loader NLTK defines."""
    from nltk.corpus.util import LazyCorpusLoader

    loaders = {}
    for module_name in ("nltk.corpus", "nltk.corpus.europarl_raw"):
        module = importlib.import_module(module_name)
        for name in sorted(dir(module)):
            loader = getattr(module, name, None)
            if isinstance(loader, LazyCorpusLoader):
                pid = vars(loader)["_LazyCorpusLoader__name"].split("/")[0]
                label = name if module_name == "nltk.corpus" else f"europarl_raw.{name}"
                loaders.setdefault(pid, []).append((label, loader))
    return loaders


def _read_corpus(run, label, reader):
    """Every public method of a reader that needs no argument, whole and per file."""
    from nltk.corpus.util import LazyCorpusLoader

    if not run.call(f"{label} loads", lambda: type(reader.fileids and reader).__name__):
        return
    if isinstance(reader, LazyCorpusLoader):
        return
    fileids = []
    try:
        fileids = list(reader.fileids())[:CORPUS_FILES]
    except Exception as e:
        run.note(f"{label}.fileids", type(e).__name__, str(e)[:200])
    for attr in sorted(dir(reader)):
        if attr.startswith("_") or attr in SKIP_METHODS:
            continue
        try:
            method = getattr(reader, attr)
        except Exception as e:
            run.note(f"{label}.{attr}", type(e).__name__, str(e)[:200])
            continue
        if not callable(method) or inspect.isclass(method):
            continue
        try:
            params = list(inspect.signature(method).parameters.values())
        except (TypeError, ValueError):
            continue
        optional = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        if any(p.default is p.empty and p.kind not in optional for p in params):
            continue
        if attr not in PER_FILE_ONLY:
            run.call(f"{label}.{attr}()", method)
        if any(p.name == "fileids" for p in params):
            for fid in fileids:
                run.call(f"{label}.{attr}({fid})", lambda m=method, f=fid: m(fileids=f))


def _all_tweets(reader):
    # every line of every file goes through safe_json_loads, hashed as it is read
    digest, count = hashlib.sha256(), 0
    for fid in reader.fileids():
        for text in reader.strings(fid):
            digest.update(text.encode("utf-8", "surrogatepass"))
            count += 1
    return count, digest.hexdigest()


def _wordnet_calls(reader):
    synsets = reader.synsets("dog")
    return [(s.name(), s.definition(), [l.name() for l in s.lemmas()]) for s in synsets]


def _information_content(reader):
    import nltk

    ic = reader.ic("ic-brown.dat")
    dog, cat = nltk.corpus.wordnet.synset("dog.n.01"), nltk.corpus.wordnet.synset(
        "cat.n.01"
    )
    return [
        dog.res_similarity(cat, ic),
        dog.jcn_similarity(cat, ic),
        dog.lin_similarity(cat, ic),
    ]


# Entry points that need an argument, by loader name.
LOADER_CALLS = {
    "wordnet": [
        ("synsets(dog)", _wordnet_calls),
        (
            "synsets(perro, spa)",
            lambda r: [s.name() for s in r.synsets("perro", lang="spa")],
        ),
        ("langs()", lambda r: sorted(r.langs())),
        (
            "path_similarity",
            lambda r: r.synset("dog.n.01").path_similarity(r.synset("cat.n.01")),
        ),
    ],
    "wordnet31": [("synsets(dog)", _wordnet_calls)],
    "wordnet2021": [("synsets(dog)", _wordnet_calls)],
    "wordnet2022": [("synsets(dog)", _wordnet_calls)],
    "english_wordnet": [("synsets(dog)", _wordnet_calls)],
    "wordnet_ic": [("ic(ic-brown.dat) similarity", _information_content)],
    "sentiwordnet": [
        ("senti_synsets(slow)", lambda r: [str(s) for s in r.senti_synsets("slow")])
    ],
    "ppattach": [
        (
            "attachments(training)",
            lambda r: [str(a) for a in r.attachments("training")[:50]],
        )
    ],
    "stopwords": [("words(english)", lambda r: r.words("english"))],
    "verbnet": [
        ("classids(take)", lambda r: [r.pprint(c) for c in r.classids("take")])
    ],
    "framenet": [
        ("frames(medical)", lambda r: [f.name for f in r.frames(r"(?i)medical")])
    ],
    "lin_thesaurus": [
        ("scored_synonyms(business)", lambda r: r.scored_synonyms("business"))
    ],
    "crubadan": [("lang_freq(en)", lambda r: sorted(r.lang_freq("en").items())[:200])],
    "twitter_samples": [("every tweet", _all_tweets)],
}


def _reader_for(pid):
    """A reader NLTK has for a corpus that no loader in nltk.corpus opens."""
    import nltk
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


def _pipelines(run, pid):
    """The pipelines that read the packages which are not corpora."""
    import nltk

    words = SAMPLE_TEXT.split()
    if pid == "averaged_perceptron_tagger_eng":
        run.call("pos_tag", lambda: nltk.pos_tag(words))
        run.call("pos_tag universal", lambda: nltk.pos_tag(words, tagset="universal"))
    elif pid == "averaged_perceptron_tagger_rus":
        run.call(
            "pos_tag rus", lambda: nltk.pos_tag("Мама мыла раму .".split(), lang="rus")
        )
    elif pid == "universal_tagset":
        run.call(
            "map_tag",
            lambda: [
                nltk.tag.map_tag("en-ptb", "universal", t)
                for t in ("NN", "VBZ", "JJ", ".")
            ],
        )
    elif pid == "punkt_tab":
        from nltk.tokenize import PunktTokenizer

        for root in _data_roots(nltk):
            tables = os.path.join(root, "tokenizers", "punkt_tab")
            if os.path.isdir(tables):
                for lang in sorted(os.listdir(tables)):
                    if os.path.isdir(os.path.join(tables, lang)):
                        run.call(
                            f"punkt {lang}",
                            lambda l=lang: PunktTokenizer(l).tokenize(SAMPLE_TEXT),
                        )
                break
        run.call("word_tokenize", lambda: nltk.word_tokenize(SAMPLE_TEXT))
        run.call("sent_tokenize", lambda: nltk.sent_tokenize(SAMPLE_TEXT))
    elif pid == "maxent_ne_chunker_tab":
        run.call("ne_chunk", lambda: str(nltk.ne_chunk(nltk.pos_tag(words))))
    elif pid == "tagsets_json":
        for name in ("upenn_tagset", "brown_tagset", "claws5_tagset"):
            run.call(name, lambda n=name: getattr(nltk.help, n)("NN.*"))
    elif pid == "vader_lexicon":
        from nltk.sentiment import SentimentIntensityAnalyzer

        run.call(
            "vader",
            lambda: SentimentIntensityAnalyzer().polarity_scores(
                "NLTK is great, but not terrible!"
            ),
        )
    elif pid == "rslp":
        run.call(
            "rslp",
            lambda: [
                nltk.stem.RSLPStemmer().stem(w)
                for w in ("correndo", "meninas", "felizmente")
            ],
        )
    elif pid == "snowball_data":
        snowball = nltk.stem.SnowballStemmer
        run.call(
            "snowball",
            lambda: {l: snowball(l).stem("running") for l in snowball.languages},
        )
    elif pid == "chat80":
        from nltk.sem import chat80

        run.call("concepts", lambda: [str(c) for c in chat80.concepts()])
        run.call(
            "make_valuation",
            lambda: chat80.make_valuation(chat80.concepts(), read=True),
        )
    elif pid == "city_database":
        from nltk.sem import chat80

        run.call(
            "sql_query",
            lambda: list(
                chat80.sql_query(
                    "corpora/city_database/city.db", "SELECT * FROM city_table"
                )
            ),
        )
    elif pid in ("pl196x", "ycoe", "verbnet3"):
        try:
            reader = _reader_for(pid)
        except Exception as e:
            run.note("reader", type(e).__name__, str(e)[:200])
        else:
            _read_corpus(run, type(reader).__name__, reader)


def _check_package(tree, nltk, pkg, loaders):
    run = _Run(tree)
    pid, subdir = pkg["id"], pkg["subdir"]
    files = _package_files(nltk, subdir, pid)
    run.note("files", "ok" if files else "absent", str(len(files)))
    for name in files[:RAW_FILES]:
        run.call(
            f"load raw {name}",
            lambda n=name: nltk.data.load(f"{subdir}/{n}", format="raw", cache=False),
        )
    for name in files:
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if extension in nltk.data.AUTO_FORMATS and extension not in ("txt", "text"):
            run.call(
                f"load {name}",
                lambda n=name: nltk.data.load(f"{subdir}/{n}", cache=False),
            )
        if extension == "json":
            run.call(
                f"safe_json_load {name}",
                lambda n=name: _safe_json(nltk, f"{subdir}/{n}"),
            )
    for label, loader in loaders:
        _read_corpus(run, label, loader)
        for call_label, fn in LOADER_CALLS.get(label, []):
            run.call(f"{label}.{call_label}", lambda f=fn, r=loader: f(r))
    _pipelines(run, pid)
    return run.calls


def _safe_json(nltk, path):
    from nltk.jsontags import safe_json_load

    with nltk.data.find(path).open() as stream:
        return safe_json_load(stream, context=path)


def _import_every_module(tree, nltk):
    """Module -> [status, detail, digest of public names and signatures, names]."""
    names = ["nltk"] + sorted(
        m.name
        for m in pkgutil.walk_packages(nltk.__path__, "nltk.", onerror=lambda n: None)
    )
    modules = {}
    for name in names:
        signal.alarm(CALL_SECONDS)
        try:
            with warnings.catch_warnings(), contextlib.redirect_stdout(
                io.StringIO()
            ), contextlib.redirect_stderr(io.StringIO()):
                warnings.simplefilter("ignore")
                module = importlib.import_module(name)
            public = sorted(n for n in dir(module) if not n.startswith("_"))
            signatures = []
            for attr in public:
                obj = getattr(module, attr, None)
                if not (inspect.isfunction(obj) or inspect.isclass(obj)):
                    continue
                if getattr(obj, "__module__", None) != name:
                    continue
                try:
                    signatures.append(
                        (attr, _ADDRESS.sub("", str(inspect.signature(obj))))
                    )
                except (TypeError, ValueError):
                    signatures.append((attr, "?"))
            modules[name] = ["ok", "", _digest((public, signatures), tree), public]
        except _Timeout:
            modules[name] = ["timeout", "", "", []]
        except BaseException as e:
            # SystemExit too: a module that exits on import is recorded, not obeyed
            modules[name] = [
                type(e).__name__,
                str(e)[:200].replace(tree, "<tree>"),
                "",
                [],
            ]
        finally:
            signal.alarm(0)
    return modules


def command_packages(tree, out_path):
    """Write the index's packages, and fail if any is not installed and current."""
    nltk = _import_tree(tree)
    from nltk.downloader import Downloader

    downloader = Downloader()
    packages, missing = [], []
    for info in sorted(downloader.packages(), key=lambda p: p.id):
        packages.append({"id": info.id, "subdir": info.subdir})
        roots = _data_roots(nltk)
        if not any(
            downloader.status(info, root) == downloader.INSTALLED for root in roots
        ):
            missing.append(info.id)
    _write_json(out_path, packages)
    print(
        f"{len(packages)} packages in the index, {len(missing)} not installed and current"
    )
    for pid in missing:
        print(f"  {pid}")
    return 1 if missing else 0


def command_run(tree, packages_path, out_path):
    if (
        os.environ.get("PYTHONHASHSEED", "random") == "random"
        or sys.flags.ignore_environment
    ):
        sys.exit(
            "run needs a fixed PYTHONHASHSEED (and no -E or -I), or set orders change per process"
        )
    tree = os.path.realpath(tree)
    nltk = _import_tree(tree)
    random.seed(0)
    signal.signal(signal.SIGALRM, _alarm)
    with open(packages_path, encoding="utf-8") as f:
        packages = json.load(f)
    loaders = _corpus_loaders()
    known = {p["id"] for p in packages}
    results = {"<loaders with no package>": {}}
    for pid, group in sorted(loaders.items()):
        if pid not in known:
            for label, _ in group:
                results["<loaders with no package>"][label] = ["no package", pid, "", 0]
    for pkg in packages:
        start = time.perf_counter()
        results[pkg["id"]] = calls = _check_package(
            tree, nltk, pkg, loaders.get(pkg["id"], [])
        )
        failed = sum(1 for c in calls.values() if c[0] != "ok")
        print(
            f"{pkg['id']}: {len(calls)} calls, {failed} not ok, {time.perf_counter() - start:.0f} s",
            file=sys.stderr,
            flush=True,
        )
    modules = _import_every_module(tree, nltk)
    _write_json(out_path, {"packages": results, "modules": modules})
    print(
        f"{len(packages)} packages, {sum(map(len, results.values()))} calls, {len(modules)} modules"
    )
    return 0


def _classify(base, head):
    """Sort every difference between two runs into failing and reported ones."""
    failing, reported = [], []
    for pid in sorted(set(base["packages"]) | set(head["packages"])):
        before, after = base["packages"].get(pid, {}), head["packages"].get(pid, {})
        for label in sorted(set(before) | set(after)):
            b, h = before.get(label), after.get(label)
            row = (pid, label, b and b[:2], h and h[:2])
            if b is None:
                reported.append(("new call",) + row)
            elif h is None:
                (failing if b[0] == "ok" else reported).append(("gone",) + row)
            elif b[0] == "ok" and h[0] != "ok":
                failing.append(("now fails",) + row)
            elif b[0] == "ok" and b[1:3] != h[1:3]:
                failing.append(("changed",) + row)
            elif b[0] != "ok" and h[0] == "ok":
                reported.append(("now works",) + row)
            elif b[0] != "ok" and b[:2] != h[:2]:
                reported.append(("fails differently",) + row)
    for name in sorted(set(base["modules"]) | set(head["modules"])):
        b, h = base["modules"].get(name), head["modules"].get(name)
        row = ("<modules>", name, b and b[:2], h and h[:2])
        if b is None:
            reported.append(("new module",) + row)
        elif b[0] == "ok" and (h is None or h[0] != "ok"):
            failing.append(("no longer imports",) + row)
        elif h is None:
            reported.append(("gone",) + row)
        elif h[0] == "ok" and b[0] != "ok":
            reported.append(("now imports",) + row)
        elif b[0] != "ok":
            if b[:2] != h[:2]:
                reported.append(("fails differently",) + row)
        elif b[2] != h[2]:
            gone = sorted(set(b[3]) - set(h[3]))
            added = sorted(set(h[3]) - set(b[3]))
            detail = f"removed {gone}, added {added}" if gone or added else "signatures"
            reported.append(("API", "<modules>", name, "ok", detail))
    return failing, reported


def command_compare(base_path, head_path):
    with open(base_path, encoding="utf-8") as f:
        base = json.load(f)
    with open(head_path, encoding="utf-8") as f:
        head = json.load(f)
    failing, reported = _classify(base, head)
    calls = sum(map(len, head["packages"].values()))
    lines = [
        f"## Every data package and module: {calls} calls over {len(head['packages']) - 1} packages, {len(head['modules'])} modules",
        "",
        f"**{len(failing)} regressions** (a call that worked on the base and fails, changed or is gone; a module that no longer imports), {len(reported)} other differences.",
    ]
    for title, rows in (("Regressions", failing), ("Other differences", reported)):
        if rows:
            lines += [
                "",
                f"### {title}",
                "",
                "| kind | package | call | base | change |",
                "|---|---|---|---|---|",
            ]
            for kind, pid, label, b, h in rows[:300]:
                cell = lambda v: str(v).replace("|", "\\|").replace("\n", " ")[:160]
                lines.append(
                    f"| {kind} | {cell(pid)} | {cell(label)} | {cell(b)} | {cell(h)} |"
                )
            if len(rows) > 300:
                lines.append(f"| ... | {len(rows) - 300} more | | | |")
    text = "\n".join(lines) + "\n"
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write(text)
    return 1 if failing else 0


def _write_json(path, value):
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False)
    os.replace(path + ".tmp", path)


def main(argv):
    commands = {
        "packages": (command_packages, 2),
        "run": (command_run, 3),
        "compare": (command_compare, 2),
    }
    if (
        len(argv) < 1
        or argv[0] not in commands
        or len(argv) - 1 != commands[argv[0]][1]
    ):
        sys.exit(__doc__)
    command, _ = commands[argv[0]]
    return command(*argv[1:])


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
# Natural Language Toolkit: every data file and module, base against change
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Read every file of every NLTK data package and import every module, on two trees.

A unit test opens the few files it was written for, so a change to a shared
loader, reader or bound (a size cap, a depth scan, a sandbox check) can still
break a file that no test reads. This check runs NLTK's own code over every
file of the data index, with nothing mocked and nothing sampled, once on the
base commit and once on the change, and compares the two runs call by call:

* every file of every package is read in full with ``nltk.data.load``, raw as
  NLTK serves it, raw again from the package's zip archive where it is
  unzipped too, and as text; a file in a format ``nltk.data.load`` recognises
  (pickle, JSON, YAML, grammars, valuations, logic) is loaded in that format,
  every ``.json`` file is also parsed with :func:`~nltk.jsontags.safe_json_load`,
  and every ``.xml`` file with NLTK's ``XMLCorpusReader``;
* every corpus loader in ``nltk.corpus`` is read through each public method
  that needs no argument but a file: on every one of its files, and on the
  whole corpus for a method that takes no file; each result is read to its
  last item. Entry points that need another argument are called on every
  value of it (WordNet in every language, information content per file,
  every TIMIT recording, ...);
* corpora with no loader are read with the reader NLTK has for them, or else
  file by file with its ``PlaintextCorpusReader``, and the taggers, tokenizers,
  chunker, tagsets, VADER, stemmers and chat80 run their real pipelines;
* every module under ``nltk`` is imported, and its public names and
  signatures are recorded.

Each call records a digest of its whole result, hashed item by item as it is
read, and of what it printed to stdout and stderr, or the exception it raised. ``compare`` fails
when a call that worked on the base fails, returns something else or is gone
on the change, when a module that imported no longer does, and when a call on
either tree ran out of time, since its files were then not read; an intended
change of output fails too, so that it is reviewed. A call that failed on both
trees is listed, never failed on, so a fix shows in the summary, as does how
many of the index's files were read.

Usage::

    python tools/check_all_data.py packages TREE OUT.json
    PYTHONHASHSEED=0 python -P -s tools/check_all_data.py run TREE PACKAGES.json \
        OUT.json [--jobs N] [--shard I/N] [--modules]
    python tools/check_all_data.py compare BASE.json HEAD.json

``run`` refuses to start without a fixed ``PYTHONHASHSEED``: the order of a
set, and of anything a reader builds from one, otherwise changes per process.
Each package is read in a process of its own, ``--jobs`` at a time, and
``--shard`` reads one of N sets of packages of about equal size.
"""

import argparse
import collections.abc
import contextlib
import hashlib
import importlib
import inspect
import io
import itertools
import json
import multiprocessing
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

#: Seconds one call may take; a call cut off leaves files unread and fails the check.
CALL_SECONDS = 3600
#: Characters of an exception message that are recorded.
MESSAGE_CHARS = 200
#: Items read of the whole-corpus call of a method that is also read file by file,
#: enough to run the path that joins the files.
JOINED_ITEMS = 200
#: The parameters through which a reader method reads one file.
PER_FILE_PARAMS = ("fileids", "fileid")
#: Bytes one file is reckoned to cost, besides its size, when shards are balanced.
FILE_COST = 200_000
SAMPLE_TEXT = (
    "NLTK is a leading platform for building Python programs. "
    "Dr. Smith went to Washington on Jan. 5th."
)

# Reader methods that return file handles, paths or settings, not the corpus.
SKIP_METHODS = {"open", "abspath", "abspaths", "ensure_loaded", "encoding"}
# Read file by file only: on the whole corpus it is one string of every file.
PER_FILE_ONLY = {"raw"}
_ADDRESS = re.compile(r" at 0x[0-9a-fA-F]+")


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


def _mask(text, masks):
    """``text`` with each path of ``masks`` replaced by its label."""
    for path, label in masks:
        text = text.replace(path, label)
    return text


def _canonical(value, masks):
    """A process-independent form of ``value``: sets sorted, addresses dropped."""
    kind = type(value)
    if value is None or kind in (str, bytes, bool, int, float):
        return value
    if kind in (list, tuple):
        return [_canonical(v, masks) for v in value]
    if kind in (set, frozenset):
        return sorted((_canonical(v, masks) for v in value), key=repr)
    if kind is dict:
        items = ((_canonical(k, masks), _canonical(v, masks)) for k, v in value.items())
        return sorted(items, key=repr)
    if isinstance(value, ElementTree.Element):
        return ElementTree.tostring(value)
    return _mask(_ADDRESS.sub("", repr(value)), masks)


def _encoded(value, masks):
    return _mask(repr(_canonical(value, masks)), masks).encode("utf-8", "surrogatepass")


def _read_all(value, masks, limit=None):
    """(items, digest) of a result read to its last item, or its first ``limit``.

    A list, a tuple, an iterator and a corpus view are read item by item and
    hashed as they are read, so a corpus is never held whole; anything else,
    a string or a file's bytes among them, is hashed as one value.
    """
    from nltk.collections import AbstractLazySequence

    digest = hashlib.sha256()
    if isinstance(value, (bytes, bytearray)):
        digest.update(value)
        return len(value), digest.hexdigest()[:16]
    if isinstance(value, str):
        digest.update(_mask(value, masks).encode("utf-8", "surrogatepass"))
        return len(value), digest.hexdigest()[:16]
    lazy = (AbstractLazySequence, collections.abc.Iterator)
    if type(value) not in (list, tuple) and not isinstance(value, lazy):
        digest.update(_encoded(value, masks))
        return 1, digest.hexdigest()[:16]
    count = 0
    for item in value if limit is None else itertools.islice(value, limit):
        digest.update(_encoded(item, masks))
        digest.update(b"\0")
        count += 1
    return count, digest.hexdigest()[:16]


class _Run:
    """The calls of one package: label -> [status, detail, printed, seconds, items]."""

    def __init__(self, masks):
        self.masks = masks
        self.calls = {}

    def call(self, label, fn, limit=None):
        while label in self.calls:
            label += "'"
        signal.alarm(CALL_SECONDS)
        start = time.perf_counter()
        try:
            printed = io.StringIO()
            with warnings.catch_warnings(), contextlib.redirect_stdout(
                printed
            ), contextlib.redirect_stderr(printed):
                warnings.simplefilter("ignore")
                items, digest = _read_all(fn(), self.masks, limit)
            out = _read_all(printed.getvalue(), self.masks)[1]
            entry = ["ok", digest, out]
        except _Timeout:
            entry, items = ["timeout", "", ""], 0
        except Exception as e:
            message = _mask(str(e), self.masks)[:MESSAGE_CHARS]
            entry, items = [type(e).__name__, message, ""], 0
        finally:
            signal.alarm(0)
        self.calls[label] = entry + [round(time.perf_counter() - start, 2), items]
        return entry[0] == "ok"

    def note(self, label, status, detail=""):
        detail = _mask(detail, self.masks)[:MESSAGE_CHARS]
        self.calls[label] = [status, detail, "", 0, 0]


def _import_tree(tree):
    sys.path.insert(0, tree)
    import nltk

    where = os.path.realpath(nltk.__file__)
    if not where.startswith(os.path.realpath(tree) + os.sep):
        sys.exit(f"nltk was imported from {where}, not from {tree}")
    return nltk


def _data_roots(nltk):
    return [p for p in nltk.data.path if os.path.isdir(p)]


def _masks(tree, nltk):
    # Both runs read one data directory, which can lie inside a tree (CI keeps
    # it in the checkout), so data paths are masked before the tree, longest first.
    paths = {
        (r, "<data>")
        for root in _data_roots(nltk)
        for r in (root, os.path.realpath(root))
    }
    paths.add((tree, "<tree>"))
    return sorted(paths, key=lambda m: -len(m[0]))


def _package_files(nltk, subdir, pid):
    """(files, unzipped): the archive's files and whether NLTK has them unzipped too."""
    for root in _data_roots(nltk):
        unzipped = os.path.join(root, subdir, pid)
        archive = unzipped + ".zip"
        if os.path.isfile(archive):
            with zipfile.ZipFile(archive) as z:
                files = sorted(n for n in z.namelist() if not n.endswith("/"))
            return files, os.path.isdir(unzipped)
        if os.path.isdir(unzipped):
            base = os.path.join(root, subdir)
            files = sorted(
                os.path.relpath(os.path.join(d, f), base)
                for d, _, names in os.walk(unzipped)
                for f in names
            )
            return files, True
    return [], False


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
    """Every public method of a reader that needs no argument but a file, read in
    full: on every file, and on the whole corpus for a method that takes none."""
    from nltk.corpus.util import LazyCorpusLoader

    if not run.call(f"{label} loads", lambda: type(reader.fileids and reader).__name__):
        return
    if isinstance(reader, LazyCorpusLoader):
        return
    fileids = []
    try:
        fileids = list(reader.fileids())
        run.note(f"{label} fileids", "ok", str(len(fileids)))
    except Exception as e:
        run.note(f"{label} fileids", type(e).__name__, str(e))
    optional = (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
    for attr in sorted(dir(reader)):
        if attr.startswith("_") or attr in SKIP_METHODS:
            continue
        try:
            method = getattr(reader, attr)
        except Exception as e:
            run.note(f"{label}.{attr}", type(e).__name__, str(e))
            continue
        if not callable(method) or inspect.isclass(method):
            continue
        try:
            params = list(inspect.signature(method).parameters.values())
        except (TypeError, ValueError):
            continue
        required = [
            p.name for p in params if p.default is p.empty and p.kind not in optional
        ]
        per_file = [p.name for p in params if p.name in PER_FILE_PARAMS][:1]
        if any(name not in PER_FILE_PARAMS for name in required):
            continue
        if not per_file:
            run.call(f"{label}.{attr}()", method)
            continue
        if not required and attr not in PER_FILE_ONLY:
            run.call(f"{label}.{attr}()", method, limit=JOINED_ITEMS)
        for fid in fileids:
            run.call(
                f"{label}.{attr}({fid})", lambda m=method, f=fid: m(**{per_file[0]: f})
            )


def _every_synset(reader):
    # every synset of every part of speech, with what its record holds
    for synset in reader.all_synsets():
        yield (
            synset.name(),
            synset.definition(),
            synset.examples(),
            [lemma.name() for lemma in synset.lemmas()],
            sorted(s.name() for s in synset.hypernyms()),
        )


def _every_language(reader):
    # the multilingual wordnets list their languages once they are added
    reader.add_omw()
    for lang in sorted(reader.langs()):
        yield lang, sorted(reader.all_lemma_names(lang=lang))


def _every_information_content(reader):
    import nltk

    dog = nltk.corpus.wordnet.synset("dog.n.01")
    cat = nltk.corpus.wordnet.synset("cat.n.01")
    for fid in reader.fileids():
        ic = reader.ic(fid)
        yield fid, ic, dog.res_similarity(cat, ic), dog.lin_similarity(cat, ic)


_WORDNETS = [("every synset", _every_synset), ("every language", _every_language)]

# Entry points that need an argument, called on every value of it, by loader name.
LOADER_CALLS = {
    "wordnet": _WORDNETS
    + [
        (
            "synsets(perro, spa)",
            lambda r: [s.name() for s in r.synsets("perro", lang="spa")],
        ),
        (
            "path_similarity",
            lambda r: r.synset("dog.n.01").path_similarity(r.synset("cat.n.01")),
        ),
    ],
    "wordnet31": _WORDNETS,
    "wordnet2021": _WORDNETS,
    "wordnet2022": _WORDNETS,
    "english_wordnet": _WORDNETS,
    "wordnet_ic": [("ic of every file, similarity", _every_information_content)],
    "sentiwordnet": [
        ("senti_synsets(slow)", lambda r: [str(s) for s in r.senti_synsets("slow")])
    ],
    "verbnet": [("every class", lambda r: (r.pprint(c) for c in r.classids()))],
    "lin_thesaurus": [
        ("scored_synonyms(business)", lambda r: r.scored_synonyms("business"))
    ],
    "crubadan": [
        (
            "every language",
            lambda r: ((l, sorted(r.lang_freq(l).items())) for l in r.langs()),
        )
    ],
    "timit": [("every recording", lambda r: (r.wav(u) for u in r.utteranceids()))],
}


#: Corpora that no loader in nltk.corpus opens, read with the reader NLTK has.
_CONSTRUCTED = ("pl196x", "ycoe", "verbnet3", "omw", "omw-1.4")


def _reader_for(pid):
    """A reader NLTK has for a corpus that no loader in nltk.corpus opens."""
    import nltk
    from nltk.corpus.reader import (
        CorpusReader,
        Pl196xCorpusReader,
        VerbnetCorpusReader,
        WordNetCorpusReader,
        YCOECorpusReader,
    )
    from nltk.corpus.util import LazyCorpusLoader

    if pid in ("omw", "omw-1.4"):
        # an older Open Multilingual Wordnet, read by WordNet as its OMW 2.0 is
        omw = LazyCorpusLoader(
            pid, CorpusReader, r".*/wn-data-.*\.tab", encoding="utf8"
        )
        return WordNetCorpusReader(nltk.corpus.wordnet.root, omw)
    try:
        root = nltk.data.find(f"corpora/{pid}/")
    except LookupError:
        root = nltk.data.find(f"corpora/{pid}.zip/{pid}/")
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
            run.call(name, lambda n=name: getattr(nltk.help, n)())
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
    if pid in _CONSTRUCTED:
        try:
            reader = _reader_for(pid)
        except Exception as e:
            run.note("reader", type(e).__name__, str(e))
        else:
            name = type(reader).__name__
            _read_corpus(run, name, reader)
            if pid.startswith("omw"):
                # a reader of its own: the sweep added the extended OMW to this one
                fresh = lambda: _every_language(_reader_for(pid))
                run.call(f"{name}.every language", fresh)


def _safe_json(nltk, path):
    from nltk.jsontags import safe_json_load

    with nltk.data.find(path).open() as stream:
        return safe_json_load(stream, context=path)


def _package_root(nltk, subdir, pid):
    for name in (f"{subdir}/{pid}/", f"{subdir}/{pid}.zip/{pid}/"):
        try:
            return nltk.data.find(name)
        except LookupError:
            pass
    return None


def _generic_readers(run, nltk, pkg, files, loaders):
    """NLTK's XML reader on every XML file, and its plaintext reader on every
    other file of a corpus that has no reader of its own."""
    from nltk.corpus.reader import PlaintextCorpusReader, XMLCorpusReader

    pid, subdir = pkg["id"], pkg["subdir"]
    inside = [n[len(pid) + 1 :] for n in files if n.startswith(pid + "/")]
    xml = [f for f in inside if f.lower().endswith(".xml")]
    plain = subdir == "corpora" and not loaders and pid not in _CONSTRUCTED
    text = [f for f in inside if not f.lower().endswith(".xml")] if plain else []
    root = _package_root(nltk, subdir, pid) if xml or text else None
    if xml and root is not None:
        reader = XMLCorpusReader(root, xml)
        for fid in xml:
            run.call(f"XMLCorpusReader.xml({fid})", lambda f=fid: reader.xml(f))
    if text and root is not None:
        reader = PlaintextCorpusReader(root, text)
        for fid in text:
            for attr in ("words", "sents", "paras"):
                method = getattr(reader, attr)
                run.call(
                    f"PlaintextCorpusReader.{attr}({fid})", lambda m=method, f=fid: m(f)
                )


def _check_package(masks, nltk, pkg, loaders):
    run = _Run(masks)
    pid, subdir = pkg["id"], pkg["subdir"]
    files, unzipped = _package_files(nltk, subdir, pid)
    run.note("files", "ok" if files else "absent", str(len(files)))
    load = lambda p, f: nltk.data.load(p, format=f, cache=False)
    for name in files:
        path = f"{subdir}/{name}"
        run.call(f"read {name}", lambda p=path: load(p, "raw"))
        if unzipped:
            run.call(
                f"read zip {name}",
                lambda p=f"{subdir}/{pid}.zip/{name}": load(p, "raw"),
            )
        run.call(f"text {name}", lambda p=path: load(p, "text"))
        extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if extension in nltk.data.AUTO_FORMATS and extension not in ("txt", "text"):
            run.call(f"load {name}", lambda p=path: load(p, "auto"))
        if extension == "json":
            run.call(f"safe_json_load {name}", lambda p=path: _safe_json(nltk, p))
    _generic_readers(run, nltk, pkg, files, loaders)
    for label, loader in loaders:
        _read_corpus(run, label, loader)
        for call_label, fn in LOADER_CALLS.get(label, []):
            run.call(f"{label}.{call_label}", lambda f=fn, r=loader: f(r))
    _pipelines(run, pid)
    return run.calls


_WORKER = None


def _start_worker(tree):
    global _WORKER
    nltk = _import_tree(tree)
    random.seed(0)
    signal.signal(signal.SIGALRM, _alarm)
    _WORKER = (nltk, _masks(tree, nltk), _corpus_loaders())


def _package_job(pkg):
    nltk, masks, loaders = _WORKER
    start = time.perf_counter()
    calls = _check_package(masks, nltk, pkg, loaders.get(pkg["id"], []))
    return pkg["id"], calls, time.perf_counter() - start


def _import_every_module(masks, nltk):
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
            digest = hashlib.sha256(_encoded((public, signatures), masks)).hexdigest()[
                :16
            ]
            modules[name] = ["ok", "", digest, public]
        except _Timeout:
            modules[name] = ["timeout", "", "", []]
        except BaseException as e:
            # SystemExit too: a module that exits on import is recorded, not obeyed
            message = _mask(str(e), masks)[:MESSAGE_CHARS]
            modules[name] = [type(e).__name__, message, "", []]
        finally:
            signal.alarm(0)
    return modules


def _shard(packages, index, count):
    """The packages of shard ``index`` of ``count``, balanced by bytes and files."""
    loads = [0] * count
    shards = [[] for _ in range(count)]
    cost = lambda p: p.get("bytes", 0) + FILE_COST * p.get("files", 0)
    for pkg in sorted(packages, key=lambda p: (-cost(p), p["id"])):
        lightest = loads.index(min(loads))
        shards[lightest].append(pkg)
        loads[lightest] += cost(pkg)
    return sorted(shards[index], key=lambda p: p["id"])


def command_packages(tree, out_path):
    """Write the index's packages, and fail if any is not installed and current."""
    nltk = _import_tree(tree)
    from nltk.downloader import Downloader

    downloader = Downloader()
    packages, missing = [], []
    for info in sorted(downloader.packages(), key=lambda p: p.id):
        roots = _data_roots(nltk)
        if not any(downloader.status(info, r) == downloader.INSTALLED for r in roots):
            missing.append(info.id)
        files, _ = _package_files(nltk, info.subdir, info.id)
        size = int(getattr(info, "unzipped_size", 0) or 0)
        packages.append(
            {"id": info.id, "subdir": info.subdir, "files": len(files), "bytes": size}
        )
    _write_json(out_path, packages)
    total = sum(p["files"] for p in packages)
    print(
        f"{len(packages)} packages, {total} files in the index, {len(missing)} not installed and current"
    )
    for pid in missing:
        print(f"  {pid}")
    return 1 if missing else 0


def command_run(tree, packages_path, out_path, jobs=1, shard="0/1", modules=False):
    if (
        os.environ.get("PYTHONHASHSEED", "random") == "random"
        or sys.flags.ignore_environment
    ):
        sys.exit(
            "run needs a fixed PYTHONHASHSEED (and no -E or -I): set orders change per process"
        )
    tree = os.path.realpath(tree)
    nltk = _import_tree(tree)
    with open(packages_path, encoding="utf-8") as f:
        packages = json.load(f)
    index, count = (int(n) for n in shard.split("/"))
    packages = _shard(packages, index, count)
    loaders = _corpus_loaders()
    known = {p["id"] for p in json.load(open(packages_path, encoding="utf-8"))}
    results = {"<loaders with no package>": {}}
    for pid, group in sorted(loaders.items()):
        if pid not in known:
            for label, _ in group:
                results["<loaders with no package>"][label] = [
                    "no package",
                    pid,
                    "",
                    0,
                    0,
                ]
    # A package per process, so one cannot change what the next one reads.
    context = multiprocessing.get_context("spawn")
    with context.Pool(jobs, _start_worker, (tree,), maxtasksperchild=1) as pool:
        for pid, calls, seconds in pool.imap_unordered(_package_job, packages):
            results[pid] = calls
            failed = sum(1 for c in calls.values() if c[0] != "ok")
            print(
                f"{pid}: {len(calls)} calls, {failed} not ok, {seconds:.0f} s",
                file=sys.stderr,
                flush=True,
            )
    found = {}
    if modules:
        signal.signal(signal.SIGALRM, _alarm)
        found = _import_every_module(_masks(tree, nltk), nltk)
    _write_json(out_path, {"shard": shard, "packages": results, "modules": found})
    calls = sum(map(len, results.values()))
    print(f"{len(packages)} packages, {calls} calls, {len(found)} modules")
    return 0


def _classify(base, head):
    """Sort every difference between two runs into failing and reported ones."""
    failing, reported = [], []
    for pid in sorted(set(base["packages"]) | set(head["packages"])):
        before, after = base["packages"].get(pid, {}), head["packages"].get(pid, {})
        for label in sorted(set(before) | set(after)):
            b, h = before.get(label), after.get(label)
            row = (pid, label, b and b[:2], h and h[:2])
            if "timeout" in (b and b[0], h and h[0]):
                failing.append(("timed out, not read",) + row)
            elif b is None:
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
        if "timeout" in (b and b[0], h and h[0]):
            failing.append(("timed out, not imported",) + row)
        elif b is None:
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


def _coverage(run):
    """(files of the index, files read in full, the files that were not) of a run."""
    files = read = 0
    unread = []
    for pid, calls in run["packages"].items():
        if "files" in calls:
            files += int(calls["files"][1] or 0)
        for label, entry in calls.items():
            if label.startswith("read ") and not label.startswith("read zip "):
                if entry[0] == "ok":
                    read += 1
                else:
                    unread.append((pid, label[5:], entry[:2]))
    return files, read, unread


def command_compare(base_path, head_path):
    with open(base_path, encoding="utf-8") as f:
        base = json.load(f)
    with open(head_path, encoding="utf-8") as f:
        head = json.load(f)
    if base["shard"] != head["shard"] or set(base["packages"]) != set(head["packages"]):
        sys.exit(
            f"the runs read different packages (shards {base['shard']}, {head['shard']})"
        )
    failing, reported = _classify(base, head)
    files, read, unread = _coverage(head)
    calls = sum(map(len, head["packages"].values()))
    packages = len(head["packages"]) - 1
    lines = [
        f"## Every data file and module, shard {head['shard']}: {packages} packages, {calls} calls, {len(head['modules'])} modules",
        "",
        f"**{read} of the {files} files** of these packages read in full on the change; {len(unread)} could not be read (listed below).",
        "",
        f"**{len(failing)} regressions** (a call that worked on the base and fails, changed or is gone; a call that ran out of time on either tree; a module that no longer imports), {len(reported)} other differences.",
    ]
    tables = (
        ("Regressions", failing),
        (
            "Files the change could not read",
            [("unread",) + u + (None,) for u in unread],
        ),
        ("Other differences", reported),
    )
    for title, rows in tables:
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
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    packages = commands.add_parser("packages")
    packages.add_argument("tree")
    packages.add_argument("out")
    run = commands.add_parser("run")
    run.add_argument("tree")
    run.add_argument("packages")
    run.add_argument("out")
    run.add_argument("--jobs", type=int, default=1)
    run.add_argument("--shard", default="0/1")
    run.add_argument("--modules", action="store_true")
    compare = commands.add_parser("compare")
    compare.add_argument("base")
    compare.add_argument("head")
    args = parser.parse_args(argv)
    if args.command == "packages":
        return command_packages(args.tree, args.out)
    if args.command == "run":
        return command_run(
            args.tree, args.packages, args.out, args.jobs, args.shard, args.modules
        )
    return command_compare(args.base, args.head)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

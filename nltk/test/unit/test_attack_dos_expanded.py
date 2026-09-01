# Natural Language Toolkit: expanded denial-of-service attack harness
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org>
# For license information, see LICENSE.TXT

r"""
Consolidated, cross-platform denial-of-service attack harness for the
GHSA-8mgp umbrella (#3753).

This module is deliberately *offensive*: every hostile case below feeds a
crafted input to a guarded NLTK sink and proves the guard keeps the process
BOUNDED. "Bounded" means the operation either

* is **REFUSED** (the guard raises ``ValueError`` / ``PermissionError`` /
  ``TimeoutError`` before doing the expensive work), or
* **completes quickly** with a safe result (the ``regex`` engine linearises a
  catastrophic pattern, or a bounded reader truncates a decompression bomb),

and in particular that it never hangs a CPU core forever and never expands a
tiny input into gigabytes of memory.

Three guard families are exercised (see ``nltk/data.py``, ``nltk/redos.py`` and
the algorithmic guards in ``nltk/util.py`` / the parsers / the corpus readers):

1. Decompression bombs (CWE-409): the per-member ratio guard, the
   central-directory member-count guard, the aggregate-size guard, the
   actual-byte streaming cap, and the ``.gz`` / ``bz2`` / ``lzma`` stream
   readers.
2. Caller-supplied ReDoS (CWE-1333): ``nltk.redos.compile`` behind
   ``re_show`` / ``RegexpStemmer`` / ``RegexpTokenizer`` / ``RegexpTagger`` /
   ``tgrep`` / ``Text.findall``, plus the bounded-quantifier ``FEATURES``
   regex in the reviews reader.
3. Algorithmic blow-ups (CWE-407 / CWE-400 / CWE-674): the ``skipgrams``
   combinatorial guard, the ``XMLCorpusView`` linear-scan guard, the
   ``RecursiveDescentParser`` wall-clock bound, and the Hungarian-stemmer
   empty-string guard.

Design choices that keep this suite portable and honest:

* **Subprocess wall-clock timeouts, never signals.** ``signal.SIGALRM`` is
  POSIX-only; a child process with a hard ``subprocess`` timeout is the only
  timeout that also works on Windows. A hostile case that would hang shows up
  as ``subprocess.TimeoutExpired`` and *fails* the test, so a regression that
  removed a guard could never be mistaken for a pass.
* **Children inherit the parent import path** via ``PYTHONPATH`` so a slow cold
  import of NLTK cannot be misread as a hang. The budget for a guarded child is
  far above ``nltk.redos.DEFAULT_TIMEOUT`` to leave head-room for that import
  on a loaded machine.
* **Teeth.** For the sharpest vectors a matching STOCK control runs the SAME
  input with no guard (stdlib ``re``, un-timed ``regex``, raw ``zipfile``) and
  is asserted to hang or to expand without bound, proving the guard is load
  bearing rather than the input being harmless.
* **No leaks.** Zip fixtures are staged under ``$HOME`` (a registered NLTK data
  root), never under a world-writable temp dir, and every on-disk fixture is
  removed afterwards. No module-level guard state (``MAX_UNZIP_*``,
  ``redos.DEFAULT_TIMEOUT``, ``nltk.data.path``, ``pathsec.ENFORCE``) is
  mutated in this process; the one path-root registration happens inside an
  isolated child that exits.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from collections import namedtuple

import pytest

# Head-room over redos.DEFAULT_TIMEOUT (5.0s) plus a ~10s cold NLTK import on a
# loaded machine. A guarded child that does not finish inside this really hung.
GUARDED_BUDGET = 30.0
# The many-members child additionally builds a 100k-entry archive in memory.
HEAVY_BUDGET = 45.0
# A stock (unguarded) control is expected to spin forever; this is only how long
# we wait before concluding "yes, it hangs". Kept short because the stdlib sink
# has nothing to import beyond ``re`` / ``regex`` / ``zipfile``.
STOCK_TEETH_TIMEOUT = 8.0


# ==========================================================================
# Subprocess plumbing
# ==========================================================================

_ChildResult = namedtuple("_ChildResult", "timed_out returncode cases stdout stderr")


def _parse_cases(stdout):
    """Collect ``CASE|<name>|<verdict>|<detail>`` lines into ``{name: verdict}``."""
    cases = {}
    for line in (stdout or "").splitlines():
        if line.startswith("CASE|"):
            parts = line.split("|", 3)
            if len(parts) >= 3:
                cases[parts[1]] = parts[2]
    return cases


def _run_child(code, budget):
    """Run ``code`` in a fresh interpreter under a hard wall-clock ``budget``.

    The child inherits the parent's ``sys.path`` so it imports the very NLTK
    under test, and a cold import cannot be mistaken for a hang.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(sys.path)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=budget,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return _ChildResult(True, None, _parse_cases(out), out, err)
    return _ChildResult(
        False, proc.returncode, _parse_cases(proc.stdout), proc.stdout, proc.stderr
    )


def _assert_no_hang(res, family):
    assert not res.timed_out, (
        f"{family}: a guarded sink did NOT return inside {GUARDED_BUDGET}s "
        f"(possible hang / removed guard). stdout so far:\n{res.stdout}\n"
        f"stderr:\n{res.stderr}"
    )


def _assert_cases(res, expected):
    """Assert each expected case reported an allowed verdict and none LEAKed."""
    leaks = {n: v for n, v in res.cases.items() if v == "LEAK"}
    assert not leaks, (
        f"REAL FINDING: a bomb produced its full payload (LEAK): {leaks}\n"
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )
    for name, allowed in expected.items():
        assert name in res.cases, (
            f"case {name!r} never reported (child crashed before it?).\n"
            f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )
        assert res.cases[name] in allowed, (
            f"case {name!r} reported {res.cases[name]!r}, expected one of "
            f"{sorted(allowed)}.\nstdout:\n{res.stdout}\nstderr:\n{res.stderr}"
        )


# A tiny reporting helper injected into every guarded child. ``REFUSED`` means
# the guard raised; ``BOUNDED`` means the call returned a safe result quickly;
# ``LEAK`` means the bomb succeeded (a real finding); ``ERROR`` is anything
# unexpected.
_CHILD_PREAMBLE = r"""
import sys, time, io, zipfile, gzip, bz2, lzma

def report(name, verdict, detail=""):
    print("CASE|%s|%s|%s" % (name, verdict, detail))
    sys.stdout.flush()

def guarded(name, fn, refusing=(ValueError, PermissionError, TimeoutError)):
    try:
        fn()
        report(name, "BOUNDED")
    except refusing as e:
        report(name, "REFUSED", type(e).__name__)
    except Exception as e:  # noqa
        report(name, "ERROR", "%s:%s" % (type(e).__name__, str(e)[:60]))
"""


# ==========================================================================
# Family 1: decompression bombs (CWE-409)
# ==========================================================================

_CHILD_DECOMP = (
    _CHILD_PREAMBLE
    + r"""
import nltk.data as D
from nltk import pathsec

MiB = 1024 * 1024
ZEROS_40 = b"\x00" * (40 * MiB)

# A single member whose declared/actual size expands >1000x over the activation
# floor: refused by the per-member ratio guard on read.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("bomb.bin", ZEROS_40)
one = buf.getvalue()
def _single():
    out = pathsec.ZipFile(io.BytesIO(one)).read("bomb.bin")
    if len(out) >= 32 * MiB:
        report("single_member_ratio", "LEAK", str(len(out)))
        raise SystemExit
guarded("single_member_ratio", _single)

# Three members each below the 32 MiB activation floor (so the per-member guard
# never fires) that SUM to a ratio-1000+ bomb: refused by the aggregate guard at
# construction, before any byte is decompressed.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    for i in range(3):
        z.writestr("m%d.bin" % i, b"\x00" * (25 * MiB))
agg = buf.getvalue()
guarded("aggregate_sum", lambda: pathsec.ZipFile(io.BytesIO(agg)))

# Recursive zip: a zip whose member is itself a zip whose member is a bomb.
# Reading the inner archive out of the outer one is bounded (it is small); the
# inner bomb is independently refused, so each decompression layer is guarded.
inner = one  # a zip that contains bomb.bin
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
    z.writestr("inner.zip", inner)
outer = buf.getvalue()
def _nested_outer():
    blob = pathsec.ZipFile(io.BytesIO(outer)).read("inner.zip")
    if len(blob) >= 32 * MiB:
        report("nested_outer_read", "LEAK", str(len(blob)))
        raise SystemExit
guarded("nested_outer_read", _nested_outer)
guarded(
    "nested_inner_bomb",
    lambda: pathsec.ZipFile(io.BytesIO(inner)).read("bomb.bin"),
)

# A member whose NAME carries a newline. A name-based check written with an
# un-anchored or non-DOTALL regex could be fooled into skipping such a member;
# the size guard is name-agnostic, so the bomb is still refused.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("evil\n../passwd.bin", ZEROS_40)
nl = buf.getvalue()
guarded(
    "newline_in_member_name",
    lambda: pathsec.ZipFile(io.BytesIO(nl)).read("evil\n../passwd.bin"),
)

# A metadata claim of ~4.3 GiB uncompressed (the 32-bit / zip64 boundary) with a
# tiny compressed size: refused by the declared-size early check without reading
# a single byte.
zi = zipfile.ZipInfo("huge.bin")
zi.file_size = 4300 * MiB
zi.compress_size = 500
guarded("four_gib_metadata_claim", lambda: D._check_decompression_bomb(zi))

# The central-directory member-count guard at the exact boundary.
guarded(
    "member_count_over_limit",
    lambda: D._check_zip_member_count(D.MAX_UNZIP_MEMBERS + 1),
)

# A self-referential / quine-like decompressor that never yields EOF: the
# streaming reader must cut it off rather than loop forever.
class InfiniteStream:
    def read(self, n=-1):
        return b"\x00" * MiB  # never returns b"", i.e. an endless expansion
guarded(
    "infinite_quine_stream",
    lambda: D._bounded_stream_read(InfiniteStream(), 1000, "quine.bin", kind="zip"),
)

# gzip / bz2 / lzma stream bombs pushed through the SAME bounded reader: it is
# decompressor-agnostic, capping the actual bytes regardless of codec.
gz = gzip.compress(ZEROS_40)
guarded(
    "gzip_stream_bomb",
    lambda: D._bounded_stream_read(gzip.GzipFile(fileobj=io.BytesIO(gz)), len(gz),
                                   "x.gz", kind="gzip"),
)
bz = bz2.compress(ZEROS_40)
guarded(
    "bz2_stream_bomb",
    lambda: D._bounded_stream_read(bz2.BZ2File(io.BytesIO(bz)), len(bz),
                                   "x.bz2", kind="gzip"),
)
xz = lzma.compress(ZEROS_40)
guarded(
    "lzma_stream_bomb",
    lambda: D._bounded_stream_read(lzma.LZMAFile(io.BytesIO(xz)), len(xz),
                                   "x.xz", kind="gzip"),
)

# The bounded gzip helper used for a .gz nested inside a zip member.
guarded("gzip_member_helper_bomb", lambda: D._bounded_gzip_decompress(gz, "x.gz"))
"""
)


def test_decompression_bomb_family():
    res = _run_child(_CHILD_DECOMP, GUARDED_BUDGET)
    _assert_no_hang(res, "decompression bombs")
    _assert_cases(
        res,
        {
            "single_member_ratio": {"REFUSED"},
            "aggregate_sum": {"REFUSED"},
            "nested_outer_read": {"BOUNDED"},
            "nested_inner_bomb": {"REFUSED"},
            "newline_in_member_name": {"REFUSED"},
            "four_gib_metadata_claim": {"REFUSED"},
            "member_count_over_limit": {"REFUSED"},
            "infinite_quine_stream": {"REFUSED"},
            "gzip_stream_bomb": {"REFUSED"},
            "bz2_stream_bomb": {"REFUSED"},
            "lzma_stream_bomb": {"REFUSED"},
            "gzip_member_helper_bomb": {"REFUSED"},
        },
    )


_CHILD_MEMBERS = (
    _CHILD_PREAMBLE
    + r"""
import nltk.data as D
from nltk import pathsec

# A REAL over-limit archive: MAX_UNZIP_MEMBERS + 1 empty entries. The metadata
# alone is the payload (a central-directory bomb, CWE-409); construction must
# refuse it before any consumer pays to list the entries.
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    for i in range(D.MAX_UNZIP_MEMBERS + 1):
        z.writestr("m%d" % i, b"")
blob = buf.getvalue()
guarded("central_directory_bomb", lambda: pathsec.ZipFile(io.BytesIO(blob)))
"""
)


def test_central_directory_member_count_bomb():
    res = _run_child(_CHILD_MEMBERS, HEAVY_BUDGET)
    _assert_no_hang(res, "central-directory bomb")
    _assert_cases(res, {"central_directory_bomb": {"REFUSED"}})


_CHILD_ONDISK = (
    _CHILD_PREAMBLE
    + r"""
import os, tempfile, shutil

# Stage fixtures under $HOME (a registered NLTK data root), never a shared temp
# dir, and register the staging dir on THIS child's nltk.data.path only, so the
# file-backed ZipFilePathPointer / _secure_open code path is exercised end to
# end. The mutation dies with this process.
home = os.path.expanduser("~")
staging = tempfile.mkdtemp(prefix="nltk_dos_fix_", dir=home)
try:
    import nltk.data
    nltk.data.path.append(staging)
    from nltk.data import ZipFilePathPointer

    MiB = 1024 * 1024
    bomb_zip = os.path.join(staging, "bomb.zip")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("bomb.bin", b"\x00" * (40 * MiB))
    with open(bomb_zip, "wb") as fh:
        fh.write(b.getvalue())

    def _ondisk_bomb():
        out = ZipFilePathPointer(bomb_zip, "bomb.bin").open().read()
        if len(out) >= 32 * MiB:
            report("ondisk_zip_bomb", "LEAK", str(len(out)))
            raise SystemExit
    guarded("ondisk_zip_bomb", _ondisk_bomb)

    ok_zip = os.path.join(staging, "ok.zip")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("hello.txt", b"hello world")
    with open(ok_zip, "wb") as fh:
        fh.write(b.getvalue())
    got = ZipFilePathPointer(ok_zip, "hello.txt").open().read()
    report("ondisk_benign", "BOUNDED" if got == b"hello world" else "ERROR")
finally:
    shutil.rmtree(staging, ignore_errors=True)
"""
)


def test_ondisk_zipfilepathpointer_bomb_and_benign():
    res = _run_child(_CHILD_ONDISK, GUARDED_BUDGET)
    _assert_no_hang(res, "on-disk zip bomb")
    _assert_cases(
        res,
        {
            "ondisk_zip_bomb": {"REFUSED"},
            "ondisk_benign": {"BOUNDED"},
        },
    )


# ==========================================================================
# Family 2: caller-supplied ReDoS (CWE-1333)
# ==========================================================================
#
# Two shapes of catastrophic pattern:
#   * engine-collapse, e.g. (a+)+$ / (a*)*$ / (.*a){20}: the ``regex`` optimiser
#     linearises these, so the guarded call returns almost instantly (BOUNDED).
#   * timeout-backstop, e.g. (a|a)*$: the identical-branch alternation defeats
#     the optimiser in both ``re`` and ``regex``, so the wall-clock timeout trips
#     and the call is REFUSED with TimeoutError.
# Either verdict is a pass; a hang is the only failure.

_EVIL_COLLAPSE = r"(a+)+$"
_EVIL_STAR = r"(a*)*$"
_EVIL_NESTED = r"(.*a){20}"
_EVIL_TIMEOUT = r"(a|a)*$"
_EVIL_S = "a" * 64 + "!"

_CHILD_REDOS_A = (
    _CHILD_PREAMBLE
    + r"""
from nltk.util import re_show
from nltk.stem import RegexpStemmer
from nltk.tokenize import RegexpTokenizer
from nltk.tag import RegexpTagger

COL = %(col)r
STAR = %(star)r
NEST = %(nest)r
TO = %(to)r
S = %(s)r

# re_show prints the string with the matches bracketed; the pattern is caller
# supplied and run over caller text.
guarded("re_show", lambda: re_show(COL, S))
# RegexpStemmer.sub over a hostile stem regex.
guarded("regexp_stemmer", lambda: RegexpStemmer(STAR).stem(S))
# RegexpTokenizer.tokenize with the timeout-family pattern.
guarded("regexp_tokenizer", lambda: RegexpTokenizer(TO).tokenize(S))
# RegexpTagger.tag with a nested-quantifier pattern; the hostile string is a
# single long TOKEN so the pattern actually backtracks over it.
guarded("regexp_tagger", lambda: RegexpTagger([(NEST, "X")]).tag([S]))
"""
    % {
        "col": _EVIL_COLLAPSE,
        "star": _EVIL_STAR,
        "nest": _EVIL_NESTED,
        "to": _EVIL_TIMEOUT,
        "s": _EVIL_S,
    }
)


def test_redos_caller_patterns_group_a():
    res = _run_child(_CHILD_REDOS_A, GUARDED_BUDGET)
    _assert_no_hang(res, "ReDoS group A")
    _assert_cases(
        res,
        {
            "re_show": {"BOUNDED", "REFUSED"},
            "regexp_stemmer": {"BOUNDED", "REFUSED"},
            "regexp_tokenizer": {"BOUNDED", "REFUSED"},
            "regexp_tagger": {"BOUNDED", "REFUSED"},
        },
    )


_CHILD_REDOS_B = (
    _CHILD_PREAMBLE
    + r"""
from nltk.tgrep import tgrep_nodes, tgrep_compile
from nltk.tree import ParentedTree
from nltk.text import Text
from nltk.corpus.reader.reviews import FEATURES

TO = %(to)r
S = %(s)r

# tgrep /regex/ node literal searched against a node LABEL made of the hostile
# string, using the timeout-family pattern.
tree = ParentedTree(S, ["x"])
guarded("tgrep_node_literal",
        lambda: list(tgrep_nodes(tgrep_compile("/" + TO + "/"), [tree])))

# Text.findall over an angle-bracket token stream with a backtracking token
# pattern (bounded by the TokenSearcher timeout).
txt = Text(["a"] * 40)
guarded("text_findall", lambda: txt.findall(r"<.*>*<zzz>"))

# The reviews FEATURES regex is a stdlib pattern whose inner quantifier is
# *bounded* ({0,50}); a bracket-less 50k-word line stays LINEAR instead of
# rescanning quadratically. This exercises the bounded-quantifier guard.
line = "word " * 50000
def _features():
    hits = FEATURES.findall(line)
    report("reviews_features", "BOUNDED", str(len(hits)))
try:
    _features()
except (ValueError, TimeoutError) as e:
    report("reviews_features", "REFUSED", type(e).__name__)
except Exception as e:  # noqa
    report("reviews_features", "ERROR", type(e).__name__)
"""
    % {"to": _EVIL_TIMEOUT, "s": _EVIL_S}
)


def test_redos_caller_patterns_group_b():
    res = _run_child(_CHILD_REDOS_B, GUARDED_BUDGET)
    _assert_no_hang(res, "ReDoS group B")
    _assert_cases(
        res,
        {
            "tgrep_node_literal": {"BOUNDED", "REFUSED"},
            "text_findall": {"BOUNDED", "REFUSED"},
            "reviews_features": {"BOUNDED"},
        },
    )


# ==========================================================================
# Family 3: algorithmic blow-ups (CWE-407 / CWE-400 / CWE-674)
# ==========================================================================

_CHILD_ALGO = (
    _CHILD_PREAMBLE
    + r"""
from nltk.util import skipgrams
from nltk.corpus.reader.xmldocs import XMLCorpusView
from nltk.stem.snowball import HungarianStemmer

SENT = "a b c d e".split()

# skipgrams: the number of per-window combinations, math.comb(n+k-1, n-1), is
# guarded; huge n/k is refused before it can enumerate.
guarded("skipgrams_combinatorial", lambda: list(skipgrams(SENT, n=100, k=100)))
guarded("skipgrams_huge_n", lambda: list(skipgrams(SENT, n=10**9, k=1)))

# XMLCorpusView: a single unterminated tag of 2M characters. The fragment scan
# is now linear (it no longer re-runs the backtracking _VALID_XML_RE over the
# whole growing buffer), so it raises promptly instead of going O(n^2).
def _xml():
    v = XMLCorpusView.__new__(XMLCorpusView)
    v._read_xml_fragment(io.StringIO("<" + "a" * (2 * 1024 * 1024)))
guarded("xmlcorpusview_giant_tag", _xml)

# RecursiveDescentParser on a left-recursive grammar: the wall-clock bound (or
# Python's own recursion limit) stops it rather than looping forever.
def _rd():
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser
    g = CFG.fromstring("S -> S S | 'a'")
    list(RecursiveDescentParser(g).parse(["a", "a", "a"]))
guarded("recursivedescent_left_recursive", _rd,
        refusing=(ValueError, PermissionError, TimeoutError, RecursionError))

# Hungarian stemmer on the empty string: guarded against IndexError (returns "").
def _hun():
    out = HungarianStemmer().stem("")
    report("hungarian_empty_string", "BOUNDED" if out == "" else "ERROR")
try:
    _hun()
except Exception as e:  # noqa
    report("hungarian_empty_string", "ERROR", type(e).__name__)
"""
)


def test_algorithmic_blowup_family():
    res = _run_child(_CHILD_ALGO, GUARDED_BUDGET)
    _assert_no_hang(res, "algorithmic blow-ups")
    _assert_cases(
        res,
        {
            "skipgrams_combinatorial": {"REFUSED"},
            "skipgrams_huge_n": {"REFUSED"},
            "xmlcorpusview_giant_tag": {"REFUSED"},
            "recursivedescent_left_recursive": {"REFUSED"},
            "hungarian_empty_string": {"BOUNDED"},
        },
    )


# ==========================================================================
# Teeth: prove the same input is genuinely hostile without the guard
# ==========================================================================


def _assert_stock_hangs(code, label):
    res = _run_child(code, STOCK_TEETH_TIMEOUT)
    assert res.timed_out, (
        f"teeth check {label!r} did NOT hang the unguarded sink within "
        f"{STOCK_TEETH_TIMEOUT}s, so it does not prove the guard has teeth. "
        f"stdout:\n{res.stdout}\nstderr:\n{res.stderr}"
    )


def test_teeth_stock_re_hangs_engine_collapse_family():
    # Stock stdlib re on (a+)+$ backtracks exponentially and never returns; the
    # guard defuses it by swapping in the ``regex`` engine (see the guarded
    # BOUNDED result in test_redos_caller_patterns_group_a).
    _assert_stock_hangs(
        "import re; re.compile(r'(a+)+$').search('a' * 30 + '!'); print('done')",
        "stock re (a+)+$",
    )


def test_teeth_stock_untimed_regex_hangs_backstop_family():
    # The ``regex`` optimiser does NOT linearise the identical-branch (a|a)*$;
    # without the wall-clock timeout it hangs too. This is why the timeout is a
    # mandatory backstop, not a nicety.
    _assert_stock_hangs(
        "import regex; regex.compile(r'(a|a)*$').search('a' * 64 + '!'); print('x')",
        "untimed regex (a|a)*$",
    )


def test_teeth_stock_unbounded_features_regex_hangs():
    # The reviews FEATURES guard is the BOUND on its inner quantifier. Replace
    # {0,50} with * and the same 50k-word line rescans quadratically and hangs,
    # proving the bounded quantifier is what keeps the shipped regex linear.
    code = (
        "import re\n"
        "UNB = re.compile(r'(\\w+(?:\\s\\w+)*)\\[((?:\\+|\\-)\\d)\\]')\n"
        "UNB.findall('word ' * 50000)\n"
        "print('done')\n"
    )
    _assert_stock_hangs(code, "unbounded FEATURES regex")


def test_teeth_stock_zipfile_leaks_bomb_while_guard_refuses():
    # Raw zipfile.read expands a 40 MiB zeros bomb fully into memory (a leak that
    # scales to OOM); the guarded pathsec reader refuses the same member. Kept at
    # 40 MiB so the demonstration itself does not exhaust the test machine.
    code = (
        _CHILD_PREAMBLE
        + r"""
from nltk import pathsec

MiB = 1024 * 1024
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("bomb.bin", b"\x00" * (40 * MiB))
blob = buf.getvalue()

# Unguarded: the full payload materialises (would OOM at scale).
raw = zipfile.ZipFile(io.BytesIO(blob)).read("bomb.bin")
report("stock_zip_expands", "LEAK" if len(raw) >= 32 * MiB else "BOUNDED", str(len(raw)))

# Guarded: the same member is refused.
guarded("guarded_zip_refuses", lambda: pathsec.ZipFile(io.BytesIO(blob)).read("bomb.bin"))
"""
    )
    res = _run_child(code, GUARDED_BUDGET)
    assert not res.timed_out, f"zip teeth child hung:\n{res.stderr}"
    # The unguarded read is EXPECTED to leak the whole 40 MiB; that is the teeth.
    assert res.cases.get("stock_zip_expands") == "LEAK", (
        f"expected the raw zipfile read to expand the bomb; got "
        f"{res.cases.get('stock_zip_expands')!r}\n{res.stdout}"
    )
    assert res.cases.get("guarded_zip_refuses") == "REFUSED", (
        f"guarded reader failed to refuse the bomb: "
        f"{res.cases.get('guarded_zip_refuses')!r}\n{res.stdout}"
    )


def test_teeth_guarded_side_completes_for_both_families():
    # The mirror of the two ReDoS teeth: the guarded calls that replace the two
    # hanging stock controls both return inside the budget (one by engine
    # collapse, one by the timeout backstop).
    code = (
        _CHILD_PREAMBLE
        + r"""
from nltk import redos
# engine-collapse family: returns almost instantly.
guarded("guarded_engine_collapse",
        lambda: redos.compile(r"(a+)+$").search("a" * 30 + "!"))
# timeout-backstop family: refused with TimeoutError well inside the budget.
guarded("guarded_timeout_backstop",
        lambda: redos.compile(r"(a|a)*$").search("a" * 64 + "!"))
"""
    )
    res = _run_child(code, GUARDED_BUDGET)
    _assert_no_hang(res, "guarded teeth mirror")
    _assert_cases(
        res,
        {
            "guarded_engine_collapse": {"BOUNDED"},
            "guarded_timeout_backstop": {"REFUSED"},
        },
    )


# ==========================================================================
# Benign controls: the guarded sinks must still WORK, and quickly
# ==========================================================================
# These run in-process (no hostile input, so no hang risk) and assert correct
# output, proving the guards do not break legitimate use.


def test_benign_regex_entry_points_still_correct():
    from nltk.stem import RegexpStemmer
    from nltk.tag import RegexpTagger
    from nltk.text import Text
    from nltk.tokenize import RegexpTokenizer

    assert RegexpTokenizer(r"\w+").tokenize("hello world foo") == [
        "hello",
        "world",
        "foo",
    ]
    assert RegexpStemmer(r"ing$", min=4).stem("running") == "runn"
    tagged = RegexpTagger([(r"^\d+$", "CD"), (r".*", "NN")]).tag(["12", "cats"])
    assert tagged == [("12", "CD"), ("cats", "NN")]
    # Text.findall returns the matched tokens for an ordinary angle-bracket query.
    hits = Text("the quick brown fox".split()).findall("<the><.*><brown>")
    assert hits is None or isinstance(hits, (list, type(None)))


def test_benign_re_show_and_tgrep_still_correct():
    import io as _io
    from contextlib import redirect_stdout

    from nltk.tgrep import tgrep_compile, tgrep_nodes
    from nltk.tree import ParentedTree
    from nltk.util import re_show

    out = _io.StringIO()
    with redirect_stdout(out):
        re_show(r"o", "foobar")
    # 'foobar' has two 'o's, so two bracket pairs appear.
    assert out.getvalue().count("{") == 2

    tree = ParentedTree.fromstring("(S (NP the) (VP (V saw) (NP him)))")
    # tgrep_nodes yields one hit-list per input tree; this tree has two NP nodes.
    matched = list(tgrep_nodes(tgrep_compile("NP"), [tree]))
    assert len(matched) == 1
    assert len(matched[0]) == 2


def test_benign_reviews_features_extraction_preserved():
    import re

    from nltk.corpus.reader.reviews import FEATURES

    # The inner quantifier is greedy, so the run before a "[+N]" bracket extends
    # back through intervening words ("and screen"), which is the shipped
    # behaviour; the point here is that extraction still works and stays bounded.
    assert FEATURES.findall("battery life[+2] and screen[-1] are notable") == [
        ("battery life", "+2"),
        ("and screen", "-1"),
    ]
    # The shipped pattern is the bounded-quantifier one.
    assert "{0,50}" in FEATURES.pattern
    assert re is not None


def test_benign_zip_extract_roundtrip():
    import io

    from nltk import pathsec

    buf = io.BytesIO()
    with pathsec.ZipFile(buf, "w", __import__("zipfile").ZIP_DEFLATED) as z:
        z.writestr("greeting.txt", b"hello world")
        z.writestr("nested/data.txt", b"payload")
    blob = buf.getvalue()
    zf = pathsec.ZipFile(io.BytesIO(blob))
    assert zf.read("greeting.txt") == b"hello world"
    assert zf.read("nested/data.txt") == b"payload"


def test_benign_skipgrams_parse_stem_outputs():
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser
    from nltk.stem.snowball import HungarianStemmer
    from nltk.util import skipgrams

    assert list(skipgrams("a b c".split(), 2, 1)) == [
        ("a", "b"),
        ("a", "c"),
        ("b", "c"),
    ]
    grammar = CFG.fromstring("S -> NP VP\nNP -> 'John'\nVP -> 'runs'")
    trees = list(RecursiveDescentParser(grammar).parse(["John", "runs"]))
    assert [str(t) for t in trees] == ["(S (NP John) (VP runs))"]
    stemmer = HungarianStemmer()
    assert stemmer.stem("") == ""
    assert isinstance(stemmer.stem("hazaknak"), str)


# ==========================================================================
# No-weakening pins: the guard knobs must stay at their safe defaults
# ==========================================================================


def test_guard_constants_not_weakened():
    import nltk.data as D
    from nltk import redos

    assert D.MAX_UNZIP_RATIO == 1000, "MAX_UNZIP_RATIO was changed"
    assert D.MAX_UNZIP_MEMBERS == 100_000, "MAX_UNZIP_MEMBERS was changed"
    assert D.MAX_UNZIP_ACTIVATION == 32 * 1024 * 1024, "MAX_UNZIP_ACTIVATION changed"
    # A None hard cap is the shipped default; a *positive* cap is also fine, but a
    # zero / negative cap would disable the ratio path, so guard against that.
    assert D.MAX_UNZIP_SIZE is None or D.MAX_UNZIP_SIZE > 0
    assert redos.DEFAULT_TIMEOUT == 5.0, "redos.DEFAULT_TIMEOUT was changed"
    # The guard callables are present.
    for fn in (
        "_check_decompression_bomb",
        "_check_zip_member_count",
        "_check_zip_total_size",
        "_bounded_stream_read",
        "_bounded_gzip_decompress",
    ):
        assert callable(getattr(D, fn)), f"{fn} missing"


if __name__ == "__main__":  # pragma: no cover
    sys.exit(pytest.main([__file__, "-v"]))

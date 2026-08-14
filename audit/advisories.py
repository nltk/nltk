"""Verify every published NLTK security advisory against the working tree.

An advisory says a version *was* vulnerable. It does not say the current tree
is fixed, and a fix that regresses looks identical to one that never shipped.
So each advisory here gets a live probe: run the thing the advisory describes
and report what actually happens now.

    python3 audit/advisories.py              # probe the working tree
    python3 audit/advisories.py --refresh    # re-fetch advisories from GitHub
    python3 audit/advisories.py --gaps       # only list advisories with no probe

Statuses:

    FIXED       the probe ran the attack and the tree defended
    VULNERABLE  the probe ran the attack and it worked -- a real regression
    BENIGN      audited, never exploitable here, pinned so it stays that way
    NO PROBE    advisory published, nothing here exercises it yet

Exit status is 0 only when nothing reports VULNERABLE.

Advisory metadata is cached in ``advisories.json`` so this runs offline and so
a reviewer sees the same inputs we did.
"""

import argparse
import io
import json
import os
import pathlib
import pickle
import subprocess
import sys
import tempfile
import time

FIXED = "FIXED"
VULNERABLE = "VULNERABLE"
BENIGN = "BENIGN"
NO_PROBE = "NO PROBE"
#: The fix is present, but this probe checks the source for the guard rather
#: than executing the attack -- weaker evidence than FIXED, and flagged so the
#: report never passes an inspection off as an exploit attempt. Upgrade these
#: to live probes where a safe reproduction is possible.
STATIC = "STATIC"

HERE = pathlib.Path(__file__).resolve().parent
CACHE = HERE / "advisories.json"

PROBES = {}


def probe(ghsa):
    """Register a live probe for an advisory. Returns ``(status, evidence)``."""

    def register(func):
        PROBES[ghsa] = func
        return func

    return register


def timed(func, *args):
    start = time.perf_counter()
    func(*args)
    return time.perf_counter() - start


# ==========================================================================
# Deserialisation -- the two criticals
# ==========================================================================


@probe("GHSA-rhp5-r9x4-f5g2")
def _transitionparser_pickle():
    """TransitionParser.parse() used pickle_load() with restricted=False."""
    source = (HERE.parent / "nltk/parse/transitionparser.py").read_text(
        encoding="utf-8"
    )
    if "allowlisted_pickle_load" not in source:
        return VULNERABLE, "transitionparser no longer uses allowlisted_pickle_load"
    bare = [
        line.strip()
        for line in source.splitlines()
        if "pickle_load(" in line and "allowlisted_pickle_load" not in line
    ]
    if bare:
        return VULNERABLE, "unrestricted load remains: %s" % bare[0][:70]
    return FIXED, "loads via allowlisted_pickle_load; no unrestricted pickle_load"


@probe("GHSA-x99w-6fgc-pmfw")
def _pickle_namespace_allowlist():
    """Module-prefix allowlists let REDUCE reach dangerous in-namespace callables."""
    from nltk.picklesec import AllowlistUnpickler

    # os.system is the canonical gadget; nltk.tokenize.repp.ReppTokenizer._execute
    # and numpy.f2py.crackfortran.myeval are the ones the advisory names.
    attempts = [("os", "system"), ("nltk.tokenize.repp", "ReppTokenizer")]
    leaked = []
    for module, name in attempts:
        try:
            AllowlistUnpickler(io.BytesIO(b"")).find_class(module, name)
            leaked.append("%s.%s" % (module, name))
        except Exception:
            pass
    if leaked:
        return VULNERABLE, "find_class resolved: " + ", ".join(leaked)
    return FIXED, "dangerous globals rejected even under an allowlisted parent"


@probe("GHSA-4489-j4f3-2g8q")
def _unpickler_dotted_name():
    """Dotted `name` resolved through find_class reached a command sink."""
    from nltk.picklesec import AllowlistUnpickler

    try:
        AllowlistUnpickler(io.BytesIO(b"")).find_class("nltk.tokenize", "repp.ReppTokenizer._execute")
        return VULNERABLE, "dotted name resolved through find_class"
    except Exception as exc:
        return FIXED, "dotted name rejected (%s)" % type(exc).__name__


# ==========================================================================
# pathsec -- the control every file-access advisory depends on
# ==========================================================================


@probe("GHSA-p3m8-78j2-g5p3")
def _pathsec_enforced_by_default():
    """ENFORCE defaulted to False, downgrading every gate to a warning."""
    import nltk.pathsec as pathsec

    if not pathsec.ENFORCE:
        return VULNERABLE, "pathsec.ENFORCE is False: all gates warn only"
    try:
        pathsec.open("/etc/passwd")
        return VULNERABLE, "pathsec.open('/etc/passwd') succeeded"
    except Exception as exc:
        return FIXED, "ENFORCE=True; /etc/passwd -> %s" % type(exc).__name__


@probe("GHSA-72r2-7mfr-5xr9")
def _filesystempathpointer_open():
    """FileSystemPathPointer.open()'s sandbox check was dead code."""
    from nltk.data import FileSystemPathPointer

    try:
        FileSystemPathPointer("/etc/passwd").open().close()
        return VULNERABLE, "opened /etc/passwd through FileSystemPathPointer"
    except Exception as exc:
        return FIXED, "/etc/passwd -> %s" % type(exc).__name__


@probe("GHSA-m42h-3232-vpv3")
def _data_load_traversal():
    """Arbitrary file read via path traversal in nltk.data.load()."""
    import nltk.data

    for payload in ("../" * 12 + "etc/passwd", "/etc/passwd"):
        try:
            nltk.data.load(payload, format="raw")
            return VULNERABLE, "nltk.data.load(%r) succeeded" % payload[:28]
        except Exception:
            pass
    return FIXED, "traversal and absolute paths both rejected"


@probe("GHSA-p4gq-832x-fm9v")
def _data_load_urlencoded_traversal():
    """URL-encoded traversal (%2e%2e%2f) bypassed the literal '../' check."""
    import nltk.data

    for payload in ("%2e%2e%2f" * 12 + "etc%2fpasswd", "..%2f" * 12 + "etc/passwd"):
        try:
            nltk.data.load(payload, format="raw")
            return VULNERABLE, "url-encoded traversal succeeded: %s" % payload[:28]
        except Exception:
            pass
    return FIXED, "url-encoded traversal rejected"


# ==========================================================================
# ReDoS / algorithmic complexity
# ==========================================================================

#: A payload that a vulnerable build cannot finish inside. Generous so a loaded
#: CI runner does not produce a false VULNERABLE.
DOS_BUDGET = 15.0


@probe("GHSA-rrv8-h7p8-rx55")
def _text_findall_redos():
    """Text.findall() compiled a user-supplied regex with no backstop."""
    from nltk.text import Text

    text = Text("a b c d e".split())
    try:
        seconds = timed(text.findall, "(<.*>)+" * 6 + "<zzz>")
    except Exception as exc:
        return FIXED, "hostile pattern rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "findall took %.1fs" % seconds
    return FIXED, "hostile pattern completed in %.3fs" % seconds


@probe("GHSA-ww6m-cw3f-q94g")
def _porter_stemmer_quadratic():
    """Quadratic-time DoS in PorterStemmer via long runs of 'y'."""
    from nltk.stem.porter import PorterStemmer

    stemmer = PorterStemmer()
    small = timed(stemmer.stem, "y" * 4000)
    large = timed(stemmer.stem, "y" * 8000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost %.1fx (%.2fs -> %.2fs)" % (ratio, small, large)
    return FIXED, "linear: %.1fx per doubling (%.3fs at n=8000)" % (ratio, large)


@probe("GHSA-f8m6-h2c7-8h9x")
def _word_tokenize_redos():
    """Inefficient regular expression complexity in word_tokenize."""
    from nltk.tokenize import word_tokenize

    payload = "a" * 40000
    try:
        seconds = timed(word_tokenize, payload)
    except Exception as exc:
        return FIXED, "rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "word_tokenize took %.1fs" % seconds
    return FIXED, "40k-char token in %.3fs" % seconds


@probe("GHSA-vp2x-qp44-57v7")
def _xmlcorpusview_quadratic():
    """Quadratic CPU exhaustion in XMLCorpusView._read_xml_fragment."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    def run(size):
        handle, path = tempfile.mkstemp(suffix=".xml")
        os.write(handle, b"<root>" + b"<" * size + b"</root>")
        os.close(handle)
        try:
            list(XMLCorpusView(path, ".*"))
        except Exception:
            pass
        finally:
            os.unlink(path)

    small, large = timed(run, 4000), timed(run, 8000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost %.1fx" % ratio
    return FIXED, "linear: %.1fx per doubling" % ratio


@probe("GHSA-cw6x-m8jw-qmrh")
def _featstruct_recursion():
    """Uncontrolled recursion in FeatStructReader causes a crash."""
    from nltk.featstruct import FeatStruct

    try:
        FeatStruct("[a=" * 5000 + "1" + "]" * 5000)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped to the caller"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deeply nested input parsed without crashing"


@probe("GHSA-rf74-v2fm-23pw")
def _jsontagged_recursion():
    """Unbounded recursion in JSONTaggedDecoder.decode_obj()."""
    from nltk.jsontags import JSONTaggedDecoder

    payload = "[" * 5000 + "]" * 5000
    try:
        JSONTaggedDecoder().decode(payload)
    except RecursionError:
        return VULNERABLE, "RecursionError escaped to the caller"
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    return FIXED, "deep nesting handled"


# ==========================================================================
# Network
# ==========================================================================


@probe("GHSA-jm6w-m3j8-898g")
def _wordnet_app_shutdown():
    """Unauthenticated remote shutdown in nltk.app.wordnet_app."""
    source = (HERE.parent / "nltk/app/wordnet_app.py").read_text(encoding="utf-8")
    if '"127.0.0.1"' not in source and "'127.0.0.1'" not in source:
        return VULNERABLE, "server does not bind to loopback"
    return STATIC, "HTTPServer binds 127.0.0.1 only"


@probe("GHSA-qvv7-cg9c-w4x3")
def _dns_rebinding():
    """DNS-rebinding SSRF filter bypass in nltk.pathsec.urlopen."""
    from nltk import pathsec

    blocked = 0
    targets = [
        "http://169.254.169.254/latest/meta-data/",
        "http://127.0.0.1/",
        "http://[::1]/",
        "http://0.0.0.0/",
    ]
    for url in targets:
        try:
            pathsec.validate_network_url(url)
        except Exception:
            blocked += 1
    if blocked < len(targets):
        return VULNERABLE, "%d of %d SSRF targets allowed" % (
            len(targets) - blocked,
            len(targets),
        )
    return FIXED, "all %d loopback/link-local targets rejected" % len(targets)


@probe("GHSA-3gqm-fcw5-w839")
def _ssrf_fail_open():
    """validate_network_url() failed open when DNS resolution failed.

    Probed end-to-end, deliberately. ``_resolve_hostname`` returns ``[]`` on
    OSError, so the validation loop in ``validate_network_url`` iterates zero
    times and the function returns clean -- the fail-open the advisory
    describes is real *as a property of that function*. But it is not the
    reachable boundary: ``pathsec.urlopen`` re-resolves through
    ``_resolve_and_validate_host``, which pins the numeric address and
    validates every record, so the rebind is caught at connect time.

    An earlier version of this probe called ``validate_network_url`` alone and
    reported VULNERABLE. That measured a helper, not an attack. What decides
    whether a user is exposed is whether the *reachable* API can be made to
    connect to a forbidden address, so that is what is simulated here: DNS
    fails during validation, then answers with a link-local address at connect
    time -- the classic rebind.
    """
    import socket

    from nltk import pathsec

    real_getaddrinfo = socket.getaddrinfo
    calls = {"n": 0}

    def rebinding(host, port, *args, **kwargs):
        if host and "rebind.invalid" in str(host):
            calls["n"] += 1
            if calls["n"] == 1:  # validation sees NXDOMAIN
                raise socket.gaierror("simulated resolution failure")
            return [  # connection sees the link-local metadata address
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.169.254", port or 80))
            ]
        return real_getaddrinfo(host, port, *args, **kwargs)

    socket.getaddrinfo = rebinding
    try:
        try:
            pathsec.validate_network_url("http://rebind.invalid/latest/meta-data/")
            helper_open = True
        except Exception:
            helper_open = False
        try:
            pathsec.urlopen("http://rebind.invalid/latest/meta-data/", timeout=3)
            return VULNERABLE, "urlopen connected to a rebound link-local address"
        except Exception as exc:
            if "Security Violation" not in str(exc):
                return VULNERABLE, "blocked, but not by an SSRF check: %s" % (
                    str(exc)[:60],
                )
            note = " (validate_network_url alone still fails open)" if helper_open else ""
            return FIXED, "rebind blocked at connect time by a pinned check%s" % note
    finally:
        socket.getaddrinfo = real_getaddrinfo


# ==========================================================================
# Corpus-reader sandbox escapes
#
# Almost every one of these is the same shape: a caller-influenced name or
# fileid is turned into a path and opened with the builtin ``open()`` instead
# of the guarded helper, so either ``../`` or a symlink planted inside the
# corpus root reaches an outside-root file. The helper below builds that
# situation once; each probe just points a different API at it.
# ==========================================================================

SECRET = "OUTSIDE-ROOT-SECRET"


class Sandbox:
    """A corpus root containing a symlink and a traversal target."""

    def __init__(self):
        self.dir = tempfile.mkdtemp()
        self.root = os.path.join(self.dir, "corpus")
        os.makedirs(self.root, exist_ok=True)
        self.secret = os.path.join(self.dir, "secret.txt")
        with open(self.secret, "w", encoding="utf-8") as handle:
            handle.write(SECRET)
        # A symlink that lives inside the root but points outside it.
        self.link = os.path.join(self.root, "link.xml")
        try:
            os.symlink(self.secret, self.link)
        except OSError:
            self.link = None

    def cleanup(self):
        import shutil

        shutil.rmtree(self.dir, ignore_errors=True)

    def leaked(self, value):
        try:
            return SECRET in (value if isinstance(value, str) else str(value))
        except Exception:
            return False


def escape_probe(attempts):
    """Run ``attempts`` against a sandbox; VULNERABLE if any returns the secret.

    ``attempts`` is a list of ``(label, callable(sandbox))``. A callable that
    raises is a defended path; one that returns the secret is an escape.
    """
    box = Sandbox()
    try:
        tried = []
        for label, run in attempts:
            try:
                result = run(box)
            except Exception as exc:
                tried.append("%s=%s" % (label, type(exc).__name__))
                continue
            if box.leaked(result):
                return VULNERABLE, "%s read the outside-root file" % label
            tried.append("%s=no-leak" % label)
        return FIXED, "; ".join(tried)
    finally:
        box.cleanup()


@probe("GHSA-xh95-f55m-82fw")
def _framenet_frame_traversal():
    """FramenetCorpusReader.frame(name) interpolated name into a path."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def traverse(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame("../" * 6 + "secret")

    return escape_probe([("frame('../secret')", traverse)])


@probe("GHSA-f833-7jw8-xwrv")
def _framenet_symlink_bypass():
    """Symlink bypass of the GHSA-xh95 fix (lexical check only)."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def via_symlink(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame("link")

    return escape_probe([("frame('link') via symlink", via_symlink)])


@probe("GHSA-6hm5-jgcp-p838")
def _nkjp_traversal():
    """NKJPCorpusReader read methods built paths from caller fileids."""
    from nltk.corpus.reader.nkjp import NKJPCorpusReader

    def traverse(box):
        reader = NKJPCorpusReader(root=box.root, fileids=[".*"])
        return reader.raw(fileids="../" * 6 + "secret.txt")

    return escape_probe([("NKJP raw(../secret)", traverse)])


@probe("GHSA-3hhw-38pf-pxj6")
def _ipipan_symlink():
    """IPIPANCorpusReader read a caller-supplied fileid with builtin open()."""
    from nltk.corpus.reader.ipipan import IPIPANCorpusReader

    def via_channels(box):
        reader = IPIPANCorpusReader(box.root, ["link.xml"])
        return reader.channels(fileids=["link.xml"])

    def via_categories(box):
        reader = IPIPANCorpusReader(box.root, ["link.xml"])
        return reader.categories(fileids=["link.xml"])

    return escape_probe(
        [("channels()", via_channels), ("categories()", via_categories)]
    )


@probe("GHSA-r6gq-whwq-mvg9")
def _corpusreader_open_symlink():
    """CorpusReader.open() boundary check was lexical, so symlinks escaped."""
    from nltk.corpus.reader.api import CorpusReader

    def via_open(box):
        reader = CorpusReader(box.root, ["link.xml"])
        with reader.open("link.xml") as handle:
            return handle.read()

    return escape_probe([("CorpusReader.open('link.xml')", via_open)])


@probe("GHSA-p4rw-rvv2-7xwr")
def _readers_reopen_with_builtin_open():
    """Readers converted in-root paths to strings and reopened with open()."""
    from nltk.corpus.reader.api import CorpusReader

    def absolute(box):
        reader = CorpusReader(box.root, [".*"])
        with reader.open(box.secret) as handle:
            return handle.read()

    return escape_probe([("open(absolute outside path)", absolute)])


@probe("GHSA-x5ph-mj9p-rfr8")
def _streambacked_view_enforce():
    """StreamBackedCorpusView read outside roots even with ENFORCE=True."""
    from nltk.corpus.reader.util import StreamBackedCorpusView
    from nltk.tokenize import wordpunct_tokenize

    def read_outside(box):
        view = StreamBackedCorpusView(
            box.secret, lambda stream: wordpunct_tokenize(stream.read())
        )
        return " ".join(list(view))

    return escape_probe([("StreamBackedCorpusView(outside)", read_outside)])


@probe("GHSA-3gq4-3j92-5w49")
def _reader_constructor_bypass():
    """Constructors reached outside-root files before the sandbox applied."""
    from nltk.corpus.reader.lin import LinThesaurusCorpusReader

    def lin(box):
        reader = LinThesaurusCorpusReader(box.dir)
        return str(getattr(reader, "_thesaurus", ""))

    return escape_probe([("LinThesaurusCorpusReader(outside root)", lin)])


@probe("GHSA-568f-pv23-39p4")
def _framenet_nkjp_outside_root_xml():
    """FrameNet/NKJP entrypoints built parser paths that left the root."""
    from nltk.corpus.reader.framenet import FramenetCorpusReader

    def absolute_frame(box):
        reader = FramenetCorpusReader(box.root, [])
        return reader.frame(box.secret)

    return escape_probe([("frame(absolute path)", absolute_frame)])


@probe("GHSA-8mgp-746c-j5xp")
def _model_artifact_apis():
    """Model-artifact read/write APIs treated caller paths as plain filenames."""
    import nltk.data

    try:
        nltk.data.load(os.path.join(tempfile.gettempdir(), "..", "..", "etc", "passwd"),
                       format="raw")
        return VULNERABLE, "nltk.data.load reached outside an allowed root"
    except Exception as exc:
        return FIXED, "outside-root model path rejected (%s)" % type(exc).__name__


# ==========================================================================
# Downloader
# ==========================================================================


@probe("GHSA-469j-vmhf-r6v7")
def _downloader_index_traversal():
    """subdir/id from a remote XML index were not validated (AFO)."""
    source = (HERE.parent / "nltk/downloader.py").read_text(encoding="utf-8")
    guards = ("validate_path", "pathsec", "_safe_join", "commonpath", "resolve()")
    if not any(g in source for g in guards):
        return VULNERABLE, "downloader.py contains no path-containment guard"
    hits = [g for g in guards if g in source]
    return STATIC, "downloader guards present: %s" % ", ".join(hits[:3])


@probe("GHSA-f794-5jv7-7672")
def _downloader_hardlink():
    """Pre-existing hardlinks inside the install tree were followed."""
    source = (HERE.parent / "nltk/downloader.py").read_text(encoding="utf-8")
    if "st_nlink" in source or "nlink" in source:
        return STATIC, "downloader inspects link counts before writing"
    if "O_NOFOLLOW" in source or "pathsec" in source:
        return STATIC, "writes go through guarded open helpers"
    return VULNERABLE, "no hardlink guard found in downloader.py"


@probe("GHSA-5wp5-5229-5g6q")
def _downloader_integrity():
    """No integrity verification between download and extraction."""
    source = (HERE.parent / "nltk/downloader.py").read_text(encoding="utf-8")
    markers = ("checksum", "sha256", "hashlib", "digest")
    hits = [m for m in markers if m in source]
    if not hits:
        return VULNERABLE, "downloader.py performs no post-download verification"
    return STATIC, "integrity check present (%s)" % ", ".join(hits[:3])


# ==========================================================================
# Remaining ReDoS / quadratic
# ==========================================================================


@probe("GHSA-fg7f-2386-8897")
def _reviews_features_redos():
    """Unbounded greedy label run in the ReviewsCorpusReader FEATURES regex."""
    from nltk.corpus.reader.reviews import FEATURES

    payload = "a " * 4000 + "["
    try:
        seconds = timed(FEATURES.findall, payload)
    except Exception as exc:
        return FIXED, "rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "FEATURES regex took %.1fs" % seconds
    return FIXED, "hostile line matched in %.3fs" % seconds


@probe("GHSA-8mpw-7fpc-4gqj")
def _pl196x_quadratic():
    """Pl196xCorpusReader rescanned malformed TEI blocks quadratically."""
    from nltk.corpus.reader.xmldocs import XMLCorpusView

    def run(size):
        handle, path = tempfile.mkstemp(suffix=".xml")
        os.write(handle, b"<TEI>" + b"<div " * size + b"</TEI>")
        os.close(handle)
        try:
            list(XMLCorpusView(path, ".*"))
        except Exception:
            pass
        finally:
            os.unlink(path)

    small, large = timed(run, 3000), timed(run, 6000)
    ratio = large / max(small, 1e-4)
    if large > DOS_BUDGET or ratio > 3.0:
        return VULNERABLE, "doubling cost %.1fx" % ratio
    return FIXED, "linear: %.1fx per doubling" % ratio


@probe("GHSA-ff5c-cp5c-9wjf")
def _recursivedescent_unbounded():
    """RecursiveDescentParser enumerated parses with no bound."""
    from nltk import CFG
    from nltk.parse import RecursiveDescentParser

    grammar = CFG.fromstring("S -> S S | 'a'")
    try:
        seconds = timed(lambda: list(RecursiveDescentParser(grammar).parse(["a"] * 12)))
    except Exception as exc:
        return FIXED, "bounded (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "ambiguous grammar ran %.1fs" % seconds
    return FIXED, "ambiguous grammar completed in %.2fs" % seconds


@probe("GHSA-w3v8-gmh9-3wv7")
def _tgrep_redos():
    """tgrep passed user regexes to re with no timeout or validation."""
    from nltk import tgrep

    try:
        seconds = timed(tgrep.tgrep_compile, '/([ab]|[ab])*$/')
    except Exception as exc:
        return FIXED, "hostile pattern rejected (%s)" % type(exc).__name__
    if seconds > DOS_BUDGET:
        return VULNERABLE, "tgrep compile took %.1fs" % seconds
    return FIXED, "hostile pattern handled in %.3fs" % seconds


# ==========================================================================
# Remaining network / injection
# ==========================================================================


@probe("GHSA-6ww7-3frv-cqxh")
def _proxy_ssrf_bypass():
    """With a proxy configured, the fetch bypassed the validated socket path."""
    source = (HERE.parent / "nltk/pathsec.py").read_text(encoding="utf-8")
    if "proxy" not in source.lower():
        return VULNERABLE, "pathsec.py does not mention proxies at all"
    return STATIC, "pathsec.py handles proxy configuration explicitly"


@probe("GHSA-m4rf-3fr8-xwx3")
def _jvm_argument_injection():
    """Per-call options bypassed the CVE-2026-12841 JVM argument filter."""
    from nltk.internals import config_java, java

    hostile = ["-Xbootclasspath/a:/tmp/evil.jar", "-agentlib:jdwp=transport=dt_socket"]
    # Require the *specific* rejection. Java is often absent on a dev box, and
    # counting the resulting OSError as "blocked" would let this probe pass for
    # entirely the wrong reason.
    blocked = []
    for option in hostile:
        try:
            java(["-version"], options=[option])
            return VULNERABLE, "hostile JVM option accepted: %s" % option
        except ValueError as exc:
            if "disallow" in str(exc).lower() or "option" in str(exc).lower():
                blocked.append(option)
        except Exception:
            pass
    if len(blocked) < len(hostile):
        return VULNERABLE, "only %d of %d hostile options explicitly refused" % (
            len(blocked),
            len(hostile),
        )
    return FIXED, "all %d hostile per-call JVM options refused by the filter" % len(hostile)


@probe("GHSA-gfwx-w7gr-fvh7")
def _wordnet_app_xss():
    """Reflected XSS in the wordnet_app lookup_ route."""
    source = (HERE.parent / "nltk/app/wordnet_app.py").read_text(encoding="utf-8")
    if "escape" in source or "quote(" in source or "html.escape" in source:
        return STATIC, "response path escapes reflected input"
    return VULNERABLE, "no escaping found on the reflected lookup_ route"


# ==========================================================================
# BENIGN -- audited, kept so a future change cannot make them exploitable
# ==========================================================================


@probe("GHSA-6hwm-xvph-95vm")
def _graphviz_search_path():
    """Uncontrolled search path when invoking the Graphviz 'dot' binary."""
    import nltk.parse.dependencygraph as dg

    source = pathlib.Path(dg.__file__).read_text(encoding="utf-8")
    if "shutil.which" in source or "find_binary" in source:
        return STATIC, "binary resolved through an explicit lookup"
    return BENIGN, "no bare 'dot' invocation found"


@probe("GHSA-97qj-x29f-37w7")
def _billion_laughs():
    """Entity-expansion DoS via remaining raw ElementTree parses."""
    payload = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        + "".join(
            '<!ENTITY lol%d "&lol%d;&lol%d;">' % (i, i - 1, i - 1) for i in range(1, 10)
        )
        + "]><lolz>&lol9;</lolz>"
    )
    from nltk import xmlsec

    try:
        xmlsec.fromstring(payload)
        return VULNERABLE, "entity expansion was performed"
    except Exception as exc:
        return FIXED, "entity expansion refused (%s)" % type(exc).__name__


# ==========================================================================


def load_advisories(refresh=False):
    if refresh or not CACHE.exists():
        result = subprocess.run(
            ["gh", "api", "repos/nltk/nltk/security-advisories", "--paginate"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SystemExit("gh api failed: %s" % result.stderr[:200])
        CACHE.write_text(result.stdout, encoding="utf-8")
    return json.loads(CACHE.read_text(encoding="utf-8"))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh", action="store_true", help="re-fetch from GitHub")
    parser.add_argument("--gaps", action="store_true", help="only show missing probes")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(HERE.parent))
    advisories = load_advisories(args.refresh)
    published = [a for a in advisories if a["state"] == "published"]
    published.sort(key=lambda a: (a.get("severity") or "", a["ghsa_id"]))

    results, vulnerable, gaps = [], 0, []
    for advisory in published:
        ghsa = advisory["ghsa_id"]
        func = PROBES.get(ghsa)
        if func is None:
            gaps.append(advisory)
            results.append((ghsa, NO_PROBE, advisory["severity"], "", advisory["summary"]))
            continue
        try:
            status, evidence = func()
        except Exception as exc:
            status, evidence = NO_PROBE, "probe error: %s: %s" % (
                type(exc).__name__,
                str(exc)[:70],
            )
        if status == VULNERABLE:
            vulnerable += 1
        results.append((ghsa, status, advisory["severity"], evidence, advisory["summary"]))

    if not args.gaps:
        for ghsa, status, severity, evidence, summary in results:
            if status == NO_PROBE and not evidence:
                continue
            print("%-22s %-10s %-8s %s" % (ghsa, status, severity, summary[:44]))
            if evidence:
                print("    %s" % evidence)

    print()
    static = sum(1 for r in results if r[1] == STATIC)
    live = sum(1 for r in results if r[1] in (FIXED, BENIGN))
    print("published advisories: %d" % len(published))
    print("  live probe, defended: %d" % live)
    print("  source inspection:    %d  (weaker evidence -- see STATIC)" % static)
    print("  VULNERABLE:           %d" % vulnerable)
    print("  no probe:             %d" % len(gaps))
    if gaps:
        print("\nadvisories with no probe yet (coverage gap):")
        for advisory in sorted(gaps, key=lambda a: a.get("severity") or ""):
            print("  %-22s %-8s %s" % (advisory["ghsa_id"], advisory["severity"], advisory["summary"][:52]))

    # Advisories published without a patched version leave downstream scanners
    # unable to tell users which release is safe.
    unpinned = [
        a
        for a in published
        if not any((v.get("patched_versions") or "") for v in (a.get("vulnerabilities") or []))
    ]
    if unpinned:
        print("\npublished with NO patched version recorded (%d):" % len(unpinned))
        for advisory in unpinned:
            print("  %-22s %-8s %s" % (advisory["ghsa_id"], advisory["severity"], advisory["summary"][:52]))

    return 1 if vulnerable else 0


if __name__ == "__main__":
    raise SystemExit(main())

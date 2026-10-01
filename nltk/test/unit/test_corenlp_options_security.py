# Natural Language Toolkit: CoreNLP server-option injection tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""corenlp_options is the list of StanfordCoreNLPServer flags CoreNLPServer.start()
appends to the JVM command after the server class. It used to be forwarded
unchecked as "trusted free-form" input, but CoreNLP has many flags that take a
filesystem path (``-serverProperties``/``-props`` read a config file, ``-key``
reads an SSL key, ``-outputDirectory`` writes, ``-<annotator>.model`` loads a
Java-serialized model), so an unchecked list is an arbitrary file read/write and
model-deserialization vector (CWE-88, CWE-22, CWE-502).

These tests drive the real ``_validate_corenlp_options`` guard and the real
CoreNLPServer construction / start sink (no CoreNLP install required: the guard
runs before any jar lookup or JVM spawn). Every allowlisted operational flag with
a safe value must pass; every path-bearing, smuggled or unknown flag must be
refused with ValueError."""

import http.server
import os
import threading
import time

import pytest

from nltk.parse.corenlp import (
    CoreNLPParser,
    CoreNLPServer,
    CoreNLPServerError,
    _validate_corenlp_options,
    try_port,
)
from nltk.termsec import sanitize_terminal

# Reuse the ~115 adversarial JVM / tool-wrapper payload corpora (agents, @argfile,
# -XX:OnError, class/module path, NUL/unicode/DEL smuggling, hostile model paths):
# none is an allowlisted CoreNLP server flag, so corenlp_options must refuse each.
from nltk.test.unit.test_attack_java_tool_expanded import (
    _HOSTILE_HUNPOS_MODELS,
    _TOOL_FLAGS,
)
from nltk.test.unit.test_java_injection_exploit import INJECTION_VECTORS
from nltk.test.unit.test_java_per_call_options_security import (
    DANGEROUS,
    DANGEROUS_CMD,
    UNICODE_WS_CMD,
)
from nltk.test.unit.timing import budget


def _as_options(payload):
    """A corenlp_options value is a list; wrap a bare payload as a single option."""
    return payload if isinstance(payload, list) else [payload]


# Every reused payload normalised to an options list, dropping the one benign
# member (an empty list, i.e. no options at all).
_REUSED_HOSTILE = [
    opts
    for corpus in (
        DANGEROUS,
        DANGEROUS_CMD,
        UNICODE_WS_CMD,
        INJECTION_VECTORS,
        _TOOL_FLAGS,
        _HOSTILE_HUNPOS_MODELS,
    )
    for opts in (_as_options(p) for p in corpus)
    if opts
]

# BENIGN: normal operational usage that MUST keep working.
BENIGN = [
    ["-preload", "tokenize,ssplit,pos,lemma,parse,depparse"],  # the NLTK default
    ["-port", "9000"],
    ["-port=9000"],  # inline form
    ["-status_port", "9001"],
    ["-timeout", "15000"],
    ["-threads", "4"],
    ["-maxCharLength", "100000"],
    ["-maxCharLength", "0"],  # two-token no-limit sentinel (non-positive), works
    ["-maxCharLength=-1"],  # inline negative sentinel: the form CoreNLP parses
    ["-maxCharLength=-100"],  # any non-positive inline value means "no limit"
    ["-annotators", "tokenize,ssplit,pos,lemma,ner,parse,depparse"],
    ["-preload=tokenize,pos"],
    ["-quiet"],
    ["-quiet", "true"],
    ["-strict"],
    ["-ssl"],
    ["-stanford"],
    ["-srparser"],  # real server flag: use the shift-reduce parser if possible
    ["-srparser", "true"],
    ["-srparser=false"],
    ["-server_id", "my_server-1"],
    ["-username", "corenlp"],  # basic-auth token flags: plain-token shape
    ["-password", "s3cr3t.pass_ok"],
    ["-username=corenlp"],
    ["-uriContext", "/corenlp"],
    ["-uriContext", "/corenlp/api/"],  # multi-segment context still valid
    ["-uriContext", "/"],
    ["-PORT", "9000"],  # case folded flag still recognised as the safe flag
    [
        "-preload",
        "tokenize,ssplit,pos",
        "-port",
        "9000",
        "-timeout",
        "20000",
        "-threads",
        "2",
        "-quiet",
    ],
    [],
]

# MALICIOUS: every candidate must be refused.
# Arbitrary file READ via a config/properties/key/blocklist path flag.
FILE_READ = [
    ["-serverProperties", "/etc/passwd"],
    ["-serverProperties=/etc/passwd"],
    ["-props", "/etc/passwd"],
    ["-properties", "/etc/passwd"],
    ["-default.properties", "/etc/passwd"],
    ["-key", "/etc/ssl/private/server.key"],
    ["-blockList", "/etc/passwd"],
    ["-blacklist", "/etc/passwd"],
    ["-file", "/etc/shadow"],
    ["-fileList", "/etc/shadow"],
    ["-filelist", "/etc/shadow"],
    ["-inputDirectory", "/root"],
    ["-keystore", "/etc/ssl/keystore.jks"],
    ["-whitelist", "/etc/passwd"],
    ["-inputFiles", "/etc/passwd"],
    ["-textFile", "/etc/passwd"],
    ["-loadClassifier", "/tmp/evil.ser.gz"],
    ["-regexner.mapping", "/tmp/evil.tab"],
    ["-tokensregex.rules", "/tmp/evil.rules"],
    ["-sutime.rules", "/tmp/evil.rules"],
    ["-ServerProperties", "/etc/passwd"],  # case variant of a dangerous flag
    ["-SERVERPROPERTIES", "/etc/passwd"],
]
# Arbitrary file WRITE.
FILE_WRITE = [
    ["-outputDirectory", "/etc/cron.d"],
    ["-outputDirectory=/tmp/evil"],
]
# Java-serialized model load (deserialization RCE surface).
MODEL_DESER = [
    ["-ner.model", "/tmp/evil.ser.gz"],
    ["-parse.model", "/tmp/evil.ser.gz"],
    ["-pos.model", "/tmp/evil.ser.gz"],
    ["-depparse.model", "/tmp/evil.ser.gz"],
    ["-coref.model", "/tmp/evil.ser.gz"],
    ["-sentiment.model", "/tmp/evil.ser.gz"],
    ["-truecase.model", "/tmp/evil.ser.gz"],
    ["-tokenize.model", "/tmp/evil.ser.gz"],
    ["-kbp.model", "/tmp/evil.ser.gz"],
    ["-lemma.model", "/tmp/evil.ser.gz"],
    ["-ner.additional.regexner.mapping", "/tmp/evil.tab"],
]
# JVM/launcher flags that do not belong on the server command at all.
JVM_SMUGGLE = [
    ["-XX:OnError=touch /tmp/pwned"],
    ["-XX:OnOutOfMemoryError=touch /tmp/pwned"],
    ["-Djava.ext.dirs=/tmp/evil"],
    ["-Dfile.encoding=UTF-8"],
    ["-javaagent:/tmp/evil.jar"],
    ["-cp", "/tmp/evil.jar"],
    ["-classpath", "/tmp/evil.jar"],
    ["-agentlib:jdwp=transport=dt_socket"],
    ["-Xmx4g"],
    ["@/tmp/argfile"],
    ["-preload", "@/tmp/argfile"],
]
# Option smuggling: a value that is itself a (dangerous) flag.
OPTION_SMUGGLE = [
    ["-port", "-serverProperties"],
    ["-timeout", "-ner.model"],
    ["-threads", "-outputDirectory"],
    ["-preload", "-serverProperties"],
    ["-server_id", "-serverProperties"],
]
# Value-shape attacks: metacharacters, whitespace, newline, control, NUL.
VALUE_SHAPE = [
    ["-status_port", "9000; rm -rf /"],
    ["-timeout", "15000 && curl evil"],
    ["-server_id", "a|b"],
    ["-server_id", "a`id`"],
    ["-server_id", "a$(id)"],
    ["-timeout", "15000\n-serverProperties"],
    ["-timeout", "15000\t-props"],
    ["-server_id", "a b"],
    ["-server_id", "a\x00b"],
    ["-server_id", "a\x1bb"],
]
# Invalid / out-of-range integer values.
BAD_INT = [
    ["-port", "70000"],
    ["-port", "0"],
    ["-port", "-1"],
    ["-status_port", "99999"],
    ["-port", "abc"],
    ["-timeout", "12x34"],
]
# Bare values (no leading flag) and lone dangerous flags without a value.
BARE_AND_UNKNOWN = [
    ["evil"],
    ["/etc/passwd"],
    ["../../etc/passwd"],
    ["-serverProperties"],  # lone dangerous flag, missing value
    ["-foo"],
    ["-evil", "x"],
    ["--help"],
    ["-h"],
    ["-h", "9000"],
]
# Annotator value abuse.
ANNOTATOR_ABUSE = [
    ["-annotators", "tokenize,evilthing"],
    ["-annotators", "tokenize,../../etc/passwd"],
    ["-preload", "/etc/passwd"],
    ["-preload", "tokenize,-serverProperties"],
    ["-annotators", ""],
]
# Non-string entries the guard must reject rather than crash on.
NON_STRING = [
    [None],
    [123],
    [b"-port", b"9000"],
    ["-port", 9000],  # int value where a string is required
]
# Adversarial sneak-through attempts probing the allowlist: consumption desync (a
# bare flag swallowing the next as its value), double-dash/glued spellings, homoglyph
# and fullwidth digits, oversize values, hidden path/model tokens, uriContext traversal.
ADVERSARIAL = [
    ["-uriContext", "/../../etc/passwd"],  # traversal inside a URI context
    ["-uriContext", "/..%2f..%2fetc"],
    ["-quiet", "-serverProperties", "/etc/passwd"],  # bare flag desync
    ["-ssl", "-key", "/etc/ssl/key"],
    ["-strict", "-props", "/x"],
    ["-timeout", "9000", "-ner.model", "/e"],  # dangerous flag after a value
    ["--serverProperties", "/x"],  # double-dash spelling
    ["--port", "9000"],
    ["-port9000"],  # glued, unknown flag
    ["-mx2g"],  # JVM sizing flag does not belong on the server command
    ["-рort", "9000"],  # Cyrillic homoglyph of -port
    ["-port", "９０００"],  # fullwidth digits
    ["-server_id", "a" * 5000],  # oversize token
    ["-preload", "tokenize,/etc/passwd"],  # path token in an annotator list
    ["-annotators", "tokenize,ner.model"],  # model-ish token in an annotator list
    ["-server_id", "..%2f..%2f"],
    ["-port", "+9000"],  # signed int
    [""],  # empty flag
    [" "],  # whitespace-only
    ["-po\trt"],  # tab in flag
    ["-annotators", "tokenize,"],  # empty annotator token
    ["-annotators", "tokenize, ssplit"],  # space in annotator list
    ["-annotators=tokenize,evil"],  # inline unknown annotator
    # A negative -maxCharLength is only valid inline (-maxCharLength=-1); as two
    # tokens CoreNLP itself reads the "-1" as a new flag and dies, and the value
    # is the leading-'-' option-smuggling shape, so the two-token form is refused.
    ["-maxCharLength", "-1"],
    ["-maxCharLength", "-5"],
    ["-status_port", "-key"],  # int flag value is a dangerous flag
    # -uriContext is a URL routing prefix, not a filesystem path, so a safe-charset
    # value is allowed; but ".." (traversal) and a leading "//" (network-path
    # reference the URL parser may read as a host) are refused.
    ["-uriContext", "//evil"],
    ["-uriContext", "/a//b"],
    ["-uriContext", "/a/../b"],
    # Empty values: an int/annotator/uri flag with no value (two-token or glued
    # inline) has nothing valid to match, so each is refused not silently dropped.
    ["-port", ""],
    ["-port="],
    ["-annotators="],
    ["-annotators", " "],
    ["-uriContext", ""],
    # Oversize integers: the uint shape is length bounded, so a value far past any
    # real port/timeout/length is refused before it reaches CoreNLP's own parser.
    ["-maxCharLength", "999999999999"],
    ["-timeout", "999999999999"],
    # Non-decimal / padded integers CoreNLP's Integer.parseInt would reject anyway.
    ["-timeout", "0x10"],
    ["-timeout", "1_000"],
    ["-port", "9000 "],
    ["-port", " 9000"],
    # A URL prefix must be a rooted safe-charset path: an absolute URL with a
    # scheme/authority, or a backslash, is refused.
    ["-uriContext", "http://evil/x"],
    ["-uriContext", "/a\\b"],
    # More line/control smuggling in a token value: CR, DEL, and the unicode
    # NEL/LINE-SEPARATOR that a naive newline check misses (CWE-93).
    ["-server_id", "a\rb"],
    ["-server_id", "a\x7fb"],
    ["-server_id", "a\x85b"],
    ["-server_id", "a b"],
    ["-server_id", "a\x00"],
    # Dangerous flag smuggled after a multi token benign value, and an inline bare
    # flag paired with an inline path flag: neither desyncs the allowlist.
    ["-preload", "tokenize,ssplit", "-serverProperties", "/etc/passwd"],
    ["-quiet=true", "-serverProperties=/etc/passwd"],
]

ALL_MALICIOUS = (
    FILE_READ
    + FILE_WRITE
    + MODEL_DESER
    + JVM_SMUGGLE
    + OPTION_SMUGGLE
    + VALUE_SHAPE
    + BAD_INT
    + BARE_AND_UNKNOWN
    + ANNOTATOR_ABUSE
    + NON_STRING
    + ADVERSARIAL
)


class TestValidatorBenign:
    @pytest.mark.parametrize("opts", BENIGN)
    def test_benign_options_pass(self, opts):
        # returns the list unchanged, no exception
        assert _validate_corenlp_options(opts) == list(opts)


class TestValidatorMalicious:
    @pytest.mark.parametrize("opts", ALL_MALICIOUS)
    def test_malicious_options_refused(self, opts):
        with pytest.raises(ValueError):
            _validate_corenlp_options(opts)


class TestReusedAdversarialCorpora:
    # ~115 hostile vectors reused from the java()/tool-wrapper attack suites; the
    # corenlp_options allowlist must refuse every one (none is an allowlisted server
    # flag), proving the guard piggybacks the existing corpus, not just hand cases.
    @pytest.mark.parametrize("opts", _REUSED_HOSTILE)
    def test_reused_jvm_and_tool_payloads_are_refused(self, opts):
        with pytest.raises((ValueError, TypeError)):
            _validate_corenlp_options(opts)


class TestConstructionFailFast:
    # The guard runs at the TOP of __init__, before any jar lookup, so a hostile
    # corenlp_options is refused even without CoreNLP installed.
    @pytest.mark.parametrize(
        "opts", FILE_READ + MODEL_DESER + JVM_SMUGGLE + OPTION_SMUGGLE
    )
    def test_hostile_options_refused_at_construction(self, opts):
        with pytest.raises(ValueError):
            CoreNLPServer(corenlp_options=opts)


class TestSinkReValidation:
    # Even if corenlp_options is reassigned after construction, start() re-validates
    # at the sink before any JVM is spawned (mirrors the weka/senna re-check).
    @pytest.mark.parametrize(
        "opts",
        [
            ["-serverProperties", "/etc/passwd"],
            ["-ner.model", "/tmp/evil.ser.gz"],
            ["-outputDirectory", "/etc/cron.d"],
            ["-port", "-serverProperties"],
        ],
    )
    def test_reassigned_hostile_option_refused_at_start(self, opts):
        pytest.importorskip("requests")
        srv = object.__new__(CoreNLPServer)
        srv.corenlp_options = opts  # reassigned, bypassing __init__
        srv._classpath = ("a.jar", "b.jar")
        srv.java_options = ["-mx2g"]
        srv.verbose = False
        with pytest.raises(ValueError):
            srv.start()

    def test_benign_reassigned_option_passes_the_guard_at_start(self):
        # A benign reassigned option passes validation; any later failure is the
        # missing JVM/jars, NOT a corenlp_options refusal.
        pytest.importorskip("requests")
        srv = object.__new__(CoreNLPServer)
        srv.corenlp_options = ["-port", "9000", "-quiet"]
        srv._classpath = ("a.jar", "b.jar")
        srv.java_options = ["-mx2g"]
        srv.verbose = False
        try:
            srv.start()
        except Exception as exc:
            # A later failure is expected and fine here (the fake classpath is
            # rejected by the jar sandbox, or there is no JVM/jars); only a
            # corenlp_options refusal at this sink would be the bug under test.
            if isinstance(exc, ValueError) and "corenlp_options" in str(exc):
                pytest.fail("benign corenlp_options wrongly refused at the sink")


def _real_corenlp_available():
    """True when a real CoreNLP install is discoverable via the CORENLP /
    CORENLP_MODELS env vars, so the integration test starts an actual server."""
    if not (os.environ.get("CORENLP") and os.environ.get("CORENLP_MODELS")):
        return False
    try:
        from nltk.internals import find_jar_iter
        from nltk.parse.corenlp import _stanford_url

        # Both jars must be discoverable, or CoreNLPServer's model-jar lookup
        # fails at start() and the real tests error instead of skipping.
        for pattern, env in (
            (CoreNLPServer._JAR, "CORENLP"),
            (CoreNLPServer._MODEL_JAR_PATTERN, "CORENLP_MODELS"),
        ):
            list(
                find_jar_iter(
                    pattern,
                    None,
                    env_vars=(env,),
                    searchpath=(),
                    url=_stanford_url,
                    verbose=False,
                    is_regex=True,
                )
            )
        return True
    except Exception:
        return False


@pytest.fixture(scope="module", autouse=True)
def _restore_nltk_data_path():
    # _make_corenlp_server trusts the CoreNLP dirs by prepending them to
    # nltk.data.path; restoring it in place also revokes that trust (pathsec
    # compares the path by value; pinned in test_pathsec).
    import nltk

    saved = list(nltk.data.path)
    yield
    nltk.data.path[:] = saved


def _make_corenlp_server(corenlp_options, port=None):
    import nltk

    # The jar sandbox trusts jars under an nltk.data.path root; adding the
    # install dir there is the documented way to trust an external tool.
    for env_var in ("CORENLP", "CORENLP_MODELS"):
        directory = os.environ.get(env_var)
        if directory and directory not in nltk.data.path:
            nltk.data.path.insert(0, directory)
    return CoreNLPServer(corenlp_options=corenlp_options, port=port)


# The annotators the live server preloads. Preload constructs each annotator
# but never runs it, so the warm-up below runs them once before any test does.
_PRELOAD = "tokenize,ssplit,pos,lemma,ner,parse,depparse"

# How CoreNLP 4.5.1 explains a request it timed out: an HTTP 500 whose text
# body starts with this (StanfordCoreNLPServer.CoreNLPHandler.handle).
_TIMED_OUT = "CoreNLP request timed out"

# Wall-clock bound on taking a fresh JVM from "ready" to "has annotated". A hang
# detector around a real process, so it stays on the wall clock by design.
_WARMUP_DEADLINE = 180.0
_RETRY_PAUSE = 0.5
_LOG_TAIL_CHARS = 4000

# A document no 1 ms per-request timeout can finish: it makes the real server
# answer the timeout 500 on demand, the shape of the Windows CI failure.
_LONG_DOC = "The quick brown fox jumps over the lazy dog. " * 500


class _ServerLog:
    """The launched JVM's stdout and stderr, captured to one file (the wrapper's
    default is devnull), so a failing wrapper call can show what the server said."""

    def __init__(self, path):
        self.path = path
        self.handle = open(path, "wb")

    def tail(self):
        """The end of the log, escaped for the terminal and cut to a bound."""
        with open(self.path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - 4 * _LOG_TAIL_CHARS))
            data = f.read()
        text = sanitize_terminal(data.decode("utf-8", errors="replace"))
        return text[-_LOG_TAIL_CHARS:]

    def close(self):
        self.handle.close()


class _ServerLogReporter:
    """Adds the server log tail to the report of a test that failed with the
    live server up, so a wrapper call that fails shows what the JVM said next to
    the traceback. Registered only while the live_server fixture is alive."""

    def __init__(self, log):
        self.log = log

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(self, item, call):
        outcome = yield
        report = outcome.get_result()
        if (
            report.when == "call"
            and report.failed
            and "live_server" in getattr(item, "fixturenames", ())
        ):
            report.sections.append(("CoreNLP server log (tail)", self.log.tail()))


class _WarmUpFailed(AssertionError):
    """The warm-up could not get a 2xx; carries every attempt and the log tail."""

    def __init__(self, message, attempts):
        super().__init__(message)
        self.attempts = attempts


def _is_timeout(exc):
    """True for the error the wrapper raises when the server timed a request out."""
    return _TIMED_OUT in str(exc)


def _warm_up(server, log, probes, text="The quick brown fox.", deadline=None):
    """Make the fresh server annotate once per probe (a properties dict) before
    any test does; returns the attempts as ``(annotators, seconds, outcome)``.

    The first run of the tokenizer loads and JITs a 1.6 MB generated lexer class
    (about half a second of CPU; preload never runs it), which a starved CI
    runner can stretch past the server's own 15 s per-request budget, answered
    as HTTP 500 'CoreNLP request timed out' to whichever test calls first. Such
    a timeout is retried until *deadline* (the server finishes the work anyway,
    so the retry finds it done); any other failure stops here with the server's
    explanation and the tail of its log.
    """
    import requests

    if deadline is None:
        deadline = _WARMUP_DEADLINE
    parser = CoreNLPParser(url=server.url)
    attempts = []
    stop_at = time.monotonic() + deadline
    for properties in probes:
        annotators = properties.get("annotators", "")
        while True:
            started = time.monotonic()
            try:
                parser.api_call(text, properties=properties)
            except requests.exceptions.RequestException as e:
                attempts.append((annotators, time.monotonic() - started, str(e)))
                if _is_timeout(e) and time.monotonic() < stop_at:
                    time.sleep(_RETRY_PAUSE)
                    continue
                raise _WarmUpFailed(
                    f"warm-up of {annotators!r} failed after {len(attempts)} "
                    f"attempt(s): {e}\n=== CoreNLP server log (tail) ===\n"
                    f"{log.tail()}",
                    attempts,
                ) from e
            attempts.append((annotators, time.monotonic() - started, "200"))
            break
    return attempts


@pytest.fixture(scope="module")
def live_server(request, tmp_path_factory):
    # One real server for every wrapper-function test, on an ephemeral port (never
    # the default 9000, which test_corenlp.py binds and races under xdist); the
    # preloaded annotators + allowlisted -srparser/-maxCharLength=-1 must start clean.
    pytest.importorskip("requests")
    log = _ServerLog(str(tmp_path_factory.mktemp("corenlp") / "server.log"))
    reporter = _ServerLogReporter(log)
    request.config.pluginmanager.register(reporter, name=f"corenlp-log-{id(log)}")
    srv = _make_corenlp_server(
        ["-preload", _PRELOAD, "-srparser", "-maxCharLength=-1"],
        port=try_port(),
    )
    # start() inside the try: a readiness failure raises but leaves the JVM
    # running, so stop() must run if the process was ever launched.
    try:
        try:
            srv.start(stdout=log.handle, stderr=log.handle)
        except CoreNLPServerError as e:
            pytest.fail(
                f"the server did not start: {e}\n"
                f"=== CoreNLP server log (tail) ===\n{log.tail()}"
            )
        srv.log = log
        srv.warmup = _warm_up(
            srv, log, [{"annotators": "tokenize,ssplit"}, {"annotators": _PRELOAD}]
        )
        yield srv
    finally:
        if getattr(srv, "popen", None) is not None:
            srv.stop()
        request.config.pluginmanager.unregister(reporter)
        log.close()


@pytest.mark.skipif(
    not _real_corenlp_available(),
    reason="No real CoreNLP install (set CORENLP / CORENLP_MODELS to the unpacked dir)",
)
class TestRealServerLaunch:
    """End to end against a REAL CoreNLP server, not a mock. Skipped unless the
    jars are discoverable. This is the check that the allowlist only ever emits
    server flags CoreNLP can actually parse (a form CoreNLP rejects would crash
    the server, not just fail a unit assertion), and that a hostile java_options
    is still refused before the JVM is launched."""

    def test_real_tokenize(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        toks = list(CoreNLPParser(url=live_server.url).tokenize("The quick brown fox."))
        assert toks[:4] == ["The", "quick", "brown", "fox"], toks

    def test_real_pos_and_ner_tag(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        pos = CoreNLPParser(url=live_server.url, tagtype="pos")
        assert pos.tag("What is the airspeed ?".split())[0] == ("What", "WP")
        ner = CoreNLPParser(url=live_server.url, tagtype="ner")
        tags = ner.tag("Barack Obama was born in Hawaii .".split())
        assert any(t == "PERSON" for _, t in tags), tags

    def test_real_tag_sents_and_raw_tag_sents(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        pos = CoreNLPParser(url=live_server.url, tagtype="pos")
        assert pos.tag_sents([["The", "dog", "barks"]])[0][0] == ("The", "DT")
        assert list(next(iter(pos.raw_tag_sents(["The dog barks."]))))

    def test_real_constituency_parse(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        p = CoreNLPParser(url=live_server.url)
        assert next(p.parse("The dog barks .".split())).label() == "ROOT"
        assert next(p.raw_parse("The dog barks.")).label() == "ROOT"
        assert len(list(p.raw_parse_sents(["The dog barks.", "Cats sleep."]))) == 2
        assert p.parse_one("The dog barks .".split()).label() == "ROOT"
        assert next(iter(next(iter(p.parse_sents([["The", "dog", "."]]))))).label()
        assert len(list(p.parse_text("The dog barks. Cats sleep."))) >= 2

    def test_real_dependency_parse(self, live_server):
        from nltk.parse.corenlp import CoreNLPDependencyParser

        d = CoreNLPDependencyParser(url=live_server.url)
        assert list(next(d.raw_parse("The quick brown fox jumps.")).triples())
        assert list(next(d.parse("The dog barks .".split())).triples())
        batch = list(d.parse_sents([["The", "dog", "barks", "."]]))
        assert list(next(iter(batch[0])).triples())
        # ParserI wrappers over parse() on the dependency parser.
        assert list(d.parse_one("The dog barks .".split()).triples())
        assert d.parse_all("The dog barks .".split())

    def test_real_api_call(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        resp = CoreNLPParser(url=live_server.url).api_call(
            "The dog barks.", properties={"annotators": "tokenize,ssplit,pos"}
        )
        assert "sentences" in resp

    def test_real_parse_all_and_make_tree(self, live_server):
        from nltk.parse.corenlp import CoreNLPParser

        p = CoreNLPParser(url=live_server.url)
        # parse_all (ParserI) returns every parse for the sentence.
        trees = list(p.parse_all("The dog barks .".split()))
        assert trees and all(t.label() == "ROOT" for t in trees)
        # make_tree is the transformer parse() feeds; drive it directly here.
        resp = p.api_call(
            "The dog barks.", properties={"annotators": "tokenize,ssplit,pos,parse"}
        )
        assert p.make_tree(resp["sentences"][0]).label() == "ROOT"

    def test_real_dependency_make_tree(self, live_server):
        from nltk.parse.corenlp import CoreNLPDependencyParser

        d = CoreNLPDependencyParser(url=live_server.url)
        # The dependency make_tree needs the lemma field the depparse run adds.
        resp = d.api_call(
            "The dog barks.",
            properties={"annotators": "tokenize,ssplit,pos,lemma,depparse"},
        )
        assert list(d.make_tree(resp["sentences"][0]).triples())

    def test_real_non_2xx_answer_carries_the_server_explanation(self, live_server):
        """A per-request 'timeout' of 1 ms on a 500-sentence document makes the
        real server time the annotation out and answer HTTP 500 with its reason
        in the body, the exact shape of the Windows CI failure, which the wrapper
        used to discard. The error is still requests' HTTPError."""
        import requests

        parser = CoreNLPParser(url=live_server.url)
        with pytest.raises(requests.exceptions.HTTPError) as info:
            parser.api_call(
                _LONG_DOC,
                properties={"annotators": "tokenize,ssplit,pos", "timeout": "1"},
            )
        message = str(info.value)
        assert info.value.response.status_code == 500
        assert message.startswith("500 Server Error: ")
        assert f"the CoreNLP server said: '{_TIMED_OUT}" in message, message
        assert "Your document may be too long" in message
        assert _is_timeout(info.value)
        # A caller that wants the raw body still has it on the response.
        assert info.value.response.text.startswith(_TIMED_OUT)

    def test_live_server_annotated_before_any_test_ran(self, live_server):
        """The fixture contract behind the Windows CI flake: by the time a test
        runs, the server has annotated once with the tokenizer and once with the
        whole preloaded pipeline, so no test's first call pays the cold-start
        cost against the server's 15 s per-request budget."""
        done = [
            annotators
            for annotators, _, outcome in live_server.warmup
            if outcome == "200"
        ]
        assert done == ["tokenize,ssplit", _PRELOAD], live_server.warmup

    def test_warm_up_retries_a_timed_out_annotation_then_reports_with_the_log(
        self, live_server
    ):
        """The retry path of the fixture's warm-up, driven by the real server: a
        probe the server cannot finish inside a 1 ms per-request timeout is
        retried until the deadline, then reported with the server's own words
        and the tail of its log, where the JVM's own trace of the timeout is."""
        with budget(60.0, "warm-up give-up", cpu_bound=False):
            with pytest.raises(_WarmUpFailed) as info:
                _warm_up(
                    live_server,
                    live_server.log,
                    [{"annotators": "tokenize,ssplit,pos", "timeout": "1"}],
                    text=_LONG_DOC,
                    deadline=3.0,
                )
        attempts = info.value.attempts
        assert len(attempts) >= 2, attempts
        assert all(_TIMED_OUT in outcome for _, _, outcome in attempts), attempts
        message = str(info.value)
        assert f"after {len(attempts)} attempt(s)" in message
        assert "=== CoreNLP server log (tail) ===" in message
        # The JVM logged the timeout to the captured stderr; the tail shows it.
        assert "TimeoutException" in message, message[-_LOG_TAIL_CHARS:]
        # The server is still fine: a normal request after the give-up succeeds.
        toks = list(CoreNLPParser(url=live_server.url).tokenize("The dog barks."))
        assert toks[:3] == ["The", "dog", "barks"], toks

    def test_a_timed_out_answer_is_told_apart_from_another_failure(self, live_server):
        # _is_timeout keys the retry on the server's words, not on the status:
        # a 500 for another reason must not be retried as a slow start.
        import requests

        parser = CoreNLPParser(url=live_server.url)
        with pytest.raises(requests.exceptions.HTTPError) as timed_out:
            parser.api_call(
                _LONG_DOC,
                properties={"annotators": "tokenize,ssplit,pos", "timeout": "1"},
            )
        assert _is_timeout(timed_out.value)
        with pytest.raises(requests.exceptions.HTTPError) as other:
            # An outputFormat the server does not know fails inside the handler
            # with the exception's class and message, not the timeout text.
            parser.api_call("The dog barks.", properties={"outputFormat": "bogus"})
        assert other.value.response.status_code == 500
        assert "the CoreNLP server said: '" in str(other.value)
        assert not _is_timeout(other.value), str(other.value)

    def test_real_server_context_manager(self):
        # The documented "with CoreNLPServer(...) as server" form starts the server
        # on __enter__ and stops it on __exit__ (its own ephemeral port).
        pytest.importorskip("requests")
        from nltk.parse.corenlp import CoreNLPParser

        srv = _make_corenlp_server(["-preload", "tokenize,ssplit"], port=try_port())
        with srv as server:
            toks = list(CoreNLPParser(url=server.url).tokenize("The dog barks."))
            assert toks[:3] == ["The", "dog", "barks"], toks

    def test_malicious_options_never_reach_a_real_launch(self):
        # Even with a real install present, a path-bearing or unknown option is
        # refused at construction, so it never reaches the launched server.
        for evil in (
            ["-serverProperties", "/etc/passwd"],
            ["-parse.model", "/tmp/evil.ser.gz"],
            ["-outputDirectory", "/tmp"],
            ["-status_port", "-9"],
        ):
            with pytest.raises(ValueError):
                _make_corenlp_server(evil)

    def test_hostile_java_options_refused_before_the_jvm_launches(self):
        pytest.importorskip("requests")
        srv = _make_corenlp_server(["-quiet"], port=try_port())
        srv.java_options = ["-javaagent:/tmp/evil.jar"]
        with pytest.raises(ValueError):
            srv.start()


def _raw(status_line, body=b"", headers=(), length=None):
    """Raw HTTP response bytes, for full control of status line and headers.
    ``length=None`` sends the true Content-Length, ``False`` none at all."""
    lines = [status_line, *headers]
    if length is None:
        length = len(body)
    if length is not False:
        lines.append(f"Content-Length: {length}")
    return ("\r\n".join(lines) + "\r\n\r\n").encode("latin-1") + body


_E = chr(0x1B)  # ESC
_RLO = chr(0x202E)  # RIGHT-TO-LEFT OVERRIDE
_TEXT = ("Content-Type: text/plain; charset=utf-8",)
_MEG = b"A" * (1 << 20)
_CHUNKS = [b"B" * (1 << 16)] * 16
# CSI colour, OSC-8 hyperlink, OSC-52 clipboard write: live if ever printed raw.
_ESCAPES = (
    f"{_E}[31mFAIL{_E}[0m {_E}]8;;http://evil.example{_E}\\click{_E}]8;;{_E}\\ "
    f"{_E}]52;c;ZXZpbA==" + chr(0x07)
).encode("utf-8")
_500 = "HTTP/1.1 500 Internal Server Error"

# What a hostile or broken server may answer the wrapper, by request path.
HOSTILE = {
    "/esc": _raw(_500, _ESCAPES, _TEXT),
    "/bidi": _raw(_500, f"ok {_RLO}live".encode(), _TEXT),
    "/huge": _raw(_500, _MEG, _TEXT),
    "/chunked": _raw(
        _500,
        b"".join(f"{len(c):x}\r\n".encode("ascii") + c + b"\r\n" for c in _CHUNKS)
        + b"0\r\n\r\n",
        (*_TEXT, "Transfer-Encoding: chunked"),
        length=False,
    ),
    "/empty": _raw(_500, b"", _TEXT),
    "/nul-and-latin1": _raw(
        _500, b"caf" + bytes([0xE9, 0x20, 0xFF, 0xFE, 0x00]), _TEXT
    ),
    "/bogus-charset": _raw(
        _500, b"caf" + bytes([0xE9]), ("Content-Type: text/plain; charset=bogus",)
    ),
    "/not-a-text-codec": _raw(
        _500, b"zipped?", ("Content-Type: text/plain; charset=zlib_codec",)
    ),
    "/utf16": _raw(
        _500, "sixteen".encode("utf-16"), ("Content-Type: text/plain; charset=utf-16",)
    ),
    "/no-content-type": _raw(_500, _ESCAPES, ()),
    "/newlines": _raw(_500, b"line one\r\nline two\nE   line three\tcol", _TEXT),
    "/status-esc": _raw(f"HTTP/1.1 500 {_E}[2J{_E}[Hwiped", b"x", _TEXT),
    "/status-long": _raw("HTTP/1.1 500 " + "R" * 5000, b"x", _TEXT),
    "/status-999": _raw("HTTP/1.1 999 Beyond", b"nine", _TEXT),
    "/status-304": _raw("HTTP/1.1 304 Not Modified", b"", ()),
    "/status-400": _raw("HTTP/1.1 400 Bad Request", b"Request is too long", _TEXT),
    "/lying-long": _raw(_500, b"ten bytes!", _TEXT, length=1 << 20),
    "/lying-short": _raw(_500, _MEG, _TEXT, length=5),
    "/bad-status-line": b"HTTP/1.1 ABC\r\n\r\n",
    "/garbage": b"not http at all\r\n\r\n",
}


class _HostileHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        try:
            self.wfile.write(HOSTILE[self.path.split("?", 1)[0]])
            self.wfile.flush()
        except OSError:
            pass  # the client stopped reading a lying body; nothing more to do

    def log_message(self, *args):
        pass  # keep the pytest output free of per-request lines


class _HostileServer(http.server.ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # a client that drops a lying body is the expected outcome here


@pytest.fixture(scope="module")
def hostile_http():
    pytest.importorskip("requests")
    server = _HostileServer(("127.0.0.1", 0), _HostileHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(5)


class TestHostileServerAnswers:
    """The body of a non-2xx answer is now part of the error, so a hostile or
    broken server gets a say in a traceback. Every case is served by a real HTTP
    server on an ephemeral port (nothing in the wrapper or in requests is
    patched): the explanation must reach the message escaped, single-line and
    capped, and a lying or malformed answer must fail fast as a requests error.
    """

    def _call(self, base, path):
        import requests

        parser = CoreNLPParser(url=base + path)
        with budget(30.0, f"the {path} answer", cpu_bound=False):
            with pytest.raises(requests.exceptions.RequestException) as info:
                parser.api_call(
                    "The quick brown fox.", properties={"annotators": "tokenize"}
                )
        return info.value

    def _explanation(self, exc):
        return str(exc).split("the CoreNLP server said: ", 1)[1]

    def test_terminal_escapes_in_the_body_are_neutralised(self, hostile_http):
        import requests

        e = self._call(hostile_http, "/esc")
        assert isinstance(e, requests.exceptions.HTTPError)
        assert e.response.status_code == 500
        message = str(e)
        assert _E not in message and chr(0x07) not in message
        assert "\\x1b]8;;http://evil.example" in message
        assert "\\x1b]52;c;" in message
        assert message.startswith("500 Server Error: Internal Server Error for url: ")

    def test_a_bidi_override_in_the_body_is_neutralised(self, hostile_http):
        e = self._call(hostile_http, "/bidi")
        assert _RLO not in str(e)
        assert "ok \\u202elive" in str(e)

    def test_a_megabyte_body_is_capped_but_kept_on_the_response(self, hostile_http):
        e = self._call(hostile_http, "/huge")
        message = str(e)
        assert len(message) < 1000, len(message)
        assert "..." in self._explanation(e)
        assert "(1048576 bytes)" in message
        assert len(e.response.content) == 1 << 20

    def test_a_chunked_megabyte_body_is_capped(self, hostile_http):
        e = self._call(hostile_http, "/chunked")
        assert len(str(e)) < 1000, len(str(e))
        assert "(1048576 bytes)" in str(e)

    def test_an_empty_body_is_named_as_such(self, hostile_http):
        e = self._call(hostile_http, "/empty")
        assert self._explanation(e) == "an empty body (0 bytes)"

    def test_undecodable_bytes_and_nul_do_not_raise(self, hostile_http):
        e = self._call(hostile_http, "/nul-and-latin1")
        explanation = self._explanation(e)
        assert explanation.startswith("'caf")
        assert chr(0) not in explanation and "\\x00" in explanation

    def test_a_charset_the_codec_registry_rejects_falls_back(self, hostile_http):
        e = self._call(hostile_http, "/bogus-charset")
        assert "'caf" + chr(0xE9) + "'" in str(e)
        e = self._call(hostile_http, "/not-a-text-codec")
        assert "'zipped?'" in str(e)

    def test_a_declared_charset_is_honoured(self, hostile_http):
        e = self._call(hostile_http, "/utf16")
        assert "'sixteen'" in str(e)

    def test_a_missing_content_type_still_escapes(self, hostile_http):
        e = self._call(hostile_http, "/no-content-type")
        assert _E not in str(e) and "\\x1b[31mFAIL" in str(e)

    def test_newlines_and_tabs_cannot_forge_report_lines(self, hostile_http):
        e = self._call(hostile_http, "/newlines")
        explanation = self._explanation(e)
        assert "\n" not in explanation and "\r" not in explanation
        assert "\t" not in explanation
        assert "line one\\x0d\\x0aline two\\x0aE   line three\\x09col" in explanation

    def test_a_hostile_status_line_reason_is_neutralised(self, hostile_http):
        e = self._call(hostile_http, "/status-esc")
        assert _E not in str(e)
        assert str(e).startswith("500 Server Error: \\x1b[2J\\x1b[Hwiped for url: ")

    def test_an_overlong_reason_phrase_is_capped(self, hostile_http):
        e = self._call(hostile_http, "/status-long")
        head = str(e).split(" for url: ", 1)[0]
        assert head.startswith("500 Server Error: RRRR") and head.endswith("...")
        assert len(head) < 200, len(head)

    def test_a_status_outside_2xx_4xx_5xx_is_an_error_too(self, hostile_http):
        import requests

        e = self._call(hostile_http, "/status-999")
        assert isinstance(e, requests.exceptions.HTTPError)
        assert str(e).startswith("999 Unexpected Status: Beyond for url: ")
        assert "'nine' (4 bytes)" in str(e)
        e = self._call(hostile_http, "/status-304")
        assert isinstance(e, requests.exceptions.HTTPError)
        assert str(e).startswith("304 Unexpected Status: Not Modified for url: ")
        assert self._explanation(e) == "an empty body (0 bytes)"

    def test_a_4xx_is_a_client_error_with_the_explanation(self, hostile_http):
        e = self._call(hostile_http, "/status-400")
        assert str(e).startswith("400 Client Error: Bad Request for url: ")
        assert "'Request is too long' (19 bytes)" in str(e)

    def test_a_body_shorter_than_its_content_length_fails_fast(self, hostile_http):
        import requests

        e = self._call(hostile_http, "/lying-long")
        # Nothing to explain: requests reports the truncated transfer itself.
        assert not isinstance(e, requests.exceptions.HTTPError), str(e)

    def test_a_body_longer_than_its_content_length_is_cut_at_the_header(
        self, hostile_http
    ):
        e = self._call(hostile_http, "/lying-short")
        assert "'AAAAA' (5 bytes)" in str(e)

    def test_a_malformed_status_line_fails_fast(self, hostile_http):
        import requests

        for path in ("/bad-status-line", "/garbage"):
            e = self._call(hostile_http, path)
            assert not isinstance(e, requests.exceptions.HTTPError), str(e)


class TestCoreNLPServerError:
    """start() raises CoreNLPServerError on both failure branches. A real server
    cannot be made to fail on demand cheaply, so the subprocess/HTTP boundary is
    fault-injected to drive the real error-construction code (no CoreNLP or JVM
    needed, so these run everywhere including CI)."""

    def _bare_server(self, corenlp_options):
        # Bypass __init__ (no jar lookup); start() re-validates options at the sink.
        srv = object.__new__(CoreNLPServer)
        srv.corenlp_options = corenlp_options
        srv._classpath = ("a.jar", "b.jar")
        srv.java_options = ["-mx512m"]
        srv.verbose = False
        srv.url = "http://localhost:9999"
        return srv

    def test_raises_when_the_launched_process_exits_immediately(self, monkeypatch):
        pytest.importorskip("requests")
        import nltk.parse.corenlp as m

        class _DeadPopen:
            def poll(self):
                return 1

            def communicate(self):
                return ("", "Error: could not find or load main class")

        monkeypatch.setattr(m, "config_java", lambda *a, **k: None)
        monkeypatch.setattr(m, "java", lambda *a, **k: _DeadPopen())
        srv = self._bare_server(["-quiet"])
        with pytest.raises(CoreNLPServerError, match="Could not start the server"):
            srv.start()

    def test_raises_when_the_server_never_becomes_reachable(self, monkeypatch):
        import requests

        import nltk.parse.corenlp as m

        class _LivePopen:
            def poll(self):
                return None

        def _refuse(*a, **k):
            raise requests.exceptions.ConnectionError("connection refused")

        monkeypatch.setattr(m, "config_java", lambda *a, **k: None)
        monkeypatch.setattr(m, "java", lambda *a, **k: _LivePopen())
        monkeypatch.setattr(m.time, "sleep", lambda *_: None)
        monkeypatch.setattr(requests, "get", _refuse)
        srv = self._bare_server(["-quiet"])
        with pytest.raises(CoreNLPServerError, match="Could not connect to the server"):
            srv.start()

    def test_sink_guard_refuses_a_hostile_option_before_any_launch(self, monkeypatch):
        # The option guard runs at the top of start(), so a reassigned path-bearing
        # flag is refused before the launcher is ever reached (java must not run).
        import nltk.parse.corenlp as m

        def _boom(*a, **k):
            raise AssertionError("java() must not be called when the guard refuses")

        monkeypatch.setattr(m, "config_java", lambda *a, **k: None)
        monkeypatch.setattr(m, "java", _boom)
        srv = self._bare_server(["-serverProperties", "/etc/passwd"])
        with pytest.raises(ValueError):
            srv.start()


class TestTransform:
    """The module-level transform() maps a CoreNLP sentence dict to the CoNLL-10
    tuples CoreNLPDependencyParser.make_tree feeds to DependencyGraph."""

    def test_maps_basic_dependencies_to_conll_tuples(self):
        from nltk.parse.corenlp import transform

        sentence = {
            "basicDependencies": [
                {"dependent": 2, "governor": 0, "dep": "ROOT"},
                {"dependent": 1, "governor": 2, "dep": "nsubj"},
            ],
            "tokens": [
                {"word": "Dogs", "lemma": "dog", "pos": "NNS"},
                {"word": "bark", "lemma": "bark", "pos": "VBP"},
            ],
        }
        assert list(transform(sentence)) == [
            (2, "_", "bark", "bark", "VBP", "VBP", "_", "0", "ROOT", "_", "_"),
            (1, "_", "Dogs", "dog", "NNS", "NNS", "_", "2", "nsubj", "_", "_"),
        ]

    def test_feeds_a_valid_dependencygraph(self):
        # sorted(transform(...)) must be consumable by make_tree -> DependencyGraph.
        from nltk.parse.corenlp import CoreNLPDependencyParser, transform

        sentence = {
            "basicDependencies": [
                {"dependent": 1, "governor": 2, "dep": "nsubj"},
                {"dependent": 2, "governor": 0, "dep": "ROOT"},
            ],
            "tokens": [
                {"word": "Dogs", "lemma": "dog", "pos": "NNS"},
                {"word": "bark", "lemma": "bark", "pos": "VBP"},
            ],
        }
        graph = CoreNLPDependencyParser(url="http://localhost:0").make_tree(sentence)
        assert ("bark", "VBP") in [g for g, _, _ in graph.triples()]


class TestScalarGate:
    """_corenlp_check_scalar is the name-agnostic first gate: every value and flag
    passes it before any per-flag shape check, so its rejections are exercised
    directly (control / DEL / unicode-confusable / metachar / @argfile / non-str)."""

    @pytest.mark.parametrize(
        "bad",
        [
            "",
            " ",
            "a b",
            "a\tb",
            "a\nb",
            "a\rb",
            "a\x00b",
            "a\x1bb",
            "a\x7fb",
            "a b",  # unicode LINE SEPARATOR
            "ｆｕ",  # fullwidth
            "ро",  # cyrillic homoglyph of "po"
            "@/tmp/argfile",
            "a;b",
            "a|b",
            "a$b",
            "a`b",
            "a&b",
            "a>b",
            "a\\b",
        ],
    )
    def test_rejects_unsafe_scalar(self, bad):
        from nltk.parse.corenlp import _corenlp_check_scalar

        with pytest.raises(ValueError):
            _corenlp_check_scalar(bad)

    @pytest.mark.parametrize("bad", [None, 123, b"bytes", 3.14, ["x"]])
    def test_rejects_non_string(self, bad):
        from nltk.parse.corenlp import _corenlp_check_scalar

        with pytest.raises(ValueError):
            _corenlp_check_scalar(bad)

    def test_rejects_str_subclass(self):
        from nltk.parse.corenlp import _corenlp_check_scalar

        class Sneaky(str):
            def lower(self):
                return "-port"

        with pytest.raises(ValueError):
            _corenlp_check_scalar(Sneaky("-serverProperties"))

    @pytest.mark.parametrize(
        "ok",
        [
            "-port",
            "9000",
            "tokenize,ssplit",
            "/corenlp/api",
            "srv-1",
            "-maxCharLength=-1",
        ],
    )
    def test_accepts_plain_ascii(self, ok):
        from nltk.parse.corenlp import _corenlp_check_scalar

        _corenlp_check_scalar(ok)  # must not raise


class TestLyingStrSubclassBypass:
    """A str subclass can override startswith/split/lower/__iter__ to validate as
    a benign flag while its real characters (what reaches the JVM argv) smuggle a
    hostile one. The guard hard-rejects any entry that is not an exact str, at the
    validator's entry, so a lying subclass never reaches a method call (CWE-88)."""

    def test_split_lower_lying_subclass_is_refused(self):
        class Lying(str):
            def startswith(self, p, *a):
                return p != "@"

            def __contains__(self, x):
                return x == "="

            def split(self, sep=None, maxsplit=-1):
                return ["-port", "9000"]

            def lower(self):
                return "-port"

        with pytest.raises(ValueError):
            _validate_corenlp_options([Lying("-serverProperties=/etc/passwd")])

    def test_iter_lying_subclass_is_refused(self):
        class IterLiar(str):
            def __iter__(self):
                return iter("-port=9000")

            def startswith(self, p, *a):
                return p != "@"

            def __contains__(self, x):
                return x == "="

            def split(self, sep=None, maxsplit=-1):
                return ["-port", "9000"]

            def lower(self):
                return "-port"

        with pytest.raises(ValueError):
            _validate_corenlp_options([IterLiar("-serverProperties=/etc/passwd")])

    def test_even_a_benign_str_subclass_is_refused(self):
        # No option is a legitimate str subclass, so the guard refuses one
        # outright (hard reject) rather than coercing it, benign value or not.
        class Plain(str):
            pass

        with pytest.raises(ValueError):
            _validate_corenlp_options([Plain("-port"), Plain("9000")])

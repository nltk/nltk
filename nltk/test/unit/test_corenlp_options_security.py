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

import os

import pytest

from nltk.parse.corenlp import (
    CoreNLPServer,
    CoreNLPServerError,
    _validate_corenlp_options,
    try_port,
)

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

        list(
            find_jar_iter(
                CoreNLPServer._JAR,
                None,
                env_vars=("CORENLP",),
                searchpath=(),
                url=_stanford_url,
                verbose=False,
                is_regex=True,
            )
        )
        return True
    except Exception:
        return False


def _make_corenlp_server(corenlp_options, port=None):
    import nltk

    # The jar sandbox trusts jars under an nltk.data.path root; adding the
    # install dir there is the documented way to trust an external tool.
    for env_var in ("CORENLP", "CORENLP_MODELS"):
        directory = os.environ.get(env_var)
        if directory and directory not in nltk.data.path:
            nltk.data.path.insert(0, directory)
    return CoreNLPServer(corenlp_options=corenlp_options, port=port)


@pytest.fixture(scope="module")
def live_server():
    # One real server for every wrapper-function test, on an ephemeral port (never
    # the default 9000, which test_corenlp.py binds and races under xdist); the
    # preloaded annotators + allowlisted -srparser/-maxCharLength=-1 must start clean.
    pytest.importorskip("requests")
    srv = _make_corenlp_server(
        [
            "-preload",
            "tokenize,ssplit,pos,lemma,ner,parse,depparse",
            "-srparser",
            "-maxCharLength=-1",
        ],
        port=try_port(),
    )
    srv.start()
    try:
        yield srv
    finally:
        srv.stop()


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

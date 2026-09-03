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

import pytest

from nltk.parse.corenlp import CoreNLPServer, _validate_corenlp_options

# Reuse the adversarial JVM / external-tool payload corpora already written for the
# java() and tool-wrapper guards. None of these is an allowlisted CoreNLP server
# flag, so corenlp_options must refuse every one of them too. This piggybacks the
# corenlp allowlist onto ~115 existing hostile vectors (JVM agents, @argfile,
# -XX:OnError, bootclasspath / module-path / class-path, codebase, metacharacter /
# NUL / unicode-whitespace / DEL smuggling, concatenated flags, tool program flags
# and hostile model paths) rather than re-authoring them.
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

# --- BENIGN: normal operational usage that MUST keep working ------------------
BENIGN = [
    ["-preload", "tokenize,ssplit,pos,lemma,parse,depparse"],  # the NLTK default
    ["-port", "9000"],
    ["-port=9000"],  # inline form
    ["-status_port", "9001"],
    ["-timeout", "15000"],
    ["-threads", "4"],
    ["-maxCharLength", "100000"],
    ["-maxCharLength", "-1"],  # CoreNLP sentinel for unbounded
    ["-annotators", "tokenize,ssplit,pos,lemma,ner,parse,depparse"],
    ["-preload=tokenize,pos"],
    ["-quiet"],
    ["-quiet", "true"],
    ["-strict"],
    ["-ssl"],
    ["-stanford"],
    ["-server_id", "my_server-1"],
    ["-uriContext", "/corenlp"],
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

# --- MALICIOUS: every candidate must be refused -------------------------------
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
# Adversarial sneak-through attempts found by probing the allowlist: consumption
# desync (a bare flag must not swallow a following dangerous flag as its value),
# double-dash spellings, glued forms, homoglyph and fullwidth digits, oversize
# values, path/model tokens hidden in an annotator list, and uriContext traversal.
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
    ["-maxCharLength", "-5"],  # only the -1 sentinel is allowed
    ["-status_port", "-key"],  # int flag value is a dangerous flag
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
    # corenlp_options allowlist must refuse every one (none is an allowlisted
    # server flag). Proves the guard piggybacks the existing corpus, not just the
    # cases written by hand for it.
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
        except ValueError as exc:
            if "corenlp_options" in str(exc):
                pytest.fail("benign corenlp_options wrongly refused at the sink")
        except Exception:
            pass  # config_java()/java() failing with no jars/JVM is fine

# Natural Language Toolkit: expanded attack harness for the JVM child
# environment scrub and the read_str literal boundary
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""``internals._java_child_env`` and ``internals.read_str`` driven with the
widest matrix, benign neighbours included, judged by what the sink received:
the environment the child JVM really sees (a real JVM prints its own, under a
minimal explicit parent environment), and the exact text ``ast.literal_eval``
was handed. A drop-list stays the mechanism (its mutation tests elsewhere pin
it as load-bearing); this file pins that every loader family of every
platform NLTK's tools run on, in any letter case, is in it."""

import os
import pathlib
import shutil
import tempfile
import unittest.mock

import pytest

import nltk.data
from nltk import internals, pathsec
from nltk.test.unit import timing

NUL = chr(0)

_JVM_INJECTING = {
    "JAVA_TOOL_OPTIONS": "-XX:OnError=touch /tmp/pwned",
    "_JAVA_OPTIONS": "-XX:OnError=touch /tmp/pwned",
    "JDK_JAVA_OPTIONS": "-XX:OnError=touch /tmp/pwned",
    "IBM_JAVA_OPTIONS": "-Xdump:tool:exec=touch /tmp/pwned",
    "OPENJ9_JAVA_OPTIONS": "-Xdump:tool:exec=touch /tmp/pwned",
    "CLASSPATH": "/evil",
    # the launcher prints its debug trace on stdout, which the wrappers parse
    "_JAVA_LAUNCHER_DEBUG": "1",
}
_LOADER = {
    "LD_PRELOAD": "/evil.so",
    "LD_LIBRARY_PATH": "/evil/lib",
    "LD_AUDIT": "/evil/audit.so",
    "LD_ASSUME_KERNEL": "2.4.1",
    "LD_DEBUG_OUTPUT": "/tmp/x",
    "DYLD_INSERT_LIBRARIES": "/evil.dylib",
    "DYLD_LIBRARY_PATH": "/evil/dylib",
    "DYLD_FRAMEWORK_PATH": "/evil/fw",
    "LDR_PRELOAD": "/evil.a",
    "LDR_PRELOAD64": "/evil64.a",
    "LDR_CNTRL": "MAXDATA=0x80000000",
    "_RLD_LIST": "/evil.so:DEFAULT",
    "_RLD_ROOT": "/evil",
    "GLIBC_TUNABLES": "glibc.malloc.check=3",
    "MALLOC_TRACE": "/tmp/mtrace",
    "MALLOC_CHECK_": "3",
    "LIBPATH": "/evil",
    "SHLIB_PATH": "/evil",
    "GCONV_PATH": "/evil/gconv",
    "LOCPATH": "/evil/locale",
    "NLSPATH": "/evil/%N",
    "IFS": "x",
    # the JDK adds it to java.library.path on macOS: a native-library redirect
    "JAVA_LIBRARY_PATH": "/evil/jni",
}
_BENIGN = {
    "HOME": "/home/user",
    "USER": "user",
    "LOGNAME": "user",
    "SHELL": "/bin/sh",
    "TERM": "xterm",
    "TZ": "UTC",
    "LANG": "en_US.UTF-8",
    "LANGUAGE": "en",
    "LC_ALL": "C.UTF-8",
    "LC_CTYPE": "C.UTF-8",
    "LC_MESSAGES": "C",
    "TMPDIR": "/tmp",
    "TMP": "/tmp",
    "TEMP": "/tmp",
    "JAVA_HOME": "/opt/jdk",
    "JAVAHOME": "/opt/jdk",
    "JRE_HOME": "/opt/jdk",
    "STANFORD_MODELS": "/models",
    "STANFORD_PARSER": "/stanford-parser",
    "STANFORD_POSTAGGER": "/stanford-postagger",
    "STANFORD_SEGMENTER": "/stanford-segmenter",
    "STANFORD_CORENLP": "/corenlp",
    "CORENLP": "/corenlp",
    "CORENLP_MODELS": "/corenlp",
    "MALT_PARSER": "/malt",
    "MALT_MODEL": "/malt/model.mco",
    "WEKAHOME": "/weka",
    "SLF4J": "/slf4j",
    "NLTK_DATA": "/data",
    "NLTK_ATK_KEEP": "keepme",
    "SYSTEMROOT": "C:\\Windows",
    "SYSTEMDRIVE": "C:",
    "WINDIR": "C:\\Windows",
    "COMSPEC": "C:\\Windows\\system32\\cmd.exe",
    "USERPROFILE": "C:\\Users\\user",
    "APPDATA": "C:\\Users\\user\\AppData\\Roaming",
    "NUMBER_OF_PROCESSORS": "4",
    # names that merely CONTAIN a hostile spelling are not the hostile name
    "MYLD_PRELOAD": "x",
    "XCLASSPATH": "x",
    "CLASSPATH_BACKUP": "x",
    "JAVA_TOOL_OPTIONS_OLD": "x",
    "OLD_LD_PRELOAD": "x",
    "DYLDX": "x",
    "GCONV_PATH2": "x",
    "IFSX": "x",
    "MALLOC": "x",
    "GLIBC": "x",
}


def _case_variants(name):
    yield name
    yield name.lower()
    yield name.swapcase()
    yield name[:1].lower() + name[1:].upper()


# === 1. The scrub over a substituted mapping: every family, every case ===
class TestChildEnvMatrix:
    @pytest.mark.parametrize(
        "name", sorted(set(_JVM_INJECTING) | set(_LOADER)), ids=lambda n: n
    )
    def test_every_hostile_name_in_every_case_is_dropped(self, name):
        value = {**_JVM_INJECTING, **_LOADER}[name]
        for variant in _case_variants(name):
            child = internals._java_child_env({variant: value, "HOME": "/h"})
            assert variant not in child, variant
            assert value not in child.values()
            assert child["HOME"] == "/h"

    def test_every_benign_name_survives_and_path_is_locked(self):
        mapping = dict(_BENIGN)
        mapping["PATH"] = "/usr/bin:/evil"
        child = internals._java_child_env(mapping)
        for name, value in _BENIGN.items():
            assert child.get(name) == value, name
        assert child["PATH"] == pathsec.safe_env()["PATH"]
        assert "/evil" not in child["PATH"]

    @pytest.mark.parametrize(
        "name",
        [
            "LD_PRELOAD=/evil.so",
            "JAVA_TOOL_OPTIONS=-Xmx1m",
            "CLASSPATH=/evil",
            "=/evil",
            "HOME=x",
            "",
            "LD_" + NUL + "PRELOAD",
            "JAVA_TOOL" + NUL + "_OPTIONS",
            "HOME" + NUL,
            NUL,
        ],
        ids=lambda n: repr(n)[:24],
    )
    def test_a_name_the_os_could_not_hold_is_dropped(self, name):
        # os.environ refuses "=" and NUL in a name; a substituted mapping must
        # not be able to smuggle one to the spawn either
        child = internals._java_child_env({name: "v", "HOME": "/h"})
        assert name not in child and "v" not in child.values()
        assert child["HOME"] == "/h"

    def test_a_value_with_nul_or_a_non_str_entry_is_dropped(self):
        child = internals._java_child_env(
            {"HOME": "/h" + NUL, "TZ": b"UTC", 1: "x", "LANG": None, "USER": "u"}
        )
        assert child == {"USER": "u", "PATH": pathsec.safe_env()["PATH"]}

    def test_the_real_environ_is_the_default_source(self, monkeypatch):
        for name, value in {**_JVM_INJECTING, **_LOADER}.items():
            monkeypatch.setenv(name, value)
        monkeypatch.setenv("ld_preload", "/lower.so")
        monkeypatch.setenv("NLTK_ATK_KEEP", "keepme")
        child = internals._java_child_env()
        for name in {**_JVM_INJECTING, **_LOADER}:
            assert name not in child, name
        assert "ld_preload" not in child
        assert child["NLTK_ATK_KEEP"] == "keepme"
        assert child["PATH"] == pathsec.safe_env()["PATH"]

    def test_the_new_loader_families_are_load_bearing(self, monkeypatch):
        # Mutation: with the prefix and exact sets emptied, every loader name
        # of every platform reaches the child, so the sets are what stop them.
        monkeypatch.setattr(internals, "_LOADER_ENV_PREFIXES", ())
        monkeypatch.setattr(internals, "_LOADER_ENV_EXACT", frozenset())
        child = internals._java_child_env(dict(_LOADER))
        assert set(_LOADER) <= set(child)

    def test_the_documented_families_are_all_in_the_prefix_set(self):
        for prefix in ("LD_", "DYLD_", "LDR_", "_RLD_", "GLIBC_", "MALLOC_"):
            assert prefix in internals._LOADER_ENV_PREFIXES
        for exact in (
            "LIBPATH",
            "SHLIB_PATH",
            "GCONV_PATH",
            "LOCPATH",
            "NLSPATH",
            "IFS",
        ):
            assert exact in internals._LOADER_ENV_EXACT


# === 2. A real JVM, launched by internals.java(), prints the env it received ===
_PRINT_ENV_JAVA = """
public class PrintEnv {
    public static void main(String[] args) {
        java.util.TreeMap<String, String> env =
            new java.util.TreeMap<>(System.getenv());
        for (java.util.Map.Entry<String, String> e : env.entrySet()) {
            System.out.println(e.getKey() + "=" + e.getValue().replace("\\n", " "));
        }
    }
}
"""

# What the minimal parent environment carries over from the real one: only
# what a JVM needs to start on each platform, never a token or a secret.
_MINIMAL_PARENT_KEYS = frozenset(
    {
        "HOME",
        "USER",
        "LOGNAME",
        "TMPDIR",
        "TMP",
        "TEMP",
        "LANG",
        "LC_ALL",
        "LC_CTYPE",
        "JAVA_HOME",
        "JAVAHOME",
        "SYSTEMROOT",
        "SYSTEMDRIVE",
        "WINDIR",
        "COMSPEC",
        "PATHEXT",
        "USERPROFILE",
        "APPDATA",
        "LOCALAPPDATA",
        "PROGRAMDATA",
        "USERNAME",
        "NUMBER_OF_PROCESSORS",
        "PROCESSOR_ARCHITECTURE",
        "OS",
        "PATH",
    }
)


@pytest.fixture
def jvm_source_root(monkeypatch):
    """A private root under $HOME holding PrintEnv.java, registered as the one
    trusted data root; the JVM binary is resolved from the real environment
    before that environment is replaced by the minimal one."""
    monkeypatch.setattr(internals, "_java_bin", None)
    monkeypatch.setattr(internals, "_java_options", [])
    try:
        internals.config_java()
    except LookupError:
        pytest.skip("no Java binary found on this machine")
    root = os.path.realpath(
        tempfile.mkdtemp(prefix=".nltk_jvm_env_", dir=pathlib.Path.home())
    )
    src = os.path.join(root, "PrintEnv.java")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(_PRINT_ENV_JAVA)
    monkeypatch.setattr(pathsec, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", [root])
    monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
    monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
    try:
        yield src
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_real_jvm_child_sees_only_the_scrubbed_environment(jvm_source_root):
    minimal = {k: v for k, v in os.environ.items() if k.upper() in _MINIMAL_PARENT_KEYS}
    hostile = {**_JVM_INJECTING, **_LOADER}
    hostile.update({name.lower(): value for name, value in list(hostile.items())[:6]})
    hostile["dyld_insert_libraries"] = "/evil.dylib"
    hostile["Ld_Audit"] = "/evil/audit.so"
    markers = {"NLTK_ATK_KEEP": "keepme", "STANFORD_MODELS": "/models"}
    with unittest.mock.patch.dict(
        os.environ, {**minimal, **hostile, **markers}, clear=True
    ):
        # source-file mode: the launcher compiles PrintEnv.java in memory, so
        # no class file is planted anywhere and no separate compiler is spawned
        with timing.budget(120.0, "the JVM call"):
            out, _err = internals.java(
                [jvm_source_root],
                classpath=None,
                options=[],
                stdout="pipe",
                stderr="pipe",
            )
    child = dict(line.partition("=")[::2] for line in out.splitlines() if "=" in line)
    survivors = sorted(name for name in hostile if name in child)
    assert survivors == [], survivors
    assert not any(value in child.values() for value in hostile.values())
    assert child.get("PATH") == pathsec.safe_env()["PATH"]
    for name, value in markers.items():
        assert child.get(name) == value, name
    for name in ("HOME", "JAVA_HOME", "LANG"):
        if name in minimal:
            assert child.get(name) == minimal[name], name


# === 3. read_str: every input judged by what ast.literal_eval received ===
@pytest.fixture
def parser_spy(monkeypatch):
    import builtins

    seen = []
    real = internals.ast.literal_eval

    def _record(text):
        seen.append(text)
        return real(text)

    def _boom(*a, **k):
        raise AssertionError("eval/exec reached")

    monkeypatch.setattr(internals.ast, "literal_eval", _record)
    monkeypatch.setattr(builtins, "eval", _boom)
    monkeypatch.setattr(builtins, "exec", _boom)
    return seen


class _Lying(str):
    def __getitem__(self, item):
        return "[__import__('os')]"

    def __str__(self):
        return "'lie'"

    def __len__(self):
        return 1


_READ_STR_CASES = [
    # (source, position, expected value or exception class)
    ('"abc"', 0, "abc"),
    ("'abc'", 0, "abc"),
    ('u"abc"', 0, "abc"),
    ('R"a\\b"', 0, "a\\b"),
    ('"""a"b"""', 0, 'a"b'),
    ("x = 'v' rest", 4, "v"),
    (_Lying('"abc"'), 0, "abc"),
    ('"a" + __import__("os").system("id")', 0, "a"),
    ('"\\x00\\udcff"', 0, chr(0) + chr(0xDCFF)),
    ('f"{__import__(1)}"', 0, internals.ReadError),
    ('b"x"', 0, internals.ReadError),
    ('rb"x"', 0, internals.ReadError),
    ('t"x"', 0, internals.ReadError),
    ('ur"x"', 0, internals.ReadError),
    ("'unterminated", 0, internals.ReadError),
    ('"a\nb"', 0, internals.ReadError),
    ('"\\N{NO SUCH NAME}"', 0, internals.ReadError),
    ('"\\U11111111"', 0, internals.ReadError),
    ("abc", 0, internals.ReadError),
    ("", 0, internals.ReadError),
    ('"abc"', -1, internals.ReadError),
    ('"abc"', 5, internals.ReadError),
    ('"abc"', 1.5, TypeError),
    ('"abc"', None, TypeError),
    (b'"abc"', 0, TypeError),
    (None, 0, TypeError),
]


@pytest.mark.parametrize(
    "source,position,expected", _READ_STR_CASES, ids=lambda v: repr(v)[:20]
)
def test_read_str_matrix_judged_by_what_reached_the_parser(
    source, position, expected, parser_spy
):
    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            internals.read_str(source, position)
        for text in parser_spy:
            assert type(text) is str and text[0] in "\"'uUrR"
        return
    value, end = internals.read_str(source, position)
    assert type(value) is str and value == expected
    assert len(parser_spy) == 1 and type(parser_spy[0]) is str
    assert parser_spy[0] == str.__getitem__(source, slice(position, end))
    assert "__import__" not in parser_spy[0]

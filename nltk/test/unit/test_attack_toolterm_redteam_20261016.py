"""
Red-team 2026-10-16, class `toolterm`: external-tool wrappers, terminal/CSV
output, and network SSRF.

Holds every REFUSED and BENIGN-OK row (the confirmed LEAK, java() source-file
mode, lives in LEAK_java_cmd.py, not here). Runs on python3.13 and python3.10;
no pytest-timeout, no tkinter, no public network. The one network test starts a
loopback server and asserts the SSRF guard refuses it BEFORE any connection.

Run with: python3.13 -m pytest -q nltk/test/unit/test_attack_toolterm_redteam_20261016.py
"""

import io
import sys

import pytest

import nltk

# Unicode payloads are built with chr(), never literal escapes (the Write tool
# would otherwise decode them to real control characters in this source).
ESC = chr(0x1B)
BEL = chr(0x07)
CSI = chr(0x9B)
OSC = ESC + "]"
RLO = chr(0x202E)
PDF = chr(0x202C)
ZWSP = chr(0x200B)


# ----------------------------------------------------------------------------
# nltk.internals.java() cmd[0] launcher-token guard (CVE-2026-12841 / GHSA-x8q7)
# These refusals fire at the cmd[0] guard, BEFORE any JVM is resolved, so they
# need no Java install.
# ----------------------------------------------------------------------------
from nltk.internals import java  # noqa: E402


@pytest.mark.parametrize(
    "cmd",
    [
        ["-jar", "/tmp/x.jar"],
        ["--module-path", "/tmp", "m/Main"],
        ["-cp", "/tmp/x.jar", "Main"],
        ["-version"],
        [" -jar", "/tmp/x.jar"],  # leading whitespace trimmed to a launcher token
    ],
    ids=["jar", "module-path", "cp-first", "version", "ws-jar"],
)
def test_java_rejects_leading_launcher_switch(cmd):
    """cmd[0] whose stripped form starts with '-' is refused as a launcher
    switch, so no caller-influenced cmd can turn java() into `java -jar`."""
    with pytest.raises(ValueError, match="main class"):
        java(cmd)


@pytest.mark.parametrize(
    "cmd",
    [
        ["@" + "/tmp/argfile"],
        ["\t@" + "/tmp/argfile"],
        ["Main", "@" + "/tmp/argfile"],  # @argfile refused in ANY position
    ],
    ids=["argfile-first", "ws-argfile-first", "argfile-later"],
)
def test_java_rejects_argfile_token(cmd):
    """An @argfile token is refused anywhere in cmd; the JVM would expand it and
    inject blocked flags."""
    with pytest.raises(ValueError, match="argfile|main class"):
        java(cmd)


def test_java_plain_mainclass_not_overblocked():
    """A legitimate main-class token (no '-'/'@') passes the cmd[0] guard: it is
    NOT rejected with the launcher-switch ValueError. It fails later (no such
    JVM/class), which is a different error, proving the guard does not over-block
    ordinary invocations."""
    try:
        java(["edu.stanford.nlp.NoSuchClass"])
    except ValueError as e:
        assert "main class" not in str(e), "guard over-blocked a plain main class"
    except Exception:
        pass  # LookupError/OSError from missing JVM or class is the expected path


# ----------------------------------------------------------------------------
# termsec.sanitize_terminal / safe_print
# ----------------------------------------------------------------------------
from nltk.termsec import sanitize_terminal  # noqa: E402


def test_sanitize_terminal_neutralises_control_sequences():
    """ESC, the OSC introducer, BEL and a C1 CSI byte are rendered as visible
    \\xNN escapes, never passed through to drive the terminal."""
    payload = OSC + "0;title" + BEL + CSI + "2J" + ESC + "[31m"
    out = sanitize_terminal(payload)
    for ch in (ESC, BEL, CSI):
        assert ch not in out
    assert "\\x1b" in out and "\\x07" in out


def test_sanitize_terminal_escapes_bidi_override_and_zero_width():
    """A bidi override (RLO) and a zero-width space are escaped to visible, so a
    Trojan-Source reorder or an invisible smuggle cannot survive."""
    out = sanitize_terminal(RLO + "admin" + ZWSP)
    assert RLO not in out and ZWSP not in out
    assert "\\u202e" in out and "\\u200b" in out


def test_sanitize_terminal_benign_arabic_survives():
    """BENIGN-OK: ordinary Arabic text (no override, balanced) passes through
    unchanged and readable."""
    arabic = "مرحبا"  # marhaba
    assert sanitize_terminal(arabic) == arabic


def test_sanitize_terminal_benign_plain_text_identity():
    """BENIGN-OK: plain ASCII with tab/newline is returned unchanged (the same
    object) in default multi-line mode."""
    s = "hello\tworld\nline2"
    assert sanitize_terminal(s) == s


# ----------------------------------------------------------------------------
# csvsec.sanitize_csv_field (re-exported as nltk.termsec.sanitize_csv_field)
# ----------------------------------------------------------------------------
from nltk.termsec import sanitize_csv_field  # noqa: E402


@pytest.mark.parametrize(
    "cell",
    ["=1+1", "+cmd", "-cmd", "@SUM(1)", "+HYPERLINK(1)", "-2+3+cmd", "=cmd", "+", "-"],
)
def test_csv_formula_lead_is_prefixed(cell):
    """A cell that would be read as a spreadsheet formula is prefixed with a
    single quote so the client treats it as text (CSV injection)."""
    assert sanitize_csv_field(cell).startswith("'")


@pytest.mark.parametrize("cell", ["+1", "-1", "+1.5", "-0", "3.14", "1+1", "-1,000"])
def test_csv_benign_numbers_not_mangled(cell):
    """BENIGN-OK: a genuine number (including signed) is NOT prefixed, so legit
    numeric data is preserved."""
    assert sanitize_csv_field(cell) == cell


@pytest.mark.parametrize("cell", ["hello", "a,b", 'has"quote', "مرحبا"])
def test_csv_benign_text_passthrough(cell):
    """BENIGN-OK: ordinary text and non-ASCII letters are returned unchanged."""
    assert sanitize_csv_field(cell) == cell


def test_csv_zero_width_before_formula_is_escaped():
    """A zero-width space before '=' is escaped to visible, so it cannot hide a
    formula lead from a human while the client still sees text."""
    out = sanitize_csv_field(ZWSP + "=1+1")
    assert ZWSP not in out and "\\u200b" in out


# ----------------------------------------------------------------------------
# Printers that route through the sanitising sink
# ----------------------------------------------------------------------------
def _captured(fn):
    buf = io.StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        fn()
    finally:
        sys.stdout = old
    return buf.getvalue()


def test_freqdist_tabulate_sanitises_samples():
    """FreqDist.tabulate() renders a control-laden sample through the terminal
    sanitiser: no raw ESC/BEL reaches stdout."""
    fd = nltk.FreqDist()
    fd[OSC + "0;x" + BEL] += 3
    fd["normal"] += 1
    out = _captured(fd.tabulate)
    assert ESC not in out and BEL not in out


def test_confusionmatrix_safe_print_sink_sanitises():
    """safe_print(ConfusionMatrix(...)) (the designated print sink) emits no raw
    ESC even when a label carries one; __str__/pretty_format stay raw by design
    for round-trip and are a separate documented finding."""
    from nltk.termsec import safe_print

    cm = nltk.ConfusionMatrix([OSC + "x" + BEL, "b"], ["b", "b"])
    out = _captured(lambda: safe_print(cm))
    assert ESC not in out and BEL not in out


def test_tree_pprint_sink_sanitises():
    """Tree.pprint() routes through safe_print, so a control char in a node
    label does not reach the terminal raw (pformat/__str__ stay raw by design)."""
    from nltk.tree import Tree

    t = Tree(OSC + "NP" + BEL, [Tree("DT", ["the"])])
    out = _captured(t.pprint)
    assert ESC not in out and BEL not in out


# ----------------------------------------------------------------------------
# pathsec SSRF filter
# ----------------------------------------------------------------------------
from nltk.pathsec import urlopen, validate_network_url  # noqa: E402


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/",
        "http://0.0.0.0/",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[64:ff9b::7f00:1]/",
        "http://[2002:7f00:1::]/",
        "http://2130706433/",
        "http://0x7f000001/",
        "http://0177.0.0.1/",
        "http://127.1/",
        "http://10.0.0.5/",
        "http://192.168.1.1/",
        "http://100.64.0.1/",
        "http://user:pass@127.0.0.1/",
        "http://[fe80::1%25eth0]/",
        "gopher://127.0.0.1/",
        "ftp://127.0.0.1/",
    ],
)
def test_ssrf_forbidden_urls_refused(url):
    """Every loopback/link-local/private/obfuscated/embedded/tunnel/unsupported
    scheme URL is refused by validate_network_url (no fetch)."""
    with pytest.raises((PermissionError, ValueError)):
        validate_network_url(url, context="redteam")


@pytest.mark.parametrize(
    "url", ["http://8.8.8.8/", "http://[2606:4700:4700::1111]/", ""]
)
def test_ssrf_benign_global_literal_passes(url):
    """BENIGN-OK: a globally routable IP literal (and the empty URL) validate
    without raising and without egress (literal classification, no DNS/fetch)."""
    assert validate_network_url(url, context="redteam") is None


def test_ssrf_urlopen_refuses_loopback_before_egress():
    """urlopen() refuses a loopback peer BEFORE connecting: a real local server
    records zero connections even though the host is reachable."""
    import http.server
    import socketserver
    import threading

    hits = {"n": 0}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # pragma: no cover - must never run
            hits["n"] += 1
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"ok")

        def log_message(self, *a):
            pass

    srv = socketserver.TCPServer(("127.0.0.1", 0), H)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        with pytest.raises(Exception):
            urlopen(f"http://127.0.0.1:{port}/", timeout=5)
        assert hits["n"] == 0, "SSRF guard let a connection reach the loopback peer"
    finally:
        srv.shutdown()
        th.join(timeout=5)

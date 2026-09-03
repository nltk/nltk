# Natural Language Toolkit: XSS + CSRF attack tests (wordnet_app)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""XSS and shutdown-CSRF attack tests for ``nltk.app.wordnet_app``.

The WordNet browser serves corpus-derived synset text (definitions, examples,
lemma names, related-synset names) as HTML. Every such sink runs the text
through :func:`html.escape` before emitting it, so a crafted gloss cannot inject
live markup (CWE-79). The shutdown route additionally requires a per-process
secret token compared with :func:`hmac.compare_digest`, so a cross-site page
cannot forge a shutdown (CWE-352).

These tests drive the real rendering functions with adversarial input. There is
no real WordNet gloss containing ``<script>``, so hostile corpus text is
supplied by temporarily setting the private text attributes of REAL, cached
Synset / Lemma objects (restored afterwards) and running the real sinks over
them; the functions under test are never replaced.
"""

import contextlib
import html
import inspect
import string

import pytest

import nltk.app.wordnet_app as wa

# Live-markup tokens that must never survive escaping. Each is a LIVE construct:
# an unescaped tag opening (``<tag``), a real ``javascript:`` href scheme, or a
# quote that breaks an attribute into an ``on*=`` handler (``"onerror=``). These
# only appear if the payload's own ``<`` / ``"`` / ``'`` survived unescaped, so a
# substring in ALREADY-ESCAPED text (e.g. ``&lt;img ... onerror=`` or the template's
# own literal ``"..."`` around an example) is inert and correctly NOT matched. The
# template's own tags (<li> <a> <ul> <i> <b> <h*>) are intentionally NOT listed.
DANGEROUS_TOKENS = [
    "<script",
    "<img",
    "<svg",
    "<iframe",
    "<object",
    "<embed",
    "<body",
    "<style",
    "<base",
    "<meta",
    "<form",
    "<textarea",
    "<link",
    "<input",
    "<marquee",
    'href="javascript:',
    "href='javascript:",
    '"onmouseover=',
    '"onerror=',
    '"onload=',
    '"onclick=',
    '"onfocus=',
    "'onmouseover=",
    "'onerror=",
]

# Corpus-text payloads spanning element-content, attribute-breakout, URI, encoded,
# case-varied, null-split, and alternate-tag injection styles. html.escape must
# neutralise EVERY one by turning <, >, ", ', & into entities so no live construct
# above can form.
XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<ScRiPt>alert(1)</ScRiPt>",  # case-varied tag
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    '"><script>alert(document.cookie)</script>',  # attribute breakout (double quote)
    "'><script>x</script>",  # attribute breakout (single quote)
    'a"onmouseover=alert(1)',
    "a'onmouseover=alert(1)",
    "javascript:alert(1)",
    "<iframe src=javascript:alert(1)>",
    "<style>@import 'x'</style>",
    "<base href=//evil>",
    "<meta http-equiv=refresh content=0>",
    "<form action=//evil><input>",
    "<textarea></textarea><script>x</script>",  # breaks out of a textarea
    "<marquee onstart=alert(1)>",
    "<a href=`javascript:alert(1)`>",  # backtick delimiter (legacy IE)
    "<scr\x00ipt>alert(1)</scr\x00ipt>",  # NUL-split tag
    "<<script>script>",  # nested-bracket smuggling
    "data:text/html,<script>x</script>",
    "\x3cscript\x3ealert(1)\x3c/script\x3e",  # backslash-x escaped < >
    "&lt;script&gt;alert(1)&lt;/script&gt;",  # already-encoded (must stay inert)
    "&#60;script&#62;alert(1)&#60;/script&#62;",
    "+ADw-script+AD4-alert(1)+ADw-/script+AD4-",  # UTF-7 (inert under a pinned charset)
]


def _wn():
    """Return the wordnet reader, or skip if its data isn't installed."""
    from nltk.corpus import wordnet as wn

    try:
        wn.synset("dog.n.01")
    except LookupError:
        pytest.skip("wordnet corpus not installed")
    return wn


@contextlib.contextmanager
def _patched_attrs(obj, **attrs):
    """Temporarily set attributes on a (possibly cached) object, restoring the
    originals afterwards so no wordnet cache pollution leaks across tests."""
    saved = {k: getattr(obj, k) for k in attrs}
    for k, v in attrs.items():
        setattr(obj, k, v)
    try:
        yield obj
    finally:
        for k, v in saved.items():
            setattr(obj, k, v)


def assert_no_live_markup(out):
    low = out.lower()
    for token in DANGEROUS_TOKENS:
        assert token.lower() not in low, f"live markup leaked: {token!r}"


class TestDefinitionAndExampleSinks:
    def test_definition_escaped(self):
        wn = _wn()
        syn = wn.synset("dog.n.01")
        for payload in XSS_PAYLOADS:
            with _patched_attrs(syn, _definition=payload, _examples=[]):
                out = wa._collect_one_synset("dog", syn, {})
            assert_no_live_markup(out)
        # spot-check that the tag payload is present but escaped, not stripped
        with _patched_attrs(syn, _definition="<script>alert(1)</script>", _examples=[]):
            out = wa._collect_one_synset("dog", syn, {})
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out

    def test_examples_escaped(self):
        wn = _wn()
        syn = wn.synset("dog.n.01")
        with _patched_attrs(
            syn,
            _definition="a dog",
            _examples=[
                "<img src=x onerror=alert(1)>",
                '"><script>x</script>',
                'a"onmouseover=alert(1)',
            ],
        ):
            out = wa._collect_one_synset("dog", syn, {})
        assert_no_live_markup(out)
        assert "&lt;img src=x onerror=alert(1)&gt;" in out
        assert "&quot;onmouseover=alert(1)" in out  # attribute quote neutralised

    def test_lemma_name_escaped(self):
        """format_lemma (nested in _collect_one_synset) escapes lemma text."""
        wn = _wn()
        syn = wn.synset("dog.n.01")
        victim = syn.lemmas()[0]
        for payload in ("<script>lem</script>", 'x"onmouseover=alert(1)'):
            with _patched_attrs(victim, _name=payload):
                out = wa._collect_one_synset("dog", syn, {})
            assert_no_live_markup(out)
        with _patched_attrs(victim, _name="<script>lem</script>"):
            out = wa._collect_one_synset("dog", syn, {})
        assert "&lt;script&gt;lem&lt;/script&gt;" in out

    def test_benign_synset_renders_correctly(self):
        """A benign synset renders real content and a working lookup link."""
        wn = _wn()
        syn = wn.synset("dog.n.01")
        out = wa._collect_one_synset("dog", syn, {})
        assert_no_live_markup(out)
        assert "domestic dog" in out  # lemma with underscores rendered as spaces
        assert "member of the genus Canis" in out  # definition text present
        assert '<a href="lookup_' in out  # a real lookup link was built
        assert out.startswith("<li>") and out.endswith("</li>\n")


class TestRelationHtmlSink:
    def test_related_lemma_name_escaped(self):
        """relation_html (nested in _synset_relations) escapes the related
        synset's lemma name. This also regression-guards the fix for the
        ``html`` local shadowing the module import (which made this sink raise
        NameError instead of escaping)."""
        wn = _wn()
        syn = wn.synset("dog.n.01")
        victim = syn.hypernyms()[0]
        with _patched_attrs(
            victim, _lemma_names=["<script>rel</script>", *victim._lemma_names[1:]]
        ):
            out = wa._synset_relations("dog", syn, {syn.name(): {wa.HYPERNYM}})
        assert_no_live_markup(out)
        assert "&lt;script&gt;rel&lt;/script&gt;" in out

    def test_relation_expansion_does_not_raise(self):
        """Benign relation expansion returns HTML without NameError (regression
        for the shadowed-``html`` bug)."""
        wn = _wn()
        syn = wn.synset("dog.n.01")
        out = wa._synset_relations("dog", syn, {syn.name(): {wa.HYPERNYM}})
        assert isinstance(out, str)
        assert_no_live_markup(out)
        assert "<ul>" in out  # relations actually expanded


class TestMakeLookupLinkSink:
    class _Ref:
        """Minimal stand-in supplying a hostile ref.encode() to the real sink."""

        def __init__(self, payload):
            self._payload = payload

        def encode(self):
            return self._payload

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_href_param_escaped(self, payload):
        out = wa.make_lookup_link(self._Ref(payload), html.escape(payload))
        assert_no_live_markup(out)

    def test_attribute_breakout_neutralised(self):
        out = wa.make_lookup_link(
            self._Ref('a"onmouseover=alert(1)'), html.escape("<b>x</b>")
        )
        assert '"onmouseover=alert(1)"' not in out
        assert "&quot;" in out and "&lt;b&gt;x&lt;/b&gt;" in out

    def test_real_reference_href_is_safe(self):
        """A real Reference whose word is a payload encodes to safe base64."""
        ref = wa.Reference("<script>alert(1)</script>")
        out = wa.make_lookup_link(ref, html.escape("<script>alert(1)</script>"))
        assert_no_live_markup(out)
        assert "&lt;script&gt;" in out  # escaped label text


class TestReflectedSearchWord:
    """The user-controlled search word is reflected into the page and must be
    escaped on every rendered path (the handler html.escape's it, and the
    'word not found' message escapes it again)."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_payload_word_renders_no_live_markup(self, payload):
        _wn()
        # A payload word matches no synset, so the 'not found' branch renders it.
        body, _ = wa.page_from_reference(wa.Reference(payload))
        assert_no_live_markup(body)

    def test_payload_word_is_escaped_not_stripped(self):
        _wn()
        body, _ = wa.page_from_reference(wa.Reference("<script>alert(1)</script>"))
        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;" in body  # escaped, present, not silently dropped


class TestUrlSchemeContext:
    """The lookup href is always a RELATIVE URL (the ``lookup_`` prefix, whose
    ``_`` is not a legal scheme character), so a ``javascript:`` payload can never
    become an executable scheme."""

    def test_javascript_payload_stays_a_relative_path(self):
        out = wa.make_lookup_link(
            TestMakeLookupLinkSink._Ref("javascript:alert(1)"), "L"
        )
        assert 'href="lookup_javascript:alert(1)"' in out  # relative, prefixed
        assert 'href="javascript:' not in out  # never a live js scheme
        assert_no_live_markup(out)

    def test_quote_in_href_cannot_break_the_attribute(self):
        out = wa.make_lookup_link(TestMakeLookupLinkSink._Ref('x"><script>y'), "L")
        assert_no_live_markup(out)
        assert "&quot;" in out or "&gt;" in out  # the breakout chars were escaped


class TestResponseCharsetHeaders:
    """html.escape only neutralises <>"'& ; it does NOT stop a UTF-7 payload like
    ``+ADw-script+AD4-`` from decoding to ``<script>`` if a browser is allowed to
    sniff the charset. The response must therefore pin the charset (UTF-8) and send
    ``X-Content-Type-Options: nosniff`` (CWE-79 / CWE-116)."""

    def _headers_for(self, ctype):
        handler = wa.MyServerHandler.__new__(wa.MyServerHandler)
        sent = []
        handler.send_response = lambda code: sent.append(("status", code))
        handler.send_header = lambda k, v: sent.append((k, v))
        handler.end_headers = lambda: sent.append(("end", ""))
        handler.send_head(ctype)
        return sent

    def test_html_response_pins_utf8_charset(self):
        pairs = self._headers_for("text/html")
        assert ("Content-type", "text/html; charset=UTF-8") in pairs

    def test_response_sends_nosniff(self):
        assert ("X-Content-Type-Options", "nosniff") in self._headers_for("text/html")

    def test_plain_response_also_pinned_and_nosniff(self):
        pairs = self._headers_for("text/plain")
        assert ("Content-type", "text/plain; charset=UTF-8") in pairs
        assert ("X-Content-Type-Options", "nosniff") in pairs

    def test_charset_not_doubled_if_already_present(self):
        pairs = self._headers_for("text/html; charset=UTF-8")
        ctype = [v for k, v in pairs if k == "Content-type"][0]
        assert ctype.lower().count("charset=") == 1

    def test_static_pages_declare_no_sniffable_charset(self):
        # The HTTP header pins UTF-8 for every page; additionally no static template
        # may declare a sniffable charset, and any that declares one must use UTF-8.
        for page in (
            wa.get_static_upper_page(True),
            wa.get_static_index_page(False),
            wa.get_static_welcome_message(),
            wa.get_static_web_help_page(),
        ):
            low = page.lower()
            assert "us-ascii" not in low
            assert "iso-8859" not in low
            assert "utf-7" not in low
            if "charset=" in low:
                assert "charset=utf-8" in low


class TestPageTitleEscaping:
    """pg() reflects the search word into the <title>; it must be escaped so it
    cannot break out of the title or inject markup into the page head."""

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_reflected_word_in_title_has_no_live_bracket(self, payload):
        out = wa.pg(payload, "body-content")
        # isolate exactly what pg reflected into the <title> and assert no raw '<'
        # (a '</title>' breakout or an injected tag needs an unescaped '<').
        title = out.split("display of: ", 1)[1].split("</title>", 1)[0]
        assert "<" not in title
        if "<" in payload:
            assert "&lt;" in title  # escaped, not stripped

    def test_pg_title_escaped_spotcheck(self):
        out = wa.pg("<script>alert(1)</script>", "body-content")
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in out


class TestReferenceDeserialization:
    """The ``lookup_`` route base64-decodes and unpickles attacker-controlled data
    (Reference.decode). Every malicious/malformed payload must be rejected with a
    ValueError (RestrictedUnpickler blocks class/function reconstruction, then the
    shape is validated), and code must NEVER run (CWE-502)."""

    @staticmethod
    def _b64(obj):
        import base64
        import pickle

        return base64.urlsafe_b64encode(pickle.dumps(obj, -1)).decode()

    def test_reduce_rce_is_blocked_and_never_executes(self, tmp_path):
        import base64
        import os
        import pickle

        marker = tmp_path / "rce_marker"

        class _Evil:
            def __reduce__(self):
                return (os.system, (f"touch {marker}",))

        href = base64.urlsafe_b64encode(pickle.dumps(_Evil(), -1)).decode()
        with pytest.raises(ValueError):
            wa.page_from_href(href)
        assert not marker.exists(), "deserialization executed code (RCE)"

    @pytest.mark.parametrize(
        "obj", [[1, 2, 3], ("w", 5), ("w", {"k": [1]}), (b"w", {}), "plain", {"a": 1}]
    )
    def test_wrong_shapes_rejected(self, obj):
        with pytest.raises(ValueError):
            wa.page_from_href(self._b64(obj))

    @pytest.mark.parametrize("junk", ["", "!!!not-base64!!!", "____", "YWJj", "*" * 40])
    def test_malformed_input_rejected(self, junk):
        with pytest.raises(ValueError):
            wa.page_from_href(junk)

    def test_benign_reference_round_trips(self):
        _wn()
        ref = wa.Reference("dog", {})
        _, word = wa.page_from_href(ref.encode())
        assert word == "dog"


class TestShutdownTokenCsrf:
    def _authorized(self, path):
        # Real handler; skip the socket __init__ and drive _shutdown_authorized.
        handler = wa.MyServerHandler.__new__(wa.MyServerHandler)
        handler.path = path
        return handler._shutdown_authorized()

    def test_correct_token_authorizes(self):
        tok = wa._shutdown_token
        assert self._authorized(f"/SHUTDOWN THE SERVER?token={tok}") is True

    @pytest.mark.parametrize(
        "bad",
        [
            "",  # empty
            "WRONG",  # wrong
            "token=",  # missing value via odd path (no real token)
        ],
    )
    def test_wrong_or_empty_token_rejected(self, bad):
        assert self._authorized(f"/SHUTDOWN THE SERVER?token={bad}") is False

    def test_missing_token_rejected(self):
        assert self._authorized("/SHUTDOWN THE SERVER") is False

    def test_truncated_and_prefix_guess_rejected(self):
        tok = wa._shutdown_token
        assert self._authorized(f"/SHUTDOWN THE SERVER?token={tok[:-1]}") is False
        assert self._authorized(f"/SHUTDOWN THE SERVER?token={tok[:8]}") is False
        assert self._authorized(f"/SHUTDOWN THE SERVER?token={tok}x") is False

    def test_uses_constant_time_compare_not_plain_eq(self):
        src = inspect.getsource(wa.MyServerHandler._shutdown_authorized)
        assert "compare_digest" in src
        assert "==" not in src  # no timing-leaky plain equality on the token

    def test_do_get_refuses_unauthorized_with_403(self):
        src = inspect.getsource(wa.MyServerHandler.do_GET)
        assert "_shutdown_authorized" in src
        assert "403" in src

    def test_token_is_per_process_secret(self):
        tok = wa._shutdown_token
        assert isinstance(tok, str) and len(tok) >= 43  # token_urlsafe(32)
        allowed = set(string.ascii_letters + string.digits + "-_")
        assert set(tok) <= allowed

    def test_upper_page_carries_token_only_when_shutdown_offered(self):
        with_shutdown = wa.get_static_upper_page(True)
        without = wa.get_static_upper_page(False)
        assert wa._shutdown_token in with_shutdown
        assert "SHUTDOWN THE SERVER?token=" in with_shutdown
        assert wa._shutdown_token not in without
        assert "SHUTDOWN THE SERVER" not in without

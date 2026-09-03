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
them -- the functions under test are never replaced.
"""

import contextlib
import html
import inspect
import string

import pytest

import nltk.app.wordnet_app as wa

# Live-markup tokens that must never survive escaping. The page template's own
# tags (<li> <a> <ul> <i> <b>) are intentionally NOT in this list.
DANGEROUS_TOKENS = [
    "<script",
    "<img",
    "<svg",
    "<iframe",
    "<object",
    "<embed",
    "<body",
    'href="javascript:',
    "href='javascript:",
    '"onmouseover=',
    '"onerror=',
    '"onload=',
]

# Corpus-text payloads spanning element-content, attribute-breakout, URI and
# encoded-entity injection styles.
XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    "<img src=x onerror=alert(1)>",
    "<svg/onload=alert(1)>",
    '"><script>alert(document.cookie)</script>',
    'a"onmouseover=alert(1)',
    "javascript:alert(1)",
    "<iframe src=javascript:alert(1)>",
    "&lt;script&gt;alert(1)&lt;/script&gt;",  # double-encoding attempt
    "&#60;script&#62;alert(1)&#60;/script&#62;",
    "<script>alert(1)</script>",  # unicode-escaped <script>
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

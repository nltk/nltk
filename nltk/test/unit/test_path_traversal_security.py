"""
Living-audit regression tests for the path-traversal / file-I/O sandbox cluster
(GHSA-8mgp-746c-j5xp umbrella). CWE-22 / CWE-59 / CWE-377 / CWE-400.

Consolidates the file-system attack surface an attacker can reach and locks in
the fixes that already live (or now land) on ``develop`` so a future refactor
cannot silently reopen any of them:

* CVE-2026-54293 (GHSA-p4gq-832x-fm9v, #3629) -- traversal via URL-encoded path
  separators / traversal segments in ``nltk.data``.
* CVE-2026-12243 (GHSA-q5h6-fcf5-49g9, #3698) -- ``..%2f`` bypass of the
  ``data.py`` guard (an "incomplete fix" for #3504).
* GHSA-f794 -- ``pathsec`` symlink/hardlink (TOCTOU) read escape (CWE-59), plus
  its newly-closed *write*-side counterpart (a symlink swapped in at a
  ``retrieve()``/model-write destination).

Payloads are kept whether or not they currently leak, as long as they are
plausible: the guard-passing-but-benign encodings are the natural place a future
double-decode bug would regress, so they are asserted to resolve in-root.
"""

import os
import tempfile

import pytest

import nltk.data as D

# ==========================================================================
# 1. Crafted resource names must not escape the data root (CVE-2026-54293/12243)
# ==========================================================================

# Forms that MUST be rejected outright (ValueError) by find() and load(). Raw
# and single-encoded traversal, absolute paths, Windows/UNC, and the nltk:
# scheme variants that resolve to a traversal.
_MUST_REJECT = [
    "../../../etc/passwd",
    "..%2f..%2fetc%2fpasswd",
    "..%2F..%2Fetc",
    "%2e%2e/%2e%2e/etc/passwd",
    "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "%2fetc%2fpasswd",
    "corpora/../../../etc/passwd",
    "corpora/%2e%2e%2f%2e%2e%2fetc%2fpasswd",
    "nltk:../secret.txt",
    "nltk:../../../secret.txt",
    "nltk:%2e%2e%2fsecret.txt",
    "nltk:..%2fsecret.txt",
    "%2e%2e%5c%2e%2e%5cwindows",
    "\\\\evil\\share",
    "C:\\Windows\\win.ini",
]

# No-protocol forms only: normalize_resource_url() rejects these at the string
# layer. (nltk:/file: forms are intentionally passed through by normalize and
# caught downstream by find()/load(); see _MUST_REJECT above for the pipeline.)
_MUST_REJECT_NORMALIZE = [p for p in _MUST_REJECT if not p.startswith("nltk:")]

# Benign names that MUST NOT be misclassified as unsafe (a false positive would
# break every legitimate corpus lookup).
_MUST_ALLOW = [
    "corpora/wordnet",
    "tokenizers/punkt/english.pickle",
    "help/tagsets",
    "corpora/stopwords/english",
    "grammars/sample_grammars/toy.cfg",
    # legitimate percent-encoded literal name: a single unquote of ``%2520`` is
    # the literal ``%20`` -- it must NOT be treated as a separator/traversal.
    "corpora/my%2520corpus/data.txt",
]


# POSIX-only: a bare leading-slash path is absolute only on POSIX. On Windows it
# has no drive letter, so it normalizes to a relative resource name and is a
# not-found LookupError (not a traversal). Windows absolute forms (drive-letter /
# UNC, in _MUST_REJECT) are rejected on every platform.
_MUST_REJECT_POSIX_ABS = ["/etc/passwd"]


@pytest.mark.parametrize("payload", _MUST_REJECT)
def test_find_rejects_traversal(payload):
    with pytest.raises(ValueError):
        D.find(payload)


@pytest.mark.skipif(
    os.name != "posix", reason="a bare leading-slash is absolute only on POSIX"
)
@pytest.mark.parametrize("payload", _MUST_REJECT_POSIX_ABS)
def test_posix_absolute_path_is_rejected(payload):
    with pytest.raises(ValueError):
        D.find(payload)
    with pytest.raises(ValueError):
        D.load(payload, format="raw")
    with pytest.raises(ValueError):
        D.normalize_resource_url(payload)


@pytest.mark.parametrize("payload", _MUST_REJECT)
def test_load_rejects_traversal(payload):
    with pytest.raises(ValueError):
        D.load(payload, format="raw")


@pytest.mark.parametrize("payload", _MUST_REJECT_NORMALIZE)
def test_normalize_resource_url_rejects_traversal(payload):
    with pytest.raises(ValueError):
        D.normalize_resource_url(payload)


@pytest.mark.parametrize("name", _MUST_ALLOW)
def test_find_allows_benign_names(name):
    try:
        D.find(name)
    except ValueError as exc:
        pytest.fail(f"benign name {name!r} wrongly rejected: {exc}")
    except LookupError:
        pass


def test_no_payload_reads_a_sentinel_outside_the_data_root():
    """End-to-end property: plant a secret at several levels above an isolated
    data root and confirm no crafted resource name -- rejected, collapsed, or
    passed through as an encoded literal -- can read it."""
    base = tempfile.mkdtemp()
    dataroot = os.path.join(base, "nltk_data")
    os.makedirs(dataroot)
    levels = [base, os.path.dirname(base), os.path.dirname(os.path.dirname(base))]
    for i, d in enumerate(levels, 1):
        try:
            with open(os.path.join(d, f"secret{i}.txt"), "w") as fh:
                fh.write(f"TOP-SECRET-{i}")
        except OSError:
            pass

    saved = list(D.path)
    D.path.insert(0, dataroot)
    try:
        payloads = []
        for i in range(1, 4):
            up = "../" * i
            payloads += [
                f"{up}secret{i}.txt",
                f"nltk:{up}secret{i}.txt",
                ("..%2f" * i) + f"secret{i}.txt",
                ("..%252f" * i) + f"secret{i}.txt",  # double-encoded
                ("..%c0%af" * i) + f"secret{i}.txt",  # overlong UTF-8
            ]
        for p in payloads:
            try:
                ptr = D.find(p)
            except Exception:
                # Any exception (ValueError guard, LookupError not-found, or a
                # UnicodeDecodeError from decoding overlong %c0%af on Python 3.14+)
                # means the payload did not resolve to a readable file -- no leak.
                continue
            try:
                content = ptr.open().read()
            except Exception:
                continue
            if isinstance(content, bytes):
                content = content.decode("latin-1", "replace")
            assert "TOP-SECRET" not in content, f"traversal leak via {p!r}: {ptr}"
    finally:
        D.path[:] = saved


def test_double_encoded_stays_literal_in_root():
    """``..%252f`` / overlong ``..%c0%af`` pass the string guard but url2pathname
    single-decodes, so they are a *literal in-root filename*, never a separator.
    This is the exact spot a future double-decode bug would regress, so assert
    the behaviour explicitly: not-found (LookupError) or a path inside the root,
    never a ValueError-worthy escape and never a leak."""
    base = tempfile.mkdtemp()
    dataroot = os.path.join(base, "nltk_data")
    os.makedirs(dataroot)
    open(os.path.join(base, "secret.txt"), "w").write("SENTINEL")
    saved = list(D.path)
    D.path.insert(0, dataroot)
    try:
        # Valid percent-encoding: url2pathname single-decodes -> literal in-root
        # name that does not exist -> LookupError (never a separator/traversal).
        for p in ("..%252fsecret.txt", "..%252f..%252fsecret.txt"):
            with pytest.raises(LookupError):
                D.find(p)
        # Overlong-UTF-8 ``%c0%af`` never decodes to "/". On Python <3.14 unquote
        # replaces the bytes (-> literal in-root -> LookupError); on 3.14+ unquote
        # raises UnicodeDecodeError. Either way it is rejected, never a leak.
        with pytest.raises((LookupError, UnicodeDecodeError)):
            D.find("..%c0%afsecret.txt")
    finally:
        D.path[:] = saved


def test_file_scheme_is_not_rejected_as_a_traversal():
    """The security-relevant, platform-independent half: the ``file:`` scheme is
    an explicit reference, NOT a data-root-relative name -- so the traversal
    guard must not reject a plain file: URL as "unsafe" (it is by-design, unlike
    a no-protocol ``..`` name). (file: URL *path* resolution -- drive letters,
    leading slashes -- differs on Windows and is exercised by nltk.data's own
    tests; the actual read is checked POSIX-only below.)"""
    for url in ("file:///data/corpus/x.txt", "file://localhost/data/x.txt"):
        # Must not raise ValueError ("unsafe resource path"); a LookupError later
        # (resource absent) would be fine, but normalization itself must accept.
        D.normalize_resource_url(url)


@pytest.mark.skipif(
    os.name != "posix", reason="file: URL path resolution is POSIX-specific here"
)
def test_file_scheme_reads_an_in_root_file(monkeypatch):
    """A legitimate file: load of a file inside an allowed root works -- pinning
    that file:// handling is by-design and not "fixed" into rejecting it."""
    import pathlib

    import nltk.data
    import nltk.pathsec as P

    base = tempfile.mkdtemp()
    allowed = os.path.join(base, "allowed")
    os.makedirs(allowed)
    monkeypatch.setattr(P, "ENFORCE", True)
    monkeypatch.setattr(nltk.data, "path", list(nltk.data.path) + [allowed])
    monkeypatch.setattr(P, "_ALLOWED_ROOTS_CACHE", None)

    target = os.path.join(allowed, "explicit.txt")
    with open(target, "w") as fh:
        fh.write("EXPLICIT-CONTENT")
    obj = D.load(pathlib.Path(target).as_uri(), format="raw")
    data = obj.decode() if isinstance(obj, bytes) else obj
    assert "EXPLICIT-CONTENT" in data


# ==========================================================================
# 2. pathsec symlink / hardlink TOCTOU -- read AND write (GHSA-f794 + write side)
# ==========================================================================


@pytest.mark.skipif(os.name != "posix", reason="O_NOFOLLOW hardening is POSIX-only")
class TestPathsecSymlinkHardening:
    def _roots(self, monkeypatch):
        import nltk.data
        import nltk.pathsec as P

        base = tempfile.mkdtemp()
        root = os.path.join(base, "root")
        os.makedirs(root)
        outside = os.path.join(base, "outside")
        os.makedirs(outside)
        monkeypatch.setattr(P, "ENFORCE", True)
        # Register ``root`` (not ``base``) as an allowed data root so pathsec
        # permits access on every platform: Linux ``/tmp`` is world-writable and
        # is deliberately NOT auto-trusted, unlike a private macOS ``$TMPDIR``.
        # ``outside`` stays a sibling of ``root`` -- outside every allowed root --
        # so an escape to it is still a genuine violation.
        monkeypatch.setattr(nltk.data, "path", list(nltk.data.path) + [root])
        monkeypatch.setattr(P, "_ALLOWED_ROOTS_CACHE", None)
        return P, base, root, outside

    def test_benign_write_read_roundtrip_and_private_perms(self, monkeypatch):
        P, base, root, outside = self._roots(monkeypatch)
        p = os.path.join(root, "model.json")
        with P.open(p, "w", required_root=root) as fh:
            fh.write("HELLO")
        assert P.open(p, required_root=root).read() == "HELLO"
        # created file must not be group/world readable (CWE-377/378)
        assert (os.stat(p).st_mode & 0o077) == 0

    def test_static_symlink_to_outside_is_refused_read_and_write(self, monkeypatch):
        P, base, root, outside = self._roots(monkeypatch)
        victim = os.path.join(outside, "victim")
        open(victim, "w").write("ORIG")
        link = os.path.join(root, "pkg")
        os.symlink(victim, link)
        # validate_path itself catches a static symlink (resolve -> outside root)
        for mode in ("r", "w", "a"):
            with pytest.raises((ValueError, PermissionError)):
                P.open(link, mode, required_root=root)
        assert open(victim).read() == "ORIG"

    def test_write_toctou_symlink_swap_is_blocked(self, monkeypatch):
        # Simulate the race the O_NOFOLLOW hardening closes: validate_path passed
        # on stale state, then a symlink appears at the destination before open.
        P, base, root, outside = self._roots(monkeypatch)
        victim = os.path.join(outside, "victim")
        open(victim, "w").write("ORIG")
        link = os.path.join(root, "evil")
        os.symlink(victim, link)
        monkeypatch.setattr(P, "validate_path", lambda *a, **k: None)
        with pytest.raises(PermissionError):
            P.open(link, "w", required_root=root)
        assert open(victim).read() == "ORIG", "write followed the symlink (TOCTOU leak)"

    def test_read_toctou_symlink_swap_is_blocked(self, monkeypatch):
        P, base, root, outside = self._roots(monkeypatch)
        secret = os.path.join(outside, "secret")
        open(secret, "w").write("TOP-SECRET")
        link = os.path.join(root, "data")
        os.symlink(secret, link)
        monkeypatch.setattr(P, "validate_path", lambda *a, **k: None)
        with pytest.raises(PermissionError):
            P.open(link, "r", required_root=root).read()

    def test_hardlink_to_outside_inode_is_refused(self, monkeypatch):
        P, base, root, outside = self._roots(monkeypatch)
        secret = os.path.join(outside, "secret")
        open(secret, "w").write("TOP-SECRET")
        hard = os.path.join(root, "hard")
        try:
            os.link(secret, hard)  # in-root name, outside-root inode
        except OSError:
            pytest.skip("cross-dir hardlink not permitted here")
        monkeypatch.setattr(P, "validate_path", lambda *a, **k: None)
        with pytest.raises(PermissionError):
            P.open(hard, "r", required_root=root).read()

    def test_malformed_mode_does_not_leak_fd(self, monkeypatch):
        # os.open() accepts some mode strings os.fdopen() rejects (e.g. ""). The
        # fdopen must be inside the fd-closing guard or repeated calls exhaust
        # the fd table (DoS).
        P, base, root, outside = self._roots(monkeypatch)
        f = os.path.join(root, "x")
        with open(f, "w") as fh:
            fh.write("hi")
        before = len(os.listdir("/dev/fd"))
        for _ in range(64):
            with pytest.raises((ValueError, OSError)):
                P.open(f, "", required_root=root)
        after = len(os.listdir("/dev/fd"))
        assert after <= before + 2, f"fd leak: {before} -> {after}"


# ==========================================================================
# 3. Predictable shared-temp squat on the trained-model save (CWE-59/377)
# ==========================================================================


@pytest.mark.skipif(os.name != "posix", reason="symlink squat is a POSIX concern")
class TestPerceptronSaveSquat:
    def _tagger(self):
        from nltk.tag.perceptron import PerceptronTagger

        t = PerceptronTagger(load=False)
        t.model.weights = {"feat": {"NN": 1.0}}
        t.tagdict = {"the": "DT"}
        t.classes = {"NN", "DT"}
        return t

    def test_benign_save_is_private_and_roundtrips(self):
        base = tempfile.mkdtemp()
        loc = os.path.join(base, "model_dir")
        t = self._tagger()
        t.save_to_json(lang="eng", loc=loc)
        files = os.listdir(loc)
        assert files, "no model files written"
        for f in files:
            # written model must not be group-/world-readable (CWE-377/378)
            assert (os.stat(os.path.join(loc, f)).st_mode & 0o077) == 0

    def test_symlinked_save_location_is_refused(self):
        # The default save dir is a guessable name in a shared temp dir; a local
        # attacker who pre-plants a symlink there must not capture/redirect the
        # model write.
        base = tempfile.mkdtemp()
        victim = os.path.join(base, "attacker_dir")
        os.makedirs(victim)
        squat = os.path.join(base, "squat")
        os.symlink(victim, squat)
        with pytest.raises(PermissionError):
            self._tagger().save_to_json(lang="eng", loc=squat)
        assert not os.listdir(victim), "write leaked through the symlink"

    def test_world_writable_save_location_is_refused(self):
        # A pre-existing real dir at the guessable name that is world-writable
        # (an attacker could drop files in it / read the model back) is refused.
        base = tempfile.mkdtemp()
        loc = os.path.join(base, "shared")
        os.makedirs(loc)
        os.chmod(loc, 0o777)
        with pytest.raises(PermissionError):
            self._tagger().save_to_json(lang="eng", loc=loc)


# ==========================================================================
# 4. Entity-expansion (billion-laughs) in the bcp47 XML corpus reader (CWE-776)
# ==========================================================================


class TestBcp47EntitySafeParse:
    def test_entity_expansion_is_rejected(self):
        # bcp47 was the only XML corpus reader using raw ElementTree.parse; a
        # malicious `bcp47` package could ship a billion-laughs subdivisions XML.
        # It now goes through nltk.xmlsec, which refuses entity declarations.
        import io

        from nltk.xmlsec import parse as safe_parse

        lol = (
            '<?xml version="1.0"?><!DOCTYPE lolz ['
            '<!ENTITY a "AAAA"><!ENTITY b "&a;&a;&a;&a;&a;">]>'
            "<localeDisplayNames><subdivisions><subdivision>&b;"
            "</subdivision></subdivisions></localeDisplayNames>"
        )
        with pytest.raises(Exception):
            safe_parse(io.BytesIO(lol.encode()))

    def test_benign_subdivisions_xml_still_parses(self):
        import io

        from nltk.xmlsec import parse as safe_parse

        benign = (
            "<localeDisplayNames><subdivisions>"
            '<subdivision type="usca">California</subdivision>'
            "</subdivisions></localeDisplayNames>"
        )
        tree = safe_parse(io.BytesIO(benign.encode()))
        subs = list(tree.iterfind("subdivisions/subdivision"))
        assert len(subs) == 1 and subs[0].text == "California"

# Natural Language Toolkit: net-new candidate attack matrix for the pathsec cluster
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Net-new attack candidates for the ``nltk.pathsec`` cluster (GHSA-8mgp-746c-j5xp
umbrella, #3753; CWE-22 / CWE-59 / CWE-59 / CWE-400 / CWE-409 / CWE-918).

Every other pathsec suite this file sits beside already carries a broad matrix
(``test_pathsec_io_attack_matrix.py``, ``test_attack_path_sandbox_expanded.py``,
``test_path_traversal_security.py``, ``test_attack_ssrf_expanded.py``,
``test_ssrf_url_encodings.py``, ``test_zipbomb_security.py``,
``test_aggregate_zip_bomb.py``, ``test_zip_extraction_toctou.py``,
``test_staging_tempdir_security.py``). This module deliberately avoids duplicating
them; each case here is a plausible vector those files do not yet exercise, and
every one is driven through the real guard (no mocked filesystem, no faked
verdict). Attacks must be REFUSED (``PermissionError`` / ``ValueError`` / refusal
before egress); benign controls must SUCCEED.

Net-new vectors:

* path -- a symlink-to-symlink chain (leaf pointing out of the root and leaf
  pointing back inside it), an absolute ``/proc/self`` and ``/etc/shadow`` system
  path refused by containment, the GHSA-8mgp blank-but-non-empty and control-only
  path, and a ``.zip`` virtual-path traversal that resolves outside an isolated
  nested root (the ENAMETOOLONG / long-component fallback branch of
  ``validate_path``);
* zip -- zip-slip member NAMES (``../``, nested ``..``, absolute), a symlink-typed
  member (which the extractor must never turn into an escaping symlink), and a
  benign nested-directory member as the over-block control;
* ssrf -- redirect re-validation refusing a non-http scheme (``file:`` / ``gopher:``
  / ``ftp:`` / ``dict:``) and an obfuscated-numeric / IPv4-mapped internal target,
  with a genuinely public redirect target as the over-block control.

POSIX-only vectors (symlink / ``/proc`` / symlink-typed member) are
``skipif``-guarded so the matrix stays green on every platform. Out-of-root
targets are staged under the real ``$HOME`` via the conftest ``sandbox`` /
``pathsec_sandbox`` fixtures (never a temp dir, which is itself an allowed root on
macOS).
"""

import os
import shutil
import socket
import stat
import tempfile
import zipfile
from pathlib import Path

import pytest

import nltk.data
from nltk import pathsec
from nltk.pathsec import (
    validate_network_url,
    validate_path,
    validate_tool_dir,
    validate_tool_path,
    validate_zip_archive,
)

REFUSALS = (PermissionError, ValueError)

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix",
    reason="symlink / /proc / symlink-typed zip member are POSIX vectors",
)


def _regular_file(directory, name="good.conll", body="x"):
    path = os.path.join(str(directory), name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    return path


# ==========================================================================
# 1. Symlink-to-symlink chains (the existing suites cover a single link only)
# ==========================================================================


@POSIX_ONLY
class TestSymlinkChains:
    def test_chain_leaf_pointing_outside_is_refused(self, pathsec_sandbox):
        # link1 -> link2 -> <outside>/secret. resolve() follows the whole chain,
        # so containment refuses the name; and even if the name check were bypassed
        # the O_NOFOLLOW open refuses a symlink leaf (CWE-59).
        root, outside = pathsec_sandbox
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").write("TOP-SECRET")
        link2 = os.path.join(str(root), "link2")
        os.symlink(secret, link2)
        link1 = os.path.join(str(root), "link1.conll")
        os.symlink(link2, link1)
        with pytest.raises(REFUSALS):
            validate_tool_path(link1)
        for mode in ("r", "w", "a"):
            with pytest.raises(REFUSALS):
                pathsec.open(link1, mode, required_root=str(root))
        assert open(secret).read() == "TOP-SECRET", "chain read/wrote the secret"

    def test_chain_leaf_pointing_back_inside_is_still_refused(self, restricted_sandbox):
        # A symlink chain that ultimately lands on a real in-root file is refused
        # anyway: the leaf handed to the tool is a symlink, and corpora/model files
        # are never symlinks, so O_NOFOLLOW refusing any symlink leaf is fail-closed.
        real = _regular_file(restricted_sandbox, "real.conll")
        l2 = os.path.join(restricted_sandbox, "l2")
        os.symlink(real, l2)
        l1 = os.path.join(restricted_sandbox, "l1.conll")
        os.symlink(l2, l1)
        with pytest.raises(REFUSALS):
            validate_tool_path(l1)

    def test_intermediate_symlink_to_outside_then_leaf_is_refused(
        self, pathsec_sandbox
    ):
        # The leaf name is benign but an INTERMEDIATE component is a symlink out of
        # the root (a chained parent redirect); resolve() walks through it and
        # containment refuses (TOCTOU-style escape).
        root, outside = pathsec_sandbox
        secret = os.path.join(str(outside), "secret")
        open(secret, "w").write("TOP-SECRET")
        hop = os.path.join(str(root), "hop")
        os.symlink(str(outside), hop)
        parent = os.path.join(str(root), "parent")
        os.symlink(hop, parent)  # parent -> hop -> outside
        with pytest.raises(REFUSALS):
            validate_tool_path(os.path.join(parent, "secret"))


# ==========================================================================
# 2. Absolute system paths refused by containment (net-new specific targets)
# ==========================================================================


class TestAbsoluteSystemPaths:
    @pytest.mark.parametrize(
        "target",
        [
            "/etc/passwd",
            "/etc/shadow",
            "/proc/self/environ",
            "/proc/self/maps",
            "/proc/self/cwd",
        ],
    )
    def test_absolute_system_path_is_refused_by_tool_guard(
        self, restricted_sandbox, target
    ):
        # None of these live under an allowed root, so validate_path refuses them
        # before the existence check ever runs (works on every platform: on Windows
        # each normalizes to a not-in-root relative name and is refused the same).
        with pytest.raises(REFUSALS):
            validate_tool_path(target)

    def test_absolute_system_path_is_refused_by_open(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            pathsec.open("/etc/passwd", "r")


# ==========================================================================
# 3. GHSA-8mgp: a blank-but-non-empty / control-only path must be validated
# ==========================================================================


class TestBlankAndControlOnlyPaths:
    @pytest.mark.parametrize("blank", ["   ", "\t", "\n", " \t ", "\x0b\x0c"])
    def test_blank_or_control_only_path_is_refused(self, restricted_sandbox, blank):
        # A whitespace/control-only string names a real relative file (it is NOT
        # empty), so it must reach containment and be refused, not waved through
        # to os.open in the working directory (GHSA-8mgp-746c-j5xp regression).
        with pytest.raises(REFUSALS):
            validate_path(blank, context="blank")

    def test_empty_path_is_a_benign_noop(self, restricted_sandbox):
        # Over-block control: an EMPTY path opens nothing, so it short-circuits to
        # a no-op (None) rather than being refused.
        assert validate_path("", context="empty") is None

    def test_blank_path_refused_at_tool_guard(self, restricted_sandbox):
        with pytest.raises(REFUSALS):
            validate_tool_path("   ")


# ==========================================================================
# 4. ``.zip`` virtual-path traversal resolving outside an isolated nested root
# ==========================================================================
# validate_path has a fallback branch for virtual paths inside a ZIP (a path whose
# ``resolve()`` raises, e.g. an over-long ENAMETOOLONG component on Linux). The
# security property must hold whichever branch runs: a ``.zip`` virtual path whose
# ``..`` components climb out of the data root is refused, while a legit in-root
# virtual path is allowed. Staged with the root's PARENT deliberately NOT an
# allowed root, so an escape is a genuine violation (not a temp-root artifact).


class TestZipVirtualTraversal:
    def _isolated_root(self):
        base = tempfile.mkdtemp(prefix=".nltk_zipvirt_", dir=str(Path.home()))
        dataroot = os.path.join(base, "nltk_data")
        os.makedirs(dataroot)
        with open(os.path.join(base, "secret.txt"), "w") as fh:
            fh.write("TOP-SECRET-ZIPVIRT")
        return base, dataroot

    def test_long_component_traversal_out_of_root_is_refused(self, monkeypatch):
        base, dataroot = self._isolated_root()
        try:
            monkeypatch.setattr(pathsec, "ENFORCE", True)
            monkeypatch.setattr(nltk.data, "path", [dataroot])
            monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
            monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
            # <root>/ok.zip/<6000 chars>/../../../secret.txt: on Linux resolve()
            # raises ENAMETOOLONG (fallback branch, the '..' check refuses it); on
            # macOS resolve() collapses it lexically to <base>/secret.txt, which
            # containment refuses. Either path is a refusal.
            long_comp = "A" * 6000
            payload = os.path.join(
                dataroot, "ok.zip", long_comp, "..", "..", "..", "secret.txt"
            )
            with pytest.raises(REFUSALS):
                validate_path(payload, context="zipvirt")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_nul_in_zip_virtual_path_is_refused(self, monkeypatch):
        base, dataroot = self._isolated_root()
        try:
            monkeypatch.setattr(pathsec, "ENFORCE", True)
            monkeypatch.setattr(nltk.data, "path", [dataroot])
            monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
            monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
            with pytest.raises(REFUSALS):
                validate_path(dataroot + "/ok.zip/a\x00b", context="zipvirt")
        finally:
            shutil.rmtree(base, ignore_errors=True)

    def test_legit_in_root_zip_virtual_path_is_allowed(self, monkeypatch):
        # Over-block control: a normal ``corpora.zip/corpora/file.txt`` virtual
        # path inside the root must NOT be refused.
        base, dataroot = self._isolated_root()
        try:
            monkeypatch.setattr(pathsec, "ENFORCE", True)
            monkeypatch.setattr(nltk.data, "path", [dataroot])
            monkeypatch.setattr(pathsec, "_ALLOWED_ROOTS_CACHE", None, raising=False)
            monkeypatch.setattr(pathsec, "_LAST_DATA_PATHS", None, raising=False)
            legit = os.path.join(dataroot, "corpora.zip", "corpora", "file.txt")
            assert validate_path(legit, context="zipvirt") is None
        finally:
            shutil.rmtree(base, ignore_errors=True)


# ==========================================================================
# 5. Zip-slip member NAMES (the existing zip suites cover bombs / TOCTOU only)
# ==========================================================================


class TestZipSlipMemberNames:
    def _archive(self, root, member, name="slip.zip"):
        path = os.path.join(str(root), name)
        with zipfile.ZipFile(path, "w") as handle:
            info = zipfile.ZipInfo(member)
            handle.writestr(info, b"PWN")
        return path

    @pytest.mark.parametrize(
        "member",
        [
            "../evil.txt",
            "../../etc/passwd",
            "pkg/../../evil",
            "a/../../../b",
            "/etc/passwd",  # absolute member name
        ],
    )
    def test_traversal_member_name_is_refused(self, restricted_sandbox, member):
        extract = os.path.join(restricted_sandbox, "ex")
        os.makedirs(extract, exist_ok=True)
        archive = self._archive(
            restricted_sandbox, member, name=f"slip_{abs(hash(member))}.zip"
        )
        with pytest.raises(REFUSALS):
            validate_zip_archive(archive, extract)

    def test_extractall_of_a_slip_member_writes_nothing_outside(
        self, restricted_sandbox
    ):
        # End-to-end: a ``../ESCAPED.txt`` member must be refused at extract time and
        # no file may appear above the extraction root.
        extract = os.path.join(restricted_sandbox, "dest")
        os.makedirs(extract, exist_ok=True)
        archive = self._archive(restricted_sandbox, "../ESCAPED.txt", name="esc.zip")
        with pytest.raises(REFUSALS):
            with pathsec.ZipFile(archive) as handle:
                handle.extractall(extract)
        assert not os.path.exists(os.path.join(restricted_sandbox, "ESCAPED.txt"))

    def test_benign_nested_directory_member_is_accepted(self, restricted_sandbox):
        # Over-block control: an ordinary nested-directory member validates and
        # extracts to the right in-root location.
        extract = os.path.join(restricted_sandbox, "ok_dest")
        os.makedirs(extract, exist_ok=True)
        archive = self._archive(restricted_sandbox, "pkg/sub/ok.txt", name="ok.zip")
        validate_zip_archive(archive, extract)  # must not raise
        with pathsec.ZipFile(archive) as handle:
            handle.extractall(extract)
        written = os.path.join(extract, "pkg", "sub", "ok.txt")
        assert os.path.isfile(written)
        with open(written, "rb") as fh:
            assert fh.read() == b"PWN"


# ==========================================================================
# 6. Symlink-TYPED zip members must never become an escaping symlink
# ==========================================================================


@POSIX_ONLY
class TestSymlinkTypedZipMember:
    def _symlink_member_zip(self, root, member_name, link_target, name="sym.zip"):
        path = os.path.join(str(root), name)
        info = zipfile.ZipInfo(member_name)
        # Mark the member as a symlink in its external attributes, the way a
        # hostile archive built with an archiver that preserves symlinks would.
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(path, "w") as handle:
            handle.writestr(info, link_target)
        return path

    def test_benign_named_symlink_member_extracts_as_a_regular_file(
        self, pathsec_sandbox
    ):
        # The member has a safe NAME but is symlink-typed with a traversal target.
        # The hardened extractor must NOT create a symlink: the leaf is written as
        # an ordinary in-root regular file, so it cannot redirect to /etc/passwd.
        root, outside = pathsec_sandbox
        victim = os.path.join(str(outside), "victim")
        open(victim, "w").write("ORIGINAL")
        extract = os.path.join(str(root), "dest")
        os.makedirs(extract)
        archive = self._symlink_member_zip(root, "link", "../../../../etc/passwd")
        with pathsec.ZipFile(archive) as handle:
            handle.extractall(extract)
        leaf = os.path.join(extract, "link")
        assert os.path.lexists(leaf), "member was not extracted at all"
        assert not os.path.islink(leaf), "extractor created an escaping symlink"
        assert stat.S_ISREG(os.lstat(leaf).st_mode)
        assert open(victim).read() == "ORIGINAL", "symlink member reached outside"

    def test_symlink_member_with_traversal_name_is_refused(self, restricted_sandbox):
        # A symlink-typed member whose NAME traverses is refused by the name check,
        # regardless of its symlink attribute.
        extract = os.path.join(restricted_sandbox, "ex")
        os.makedirs(extract, exist_ok=True)
        archive = self._symlink_member_zip(
            restricted_sandbox, "../escape", "/etc/passwd", name="symslip.zip"
        )
        with pytest.raises(REFUSALS):
            validate_zip_archive(archive, extract)


# ==========================================================================
# 7. SSRF redirect re-validation: net-new schemes and obfuscated targets
# ==========================================================================
# The existing suite covers redirect to a plain / decimal / IPv6-loopback / RFC1918
# target. These add the non-http schemes and the hex / octal / IPv4-mapped numeric
# spellings, each of which the redirect handler must refuse before the 3xx is
# followed. A genuinely public target is the over-block control.


class _FakeReq:
    full_url = "https://benign.example.com/start"

    def get_full_url(self):
        return self.full_url

    def get_method(self):
        return "GET"

    def has_header(self, name):
        return False


class TestRedirectRevalidation:
    @pytest.fixture(autouse=True)
    def enforce_on(self, monkeypatch):
        monkeypatch.setattr(pathsec, "ENFORCE", True)

    @pytest.mark.parametrize(
        "target",
        [
            "file:///etc/passwd",  # scheme downgrade to a local file
            "gopher://127.0.0.1/x",  # gopher smuggling
            "ftp://127.0.0.1/x",  # ftp to loopback
            "dict://127.0.0.1:11211/",  # memcached via dict
            "http://0x7f000001/admin",  # hex loopback
            "http://017700000001/x",  # octal loopback
            "http://[::ffff:127.0.0.1]/x",  # IPv4-mapped loopback literal
            "http://2852039166/",  # decimal 169.254.169.254 cloud metadata
        ],
    )
    def test_redirect_to_internal_or_non_http_is_refused(self, target, monkeypatch):
        # The Windows-nonfolding resolver is simulated (empty) so the numeric guard
        # itself must refuse the obfuscated forms.
        monkeypatch.setattr(pathsec, "_resolve_hostname", lambda h: [])
        handler = pathsec._ValidatingRedirectHandler()
        with pytest.raises((PermissionError, ValueError, OSError)):
            handler.redirect_request(_FakeReq(), None, 302, "Found", {}, target)

    def test_public_redirect_target_is_allowed(self, monkeypatch):
        # Over-block control: the redirect handler delegates to validate_network_url,
        # which must ACCEPT a genuinely public target (proven with the resolver
        # pinned to a public address so the verdict does not depend on live DNS).
        monkeypatch.setattr(
            pathsec,
            "_resolve_hostname",
            lambda h: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 80))
            ],
        )
        # validate_network_url is exactly what the handler calls first; a public
        # target returns without raising.
        assert validate_network_url("http://downloads.example.org/x") is None

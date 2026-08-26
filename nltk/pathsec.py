# Natural Language Toolkit: Centralized I/O security sentinel
#
# Copyright (C) 2001-2026 NLTK Project
# Author: Eric Kafe <kafe.eric@gmail.com>
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
#
"""Centralized I/O security sentinel for NLTK."""

"""Centralized I/O security sentinel for NLTK."""
import builtins
import http.client
import io
import ipaddress
import os
import re
import socket
import stat
import sys
import tempfile
import urllib.request
import warnings
import zipfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse

# A URL is not a filesystem path: to the kernel "http://.." is the dir "http:"
# then a ".." traversal. Anchored, whitespace-tolerant, case-insensitive match.
_URL_SCHEME_RE = re.compile(r"^\s*(?:https?|ftp)://", re.IGNORECASE)
_FILE_SCHEME_RE = re.compile(r"^\s*file:", re.IGNORECASE)

# Security Enforcement Toggle
# ENFORCE = False
ENFORCE = True

# When a proxy is configured, the proxy -- not NLTK -- resolves the hostname and
# performs the egress, so NLTK cannot pin the validated destination IP and its
# SSRF filter no longer governs where the request actually lands (CWE-918,
# GHSA-6ww7). Proxied fetches are therefore refused under ``ENFORCE`` unless the
# operator explicitly opts in here (or via ``NLTK_ALLOW_PROXIED_URLOPEN``),
# asserting that the proxy itself is trusted to be SSRF-safe.
ALLOW_PROXIED_FETCH = False

_ALLOWED_ROOTS_CACHE = None
_LAST_DATA_PATHS = None

# Reserved DOS device names. On Windows these resolve to a device rather than a
# file in the current directory, whatever the surrounding path is.
_WINDOWS_DEVICE_NAMES = frozenset(
    ["CON", "PRN", "AUX", "NUL"]
    + [f"COM{i}" for i in range(1, 10)]
    + [f"LPT{i}" for i in range(1, 10)]
)


def is_private_dir(path):
    """Return True if *path* is a directory safe to trust as a data root: another
    *unprivileged local user* cannot plant files in it.

    This is the test that distinguishes a shared, world-writable temp directory
    (Linux ``/tmp``, mode ``1777``) -- which a local attacker could use to plant
    trusted-looking data (CWE-377/CWE-378) -- from a *private* per-user temp
    directory (macOS ``$TMPDIR`` ``/var/folders/...`` mode ``0700``, Windows
    ``%TEMP%`` under the ACL-protected user profile), which is safe.

    Cross-platform:
      * POSIX: the directory must be owned by the current user (or root) and be
        neither group- nor world-writable (unless the writable group/other bit
        is paired with the sticky bit *and* the dir is user-owned -- but we keep
        it strict and simply reject any group/other-writable dir).
      * Windows: ``st_uid``/mode are not meaningful; the per-user temp/profile is
        ACL-protected, so a plain "exists and is a directory" check is used.
    """
    try:
        st = os.stat(path)
    except OSError:
        return False
    if not stat.S_ISDIR(st.st_mode):
        return False
    if os.name != "posix":
        # Windows / other: rely on the per-user profile ACLs (no POSIX mode).
        return True
    # Must be owned by us (or by root, e.g. a system-wide /usr/share dir).
    if st.st_uid not in (os.getuid(), 0):
        return False
    # Reject group- or world-writable directories: those let another account
    # write into (or, without the sticky bit, replace) the directory.
    if st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return False
    return True


def _get_allowed_roots():
    """Dynamically determines allowed directories based on NLTK data paths."""
    global _ALLOWED_ROOTS_CACHE, _LAST_DATA_PATHS

    current_paths = []
    if "nltk.data" in sys.modules:
        # Accessing nltk.data.path via sys.modules to avoid top-level circularity
        current_paths = list(getattr(sys.modules["nltk.data"], "path", []))

    env_paths = os.environ.get("NLTK_DATA", "")
    current_state = (current_paths, env_paths)

    if _ALLOWED_ROOTS_CACHE is not None and _LAST_DATA_PATHS == current_state:
        return _ALLOWED_ROOTS_CACHE

    roots = set()
    for p in current_paths + env_paths.split(os.pathsep):
        if p:
            try:
                # Handle both string paths and PathPointer objects
                raw_p = p.path if hasattr(p, "path") else p
                roots.add(Path(str(raw_p)).expanduser().resolve())
            except (OSError, ValueError, RuntimeError):
                continue

    candidate_locs = ["~/nltk_data", "/usr/share/nltk_data"]

    for loc in candidate_locs:
        try:
            p = Path(loc).expanduser().resolve()
            if p.exists():
                roots.add(p)
        except (OSError, ValueError, RuntimeError):
            continue

    # The system temp directory is trusted ONLY when it is private to the current
    # user.  A *shared, world-writable* temp dir (Linux ``/tmp``, mode ``1777``)
    # must not be an allowed root: a local attacker could plant trusted-looking
    # data there (CWE-377/CWE-378, GHSA-p4rw follow-up).  A *private* per-user
    # temp dir (macOS ``/var/folders/...`` mode ``0700``, Windows ``%TEMP%`` under
    # the user profile, or a private Linux ``$TMPDIR``) is safe and is where
    # NLTK / its test-suite legitimately stage temporary corpora, so it is kept.
    try:
        tmp = Path(tempfile.gettempdir()).resolve()
        if is_private_dir(tmp):
            roots.add(tmp)
    except (OSError, ValueError, RuntimeError):
        pass

    _ALLOWED_ROOTS_CACHE = roots
    _LAST_DATA_PATHS = current_state
    return roots


def validate_path(path_input, context="NLTK", required_root=None):
    """
    Ensures file access is restricted to allowed data directories.

    :param path_input: The path to validate.
    :param context: Diagnostic context for warnings/errors.
    :param required_root: If provided, enforces that the path is strictly
                          within this specific directory (scoped sandbox).
    """
    if isinstance(path_input, int) or not path_input or not str(path_input).strip():
        return
    try:
        raw = path_input.path if hasattr(path_input, "path") else str(path_input)

        # Reject a URL outright: no caller validates a network URL here, and
        # "http://../.." is a kernel traversal, not a host (GHSA-8mgp-746c-j5xp).
        if _URL_SCHEME_RE.match(raw):
            msg = (
                f"Security Violation [{context}]: a URL was passed to a "
                f"filesystem path check: {raw!r}. Use nltk.pathsec.urlopen() "
                "for network I/O."
            )
            if ENFORCE:
                raise PermissionError(msg)
            warnings.warn(msg, RuntimeWarning, stacklevel=3)
            return
        if _FILE_SCHEME_RE.match(raw):
            parsed = urlparse(raw)
            # urllib opens Request.selector (keeps ?/#/;) but urlparse().path
            # drops them -- that would validate a different file than opens.
            if parsed.query or parsed.fragment or ";" in parsed.path:
                raise PermissionError(
                    f"Security Violation [{context}]: ambiguous file URL "
                    f"(query/fragment/params) not allowed: {raw!r}"
                )
            raw = unquote(parsed.path)
            if not raw:
                return

        # Resolve path to catch symlink escapes
        try:
            target = Path(raw).resolve()
        except (OSError, ValueError):
            # Fallback for virtual paths inside ZIPs (e.g. corpora/foo.zip/file.txt)
            lower_raw = raw.lower()
            if ".zip" in lower_raw:
                zip_idx = lower_raw.find(".zip") + 4
                target = Path(raw[:zip_idx]).resolve()
            else:
                target = Path(raw)

        # LAYER 1: Scoped Sandbox (PR #3528 Integration)
        # This resolves both target and root to block symlink-based escapes.
        if required_root:
            root_raw = (
                required_root.path
                if hasattr(required_root, "path")
                else str(required_root)
            )
            scoped_root = Path(root_raw).resolve()
            if not (target == scoped_root or target.is_relative_to(scoped_root)):
                # Raise ValueError to match NLTK's historical CorpusReader error type
                raise ValueError(
                    f"Security Violation [{context}]: Path {target} escapes root {scoped_root}"
                )

        # LAYER 2: Global NLTK_DATA Sandbox
        allowed_roots = _get_allowed_roots()
        if any(target == root or target.is_relative_to(root) for root in allowed_roots):
            return

        # CWD Fallback (Explicit Opt-In for ENFORCE mode)
        try:
            cwd = Path(os.getcwd()).resolve()
            if target == cwd or target.is_relative_to(cwd):
                if any(cwd == root for root in allowed_roots):
                    return
                msg = (
                    f"Security Violation [{context}]: CWD access restricted in ENFORCE mode. "
                    "Authorize via: nltk.data.path.append('.')"
                )
                if ENFORCE:
                    raise PermissionError(msg)
                else:
                    warnings.warn(
                        f"Security Warning [{context}]: Path {target} allowed via CWD.",
                        RuntimeWarning,
                        stacklevel=3,
                    )
                    return
        except (OSError, ValueError):
            pass

        msg = f"Security Violation [{context}]: Unauthorized path {target}"
        if ENFORCE:
            raise PermissionError(msg)
        else:
            warnings.warn(msg, RuntimeWarning, stacklevel=3)
    except (PermissionError, ValueError):
        raise
    except Exception:
        if ENFORCE:
            raise


def _reject_bad_name_syntax(text, context):
    """Syntactic checks shared by every caller-supplied model or tool path.

    None of these can be a legitimate model, corpus or output file, so they are
    refused before the value is treated as a path at all. ``..`` is checked after
    folding ``\\`` to ``/``: a backslash is an ordinary filename character on
    POSIX but a separator on Windows, so ``..\\..\\etc`` has to be rejected on both.
    """

    def _refuse(why):
        raise ValueError(f"Security Violation [{context}]: {text!r} {why}.")

    if not text or not text.strip():
        _refuse("is empty")
    # A NUL truncates the path in a tool's native layer, so "good.ser.gz\0evil"
    # can name a different file there than it does here.
    if "\x00" in text:
        _refuse("contains a NUL byte")
    # A leading '-' would be parsed as another option by the tool we hand it to.
    if text.startswith("-"):
        _refuse("looks like a command-line option (argument injection)")
    # Stanford's loaders will fetch a URL; only local resources are permitted.
    if "://" in text or text.lower().startswith(("file:", "jar:")):
        _refuse("is a URL; only local resources are permitted")
    # Nothing downstream expands '~', but a sink that did would reach $HOME.
    if text.startswith("~"):
        _refuse("starts with '~'; pass an already-expanded path")
    # A Windows UNC path reaches a remote share.
    if text.startswith("\\\\") or text.startswith("//"):
        _refuse("is a UNC path; only local resources are permitted")
    if ".." in text.replace("\\", "/").split("/"):
        _refuse("contains a '..' component; it may not traverse out of the namespace")
    # ':' names an NTFS alternate data stream, except in a drive prefix (C:\...).
    # This also catches the drive-RELATIVE form "C:name", which means "name in
    # the current directory of drive C" and so escapes the validated location.
    if ":" in text and not re.match(r"^[A-Za-z]:[\\/]", text):
        _refuse("contains ':', which names an NTFS alternate data stream")
    # On Windows a leading separator with no drive is relative to the CURRENT
    # drive, so it names a different file than the same string does on POSIX.
    if os.name != "posix" and re.match(r"^[\\/]", text):
        _refuse("is relative to the current drive; give a full path with a drive")
    # On Windows these resolve to devices (a serial port, the null device) no
    # matter which directory they appear in. Refused everywhere for determinism.
    stem = os.path.basename(text.replace("\\", "/")).split(".")[0].upper()
    if stem in _WINDOWS_DEVICE_NAMES:
        _refuse(f"names the reserved Windows device {stem!r}")


def validate_model_resource(model_path, context="NLTK model"):
    """Bound a caller-supplied model argument that may be a *resource name*.

    Several JVM wrappers (Stanford parser/tagger/segmenter) accept the same
    ``-model`` argument as either a filesystem path or a jar-internal classpath
    resource, e.g. the default
    ``edu/stanford/nlp/models/lexparser/englishPCFG.ser.gz``. Bounding every value
    with :func:`validate_path` would break the jar-internal defaults, and skipping
    validation entirely lets an attacker hand the JVM any file on disk.

    So: a plain resource name is left alone, any real filesystem path is bounded to
    the NLTK data roots, and a value that is neither (empty, an option-looking
    token, a URL, or a ``..`` traversal) is refused outright so that a
    resource-looking name cannot traverse out of the jar namespace.

    ``..`` is checked after folding ``\\`` to ``/``: a backslash is an ordinary
    filename character on POSIX but a separator on Windows, so ``..\\..\\etc`` has
    to be rejected on both.

    :param model_path: the model argument as supplied by the caller
    :param context: label used in the security-violation message
    :raises ValueError: if the value is empty, option-like, a URL, or traverses
    :raises PermissionError: if it is a filesystem path outside the data roots
    """
    text = os.fspath(model_path)
    _reject_bad_name_syntax(text, context)

    # Only a real filesystem path is sandboxed; a bare resource name is not a
    # path. A bare name is deliberately NOT probed against the CWD: doing so made
    # the default `malt_temp.mco` resolve to whatever happened to sit in the
    # user's directory, which is exactly what older NLTK versions left there.
    has_directory = bool(os.path.dirname(text.replace("\\", "/")))
    if os.path.isabs(text) or (has_directory and os.path.exists(text)):
        validate_path(text, context=context)
        _reject_aliased_or_special(text, context)


def _reject_aliased_or_special(text, context, check_links=False):
    """Physical checks on a path that already passed :func:`validate_path`.

    A FIFO, socket or device planted in a data root would block the reader
    forever, so only regular files and directories are accepted. Directories stay
    legal, since corpora are passed as directories.

    ``check_links`` additionally refuses a hardlinked file. ``realpath()`` cannot
    see a hardlink, so an in-root alias of an outside file passes every
    name-based check and the tool would overwrite the original. This is only
    applied to paths the tool *writes*: for a read it is not an escalation (the
    link can only be created by someone who can already write to the data root),
    and rejecting ``st_nlink > 1`` outright would refuse ordinary
    hardlink-deduplicated data such as ``cp -l`` or ``rsync --link-dest`` trees,
    including the original file.

    A path that does not exist yet (an output file) has nothing to check.
    """
    try:
        info = os.stat(text)
    except OSError:
        return
    if check_links and stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
        raise PermissionError(
            f"Security Violation [{context}]: {text!r} has {info.st_nlink} hard "
            "links, so writing it may overwrite a file outside the trusted NLTK "
            "data roots."
        )
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise PermissionError(
            f"Security Violation [{context}]: {text!r} is not a regular file or "
            "directory; reading it could block indefinitely."
        )


def validate_tool_path(path_input, context="NLTK tool file", for_write=False):
    """Bound a filesystem path handed to an external tool to read or write.

    Unlike :func:`validate_model_resource` this never accepts a bare resource
    name: the value must be a real path inside the NLTK data roots. Use it for
    arguments the tool opens directly, such as MaltParser's ``-i`` input and
    ``-o`` output, where an unbounded value is an arbitrary file read and an
    arbitrary file write respectively.

    :param path_input: the path as supplied by the caller
    :param context: label used in the security-violation message
    :param for_write: True when the tool will write the path, which additionally
        refuses a hardlinked file that could alias a target outside the roots
    :raises ValueError: if the value is empty or contains a NUL byte
    :raises PermissionError: if it is outside the data roots or is a non-regular
        file such as a FIFO
    """
    text = os.fspath(path_input)
    _reject_bad_name_syntax(text, context)
    validate_path(text, context=context)
    _reject_aliased_or_special(text, context, check_links=for_write)


def _zip_member_is_unsafe(name_str):
    """True if a ZIP member is written somewhere other than where it is validated.

    ``zipfile.ZipFile.extract`` sanitises a member name by *dropping* the drive
    and every empty / ``.`` / ``..`` component while keeping the rest, whereas
    ``Path.resolve`` collapses a ``..`` against its *preceding* component.  For a
    member such as ``a/../b/x`` the two disagree: it is validated as ``<root>/b/x``
    but written to ``<root>/a/b/x``, which can escape through a pre-existing
    symlink at ``<root>/a/b`` that the collapsed validation path never visits.

    The mismatch only ever arises from absolute / drive-qualified / ``..`` members
    -- exactly the shapes a legitimate archive never uses -- so rather than keep
    two different normalizations in sync we reject them outright.  This both
    closes the validate/extract gap and is the proactive block the hardened
    extractor promises (CWE-22 / CWE-59).
    """
    # Normalize every separator zipfile treats as such on this platform to "/".
    normalized = name_str.replace("\\", "/") if os.path.altsep else name_str
    if os.path.splitdrive(name_str)[0] or normalized.startswith("/"):
        return True
    return os.path.pardir in normalized.split("/")


def validate_zip_archive(
    zip_obj_or_path, target_root, specific_member=None, context="ZipAudit"
):
    """Enhanced Zip-Slip protection using Pathlib for cross-platform safety."""
    try:
        target = Path(target_root).resolve()

        def _audit(zf):
            members = (
                [specific_member] if specific_member is not None else zf.namelist()
            )
            # Covers the raw-zipfile branch below, which bypasses ZipFile.__init__'s
            # entry-count guard on purpose (constructing one here would recurse).
            if specific_member is None:
                _member_count_guard()(
                    len(members), getattr(zf, "filename", None) or "<archive>"
                )
            for name in members:
                name_str = name.filename if hasattr(name, "filename") else str(name)
                if "\0" in name_str:
                    raise ValueError(f"Null byte in ZIP member: {name_str}")

                # ``resolve()`` follows symlinks, catching escapes through a
                # pre-existing symlinked subpath. The extra component check
                # rejects absolute / ``..`` members, whose write target diverges
                # from this resolved path (CWE-22 / CWE-59).
                member_path = (target / name_str).resolve()
                if _zip_member_is_unsafe(name_str) or not (
                    member_path == target or member_path.is_relative_to(target)
                ):
                    msg = f"Security Violation [{context}]: Traversal member '{name_str}' detected."
                    if ENFORCE:
                        raise PermissionError(msg)
                    else:
                        warnings.warn(msg, RuntimeWarning, stacklevel=3)

        if isinstance(zip_obj_or_path, zipfile.ZipFile):
            _audit(zip_obj_or_path)
        else:
            with zipfile.ZipFile(zip_obj_or_path, "r") as zf:
                _audit(zf)
    except (PermissionError, ValueError):
        raise
    except (OSError, zipfile.BadZipFile):
        if ENFORCE:
            raise PermissionError("Zip validation failed")


@lru_cache(maxsize=256)
def _resolve_hostname(hostname):
    """Cached hostname resolution for the early SSRF pre-check.

    Note: the cache alone does NOT prevent DNS rebinding, because the connection
    layer re-resolves the hostname independently. The actual rebinding
    protection is the connect-time IP pinning in ``_SafeHTTPConnection`` /
    ``_SafeHTTPSConnection``.
    """
    try:
        return socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError):
        return []


# IPv6->IPv4 transition prefixes that have no dedicated stdlib accessor.
_NAT64_WELL_KNOWN = ipaddress.ip_network("64:ff9b::/96")
_IPV4_COMPATIBLE = ipaddress.ip_network("::/96")


def _embedded_ipv4(ip):
    """The embedded IPv4 for IPv6 forms that *are* an IPv4 address, else None.

    Covers IPv4-mapped (``::ffff:0:0/96``), IPv4-compatible (``::/96``) and the
    NAT64 well-known prefix (``64:ff9b::/96``). For these the IPv6 wrapper has no
    independent routable meaning, so the embedded IPv4 is what gets reached.
    """
    if not isinstance(ip, ipaddress.IPv6Address):
        return None
    mapped = ip.ipv4_mapped
    if mapped is not None:
        return mapped
    if ip in _NAT64_WELL_KNOWN or ip in _IPV4_COMPATIBLE:
        return ipaddress.IPv4Address(ip.packed[-4:])
    return None


def _tunneled_ipv4s(ip):
    """IPv4 addresses tunneled by routable IPv6 wrappers (6to4 / Teredo)."""
    if not isinstance(ip, ipaddress.IPv6Address):
        return
    sixtofour = ip.sixtofour
    if sixtofour is not None:
        yield sixtofour
    teredo = ip.teredo
    if teredo is not None:
        yield from teredo  # (Teredo server, Teredo client)


def _ip_is_forbidden(ip):
    """Return True if the SSRF filter must refuse to connect to ``ip``.

    Policy (defense in depth): only *globally routable* addresses are allowed;
    anything that is not global -- loopback, link-local, private, carrier-grade
    NAT (100.64.0.0/10), reserved, unspecified (``0.0.0.0`` / ``::``),
    documentation ranges, etc. -- is forbidden. This generalises the previous
    explicit ``loopback / link-local / multicast / private`` list and is a strict
    superset of it. Multicast is still rejected explicitly because some CPython
    versions classify multicast addresses as ``is_global``.

    IPv6 addresses that embed an IPv4 address are evaluated by that embedded IPv4,
    not by the wrapper: the stdlib classifies the wrappers (IPv4-mapped,
    IPv4-compatible, NAT64 ``64:ff9b::/96``, 6to4 ``2002::/16``, Teredo
    ``2001:0::/32``) as globally routable, so a forbidden internal IPv4 (loopback,
    the link-local cloud-metadata address, ...) could otherwise be smuggled past
    the check and then routed to that IPv4 by a NAT64/6to4/Teredo gateway
    (CWE-918). This extends the previous IPv4-mapped-only unwrap.
    """
    embedded = _embedded_ipv4(ip)
    if embedded is not None:
        ip = embedded
    for tunneled in _tunneled_ipv4s(ip):
        if tunneled.is_multicast or not tunneled.is_global:
            return True
    return ip.is_multicast or not ip.is_global


def validate_network_url(url_input, context="NetworkIO"):
    """Hardened URL validation with SSRF protection."""
    if not url_input or not str(url_input).strip():
        return
    try:
        parsed = urlparse(str(url_input))

        if parsed.scheme == "file":
            file_path = unquote(parsed.path)
            netloc = parsed.netloc

            # Only local file:// URIs are allowed.
            # Reject remote/UNC-style authorities so validation matches actual access.
            if netloc not in ("", "localhost"):
                raise OSError(
                    f"Security Violation [{context}.file_scheme]: "
                    f"Non-local file URI authority not allowed: {netloc!r}"
                )

            # Windows file:// URIs arrive like /C:/path/to/file
            # Convert them to a native absolute path before validation.
            if (
                os.name == "nt"
                and len(file_path) >= 3
                and file_path[0] == "/"
                and file_path[2] == ":"
            ):
                file_path = file_path[1:]

            validate_path(file_path, context=f"{context}.file_scheme")
            return

        if parsed.scheme not in ("http", "https"):
            msg = (
                f"Security Violation [{context}]: Unsupported scheme '{parsed.scheme}'."
            )
            if ENFORCE:
                raise PermissionError(msg)
            else:
                warnings.warn(msg, RuntimeWarning, stacklevel=3)
            return

        for result in _resolve_hostname(parsed.hostname or ""):
            ip = ipaddress.ip_address(result[4][0])
            if _ip_is_forbidden(ip):
                msg = f"Security Violation [{context}]: SSRF attempt to restricted IP {ip}"
                if ENFORCE:
                    raise PermissionError(msg)
                else:
                    warnings.warn(msg, RuntimeWarning, stacklevel=3)
    except (PermissionError, ValueError):
        raise
    except Exception:
        if ENFORCE:
            raise


class _ValidatingRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Ensures that every step of a redirect chain is re-validated against SSRF."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_network_url(newurl, context="NetworkRedirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _resolve_and_validate_host(host, port):
    """
    Resolve ``host`` once and SSRF-validate *every* address it resolves to.

    Returns the resolved ``getaddrinfo`` records so the caller can connect to a
    **pinned** numeric address. Because validation and the subsequent connection
    observe the same resolution (the connection is made to the numeric IP, which
    triggers no further name lookup), this closes the DNS-rebinding TOCTOU where
    a hostname resolves to a public IP during validation and to an internal /
    loopback IP during the actual connect.
    """
    try:
        addrinfo = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError):
        return []
    for res in addrinfo:
        try:
            ip = ipaddress.ip_address(res[4][0])
        except ValueError:
            continue
        if _ip_is_forbidden(ip):
            msg = f"Security Violation [pathsec.urlopen]: SSRF attempt to restricted IP {ip}"
            if ENFORCE:
                raise PermissionError(msg)
            warnings.warn(msg, RuntimeWarning, stacklevel=2)
    return addrinfo


def _pinned_connection(host, port, timeout, source_address):
    """Open a socket to ``host``/``port`` over an SSRF-validated, pinned address.

    Every address ``host`` resolves to is validated together, then the socket is
    opened to those **numeric** addresses, so no second (unvalidated) name lookup
    happens at connect time -- this closes the DNS-rebinding TOCTOU.  All
    validated addresses are tried in order, preserving urllib/socket's normal
    dual-stack / multi-A fallback.  If nothing resolves to a validated address we
    fail closed: we never fall back to connecting by the raw hostname, which
    would re-resolve unvalidated and reopen the rebinding hole.
    """
    addrinfo = _resolve_and_validate_host(host, port)
    if not addrinfo:
        # Fail closed: never fall back to connecting by the raw hostname (that
        # would re-resolve unvalidated and reopen the rebinding hole). The host
        # produced no usable address, which is a name-resolution failure, so we
        # surface it as socket.gaierror rather than a bare OSError. gaierror is
        # an OSError subclass, so urllib still wraps it as URLError and the
        # fail-closed contract is unchanged; but callers that legitimately
        # expect a DNS failure -- e.g. obfuscated/decimal-IP hosts that some
        # platforms (Windows) refuse to resolve -- then see the expected
        # gaierror reason instead of an opaque OSError.
        raise socket.gaierror(
            f"pathsec.urlopen: no validated address for host {host!r}; "
            "refusing to connect by unvalidated hostname"
        )
    last_err = None
    for res in addrinfo:
        ip = res[4][0]
        try:
            return socket.create_connection((ip, port), timeout, source_address)
        except OSError as e:
            last_err = e
    raise last_err


class _SafeHTTPConnection(http.client.HTTPConnection):
    """HTTPConnection that resolves, SSRF-validates and pins the address at connect()."""

    def connect(self):
        self.sock = _pinned_connection(
            self.host, self.port, self.timeout, self.source_address
        )


class _SafeHTTPSConnection(http.client.HTTPSConnection):
    """HTTPS variant of :class:`_SafeHTTPConnection`.

    Connects to a validated, pinned IP but keeps SNI / certificate verification
    against the original hostname.
    """

    def connect(self):
        sock = _pinned_connection(
            self.host, self.port, self.timeout, self.source_address
        )
        self.sock = self._context.wrap_socket(sock, server_hostname=self.host)


class _SafeHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_SafeHTTPConnection, req)


class _SafeHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        kwargs = {}
        if getattr(self, "_context", None) is not None:
            kwargs["context"] = self._context
        if getattr(self, "_check_hostname", None) is not None:
            kwargs["check_hostname"] = self._check_hostname
        return self.do_open(_SafeHTTPSConnection, req, **kwargs)


def _proxied_fetch_allowed():
    """True only if the operator has explicitly opted into trusting the proxy."""
    if ALLOW_PROXIED_FETCH:
        return True
    return os.environ.get("NLTK_ALLOW_PROXIED_URLOPEN", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _reject_unpinnable_proxied_fetch(url_str):
    """Fail closed on a proxied fetch NLTK cannot SSRF-validate (CWE-918).

    A configured proxy performs the egress, so NLTK can neither pin the
    validated IP nor observe the address the proxy ultimately reaches. Rather
    than reintroduce the DNS-rebinding / internal-routing SSRF that the pinned
    direct path closes, refuse the request unless the operator has asserted the
    proxy is trusted (``ALLOW_PROXIED_FETCH`` / ``NLTK_ALLOW_PROXIED_URLOPEN``).
    """
    if _proxied_fetch_allowed():
        return
    msg = (
        f"Security Violation [pathsec.urlopen]: refusing a proxied fetch of "
        f"{url_str!r}. A configured proxy performs the egress, so NLTK cannot "
        "pin the validated IP and SSRF protection cannot be enforced (CWE-918). "
        "If and only if the proxy is trusted to be SSRF-safe, opt in via "
        "NLTK_ALLOW_PROXIED_URLOPEN=1 or nltk.pathsec.ALLOW_PROXIED_FETCH=True."
    )
    if ENFORCE:
        raise PermissionError(msg)
    warnings.warn(msg, RuntimeWarning, stacklevel=3)


def _env_proxy_carries(url_str):
    """True if an http/https environment proxy would actually carry ``url_str``.

    ``getproxies()`` reports a ``"no"`` key for ``NO_PROXY`` -- a host *exclusion*
    list, not a proxy -- so keying on the real ``http``/``https`` schemes and
    deferring the host decision to ``urllib.request.proxy_bypass`` mirrors what
    urllib actually does. That fixes the false positive where ``NO_PROXY`` alone
    made every fetch look proxied (issue #3748), while keeping the SSRF block
    (GHSA-6ww7) for a genuinely proxied egress: if a proxy would carry the
    request, NLTK cannot pin the validated IP, so it must still refuse.
    """
    proxies = urllib.request.getproxies()
    if "http" not in proxies and "https" not in proxies:
        return False
    host = urlparse(url_str).hostname
    return bool(host) and not urllib.request.proxy_bypass(host)


def urlopen(url, *args, **kwargs):
    """
    Secure wrapper for urllib.request.urlopen with redirect validation.
    Inherits NLTK proxy settings, but intentionally ignores other custom
    global handlers to strictly enforce the security sandbox.
    """
    url_str = url.full_url if hasattr(url, "full_url") else str(url)
    validate_network_url(url_str, context="pathsec.urlopen")

    # Start with our security-enforcing redirect handler
    handlers = [_ValidatingRedirectHandler()]

    # Safely inherit proxy settings without reusing handler instances
    # (Reusing instances overwrites their .parent, breaking the global opener)
    proxied = False
    has_proxy_handler = False
    if urllib.request._opener is not None:
        for handler in urllib.request._opener.handlers:
            if isinstance(handler, urllib.request.ProxyHandler):
                has_proxy_handler = True
                # Copy the dictionary to prevent shared mutable state
                isolated_proxies = dict(handler.proxies) if handler.proxies else {}
                if isolated_proxies:
                    proxied = True
                handlers.append(urllib.request.ProxyHandler(isolated_proxies))
            elif isinstance(handler, urllib.request.ProxyBasicAuthHandler):
                handlers.append(urllib.request.ProxyBasicAuthHandler(handler.passwd))
            elif isinstance(handler, urllib.request.ProxyDigestAuthHandler):
                handlers.append(urllib.request.ProxyDigestAuthHandler(handler.passwd))

    # If the caller configured no ProxyHandler at all, environment proxies still
    # apply: build_opener() would install a default ProxyHandler from
    # getproxies(). Treat that as proxied too -- but only when a proxy would
    # actually carry *this* URL, so NO_PROXY alone does not falsely block every
    # fetch (issue #3748). When it is genuinely proxied, the proxy is the egress
    # that resolves names and performs the CONNECT tunnel; the connect-time
    # pinning handlers cannot tunnel and would break proxied HTTPS.
    if not proxied and not has_proxy_handler and _env_proxy_carries(url_str):
        proxied = True

    if not proxied:
        # No proxy in effect: NLTK makes the connection itself, so pin the
        # validated IP (a rebinding hostname cannot be re-resolved to an internal
        # address at connect time). Add an explicit empty ProxyHandler so
        # build_opener() does not silently re-enable environment proxies, which
        # the pinning handlers cannot tunnel through.
        if not has_proxy_handler:
            handlers.append(urllib.request.ProxyHandler({}))
        handlers.append(_SafeHTTPHandler())
        handlers.append(_SafeHTTPSHandler())
    else:
        # Proxied: the proxy resolves the name and performs the egress, so the
        # earlier validate_network_url() only reflects NLTK's *local* view of the
        # host, not what the proxy actually reaches. A rebinding name or a proxy
        # with an internal network view re-opens SSRF (CWE-918, GHSA-6ww7). We
        # cannot pin through a proxy, so fail closed unless the operator has
        # asserted the proxy is trusted.
        _reject_unpinnable_proxied_fetch(url_str)

    opener = urllib.request.build_opener(*handlers)
    return opener.open(url, *args, **kwargs)


def _is_readonly_mode(mode):
    """True for a plain read mode with no create/write/append/update intent."""
    return set(mode) <= set("rbt") and "r" in mode


def _fd_realpath(fd):
    """The kernel's real path for an open descriptor, or ``None`` if unavailable.

    This reflects the inode actually opened, so validating it is race-free: no
    path re-resolution (which an attacker could win) is involved.
    """
    if sys.platform == "darwin":
        try:
            import fcntl

            f_getpath = 50  # <sys/fcntl.h> F_GETPATH
            buf = fcntl.fcntl(fd, f_getpath, b"\x00" * 1024)
            return os.fsdecode(buf.split(b"\x00", 1)[0])
        except (OSError, ValueError):
            return None
    try:  # Linux and other /proc systems
        return os.readlink(f"/proc/self/fd/{fd}")
    except OSError:
        return None


def _os_open_flags(mode):
    """Translate a :func:`builtins.open` *mode* string into ``os.open()`` flags.

    Mirrors the read/write/create/append/truncate intent of *mode* so the
    hardened opener can add ``O_NOFOLLOW`` on top of exactly what the caller
    asked for. POSIX only.
    """
    chars = set(mode)
    if "x" in chars:
        creat = os.O_CREAT | os.O_EXCL
    elif "w" in chars:
        creat = os.O_CREAT | os.O_TRUNC
    elif "a" in chars:
        creat = os.O_CREAT | os.O_APPEND
    else:  # "r" -- open existing, no create
        creat = 0
    if "+" in chars:
        access = os.O_RDWR
    elif chars & {"w", "a", "x"}:
        access = os.O_WRONLY
    else:
        access = os.O_RDONLY
    return access | creat


def _hardened_open(raw_path, mode, context, required_root, **kwargs):
    """Open ``raw_path`` for read *or* write, closing the symlink-swap TOCTOU and
    the hardlink escape that a path-only ``validate_path`` cannot.

    1. Open ``raw_path`` with ``O_NOFOLLOW`` so its final component is never
       followed as a symlink. Unlike opening a re-resolved path, this is atomic:
       the kernel either opens the real inode at that path or fails, so a symlink
       swapped in after the caller's ``validate_path`` cannot redirect the open
       (TOCTOU). On the write side this stops an attacker who plants/swaps
       ``<root>/pkg`` -> ``/etc/...`` between the check and a ``retrieve()`` /
       model write from redirecting the write outside the root -- the symmetric
       counterpart of the read-side content leak (CWE-59, GHSA-f794 class).
       Corpora/data files are never symlinks, so refusing a final-component
       symlink outright is fail-closed.
    2. ``fstat`` the descriptor and refuse ``st_nlink > 1``: a hardlink is another
       name for the same inode with no symlink to resolve, so an in-root hardlink
       to an outside inode would otherwise be read or written through.
    3. Re-validate the *opened descriptor's* real path (from the kernel, not by
       re-resolving the string) so a swapped intermediate directory symlink that
       redirected the open to an outside inode is still caught.

    A newly created file is given ``0600`` permissions so a write into a shared
    temp dir is not left group-/world-readable (CWE-377/378). POSIX only;
    callers fall back to :func:`builtins.open` elsewhere.
    """
    import errno

    flags = (
        _os_open_flags(mode)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        # 0o600 is only consulted when O_CREAT is in flags (write/append/x modes).
        fd = os.open(raw_path, flags, 0o600)
    except OSError as e:
        if e.errno in (errno.ELOOP, errno.EMLINK):
            raise PermissionError(
                f"Security Violation [pathsec.open]: refusing to follow a symlink "
                f"at open time for {raw_path!r} (TOCTOU guard, CWE-59)"
            ) from e
        raise
    try:
        st = os.fstat(fd)
        if st.st_nlink > 1:
            raise PermissionError(
                f"Security Violation [pathsec.open]: refusing multiply-linked file "
                f"{raw_path!r} (st_nlink={st.st_nlink}); a hardlink can point at an "
                "outside-root inode (CWE-59)"
            )
        # Validate what was actually opened (race-free: the fd is pinned). Falls
        # back to the resolved string only if the kernel path is unavailable.
        actual = _fd_realpath(fd)
        validate_path(
            actual if actual is not None else os.path.realpath(raw_path),
            context=context,
            required_root=required_root,
        )
    except BaseException:
        os.close(fd)
        raise
    try:
        return os.fdopen(fd, mode, **kwargs)
    except BaseException:
        # os.open() accepts some mode strings that os.fdopen() rejects (e.g. an
        # empty or malformed mode); without this the descriptor would leak and
        # repeated calls could exhaust the fd table (DoS).
        os.close(fd)
        raise


# Back-compat alias: the opener now handles write modes too, but external
# callers/tests may still import the original read-only name.
_hardened_read_open = _hardened_open


def open(file, mode="r", *, context="pathsec.open", required_root=None, **kwargs):
    """Secure wrapper for builtins.open."""
    # 1. Allow file descriptors (integers) to pass through, matching original logic
    if isinstance(file, int):
        validate_path(file, context=context, required_root=required_root)
        return builtins.open(file, mode=mode, **kwargs)

    # 2a. NLTK PathPointer objects (e.g. FileSystemPathPointer, which is a str
    # subclass) expose a string ``.path``; normalise to that exact string so the
    # strict primitive check below accepts it, matching validate_path's handling.
    if type(file) not in (str, bytes) and isinstance(
        getattr(file, "path", None), (str, bytes)
    ):
        file = file.path

    # 2. Force extraction of the real path from PathLike objects
    try:
        raw_path = os.fspath(file)
    except TypeError:
        raise TypeError("Path must be a string, bytes, or os.PathLike") from None

    # 3. Strict primitive enforcement against type manipulation
    if type(raw_path) not in (str, bytes):
        raise TypeError(
            f"Strict security policy: Path must resolve to exact str or bytes, not '{type(raw_path).__name__}'"
        )

    if type(raw_path) is bytes:
        raw_path = os.fsdecode(raw_path)

    # 4. Execution Substitution: validate and open the pure primitive, discarding the original object
    validate_path(raw_path, context=context, required_root=required_root)
    # 5. Under enforcement on POSIX, additionally close the validate-then-open
    # symlink TOCTOU and the hardlink escape that a path-based check cannot see.
    # This now covers read *and* write/append/update modes: the write side is the
    # symmetric counterpart of the read-side leak -- a symlink swapped in at the
    # destination after validate_path would otherwise let a retrieve()/model write
    # land outside the root (CWE-59). Non-POSIX keeps the plain open.
    if ENFORCE and os.name == "posix":
        # The hardened path owns this open entirely: it raises PermissionError /
        # ValueError on a security violation and the usual OSError (e.g.
        # FileNotFoundError) on a genuine open failure. We must NOT fall back to
        # builtins.open on OSError -- retrying the raw path would follow a symlink
        # the hardened open deliberately refused, reopening the TOCTOU leak.
        return _hardened_open(raw_path, mode, context, required_root, **kwargs)
    return builtins.open(raw_path, mode=mode, **kwargs)


def _decompression_guards():
    # Deferred to break the nltk.data <-> nltk.pathsec import cycle (data owns the
    # public MAX_UNZIP_* policy); runs once both modules are fully loaded.
    from nltk.data import (
        _bounded_stream_read,
        _check_decompression_bomb,
        _reject_decompression_total,
    )

    return _check_decompression_bomb, _bounded_stream_read, _reject_decompression_total


def _member_count_guard():
    """Deferred import of the central-directory-bomb check (see above)."""
    from nltk.data import _check_zip_member_count

    return _check_zip_member_count


class _BoundedZipExtFile(io.RawIOBase):
    """Wraps zipfile's streaming member reader and refuses a decompression bomb
    (CWE-409) as the member is consumed: it accumulates the ACTUAL decompressed
    bytes and applies nltk's ratio/size policy on every read, so streaming and
    partial reads keep working (unlike buffering the whole member into memory)
    while an over-expanding member is cut off mid-stream before it can exhaust RAM.

    All reads funnel through :meth:`readinto`; wrap this in an ``io.BufferedReader``
    to get ``read``/``readline``/``peek``/iteration, every one of them bounded.
    """

    def __init__(self, raw, compress_size, name, reject):
        self._raw = raw
        self._compress_size = compress_size
        self._name = name
        self._reject = reject
        self._total = 0

    def readable(self):
        return True

    def readinto(self, b):
        n = self._raw.readinto(b)
        if n:
            self._total += n
            self._reject(self._total, self._compress_size, self._name, "zip")
        return n

    def close(self):
        try:
            raw = getattr(self, "_raw", None)
            if raw is not None:
                self._raw = None
                raw.close()
        finally:
            super().close()


class ZipFile(zipfile.ZipFile):
    """Secure wrapper for zipfile.ZipFile."""

    def __init__(self, file, *args, **kwargs):
        # zipfile.ZipFile also accepts file-like objects (e.g., io.BytesIO).
        # We only strictly normalize and validate path-like objects.
        if isinstance(file, (str, bytes, os.PathLike)):
            try:
                raw_path = os.fspath(file)
            except TypeError:
                raise TypeError(
                    "Path must be a string, bytes, or os.PathLike"
                ) from None

            if type(raw_path) not in (str, bytes):
                raise TypeError(
                    f"Strict security policy: Path must resolve to exact str or bytes, not '{type(raw_path).__name__}'"
                )

            if type(raw_path) is bytes:
                raw_path = os.fsdecode(raw_path)

            validate_path(raw_path, context="pathsec.ZipFile")
            file_to_open = raw_path
        else:
            file_to_open = file

        super().__init__(file_to_open, *args, **kwargs)
        # Refuse a central-directory bomb here, the earliest point the entry count
        # is known, so no consumer pays to list, validate or extract its members.
        if getattr(self, "mode", "r") == "r":
            _member_count_guard()(
                len(self.filelist), getattr(self, "filename", None) or "<archive>"
            )

    def extract(self, member, path=None, pwd=None):
        validate_zip_archive(self, path or os.getcwd(), specific_member=member)
        return super().extract(member, path, pwd)

    def extractall(self, path=None, members=None, pwd=None):
        validate_zip_archive(self, path or os.getcwd())
        super().extractall(path, members, pwd)

    def read(self, name, pwd=None):
        # Not the raw one-shot super().read() (bounded only by the attacker-declared
        # size): stream it and cap the ACTUAL bytes produced (CWE-409).
        _check_decompression_bomb, _bounded_stream_read, _ = _decompression_guards()
        info = name if isinstance(name, zipfile.ZipInfo) else self.getinfo(name)
        _check_decompression_bomb(info)  # cheap declared-size early reject
        with super().open(info, mode="r", pwd=pwd) as raw:
            return _bounded_stream_read(raw, info.compress_size, info.filename)

    def open(self, name, mode="r", pwd=None, *, force_zip64=False):
        # Write mode has no member to decompress; only reads are bounded.
        if mode != "r":
            return super().open(name, mode, pwd, force_zip64=force_zip64)
        # Preserve zipfile.open()'s streaming/partial-read contract: hand back a bounded
        # reader that caps the ACTUAL bytes and cuts off an over-expanding member (CWE-409).
        _check_decompression_bomb, _, _reject = _decompression_guards()
        info = name if isinstance(name, zipfile.ZipInfo) else self.getinfo(name)
        _check_decompression_bomb(info)
        raw = super().open(info, mode="r", pwd=pwd, force_zip64=force_zip64)
        try:
            return io.BufferedReader(
                _BoundedZipExtFile(raw, info.compress_size, info.filename, _reject)
            )
        except BaseException:
            raw.close()
            raise


__all__ = [
    "validate_path",
    "validate_model_resource",
    "validate_tool_path",
    "validate_network_url",
    "validate_zip_archive",
    "open",
    "urlopen",
    "ZipFile",
    "ENFORCE",
]

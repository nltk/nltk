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
import ipaddress
import os
import socket
import sys
import urllib.request
import warnings
import zipfile
from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlparse

# Security Enforcement Toggle
# ENFORCE = False
ENFORCE = True

_ALLOWED_ROOTS_CACHE = None
_LAST_DATA_PATHS = None


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
                roots.add(Path(str(raw_p)).resolve())
            except (OSError, ValueError, RuntimeError):
                continue

    import tempfile

    for loc in ["~/nltk_data", "/usr/share/nltk_data", tempfile.gettempdir()]:
        try:
            p = Path(loc).expanduser().resolve()
            if p.exists():
                roots.add(p)
        except (OSError, ValueError, RuntimeError):
            continue

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

        if "://" in raw:
            parsed = urlparse(raw)
            if parsed.scheme in ("http", "https", "ftp"):
                return
            if parsed.scheme == "file":
                raw = unquote(parsed.path)

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
    # getproxies(). Treat that as proxied too, because the proxy -- not NLTK --
    # is then the egress that resolves names and performs the CONNECT tunnel; the
    # connect-time pinning handlers cannot tunnel and would break proxied HTTPS.
    if not proxied and not has_proxy_handler and urllib.request.getproxies():
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

    opener = urllib.request.build_opener(*handlers)
    return opener.open(url, *args, **kwargs)


def open(file, mode="r", *, context="pathsec.open", required_root=None, **kwargs):
    """Secure wrapper for builtins.open."""
    # 1. Allow file descriptors (integers) to pass through, matching original logic
    if isinstance(file, int):
        validate_path(file, context=context, required_root=required_root)
        return builtins.open(file, mode=mode, **kwargs)

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
    return builtins.open(raw_path, mode=mode, **kwargs)


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

    def extract(self, member, path=None, pwd=None):
        validate_zip_archive(self, path or os.getcwd(), specific_member=member)
        return super().extract(member, path, pwd)

    def extractall(self, path=None, members=None, pwd=None):
        validate_zip_archive(self, path or os.getcwd())
        super().extractall(path, members, pwd)


__all__ = [
    "validate_path",
    "validate_network_url",
    "validate_zip_archive",
    "open",
    "urlopen",
    "ZipFile",
    "ENFORCE",
]

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
ENFORCE = False

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

                member_path = (target / name_str).resolve()
                if not (member_path == target or member_path.is_relative_to(target)):
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
    """Cached hostname resolution to mitigate DNS rebinding."""
    try:
        return socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError):
        return []


def validate_network_url(url_input, context="NetworkIO"):
    """Hardened URL validation with SSRF protection."""
    if not url_input or not str(url_input).strip():
        return
    try:
        parsed = urlparse(str(url_input))
        if parsed.scheme == "file":
            validate_path(unquote(parsed.path), context=f"{context}.file_scheme")
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
            if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_private:
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
    if urllib.request._opener is not None:
        for handler in urllib.request._opener.handlers:
            if isinstance(handler, urllib.request.ProxyHandler):
                # Copy the dictionary to prevent shared mutable state
                isolated_proxies = dict(handler.proxies) if handler.proxies else {}
                handlers.append(urllib.request.ProxyHandler(isolated_proxies))
            elif isinstance(handler, urllib.request.ProxyBasicAuthHandler):
                handlers.append(urllib.request.ProxyBasicAuthHandler(handler.passwd))
            elif isinstance(handler, urllib.request.ProxyDigestAuthHandler):
                handlers.append(urllib.request.ProxyDigestAuthHandler(handler.passwd))

    opener = urllib.request.build_opener(*handlers)
    return opener.open(url, *args, **kwargs)


def open(file, mode="r", **kwargs):
    """Secure wrapper for builtins.open."""
    validate_path(file, context="pathsec.open")
    return builtins.open(file, mode=mode, **kwargs)


class ZipFile(zipfile.ZipFile):
    """Secure wrapper for zipfile.ZipFile."""

    def __init__(self, file, *args, **kwargs):
        if isinstance(file, (str, Path)):
            validate_path(file, context="pathsec.ZipFile")
        super().__init__(file, *args, **kwargs)

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

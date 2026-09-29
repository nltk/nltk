# Natural Language Toolkit: pathsec special-file and exact-text tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Two ``nltk.pathsec`` hardenings the chat80 store class relies on.

* ``validate_path`` validates the characters a native open will use. A ``str``
  subclass that overrides ``__str__`` (or carries a ``path`` attribute) showed
  one path to the check while ``shelve``/``sqlite3`` opened its real characters,
  so a caller-supplied store name could pass validation and be created outside
  every data root (CWE-59, the 7j4p store class).
* ``pathsec.open`` never blocks on, or reads from, a FIFO, socket or device: the
  open is non-blocking, the inode is inspected before any read, and a special
  file is refused as a security decision instead of hanging the reader.

Every verdict comes from the filesystem (what exists, what was opened, how long
it took), not from the exception alone.
"""

import os
import socket
import threading
import time

import pytest

import nltk.pathsec as pathsec
from nltk.pathsec import validate_path

SECURITY = (PermissionError, ValueError)


class _LyingStr(str):
    """Real characters ``real``; every Python-level view shows ``shown``."""

    def __new__(cls, real, shown):
        obj = str.__new__(cls, real)
        obj._shown = shown
        return obj

    def __str__(self):
        return self._shown

    def __repr__(self):
        return repr(self._shown)

    @property
    def path(self):
        return self._shown


class _LyingPathAttr:
    """Not a str: ``path`` shows an in-root name, ``__fspath__`` the real one."""

    def __init__(self, real, shown):
        self._real, self.path = real, shown

    def __fspath__(self):
        return self._real


class TestValidatePathUsesExactCharacters:
    def test_lying_str_subclass_is_judged_on_its_real_characters(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        lying = _LyingStr(str(outside / "pwn"), str(root / "ok"))
        with pytest.raises(PermissionError, match="Unauthorized path"):
            validate_path(lying, context="test")

    def test_exact_text_ignores_str_and_path_overrides(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        lying = _LyingStr(str(outside / "pwn"), str(root / "ok"))
        assert pathsec._exact_path_text(lying) == str(outside / "pwn")
        assert type(pathsec._exact_path_text(lying)) is str

    def test_non_str_pointer_is_taken_from_its_path_attribute(self, pathsec_sandbox):
        root, outside = pathsec_sandbox

        class PointerOnly:
            """A dataset-style pointer: a path attribute and no __fspath__."""

            def __init__(self, path):
                self.path = path

        # validated on .path, which is also what pathsec.open opens
        assert pathsec._exact_path_text(PointerOnly(str(root / "a"))) == str(root / "a")
        validate_path(PointerOnly(str(root / "a")))
        with pytest.raises(PermissionError, match="Unauthorized path"):
            validate_path(PointerOnly(str(outside / "pwn")))
        # an object answering __fspath__ with a different name is never
        # validated on its path attribute: it is refused as two-faced
        with pytest.raises(PermissionError, match="two different files"):
            pathsec._exact_path_text(
                _LyingPathAttr(str(outside / "pwn"), str(root / "a"))
            )

    def test_required_root_is_read_exactly_too(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        os.makedirs(str(root / "corpus"))
        lying_root = _LyingStr(str(root / "corpus"), str(outside))
        # the real root is root/corpus, so root/corpus/x is inside it
        validate_path(str(root / "corpus" / "x"), required_root=lying_root)
        with pytest.raises(ValueError, match="escapes root"):
            validate_path(str(root / "other"), required_root=lying_root)

    def test_val_dump_with_lying_name_creates_nothing_outside(self, pathsec_sandbox):
        """The store-class consequence: before the fix this created outside/pwn."""
        from nltk.sem import chat80

        root, outside = pathsec_sandbox
        lying = _LyingStr(str(outside / "pwn"), str(root / "ok"))
        with pytest.raises(PermissionError, match="Security Violation"):
            chat80.val_dump([], lying)
        assert os.listdir(str(outside)) == []

    def test_lying_name_passes_when_exact_text_is_bypassed(
        self, pathsec_sandbox, monkeypatch
    ):
        """Teeth: put the old str() coercion back and validate_path waves the
        lying name through, proving the exact-text coercion is what holds the
        line. (val_dump itself stays refused on this branch because the store
        link guard re-validates the real characters of every backing name; on
        develop, without that guard, the same call created outside/pwn.)"""
        root, outside = pathsec_sandbox
        lying = _LyingStr(str(outside / "pwn"), str(root / "ok"))
        monkeypatch.setattr(
            pathsec, "_exact_path_text", lambda value, context="NLTK": str(value)
        )
        validate_path(lying, context="test")  # old behaviour: not refused
        monkeypatch.undo()
        with pytest.raises(PermissionError):
            validate_path(lying, context="test")

    def test_non_str_object_is_validated_on_its_fspath(self, pathsec_sandbox):
        """A stdlib sink opens os.fspath(obj); a lying __str__ must not matter."""
        root, outside = pathsec_sandbox

        class LyingStr:
            def __str__(self):
                return str(root / "ok")

            def __fspath__(self):
                return str(outside / "pwn")

        with pytest.raises(PermissionError, match="Unauthorized path"):
            validate_path(LyingStr(), context="test")

    def test_object_whose_path_and_fspath_disagree_is_refused(self, pathsec_sandbox):
        """.path in-root, __fspath__ outside: validated on one face and opened
        on the other before; now refused as ambiguous, by validate_path and by
        pathsec.open alike."""
        root, outside = pathsec_sandbox

        class TwoFaced:
            path = str(root / "ok")

            def __fspath__(self):
                return str(outside / "pwn")

        with pytest.raises(PermissionError, match="two different files"):
            validate_path(TwoFaced(), context="test")
        with pytest.raises(PermissionError, match="two different files"):
            pathsec.open(TwoFaced(), "rb")
        assert os.listdir(str(outside)) == []

    def test_honest_path_objects_still_pass(self, pathsec_sandbox):
        import pathlib

        root, outside = pathsec_sandbox
        target = str(root / "ok.txt")
        with open(target, "w", encoding="utf8") as f:
            f.write("x")

        class Honest:
            path = target

            def __fspath__(self):
                return target

        class BytesPath:
            def __fspath__(self):
                return target.encode()

        validate_path(pathlib.Path(target), context="test")
        validate_path(Honest(), context="test")
        validate_path(BytesPath(), context="test")
        with pathsec.open(Honest(), "rb") as f:
            assert f.read() == b"x"
        with pathsec.open(pathlib.Path(target), "rb") as f:
            assert f.read() == b"x"

    def test_fspath_returning_garbage_is_refused(self, pathsec_sandbox):
        class Garbage:
            def __fspath__(self):
                return 42

        with pytest.raises(PermissionError, match="not a filesystem path"):
            validate_path(Garbage(), context="test")

    def test_plain_and_pointer_paths_unchanged(self, pathsec_sandbox):
        from nltk.data import FileSystemPathPointer

        root, outside = pathsec_sandbox
        ok = str(root / "ok.txt")
        with open(ok, "w", encoding="utf8") as f:
            f.write("x")
        validate_path(ok)
        validate_path(FileSystemPathPointer(ok))
        with pytest.raises(PermissionError):
            validate_path(str(outside / "no.txt"))


def _finishes_within(seconds, fn):
    done, out = threading.Event(), {}

    def run():
        try:
            out["v"] = fn()
        except BaseException as exc:
            out["e"] = exc
        finally:
            done.set()

    started = time.monotonic()
    threading.Thread(target=run, daemon=True).start()
    finished = done.wait(seconds)
    return finished, out.get("e"), time.monotonic() - started


class TestByNameLinkCheckForNonPosixOpens:
    """The inode policy applied by name where O_NOFOLLOW is unavailable. It is
    exercised directly here so its verdicts are proven on every platform; the
    non-POSIX open branch calls it before builtins.open."""

    def test_symlink_hardlink_and_missing_names(self, pathsec_sandbox):
        root, outside = pathsec_sandbox
        real = str(root / "real.txt")
        with open(real, "w", encoding="utf8") as f:
            f.write("x")
        pathsec._reject_link_or_special_by_name(real, "test")  # plain file passes
        pathsec._reject_link_or_special_by_name(str(root / "absent"), "test")
        link = str(root / "link.txt")
        os.symlink(real, link)
        with pytest.raises(PermissionError, match="symlink"):
            pathsec._reject_link_or_special_by_name(link, "test")
        hard = str(root / "hard.txt")
        os.link(real, hard)
        with pytest.raises(PermissionError, match="multiply-linked"):
            pathsec._reject_link_or_special_by_name(hard, "test")

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_fifo_by_name(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        fifo = str(root / "planted.fifo")
        os.mkfifo(fifo)
        with pytest.raises(PermissionError, match="FIFO"):
            pathsec._reject_link_or_special_by_name(fifo, "test")

    def test_non_posix_tool_path_branch_refuses_a_hardlink(
        self, pathsec_sandbox, monkeypatch
    ):
        """The tool-path open check has a stat-only branch off POSIX; it must
        refuse a multiply-linked file like the fstat branch does (the weka -l
        read of a hardlinked model was accepted on Windows without it)."""
        root, _ = pathsec_sandbox
        real = str(root / "model.bin")
        with open(real, "wb") as f:
            f.write(b"m")
        hard = str(root / "alias.bin")
        os.link(real, hard)
        monkeypatch.setattr(pathsec.os, "name", "nt")
        with pytest.raises(PermissionError, match="multiply-linked"):
            pathsec._reject_unsafe_open(hard, "test", must_exist=True)
        os.unlink(hard)
        pathsec._reject_unsafe_open(real, "test", must_exist=True)  # single link passes
        pathsec._reject_unsafe_open(str(root / "absent"), "test", must_exist=False)

    def test_non_posix_open_branch_is_wired_to_it(self):
        """The fallback branch cannot be forced on a POSIX interpreter (pathlib
        refuses a foreign flavour), so the wiring is pinned from the source: the
        by-name check runs in the non-POSIX enforcing branch of pathsec.open,
        before builtins.open. Windows CI exercises it through the store harness."""
        import inspect

        source = inspect.getsource(pathsec.open)
        branch = source.index("if ENFORCE:\n")
        assert "_reject_link_or_special_by_name(raw_path, context)" in source[branch:]
        assert source.index("_reject_link_or_special_by_name") < source.rindex(
            "builtins.open("
        )


@pytest.mark.skipif(os.name != "posix", reason="hardened open is POSIX-only")
class TestHardenedOpenRefusesSpecialFiles:
    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_fifo_is_refused_without_blocking(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        fifo = str(root / "planted.fifo")
        os.mkfifo(fifo)
        finished, exc, took = _finishes_within(10, lambda: pathsec.open(fifo, "rb"))
        assert finished, "pathsec.open blocked on a FIFO"
        assert isinstance(exc, PermissionError) and "FIFO" in str(exc), exc
        assert took < 5

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_fifo_write_mode_is_refused_too(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        fifo = str(root / "planted.fifo")
        os.mkfifo(fifo)
        finished, exc, _ = _finishes_within(10, lambda: pathsec.open(fifo, "wb"))
        assert finished and isinstance(exc, PermissionError), exc

    @pytest.mark.skipif(not hasattr(socket, "AF_UNIX"), reason="no unix sockets")
    def test_unix_socket_is_refused(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        path = str(root / "planted.sock")
        if len(path) > 100:
            pytest.skip("socket path too long for AF_UNIX here")
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.bind(path)
            with pytest.raises(PermissionError, match="Security Violation"):
                pathsec.open(path, "rb")
        finally:
            sock.close()

    def test_regular_file_reads_and_writes_normally(self, pathsec_sandbox):
        root, _ = pathsec_sandbox
        path = str(root / "data.txt")
        with pathsec.open(path, "w", encoding="utf8") as f:
            f.write("payload")
        with pathsec.open(path, "r", encoding="utf8") as f:
            assert f.read() == "payload"
        # the non-blocking flag used for the probe is cleared on the returned file
        import fcntl

        with pathsec.open(path, "rb") as f:
            assert not fcntl.fcntl(f.fileno(), fcntl.F_GETFL) & os.O_NONBLOCK

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="no FIFOs here")
    def test_bare_open_would_block_so_the_guard_has_teeth(self, pathsec_sandbox):
        """The primitive the hardening replaces does block: a plain O_NOFOLLOW
        open of the same FIFO does not return within the window."""
        root, _ = pathsec_sandbox
        fifo = str(root / "planted.fifo")
        os.mkfifo(fifo)
        finished, _, _ = _finishes_within(
            2, lambda: os.open(fifo, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        )
        assert not finished, "a bare open did not block; nothing to guard against"
        # unblock the reader thread so it does not linger
        writer = os.open(fifo, os.O_WRONLY | os.O_NONBLOCK)
        os.close(writer)

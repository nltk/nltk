# Natural Language Toolkit: owner-only fixture files for the security tests
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT
"""Fixture files and directories that pathsec's trust checks accept under any umask.

``open(path, "w")`` and ``os.makedirs`` take their mode from the umask. With
umask 002 they come out group-writable, the trust checks refuse them, and the
test trips on that refusal before it gets to the guard it was written for.
"""

import errno
import os


def write_private(path: str, data: str | bytes, mode: int = 0o600) -> str:
    """Create ``path`` with ``data`` and ``mode``.

    The umask only clears bits, so the file never ends up more open than
    ``mode``. Use ``mode=0o700`` for an executable.

    Raises:
        FileExistsError: Something is already at ``path``, a dangling symlink
            included. ``O_EXCL`` never overwrites, so pass a fresh path or
            remove the old fixture first.
    """
    # without O_BINARY, Windows writes \n as \r\n
    flags: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    fd: int = os.open(path, flags, mode=mode)
    payload: bytes = data.encode("utf-8") if isinstance(data, str) else data
    with os.fdopen(fd, "wb") as f:
        f.write(payload)
    return path


def makedirs_private(path: str) -> str:
    """Create ``path`` and any missing parents, each with mode 0700.

    ``os.makedirs(path, mode=0o700)`` only applies the mode to the leaf, so a
    parent it creates under umask 002 ends up 0775. Directories that already
    exist, ``path`` included, keep their mode and are never tightened, so
    start from a base that is already private. See ``make_home_dir`` in
    ``conftest.py`` for one that pathsec's private-chain check accepts.
    """
    missing: list[str] = []
    level: str = os.path.abspath(path)
    while not os.path.isdir(level):
        missing.append(level)
        parent: str = os.path.dirname(level)
        # dirname of a root is the root, so a missing drive would loop forever
        if parent == level:
            raise FileNotFoundError(errno.ENOENT, "root does not exist", level)
        level = parent
    for level in reversed(missing):
        os.mkdir(level, mode=0o700)
    return path

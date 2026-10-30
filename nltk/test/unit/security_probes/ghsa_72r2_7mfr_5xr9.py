"""GHSA-72r2-7mfr-5xr9 [medium] -- FileSystemPathPointer.open() sandbox check is dead code — arbitrary file read via file:// protocol"""

from ._base import FIXED, VULNERABLE, probe


@probe("GHSA-72r2-7mfr-5xr9")
def _filesystempathpointer_open():
    """FileSystemPathPointer.open()'s sandbox check was dead code."""
    from nltk.data import FileSystemPathPointer

    try:
        FileSystemPathPointer("/etc/passwd").open().close()
        return VULNERABLE, "opened /etc/passwd through FileSystemPathPointer"
    except Exception as exc:
        return FIXED, "/etc/passwd -> %s" % type(exc).__name__

# Natural Language Toolkit: Windows-specific path-syntax gaps
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Windows path forms that name a different file than they appear to.

These only matter under Windows semantics, so every case is run with ``os.name``
and ``os.path`` swapped for Windows' -- a Linux CI run then covers the Windows
behaviour, which no single-platform test can. Security research on this class
(``\\?\\`` extended-length, ``\\.\\`` device namespace, ``CONIN$``/``CONOUT$``
console devices, 8.3 short names like ``PROGRA~1``) drove the additions here.

The 8.3 and device checks run on EVERY path component, not just the last: a
short name or a device in a middle segment (``dir/PROGRA~1/x``) traverses
through the alias just as a final one does.
"""

import ntpath
import os
import posixpath

import pytest

from nltk.pathsec import validate_model_resource, validate_tool_path


def _verdict(guard, value, windows=True):
    saved = (os.name, os.path.altsep, os.path.splitdrive)
    if windows:
        os.name = "nt"
        os.path.altsep, os.path.splitdrive = ntpath.altsep, ntpath.splitdrive
    else:
        os.name = "posix"
        os.path.altsep, os.path.splitdrive = posixpath.altsep, posixpath.splitdrive
    try:
        guard(value, context="test")
        return "allowed"
    except (PermissionError, ValueError):
        return "blocked"
    finally:
        os.name, os.path.altsep, os.path.splitdrive = saved


_WINDOWS_HOSTILE = [
    "\\\\?\\C:\\Windows\\x",
    "\\\\?\\UNC\\server\\share\\x",
    "\\\\.\\C:\\x",
    "\\\\.\\PhysicalDrive0",
    "CONIN$",
    "CONOUT$",
    "PROGRA~1",
    "EVILFI~1.EXE",
    "dir/PROGRA~1/x",
    "a/CON/b",
    "x/CONIN$/y",
    "model.ser.gz::$DATA",
    "model.ser.gz:hidden",
    "C:model.mco",
    "\\model",
    "model.mco.",
    "model.mco ",
    "CON",
    "NUL",
    "COM1",
    "LPT1",
    "AUX",
    "PRN",
]


@pytest.mark.parametrize("value", _WINDOWS_HOSTILE)
def test_hostile_windows_forms_are_refused_by_both_guards(value):
    assert _verdict(validate_model_resource, value) == "blocked", value
    assert _verdict(validate_tool_path, value) == "blocked", value


@pytest.mark.parametrize(
    "value",
    [
        "model~backup.mco",
        "file~.txt",
        "CONTEXT.mco",
        "console.gz",
        "edu/stanford/x.ser.gz",
    ],
)
def test_lookalikes_are_still_allowed(value):
    """Over-block control. A '~' without a trailing digit is not an 8.3 name, and
    a name that merely starts like a device (CONTEXT, console) is a real file."""
    assert _verdict(validate_model_resource, value) == "allowed", value


@pytest.mark.parametrize(
    "value", ["CON", "NUL", "CONIN$", "PROGRA~1", "dir/EVILFI~1/x"]
)
def test_these_are_ordinary_filenames_on_posix(value):
    """The whole point of the os.name guard: on POSIX these are legal filenames
    and refusing them would break real usage."""
    assert _verdict(validate_model_resource, value, windows=False) == "allowed", value

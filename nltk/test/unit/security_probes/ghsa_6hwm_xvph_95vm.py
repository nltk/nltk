"""GHSA-6hwm-xvph-95vm [low] -- Uncontrolled search path when invoking the Graphviz 'dot' binary (CWE-426/CWE-427)"""

import os
import shutil
import tempfile

from ._base import FIXED, STATIC, VULNERABLE, probe, write_private


@probe("GHSA-6hwm-xvph-95vm")
def _graphviz_search_path():
    """Plant an executable ./dot in the CWD and resolve the bare name.

    ``find_binary`` must not hand back a binary from the current working
    directory (attacker-writable, untrusted): it either raises ``LookupError``
    naming the CWD, or returns a real absolute system ``dot`` and ignores the
    plant. Returning the planted relative file would be the search-path bypass.
    """
    from nltk.internals import find_binary

    box = tempfile.mkdtemp()
    plant = write_private(
        path=os.path.join(box, "dot"), data="#!/bin/sh\necho PWNED\n", mode=0o700
    )
    old = os.getcwd()
    try:
        os.chdir(box)
        try:
            result = find_binary("dot")
        except LookupError as exc:
            if "current working directory" in str(exc):
                return FIXED, "planted ./dot refused (CWD is not a trusted location)"
            return STATIC, "dot absent; lookup did not reach the CWD plant"
        planted = os.path.realpath(plant)
        if os.path.isabs(result) and os.path.realpath(result) != planted:
            return FIXED, "ignored planted ./dot, used trusted %s" % result
        return VULNERABLE, "find_binary returned the planted CWD file: %r" % result
    finally:
        os.chdir(old)
        shutil.rmtree(box, ignore_errors=True)

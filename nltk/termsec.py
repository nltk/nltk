# Natural Language Toolkit: Terminal-output safety helpers (routing stub)
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

"""Routing stub for terminal-output sanitisation.

This module gives every print site in NLTK a single chokepoint to route
through: :func:`safe_print`. In this stub, ``safe_print`` IS the builtin
``print`` (a pass-through alias), so behaviour is byte-identical and the
call-site conversion can be reviewed as a pure mechanical rename.

The sanitising implementation (escaping ANSI/OSC control sequences, C1
controls, Trojan-Source bidi overrides, invisible smuggling characters and
spreadsheet formula leads; CWE-150 / CVE-2021-42574 / CWE-1236) is developed
separately in pull request #3914 and replaces this file without touching any
call site: for text free of control characters the sanitising ``safe_print``
is output-identical to ``print``, which is exactly the contract this stub
already satisfies.
"""

__all__ = ["safe_print"]

safe_print = print

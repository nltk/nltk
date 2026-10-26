# -*- coding: utf-8 -*-
"""
This module previously provided an interface to Babelfish online
translation service; this service is no longer available; this
module is kept in NLTK source code in order to provide better error
messages for people following the NLTK Book 2.0.
"""
from __future__ import absolute_import, division, print_function, unicode_literals
import six

from nltk.termsec import safe_print


def babelize_shell():
    safe_print("Babelfish online translation service is no longer available.")

# -*- coding: utf-8 -*-
# Natural Language Toolkit: Compatibility
#
# Copyright (C) 2001-2019 NLTK Project
#
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

import os
import sys
from functools import update_wrapper, wraps
import fractions
import unicodedata

PY3 = sys.version_info[0] == 3

# ======= Compatibility for datasets that care about Python versions ========

# The following datasets have a /PY3 subdirectory containing
# a full copy of the data which has been re-encoded or repickled.
DATA_UPDATES = [
    ("chunkers", "maxent_ne_chunker"),
    ("help", "tagsets"),
    ("taggers", "maxent_treebank_pos_tagger"),
    ("tokenizers", "punkt"),
]

_PY3_DATA_UPDATES = [os.path.join(*path_list) for path_list in DATA_UPDATES]


def add_py3_data(path):
    if PY3:
        for item in _PY3_DATA_UPDATES:
            if item in str(path) and "/PY3" not in str(path):
                pos = path.index(item) + len(item)
                if path[pos : pos + 4] == ".zip":
                    pos += 4
                path = path[:pos] + "/PY3" + path[pos:]
                break
    return path


# for use in adding /PY3 to the second (filename) argument
# of the file pointers in data.py
def py3_data(init_func):
    def _decorator(*args, **kwargs):
        args = (args[0], add_py3_data(args[1])) + args[2:]
        return init_func(*args, **kwargs)

    return wraps(init_func)(_decorator)


# ======= Compatibility layer for __str__ and __repr__ ==========
def remove_accents(text):

    if isinstance(text, bytes):
        text = text.decode("ascii")

    category = unicodedata.category  # this gives a small (~10%) speedup
    return "".join(
        c for c in unicodedata.normalize("NFKD", text) if category(c) != "Mn"
    )


# Select the best transliteration method:
try:
    # Older versions of Unidecode are licensed under Artistic License;
    # assume an older version is installed.
    from unidecode import unidecode as transliterate
except ImportError:
    try:
        # text-unidecode implementation is worse than Unidecode
        # implementation so Unidecode is preferred.
        from text_unidecode import unidecode as transliterate
    except ImportError:
        # This transliteration method should be enough
        # for many Western languages.
        transliterate = remove_accents


def python_2_unicode_compatible(klass):
    """
    This decorator defines __unicode__ method and fixes
    __repr__ and __str__ methods under Python 2.

    To support Python 2 and 3 with a single code base,
    define __str__ and __repr__ methods returning unicode
    text and apply this decorator to the class.

    Original __repr__ and __str__ would be available
    as unicode_repr and __unicode__ (under both Python 2
    and Python 3).
    """

    if not issubclass(klass, object):
        raise ValueError("This decorator doesn't work for old-style classes")

    # both __unicode__ and unicode_repr are public because they
    # may be useful in console under Python 2.x

    # if __str__ or __repr__ are not overriden in a subclass,
    # they may be already fixed by this decorator in a parent class
    # and we shouldn't them again

    if not _was_fixed(klass.__str__):
        klass.__unicode__ = klass.__str__
        if not PY3:
            klass.__str__ = _7bit(_transliterated(klass.__unicode__))

    if not _was_fixed(klass.__repr__):
        klass.unicode_repr = klass.__repr__
        if not PY3:
            klass.__repr__ = _7bit(klass.unicode_repr)

    return klass


def unicode_repr(obj):
    """Compatibility alias for ``repr``."""
    return repr(obj)


def _transliterated(method):
    def wrapper(self):
        return transliterate(method(self))

    update_wrapper(wrapper, method, ["__name__", "__doc__"])
    if hasattr(method, "_nltk_compat_7bit"):
        wrapper._nltk_compat_7bit = method._nltk_compat_7bit

    wrapper._nltk_compat_transliterated = True
    return wrapper


def _7bit(method):
    def wrapper(self):
        return method(self).encode("ascii", "backslashreplace")

    update_wrapper(wrapper, method, ["__name__", "__doc__"])

    if hasattr(method, "_nltk_compat_transliterated"):
        wrapper._nltk_compat_transliterated = method._nltk_compat_transliterated

    wrapper._nltk_compat_7bit = True
    return wrapper


def _was_fixed(method):
    return getattr(method, "_nltk_compat_7bit", False) or getattr(
        method, "_nltk_compat_transliterated", False
    )


class Fraction(fractions.Fraction):
    """
    This is a simplified backwards compatible version of fractions.Fraction
    from Python >=3.5. It adds the `_normalize` parameter such that it does
    not normalize the denominator to the Greatest Common Divisor (gcd) when
    the numerator is 0.

    This is most probably only used by the nltk.translate.bleu_score.py where
    numerator and denominator of the different ngram precisions are mutable.
    But the idea of "mutable" fraction might not be applicable to other usages,
    See http://stackoverflow.com/questions/34561265

    This objects should be deprecated once NLTK stops supporting Python < 3.5
    See https://github.com/nltk/nltk/issues/1330
    """

    def __new__(cls, numerator=0, denominator=None, _normalize=True):
        cls = super(Fraction, cls).__new__(cls, numerator, denominator)
        # To emulate fraction.Fraction.from_float across Python >=2.7,
        # check that numerator is an integer and denominator is not None.
        if not _normalize and type(numerator) == int and denominator:
            cls._numerator = numerator
            cls._denominator = denominator
        return cls

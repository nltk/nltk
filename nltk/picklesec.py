# -*- coding: utf-8 -*-
# Natural Language Toolkit: Restricted unpickling
#
# Copyright (C) 2001-2026 NLTK Project
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
"""
Restricted unpickling for the 3.4 maintenance line, named as in the 3.10
line's ``nltk.picklesec``. NLTK's pickled resources (tokenizer and tagger
models, corpus pickle views, cached charts) reference NLTK classes and a few
containers; :class:`RestrictedUnpickler` refuses every other global before
any object is built, so a planted pickle cannot name ``os.system`` or any
other callable (CWE-502). The 3.10 module adds opcode screening and
allowlists per caller; this line keeps the class-level refusal only.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import io
import pickle

from six import PY2

__all__ = ["RestrictedUnpickler", "restricted_pickle_load", "restricted_pickle_loads"]

#: Modules whose classes a pickled NLTK resource may legitimately reference.
_ALLOWED_MODULE_PREFIXES = ("nltk.",)
_ALLOWED = {
    "builtins": {"set", "frozenset", "list", "dict", "tuple", "bytes", "str",
                 "int", "float", "bool", "complex", "object", "slice", "range",
                 "bytearray"},
    "__builtin__": {"set", "frozenset", "list", "dict", "tuple", "str", "unicode",
                    "int", "long", "float", "bool", "complex", "object", "slice",
                    "xrange", "bytearray"},
    "collections": {"OrderedDict", "defaultdict", "Counter", "deque"},
    "copy_reg": {"_reconstructor"},
    "copyreg": {"_reconstructor"},
    "_codecs": {"encode"},
    "numpy": {"ndarray", "dtype", "float64", "float32", "int64", "int32", "bool_"},
    "numpy.core.multiarray": {"_reconstruct", "scalar"},
    "numpy._core.multiarray": {"_reconstruct", "scalar"},
    "scipy.sparse.csr": {"csr_matrix"},
    "scipy.sparse._csr": {"csr_matrix"},
    "sklearn.svm.classes": {"SVC"},
    "sklearn.svm._classes": {"SVC"},
}

# The pure-Python unpickler on both interpreters: the C one on 2.7 does not
# route every global lookup through find_class.
_Unpickler = pickle.Unpickler if PY2 else pickle._Unpickler


class RestrictedUnpickler(_Unpickler):
    """An unpickler that refuses every global outside the allowlist.

    ``find_class`` is the single point every pickle opcode that names a
    global goes through, so refusing there stops ``os.system`` or any other
    callable from ever being looked up (CWE-502).
    """

    def find_class(self, module, name):
        if module.startswith(_ALLOWED_MODULE_PREFIXES) and not name.startswith("_"):
            return _Unpickler.find_class(self, module, name)
        allowed = _ALLOWED.get(module)
        if allowed is not None and name in allowed:
            return _Unpickler.find_class(self, module, name)
        raise pickle.UnpicklingError(
            "refusing to unpickle %s.%s: not an NLTK resource class" % (module, name)
        )


def restricted_pickle_load(fileobj):
    """Load a pickle from *fileobj* with :class:`RestrictedUnpickler`."""
    return RestrictedUnpickler(fileobj).load()


def restricted_pickle_loads(data):
    """Load a pickle from the bytes *data* with :class:`RestrictedUnpickler`."""
    return RestrictedUnpickler(io.BytesIO(data)).load()

# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys

def should_raise(eclass, method, *args, **kw):
     try:
         method(*args, **kw)
     except Exception:
         e = sys.exc_info()[1]
         if not isinstance(e, eclass):
             raise
         return True
     raise Exception("Expected exception %s not raised" % str(eclass))


def float_equal(a, b, eps=1e-8):
    return abs(a-b) < eps


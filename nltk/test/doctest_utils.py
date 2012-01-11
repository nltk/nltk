# -*- coding: utf-8 -*-
from __future__ import absolute_import
import sys


def float_equal(a, b, eps=1e-8):
    return abs(a-b) < eps


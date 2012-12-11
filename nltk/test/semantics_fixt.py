# -*- coding: utf-8 -*-
from __future__ import absolute_import

# reset the variables counter before running tests
def setup_module(module):
    from nltk.sem import logic
    logic._counter._value = 0

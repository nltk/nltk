#!/usr/bin/env python

"""
sort program in windows sometimes behaves strangely
so we write a small sorting program to be used in testing
"""

import sys

li = []
for line in sys.stdin:
    li.append(line)

li.sort()
for e in li:
    print e,

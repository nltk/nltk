#!/usr/bin/env python

import sys

li = []
for line in sys.stdin:
	li.append(line)

li.sort()
for e in li:
	print e,

#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
run doctests
"""

from __future__ import print_function
import sys, subprocess, os

for root, dirs, filenames in os.walk('.'):
    for filename in filenames:
        if filename.endswith('.py'):
            path = os.path.join(root, filename)
            for pyver in ["python2.6", "python2.7", "python3.2"]:
                print(pyver, filename, file=sys.stderr)
                subprocess.call([pyver,  "-m", "doctest", path])

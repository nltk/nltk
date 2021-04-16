#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
run doctests
"""

import sys
import subprocess
import os

for root, dirs, filenames in os.walk('.'):
    for filename in filenames:
        if filename.endswith('.py'):
            path = os.path.join(root, filename)
            for pyver in ["python3.5", "python3.6", "python3.7"]:
                print(pyver, filename, file=sys.stderr)
                subprocess.call([pyver, "-m", "doctest", path])

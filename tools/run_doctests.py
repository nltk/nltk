#!/usr/bin/python3
"""
run doctests
"""

import os
import subprocess
import sys

for root, dirs, filenames in os.walk("."):
    for filename in filenames:
        if filename.endswith(".py"):
            path = os.path.join(root, filename)
            for pyver in ["python3.5", "python3.6", "python3.7"]:
                print(pyver, filename, file=sys.stderr)
                subprocess.call([pyver, "-m", "doctest", path])

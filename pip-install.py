#! /usr/bin/env python
#
# Read pip-req.txt file, which is a pip requirements file, and then install the
# modules one by one using pip. The installation process stops if there's an
# installation error before reaching the bottom of the list.
#

import sys
import os
import subprocess

REQ_FILE = 'pip-req.txt'
REQ_PATH = os.path.join(os.path.dirname(sys.argv[0]), REQ_FILE)

for line in open(REQ_PATH):
    cmd = "pip install %s" % line.strip()
    ret = subprocess.call(cmd.split())
    if ret != 0:
        break


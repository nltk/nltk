#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
run the doctests in nltk.tag.brill
"""


from __future__ import print_function
import glob, sys, subprocess, os.path
from os.path import abspath

currdir = os.getcwd()
if not currdir.endswith("nltk/tag/brill"):
    raise RuntimeError("run me in /<PATH/TO/NLTK>/nltk/tag/brill/")
sys.path.insert(0, "../../..")

#a list of all the python files in this dir and two levels of subdirs
files = [pyfile for patt in ("*.py", "*/*.py", "*/*/*.py") for pyfile in glob.glob(patt)
         if not abspath(__file__) == abspath(pyfile)]

for pyver in ["python2.6", "python2.7", "python3.2", "python3.3"]:
    for (i, f) in enumerate(files, 1):
        print(pyver, i, f, file=sys.stderr)
        subprocess.call([pyver,  "-m", "doctest", f])



#!/usr/bin/env python

"""
Build the corpus package index.  Usage:

  build_pkg_index.py <path-to-packages> <base-url> <output-file>
"""

xml_header = """<?xml version="1.0"?>
<?xml-stylesheet href="index.xsl" type="text/xsl"?>
"""

import sys
from nltk.downloader import build_index
from nltk.etree import ElementTree

if len(sys.argv) != 4:
    print "Usage: "
    print "build_pkg_index.py <path-to-packages> <base-url> <output-file>"
    sys.exit(-1)

ROOT, BASE_URL, OUT = sys.argv[1:]

index = build_index(ROOT, BASE_URL)
s = ElementTree.tostring(index)
out = open(OUT, 'w')
out.write(xml_header)
out.write(s)
out.close()


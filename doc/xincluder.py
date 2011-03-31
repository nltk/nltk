#!/usr/bin/env python
#
# Natural Language Toolkit: Process the XIncludes of an XML document
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import sys
import re

EXT = "-flat"              # output filename extension
XI1 = r'<xi:include href="(.*?)".*/>'
DOC = r'(?s)<!DOCTYPE .*?>'
NAMESPACE = r' xmlns:xi="http://www.w3.org/2001/XInclude"'

for filename in sys.argv[1:]:
    basename, suffix = filename.split('.')
    output_filename = basename + EXT + "." + suffix
    output = open(output_filename, "w")
    for line in open(filename):
        m = re.search(XI1, line)
        if m:
            contents = open(m.group(1)).read()
            if re.search(DOC, contents):
                contents = re.split(DOC, contents)[1]
            output.write(contents)
        else:
            if NAMESPACE in line:
                line = re.sub(NAMESPACE, '', line)
            output.write(line)
    output.close()



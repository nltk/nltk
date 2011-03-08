#!/usr/bin/env python
#
## Natural Language Toolkit: update the checksums in a Portfile
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
#
# $Id:$

import re
import sys

CKSUM = re.compile(r'^checksums\s.*\n\s.*\n\s.*\n', re.MULTILINE)
VER_ARG = re.compile(r'^\d+\.\d+([ab]\d+)?$')
VERSION = re.compile(r'^version\s.*$', re.MULTILINE)

if __name__ == '__main__':

    if len(sys.argv) != 4:
        exit("Usage: %s <Portfile> <checksum file> <version>" % sys.argv[0])

    portfile = open(sys.argv[1])
    port = portfile.read()
    portfile.close()

    cksum = open(sys.argv[2]).read()
    if not VER_ARG.match(sys.argv[3]):
        raise ValueError, "Incorrect format for version"
    version = "version             " + sys.argv[3]

    if not CKSUM.search(port):
        raise ValueError, "Checksum pattern was not matched"

    port = CKSUM.sub(cksum, port)
    port = VERSION.sub(version, port)
    open(sys.argv[1], "w").write(port)


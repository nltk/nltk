#!/usr/bin/env python
# Pre-process rst source

from optparse import OptionParser
import re

_SCALE_RE = r'(:scale:\s+)(\d+):(\d+):(\d+)'

def process(file, format):
    contents = open(file).read()
    if format == "html":
        contents = re.sub(_SCALE_RE, r'\1\2', contents)
    elif format == "latex":
        contents = re.sub(_SCALE_RE, r'\1\3', contents)
    elif format == "xml":
        contents = re.sub(_SCALE_RE, r'\1\4', contents)
    open(file + "2", 'w').write(contents)

parser = OptionParser()
parser.add_option("-f", "--format", dest="format",
                      help="output format (html, latex, xml)", metavar="FMT")

o, a = parser.parse_args()

if o.format and o.format in ["html", "latex", "xml"] and a and len(a) == 1:
    process(a[0], o.format)

else:
    exit("Must specify a format (html, latex, xml) and a filename")

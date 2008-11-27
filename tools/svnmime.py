#!/usr/bin/env python

import os
import sys

types_map = {
    'ai': 'application/postscript',
    'css': 'text/css',
    'exe': 'application/octet-stream',
    'eps': 'application/postscript',
    'gif': 'image/gif',
    'htm': 'text/html',
    'html': 'text/html',
    'jpeg': 'image/jpeg',
    'jpg': 'image/jpeg',
    'js': 'application/x-javascript',
    'pbm': 'image/x-portable-bitmap',
    'pdf': 'application/pdf',
    'pgm': 'image/x-portable-graymap',
    'pnm': 'image/x-portable-anymap',
    'png': 'image/png',
    'ppm': 'image/x-portable-pixmap',
    'py': 'text/x-python',
    'pyc': 'application/x-python-code',
    'ps': 'application/postscript',
    'rst': 'text/plain',
    'tex': 'application/x-tex',
    'txt': 'text/plain',
    'zip': 'application/zip',
    }

def usage():
    exit("Usage: svnmime files")

for file in sys.argv[1:]:
    if "." in file:
        extension = file.rsplit('.', 1)[1]
        if extension in types_map:
            os.system("svn propset svn:mime-type %s %s" % (types_map[extension], file))
        else:
            print "Unrecognized extension", extension

#!/usr/bin/env python

# NB, this wouldn't be needed if everyone had .subversion/config
# configured to automatically set mime types
# http://code.google.com/p/support/wiki/FAQ


import os
import sys

types_map = {
    "ai": "application/postscript",
    "coverage": "text/plain",
    "css": "text/css",
    "eps": "application/postscript",
    "exe": "application/octet-stream",
    "errs": "text/plain",
    "gif": "image/gif",
    "htm": "text/html",
    "html": "text/html",
    "jpeg": "image/jpeg",
    "jpg": "image/jpeg",
    "js": "application/x-javascript",
    "pbm": "image/x-portable-bitmap",
    "pdf": "application/pdf",
    "pgm": "image/x-portable-graymap",
    "pnm": "image/x-portable-anymap",
    "png": "image/png",
    "ppm": "image/x-portable-pixmap",
    "py": "text/x-python",
    "ps": "application/postscript",
    "rst": "text/plain",
    "tex": "application/x-tex",
    "txt": "text/plain",
    "xml": "text/xml",
    "xsl": "text/plain",
    "zip": "application/zip",
}


def usage():
    exit("Usage: svnmime files")


for file in sys.argv[1:]:
    if "." in file:
        extension = file.rsplit(".", 1)[1]
        if extension in types_map:
            os.system(f"svn propset svn:mime-type {types_map[extension]} {file}")
        else:
            print("Unrecognized extension", extension)

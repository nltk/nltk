#!/usr/bin/env python
#
# Natural Language Toolkit: substitute a pattern with
#                           a replacement in every file
# Copyright (C) 2001-2020 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

# NB Should work on all platforms,
# http://www.python.org/doc/2.5.2/lib/os-file-dir.html

import os
import stat
import sys


def update(file, pattern, replacement):

    try:
        # make sure we can write the file
        old_perm = os.stat(file)[0]
        if not os.access(file, os.W_OK):
            os.chmod(file, old_perm | stat.S_IWRITE)

        # write the file
        s = open(file, 'rb').read().decode('utf-8')
        t = s.replace(pattern, replacement)
        out = open(file, 'wb')
        out.write(t.encode('utf-8'))
        out.close()

        # restore permissions
        os.chmod(file, old_perm)

        return s != t

    except Exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        print('Unable to check {0:s} {1:s}'.format(file, str(exc_type)))
        return 0


if __name__ == '__main__':

    if len(sys.argv) != 3:
        exit("Usage: %s <pattern> <replacement>" % sys.argv[0])

    pattern = sys.argv[1]
    replacement = sys.argv[2]
    count = 0

    for root, dirs, files in os.walk('.'):
        if not ('/.git' in root or '/.tox' in root):
            for file in files:
                path = os.path.join(root, file)
                if update(path, pattern, replacement):
                    print("Updated:", path)
                    count += 1

    print("Updated {} files".format(count))

# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

import os, sys

def set_basedir(path):
    """
    Set the path to the directory where NLTK looks for corpora.
    
    @type path: C{string}
    @param path: The path to the directory where NLTK should look for corpora.
    """
    global _BASEDIR
    _BASEDIR = path

def get_basedir():
    """
    @return: The path of the directory where NLTK looks for corpora.
    @rtype: C{string}
    """
    return _BASEDIR

# Find a default base directory.
if os.environ.has_key('NLTK_LITE_CORPORA'):
    set_basedir(os.environ['NLTK_LITE_CORPORA'])
elif sys.platform.startswith('win'):
    if os.path.isdir(os.path.join(sys.prefix, 'nltk_lite')):
        set_basedir(os.path.join(sys.prefix, 'nltk_lite'))
    elif os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk_lite')):
        set_basedir(os.path.join(sys.prefix, 'lib', 'nltk_lite'))
    else:
        set_basedir(os.path.join(sys.prefix, 'nltk_lite'))
elif os.path.isdir('/usr/lib/nltk_lite'):
    set_basedir('/usr/lib/nltk_lite')
elif os.path.isdir('/usr/local/lib/nltk_lite'):
    set_basedir('/usr/local/lib/nltk_lite')
elif os.path.isdir('/usr/share/nltk_lite'):
    set_basedir('/usr/share/nltk_lite')
else:
    set_basedir('/usr/lib/nltk_lite')

# Access to individual corpus items

# extract the nth item from iterator i
from itertools import islice
def extract(n, i):
    return list(islice(i, n, n+1))[0]

# Natural Language Toolkit: Corpus Readers
#
# Copyright (C) 2001-2007 University of Pennsylvania
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
if os.environ.has_key('NLTK_CORPORA'):
    set_basedir(os.environ['NLTK_CORPORA'])
elif sys.platform.startswith('win'):
    if os.path.isdir('C:\\corpora'):
        set_basedir('C:\\corpora')
    elif os.path.isdir(os.path.join(sys.prefix, 'nltk', 'corpora')):
        set_basedir(os.path.join(sys.prefix, 'nltk', 'corpora'))
    elif os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk', 'corpora')):
        set_basedir(os.path.join(sys.prefix, 'lib', 'nltk', 'corpora'))
    elif os.path.isdir(os.path.join(sys.prefix, 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'nltk'))
    elif os.path.isdir(os.path.join(sys.prefix, 'lib', 'nltk')):
        set_basedir(os.path.join(sys.prefix, 'lib', 'nltk'))
    else:
        set_basedir('C:\\corpora')
elif os.path.isdir('/usr/share/nltk/corpora'):
   set_basedir('/usr/share/nltk/corpora')
elif os.path.isdir('/usr/local/share/nltk/corpora'):
   set_basedir('/usr/local/share/nltk/corpora')
elif os.path.isdir('/usr/share/nltk'):
   set_basedir('/usr/share/nltk')
elif os.path.isdir('/usr/local/share/nltk'):
   set_basedir('/usr/local/share/nltk')
else:
    set_basedir('/usr/share/nltk/corpora')

# Access to individual corpus items

# extract the nth item from iterator i
from itertools import islice
def extract(n, i):
    return list(islice(i, n, n+1))[0]

import abc, brown, chat80, cmudict, conll2000, conll2002, genesis, gutenberg
import ieer, inaugural, indian, names, ppattach, senseval, shakespeare
import sinica_treebank, state_union, stopwords, timit, toolbox, treebank
import web, webtext, words, ycoe

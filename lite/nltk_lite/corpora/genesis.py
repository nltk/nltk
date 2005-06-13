# Natural Language Toolkit: Genesis Corpus Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
import os

items = [
    'english-kjv',
    'english-web',
    'french',
    'german',
    'swedish',
    'finnish']

item_name = {
    'english-kjv': 'Genesis, King James version (Project Gutenberg)',
    'english-web': 'Genesis, World English Bible (Project Gutenberg)',
    'french': 'Genesis, Louis Segond 1910',
    'german': 'Genesis, Luther Translation',
    'swedish': 'Genesis, Gamla och Nya Testamentet, 1917 (Project Runeberg)',
    'finnish': 'Genesis, Suomen evankelis-luterilaisen kirkon kirkolliskokouksen vuonna 1992 käyttöön ottama suomennos'
}

def raw(files = 'english-kjv'):
    """
    Read text from the Genesis Corpus.

    This corpus has been prepared from several web sources; formatting,
    markup and verse numbers have been stripped.

    english-kjv - Genesis, King James version (Project Gutenberg)
    english-web - Genesis, World English Bible (Project Gutenberg)
    french - Genesis, Louis Segond 1910
    german - Genesis, Luther Translation
    swedish - Genesis, Gamla och Nya Testamentet, 1917 (Project Runeberg)
    finnish - Genesis, Suomen evankelis-luterilaisen kirkon kirkolliskokouksen vuonna 1992 käyttöön ottama suomennos

    @param files: One or more treebank files to be processed
    @type files: L{string} or L{tuple(string)}
    @param basedir: Base directory of the files
    @type basedir: L{string}
    @rtype: iterator over L{tree}
    """       

    # Just one file to process?  If so convert to a tuple so we can iterate
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "genesis", file+".txt")
        s = open(path).read()
        for t in tokenize.whitespace(s):
            yield t

def demo():

    i=0
    for word in raw():
        print word,
        i+=1
        if i>26: break
    print

    i=0
    for word in raw('finnish'):
        print word,
        i+=1
        if i>26: break
    print

if __name__ == '__main__':
    demo()


# Natural Language Toolkit: IEER Corpus Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for the Information Extraction and Entity Recognition Corpus.

NIST 1999 Information Extraction: Entity Recognition Evaluation
http://www.itl.nist.gov/iad/894.01/tests/ie-er/er_99/er_99.htm

This corpus contains the NEWSWIRE development test data for the
NIST 1999 IE-ER Evaluation.  The files were taken from the
subdirectory: /ie_er_99/english/devtest/newswire/*.ref.nwt
and filenames were shortened.

The corpus contains the following files: APW_19980314, APW_19980424,
APW_19980429, NYT_19980315, NYT_19980403, and NYT_19980407.
"""

from nltk_lite.corpora import get_basedir, extract
from nltk_lite.parse.tree import ieer_chunk
import os

items = ['APW_19980314', 'APW_19980424', 'APW_19980429',
         'NYT_19980315', 'NYT_19980403', 'NYT_19980407']

item_name = {
    'APW_19980314': 'Associated Press Weekly, 14 March 1998',
    'APW_19980424': 'Associated Press Weekly, 24 April 1998',
    'APW_19980429': 'Associated Press Weekly, 29 April 1998',
    'NYT_19980315': 'New York Times, 15 March 1998',
    'NYT_19980403': 'New York Times, 3 April 1998',
    'NYT_19980407': 'New York Times, 7 April 1998',
    }

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "ieer", file)
        for doc in open(path).read().split('</DOC>'):
            doc = doc.split('<DOC>')
            if len(doc) == 2:
                yield "<DOC>" + doc[1] + "</DOC>\n"

def dictionary(files = items):
    for doc in raw(files):
        yield ieer_chunk(doc)

def demo():
    from nltk_lite.corpora import ieer
    from itertools import islice
    from pprint import pprint

#    pprint(extract(75, ieer.raw()))
    pprint(extract(75, ieer.dictionary()))

if __name__ == '__main__':
    demo()


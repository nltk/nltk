# Natural Language Toolkit: Presidential State of the Union Addres Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
C-Span Inaugural Address Corpus

US presidential inaugural addresses 1789-2005
"""       

from util import *
from nltk import tokenize
import os, re

#: A list of all documents in this corpus.
documents = {
    '1789-Washington': 'Washington\'s 1789 Inaugural Address',
    '1793-Washington': 'Washington\'s 1793 Inaugural Address',
    '1797-Adams': 'Adams\'s 1797 Inaugural Address',
    '1801-Jefferson': 'Jefferson\'s 1801 Inaugural Address',
    '1805-Jefferson': 'Jefferson\'s 1805 Inaugural Address',
    '1809-Madison': 'Madison\'s 1809 Inaugural Address',
    '1813-Madison': 'Madison\'s 1813 Inaugural Address',
    '1817-Monroe': 'Monroe\'s 1817 Inaugural Address',
    '1821-Monroe': 'Monroe\'s 1821 Inaugural Address',
    '1825-Adams': 'Adams\'s 1825 Inaugural Address',
    '1829-Jackson': 'Jackson\'s 1829 Inaugural Address',
    '1833-Jackson': 'Jackson\'s 1833 Inaugural Address',
    '1837-VanBuren': 'VanBuren\'s 1837 Inaugural Address',
    '1841-Harrison': 'Harrison\'s 1841 Inaugural Address',
    '1845-Polk': 'Polk\'s 1845 Inaugural Address',
    '1849-Taylor': 'Taylor\'s 1849 Inaugural Address',
    '1853-Pierce': 'Pierce\'s 1853 Inaugural Address',
    '1857-Buchanan': 'Buchanan\'s 1857 Inaugural Address',
    '1861-Lincoln': 'Lincoln\'s 1861 Inaugural Address',
    '1865-Lincoln': 'Lincoln\'s 1865 Inaugural Address',
    '1869-Grant': 'Grant\'s 1869 Inaugural Address',
    '1873-Grant': 'Grant\'s 1873 Inaugural Address',
    '1877-Hayes': 'Hayes\'s 1877 Inaugural Address',
    '1881-Garfield': 'Garfield\'s 1881 Inaugural Address',
    '1885-Cleveland': 'Cleveland\'s 1885 Inaugural Address',
    '1889-Harrison': 'Harrison\'s 1889 Inaugural Address',
    '1893-Cleveland': 'Cleveland\'s 1893 Inaugural Address',
    '1897-McKinley': 'McKinley\'s 1897 Inaugural Address',
    '1901-McKinley': 'McKinley\'s 1901 Inaugural Address',
    '1905-Roosevelt': 'Roosevelt\'s 1905 Inaugural Address',
    '1909-Taft': 'Taft\'s 1909 Inaugural Address',
    '1913-Wilson': 'Wilson\'s 1913 Inaugural Address',
    '1917-Wilson': 'Wilson\'s 1917 Inaugural Address',
    '1921-Harding': 'Harding\'s 1921 Inaugural Address',
    '1925-Coolidge': 'Coolidge\'s 1925 Inaugural Address',
    '1929-Hoover': 'Hoover\'s 1929 Inaugural Address',
    '1933-Roosevelt': 'Roosevelt\'s 1933 Inaugural Address',
    '1937-Roosevelt': 'Roosevelt\'s 1937 Inaugural Address',
    '1941-Roosevelt': 'Roosevelt\'s 1941 Inaugural Address',
    '1945-Roosevelt': 'Roosevelt\'s 1945 Inaugural Address',
    '1949-Truman': 'Truman\'s 1949 Inaugural Address',
    '1953-Eisenhower': 'Eisenhower\'s 1953 Inaugural Address',
    '1957-Eisenhower': 'Eisenhower\'s 1957 Inaugural Address',
    '1961-Kennedy': 'Kennedy\'s 1961 Inaugural Address',
    '1965-Johnson': 'Johnson\'s 1965 Inaugural Address',
    '1969-Nixon': 'Nixon\'s 1969 Inaugural Address',
    '1973-Nixon': 'Nixon\'s 1973 Inaugural Address',
    '1977-Carter': 'Carter\'s 1977 Inaugural Address',
    '1981-Reagan': 'Reagan\'s 1981 Inaugural Address',
    '1985-Reagan': 'Reagan\'s 1985 Inaugural Address',
    '1989-Bush': 'Bush\'s 1989 Inaugural Address',
    '1993-Clinton': 'Clinton\'s 1993 Inaugural Address',
    '1997-Clinton': 'Clinton\'s 1997 Inaugural Address',
    '2001-Bush': 'Bush\'s 2001 Inaugural Address',
    '2005-Bush': 'Bush\'s 2005 Inaugural Address'
}

#: A list of all documents in this corpus.
items = sorted(documents)

def read_document(item=items, format='tokenized'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'tokenized'}: a list of words and punctuation symbols.
    """
    if isinstance(item, list):
        return concat([read(doc, format) for doc in item])
    filename = find_corpus_file('inaugural', item, '.txt')
    if format == 'raw':
        return open(filename).read()
    elif format == 'tokenized':
        return StreamBackedCorpusView(filename, read_wordpunct_block)
    else:
        raise ValueError('Bad format: expected raw or tokenized')

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item=items):
    """@return: the given document as a single string."""
    return read_document(item, 'raw')

def tokenized(item=items):
    """@return: the given document as a list of words and punctuation
    symbols.
    @rtype: C{list} of C{str}"""
    return read_document(item, 'tokenized')

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import inaugural

    for speech in inaugural.items:
        year = speech[:4]
        freq = list(read(speech)).count('men')
        print year, freq

if __name__ == '__main__':
    demo()

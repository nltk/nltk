# Natural Language Toolkit: Presidential State of the Union Addres Corpus Reader
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
C-Span Inaugural Address Corpus

US presidential inaugural addresses 1789-2005
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
import os, re

items = [
    '1789-Washington',
    '1793-Washington',
    '1797-Adams',
    '1801-Jefferson',
    '1805-Jefferson',
    '1809-Madison',
    '1813-Madison',
    '1817-Monroe',
    '1821-Monroe',
    '1825-Adams',
    '1829-Jackson',
    '1833-Jackson',
    '1837-VanBuren',
    '1841-Harrison',
    '1845-Polk',
    '1849-Taylor',
    '1853-Pierce',
    '1857-Buchanan',
    '1861-Lincoln',
    '1865-Lincoln',
    '1869-Grant',
    '1873-Grant',
    '1877-Hayes',
    '1881-Garfield',
    '1885-Cleveland',
    '1889-Harrison',
    '1893-Cleveland',
    '1897-McKinley',
    '1901-McKinley',
    '1905-Roosevelt',
    '1909-Taft',
    '1913-Wilson',
    '1917-Wilson',
    '1921-Harding',
    '1925-Coolidge',
    '1929-Hoover',
    '1933-Roosevelt',
    '1937-Roosevelt',
    '1941-Roosevelt',
    '1945-Roosevelt',
    '1949-Truman',
    '1953-Eisenhower',
    '1957-Eisenhower',
    '1961-Kennedy',
    '1965-Johnson',
    '1969-Nixon',
    '1973-Nixon',
    '1977-Carter',
    '1981-Reagan',
    '1985-Reagan',
    '1989-Bush',
    '1993-Clinton',
    '1997-Clinton',
    '2001-Bush',
    '2005-Bush'
]

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "inaugural", file + ".txt")
        f = open(path)
        preamble = True
        text = f.read()
        for t in tokenize.wordpunct(text):
            yield t

def demo():
    from nltk_lite.corpora import inaugural

    for speech in inaugural.items:
        year = speech[:4]
        freq = list(inaugural.raw(speech)).count('men')
        print year, freq

if __name__ == '__main__':
    demo()

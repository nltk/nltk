# Natural Language Toolkit: Presidential State of the Union Addres Corpus Reader
#
# Copyright (C) 2001-2005 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
C-Span State of the Union Address Corpus

Annual US presidential addresses 1945-2005

http://www.c-span.org/executive/stateoftheunion.asp
"""       

from nltk_lite.corpora import get_basedir
from nltk_lite import tokenize
import os, re

items = [
    '1945-Truman',
    '1946-Truman',
    '1947-Truman',
    '1948-Truman',
    '1949-Truman',
    '1950-Truman',
    '1951-Truman',
    '1953-Eisenhower',
    '1954-Eisenhower',
    '1955-Eisenhower',
    '1956-Eisenhower',
    '1957-Eisenhower',
    '1958-Eisenhower',
    '1959-Eisenhower',
    '1960-Eisenhower',
    '1961-Kennedy',
    '1962-Kennedy',
    '1963-Johnson',
    '1963-Kennedy',
    '1964-Johnson',
    '1965-Johnson-1',
    '1965-Johnson-2',
    '1966-Johnson',
    '1967-Johnson',
    '1968-Johnson',
    '1969-Johnson',
    '1970-Nixon',
    '1971-Nixon',
    '1972-Nixon',
    '1973-Nixon',
    '1974-Nixon',
    '1975-Ford',
    '1976-Ford',
    '1977-Ford',
    '1978-Carter',
    '1979-Carter',
    '1980-Carter',
    '1981-Reagan',
    '1982-Reagan',
    '1983-Reagan',
    '1984-Reagan',
    '1985-Reagan',
    '1986-Reagan',
    '1987-Reagan',
    '1988-Reagan',
    '1989-Bush',
    '1990-Bush',
    '1991-Bush-1',
    '1991-Bush-2',
    '1992-Bush',
    '1993-Clinton',
    '1994-Clinton',
    '1995-Clinton',
    '1996-Clinton',
    '1997-Clinton',
    '1998-Clinton',
    '1999-Clinton',
    '2000-Clinton',
    '2001-Bush-1',
    '2001-Bush-2',
    '2002-Bush',
    '2003-Bush',
    '2004-Bush',
    '2005-Bush'
]

def raw(files = items):
    if type(files) is str: files = (files,)

    for file in files:
        path = os.path.join(get_basedir(), "state_union", file + ".txt")
        f = open(path)
        preamble = True
        text = f.read()
        for t in tokenize.wordpunct(text):
            yield t

def demo():
    from nltk_lite.corpora import state_union

    for speech in state_union.items:
        year = speech[:4]
        freq = list(state_union.raw(speech)).count('men')
        print year, freq

if __name__ == '__main__':
    demo()

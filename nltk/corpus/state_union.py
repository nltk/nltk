# Natural Language Toolkit: Presidential State of the Union Addres Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
C-Span State of the Union Address Corpus

Annual US presidential addresses 1945-2005

http://www.c-span.org/executive/stateoftheunion.asp
"""       

from util import *
from nltk import tokenize
import os, re

documents = [
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
    '2001-GWBush-1',
    '2001-GWBush-2',
    '2002-GWBush',
    '2003-GWBush',
    '2004-GWBush',
    '2005-GWBush'
]

def read_document(name):
    filename = find_corpus_file('state_union', name, '.txt')
    return StreamBackedCorpusView(filename, tokenize_wordpunct)
read = read_document

def demo():
    from nltk.corpus import state_union

    for speech in state_union.documents:
        year = speech[:4]
        freq = list(state_union.read(speech)).count('men')
        print year, freq

if __name__ == '__main__':
    demo()

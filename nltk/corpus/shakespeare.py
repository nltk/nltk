# Natural Language Toolkit: Shakespeare XML Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read from the Shakespeare XML Corpus Sample

http://www.andrew.cmu.edu/user/akj/shakespeare/

Marked up in XML by Jon Bosak, CSS stylesheet by Ajay Juneja.
"""       

import os
from util import *
from nltk.etree import ElementTree

#: A dictionary whose keys are the names of documents in this corpus;
#: and whose values are descriptions of those documents' contents.
documents = {'a_and_c':  'Antony and Cleopatra',
             'dream':    'A Midsummer Night\'s Dream',
             'hamlet':   'Hamlet',
             'j_caesar': 'Julius Caesar',
             'macbeth':  'Macbeth',
             'merchant': 'The Merchant of Venice',
             'othello':  'Othello',
             'r_and_j':  'Romeo and Juliet',
}

#: A list of all documents in this corpus.
items = list(documents)

def read_document(item, format='xml'):
    """
    Read the given document from the corpus, and return its contents.
    C{format} determines the format that the result will be returned
    in:
      - C{'raw'}: a single C{string}
      - C{'xml'}: an xml ElementTree.
    """
    filename = find_corpus_file('shakespeare', item, '.xml')
    if format == 'xml':
        return ElementTree.parse(filename).getroot()
    elif format == 'raw':
        return open(filename).read()
    else:
        raise ValueError('expected format to be xml or raw')
read = read_document

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

def raw(item):
    """@Return the given document as a single string."""
    return read_document(item, 'raw')

def xml(item):
    """@Return the given document as an xml ElementTree."""
    return read_document(item, 'xml')

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import shakespeare
    from pprint import pprint
    import re

    play = shakespeare.read('dream', 'xml')
    
    print "Access the subelements"
    print play.getchildren()
    print
    
    print "Access the text content of the first subelement"
    print play[0].text
    print
    
    print "Persona"
    personae = [persona.text for persona in play.findall('PERSONAE/PERSONA')]
    print personae
    print
    
    print "Are any speakers not identified as personae?"
    names = set(re.match(r'[A-Z]*', persona).group() for persona in personae)
    speakers = set(speaker.text for speaker in play.findall('*/*/*/SPEAKER'))
    print speakers.difference(names)
    print

    print "who responds to whom?"
    responds_to = {}
    for scene in play.findall('ACT/SCENE'):
        prev = None
        for speaker in scene.findall('SPEECH/SPEAKER'):
            name = speaker.text
            if prev:
                if prev not in responds_to:
                    responds_to[prev] = set()
                responds_to[prev].add(name)
            prev = name
    pprint(responds_to)
    print

if __name__ == '__main__':
    demo()


# Natural Language Toolkit: XML Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@csse.unimelb.edu.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Corpus reader for corpora whose documents are xml files.

(note -- not named 'xml' to avoid conflicting w/ standard xml package)
"""

from api import CorpusReader
from util import *
from nltk.etree import ElementTree

class XMLCorpusReader(CorpusReader):
    """
    Corpus reader for corpora whose documents are xml files.
    """
    def __init__(self, root, items, extension='.xml'):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension

    def xml(self, items=None):
        return concat([ElementTree.parse(filename).getroot()
                       for filename in self._item_filenames(items)])

    def raw(self, items=None):
        return concat([open(filename).read()
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import shakespeare
    from pprint import pprint
    import re

    plays = shakespeare.xml()
    print 'Number of plays:', len(plays)

    play = shakespeare.xml('dream')
    
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

# Natural Language Toolkit: Senseval 2 Corpus Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
#         Steven Bird <sb@csse.unimelb.edu.au> (modifications)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

"""
Read from the Senseval 2 Corpus.

SENSEVAL [http://www.senseval.org/]
Evaluation exercises for Word Sense Disambiguation.
Organized by ACL-SIGLEX [http://www.siglex.org/]

Prepared by Ted Pedersen <tpederse@umn.edu>, University of Minnesota,
http://www.d.umn.edu/~tpederse/data.html
Distributed with permission.

The NLTK version of the Senseval 2 files uses well-formed XML.
Each instance of the ambiguous words "hard", "interest", "line", and "serve"
is tagged with a sense identifier, and supplied with context.
"""       

from util import *
from nltk import tokenize
import os, re, xml.sax

documents = ["hard", "interest", "line", "serve"]
items = list(documents)

class SensevalParser(xml.sax.ContentHandler):

    def __init__(self, buffer_size=1024):
        xml.sax.ContentHandler.__init__(self)
        self._lemma = ''
        self._buffer_size = buffer_size
        self.reset()

    def parse(self, text):
        if hasattr(text, '__iter__') and hasattr(text, 'next'):
            text = ''.join(text)
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        current = 0
        while current < len(text):
            buffer = text[current : current + self._buffer_size]
            parser.feed(buffer)
            for instance in self._instances:
                yield instance
                self.reset(True, False)
            current += self._buffer_size
        parser.close()

    def characters(self, ch):
        self._data += _to_ascii(ch)

    def startElement(self, tag, attr):
        if tag == 'wf':
            self._pos = _to_ascii(attr.getValueByQName('pos'))
        elif tag == 'answer':
            instance_id = _to_ascii(attr.getValueByQName('instance'))
            self._senses.append(_to_ascii(attr.getValueByQName('senseid')))
            self._iloc = instance_id
            
        elif tag == 'context':
            self._data = ''
        elif tag == 'lexelt':
            self._lemma = _to_ascii(attr.getValueByQName('item'))
        elif tag == 'head':
            self._head = self._wnum - 1
        
    def endElement(self, tag):
        if tag == 'wf':
            text = self._data.strip()
            pos = self._pos
            self._tokens.append((text, pos))
            self._wnum += 1
            self._data = ''
        elif tag == 'context':
            self._instances.append((tuple(self._senses), self._head, self._tokens))
            self.reset(False)

    def instances(self):
        return self._instances

    def reset(self, instances=True, state=True):
        if instances:
            self._instances = []
        if state:
            self._senses = []
            self._head = None
            self._data = ''
            self._wnum = 1
            self._iloc = None
            self._tokens = []
            self._pos = None

def _to_ascii(text):
    return text.encode('Latin-1')


def read_document(name):
    filename = find_corpus_file('senseval', name, '.pos')
    parser = SensevalParser()
    return parser.parse(open(filename).read())

######################################################################
#{ Convenience Functions
######################################################################
read = read_document

######################################################################
#{ Demo
######################################################################
def demo():
    from nltk.corpus import senseval
    from itertools import islice
    import string

    # Print one example of each sense
    
    seen = set()
    for (senses, position, context) in senseval.read('line'):
        if senses not in seen:
            seen.add(senses)
            print "senses:", senses
            print "position:", position
            print "context:", string.join('%s/%s' % ttok for ttok in context)
            print
        
if __name__ == '__main__':
    demo()


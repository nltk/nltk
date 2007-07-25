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

from nltk.corpus.reader.util import *
from api import *
from nltk.tokenize import *
import os, re, xml.sax
from xmldocs import XMLCorpusReader
from nltk.etree import ElementTree

#: A list of all documents in this corpus.
items = sorted(["hard", "interest", "line", "serve"])

class SensevalInstance:
    def __init__(self, word, position, context, senses):
        self.word = word
        self.senses = tuple(senses)
        self.position = position
        self.context = context
    def __repr__(self):
        return ('SensevalInstance(word=%r, position=%r, '
                'context=%r, senses=%r)' %
                (self.word, self.position, self.context, self.senses))

class SensevalCorpusReader(CorpusReader):
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

    def instances(self, items=None):
        return concat([SensevalCorpusView(filename)
                       for filename in self._item_filenames(items)])

    def _item_filenames(self, items):
        if items is None: items = self.items
        if isinstance(items, basestring): items = [items]
        return [os.path.join(self._root, '%s%s' % (item, self._extension))
                for item in items]
    
    def _entry(self, tree):
        elts = []
        for lexelt in tree.findall('lexelt'):
            for inst in lexelt.findall('instance'):
                sense = inst[0].attrib['senseid']
                context = [(w.text, w.attrib['pos'])
                           for w in inst[1]]
                elts.append( (sense, context) )
        return elts

class SensevalCorpusView(StreamBackedCorpusView):
    def __init__(self, filename):
        StreamBackedCorpusView.__init__(self, filename)

        self._word_tokenizer = WhitespaceTokenizer()
        self._lexelt_starts = [0] # list of streampos
        self._lexelts = [None] # list of lexelt names
    
    def read_block(self, stream):
        # Decide which lexical element we're in.
        lexelt_num = bisect.bisect_right(self._lexelt_starts, stream.tell())-1
        lexelt = self._lexelts[lexelt_num]
        
        instance_lines = []
        in_instance = False
        while True:
            line = stream.readline()
            if line == '':
                assert instance_lines == []
                return []
            
            # Start of a lexical element?
            if line.lstrip().startswith('<lexelt'):
                lexelt_num += 1
                m = re.search('item=("[^"]+"|\'[^\']+\')', line)
                assert m is not None # <lexelt> has no 'item=...'
                lexelt = m.group(1)[1:-1]
                if lexelt_num < len(self._lexelts):
                    assert lexelt == self._lexelts[lexelt_num]
                else:
                    self._lexelts.append(lexelt)
                    self._lexelt_starts.append(stream.tell())
                
            # Start of an instance?
            if line.lstrip().startswith('<instance'):
                assert instance_lines == []
                in_instance = True

            # Body of an instance?
            if in_instance:
                instance_lines.append(line)

            # End of an instance?
            if line.lstrip().startswith('</instance'):
                xml_block = '\n'.join(instance_lines)
                xml_block = re.sub(r'&(\w+);', r'[\1]', xml_block)
                #print xml_block
                inst = ElementTree.fromstring(xml_block)
                return [self._parse_instance(inst, lexelt)]

    def _parse_instance(self, instance, lexelt):
        senses = []
        context = []
        position = None
        for child in instance:
            if child.tag == 'answer':
                senses.append(child.attrib['senseid'])
            elif child.tag == 'context':
                context += self._word_tokenizer.tokenize(child.text)
                for cword in child:
                    if cword.tag == 'compound': 
                        cword = cword[0] # is this ok to do?
                    
                    if cword.tag == 'head':
                        # Some santiy checks:
                        assert position is None, 'head specified twice'
                        assert cword.text.strip() or len(cword)==1
                        assert not (cword.text.strip() and len(cword)==1)
                        # Record the position of the head:
                        position = len(context)
                        # Addd on the head word itself:
                        if cword.text.strip():
                            context.append(cword.text.strip())
                        elif cword[0].tag == 'wf':
                            context.append((cword[0].text,
                                            cword[0].attrib['pos']))
                            if cword[0].tail:
                                context += self._word_tokenizer.tokenize(
                                    cword[0].tail)
                        else:
                            assert False, 'expected CDATA or wf in <head>'
                    elif cword.tag == 'wf':
                        context.append((cword.text, cword.attrib['pos']))
                    elif cword.tag == 's':
                        pass # Sentence boundary marker.
                    
                    else:
                        print 'ACK', cword.tag
                        assert False, 'expected CDATA or <wf> or <head>'
                    if cword.tail:
                        context += self._word_tokenizer.tokenize(cword.tail)
            else:
                assert False, 'unexpected tag %s' % child.tag
        return SensevalInstance(lexelt, position, context, senses)
    

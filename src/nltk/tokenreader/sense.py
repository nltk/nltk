# Natural Language Toolkit: Word sense utilities
#
# Copyright (C) 2003 University of Melbourne
# Author: Trevor Cohn <tacohn@cs.mu.oz.au>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT
#
# $Id$
#

"""
(Under construction.)

Grouping of tools relating to Word Sense Disambiguation (WSD).
Currently, this module is comprised of the C{SenseTaggedType} and
C{SemcorTokenizer} classes. It is intended to grow as more general
WSD utilities are created, however, it may be conflated with the
classifier modules due to the high levels of similarity between
classification for Infromation Retrieval (IR) and classification for
WSD.

C{SenseTaggedType} extends C{TaggedType} to include sense identifiers.
These can be accessed via the C{lemma}, C{sense_id} and C{global_id}
methods. The interface may need subtle adjustments to reflect the sense
tagging of other data sources (eg. SENSEVAL) as parsers are developed.

The C{SemcorTokenizer} parses Semcor 1.7 data, as used in the C{corpus}
module. This data is sourced from C{http://engr.smu.edu/~rada/semcor/}.
"""

from __future__ import generators
import re
import sgmllib
import xml.dom.minidom
import xml.sax
from nltk.tokenizer import AbstractTokenizer
from nltk.token import *

# [XX] Register reprs for these?

############################################################
# Semcor
############################################################

class SemcorTokenizer(AbstractTokenizer):
    """
    Tokenizer for Semcor 1.7 files. These files are encoded in SGML,
    hierarchically organised into paragraphs, sentences and individual
    tokens. Each token is marked up with its part-of-speech, and
    optionally with a WordNet lemma, synset number and global
    identifier. These tags allow the synset of each tagged word to be
    located in WordNet. Nb. The C{pywordnet} project provides a Python
    interface to WordNet.

    This tokenizer may be parametised with the unit of hierarchy to
    preserve -- either word, sentence or paragraph. When tokenizing
    with word units, a list of tokens of words will be returned. When
    tokenizing with sentence units, a list of tokens of sentences will
    be returned. A token of a sentence contains a list of tokens of
    words. Paragraph goes a set further, returning a list of tokens of
    paragraphs (lists of sentences).
    """

    UNIT_WORD       = 'word'
    UNIT_SENTENCE   = 'sentence'
    UNIT_PARAGRAPH  = 'paragraph'

    def __init__(self, unit=UNIT_WORD, **property_names):
        """
        Creates a SemcorTokenizer.

        @param unit: one of 'word', 'sentence' or 'paragraph';
            indicating the level of hierarchy to be processed.
        @type unit: C{String}
        """
        assert unit in [ SemcorTokenizer.UNIT_WORD,
                         SemcorTokenizer.UNIT_SENTENCE,
                         SemcorTokenizer.UNIT_PARAGRAPH ]
        self._unit = unit
        self._parse_method = _parseSGMLString
        # if it were valid XML, we could use this:
        #self._parse_method = xml.dom.minidom.parseString
        AbstractTokenizer.__init__(self, **property_names)

    # [XX] add_locs and add_contexts are ignored.
    def tokenize(self, token, add_locs=False, add_contexts=False):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        TEXT = self._property_names.get('TEXT', 'TEXT')
        
        text = token[TEXT]
        
        output = []
        dom = self._parse_method(text)
        files = dom.getElementsByTagName('contextfile')
        for file in files:
            contexts = file.getElementsByTagName('context')
            for context in contexts:
                filename = _to_ascii(file.getAttribute('concordance')) \
                    + ':' + _to_ascii(context.getAttribute('filename'))
                paragraphs = context.getElementsByTagName('p')
                for paragraph in paragraphs:
                    item = self._map_paragraph(paragraph, filename)
                    if self._unit == self.UNIT_PARAGRAPH:
                        output.append(item)
                    else:
                        output.extend(item)
        token[SUBTOKENS] = output

    def _map_paragraph(self, node, source):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        LOC = self._property_names.get('LOC', 'LOC')
        pnum = int(node.getAttribute('pnum'))
        ploc = ParaIndexLocation(pnum, source)
        sentences = node.getElementsByTagName('s')
        out = []
        for sentence in sentences:
            item = self._map_sentence(sentence, ploc)
            if self._unit != self.UNIT_WORD:
                out.append(item)
            else:
                out.extend(item)
        if self._unit == self.UNIT_PARAGRAPH:
            return Token({SUBTOKENS:out, LOC:ploc})
        else:
            return out

    def _map_sentence(self, node, source):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        LOC = self._property_names.get('LOC', 'LOC')
        snum = int(node.getAttribute('snum'))
        sloc = SentIndexLocation(snum, source)
        out = []
        index = 0
        for word in node.childNodes:
            wloc = WordIndexLocation(index, sloc)
            item = self._map_word(word, wloc)
            if item <> None:
                index += 1
                out.append(item)
        if self._unit != self.UNIT_WORD:
            return Token({SUBTOKENS:out, LOC:sloc})
        else:
            return out

    def _map_word(self, node, loc):
        if node.localName == 'wf':
            text = _to_ascii(node.childNodes[0].data)
            pos = _to_ascii(node.getAttribute('pos'))
            lemma = _to_ascii(node.getAttribute('lemma'))
            wnsn = _to_ascii(node.getAttribute('wnsn'))
            lexsn = _to_ascii(node.getAttribute('lexsn'))
            if not lemma or not wnsn or not lexsn:
                lemma = wnsn = lexsn = None

            return Token(text=text, pos=pos, lemma=lemma,
                         wnsn=wnsn, lexsn=lexsn, loc=loc)
                         
        elif node.localName == 'punc':
            text = _to_ascii(node.childNodes[0].data)
            return Token(text=text, pos=text, lemma=None,
                         wnsn=None, lexsn=None, loc=loc)
        else:
            return None

def _to_ascii(text):
    return text.encode('Latin-1')

class _SGMLNode:
    """
    Mimics a xml.dom.Node object, well, enough for SemcorTokenizer to be
    fooled.
    """

    def __init__(self, name, text, attributes, children):
        self.localName = name
        self.data = text
        self.attributes = attributes
        self.childNodes = children

    def getElementsByTagName(self, name):
        out = []
        for child in self.childNodes:
            if child.localName == name:
                out.append(child)
        return out

    def getAttribute(self, name):
        return self.attributes.get(name, '')

    def __repr__(self):
        if self.localName == None:
            return self.data
        else:
            return '<%s %s>%s</%s>' % (self.localName, 
                ' '.join(['%s="%s"' % item for item in self.attributes.items()]),
                ' '.join([str(kid) for kid in self.childNodes]),
                self.localName)

class _SimpleSGMLParser(sgmllib.SGMLParser):
    """
    Dumb parser that simply creates an SGMLNode hierarchy corresponding
    to the input SGML text. This hierarchy is roughly equivalent to the
    DOM hierarchy created by C{minidom} on the equivalent XML file.
    """

    def __init__(self):
        sgmllib.SGMLParser.__init__(self)
        self._document = _SGMLNode('document', None, {}, [])
        self._stack = [self._document]

    def document(self): 
        return self._document
    
    def _current(self):
        return self._stack[-1]

    def handle_data(self, data):
        new = _SGMLNode(None, data, {}, [])
        self._current().childNodes.append(new)

    def unknown_starttag(self, tag, attributes):
        new = _SGMLNode(tag, None, dict(attributes), [])
        self._current().childNodes.append(new)
        self._stack.append(new)

    def unknown_endtag(self, tag):
        self._stack.pop()

def _parseSGMLString(text):
    p = _SimpleSGMLParser()
    p.feed(text)
    p.close()
    return p.document()

############################################################
# Senseval
############################################################

class DOMSensevalTokenizer(AbstractTokenizer):
    """
    Tokenizer for Senseval-2 files. These files are encoded in pseudo-XML
    grouped into instances, each containing a few paragraphs of text
    including the head word. The instance is tagged with the sense 
    identifier, and the head word is marked up. This tokenizer accepts
    those files with POS tags.

    The XML is first cleaned up before being processed. The code is
    not particularly efficient - with large files, memory usage may
    cause problems. This is due to the use of the XML DOM - the less
    readable C{SensevalTokenizer} is
    """

    def __init__(self, **property_names):
        AbstractTokenizer.__init__(self, **property_names)

    def _map_context(self, node, source):
        head = None
        tokens = []
        for index, child in enumerate(node.childNodes):
            if child.localName == 'head':
                head = index
                child = child.getElementsByTagName('wf')[0]
            if child.localName == 'wf':
                pos = _to_ascii(child.getAttribute('pos'))
                text = _to_ascii(child.firstChild.data)
                loc = WordIndexLocation(index, source)
                tokens.append(Token(text=text, pos=pos, loc=loc))
        return tokens, head

    # [XX] add_locs and add_contexts are ignored.
    def tokenize(self, token, add_locs=False, add_contexts=False):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        self.xtokenize(token, add_locs, add_contexts)
        token[SUBTOKENS] = list(token[SUBTOKENS])

    # [XX] add_locs and add_contexts are ignored.
    def xtokenize(self, token, add_locs=False, add_contexts=False):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        TEXT = self._property_names.get('TEXT', 'TEXT')
        text = token[TEXT]
        if hasattr(text, '__iter__') and hasattr(text, 'next'):
            text = ''.join(text)
        token[SUBTOKENS] = self._tokengen(text, add_locs, add_contexts)

    # [XX] add_locs and add_contexts are ignored.
    def _tokengen(self, text, add_locs=False, add_contexts=False):
        SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        # inherit docs
        fixed = _fixXML(text)
        doc = xml.dom.minidom.parseString(fixed)
        # this takes up a HUGE amount of memory
        instances = doc.getElementsByTagName('instance')
        for instance in instances:
            lexelt = instance.getElementsByTagName('lexelt')[0]
            context = instance.getElementsByTagName('context')[0]
            answers = instance.getElementsByTagName('answer')
            senses = []
            for answer in answers:
                senses.append(_to_ascii(answer.getAttribute('senseid')))

            # [XX] ??
            loc = _to_ascii(answer.getAttribute('instance'))

            tokens, head = self._map_context(context, loc)
            lemma = _to_ascii(lexelt.getAttribute('item'))
            
            yield Token({SUBTOKENS:tokens, 'senses':tuple(sense),
                           'head':head, 'lemma':lemma})
        doc.unlink()

def _fixXML(text):
    """
    Fix the various issues with Senseval pseudo-XML.
    """
    # <~> or <^> => ~ or ^
    text = re.sub(r'<([~\^])>', r'\1', text)
    # fix lone &
    text = re.sub(r'(\s+)\&(\s+)', r'\1&amp;\2', text)
    # fix """
    text = re.sub(r'"""', '\'"\'', text)
    # fix <s snum=dd> => <s snum="dd"/>
    text = re.sub(r'(<[^<]*snum=)([^">]+)>', r'\1"\2"/>', text)
    # fix foreign word tag
    text = re.sub(r'<\&frasl>\s*<p[^>]*>', 'FRASL', text)
    # remove <&I .> 
    text = re.sub(r'<\&I[^>]*>', '', text)
    # fix <{word}>
    text = re.sub(r'<{([^}]+)}>', r'\1', text)
    # remove <@>, <p>, </p>
    text = re.sub(r'<(@|/?p)>', r'', text)
    # remove <&M .> and <&T .> and <&Ms .>
    text = re.sub(r'<&\w+ \.>', r'', text)
    # remove <!DOCTYPE... > lines
    text = re.sub(r'<!DOCTYPE[^>]*>', r'', text)
    # remove <[hi]> and <[/p]> etc
    text = re.sub(r'<\[\/?[^>]+\]*>', r'', text)
    # take the thing out of the brackets: <&hellip;>
    text = re.sub(r'<(\&\w+;)>', r'\1', text)
    # and remove the & for those patterns that aren't regular XML
    text = re.sub(r'&(?!amp|gt|lt|apos|quot)', r'', text)
    # fix 'abc <p="foo"/>' style tags - now <wf pos="foo">abc</wf>
    text = re.sub(r'[ \t]*([^<>\s]+?)[ \t]*<p="([^"]*"?)"/>',
                  r' <wf pos="\2">\1</wf>', text)
    text = re.sub(r'\s*"\s*<p=\'"\'/>', " <wf pos='\"'>\"</wf>", text)
    return text

class SAXSensevalTokenizer(xml.sax.ContentHandler, AbstractTokenizer):
    """
    Tokenizer for Senseval-2 files. These files are encoded in pseudo-XML
    grouped into instances, each containing a few paragraphs of text
    including the head word. The instance is tagged with the sense 
    identifiers, and the head word is marked up. This tokenizer accepts
    those files with POS tags. Note that the labels of the
    C{SenseLabeledText}s (as returned inside C{Token}s from the tokenize
    method) are tuples, as the Senseval-2 format allows for multiple senses
    for a given instance. This sequence will have at least one item.

    The XML is first cleaned up before being processed. 
    """

    def __init__(self, buffer_size=1024, **property_names):
        xml.sax.ContentHandler.__init__(self)
        self._lemma = ''
        self._buffer_size = buffer_size
        self.reset()
        AbstractTokenizer.__init__(self, **property_names)

    # [XX] add_locs and add_contexts are ignored.
    def tokenize(self, token, add_locs=False, add_contexts=False):
#       SUBTOKENS = self._property_names.get('SUBTOKENS', 'SUBTOKENS')
        SUBTOKENS = self.property('SUBTOKENS')
        TEXT = self.property('TEXT')
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        fixed =  _fixXML(token[TEXT])
        parser.feed(fixed)
        parser.close()
        token[SUBTOKENS] = self._instances

    # [XX] add_locs and add_contexts are ignored.
    def xtokenize(self, token, add_locs=False, add_contexts=False):
        SUBTOKENS = self.property('SUBTOKENS')
        TEXT = self.property('TEXT')
        text = token[TEXT]
        if hasattr(text, '__iter__') and hasattr(text, 'next'):
            text = ''.join(text)
        token[SUBTOKENS] = self._tokengen(text)
        
    def _tokengen(self, text):
        fixed = _fixXML(text)
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        current = 0
        while current < len(fixed):
            buffer = fixed[current : current + self._buffer_size]
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

            # [XX] ???
            self._iloc = instance_id
            
        elif tag == 'context':
            self._data = ''
        elif tag == 'lexelt':
            self._lemma = _to_ascii(attr.getValueByQName('item'))
        elif tag == 'head':
            self._head = self._wnum - 1
        
    def endElement(self, tag):
        SUBTOKENS = self.property('SUBTOKENS')
        if tag == 'wf':
            text = self._data.strip()
            pos = self._pos
            loc = WordIndexLocation(self._wnum, self._iloc)
            self._tokens.append(Token(text=text, pos=pos, loc=loc))
            self._wnum += 1
            self._data = ''
        elif tag == 'context':
            self._instances.append(Token({SUBTOKENS:self._tokens,
                                            'senses':tuple(self._senses),
                                            'head':self._head,
                                            'lemma':self._lemma}))
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

#SensevalTokenizer = DOMSensevalTokenizer
SensevalTokenizer = SAXSensevalTokenizer

def _demo_semcor_tokenizer(type, files):
    import pprint, sys
    r = SemcorTokenizer(type)
    for file in files:
        print 'Parsing', file, '...'
        print '=' * 75
        try:
            tok = Token(TEXT=open(file).read())
            r.tokenize(tok)
            for item in tok['SUBTOKENS']:
                pprint.pprint(item)
        except:
            print >>sys.stderr, 'Error parsing file:', file
            raise

def _demo_senseval_tokenizer(files):
    tk = SensevalTokenizer()
    for file in files:
        print '=' * 75
        print file
        print '=' * 75
        tok = Token(TEXT=open(file).read())
        tk.xtokenize(tok)
        for token in tok['SUBTOKENS']:
            print token

if __name__ == '__main__':
    #files = ['%s/br-%s' % (path,x) for x in 'a01 a02 a11 k29'.split()]
    #_demo_semcor_tokenizer('sentence', files)
    path = '/usr/share/nltk/senseval/'
    files = ['%s/%s.pos' % (path,x)
             for x in 'line serve hard interest'.split()]
    _demo_senseval_tokenizer(files)



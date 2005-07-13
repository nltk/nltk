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
C{SemcorTokenReader} classes. It is intended to grow as more general
WSD utilities are created, however, it may be conflated with the
classifier modules due to the high levels of similarity between
classification for Infromation Retrieval (IR) and classification for
WSD.

C{SenseTaggedType} extends C{TaggedType} to include sense identifiers.
These can be accessed via the C{lemma}, C{sense_id} and C{global_id}
methods. The interface may need subtle adjustments to reflect the sense
tagging of other data sources (eg. SENSEVAL) as parsers are developed.

The C{SemcorTokenReader} parses Semcor 1.7 data, as used in the C{corpus}
module. This data is sourced from C{http://engr.smu.edu/~rada/semcor/}.
"""

import re
import sgmllib
import xml.sax
from nltk.token import *
from nltk.tokenreader import *

# [XX] Register reprs for these?

############################################################
# Semcor
############################################################

class SemcorTokenReader(TokenReaderI, PropertyIndirectionMixIn):
    """
    Token reader for Semcor 1.7 files. These files are encoded in SGML,
    hierarchically organised into paragraphs, sentences and individual
    tokens. Each token is marked up with its part-of-speech, and
    optionally with a WordNet lemma, synset number and global
    identifier. These tags allow the synset of each tagged word to be
    located in WordNet. Nb. The C{pywordnet} project provides a Python
    interface to WordNet.

    This token reader may be parametised with the unit of hierarchy to
    preserve -- either word, sentence or paragraph. When processing
    with word units, a list of tokens of words will be returned. When
    processing sentence units, a list of tokens of sentences will
    be returned. A token of a sentence contains a list of tokens of
    words. Paragraph goes a set further, returning a list of tokens of
    paragraphs (lists of sentences).

    Nb: The properties SUBTOKENS, TEXT, LOC, POS and SENSE are used
    in constructing the tokens. They take on the usual meanings, however 
    POS is used in the place of TAG, and SENSE is a new property
    unique to sense tagged data.

    @outprop: C{SUBTOKENS}: The list of subtokens.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{POS}: The subtokens' part-of-speech tags.
    @outprop: C{LOC}: The subtokens' location.
    @outprop: C{SENSE}: The subtokens' wordnet sense tags -- a 3-tuple of
        the lemma, sense number and wordnet sense reference.
    """

    UNIT_WORD       = 'word'
    UNIT_SENTENCE   = 'sentence'
    UNIT_PARAGRAPH  = 'paragraph'

    def __init__(self, unit=UNIT_WORD, **property_names):
        """
        @param unit: one of 'word', 'sentence' or 'paragraph';
            indicating the level of hierarchy to be processed.
        @type unit: C{String}
        """
        assert unit in [ SemcorTokenReader.UNIT_WORD,
                         SemcorTokenReader.UNIT_SENTENCE,
                         SemcorTokenReader.UNIT_PARAGRAPH ]
        self._unit = unit
        self._parse_method = _parseSGMLString
        # if it were valid XML, we could use this:
        #self._parse_method = xml.dom.minidom.parseString
        PropertyIndirectionMixIn.__init__(self, **property_names)

    # [XX] add_contexts and source are ignored.
    def read_token(self, s, add_contexts=False, add_locs=False, source=None):
        TEXT = self.property('TEXT')
        SUBTOKENS = self.property('SUBTOKENS')
        
        output = []
        dom = self._parse_method(s)
        files = dom.getElementsByTagName('contextfile')
        for file in files:
            contexts = file.getElementsByTagName('context')
            for context in contexts:
                filename = _to_ascii(file.getAttribute('concordance')) \
                    + ':' + _to_ascii(context.getAttribute('filename'))
                paragraphs = context.getElementsByTagName('p')
                for paragraph in paragraphs:
                    item = self._map_paragraph(paragraph, filename, add_locs)
                    if self._unit == self.UNIT_PARAGRAPH:
                        output.append(item)
                    else:
                        output.extend(item)
        return Token(**{SUBTOKENS: output})

    def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
        return [self.read_token(s, add_contexts, add_locs, source)]

    def _map_paragraph(self, node, source, add_locs):
        SUBTOKENS = self.property('SUBTOKENS')
        LOC = self.property('LOC')
        ploc = None
        if add_locs:
            pnum = int(node.getAttribute('pnum'))
            ploc = ParaIndexLocation(pnum, source)
        sentences = node.getElementsByTagName('s')
        out = []
        for sentence in sentences:
            item = self._map_sentence(sentence, ploc, add_locs)
            if self._unit != self.UNIT_WORD:
                out.append(item)
            else:
                out.extend(item)
        if self._unit == self.UNIT_PARAGRAPH:
            if add_locs:
                return Token(SUBTOKENS=out, LOC=ploc)
            else:
                return Token(SUBTOKENS=out)
        else:
            return out

    def _map_sentence(self, node, source, add_locs):
        SUBTOKENS = self.property('SUBTOKENS')
        LOC = self.property('LOC')
        if add_locs:
            snum = int(node.getAttribute('snum'))
            sloc = SentIndexLocation(snum, source)
        out = []
        index = 0
        for word in node.childNodes:
            wloc = None
            if add_locs:
                wloc = WordIndexLocation(index, sloc)
            item = self._map_word(word, wloc, add_locs)
            if item <> None:
                index += 1
                out.append(item)
        if self._unit != self.UNIT_WORD:
            if add_locs:
                return Token(SUBTOKENS=out, LOC=sloc)
            else:
                return Token(SUBTOKENS=out)
        else:
            return out

    def _map_word(self, node, loc, add_locs):
        TEXT = self.property('TEXT')
        LEMMA = self.property('LEMMA')
        POS = self.property('POS')
        SENSE = self.property('SENSE')

        if node.localName == 'wf':
            text = _to_ascii(node.childNodes[0].data)
            pos = _to_ascii(node.getAttribute('pos'))
            lemma = _to_ascii(node.getAttribute('lemma'))
            wnsn = _to_ascii(node.getAttribute('wnsn'))
            lexsn = _to_ascii(node.getAttribute('lexsn'))

            t = Token(TEXT=text, POS=pos)
            if add_locs:
                t[LOC] = loc
            if lemma:
                t[LEMMA] = lemma
                if wnsn and lexsn:
                    t[SENSE] = (lemma, wnsn, lexsn)
            return t
                         
        elif node.localName == 'punc':
            text = _to_ascii(node.childNodes[0].data)
            if add_locs:
                return Token(TEXT=text, POS=text, LOC=loc)
            else:
                return Token(TEXT=text, POS=text)
        else:
            return None

def _to_ascii(text):
    return text.encode('Latin-1')

class _SGMLNode:
    """
    Mimics a xml.dom.Node object, well, enough for SemcorTokenReader to be
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

class SensevalTokenReader(xml.sax.ContentHandler, TokenReaderI, PropertyIndirectionMixIn):
    """
    Token reader for Senseval-2 files. These files are encoded in pseudo-XML
    grouped into instances, each containing a few paragraphs of text including
    the head word. The instance is tagged with the sense identifiers, and the
    head word is marked up. This tokenizer accepts those files with POS tags.
    Note that the labels of the C{SenseLabeledText}s (as returned inside
    C{Token}s from the tokenize method) are tuples, as the Senseval-2 format
    allows for multiple senses for a given instance. This sequence will have
    at least one item.

    The XML is first cleaned up before being processed. 

    @outprop: C{INSTANCES}: The list of instances (polysemous word and its context).
    @outprop: C{SUBTOKENS}: The list of subtokens withing each instance.
    @outprop: C{TEXT}: The subtokens' text contents.
    @outprop: C{POS}: The subtokens' part-of-speech tags.
    @outprop: C{LOC}: The subtokens' location.
    @outprop: C{SENSE}: The subtokens' senseval sense tag - a tuple of the
        lemma and the list of correct sense tags.
    """

    def __init__(self, buffer_size=1024, **property_names):
        xml.sax.ContentHandler.__init__(self)
        self._lemma = ''
        self._buffer_size = buffer_size
        self._add_locs = False
        self.reset()
        PropertyIndirectionMixIn.__init__(self, **property_names)

    # [XX] add_contexts and source are ignored.
    def read_token(self, s, add_contexts=False, add_locs=False, source=None):
        INSTANCES = self.property('INSTANCES')
        self._add_locs = add_locs
        parser = xml.sax.make_parser()
        parser.setContentHandler(self)
        fixed =  _fixXML(s)
        parser.feed(fixed)
        parser.close()
        return Token(INSTANCES = self._instances)

    def read_tokens(self, s, add_contexts=False, add_locs=False, source=None):
        return [self.read_token(s, add_contexts, add_locs, source)]

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
            self._head = 'next'
        
    def endElement(self, tag):
        SUBTOKENS = self.property('SUBTOKENS')
        SENSE = self.property('SENSE')
        HEAD = self.property('HEAD')
        LEMMA = self.property('LEMMA')
        LOC = self.property('LOC')
        POS = self.property('POS')

        if tag == 'wf':
            text = self._data.strip()
            pos = self._pos
            tk = Token(TEXT=text, POS=pos)
            loc = WordIndexLocation(self._wnum, self._iloc)
            if self._add_locs:
                tk[LOC] = loc
            if self._head == 'next':
                self._head = loc
                tk[SENSE] = (self._lemma, self._senses)
                tk[LEMMA] = self._lemma
            self._tokens.append(tk)
            self._wnum += 1
            self._data = ''
        elif tag == 'context':
            self._instances.append(Token(SUBTOKENS=self._tokens, HEAD=self._head))
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

def demo_SemcorTokenReader(type, files):
    import pprint, sys
    r = SemcorTokenReader(type)
    for file in files:
        print 'Parsing', file, '...'
        print '=' * 75
        try:
            tok = r.read_token(open(file).read())
            for item in tok['SUBTOKENS']:
                pprint.pprint(item)
        except:
            print >>sys.stderr, 'Error parsing file:', file
            raise

def demo_SensevalTokenReader(files):
    r = SensevalTokenReader()
    for file in files:
        print '=' * 75
        print file
        print '=' * 75
        tok = r.read_token(open(file).read())
        for token in tok['SUBTOKENS']:
            print token

def demo(add_locs = False):
    import nltk.corpus, os.path

    print '*' * 80
    print 'SemcorTokenReader'
    print '*' * 80
    print
    path = os.path.join(nltk.corpus.get_basedir(), 'semcor1.7', 'brown1', 'tagfiles')
    infile = os.path.join(path, 'br-a01')
    demo_SemcorTokenReader('sentence', [infile])

    print
    print '*' * 80
    print 'SensevalTokenReader'
    print '*' * 80
    print
    path = os.path.join(nltk.corpus.get_basedir(), 'senseval')
    infile = os.path.join(path, 'interest.pos')
    demo_SensevalTokenReader([infile])

if __name__ == '__main__':
    demo()


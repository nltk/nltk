# Natural Language Toolkit: A Chunk Parser
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from parser import *
from token import *
from tree import *
from tagger import *
from re import *
from string import *

class ChunkRule:
    def __init__(self, target, action, **kwargs):
        self._target = target
        self._action = action
        self._left = self._right = self._doc = ''
        if kwargs.has_key('left'):
            self._left = kwargs['left']
        if kwargs.has_key('right'):
            self._right = kwargs['right']
        if kwargs.has_key('doc'):
            self._doc = kwargs['doc']
    def target(self):
        return self._target
    def action(self):
        return self._action
    def left(self):
        return self._left
    def right(self):
        return self._right
    def doc(self):
        return self._doc
    def __str__(self):
        return self.doc() + ":\n  "\
               + self.target() + " -> " + self.action() + "\n  "\
               + "left=" + self.left() + ", right=" + self.right()

# A version of ChunkRule which understands a simplified regexp syntax
# in which users don't need to know about locations, and in which <>
# functions as anonymous brackets, both with respect to the tags
# it contains (e.g. <DT|JJ>) and with respect to external operators
# (e.g. <JJ>*)

def expand(str):
    return sub(r'<([^>]+)>', r'(?:<(?:\1)@\d+>)', str)

class AbstractChunkRule(ChunkRule):
    def __init__(self, target, action, **kwargs):
        self._target = expand(target)
        self._action = action
        self._left = self._right = self._doc = ''
        if kwargs.has_key('left'):
            self._left = expand(kwargs['left'])
        if kwargs.has_key('right'):
            self._right = expand(kwargs['right'])
        if kwargs.has_key('doc'):
            self._doc = kwargs['doc']

def lookbehind(str):
    return '(?<='+str+')'
def lookahead(str):
    return '(?='+str+')'
# assumes the only difference is indels of '{' and '}'
def pad(str):
    str = sub(r' +', '', str)
    str = sub(r'@\d+', '', str)
    str = sub(r'<', ' <', str)
    str = sub(r'>', '> ', str)
    str = sub(r'> }', '>}', str)
    str = sub(r'{ <', '{<', str)
    return str
# assumes tags are strings and locations are unary
def tag2str(tagged_sent):
    str = ''
    for tok in tagged_sent:
        str += '<' + tok.type().tag() + '@' + `tok.loc().start()` + '>'
    return str

# take a chunked string and return the chunk locations
def chunks2locs(str):
    braces = sub(r'[^{}]', '', str)
    if not match(r'(\{\})*', braces):
        print "ERROR"
    spaced = sub(r'([<>{}])(?=[<>{}])', r'\1 ', str)
    list = split(spaced)
    newlist = []
    prev = 0
    building = 0
    for elt in list:
        if elt == '{':
            building = 1
            prev = 0
        elif elt == '}':
            building = 0
        elif building:
            x = re.match(r'<.*?@(\d+)>', elt)
            if x:
                loc = Location(int(x.group(1)))
                if prev:
                    newlist[-1] += loc
                else:
                    newlist.append(loc)
                    prev = 1
            else:
                prev = 0
    return newlist


class ChunkParser(ParserI):
    def __init__(self, tagger, rulelist):
        self._tagger = tagger
        self._rulelist = rulelist

    def _diagnostic(self, pattern, action, str, result, doc):
        print "\n%s: %s -> %s" % (doc, pattern, action)
        print "    ", pad(str)
        print " -> ", pad(result)

    def _apply(self, rule, str):
        action = rule.action()
        doc = rule.doc()
        pattern = lookbehind(rule.left())\
                  + rule.target()\
                  + lookahead(rule.right())
        result = sub(pattern, action, str)
        self._diagnostic(pattern, action, str, result, doc)
        return result

    # needs to return a tree, not locations
    def parse(self, tok_sent):
        print tok_sent
        tagged_sent = self._tagger.tag(tok_sent)
        str = tag2str(tagged_sent)
        for rule in self._rulelist:
            print rule
            str = self._apply(rule, str)
        locs = chunks2locs(str)
        return locs

### DEMO CODE ###

from nltk.set import *
def demo():
    class MyTagger(TaggerI):
        def tag(self, tokens):
            mydict = {'the':'DT', 'little':'JJ', 'cat':'NN', 'sat':'VB',
                      'on':'PP', 'the':'DT', 'mat':'NN'}
            tagged_tokens = []
            for token in tokens:
                word = token.type()
                if mydict.has_key(word):
                    token_type = TaggedType(word, mydict[word])
                else:
                    token_type = TaggedType(word, 'NN')
                tagged_tokens.append(Token(token_type, token.loc()))
            return tagged_tokens

    sent = [
        Token('the', Location(1)),
        Token('little', Location(2)),
        Token('cat', Location(3)),
        Token('sat', Location(4)),
        Token('on', Location(5)),
        Token('the', Location(6)),
        Token('mat', Location(7))
    ]

    def score(correct, guess):
        print "PREC:", correct.precision(Set(*guess))
        print "RECALL:", correct.recall(Set(*guess))

    correct = Set(Location(1,4), Location(5,8))

    tagged_sent = MyTagger().tag(sent)

    from re import *
    from string import *

    r1 = AbstractChunkRule(r'(<DT><JJ>*<NN>)', r'{\1}', doc="chunking <DT><JJ>*<NN>")
    cp = ChunkParser(MyTagger(), [r1])
    locs = cp.parse(sent)
    score(correct, locs)

    r1 = AbstractChunkRule(r'(<.*?>)', r'{\1}', doc="chunking every tag")

    DT_JJ_NNX = r'<DT|JJ|NN.*?>'
    r2 = AbstractChunkRule('('+DT_JJ_NNX+')}{', r'\1', right=DT_JJ_NNX,
                doc="chunk any groups of <DT> <JJ> and <NNX>")

    cp = ChunkParser(MyTagger(), [r1,r2])
    locs = cp.parse(sent)
    score(correct, locs)

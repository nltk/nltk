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

# this type stuff should be pulled in from somewhere else
# rather than being defined here...
from types import InstanceType as _InstanceType
def _pytype(obj):
    """
    @return: the pytype of C{obj}.  For class instances, this is
        their class; for all other objects, it is their type, as
        returned by type().
    @rtype: C{type} or C{class}
    @param obj: The object whose pytype should be returned.
    @type obj: (any)
    """
    if type(obj) == _InstanceType:
        return obj.__class__
    else:
        return type(obj)

# A chunk rule matches a target string and performs an action
# on it, usually adding or removing {}, the chunk delimiters.
# Keyword arguments handle context using zero-width assertions.
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
    return sub(r'<([^>]+)>', r'(?:<[^>]*?_(?:\1)@\d+>)', str)

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
# ignores the source and unit (bug)
def tag2str(tagged_sent):
    str = ''
    for tok in tagged_sent:
        str += '<' + tok.type().base() + '_' + tok.type().tag() + '@' + `tok.loc().start()` + '>'
    return str

# take a chunked string and return a tree
def chunks2tree(tagged_sent, str):
    braces = sub(r'[^{}]', '', str)
    if not match(r'(\{\})*', braces):
        print "ERROR: mismatched or nested braces"
    str = sub(r'([>}])(?=[<{])', r'\1, ', str)
    str = sub(r'<(.*?)_(.*?)@(\d+)>', r'Token(TaggedType("\1", "\2"), Location(\3))', str)
    str = sub(r'{(.*?)}', r'TreeToken("chunk", \1)', str)
    str = 'TreeToken("sent", ' + str + ')'
    print str
    return eval(str)

def tree2locs(tree):
    print "tree2locs:", tree
    locs = []
    for child in tree[:]:
        if _pytype(child) == TreeToken and child.node() == 'chunk':
            print child
            locs.append(child.location())
    return locs

class ChunkParser(ParserI):
    def __init__(self, tagger, rulelist):
        self._tagger = tagger
        self._rulelist = rulelist

    def _diagnostic(self, rule, str, result):
        print "\n%s:" % rule.doc()
        print "left:  ", rule.left()
        print "target:", rule.target()
        print "right: ", rule.right()
        print "action:", rule.action()
        print "input: ", pad(str)
        print "   ->  ", pad(result)

    def _apply(self, rule, str):
        action = rule.action()
        pattern = lookbehind(rule.left())\
                  + rule.target()\
                  + lookahead(rule.right())
        result = sub(pattern, action, str)
        self._diagnostic(rule, str, result)
        return result

    def parse(self, tok_sent):
        print tok_sent
        tagged_sent = self._tagger.tag(tok_sent)
        str = tag2str(tagged_sent)
        for rule in self._rulelist:
            print rule
            str = self._apply(rule, str)
        return chunks2tree(tagged_sent, str)

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

    from re import sub

    r1 = AbstractChunkRule(r'(<DT><JJ>*<NN>)', r'{\1}', doc="chunking <DT><JJ>*<NN>")
    cp = ChunkParser(MyTagger(), [r1])
    chunks = cp.parse(sent)
    locs = tree2locs(chunks)
    print locs
    score(correct, locs)

    r1 = AbstractChunkRule(r'(<.*?>)', r'{\1}', doc="chunking every tag")

    DT_JJ_NNX = r'<DT|JJ|NN.*?>'
#    DT_JJ_NNX = r'<DT>'
    r2 = AbstractChunkRule('('+DT_JJ_NNX+')}{', r'\1', right=DT_JJ_NNX,
                doc="chunk any groups of <DT> <JJ> and <NNX>")

    cp = ChunkParser(MyTagger(), [r1,r2])
    chunks = cp.parse(sent)
    locs = tree2locs(chunks)
    print locs
    score(correct, locs)

    

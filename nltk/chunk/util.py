# Natural Language Toolkit: Chunk format conversions
#
# Copyright (C) 2001-2009 NLTK Project
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT

import re
import string

from nltk import Tree
import nltk.tag.util

from api import *

##//////////////////////////////////////////////////////
## EVALUATION
##//////////////////////////////////////////////////////

from nltk.metrics import accuracy as _accuracy
def accuracy(chunker, gold):
    """
    Score the accuracy of the chunker against the gold standard.
    Strip the chunk information from the gold standard and rechunk it using
    the chunker, then compute the accuracy score.

    @type chunker: C{ChunkParserI}
    @param chunker: The chunker being evaluated.
    @type gold: C{tree}
    @param gold: The chunk structures to score the chunker on.
    @rtype: C{float}
    """

    gold_tags = []
    test_tags = []
    for gold_tree in gold:
        test_tree = chunker.parse(gold_tree.flatten())
        gold_tags += tree2conlltags(gold_tree)
        test_tags += tree2conlltags(test_tree)

#    print 'GOLD:', gold_tags[:50]
#    print 'TEST:', test_tags[:50]
    return _accuracy(gold_tags, test_tags)


# Patched for increased performance by Yoav Goldberg <yoavg@cs.bgu.ac.il>, 2006-01-13
#  -- statistics are evaluated only on demand, instead of at every sentence evaluation
#
# SB: use nltk.metrics for precision/recall scoring?
#
class ChunkScore(object):
    """
    A utility class for scoring chunk parsers.  C{ChunkScore} can
    evaluate a chunk parser's output, based on a number of statistics
    (precision, recall, f-measure, misssed chunks, incorrect chunks).
    It can also combine the scores from the parsing of multiple texts;
    this makes it signifigantly easier to evaluate a chunk parser that
    operates one sentence at a time.

    Texts are evaluated with the C{score} method.  The results of
    evaluation can be accessed via a number of accessor methods, such
    as C{precision} and C{f_measure}.  A typical use of the
    C{ChunkScore} class is::

        >>> chunkscore = ChunkScore()
        >>> for correct in correct_sentences:
        ...     guess = chunkparser.parse(correct.leaves())
        ...     chunkscore.score(correct, guess)
        >>> print 'F Measure:', chunkscore.f_measure()
        F Measure: 0.823

    @ivar kwargs: Keyword arguments:

        - max_tp_examples: The maximum number actual examples of true
          positives to record.  This affects the C{correct} member
          function: C{correct} will not return more than this number
          of true positive examples.  This does *not* affect any of
          the numerical metrics (precision, recall, or f-measure)

        - max_fp_examples: The maximum number actual examples of false
          positives to record.  This affects the C{incorrect} member
          function and the C{guessed} member function: C{incorrect}
          will not return more than this number of examples, and
          C{guessed} will not return more than this number of true
          positive examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)
        
        - max_fn_examples: The maximum number actual examples of false
          negatives to record.  This affects the C{missed} member
          function and the C{correct} member function: C{missed}
          will not return more than this number of examples, and
          C{correct} will not return more than this number of true
          negative examples.  This does *not* affect any of the
          numerical metrics (precision, recall, or f-measure)

        - chunk_node: A regular expression indicating which chunks
          should be compared.  Defaults to C{'.*'} (i.e., all chunks).
        
    @type _tp: C{list} of C{Token}
    @ivar _tp: List of true positives
    @type _fp: C{list} of C{Token}
    @ivar _fp: List of false positives
    @type _fn: C{list} of C{Token}
    @ivar _fn: List of false negatives
    
    @type _tp_num: C{int}
    @ivar _tp_num: Number of true positives
    @type _fp_num: C{int}
    @ivar _fp_num: Number of false positives
    @type _fn_num: C{int}
    @ivar _fn_num: Number of false negatives.
    """
    def __init__(self, **kwargs):
        self._correct = set()
        self._guessed = set()
        self._tp = set()
        self._fp = set()
        self._fn = set()
        self._max_tp = kwargs.get('max_tp_examples', 100)
        self._max_fp = kwargs.get('max_fp_examples', 100)
        self._max_fn = kwargs.get('max_fn_examples', 100)
        self._chunk_node = kwargs.get('chunk_node', '.*')
        self._tp_num = 0
        self._fp_num = 0
        self._fn_num = 0
        self._count = 0

        self._measuresNeedUpdate = False

    def _updateMeasures(self):
        if (self._measuresNeedUpdate):
           self._tp = self._guessed & self._correct
           self._fn = self._correct - self._guessed
           self._fp = self._guessed - self._correct
           self._tp_num = len(self._tp)
           self._fp_num = len(self._fp)
           self._fn_num = len(self._fn)
           self._measuresNeedUpdate = False

    def score(self, correct, guessed):
        """
        Given a correctly chunked sentence, score another chunked
        version of the same sentence.
        
        @type correct: chunk structure
        @param correct: The known-correct ("gold standard") chunked
            sentence.
        @type guessed: chunk structure
        @param guessed: The chunked sentence to be scored.
        """
        self._correct |= _chunksets(correct, self._count, self._chunk_node)
        self._guessed |= _chunksets(guessed, self._count, self._chunk_node)
        self._count += 1
        self._measuresNeedUpdate = True

    def precision(self):
        """
        @return: the overall precision for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        self._updateMeasures()
        div = self._tp_num + self._fp_num
        if div == 0: return 0
        else: return float(self._tp_num) / div
    
    def recall(self):
        """
        @return: the overall recall for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        """
        self._updateMeasures()
        div = self._tp_num + self._fn_num
        if div == 0: return 0
        else: return float(self._tp_num) / div
    
    def f_measure(self, alpha=0.5):
        """
        @return: the overall F measure for all texts that have been
            scored by this C{ChunkScore}.
        @rtype: C{float}
        
        @param alpha: the relative weighting of precision and recall.
            Larger alpha biases the score towards the precision value,
            while smaller alpha biases the score towards the recall
            value.  C{alpha} should have a value in the range [0,1].
        @type alpha: C{float}
        """
        self._updateMeasures()
        p = self.precision()
        r = self.recall()
        if p == 0 or r == 0:    # what if alpha is 0 or 1?
            return 0
        return 1/(alpha/p + (1-alpha)/r)
    
    def missed(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the
            correct chunk structures, but not in the guessed chunk
            structures, listed in input order.
        """
        self._updateMeasures()
        chunks = list(self._fn)
        return [c[1] for c in chunks]  # discard position information
    
    def incorrect(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the
            guessed chunk structures, but not in the correct chunk
            structures, listed in input order.
        """
        self._updateMeasures()
        chunks = list(self._fp)
        return [c[1] for c in chunks]  # discard position information
    
    def correct(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the correct
            chunk structures, listed in input order.
        """
        chunks = list(self._correct)
        return [c[1] for c in chunks]  # discard position information

    def guessed(self):
        """
        @rtype: C{list} of chunks
        @return: the chunks which were included in the guessed
            chunk structures, listed in input order.
        """
        chunks = list(self._guessed)
        return [c[1] for c in chunks]  # discard position information

    def __len__(self):
        self._updateMeasures()
        return self._tp_num + self._fn_num
    
    def __repr__(self):
        """
        @rtype: C{String}
        @return: a concise representation of this C{ChunkScoring}.
        """
        return '<ChunkScoring of '+`len(self)`+' chunks>'

    def __str__(self):
        """
        @rtype: C{String}
        @return: a verbose representation of this C{ChunkScoring}.
            This representation includes the precision, recall, and
            f-measure scores.  For other information about the score,
            use the accessor methods (e.g., C{missed()} and
            C{incorrect()}). 
        """
        return ("ChunkParse score:\n" +
                ("    Precision: %5.1f%%\n" % (self.precision()*100)) +
                ("    Recall:    %5.1f%%\n" % (self.recall()*100))+
                ("    F-Measure: %5.1f%%" % (self.f_measure()*100)))
        
# extract chunks, and assign unique id, the absolute position of
# the first word of the chunk
def _chunksets(t, count, chunk_node):
    pos = 0
    chunks = []
    for child in t:
        if isinstance(child, Tree):
            if re.match(chunk_node, child.node):
                chunks.append(((count, pos), tuple(child.freeze())))
            pos += len(child.leaves())
        else:
            pos += 1
    return set(chunks)


def tagstr2tree(s, chunk_node="NP", top_node="S", sep='/'):
    """
    Divide a string of bracketted tagged text into
    chunks and unchunked tokens, and produce a C{Tree}.
    Chunks are marked by square brackets (C{[...]}).  Words are
    delimited by whitespace, and each word should have the form
    C{I{text}/I{tag}}.  Words that do not contain a slash are
    assigned a C{tag} of C{None}.

    @return: A tree corresponding to the string representation.
    @rtype: C{tree}
    @param s: The string to be converted
    @type s: C{string}
    @param chunk_node: The label to use for chunk nodes
    @type chunk_node: C{string}
    @param top_node: The label to use for the root of the tree
    @type top_node: C{string}
    """

    WORD_OR_BRACKET = re.compile(r'\[|\]|[^\[\]\s]+')

    stack = [Tree(top_node, [])]
    for match in WORD_OR_BRACKET.finditer(s):
        text = match.group()
        if text[0] == '[':
            if len(stack) != 1:
                raise ValueError('Unexpected [ at char %d' % match.start())
            chunk = Tree(chunk_node, [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif text[0] == ']':
            if len(stack) != 2:
                raise ValueError('Unexpected ] at char %d' % match.start())
            stack.pop()
        else:
            if sep is None:
                stack[-1].append(text)
            else:
                stack[-1].append(nltk.tag.util.str2tuple(text, sep))

    if len(stack) != 1:
        raise ValueError('Expected ] at char %d' % len(s))
    return stack[0]

### CONLL

_LINE_RE = re.compile('(\S+)\s+(\S+)\s+([IOB])-?(\S+)?')
def conllstr2tree(s, chunk_types=('NP', 'PP', 'VP'), top_node="S"):
    """
    Convert a CoNLL IOB string into a tree.  Uses the specified chunk types
    (defaults to NP, PP and VP), and creates a tree rooted at a node
    labeled S (by default).

    @param s: The CoNLL string to be converted.
    @type s: C{string}
    @param chunk_types: The chunk types to be converted.
    @type chunk_types: C{tuple}
    @param top_node: The node label to use for the root.
    @type top_node: C{string}
    @return: A chunk structure for a single sentence
        encoded in the given CONLL 2000 style string.
    @rtype: L{Tree}
    """

    stack = [Tree(top_node, [])]

    for lineno, line in enumerate(s.split('\n')):
        if not line.strip(): continue

        # Decode the line.
        match = _LINE_RE.match(line)
        if match is None:
            raise ValueError, 'Error on line %d' % lineno
        (word, tag, state, chunk_type) = match.groups()

        # If it's a chunk type we don't care about, treat it as O.
        if (chunk_types is not None and
            chunk_type not in chunk_types):
            state = 'O'

        # For "Begin"/"Outside", finish any completed chunks -
        # also do so for "Inside" which don't match the previous token.
        mismatch_I = state == 'I' and chunk_type != stack[-1].node
        if state in 'BO' or mismatch_I:
            if len(stack) == 2: stack.pop()

        # For "Begin", start a new chunk.
        if state == 'B' or mismatch_I:
            chunk = Tree(chunk_type, [])
            stack[-1].append(chunk)
            stack.append(chunk)

        # Add the new word token.
        stack[-1].append((word, tag))

    return stack[0]

def tree2conlltags(t):
    """
    Convert a tree to the CoNLL IOB tag format

    @param t: The tree to be converted.
    @type t: C{Tree}
    @return: A list of 3-tuples containing word, tag and IOB tag.
    @rtype: C{list} of C{tuple}
    """

    tags = []
    for child in t:
        try:
            category = child.node
            prefix = "B-"
            for contents in child:
                if isinstance(contents, Tree):
                    raise ValueError, "Tree is too deeply nested to be printed in CoNLL format"
                tags.append((contents[0], contents[1], prefix+category))
                prefix = "I-"
        except AttributeError:
            tags.append((child[0], child[1], "O"))
    return tags

def tree2conllstr(t):
    """
    Convert a tree to the CoNLL IOB string format

    @param t: The tree to be converted.
    @type t: C{Tree}
    @return: A multiline string where each line contains a word, tag and IOB tag.
    @rtype: C{string}
    """
    lines = [string.join(token) for token in tree2conlltags(t)]
    return '\n'.join(lines)

### IEER

_IEER_DOC_RE = re.compile(r'<DOC>\s*'
                          r'(<DOCNO>\s*(?P<docno>.+?)\s*</DOCNO>\s*)?'
                          r'(<DOCTYPE>\s*(?P<doctype>.+?)\s*</DOCTYPE>\s*)?'
                          r'(<DATE_TIME>\s*(?P<date_time>.+?)\s*</DATE_TIME>\s*)?'
                          r'<BODY>\s*'
                          r'(<HEADLINE>\s*(?P<headline>.+?)\s*</HEADLINE>\s*)?'
                          r'<TEXT>(?P<text>.*?)</TEXT>\s*'
                          r'</BODY>\s*</DOC>\s*', re.DOTALL)

_IEER_TYPE_RE = re.compile('<b_\w+\s+[^>]*?type="(?P<type>\w+)"')

def _ieer_read_text(s, top_node):
    stack = [Tree(top_node, [])]
    # s will be None if there is no headline in the text
    # return the empty list in place of a Tree
    if s is None:
        return []
    for piece_m in re.finditer('<[^>]+>|[^\s<]+', s):
        piece = piece_m.group()
        try:
            if piece.startswith('<b_'):
                m = _IEER_TYPE_RE.match(piece)
                if m is None: print 'XXXX', piece
                chunk = Tree(m.group('type'), [])
                stack[-1].append(chunk)
                stack.append(chunk)
            elif piece.startswith('<e_'):
                stack.pop()
#           elif piece.startswith('<'):
#               print "ERROR:", piece
#               raise ValueError # Unexpected HTML
            else:
                stack[-1].append(piece)
        except (IndexError, ValueError):
            raise ValueError('Bad IEER string (error at character %d)' %
                             piece_m.start())
    if len(stack) != 1:
        raise ValueError('Bad IEER string')
    return stack[0]

def ieerstr2tree(s, chunk_types = ['LOCATION', 'ORGANIZATION', 'PERSON', 'DURATION',
               'DATE', 'CARDINAL', 'PERCENT', 'MONEY', 'MEASURE'], top_node="S"):
    """
    Convert a string of chunked tagged text in the IEER named
    entity format into a chunk structure.  Chunks are of several
    types, LOCATION, ORGANIZATION, PERSON, DURATION, DATE, CARDINAL,
    PERCENT, MONEY, and MEASURE.

    @return: A chunk structure containing the chunked tagged text that is
        encoded in the given IEER style string.
    @rtype: L{Tree}
    """

    # Try looking for a single document.  If that doesn't work, then just
    # treat everything as if it was within the <TEXT>...</TEXT>.
    m = _IEER_DOC_RE.match(s)
    if m:
        return {
            'text': _ieer_read_text(m.group('text'), top_node),
            'docno': m.group('docno'),
            'doctype': m.group('doctype'),
            'date_time': m.group('date_time'),
            #'headline': m.group('headline')
            # we want to capture NEs in the headline too!
            'headline': _ieer_read_text(m.group('headline'), top_node),
            }
    else:
        return _ieer_read_text(s, top_node)


def demo():

    s = "[ Pierre/NNP Vinken/NNP ] ,/, [ 61/CD years/NNS ] old/JJ ,/, will/MD join/VB [ the/DT board/NN ] ./."
    from nltk import chunk
    t = chunk.tagstr2tree(s, chunk_node='NP')
    print t.pprint()
    print

    s = """
These DT B-NP
research NN I-NP
protocols NNS I-NP
offer VBP B-VP
to TO B-PP
the DT B-NP
patient NN I-NP
not RB O
only RB O
the DT B-NP
very RB I-NP
best JJS I-NP
therapy NN I-NP
which WDT B-NP
we PRP B-NP
have VBP B-VP
established VBN I-VP
today NN B-NP
but CC B-NP
also RB I-NP
the DT B-NP
hope NN I-NP
of IN B-PP
something NN B-NP
still RB B-ADJP
better JJR I-ADJP
. . O
"""

    conll_tree = conllstr2tree(s, chunk_types=('NP', 'PP'))
    print conll_tree.pprint()

    # Demonstrate CoNLL output
    print "CoNLL output:"
    print chunk.tree2conllstr(conll_tree)
    print


if __name__ == '__main__':
    demo()


# Natural Language Toolkit: Chunk format conversions
#
# Copyright (C) 2001-2006 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor additions)
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk_lite.chunk import *
from nltk_lite import tokenize
from nltk_lite.parse.tree import Tree
import re

def tagstr2tree(s, chunk_node="NP", top_node="S"):
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
    VALID = re.compile(r'^([^\[\]]+|\[[^\[\]]*\])*$')

    if not VALID.match(s):
        raise ValueError, 'Invalid token string (bad brackets)'
        
    stack = [Tree(top_node, [])]
    for match in WORD_OR_BRACKET.finditer(s):
        text = match.group()
        if text[0] == '[':
            chunk = Tree(chunk_node, [])
            stack[-1].append(chunk)
            stack.append(chunk)
        elif text[0] == ']':
            stack.pop()
        else:
            slash = text.rfind('/')
            if slash >= 0:
                tok = (text[:slash], text[slash+1:])
            else:
                tok = (text, None)
            stack[-1].append(tok)

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
    @type chunk_types: C{string}
    @return: A chunk structure for a single sentence
        encoded in the given CONLL 2000 style string.
    @rtype: L{Tree}
    """

    stack = [Tree(top_node, [])]

    for lineno, line in enumerate(tokenize.line(s)):

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
    lines = [' '.join(token) for token in tree2conlltags(t)]
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
            'headline': m.group('headline')
            }
    else:
        return _ieer_read_text(s, top_node)


def demo():

    s = "[ Pierre/NNP Vinken/NNP ] ,/, [ 61/CD years/NNS ] old/JJ ,/, will/MD join/VB [ the/DT board/NN ] ./."
    from nltk_lite import chunk
    t = chunk.tagstr2tree(s, chunk_node='NP')
    print t.pp()
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
    print conll_tree.pp()

    # Demonstrate CoNLL output
    print "CoNLL output:"
    print chunk.tree2conllstr(conll_tree)
    print


if __name__ == '__main__':
    demo()


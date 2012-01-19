# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2012 NLTK Project
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://www.nltk.org/>
# For license information, see LICENSE.TXT
"""
Corpus reader for corpora that consist of parenthesis-delineated parse trees.
"""

import sys

from nltk.tree import Tree

from util import *
from api import *


# we use [^\s()]+ instead of \S+? to avoid matching ()
TAGWORD = re.compile(r'\(([^\s()]+) ([^\s()]+)\)')
WORD = re.compile(r'\([^\s()]+ ([^\s()]+)\)')
EMPTY_BRACKETS = re.compile(r'\s*\(\s*\(')

class BracketParseCorpusReader(SyntaxCorpusReader):
    """
    Reader for corpora that consist of parenthesis-delineated parse
    trees.
    """
    def __init__(self, root, fileids, comment_char=None,
                 detect_blocks='unindented_paren', encoding=None,
                 tag_mapping_function=None):
        """
        :param root: The root directory for this corpus.
        :param fileids: A list or regexp specifying the fileids in this corpus.
        :param comment_char: The character which can appear at the start of
            a line to indicate that the rest of the line is a comment.
        :param detect_blocks: The method that is used to find blocks
          in the corpus; can be 'unindented_paren' (every unindented
          parenthesis starts a new parse) or 'sexpr' (brackets are
          matched).
        """
        CorpusReader.__init__(self, root, fileids, encoding)
        self._comment_char = comment_char
        self._detect_blocks = detect_blocks
        self._tag_mapping_function = tag_mapping_function

    def _read_block(self, stream):
        if self._detect_blocks == 'sexpr':
            return read_sexpr_block(stream, comment_char=self._comment_char)
        elif self._detect_blocks == 'blankline':
            return read_blankline_block(stream)
        elif self._detect_blocks == 'unindented_paren':
            # Tokens start with unindented left parens.
            toks = read_regexp_block(stream, start_re=r'^\(')
            # Strip any comments out of the tokens.
            if self._comment_char:
                toks = [re.sub('(?m)^%s.*'%re.escape(self._comment_char),
                               '', tok)
                        for tok in toks]
            return toks
        else:
            assert 0, 'bad block type'

    def _normalize(self, t):
        # If there's an empty set of brackets surrounding the actual
        # parse, then strip them off.
        if EMPTY_BRACKETS.match(t):
            t = t.strip()[1:-1]
        # Replace leaves of the form (!), (,), with (! !), (, ,)
        t = re.sub(r"\((.)\)", r"(\1 \1)", t)
        # Replace leaves of the form (tag word root) with (tag word)
        t = re.sub(r"\(([^\s()]+) ([^\s()]+) [^\s()]+\)", r"(\1 \2)", t)
        return t

    def _parse(self, t):
        try:
            return Tree.parse(self._normalize(t))

        except ValueError, e:
            sys.stderr.write("Bad tree detected; trying to recover...\n")
            # Try to recover, if we can:
            if e.args == ('mismatched parens',):
                for n in range(1, 5):
                    try:
                        v = Tree.parse(self._normalize(t+')'*n))
                        sys.stderr.write("  Recovered by adding %d close "
                                         "paren(s)\n" % n)
                        return v
                    except ValueError: pass
            # Try something else:
            sys.stderr.write("  Recovered by returning a flat parse.\n")
            #sys.stderr.write(' '.join(t.split())+'\n')
            return Tree('S', self._tag(t))

    def _tag(self, t, simplify_tags=False):
        tagged_sent = [(w,t) for (t,w) in TAGWORD.findall(self._normalize(t))]
        if simplify_tags:
            tagged_sent = [(w, self._tag_mapping_function(t))
                           for (w,t) in tagged_sent]
        return tagged_sent

    def _word(self, t):
        return WORD.findall(self._normalize(t))

class AlpinoCorpusReader(BracketParseCorpusReader):
    """
    Reader for the Alpino Dutch Treebank.
    """
    def __init__(self, root, encoding=None, tag_mapping_function=None):
        BracketParseCorpusReader.__init__(self, root, 'alpino\.xml',
                                 detect_blocks='blankline',
                                 encoding=encoding,
                                 tag_mapping_function=tag_mapping_function)

    def _normalize(self, t):
        if t[:10] != "<alpino_ds":
            return ""
        # convert XML to sexpr notation
        t = re.sub(r'  <node .*? cat="(\w+)".*>', r"(\1", t)
        t = re.sub(r'  <node .*? pos="(\w+)".*? word="([^"]+)".*/>', r"(\1 \2)", t)
        t = re.sub(r"  </node>", r")", t)
        t = re.sub(r"<sentence>.*</sentence>", r"", t)
        t = re.sub(r"</?alpino_ds.*>", r"", t)
        return t

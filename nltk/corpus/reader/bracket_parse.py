# Natural Language Toolkit: Penn Treebank Reader
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Steven Bird <sb@ldc.upenn.edu>
#         Edward Loper <edloper@gradient.cis.upenn.edu>
# URL: <http://nltk.sf.net>
# For license information, see LICENSE.TXT

from nltk.corpus.reader.util import *
from nltk.corpus.reader.api import *
from nltk.tree import bracket_parse, Tree
import os.path, sys

"""
Corpus reader for corpora that consist of parenthesis-delineated parse trees.
"""

TAGWORD = re.compile(r'\((\S+?) (\S+?)\)')
WORD = re.compile(r'\(\S+? (\S+?)\)')
EMPTY_BRACKETS = re.compile(r'\s*\(\s*\(')

class BracketParseCorpusReader(SyntaxCorpusReader):
    """
    Reader for corpora that consist of parenthesis-delineated parse
    trees.
    """
    def __init__(self, root, items, extension='', comment_char=None,
                 detect_blocks='sexpr'):
        """
        @param root: The root directory for this corpus.
        @param items: A list of items in this corpus.
        @param extension: File extension for items in this corpus.
        @param comment: The character which can appear at the start of a line to
          indicate that the rest of the line is a comment.
        @param detect_blocks: The method that is used to find blocks
          in the corpus; can be 'unindented_parens' (every unindented
          parenthasis starts a new parse) or 'sexpr' (brackets are
          matched).
        """
        if isinstance(items, basestring):
            items = find_corpus_items(root, items, extension)
        self._root = root
        self.items = tuple(items)
        self._extension = extension
        self._comment_char = comment_char
        self._detect_blocks = detect_blocks

    def _read_block(self, stream):
        if self._detect_blocks == 'sexpr':
            return read_sexpr_block(stream, comment_char=self._comment_char)
        elif self._detect_blocks == 'unindented_paren':
            # Tokens start with unindented left parens.
            toks = read_regexp_block(stream, start_re=r'^\(')
            # Strip any comments out of the tokens.
            toks = [re.sub('(?m)^%s.*'%re.escape(self._comment_char), '', tok)
                    for tok in toks]
            return toks
        else:
            assert 0, 'bad block type'
    
# low-level string processing
    
    def _normalize(self, t):
        # If there's an empty set of brackets surrounding the actual
        # parse, then strip them off.
        if EMPTY_BRACKETS.match(t):
            t = t.strip()[1:-1]
        # Replace any punctuation leaves of the form (!), (,), with (! !), (, ,)
        t = re.sub(r"\((.)\)", r"(\1 \1)", t)
        return t

    def _parse(self, t):
        try:
            return bracket_parse(self._normalize(t))
        except ValueError, e:
            sys.stderr.write("Bad tree detected; trying to recover...\n")
            # Try to recover, if we can:
            if e.args == ('mismatched parens',):
                for n in range(1, 5):
                    try:
                        v = bracket_parse(self._normalize(t+')'*n))
                        sys.stderr.write("  Recovered by adding %d close "
                                         "paren(s)\n" % n)
                        return v
                    except ValueError: pass
            # Try something else:
            sys.stderr.write("  Recovered by returning a flat parse.\n")
            #sys.stderr.write(' '.join(t.split())+'\n')
            return Tree('S', self._tag(t))

    def _tag(self, t):
        return [(w,t) for (t,w) in TAGWORD.findall(self._normalize(t))]

    def _word(self, t):
        return WORD.findall(self._normalize(t))

# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2011 NLTK Project
# Author: Yoav Goldberg <yoavg@cs.bgu.ac.il>
#         Steven Bird <sb@csse.unimelb.edu.au> (minor edits)
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
S-Expression Tokenizer

``SExprTokenizer`` is used to find parenthesized expressions in a
string.  In particular, it divides a string into a sequence of
substrings that are either parenthesized expressions (including any
nested parenthesized expressions), or other whitespace-separated
tokens.

    >>> SExprTokenizer().tokenize('(a b (c d)) e f (g)')
    ['(a b (c d))', 'e', 'f', '(g)']

By default, `SExprTokenizer` will raise a ``ValueError`` exception if
used to tokenize an expression with non-matching parentheses:

    >>> SExprTokenizer().tokenize('c) d) e (f (g')
    Traceback (most recent call last):
      ...
    ValueError: Un-matched close paren at char 1

The ``strict`` argument can be set to False to allow for
non-matching parentheses.  Any unmatched close parentheses will be
listed as their own s-expression; and the last partial sexpr with
unmatched open parentheses will be listed as its own sexpr:

    >>> SExprTokenizer(strict=False).tokenize('c) d) e (f (g')
    ['c', ')', 'd', ')', 'e', '(f (g']

The characters used for open and close parentheses may be customized
using the ``parens`` argument to the `SExprTokenizer` constructor:

    >>> SExprTokenizer(parens='{}').tokenize('{a b {c d}} e f {g}')
    ['{a b {c d}}', 'e', 'f', '{g}']

The s-expression tokenizer is also available as a function:

    >>> sexpr_tokenize('(a b (c d)) e f (g)')
    ['(a b (c d))', 'e', 'f', '(g)']

"""

import re

from .api import TokenizerI

class SExprTokenizer(TokenizerI):
    """
    A tokenizer that divides strings into s-expressions.
    An s-expresion can be either:
   
      - a parenthesized expression, including any nested parenthesized
        expressions, or
      - a sequence of non-whitespace non-parenthesis characters.
    
    For example, the string ``(a (b c)) d e (f)`` consists of four
    s-expressions: ``(a (b c))``, ``d``, ``e``, and ``(f)``.  

    By default, the characters ``(`` and ``)`` are treated as open and
    close parentheses, but alternative strings may be specified.

    :param parens: A two-element sequence specifying the open and close parentheses
        that should be used to find sexprs.  This will typically be either a
        two-character string, or a list of two strings.
    :type parens: C{str} or C{list}
    :param strict: If true, then raise an exception when tokenizing an ill-formed sexpr.
    """

    def __init__(self, parens='()', strict=True):
        if len(parens) != 2:
            raise ValueError('parens must contain exactly two strings')
        self._strict = strict
        self._open_paren = parens[0]
        self._close_paren = parens[1]
        self._paren_regexp = re.compile('%s|%s' % (re.escape(parens[0]),
                                                   re.escape(parens[1])))
    
    def tokenize(self, text):
        """
        Return a list of s-expressions extracted from *text*.
        For example:
    
            >>> SExprTokenizer().tokenize('(a b (c d)) e f (g)')
            ['(a b (c d))', 'e', 'f', '(g)']

        All parentheses are assumed to mark s-expressions.
        (No special processing is done to exclude parentheses that occur
        inside strings, or following backslash characters.)

        If the given expression contains non-matching parentheses,
        then the behavior of the tokenizer depends on the C{strict}
        parameter to the constructor.  If C{strict} is C{True}, then
        raise a C{ValueError}.  If C{strict} is C{False}, then any
        unmatched close parentheses will be listed as their own
        s-expression; and the last partial s-expression with unmatched open
        parentheses will be listed as its own s-expression:

            >>> SExprTokenizer(strict=False).tokenize('c) d) e (f (g')
            ['c', ')', 'd', ')', 'e', '(f (g']
        
        :param text: the string to be tokenized
        :type text: str or iter(str)
        :rtype: iter(str)
        """
        result = []
        pos = 0
        depth = 0
        for m in self._paren_regexp.finditer(text):
            paren = m.group()
            if depth == 0:
                result += text[pos:m.start()].split()
                pos = m.start()
            if paren == self._open_paren:
                depth += 1
            if paren == self._close_paren:
                if self._strict and depth == 0:
                    raise ValueError('Un-matched close paren at char %d'
                                     % m.start())
                depth = max(0, depth-1)
                if depth == 0:
                    result.append(text[pos:m.end()])
                    pos = m.end()
        if self._strict and depth > 0:
            raise ValueError('Un-matched open paren at char %d' % pos)
        if pos < len(text):
            result.append(text[pos:])
        return result

sexpr_tokenize = SExprTokenizer().tokenize

def demo():
    from nltk import tokenize

    example = "d (d ((e) ((f) ss) a a c) d) r (t i) (iu a"
    example = "d [d [[e] [[f] ss] a a c] d] r [t i]"
    print 'Input text:'
    print example
    print
    print 'Tokenize s-expressions:'
    for x in SExprTokenizer('[]').tokenize(example):
        print x

if __name__ == '__main__':
    demo()

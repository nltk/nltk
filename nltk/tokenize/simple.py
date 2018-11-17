# Natural Language Toolkit: Simple Tokenizers
#
# Copyright (C) 2001-2019 NLTK Project
# Author: Edward Loper <edloper@gmail.com>
#         Steven Bird <stevenbird1@gmail.com>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

r"""
Simple Tokenizers

These tokenizers divide strings into substrings using the string
``split()`` method.
When tokenizing using a particular delimiter string, use
the string ``split()`` method directly, as this is more efficient.

The simple tokenizers are *not* available as separate functions;
instead, you should just use the string ``split()`` method directly:

    >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
    >>> s.split()
    ['Good', 'muffins', 'cost', '$3.88', 'in', 'New', 'York.',
    'Please', 'buy', 'me', 'two', 'of', 'them.', 'Thanks.']
    >>> s.split(' ')
    ['Good', 'muffins', 'cost', '$3.88\nin', 'New', 'York.', '',
    'Please', 'buy', 'me\ntwo', 'of', 'them.\n\nThanks.']
    >>> s.split('\n')
    ['Good muffins cost $3.88', 'in New York.  Please buy me',
    'two of them.', '', 'Thanks.']

The simple tokenizers are mainly useful because they follow the
standard ``TokenizerI`` interface, and so can be used with any code
that expects a tokenizer.  For example, these tokenizers can be used
to specify the tokenization conventions when building a `CorpusReader`.

"""
from __future__ import unicode_literals
from nltk.tokenize.api import TokenizerI, StringTokenizer
from nltk.tokenize.util import string_span_tokenize, regexp_span_tokenize


class SpaceTokenizer(StringTokenizer):
    r"""Tokenize a string using the space character as a delimiter,
    which is the same as ``s.split(' ')``.

        >>> from nltk.tokenize import SpaceTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> SpaceTokenizer().tokenize(s)
        ['Good', 'muffins', 'cost', '$3.88\nin', 'New', 'York.', '',
        'Please', 'buy', 'me\ntwo', 'of', 'them.\n\nThanks.']
    """

    _string = ' '


class TabTokenizer(StringTokenizer):
    r"""Tokenize a string use the tab character as a delimiter,
    the same as ``s.split('\t')``.

        >>> from nltk.tokenize import TabTokenizer
        >>> TabTokenizer().tokenize('a\tb c\n\t d')
        ['a', 'b c\n', ' d']
    """

    _string = '\t'


class CharTokenizer(StringTokenizer):
    """Tokenize a string into individual characters.  If this functionality
    is ever required directly, use ``for char in string``.
    """

    def tokenize(self, s):
        return list(s)

    def span_tokenize(self, s):
        for i, j in enumerate(range(1, len(s) + 1)):
            yield i, j


class LineTokenizer(TokenizerI):
    r"""Tokenize a string into its lines, optionally discarding blank lines.
    This is similar to ``s.split('\n')``.

        >>> from nltk.tokenize import LineTokenizer
        >>> s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
        >>> LineTokenizer(blanklines='keep').tokenize(s)
        ['Good muffins cost $3.88', 'in New York.  Please buy me',
        'two of them.', '', 'Thanks.']
        >>> # same as [l for l in s.split('\n') if l.strip()]:
        >>> LineTokenizer(blanklines='discard').tokenize(s)
        ['Good muffins cost $3.88', 'in New York.  Please buy me',
        'two of them.', 'Thanks.']

    :param blanklines: Indicates how blank lines should be handled.  Valid values are:

        - ``discard``: strip blank lines out of the token list before returning it.
           A line is considered blank if it contains only whitespace characters.
        - ``keep``: leave all blank lines in the token list.
        - ``discard-eof``: if the string ends with a newline, then do not generate
           a corresponding token ``''`` after that newline.
    """

    def __init__(self, blanklines='discard'):
        valid_blanklines = ('discard', 'keep', 'discard-eof')
        if blanklines not in valid_blanklines:
            raise ValueError(
                'Blank lines must be one of: %s' % ' '.join(valid_blanklines)
            )

        self._blanklines = blanklines

    def tokenize(self, s):
        lines = s.splitlines()
        # If requested, strip off blank lines.
        if self._blanklines == 'discard':
            lines = [l for l in lines if l.rstrip()]
        elif self._blanklines == 'discard-eof':
            if lines and not lines[-1].strip():
                lines.pop()
        return lines

    # discard-eof not implemented
    def span_tokenize(self, s):
        if self._blanklines == 'keep':
            for span in string_span_tokenize(s, r'\n'):
                yield span
        else:
            for span in regexp_span_tokenize(s, r'\n(\s+\n)*'):
                yield span


######################################################################
# { Tokenization Functions
######################################################################
# XXX: it is stated in module docs that there is no function versions


def line_tokenize(text, blanklines='discard'):
    return LineTokenizer(blanklines).tokenize(text)

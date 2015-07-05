# coding: utf-8
#
# Natural Language Toolkit: Twitter Tokenizer
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Christopher Potts <cgpotts@stanford.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk> (modifications)
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT
#


"""
Twitter-aware tokenizer, designed to be flexible and easy to adapt to new
domains and tasks. The basic logic is this:

1. The tuple regex_strings defines a list of regular expression
   strings.

2. The regex_strings strings are put, in order, into a compiled
   regular expression object called word_re.

3. The tokenization is done by word_re.findall(s), where s is the
   user-supplied string, inside the tokenize() method of the class
   Tokenizer.

4. When instantiating Tokenizer objects, there is a single option:
   preserve_case.  By default, it is set to True. If it is set to
   False, then the tokenizer will downcase everything except for
   emoticons.

"""



######################################################################

from __future__ import unicode_literals
import re
from nltk.compat import htmlentitydefs, int2byte, unichr


######################################################################
# The following strings are components in the regular expression
# that is used for tokenizing. It's important that phone_number
# appears first in the final regex (since it can contain whitespace).
# It also could matter that tags comes after emoticons, due to the
# possibility of having text like
#
#     <:| and some text >:)
#
# Most importantly, the final element should always be last, since it
# does a last ditch whitespace-based tokenization of whatever is left.

# ToDo: Update with http://en.wikipedia.org/wiki/List_of_emoticons ?

# This particular element is used in a couple ways, so we define it
# with a name:
EMOTICONS = r"""
    (?:
      [<>]?
      [:;=8]                     # eyes
      [\-o\*\']?                 # optional nose
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      |
      [\)\]\(\[dDpP/\:\}\{@\|\\] # mouth
      [\-o\*\']?                 # optional nose
      [:;=8]                     # eyes
      [<>]?
      |
      <3                         # heart
    )"""

# URL pattern due to John Gruber, modified by Tom Winzig. See
# https://gist.github.com/winzig/8894715

URLS = r"""			# Capture 1: entire matched URL
  (?:
  https?:				# URL protocol and colon
    (?:
      /{1,3}				# 1-3 slashes
      |					#   or
      [a-z0-9%]				# Single letter or digit or '%'
                                       # (Trying not to match e.g. "URI::Escape")
    )
    |					#   or
                                       # looks like domain name followed by a slash:
    [a-z0-9.\-]+[.]
    (?:[a-z]{2,13})
    /
  )
  (?:					# One or more:
    [^\s()<>{}\[\]]+			# Run of non-space, non-()<>{}[]
    |					#   or
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\) # balanced parens, one level deep: (...(...)...)
    |
    \([^\s]+?\)				# balanced parens, non-recursive: (...)
  )+
  (?:					# End with:
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\) # balanced parens, one level deep: (...(...)...)
    |
    \([^\s]+?\)				# balanced parens, non-recursive: (...)
    |					#   or
    [^\s`!()\[\]{};:'".,<>?«»“”‘’]	# not a space or one of these punct chars
  )
  |					# OR, the following to match naked domains:
  (?:
  	(?<!@)			        # not preceded by a @, avoid matching foo@_gmail.com_
    [a-z0-9]+
    (?:[.\-][a-z0-9]+)*
    [.]
    (?:[a-z]{2,13})
    \b
    /?
    (?!@)			        # not succeeded by a @, avoid matching "foo.na" in "foo.na@example.com"
  )
"""

# The components of the tokenizer:
REGEXPS = (
    URLS,
    # Phone numbers:
    r"""
    (?:
      (?:            # (international)
        \+?[01]
        [\-\s.]*
      )?
      (?:            # (area code)
        [\(]?
        \d{3}
        [\-\s.\)]*
      )?
      \d{3}          # exchange
      [\-\s.]*
      \d{4}          # base
    )"""
    ,
    # ASCII Emoticons
    EMOTICONS
    ,
    # HTML tags:
    r"""<[^>\s]+>"""
    ,
    # ASCII Arrows
    r"""[\-]+>|<[\-]+"""
    ,
    # Twitter username:
    r"""(?:@[\w_]+)"""
    ,
    # Twitter hashtags:
    r"""(?:\#+[\w_]+[\w\'_\-]*[\w_]+)"""
    ,

    # Remaining word types:
    r"""
    (?:[a-z][a-z'\-_]+[a-z])       # Words with apostrophes or dashes.
    |
    (?:[+\-]?\d+[,/.:-]\d+[+\-]?)  # Numbers, including fractions, decimals.
    |
    (?:[\w_]+)                     # Words without apostrophes or dashes.
    |
    (?:\.(?:\s*\.){1,})            # Ellipsis dots.
    |
    (?:\S)                         # Everything else that isn't whitespace.
    """
    )

######################################################################
# This is the core tokenizing regex:

WORD_RE = re.compile(r"""(%s)""" % "|".join(REGEXPS), re.VERBOSE | re.I
                     | re.UNICODE)

# The emoticon string gets its own regex so that we can preserve case for
# them as needed:
EMOTICON_RE = re.compile(EMOTICONS, re.VERBOSE | re.I | re.UNICODE)

# These are for regularizing HTML entities to Unicode:
_ent_re = re.compile(r'&(#?(x?))([^&;\s]+);')


######################################################################
# Functions for converting html entities
######################################################################

def _str_to_unicode(text, encoding=None, errors='strict'):
    if encoding is None:
        encoding = 'utf-8'
    if isinstance(text, bytes):
        return text.decode(encoding, errors)
    return text

def _replace_html_entities(text, keep=(), remove_illegal=True, encoding='utf-8'):
    u"""Remove entities from the given `text` by converting them to their
    corresponding unicode character.
    `text` can be a unicode string or a byte string encoded in the given
    `encoding` (which defaults to 'utf-8').
    If `keep` is passed (with a list of entity names) those entities will
    be kept (they won't be removed).
    It supports both numeric entities (``&#nnnn;`` and ``&#hhhh;``)
    and named entities (such as ``&nbsp;`` or ``&gt;``).
    If `remove_illegal` is ``True``, entities that can't be converted are removed.
    If `remove_illegal` is ``False``, entities that can't be converted are kept "as
    is". For more information see the tests.
    Always returns a unicode string (with the entities removed).
    """

    def convert_entity(m):
        entity_body = m.group(3)
        if m.group(1):
            try:
                if m.group(2):
                    number = int(entity_body, 16)
                else:
                    number = int(entity_body, 10)
                # Numeric character references in the 80-9F range are typically
                # interpreted by browsers as representing the characters mapped
                # to bytes 80-9F in the Windows-1252 encoding. For more info
                # see: http://en.wikipedia.org/wiki/Character_encodings_in_HTML
                if 0x80 <= number <= 0x9f:
                    return int2byte(number).decode('cp1252')
            except ValueError:
                number = None
        else:
            if entity_body in keep:
                return m.group(0)
            else:
                number = htmlentitydefs.name2codepoint.get(entity_body)
        if number is not None:
            try:
                return unichr(number)
            except ValueError:
                pass

        return u'' if remove_illegal else m.group(0)

    return _ent_re.sub(convert_entity, _str_to_unicode(text, encoding))


######################################################################

class TweetTokenizer:
    """Tokenize Tweets"""
    def __init__(self, preserve_case=True, normalize=False):
        self.preserve_case = preserve_case
        self.normalize = normalize

    def tokenize(self, text):
        """
        :param s: str
        :rtype: list(str)
        :return: a tokenized list of strings; concatenating this list returns
        the original string if preserve_case=False
        """
        # Fix HTML character entities:
        text = _replace_html_entities(text)
        if self.normalize:
          text = normalize(text)
        # Tokenize:
        words = WORD_RE.findall(text)
        # Possibly alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:
            words = list(map((lambda x : x if EMOTICON_RE.search(x) else
                              x.lower()), words))
        return words

######################################################################
# Normalization Functions
######################################################################

def normalize(text, reduce_length=True):
    if reduce_length:
      text = _reduce_length(text)
    return text

def _reduce_length(text):
    '''
    Replace character sequences of length 3 or greater with sequences of length 3
    '''
    pattern = re.compile(r"(.)\1{2,}")
    return pattern.sub(r"\1\1\1", text)

######################################################################
# Tokenization Function
######################################################################

def casual_tokenize(text, preserve_case=True, normalize=True):
    """
    Convenience function for wrapping the tokenizer.
    """
    return TweetTokenizer(preserve_case=preserve_case, normalize=normalize).tokenize(text)

###############################################################################

if __name__ == '__main__':
    s0 = "This is a cooool #dummysmiley: :-) :-P <3 and some arrows < > -> <--"
    s1 = "Naps are a must \ud83d\ude34\ud83d\ude34"
    s2 = "Renato fica com muito medo de ouvir meus \u00e1udios perto da gaja\
    dele, pois s\u00f3 falo merda KKK"
    s3 = "\u0412\u043b\u0430\u0434\u0435\u043b\u0435\u0446 20th Century Fox\
    \u043d\u0430\u043c\u0435\u0440\u0435\u043d\
    \u043a\u0443\u043f\u0438\u0442\u044c Warner Bros."
    s4 = "RT @facugambande: Ya por arrancar a grabar !!! #TirenTirenTiren vamoo !!"
    s5 = "http://t.co/7r8d5bVKyA http://t.co/hZpwZe1uKt\
    http://t.co/ZKb7GKWocy Ничто так не сближает\
    людей"
    s6 = "These words are waaaaay toooo loooooong for a tokenizer! :P"

    t0 = ['This', 'is', 'a', 'cooool', '#dummysmiley', ':', ':-)', ':-P',\
          '<3', 'and', 'some', 'arrows', '<', '>', '->', '<--']
    t1 = ['Naps', 'are', 'a', 'must', '\ud83d', '\ude34', '\ud83d', '\ude34']
    t2 = ['Renato', 'fica', 'com', 'muito', 'medo', 'de', 'ouvir', 'meus',
          'áudios', 'perto', 'da', 'gaja', 'dele', ',', 'pois', 'só', 'falo',
          'merda', 'KKK']
    t3 = ['Владелец', '20th', 'Century', 'Fox', 'намерен',
          'купить', 'Warner', 'Bros', '.']
    t4 = ['RT', '@facugambande', ':', 'Ya', 'por', 'arrancar', 'a', 'grabar',
          '!', '!', '!', '#TirenTirenTiren', 'vamoo', '!', '!']
    t5 = ['http://t.co/7r8d5bVKyA', 'http://t.co/hZpwZe1uKt',
          'http://t.co/ZKb7GKWocy', 'Ничто', 'так', 'не',
          'сближает', 'людей']
    t6 = ['These', 'words', 'are', 'waaay', 'tooo', 'looong', 'for', 'a',
          'tokenizer', '!', ':P']

    TWEETS = [s0, s1, s2, s3, s4, s5, s6]
    TOKS = [t0, t1, t2, t3, t4, t5, t6]

    def test(left, right):
        """
        Compare the tool's tokenization with expected 'gold standard' output.
        """
        tokenizer = TweetTokenizer()
        toks = tokenizer.tokenize(left)
        if toks == right:
            return True
        else:
            return toks

    for (tweet, tokenized) in zip(TWEETS, TOKS):
        if test(tweet, tokenized):
            print("Pass")
        else:
            print("Expected: {}".format(tokenized))
            print("Actual: {}".format(test(tweet, tokenized)))






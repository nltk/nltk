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

import re
from nltk.compat import htmlentitydefs


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
HTML_ENTITY_DIGIT_RE = re.compile(r"&#\d+;")
HTML_ENTITY_ALPHA_RE = re.compile(r"&\w+;")
AMP = "&amp;"

######################################################################

class TweetTokenizer:
    """Tokenize Tweets"""
    def __init__(self, preserve_case=True):
        self.preserve_case = preserve_case

    def tokenize(self, s):
        """
        :param s: str
        :rtype: list(str)
        :return: a tokenized list of strings; concatenating this list returns
        the original string if preserve_case=False
        """
        # Try to ensure unicode:
        try:
            s = str(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = str(s)
        # Fix HTML character entities:
        s = self._html2unicode(s)
        # Tokenize:
        words = WORD_RE.findall(s)
        # Possibly alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:
            words = list(map((lambda x : x if EMOTICON_RE.search(x) else
                              x.lower()), words))
        return words


    def _html2unicode(self, s):
        """
        Try to replace all the HTML entities in `s` with their corresponding
        Unicode characters.
        """
        # First the digits:
        ents = set(HTML_ENTITY_DIGIT_RE.findall(s))
        if len(ents) > 0:
            for ent in ents:
                entnum = ent[2:-1]
                try:
                    entnum = int(entnum)
                    s = s.replace(ent, chr(entnum))
                except:
                    pass
        # Now the alpha versions:
        ents = set(HTML_ENTITY_ALPHA_RE.findall(s))
        ents = list(filter((lambda x : x != AMP), ents))
        for ent in ents:
            entname = ent[1:-1]
            try:
                s = s.replace(ent, chr(htmlentitydefs.name2codepoint[entname]))
            except:
                pass
            s = s.replace(AMP, " and ")
        return s

######################################################################
#{ Tokenization Function
######################################################################

def casual_tokenize(text, preserve_case=True):
    """
    Convenience function for wrapping the tokenizer.
    """
    return TweetTokenizer(preserve_case=preserve_case).tokenize(text)

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

    t0 = ['This', 'is', 'a', 'cooool', '#dummysmiley', ':', ':-)', ':-P',\
          '<3', 'and', 'some', 'arrows', '<', '>', '->', '<--']
    t1 = ['Naps', 'are', 'a', 'must', '\ud83d', '\ude34', '\ud83d', '\ude34']
    t2 = ['Renato', 'fica', 'com', 'muito', 'medo', 'de', 'ouvir', 'meus',
          'áudios', 'perto', 'da', 'gaja', 'dele', ',', 'pois', 'só', 'falo',
          'merda', 'KKK']
    t3 = ['Владелец', '20th', 'Century', 'Fox', 'намерен', 'купить', 'Warner', 'Bros', '.']
    t4 = ['RT', '@facugambande', ':', 'Ya', 'por', 'arrancar', 'a', 'grabar', '!', '!', '!', '#TirenTirenTiren', 'vamoo', '!', '!']
    t5 = ['http://t.co/7r8d5bVKyA', 'http://t.co/hZpwZe1uKt', 'http://t.co/ZKb7GKWocy', 'Ничто', 'так', 'не', 'сближает', 'людей']

    TWEETS = [s0, s1, s2, s3, s4, s5]
    TOKS = [t0, t1, t2, t3, t4, t5]

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






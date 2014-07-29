# Natural Language Toolkit: Twitter Tokenizer
#
# Copyright (C) 2001-2014 NLTK Project
# Author: Christopher Potts <cgpotts@stanford.edu>
#         Ewan Klein <ewan@inf.ed.ac.uk>
# URL: <http://nltk.org/>
# For license information, see LICENSE.TXT

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


import html.entities
import re

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

# This particular element is used in a couple ways, so we define it
# with a name:
emoticon_string = r"""
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

# URL pattern due to John Gruber, modified by Tom Winzig https://gist.github.com/winzig/8894715

url_string = r"""				# Capture 1: entire matched URL
  (?:
  https?:				# URL protocol and colon
    (?:
      /{1,3}						# 1-3 slashes
      |								#   or
      [a-z0-9%]						# Single letter or digit or '%'
      								# (Trying not to match e.g. "URI::Escape")
    )
    |							#   or
    							# looks like domain name followed by a slash:
    [a-z0-9.\-]+[.]
    (?:[a-z]{2,13})
    /
  )
  (?:							# One or more:
    [^\s()<>{}\[\]]+						# Run of non-space, non-()<>{}[]
    |								#   or
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\)  # balanced parens, one level deep: (…(…)…)
    |
    \([^\s]+?\)							# balanced parens, non-recursive: (…)
  )+
  (?:							# End with:
    \([^\s()]*?\([^\s()]+\)[^\s()]*?\)  # balanced parens, one level deep: (…(…)…)
    |
    \([^\s]+?\)							# balanced parens, non-recursive: (…)
    |									#   or
    [^\s`!()\[\]{};:'".,<>?«»“”‘’]		# not a space or one of these punct chars
  )
  |					# OR, the following to match naked domains:
  (?:
  	(?<!@)			# not preceded by a @, avoid matching foo@_gmail.com_
    [a-z0-9]+
    (?:[.\-][a-z0-9]+)*
    [.]
    (?:[a-z]{2,13})
    \b
    /?
    (?!@)			# not succeeded by a @, avoid matching "foo.na" in "foo.na@example.com"
  )
"""

# The components of the tokenizer:
regex_strings = (
    url_string,
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
    emoticon_string
    ,
    # HTML tags:
     r"""<[^>]+>"""
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
    #,
    ## URLs
    #url_string
    )

######################################################################
# This is the core tokenizing regex:
    
word_re = re.compile(r"""(%s)""" % "|".join(regex_strings), re.VERBOSE | re.I
                     | re.UNICODE)

# The emoticon string gets its own regex so that we can preserve case for them as needed:
emoticon_re = re.compile(emoticon_string, re.VERBOSE | re.I | re.UNICODE)

# These are for regularizing HTML entities to Unicode:
html_entity_digit_re = re.compile(r"&#\d+;")
html_entity_alpha_re = re.compile(r"&\w+;")
amp = "&amp;"

######################################################################

class TweetTokenizer:
    def __init__(self, preserve_case=True):
        self.preserve_case = preserve_case

    def tokenize(self, s):
        """
        Argument: s -- any string or unicode object
        Value: a tokenize list of strings; conatenating this list returns the original string if preserve_case=False
        """        
        # Try to ensure unicode:
        try:
            s = str(s)
        except UnicodeDecodeError:
            s = str(s).encode('string_escape')
            s = str(s)
        # Fix HTML character entities:
        s = self.__html2unicode(s)
        # Tokenize:
        words = word_re.findall(s)
        # Possibly alter the case, but avoid changing emoticons like :D into :d:
        if not self.preserve_case:            
            words = list(map((lambda x : x if emoticon_re.search(x) else x.lower()), words))
        return words


    def __html2unicode(self, s):
        """
        Internal method that seeks to replace all the HTML entities in
        s with their corresponding unicode characters.
        """
        # First the digits:
        ents = set(html_entity_digit_re.findall(s))
        if len(ents) > 0:
            for ent in ents:
                entnum = ent[2:-1]
                try:
                    entnum = int(entnum)
                    s = s.replace(ent, chr(entnum))	
                except:
                    pass
        # Now the alpha versions:
        ents = set(html_entity_alpha_re.findall(s))
        ents = list(filter((lambda x : x != amp), ents))
        for ent in ents:
            entname = ent[1:-1]
            try:            
                s = s.replace(ent, chr(html.entities.name2codepoint[entname]))
            except:
                pass                    
            s = s.replace(amp, " and ")
        return s

###############################################################################

if __name__ == '__main__':
    
    def test(s, toks):
        tokenise = TweetTokenizer().tokenize
        if tokenise(s) == toks:
            return True
        return tokenise(s)
    
    
    s0 = "This is a cooool #dummysmiley: :-) :-P <3"
    s1 = "Naps are a must \ud83d\ude34\ud83d\ude34"
    s2 = "Renato fica com muito medo de ouvir meus \u00e1udios perto da gaja dele, pois s\u00f3 falo merda KKK"
    s3 = "\u0412\u043b\u0430\u0434\u0435\u043b\u0435\u0446 20th Century Fox \u043d\u0430\u043c\u0435\u0440\u0435\u043d \u043a\u0443\u043f\u0438\u0442\u044c Warner Bros."
    s4 = "RT @facugambande: Ya por arrancar a grabar !!! #TirenTirenTiren vamoo !!"
    s5 = "http://t.co/7r8d5bVKyA http://t.co/hZpwZe1uKt http://t.co/ZKb7GKWocy Ничто так не сближает людей"
    
   
    
    t0 = ['This', 'is', 'a', 'cooool', '#dummysmiley', ':', ':-)', ':-P', '<3']
    t1 = ['Naps', 'are', 'a', 'must', '\ud83d', '\ude34', '\ud83d', '\ude34']
    t2 = ['Renato', 'fica', 'com', 'muito', 'medo', 'de', 'ouvir', 'meus', 'áudios', 'perto', 'da', 'gaja', 'dele', ',', 'pois', 'só', 'falo', 'merda', 'KKK']
    t3 = ['Владелец', '20th', 'Century', 'Fox', 'намерен', 'купить', 'Warner', 'Bros', '.']
    t4 = ['RT', '@facugambande', ':', 'Ya', 'por', 'arrancar', 'a', 'grabar', '!', '!', '!', '#TirenTirenTiren', 'vamoo', '!', '!']
    t5 = ['http://t.co/7r8d5bVKyA', 'http://t.co/hZpwZe1uKt', 'http://t.co/ZKb7GKWocy', 'Ничто', 'так', 'не', 'сближает', 'людей'] 

    tweets = [s0, s1, s2, s3, s4, s5]
    toks = [t0, t1, t2, t3, t4, t5]
    
    for (s, t) in zip(tweets, toks):
        print(test(s, t))

    #print(tokenise(s0) == ['This', 'is', 'a', 'cooool', '#dummysmiley', ':', ':-)', ':-P', '<3'])
    #print(tokenise(s1) == ['Naps', 'are', 'a', 'must', '\ud83d', '\ude34', '\ud83d', '\ude34'])
    #print(tokenise(s2) == ['Renato', 'fica', 'com', 'muito', 'medo', 'de', 'ouvir', 'meus', 'áudios', 'perto', 'da', 'gaja', 'dele', ',', 'pois', 'só', 'falo', 'merda', 'KKK'])
    #print(tokenise(s3) == ['Владелец', '20th', 'Century', 'Fox', 'намерен', 'купить', 'Warner', 'Bros', '.'])
    #print(tokenise(s4) == ['RT', '@facugambande', ':', 'Ya', 'por', 'arrancar', 'a', 'grabar', '!', '!', '!', '#TirenTirenTiren', 'vamoo', '!', '!'])
    #print(tokenise(s5) == ['http://t.co/7r8d5bVKyA', 'http://t.co/hZpwZe1uKt', 'http://t.co/ZKb7GKWocy', 'Ничто', 'так', 'не', 'сближает', 'людей']    )
    

    
    
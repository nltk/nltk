# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001-2007 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@csse.unimelb.edu.au>
#         Trevor Cohn <tacohn@csse.unimelb.edu.au>
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

"""
Functions for tokenizing a text, based on a regular expression
which matches tokens or gaps.
"""

import re, sre_parse, sre_constants, sre_compile

WHITESPACE = r'\s+'
NEWLINE    = r'\n'
BLANKLINE  = r'\s*\n\s*\n\s*'
WORD       = r'\w+'
WORDPUNCT  = r'[a-zA-Z]+|[^a-zA-Z\s]+'
SHOEBOXSEP = r'^\\'
TREEBANK   = r'^\(.*?(?=^\(|\Z)'

def _remove_group_identifiers(parsed_re):
    """
    Modifies the given parsed regular expression, replacing all groupings
    (as indicated by parenthesis in the regular expression string) with
    non-grouping variants (indicated with '(?:...)'). This works on the
    output of sre_parse.parse, modifing the group indentifier in
    SUBPATTERN structures to None.

    @param parsed_re: the output of sre_parse.parse(string)
    @type parsed_re: C{SubPattern}
    """
    if isinstance(parsed_re, sre_parse.SubPattern):
        # If it's a SubPattern, replace each item with its processed
        # equivalent. These classes are mutable, so that in-place
        # modification is allowed.
        for i in range(len(parsed_re)):
            parsed_re[i] = _remove_group_identifiers(parsed_re[i])
        return parsed_re
    elif isinstance(parsed_re, list) or isinstance(parsed_re, tuple):
        # Otherwise, if it's a sequence, check for the tell-tale
        # SUBPATTERN item and repair the sub item if needed
        to_process = list(parsed_re)
        if to_process[0] == sre_constants.SUBPATTERN:
            # replace next int with None
            sub_item = list(to_process[1])
            sub_item[0] = None
            to_process[1] = tuple(sub_item)

        # Process each item, in the case of nested SUBPATTERNS
        processed = map(_remove_group_identifiers, to_process)

        # Coerce back into the original type
        if isinstance(parsed_re, list):
            return processed
        else:
            return tuple(processed)
    else:
        # Don't need to do anything to other types
        return parsed_re

# Replace any grouping parentheses with non-grouping ones.  We
# need to do this, because the list returned by re.sub will
# contain an element corresponding to every set of grouping
# parentheses.  We must not touch escaped parentheses, and
# need to handle the case of escaped escapes (e.g. "\\(").
# We also need to handle nested parentheses, which means our
# regexp contexts must be zero-width. There are also issues with
# parenthesis appearing in bracketed contexts, hence we've
# operated on the intermediate parse structure from sre_parse.

def _compile(regexp):

    parsed = sre_parse.parse(regexp)
    parsed = _remove_group_identifiers(parsed)

    # Add grouping parentheses around the regexp; this will allow
    # us to access the material that was split on.
    # Need to set the Pattern to expect a single group

    pattern = sre_parse.Pattern()
    pattern.groups += 1
    grouped = sre_parse.SubPattern(pattern)
    grouped.append((sre_constants.SUBPATTERN, (1, parsed)))

    return sre_compile.compile(grouped, re.UNICODE | re.MULTILINE | re.DOTALL)

def token_split(text, pattern, advanced=False):
        """
        @return: An iterator that generates tokens and the gaps between them
        """

        if advanced:
            regex = _compile(pattern)   # pattern contains ()
        else:
            regex = re.compile(pattern, re.UNICODE | re.MULTILINE | re.DOTALL)

        # If it's a single string, then convert it to a tuple
        # (which we can iterate over, just like an iterator.)
        if isinstance(text, (str, unicode)):
            text = (text,)

        # Process each substring returned by the iterator, in turn.
        # "leftover" is used to record any leftover material when we
        # move on to a new substring.
        leftover = ''
        offset = 0
        for substring in text:
            position = 0  # The position within the substring
            
            # Skip any matching material in the substring:
            match = regex.match(substring)
            if match:
                yield leftover+substring[position:match.start()]
                yield substring[match.start():match.end()]
                position = match.end()
                leftover = ''

            # Walk through the substring, looking for matches.
            while position < len(substring):
                match = regex.search(substring, position)
                if match:
                    yield leftover+substring[position:match.start()]
                    yield substring[match.start():match.end()]
                    position = match.end()
                    leftover = ''
                else:
                    leftover = substring[position:]
                    break

            # Update the offset
            offset += position

        # If the last string had leftover, then return it.
        if leftover:
            yield leftover
            
def regexp(text, pattern, gaps=False, advanced=False):
    """
    Tokenize the text according to the regular expression pattern.

    @param text: the string or string iterator to be tokenized
    @type text: C{string} or C{iter(string)}
    @param pattern: the regular expression
    @type pattern: C{string}
    @param gaps: set to True if the pattern matches material between tokens
    @type gaps: C{boolean}
    @param advanced: set to True if the pattern is complex, making use of () groups
    @type advanced: C{boolean}
    @return: An iterator over tokens
    """

    for (i,token) in enumerate(token_split(text, pattern, advanced)):
        if ((i%2==0) == gaps and token != ''):
            yield token

def whitespace(s):
    """
    Tokenize the text at whitespace.

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=WHITESPACE, gaps=True)

def line(s):
    """
    Tokenize the text into lines.

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=NEWLINE, gaps=True)

def blankline(s):
    """
    Tokenize the text into paragraphs (separated by blank lines).

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=BLANKLINE, gaps=True)

def word(s):
    """
    Tokenize the text into sequences of word characters (a-zA-Z0-9).

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=WORD)

def wordpunct(s):
    """
    Tokenize the text into sequences of alphabetic and non-alphabetic
    characters.  E.g. "She said 'hello.'" would be tokenized to
    ["She", "said", "'", "hello", ".'"]

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=WORDPUNCT)

def shoebox(s):
    """
    Tokenize a Shoebox entry into its fields (separated by backslash markers).

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=SHOEBOXSEP, gaps=True)

def treebank(s):
    """
    Tokenize a Treebank file into its tree strings

    @param s: the string or string iterator to be tokenized
    @type s: C{string} or C{iter(string)}
    @return: An iterator over tokens
    """
    return regexp(s, pattern=TREEBANK, advanced=True)

# These rules are based on Punkt original implementation 
# with some omission of symbols that are usually not found in English text
# (e.g. chevrons).

def pword(s):
    """
    Tokenize a string using the rules from the Punkt word tokenizer.
    """

    # Separate punctuation (except period) from words:
    s = re.sub(r'(?=[\(\"\`{\[:;&\#\*@])(.)', r'\1 ', s)
    
    s = re.sub(r'(.)(?=[?!)\";}\]\*:@\'])', r'\1 ', s)
    s = re.sub(r'(?=[\)}\]])(.)', r'\1 ', s)
    s = re.sub(r'(.)(?=[({\[])', r'\1 ', s)
    s = re.sub(r'((^|\s)\-)(?=[^\-])', r'\1 ', s)

    # Treat double-hyphen as one token:
    s = re.sub(r'([^-])(\-\-+)([^-])', r'\1 \2 \3', s)
    s = re.sub(r'(\s|^)(,)(?=(\S))', r'\1\2 ', s)

    # Only separate comma if space follows:
    s = re.sub(r'(.)(,)(\s|$)', r'\1 \2\3', s)

    # Combine dots separated by whitespace to be a single token:
    s = re.sub(r'\.\s\.\s\.', r'...', s)

# Separate "No.6" (These 2 commented lines are left uncommented in original system)
##  s = re.sub(r'([A-Za-z]\.)(\d+)', r'\1 \2', s)        
##  s = re.sub(r'(.|^)(\.{2,})(.)?', r'\1 \2 \3', s)     #Separate words from ellipses

    s = re.sub(r'(^|\s)(\.{2,})([^\.\s])', r'\1\2 \3', s)
    s = re.sub(r'([^\.\s])(\.{2,})($|\s)', r'\1 \2\3', s)
    
    return iter(s.split())

##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _display(tokens):
    """
    A helper function for L{demo} that displays a list of tokens.
    """

    str = '    '+`list(tokens)`+' '   # an indented string representation
    str = re.sub(r"(.{,70})\s", r'\1\n     ', str).rstrip()   # wrap at 70 characters

    # Truncate after three lines:
    str = re.sub(r'(.+\n.+\n.+)\s\S+\n[\s\S]+(?!$)', r'\1 ...]', str)

    print str

def demo():
    """
    A demonstration that shows the output of several different
    tokenizers on the same string.
    """

    from nltk import tokenize

    # Define the test string.
    s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them.\n\nThanks."
    print 'Input text:'
    print `s`
    print
    print 'Tokenize using whitespace:'
    _display(tokenize.whitespace(s))
    print
    print 'Tokenize sequences of alphanumeric characters:'
    _display(tokenize.regexp(s, pattern=r'\w+', gaps=False))
    print
    print 'Tokenize sequences of letters and sequences of nonletters:'
    _display(tokenize.wordpunct(s))
    print
    print 'Tokenize words according to the rules of the Punkt system:'
    _display(tokenize.pword(s))
    print
    print 'Tokenize by lines:'
    _display(tokenize.line(s))
    print
    print 'Tokenize by blank lines:'
    _display(tokenize.blankline(s))
    print
    print 'A simple sentence tokenizer:'
    _display(tokenize.regexp(s, pattern=r'\.(\s+|$)', gaps=True))
    print
    
if __name__ == '__main__':
    demo()

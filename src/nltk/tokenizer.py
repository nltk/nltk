# Natural Language Toolkit: Tokenizers
#
# Copyright (C) 2001 University of Pennsylvania
# Author: Edward Loper <edloper@gradient.cis.upenn.edu>
#         Steven Bird <sb@ldc.upenn.edu> (additions)
#         Trevor Cohn <tacohn@cs.mu.oz.au> (additions)
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT
#
# $Id$

"""
Classes and interfaces for dividing a token into its constituent
pieces.  This task, which is known as X{tokenizing}, is defined by the
L{TokenizerI} interface.

This module defines several implementations of the tokenizer
interface, such as L{WSTokenizer}, which splits texts based on
whitespace; and L{RegexpTokenizer}, which uses a regular expression to
divide a token into pieces.  Several other modules also define
specialized tokenizers, such as L{nltk.tree.TreebankTokenizer} and
L{nltk.tagger.TaggedTokenizer}.  For a complete list of available
tokenizers, see the reference documentation for L{TokenizerI}.

@group Interfaces: TokenizerI
@group Tokenizers: WSTokenizer, RegexpTokenizer, LineTokenizer
@sort: TokenizerI, WSTokenizer, RegexpTokenizer, LineTokenizer
"""

import re, sre_parse, sre_constants, sre_compile
from nltk.chktype import chktype
from nltk.token import *

"""
QUESTIONS
  - should tokenizers be defined over strings or content?
  - how does abstract tokenizer get locs?
  
"""

##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
class TokenizerI:
    """
    A processing class for dividing a token's content into a list
    of subtokens.

    By default, the subtokens will be given unique location
    identifiers, based on the location of the input token.  But if the
    input token's location is unspecified, or the C{addlocs} paramater
    to the constructor is false, then locations will not be added.
    
    Particular implementations of the tokenizer interface vary in
    two ways:
    
      - They may split the token's content at different points
      - They may operate over different kinds of content (e.g., text
        content vs audio content).

    @group Tokenizing: tokenize, xtokenize, raw_tokenize, raw_xtokenize
    @group Accessors: unit, propnames
    @sort: tokenize, xtokenize, raw_tokenize, raw_xtokenize
    """
    # The input and output properties that are used by most
    # tokenizers.  Specialized tokenizers might add extra input
    # properties or output properties.
    _STANDARD_PROPERTIES = """
    @inprop:  C{text}: The content that should be divided into tokens.
    @inprop:  C{loc}: The content's location.
    @outprop: C{subtokens}: The property where the generated subtokens
              should be stored.
    @outprop: C{subtokens.text}: The content for individual subtokens.
    @outprop: C{subtokens.loc}: The locations of individual subtokens.
    """
    __doc__ += _STANDARD_PROPERTIES
    
    def __init__(self, addlocs=True, propnames={}):
        """
        Construct a new tokenizer.

        @type addlocs: C{boolean}
        @param addlocs: If true, then add a location to each generated
            subtoken, based on the input token's location.  If false,
            or if the input token does not define the C{loc} property,
            then do not add locations.
        @type propnames: C{dict}
        @param propnames: The names of the properties that are used by
            this tokenizer.  These names are encoded as a dictionary
            that maps from abstract \"property specifications\" to
            concrete property names.  For a list of the property
            property specifications used by a particular tokenizer,
            see its class docstring.
        """
        if self.__class__ == TokenizerI:
            raise AssertionError, "Interfaces can't be instantiated"

    def tokenize(self, token):
        """
        Divide the given token's C{text} property into a list of
        subtokens, and output that list to the C{subtokens} property.
        Each subtoken defines a C{text} property, containing its
        text; and a C{loc} property, containing its location.  The
        locations are properly ordered; i.e., for any i and j such
        that i<j::

            subtokens[i]['loc'] < subtokens[j]['loc']
        
        @param token: The token whose text should be tokenized.
        @type token: C{Token}
        """
        raise NotImplementedError()

    def xtokenize(self, token):
        """
        Divide the given token's C{text} property into a list of
        subtokens, and output an iterator over that list to the
        C{subtokens} property.  Each subtoken defines a C{text}
        property, containing its text; and a C{'loc'} property,
        containing its location.  The locations are properly ordered;
        i.e., for any i and j such that i<j::

            subtokens[i]['loc'] < subtokens[j]['loc']
        
        The token's C{text} property may contain an iterator over
        strings, in which case the text content is taken to be the
        concatenation of the substrings returned by the iterator
        (i.e., C{''.join(token['text'])}).

        @param token: The token whose text should be tokenized.
        @type token: C{Token}
        """
        # By default, call tokenize.
        raise NotImplementedError()

    def raw_tokenize(self, text):
        """
        Divide the given text string into a list of substrings, and
        return that list.
        
        @param text: The text to be tokenized.
        @type text: C{string}
        @rtype: C{string}
        """
        raise NotImplementedError()

    def raw_xtokenize(self, text):
        """
        Divide the given text string into a list of substrings, and
        return an iterator over that list.
        
        C{text} may be an iterator over strings, in which case the
        text is taken to be the concatination of the substrings
        returned by the iterator (i.e., C{''.join(text)}).

        @param text: The text to be tokenized.
        @type text: C{string}
        @rtype: C{string}
        """
        raise NotImplementedError()

class AbstractTokenizer(TokenizerI):
    """
    An abstract base class for tokenizers that provides default
    implementations for:
      - L{tokenize} (based on L{raw_tokenize})
      - L{xtokenize} (based on L{raw_xtokenize})
      - L{raw_xtokenize} (based on L{raw_tokenize})

    @requires: The tokenizations produced by subclasses must 
        meet the following requirement:

            - For each subtoken M{t[i]}, the text separating M{t[i-1]}
            and M{t[i]} does not contain M{t[i]} as a substring.

        This is necessary to ensure that C{AbstractLocation} can
        reconstruct the locations of tokens, given only the input
        string and the subtokens' string content.
    
    @ivar _propnames: A dictionary from property specifications to
        property names, indicating which property names to use.
    """
    __doc__ += TokenizerI._STANDARD_PROPERTIES
    
    def __init__(self, addlocs=True, propnames={}):
        # Make sure we're not directly instantiated:
        if self.__class__ == AbstractTokenizer:
            raise AssertionError, "Abstract classes can't be instantiated"

        self._addlocs = addlocs
        self._props = propnames

    def tokenize(self, token):
        assert chktype(1, token, Token)
        text_prop = self._props.get('text', 'text')
        loc_prop = self._props.get('loc', 'loc')
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        subtokens_loc_prop = self._props.get('subtokens.loc', 'loc')

        # Use raw_tokenize to get a list of subtoken texts.
        text = token[text_prop]
        subtok_texts = self.raw_tokenize(text)

        # Find the subtokens' locations (if requested)
        locs = []
        if self._addlocs and token.has(loc_prop):
            source = token[loc_prop].source()
            end = token[loc_prop].start()
            for subtok_text in subtok_texts:
                start = text.find(subtok_text, end)
                end = start+len(subtok_text)
                locs.append(CharSpanLocation(start,end,source))
            if len(locs) != len(subtok_texts):
                raise AssertionError('Unable to align subtokens with '+
                                     'the input text')
        
        # Create each subtoken from its text.
        if self._addlocs and token.has(loc_prop):
            subtoks = [Token(**{subtokens_text_prop:text,
                                subtokens_loc_prop:loc})
                       for (text,loc) in zip(subtok_texts, locs)]
        else:
            subtoks = [Token(**{subtokens_text_prop:text})
                       for text in subtok_texts]

        # Write subtoks to the subtokens property.
        token[subtokens_prop] = subtoks

    def _subtoken_generator(self, token):
        text_prop = self._props.get('text', 'text')
        loc_prop = self._props.get('loc', 'loc')
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        subtokens_loc_prop = self._props.get('subtokens.loc', 'loc')

        # Use raw_xtokenize to get an iterator over subtoken texts.
        text = token[text_prop]

        # XX OUCH: THIS WILL USE IT UP!!
        subtok_iter = self.raw_xtokenize(text)
        
        if self._addlocs and token.has(loc_prop):
            source = token[loc_prop].source()
            end = token[loc_prop].start()
            for subtok_text in subtok_iter:
                start = XXXXtext.find(subtok_text, end)
                end = start+len(subtok_text)
                loc = CharSpanLocation(start, end, source)
                yield Token(**{subtokens_text_prop:subtok_text,
                               subtokens_loc_prop:loc})
        else:
            for subtok_text in subtok_iter:
                yield Token(**{subtokens_text_prop:subtok_text})

#    def xtokenize(self, token):
#        assert chktype(1, token, Token)
#        subtokens_prop = self._props.get('subtokens', 'subtokens')
#        token[subtokens_prop] = self._subtoken_generator(token)

#    def raw_xtokenize(self, text):
#        assert chktype(1, text, str, iter)
#        if isinstance(text, iter): text = ''.join(text)
#        return iter(self.raw_tokenize(text))

    
class WSTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of text into subtokens, based on
    whitespace.  I.e., C{WSTokenizer} creates a token for each
    whitespace-delimited substring in the input text.  Leading and
    trailing whitespace are ignored.
    """ 
    __doc__ += TokenizerI._STANDARD_PROPERTIES
    
    def __init__(self, addlocs=True, propnames={}):
        AbstractTokenizer.__init__(self, addlocs, propnames)

    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return text.split()

    # WSTokenizer is a commonly-used tokenizer; so provide a
    # real implementation for xtokenize.
    def xtokenize_raw(self, text):
        for (start, end, subtext) in self._xtokenize(text):
            yield subtext

    def xtokenize(self, token):
        assert chktype(1, token, Token)
        subtokens_prop = self._props.get('subtokens', 'subtokens')
        token[subtokens_prop] = self._subtoken_generator(token)

    def _subtoken_generator(self, token):
        text_prop = self._props.get('text', 'text')
        loc_prop = self._props.get('loc', 'loc')
        subtokens_text_prop = self._props.get('subtokens.text', 'text')
        subtokens_loc_prop = self._props.get('subtokens.loc', 'loc')

        text_iter = token[text_prop]
        if self._addlocs and token.has(loc_prop):
            source = token[loc_prop].source()
            for (start, end, subtext) in self._xtokenize(text_iter):
                loc = CharSpanLocation(start, end, source)
                yield Token(**{subtokens_text_prop: subtext,
                               subtokens_loc_prop: loc})
        else:
            for (start, end, subtext) in self._xtokenize(text_iter):
                yield Token(**{subtokens_text_prop: subtext})
    
    def _xtokenize(self, text):
        whitespace = re.compile('\s+')

        # If it's a single string, then convert it to a tuple
        # (which we can iterate over, just like an iterator.)
        if type(text) is str: text = (text,)

        # Process each substring returned by the iterator, in turn.
        # "leftover" is used to record any leftover material when we
        # move on to a new substring.
        leftover = ''
        offset = 0
        for substring in text:
            position = 0  # The position within the substring
            
            # Skip any initial whitespace in the substring:
            match = whitespace.match(substring)
            if match:
                if leftover:
                    end = offset+match.start()
                    start = end-len(leftover)
                    text = leftover
                    yield start, end, text
                    leftover = ''
                position = match.end()
                

            # Walk through the substring, looking for whitespace.
            while position < len(substring):
                match = whitespace.search(substring, position)
                if match:
                    start = offset+position
                    end = offset+match.start()
                    text = leftover+substring[position:match.start()]
                    yield start, end, text
                    position = match.end()
                    leftover = ''
                else:
                    leftover = substring[position:]

            # Update the offset
            offset += position

        # If the last string had leftover, then return it.
        if leftover:
            end = offset
            start = end-len(leftover)
            text = leftover
            yield start, end, leftover
            
class LineTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of text into subtokens, based on
    newline characters.  I.e., C{LineTokenizer} creates a token for
    each newline-delimited substring in the input text.  Blank lines
    are ignored.    
    """
    __doc__ += TokenizerI._STANDARD_PROPERTIES

    def __init__(self, addlocs=True, propnames={}):
        AbstractTokenizer.__init__(self, addlocs, propnames)
        
    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return [s for s in text.split('\n') if s.strip() != '']

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

    is_list = isinstance(parsed_re, list)
    is_tuple = isinstance(parsed_re, tuple)

    if isinstance(parsed_re, sre_parse.SubPattern):
        # If it's a SubPattern, replace each item with its processed
        # equivalent. These classes are mutable, so the in place
        # modification is allowed.
        for i in range(len(parsed_re)):
            parsed_re[i] = _remove_group_identifiers(parsed_re[i])
        return parsed_re
    elif is_list or is_tuple:
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
        if is_list:
            return processed
        else:
            return tuple(processed)
    else:
        # Don't need to do anything to other types
        return parsed_re

# [XX] THIS CANT DERIVE FROM ABSTRACTTOKENIZER!!!
class RegexpTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of text into words, based on a
    regular expression.  By default, the regular expression specifies
    the form of a single word type; so the list of tokens returned
    includes all non-overlapping substrings that match the given
    regular expression.  However, if the optional constructor
    parameter C{negative} is true, then the regular expression
    specifies the form of word separators; so the list of tokens
    returned includes all substrings that occur between matches of the
    regular expression.
    
    Each word is encoded as a C{Token} whose type is a C{string}.
    Location indices start at zero, and have a unit of C{'word'}.
    """
    __doc__ += TokenizerI._STANDARD_PROPERTIES

    def __init__(self, regexp, negative=0, unit='w', propnames={}):
        """
        Create a new C{RegexpTokenizer} from a given regular expression.
        
        @type regexp: C{string} or C{SRE_Pattern}
        @param regexp: The regular expression used to tokenized texts.
            Unless C{negative} is true, this regular expression
            specifies the form of a single word type; so the list of
            tokens generated by tokenization includes all non-overlapping
            substrings that match C{regexp}
        @type negative: C{boolean}
        @param negative: An optional parameter that inverts the
            meaning of C{regexp}.  In particular, if C{negative} is
            true, then C{regexp} is taken to specify the form of word
            separators (and not word types); so the list of tokens
            generated by tokenization includes all substrings that
            occur I{between} matches of the regular expression.
        @type unit: C{string}
        @param unit: The unit that should be used for the locations of
            tokens created by the tokenizer.  If no unit is specified,
            then the default unit C{'w'} will be used.
        """
        assert chktype(1, regexp, str)
        
        AbstractTokenizer.__init__(self, unit, propnames)

        if hasattr(regexp, 'pattern'): regexp = regexp.pattern
        self._negative = negative

        # Replace any grouping parentheses with non-grouping ones.  We
        # need to do this, because the list returned by re.sub will
        # contain an element corresponding to every set of grouping
        # parentheses.  We must not touch escaped parentheses, and
        # need to handle the case of escaped escapes (e.g. "\\(").
        # We also need to handle nested parentheses, which means our
        # regexp contexts must be zero-width. There are also issues with
        # parenthesis appearing in bracketed contexts, hence we've
        # operated on the intermediate parse structure from sre_parse.
        parsed = sre_parse.parse(regexp)
        parsed = _remove_group_identifiers(parsed)

        # Add grouping parentheses around the regexp; this will allow
        # us to access the material that was split on.
        # Need to set the Pattern to expect a single group
        pattern = sre_parse.Pattern()
        pattern.groups += 1
        grouped = sre_parse.SubPattern(pattern)
        grouped.append((sre_constants.SUBPATTERN, (1, parsed)))

        self._regexp = sre_compile.compile(grouped, re.UNICODE)

    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        
        # This split will return a list of alternating matches and
        # non-matches.  If negative=1, then we want the even elements;
        # if negative=0, then we want the odd elements.
        words = self._regexp.split(text)
        
        if self._negative:
            # Return only the even words.
            return [w for (i,w) in enumerate(words) if i%2==0 and w!='']
        else:
            # Return only the odd words.
            return [w for (i,w) in enumerate(words) if i%2==1 and w!='']
            
##//////////////////////////////////////////////////////
##  Demonstration
##//////////////////////////////////////////////////////

def _display(token, tokenizer):
    """
    A helper function for L{demo} that displays a list of tokens.
    """
    token = token.copy() # Make a new copy.
    tokenizer.tokenize(token)
    tokens = token['subtokens']
    
    # Get the string representation:
    str = '    '+`tokens`+' '
    
    # Word wrap the string at 70 characters:
    str = re.sub(r"(.{,70})\s", r'\1\n     ', str).rstrip()

    # Truncate the string at 3 lines:
    str = re.sub(r'(.+\n.+\n.+)\s\S+\n[\s\S]+(?!$)', r'\1 ...]', str)

    # Print the string
    print str

def demo():
    """
    A demonstration that shows the output of several different
    tokenizers on the same string.
    """
    # Define the test string.
    s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them."
    print 'Test string:'
    print `s`
    tok = Token(text=s)
    print
    print 'Tokenize using whitespace:'
    _display(tok, WSTokenizer())
    print
    print 'Tokenize sequences of alphanumeric characters:'
    _display(tok, RegexpTokenizer(r'\w+'))
    print
    print 'Tokenize sequences of letters and sequences of nonletters:'
    _display(tok, RegexpTokenizer(r'[a-zA-zZ]+|[^a-zA-Z\s]+'))
    print
    print 'A simple sentence tokenizer:'
    _display(tok, RegexpTokenizer(r'\.(\s+|$)', negative=1, unit='s'))
    print
    print 'Tokenize by lines:'
    _display(tok, LineTokenizer())
    print
    
if __name__ == '__main__':
    demo()
    

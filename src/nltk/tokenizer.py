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
@group Tokenizers: WSTokenizer, RegexpTokenizer, LineTokenizer,
                   AbstractTokenizer
"""

import re, sre_parse, sre_constants, sre_compile
from nltk.chktype import chktype
from nltk.token import *

##//////////////////////////////////////////////////////
##  Tokenizers
##//////////////////////////////////////////////////////
class TokenizerI:
    """
    A processing class for dividing a token's content into a list of
    subtokens.  Particular implementations of the tokenizer interface
    vary in two ways:
    
      - They may split the token's content at different points
      - They may operate over different kinds of content (e.g., text
        content vs audio content).

    @group Tokenizing: tokenize, xtokenize, raw_tokenize, raw_xtokenize
    @group Accessors: unit
    @sort: tokenize, xtokenize, raw_tokenize, raw_xtokenize
    
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{loc}: The subtokens' locations.
    """
    def tokenize(self, token):
        """
        Divide the given token's C{text} property into a list of
        subtokens, and output that list to the C{subtokens} property.
        Each subtoken defines a C{text} property, containing its
        text; and a C{loc} property, containing its location.  The
        locations are properly ordered; i.e., for any i and j such
        that i<j::

           subtokens[i]['loc'].end() <= subtokens[j]['loc'].start()
        
        @type token: L{Token}
        @param token: The token whose text should be tokenized.
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

           subtokens[i]['loc'].end() <= subtokens[j]['loc'].start()
        
        The token's C{text} property may contain an iterator over
        strings, in which case the text content is taken to be the
        concatenation of the substrings returned by the iterator
        (i.e., C{''.join(token['text'])}).

        @type token: L{Token}
        @param token: The token whose text should be tokenized.
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
    An abstract base class for tokenizers.  C{AbstractTokenizer}
    provides default implementations for:
    
      - L{xtokenize} (based on C{tokenize})
      - L{raw_tokenize} (based on C{tokenize})
      - L{raw_xtokenize} (based on C{xtokenize})

    It also provides L{_tokenize_from_raw}, which can be used to
    implement C{tokenize} based on C{raw_tokenize}; and
    L{_xtokenize_from_raw}, which can be used to implement
    X{xtokenize} based on X{raw_xtokenize}.

    @inprop: C{text}: The input token's text content.
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{text}: The subtokens' text content.
    @outprop: C{loc}: The subtokens' locations.
    """
    def __init__(self, addlocs=True, **property_names):
        """
        Construct a new tokenizer.

        @type addlocs: C{boolean}
        @param addlocs: If true, then add a location to each generated
            subtoken, based on the input token's location.  If false,
            or if the input token does not define the C{loc} property,
            then do not add locations.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        if self.__class__ == AbstractTokenizer:
            raise AssertionError, "Abstract classes can't be instantiated"
        self._addlocs = addlocs
        self._property_names = property_names

    def xtokenize(self, token):
        assert chktype(1, token, Token)
        TEXT = self._property_names.get('text', 'text')
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        text = token[TEXT]
        if hasattr(text, '__iter__') and hasattr(text, 'next'):
            token[TEXT] = ''.join(text)
        self.tokenize(token)
        token[SUBTOKENS] = iter(token[SUBTOKENS])

    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        TEXT = self._property_names.get('text', 'text')
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        token = Token({TEXT:text})
        self.tokenize(token)
        return [subtok[TEXT] for subtok in token[SUBTOKENS]]

    def raw_xtokenize(self, text):
        assert chktype(1, text, str)
        TEXT = self._property_names.get('text', 'text')
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        token = Token({TEXT:text})
        self.xtokenize(token)
        for subtok in token[SUBTOKENS]:
            yield subtok[TEXT]

    def _tokenize_from_raw(self, token, **property_names):
        """
        Tokenize the given token by using C{self.raw_tokenize} to
        tokenize its text string.  Locations are reconstructed by
        searching for each consecutive token in the text string.  To
        ensure that locations are correctly assigned,
        C{self.raw_tokenize} must make the following guarantee:

            - For each subtoken M{t[i]}, the text separating M{t[i-1]}
              and M{t[i]} does not contain M{t[i]} as a substring.

        This method is intended to be used by subclasses that wish to
        implement the C{tokenize} method based on C{raw_tokenize}.
        """
        assert chktype(1, token, Token)
        TEXT = self._property_names.get('text', 'text')
        LOC = self._property_names.get('loc', 'loc')
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')

        # Use raw_tokenize to get a list of subtoken texts.
        text = token[TEXT]
        subtok_texts = self.raw_tokenize(text)

        # Find the subtokens' locations (if requested)
        locs = []
        if self._addlocs and token.has(LOC):
            source = token[LOC].source()
            end = token[LOC].start()
            for subtok_text in subtok_texts:
                start = text.find(subtok_text, end)
                assert start>=0, 'Tokenization alignment failure'
                end = start+len(subtok_text)
                locs.append(CharSpanLocation(start,end,source))
        
        # Create each subtoken from its text.
        if self._addlocs and token.has(LOC):
            subtoks = [Token({TEXT:text, LOC:loc})
                       for (text,loc) in zip(subtok_texts, locs)]
        else:
            subtoks = [Token({TEXT:text})
                       for text in subtok_texts]

        # Write subtoks to the subtokens property.
        token[SUBTOKENS] = subtoks

    def _xtokenize_from_raw(self, token):
        """
        XTokenize the given token by using C{self.raw_xtokenize} to
        tokenize its text string.  Locations are reconstructed by
        searching for each consecutive token in the text string.  To
        ensure that locations are correctly assigned,
        C{self.raw_xtokenize} must make the following guarantee:

            - For each subtoken M{t[i]}, the text separating M{t[i-1]}
              and M{t[i]} does not contain M{t[i]} as a substring.

        This method is intended to be used by subclasses that wish to
        implement the C{xtokenize} method based on C{raw_xtokenize}.
        """
        assert chktype(1, token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        iter = self._xtokenize_from_raw_helper(token, **self._property_names)
        token[SUBTOKENS] = iter
        
    def _xtokenize_from_raw_helper(token):
        """
        A helper function for L{xtokenize_from_raw}.
        """
        assert chktype(1, token, Token)
        TEXT = self._property_names.get('text', 'text')
        LOC = self._property_names.get('loc', 'loc')

        # Get the token's text.  If it's an iterator, then collapse
        # it into a single string.
        text = token[TEXT]
        if hasattr(text, '__iter__') and hasattr(text, 'next'):
            text = ''.join(text)
            
        # Use raw_xtokenize to get an iterator of subtoken texts.
        subtok_textiter = self.raw_xtokenize(text)

        # Find the subtokens' locations (if requested)
        locs = []
        if self._addlocs and token.has(LOC):
            source = token[LOC].source()
            end = token[LOC].start()
            for subtok_text in subtok_textiter:
                start = text.find(subtok_text, end)
                assert start>=0, 'Tokenization alignment failure'
                end = start+len(subtok_text)
                loc = CharSpanLocation(start,end,source)
                yield Token({TEXT:subtok_text, LOC:loc})
        else:
            for subtok_text in subtok_iter:
                yield Token({TEXT:subtok_text})

class WSTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of text into subtokens, based on
    whitespace.  I.e., C{WSTokenizer} creates a token for each
    whitespace-delimited substring in the input text.  Leading and
    trailing whitespace are ignored.
    
    @inprop: C{text}: The input token's text content.
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{text}: The subtokens' text content.
    @outprop: C{loc}: The subtokens' locations.
    """ 
    #////////////////////////////////////////////////////////////
    # Basic tokenization

    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return text.split()

    def tokenize(self, token):
        # Delegate to self.raw_tokenize()
        assert chktype(1, token, Token)
        self._tokenize_from_raw(token)

    #////////////////////////////////////////////////////////////
    # Iterated tokenization

    def xtokenize_raw(self, text):
        for (start, end, subtext) in self._xtokenize_helper(text):
            yield subtext

    def xtokenize(self, token):
        assert chktype(1, token, Token)
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')
        token[SUBTOKENS] = self._subtoken_generator(token)

    def _subtoken_generator(self, token):
        TEXT = self._property_names.get('text', 'text')
        LOC = self._property_names.get('loc', 'loc')

        text_iter = token[TEXT]
        if self._addlocs and token.has(LOC):
            source = token[LOC].source()
            for (start, end, subtext) in self._xtokenize_helper(text_iter):
                loc = CharSpanLocation(start, end, source)
                yield Token({TEXT: subtext, LOC: loc})
        else:
            for (start, end, subtext) in self._xtokenize_helper(text_iter):
                yield Token({TEXT: subtext})
    
    def _xtokenize_helper(self, text):
        """
        @return: An iterator that generates a tripple (M{start},
        M{end}, M{word}) for each whitespace-separated token, where
        M{start} is the start position; M{end} is the end position;
        and M{word} is C{text[M{start}:M{end}]}
        """
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
                    yield end-len(leftover), end, leftover
                    leftover = ''
                position = match.end()

            # Walk through the substring, looking for whitespace.
            while position < len(substring):
                match = whitespace.search(substring, position)
                if match:
                    yield (offset+position, offset+match.start(),
                           leftover+substring[position:match.start()])
                    position = match.end()
                    leftover = ''
                else:
                    leftover = substring[position:]

            # Update the offset
            offset += position

        # If the last string had leftover, then return it.
        if leftover:
            yield offest-len(leftover), offset, leftover
            
class LineTokenizer(AbstractTokenizer):
    """
    A tokenizer that divides a string of text into subtokens, based on
    newline characters.  I.e., C{LineTokenizer} creates a token for
    each newline-delimited substring in the input text.  Blank lines
    are ignored.
    
    @inprop: C{text}: The input token's text content.
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{text}: The subtokens' text content.
    @outprop: C{loc}: The subtokens' locations.
    """
    def raw_tokenize(self, text):
        assert chktype(1, text, str)
        return [s for s in text.split('\n') if s.strip() != '']

    def tokenize(self, token):
        # Delegate to self.raw_tokenize()
        assert chktype(1, token, Token)
        self._tokenize_from_raw(token)
        
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
        # equivalent. These classes are mutable, so the in place
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
    
    @inprop: C{text}: The input token's text content.
    @inprop: C{loc}: The input token's location.  I{(optional)}
    @outprop: C{subtokens}: The list of tokenized subtokens.
    @outprop: C{text}: The subtokens' text content.
    @outprop: C{loc}: The subtokens' locations.
    """
    def __init__(self, regexp, negative=False, addlocs=True,
                 **property_names):
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
        @type addlocs: C{boolean}
        @param addlocs: If true, then add a location to each generated
            subtoken, based on the input token's location.  If false,
            or if the input token does not define the C{loc} property,
            then do not add locations.
        @type property_names: C{dict}
        @param property_names: A dictionary that can be used to override
            the default property names.  Each entry maps from a
            default property name to a new property name.
        """
        assert chktype(1, regexp, str)
        
        AbstractTokenizer.__init__(self, addlocs, **property_names)

        if hasattr(regexp, 'pattern'): regexp = regexp.pattern
        self._negative = bool(negative)

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

    def tokenize(self, token):
        assert chktype(1, token, Token)
        TEXT = self._property_names.get('text', 'text')
        LOC = self._property_names.get('loc', 'loc')
        SUBTOKENS = self._property_names.get('subtokens', 'subtokens')

        # If we're not adding locations, then just delegate to
        # raw_tokenize.
        if not (self._addlocs and token.has(LOC)):
            self._tokenize_from_raw(token)
            return

        # This split will return a list of alternating matches and
        # non-matches.  If negative=1, then we want the even elements;
        # if negative=0, then we want the odd elements.
        words = self._regexp.split(token[TEXT])

        # Get the input token's source and start position.
        source = token[LOC].source()
        pos = token[LOC].start()

        # Generate a list of subtokens with locations.
        subtoks = []
        for i, w in enumerate(words):
            if (i%2==0) == self._negative and w!='':
                loc = CharSpanLocation(pos, pos+len(w), source)
                subtoks.append(Token({TEXT:w, LOC:loc}))
            pos += len(w)
            
        # Write subtoks to the subtokens property.
        token[SUBTOKENS] = subtoks

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

def demo(addlocs=False):
    """
    A demonstration that shows the output of several different
    tokenizers on the same string.
    """
    # Define the test string.
    s = "Good muffins cost $3.88\nin New York.  Please buy me\ntwo of them."
    tok = Token(text=s, loc=CharSpanLocation(0, len(s), 's'))
    print 'Input text:'
    print `s`
    print
    print 'Tokenize using whitespace:'
    _display(tok, WSTokenizer(addlocs=addlocs))
    print
    print 'Tokenize sequences of alphanumeric characters:'
    _display(tok, RegexpTokenizer(r'\w+', addlocs=addlocs))
    print
    print 'Tokenize sequences of letters and sequences of nonletters:'
    _display(tok, RegexpTokenizer(r'[a-zA-zZ]+|[^a-zA-Z\s]+',
                                  addlocs=addlocs))
    print
    print 'A simple sentence tokenizer:'
    _display(tok, RegexpTokenizer(r'\.(\s+|$)', negative=True,
                                  addlocs=addlocs))
    print
    print 'Tokenize by lines:'
    _display(tok, LineTokenizer(addlocs=addlocs))
    print
    
if __name__ == '__main__':
    print '#'*70
    print '##'+'nltk.tokenizer Demonstration'.center(66)+'##'
    print '##'+'(addlocs = True)'.center(66)+'##'
    print '#'*70
    demo(True)
    
    print '#'*70
    print '##'+'nltk.tokenizer Demonstration'.center(66)+'##'
    print '##'+'(addlocs = False)'.center(66)+'##'
    print '#'*70
    demo(False)
    

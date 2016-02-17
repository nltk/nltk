# -*- coding: utf-8 -*-
# Natural Language Toolkit: 
#
# Copyright (C) 2001-2015 NLTK Project
# Author: Pidong Wang, Josh Schroeder, based on code by Philipp Koehn
# Contributors: Liling Tan, Martijn Pieters, Wiktor Stribizew
#
# URL: <http://nltk.sourceforge.net>
# For license information, see LICENSE.TXT

import re
from six import text_type

from nltk.tokenize.api import TokenizerI
from nltk.corpus import perluniprops, nonbreaking_prefixes

class MosesTokenizer(TokenizerI):
    """
    This is a Python port of the Moses Tokenizer from 
    https://github.com/moses-smt/mosesdecoder/blob/master/scripts/tokenizer/tokenizer.perl
    """
    
    # Perl Unicode Properties character sets.
    IsN = text_type(''.join(perluniprops.chars('IsN')))
    IsAlnum = text_type(''.join(perluniprops.chars('IsAlnum')))
    IsSc = text_type(''.join(perluniprops.chars('IsSc')))
    IsSo = text_type(''.join(perluniprops.chars('IsSo')))
    IsAlpha = text_type(''.join(perluniprops.chars('IsAlpha')))
    IsLower = text_type(''.join(perluniprops.chars('IsLower')))
    
    # Remove ASCII junk.
    DEDUPLICATE_SPACE = r'\s+', r' '
    ASCII_JUNK = r'[\000-\037]', r''
    
    # Neurotic Perl heading space, multi-space and trailing space chomp.
    # These regexes are kept for reference purposes and shouldn't be used!!
    MID_STRIP = r" +", r" "     # Use DEDUPLICATE_SPACE instead.
    LEFT_STRIP = r"^ ", r""     # Uses text.lstrip() instead.
    RIGHT_STRIP = r" $", r""    # Uses text.rstrip() instead.
    
    # Pad all "other" special characters not in IsAlnum.
    PAD_NOT_ISALNUM = u'([^{}\s\.\'\`\,\-])'.format(IsAlnum), r' \1 '
    
    # Splits all hypens (regardless of circumstances), e.g.
    # 'foo -- bar' -> 'foo @-@ @-@ bar' , 'foo-bar' -> 'foo @-@ bar'
    AGGRESSIVE_HYPHEN_SPLIT = u'([{alphanum}])\-(?=[{alphanum}])'.format(alphanum=IsAlnum), r'\1 \@-\@ '
    
    # Make multi-dots stay together.
    REPLACE_DOT_WITH_LITERALSTRING_1 = r'\.([\.]+)', ' DOTMULTI\1'
    REPLACE_DOT_WITH_LITERALSTRING_2 = r'DOTMULTI\.([^\.])', 'DOTDOTMULTI \1'
    REPLACE_DOT_WITH_LITERALSTRING_3 = r'DOTMULTI\.', 'DOTDOTMULTI'
  
    # Separate out "," except if within numbers (5,300)
    # e.g.  A,B,C,D,E > A , B,C , D,E
    # First application uses up B so rule can't see B,C
    # two-step version here may create extra spaces but these are removed later
    # will also space digit,letter or letter,digit forms (redundant with next section)
    COMMA_SEPARATE_1 = u'([^{}])[,]'.format(IsN), r'\1 , '
    COMMA_SEPARATE_2 = u'[,]([^{}])'.format(IsN), r' , \1'
    
    # Attempt to get correct directional quotes.
    DIRECTIONAL_QUOTE_1 = r'^``',               r'`` '
    DIRECTIONAL_QUOTE_2 = r'^"',                r'`` '
    DIRECTIONAL_QUOTE_3 = r'^`([^`])',          r'` \1'
    DIRECTIONAL_QUOTE_4 = r"^'",                r'`  '
    DIRECTIONAL_QUOTE_5 = r'([ ([{<])"',        r'\1 `` '
    DIRECTIONAL_QUOTE_6 = r'([ ([{<])``',       r'\1 `` '
    DIRECTIONAL_QUOTE_7 = r'([ ([{<])`([^`])',  r'\1 ` \2'
    DIRECTIONAL_QUOTE_8 = r"([ ([{<])'",        r'\1 ` '
    
    # Replace ... with _ELLIPSIS_
    REPLACE_ELLIPSIS = r'\.\.\.',       r' _ELLIPSIS_ '
    # Restore _ELLIPSIS_ with ...
    RESTORE_ELLIPSIS = r'_ELLIPSIS_',   r'\.\.\.'
    
    # Pad , with tailing space except if within numbers, e.g. 5,300
    # These are used in nltk.tokenize.moses.penn_tokenize()
    COMMA_1 = u'([^{numbers})[,]([^{numbers}])'.format(numbers=IsN), r'\1 , \2'
    COMMA_2 = u'([{numbers}])[,]([^{numbers}])'.format(numbers=IsN), r'\1 , \2'
    COMMA_3 = u'([^{numbers}])[,]([{numbers}])'.format(numbers=IsN), r'\1 , \2'
    
    # Pad unicode symbols with spaces.
    SYMBOLS = u'([;:@#\$%&{}{}])'.format(IsSc, IsSo), r' \1 '
    
    # Separate out intra-token slashes.  PTB tokenization doesn't do this, so
    # the tokens should be merged prior to parsing with a PTB-trained parser.
    # e.g. "and/or" -> "and @/@ or"
    INTRATOKEN_SLASHES = u'([{alphanum}])\/([{alphanum}])'.format(alphanum=IsAlnum), r'$1 \@\/\@ $2'
    
    # Splits final period at end of string.
    FINAL_PERIOD = r"""([^.])([.])([\]\)}>"']*) ?$""", r'\1 \2\3'
    # Pad all question marks and exclamation marks with spaces.
    PAD_QUESTION_EXCLAMATION_MARK = r'([?!])', r' \1 '
    
    # Handles parentheses, brackets and converts them to PTB symbols.
    PAD_PARENTHESIS = r'([\]\[\(\){}<>])', r' \1 '
    CONVERT_PARENTHESIS_1 = r'\(', '-LRB-'
    CONVERT_PARENTHESIS_2 = r'\)', '-RRB-'
    CONVERT_PARENTHESIS_3 = r'\[', '-LSB-'
    CONVERT_PARENTHESIS_4 = r'\]', '-RSB-'
    CONVERT_PARENTHESIS_5 = r'\{', '-LCB-'
    CONVERT_PARENTHESIS_6 = r'\}', '-RCB-'
    
    # Pads double dashes with spaces.
    PAD_DOUBLE_DASHES = r'--', ' -- '
    
    # Adds spaces to start and end of string to simplify further regexps.
    PAD_START_OF_STR = r'^', ' '
    PAD_END_OF_STR = r'$', ' ' 
    
    # Converts double quotes to two single quotes and pad with spaces.
    CONVERT_DOUBLE_TO_SINGLE_QUOTES = r'"', " '' "
    # Handles single quote in possessives or close-single-quote.
    HANDLES_SINGLE_QUOTES = r"([^'])' ", r"\1 ' "
    
    # Pad apostrophe in possessive or close-single-quote.
    APOSTROPHE = r"([^'])'", r"\1 ' "
    
    # Prepend space on contraction apostrophe.
    CONTRACTION_1 = r"'([sSmMdD]) ", r" '\1 "
    CONTRACTION_2 = r"'ll ", r" 'll "
    CONTRACTION_3 = r"'re ", r" 're "
    CONTRACTION_4 = r"'ve ", r" 've "
    CONTRACTION_5 = r"n't ", r" n't "
    CONTRACTION_6 = r"'LL ", r" 'LL "
    CONTRACTION_7 = r"'RE ", r" 'RE "
    CONTRACTION_8 = r"'VE ", r" 'VE "
    CONTRACTION_9 = r"N'T ", r" N'T "
    
    # Informal Contractions.
    CONTRACTION_10 = r" ([Cc])annot ",  r" \1an not " 
    CONTRACTION_11 = r" ([Dd])'ye ",    r" \1' ye "
    CONTRACTION_12 = r" ([Gg])imme ",   r" \1im me "
    CONTRACTION_13 = r" ([Gg])onna ",   r" \1on na "
    CONTRACTION_14 = r" ([Gg])otta ",   r" \1ot ta "
    CONTRACTION_15 = r" ([Ll])emme ",   r" \1em me "
    CONTRACTION_16 = r" ([Mm])ore$text =~ s='n ",  r" \1ore 'n "
    CONTRACTION_17 = r" '([Tt])is ",    r" '\1 is "
    CONTRACTION_18 = r" '([Tt])was ",   r" '\1 was "
    CONTRACTION_19 = r" ([Ww])anna ",   r" \1an na "
    
    # Clean out extra spaces
    CLEAN_EXTRA_SPACE_1 = r'  *', r' '
    CLEAN_EXTRA_SPACE_2 = r'^ *', r''
    CLEAN_EXTRA_SPACE_3 = r' *$', r''
    
    # Escape special characters.
    ESCAPE_AMPERSAND = r'\&', r'\&amp;'
    ESCAPE_PIPE = r'\|', r'\&#124;'
    ESCAPE_LEFT_ANGLE_BRACKET = r'\<', r'\&lt;'
    ESCAPE_RIGHT_ANGLE_BRACKET = r'\>', r'\&gt;'
    ESCAPE_SINGLE_QUOTE = r"\'", r"\&apos;"
    ESCAPE_DOUBLE_QUOTE = r'\"', r'\&quot;'
    ESCAPE_LEFT_SQUARE_BRACKET = r"\[", r"\&#91;"
    ESCAPE_RIGHT_SQUARE_BRACKET = r"\]", r"\&#93;"
    
    EN_SPECIFIC_1 = u"([^{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    EN_SPECIFIC_2 = u"([^{alpha}{isn}])[']([{alpha}])".format(alpha=IsAlpha, isn=IsN), r"\1 ' \2" 
    EN_SPECIFIC_3 = u"([{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    EN_SPECIFIC_4 = u"([{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    EN_SPECIFIC_5 = u"([{isn}])[']([s])".format(isn=IsN), r"\1 '\2"
    
    ENGLISH_SPECIFIC_APOSTROPHE = [EN_SPECIFIC_1, EN_SPECIFIC_2, EN_SPECIFIC_3, 
                                   EN_SPECIFIC_4, EN_SPECIFIC_5]
    
    FR_IT_SPECIFIC_1 = u"([^{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_2 = u"([^{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_3 = u"([{alpha}])[']([^{alpha}])".format(alpha=IsAlpha), r"\1 ' \2"
    FR_IT_SPECIFIC_4 = u"([{alpha}])[']([{alpha}])".format(alpha=IsAlpha), r"\1' \2"
    
    FR_IT_SPECIFIC_APOSTROPHE = [FR_IT_SPECIFIC_1, FR_IT_SPECIFIC_2, 
                                 FR_IT_SPECIFIC_3, FR_IT_SPECIFIC_4]
    
    NON_SPECIFIC_APOSTROPHE = r"\'", r" \' " 
    
    MOSES_PENN_REGEXES_1 = [DEDUPLICATE_SPACE, ASCII_JUNK, DIRECTIONAL_QUOTE_1,
                              DIRECTIONAL_QUOTE_2, DIRECTIONAL_QUOTE_3, 
                              DIRECTIONAL_QUOTE_4, DIRECTIONAL_QUOTE_5,
                              DIRECTIONAL_QUOTE_6, DIRECTIONAL_QUOTE_7,
                              DIRECTIONAL_QUOTE_8, REPLACE_ELLIPSIS, COMMA_1, 
                              COMMA_2, COMMA_3, SYMBOLS, INTRATOKEN_SLASHES, 
                              FINAL_PERIOD, PAD_QUESTION_EXCLAMATION_MARK, 
                              PAD_PARENTHESIS, CONVERT_PARENTHESIS_1, 
                              CONVERT_PARENTHESIS_2, CONVERT_PARENTHESIS_3, 
                              CONVERT_PARENTHESIS_4, CONVERT_PARENTHESIS_5, 
                              CONVERT_PARENTHESIS_6, PAD_DOUBLE_DASHES, 
                              PAD_START_OF_STR, PAD_END_OF_STR, 
                              CONVERT_DOUBLE_TO_SINGLE_QUOTES, 
                              HANDLES_SINGLE_QUOTES, APOSTROPHE, CONTRACTION_1, 
                              CONTRACTION_2, CONTRACTION_3, CONTRACTION_4, 
                              CONTRACTION_5, CONTRACTION_6, CONTRACTION_7, 
                              CONTRACTION_8, CONTRACTION_9, CONTRACTION_10, 
                              CONTRACTION_11, CONTRACTION_12, CONTRACTION_13, 
                              CONTRACTION_14, CONTRACTION_15, CONTRACTION_16, 
                              CONTRACTION_17, CONTRACTION_18, CONTRACTION_19]
        
    MOSES_PENN_REGEXES_2 = [RESTORE_ELLIPSIS, CLEAN_EXTRA_SPACE_1, 
                        CLEAN_EXTRA_SPACE_2, CLEAN_EXTRA_SPACE_3, 
                        ESCAPE_AMPERSAND, ESCAPE_PIPE, 
                        ESCAPE_LEFT_ANGLE_BRACKET, ESCAPE_RIGHT_ANGLE_BRACKET, 
                        ESCAPE_SINGLE_QUOTE, ESCAPE_DOUBLE_QUOTE]    

    MOSES_ESCAPE_XML_REGEXES = [ESCAPE_AMPERSAND, ESCAPE_PIPE, 
                                ESCAPE_LEFT_ANGLE_BRACKET, 
                                ESCAPE_RIGHT_ANGLE_BRACKET, 
                                ESCAPE_SINGLE_QUOTE, ESCAPE_DOUBLE_QUOTE, 
                                ESCAPE_LEFT_SQUARE_BRACKET, 
                                ESCAPE_RIGHT_SQUARE_BRACKET]
    
    def __init__(self, lang='en'):
        # Initialize the object.
        super(MosesTokenizer, self).__init__()
        self.lang = lang
        # Initialize the language specific nonbreaking prefixes.
        self.NONBREAKING_PREFIXES = nonbreaking_prefixes.words(lang)
        self.NUMERIC_ONLY_PREFIXES = [w.rpartition(' ')[0] for w in 
                                      self.NONBREAKING_PREFIXES if 
                                      self.has_numeric_only(w)]
        
        
    
    def replace_multidots(self, text):
        text = re.sub(r'\.([\.]+)', r' DOTMULTI\1', text)
        while re.search(r'DOTMULTI\.', text):
            text = re.sub(r'DOTMULTI\.([^\.])', r'DOTDOTMULTI \1', text)
            text = re.sub(r'DOTMULTI\.', 'DOTDOTMULTI', text)
        return text

    def restore_multidots(self, text):
        while re.search(r'DOTDOTMULTI', text):
            text = re.sub(r'DOTDOTMULTI', r'DOTMULTI.', text)
        return re.sub(r'DOTMULTI', r'.', text)
    
    def islower(self, text):
        return not set(text).difference(set(IsLower))
    
    def isalpha(self, text):
        return not set(text).difference(set(IsAlpha))
    
    def has_numeric_only(self, text):
        return bool(re.match(r'(.*)[\s]+(\#NUMERIC_ONLY\#)', text))
    
    def handles_nonbreaking_prefixes(self, text):
        # Splits the text into toknes to check for nonbreaking prefixes.
        tokens = text.split()
        num_tokens = len(tokens)
        for i, token in enumerate(tokens):
            # Checks if token ends with a fullstop.
            token_ends_with_period = re.match(r'^(\S+)\.$', text)
            if token_ends_with_period:
                prefix = token_ends_with_period.group(0)
                # Checks for 3 conditions if
                # i.   the prefix is a token made up of chars within the IsAlpha
                # ii.  the prefix is in the list of nonbreaking prefixes and
                #      does not contain #NUMERIC_ONLY#
                # iii. the token is not the last token and that the 
                #      next token contains all lowercase. 
                if ( (prefix and self.isalpha(prefix)) or
                     (prefix in self.NONBREAKING_PREFIXES and 
                      prefix not in self.NUMERIC_ONLY_PREFIXES) or
                     (i != num_tokens-1 and self.islower(tokens[i+1])) ):
                    pass # No change to the token.
                # Checks if the prefix is in NUMERIC_ONLY_PREFIXES
                # and ensures that the next word is a digit.
                elif (prefix in self.NUMERIC_ONLY_PREFIXES and
                      re.match(r'^[0-9]+', token[i+1])):
                    pass # No change to the token.
                else: # Otherwise, adds a space after the tokens before a dot.
                    tokens[i] = prefix + ' .'
        return " ".join(tokens) # Stitch the tokens back.
    
    def escape_xml(self, text):
        for regexp, subsitution in self.MOSES_ESCAPE_XML_REGEXES:
            text = re.sub(regexp, subsitution, text)
        return text
    
    def penn_tokenize(self, text):
        """
        This is a Python port of the Penn treebank tokenizer adapted by the Moses
        machine translation community. It's a little different from the 
        version in nltk.tokenize.treebank.
        """
        # Converts input string into unicode.
        text = text_type(text) 
        # Perform a chain of regex substituitions using MOSES_PENN_REGEXES_1
        for regexp, subsitution in self.MOSES_PENN_REGEXES_1:
            text = re.sub(regexp, subsitution, text)
        # Handles nonbreaking prefixes.
        text = handles_nonbreaking_prefixes(text)
        # Restore ellipsis, clean extra spaces, escape XML symbols.
        for regexp, subsitution in self.MOSES_PENN_REGEXES_2:
            text = re.sub(regexp, subsitution, text)        
        return text
    
    def tokenize(self, text, agressive_dash_splits=False):
        """
        Python port of the Moses tokenizer. 
        
        >>> mtokenizer = MosesTokenizer()
        >>> text = u'Is 9.5 or 525,600 my favorite number?'
        >>> print (mtokenizer.tokenize(text))
        Is 9.5 or 525,600 my favorite number ?
        >>> text = u'The https://github.com/jonsafari/tok-tok/blob/master/tok-tok.pl is a website with/and/or slashes and sort of weird : things'
        >>> print (mtokenizer.tokenize(text))
        The https : / / github.com / jonsafari / tok-tok / blob / master / tok-tok.pl is a website with / and / or slashes and sort of weird : things
        >>> text = u'This, is a sentence with weird\xbb symbols\u2026 appearing everywhere\xbf'
        >>> expected = u'This , is a sentence with weird \xbb symbols \u2026 appearing everywhere \xbf'
        >>> assert mtokenizer.tokenize(text) == expected
        """
        # Converts input string into unicode.
        text = text_type(text) 
        
        # De-duplicate spaces and clean ASCII junk
        for regexp, subsitution in [self.DEDUPLICATE_SPACE, self.ASCII_JUNK]:
            text = re.sub(regexp, subsitution, text)
        # Strips heading and trailing spaces.
        text = text.strip()
        # Separate special characters outside of IsAlnum character set.
        regexp, subsitution = self.PAD_NOT_ISALNUM
        text = re.sub(regexp, subsitution, text)
        # Aggressively splits dashes
        if agressive_dash_splits:
            regexp, subsitution = self.AGGRESSIVE_HYPHEN_SPLIT
            text = re.sub(regexp, subsitution, text)
        # Replaces multidots with "DOTDOTMULTI" literal strings.
        text = self.replace_multidots(text)
        # Separate out "," except if within numbers e.g. 5,300
        for regexp, subsitution in [self.COMMA_SEPARATE_1, self.COMMA_SEPARATE_2]:
            text = re.sub(regexp, subsitution, text)
        
        # (Language-specific) apostrophe tokenization.
        if self.lang == 'en':
            for regexp, subsitution in self.ENGLISH_SPECIFIC_APOSTROPHE:
                 text = re.sub(regexp, subsitution, text)
        elif self.lang in ['fr', 'it']:
            for regexp, subsitution in self.FR_IT_SPECIFIC_APOSTROPHE:
                text = re.sub(regexp, subsitution, text)
        else:
            regexp, subsitution = self.NON_SPECIFIC_APOSTROPHE
            text = re.sub(regexp, subsitution, text)
        
        # Handles nonbreaking prefixes.
        text = self.handles_nonbreaking_prefixes(text)
        # Cleans up extraneous spaces.
        regexp, subsitution = self.DEDUPLICATE_SPACE
        text = re.sub(regexp,subsitution, text).strip()
        # Restore multidots.
        text = self.restore_multidots(text)
        # Escape XML symbols.
        text = self.escape_xml(text)
        
        return text
